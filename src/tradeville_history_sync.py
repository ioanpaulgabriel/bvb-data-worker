#!/usr/bin/env python3
"""Resilient TradeVille daily OHLCV history sync."""

import json
import os
import sys
import time
from urllib.parse import urlparse

import psycopg
from dotenv import load_dotenv
from websocket import create_connection, WebSocketConnectionClosedException

WS_URL = "wss://api.tradeville.ro:443"


def connect_tradeville():
    load_dotenv("/home/bvb/bvb-data-worker/.env")
    load_dotenv("/home/bvb/bvb-info/.env")

    ws = create_connection(
        WS_URL,
        subprotocols=["apitv"],
        timeout=30,
    )

    ws.send(json.dumps({
        "cmd": "login",
        "prm": {
            "coduser": os.getenv("TRADEVILLE_USER"),
            "parola": os.getenv("TRADEVILLE_PASSWORD"),
            "demo": os.getenv("TRADEVILLE_DEMO", "false").lower() == "true",
        },
    }))

    ws.settimeout(30)
    login = json.loads(ws.recv())

    if not login.get("OK"):
        ws.close()
        raise RuntimeError(f"Login TradeVille eșuat: {login}")

    return ws


def sync_symbol(ws, cur, symbol):
    ws.send(json.dumps({
        "cmd": "DailyValues",
        "prm": {"symbol": symbol},
    }))

    response = json.loads(ws.recv())
    data = response.get("data") or {}

    if not data.get("Symbol"):
        return 0, 0

    inserted = 0
    skipped = 0

    for i, trade_date in enumerate(data["Date"]):
        values = [
            data["Open"][i],
            data["High"][i],
            data["Low"][i],
            data["Close"][i],
            data["Volume"][i],
        ]

        if any(value is None for value in values):
            skipped += 1
            continue

        cur.execute(
            """
            INSERT INTO bvb_info.public.historical_ohlcv_tradeville
                (symbol, trade_date, open, high, low, close, volume, value, trades)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (symbol, trade_date) DO UPDATE SET
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                volume = EXCLUDED.volume,
                value = EXCLUDED.value,
                trades = EXCLUDED.trades,
                created_at = now()
            """,
            (
                symbol,
                trade_date,
                data["Open"][i],
                data["High"][i],
                data["Low"][i],
                data["Close"][i],
                data["Volume"][i],
                data["Value"][i],
                data["Trades"][i],
            ),
        )
        inserted += 1

    return inserted, skipped


def main():
    load_dotenv("/home/bvb/bvb-data-worker/.env")
    load_dotenv("/home/bvb/bvb-info/.env")

    db_url = os.getenv("BVB_DATABASE_URL")
    if not db_url:
        print("BVB_DATABASE_URL lipsește.", file=sys.stderr)
        return 1

    db_url = db_url.replace("postgresql+psycopg2://", "postgresql://")
    parsed = urlparse(db_url)

    symbols = sys.argv[1:] if len(sys.argv) > 1 else None

    conn = psycopg.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        user=parsed.username,
        password=parsed.password,
        dbname=parsed.path.lstrip("/"),
    )

    info_env = {}
    with open("/home/bvb/bvb-info/.env") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                info_env[k.strip()] = v.strip()
    info_url = info_env.get("BVB_DATABASE_URL", "").replace("postgresql+psycopg2://", "postgresql://")
    if not info_url:
        print("BVB_DATABASE_URL lipsește în bvb-info/.env", file=sys.stderr)
        return 1
    info_parsed = urlparse(info_url)
    info_conn = psycopg.connect(
        host=info_parsed.hostname,
        port=info_parsed.port or 5432,
        user=info_parsed.username,
        password=info_parsed.password,
        dbname=info_parsed.path.lstrip("/"),
    )

    with info_conn.cursor() as cur:
        if symbols:
            cur.execute(
                """
                SELECT DISTINCT symbol
                FROM public.daily_prices
                WHERE symbol = ANY(%s)
                ORDER BY symbol
                """,
                (symbols,),
            )
        else:
            cur.execute(
                """
                SELECT DISTINCT symbol
                FROM public.daily_prices
                ORDER BY symbol
                """
            )
        symbol_list = [row[0] for row in cur.fetchall()]

    print(f"Simboluri de sincronizat: {len(symbol_list)}", flush=True)

    ws = connect_tradeville()
    total_inserted = 0
    total_skipped = 0

    with info_conn.cursor() as cur:
        for symbol in symbol_list:
            for attempt in range(1, 4):
                try:
                    inserted, skipped = sync_symbol(ws, cur, symbol)
                    info_conn.commit()
                    total_inserted += inserted
                    total_skipped += skipped
                    print(
                        f"{symbol}: importate={inserted}, sărite={skipped}",
                        flush=True,
                    )
                    break
                except (
                    WebSocketConnectionClosedException,
                    ConnectionError,
                    TimeoutError,
                    OSError,
                ) as exc:
                    print(
                        f"{symbol}: conexiune pierdută, încercare {attempt}/3: {exc}",
                        flush=True,
                    )
                    try:
                        ws.close()
                    except Exception:
                        pass
                    time.sleep(3 * attempt)
                    ws = connect_tradeville()
            else:
                print(f"{symbol}: renunțat după 3 încercări", flush=True)

    ws.close()
    conn.close()

    print(f"TOTAL: importate={total_inserted}, sărite={total_skipped}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
