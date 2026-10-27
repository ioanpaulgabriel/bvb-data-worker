"""Generator de semnale live: blochează pozițiile pe evenimente și generează semnale Varianta E."""
import os, json
from dotenv import load_dotenv
load_dotenv("/home/bvb/bvb-data-worker/.env")
from datetime import date
import psycopg2
import pandas as pd

DB_URL = os.environ["BVB_DATABASE_URL"].replace("postgresql+psycopg2://", "postgresql://")

def get_blocked_symbols():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT symbol, action_type, ex_date, 5
        FROM corporate_actions
        WHERE status = 'verified'
          AND ex_date <= %s
          AND ex_date >= %s - INTERVAL '5 days'
        ORDER BY symbol
    """, (date.today(), date.today()))
    rows = cur.fetchall()
    cur.close(); conn.close()
    seen, unique = set(), []
    for r in rows:
        if r[0] not in seen:
            seen.add(r[0])
            unique.append({"symbol": r[0], "event_type": r[1], "effective_date": str(r[2]), "block_days": r[3]})
    return unique

def get_latest_prices():
    conn = psycopg2.connect(DB_URL)
    df = pd.read_sql("SELECT symbol, trade_date, close FROM historical_ohlcv ORDER BY symbol, trade_date", conn)
    conn.close()
    return df

def compute_signals(df):
    signals = []
    for sym, g in df.groupby("symbol"):
        g = g.sort_values("trade_date").reset_index(drop=True)
        if len(g) < 200:
            continue
        g["sma_20"] = g["close"].rolling(20).mean()
        g["sma_50"] = g["close"].rolling(50).mean()
        g["sma_200"] = g["close"].rolling(200).mean()
        last = g.iloc[-1]
        prev = g.iloc[-2]
        cross_up = (last["sma_20"] > last["sma_50"]) and (prev["sma_20"] <= prev["sma_50"])
        cross_down = (last["sma_20"] < last["sma_50"]) and (prev["sma_20"] >= prev["sma_50"])
        trend_ok = last["close"] > last["sma_200"]
        if cross_up and trend_ok:
            signals.append({"symbol": sym, "signal": "ENTRY", "close": float(last["close"])})
        elif cross_down:
            signals.append({"symbol": sym, "signal": "EXIT", "close": float(last["close"])})
    return signals

def main():
    blocked = get_blocked_symbols()
    blocked_syms = {b["symbol"] for b in blocked}
    df = get_latest_prices()
    raw_signals = compute_signals(df)
    # Filtrare: nu deschidem poziții pe simboluri blocate
    final_signals = [s for s in raw_signals if not (s["signal"] == "ENTRY" and s["symbol"] in blocked_syms)]
    result = {
        "date": str(date.today()),
        "blocked_count": len(blocked),
        "blocked_symbols": [b["symbol"] for b in blocked],
        "signals": final_signals,
        "entry_count": sum(1 for s in final_signals if s["signal"] == "ENTRY"),
        "exit_count": sum(1 for s in final_signals if s["signal"] == "EXIT"),
    }
    print(json.dumps(result, indent=2))
    os.makedirs("output", exist_ok=True)
    with open("output/live_signal_status.json", "w") as f:
        json.dump(result, f, indent=2)

if __name__ == "__main__":
    main()
