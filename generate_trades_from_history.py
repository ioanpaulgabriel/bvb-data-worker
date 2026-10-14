#!/usr/bin/env python3
"""
Etapa 6 - Generare tranzactii istorice din historical_ohlcv.
Strategie: BET Overextended Mean Reversion v1.0.
"""

import csv
import os
from datetime import date
from dotenv import load_dotenv
import psycopg

START_DATE = date(2021, 1, 1)
OUTPUT_FILE = "output/trades_history.csv"
HOLD_DAYS = 5
MIN_VOLUME_RATIO = 1.5
MIN_RSI = 35
PRICE_DISCOUNT = 0.95


def wilder_rsi(closes, period=14):
    if len(closes) < period + 1:
        return None

    gains, losses = [], []

    for i in range(1, period + 1):
        change = closes[i] - closes[i - 1]
        gains.append(max(change, 0))
        losses.append(max(-change, 0))

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    for i in range(period + 1, len(closes)):
        change = closes[i] - closes[i - 1]
        avg_gain = (avg_gain * (period - 1) + max(change, 0)) / period
        avg_loss = (avg_loss * (period - 1) + max(-change, 0)) / period

    if avg_loss == 0:
        return 100.0

    return 100 - (100 / (1 + avg_gain / avg_loss))


def main():
    load_dotenv(".env")
    os.makedirs("output", exist_ok=True)

    with psycopg.connect(os.getenv("DATABASE_URL")) as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT DISTINCT symbol
            FROM historical_ohlcv
            WHERE trade_date >= %s
            ORDER BY symbol
        """, (START_DATE,))

        symbols = [row[0] for row in cur.fetchall()]
        trades = []

        for symbol in symbols:
            cur.execute("""
                SELECT trade_date, open, high, low, close, volume
                FROM historical_ohlcv
                WHERE symbol = %s
                  AND trade_date >= %s
                  AND open IS NOT NULL
                  AND high IS NOT NULL
                  AND low IS NOT NULL
                  AND close IS NOT NULL
                  AND volume IS NOT NULL
                  AND volume > 0
                ORDER BY trade_date ASC
            """, (symbol, START_DATE))

            rows = [
                {
                    "date": r[0], "open": float(r[1]), "high": float(r[2]),
                    "low": float(r[3]), "close": float(r[4]), "volume": float(r[5])
                }
                for r in cur.fetchall()
            ]

            position_open_until = date.min

            for i in range(20, len(rows) - HOLD_DAYS - 1):
                if rows[i]["date"] <= position_open_until:
                    continue

                closes = [r["close"] for r in rows[:i + 1]]
                volumes = [r["volume"] for r in rows[:i + 1]]

                sma = sum(closes[-20:]) / 20
                sma_volume = sum(volumes[-20:]) / 20

                if sma_volume <= 0:
                    continue

                volume_ratio = rows[i]["volume"] / sma_volume
                rsi = wilder_rsi(closes)

                signal = (
                    rows[i]["close"] < sma * PRICE_DISCOUNT
                    and rows[i]["close"] > rows[i]["open"]
                    and rsi is not None
                    and rsi > MIN_RSI
                    and volume_ratio >= MIN_VOLUME_RATIO
                )

                if not signal:
                    continue

                entry = rows[i + 1]
                exit_row = rows[i + 1 + HOLD_DAYS]

                trades.append({
                    "symbol": symbol,
                    "entry_date": entry["date"],
                    "exit_date": exit_row["date"],
                    "entry_price": entry["open"],
                    "exit_price": exit_row["open"],
                    "volume_ratio": round(volume_ratio, 6),
                })

                position_open_until = exit_row["date"]

            print(f"{symbol}: {len([t for t in trades if t['symbol'] == symbol])} tranzacții")

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["symbol", "entry_date", "exit_date",
                        "entry_price", "exit_price", "volume_ratio"]
        )
        writer.writeheader()
        writer.writerows(trades)

    print(f"Total tranzacții: {len(trades)}")
    print(f"Fișier generat: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
