import os, sys
from datetime import timedelta
from dotenv import load_dotenv
load_dotenv("/home/bvb/bvb-data-worker/.env")
import psycopg2
import pandas as pd
from urllib.parse import urlparse

def get_conns():
    url = os.environ["BVB_DATABASE_URL"].replace("postgresql+psycopg2://", "postgresql://")
    conn = psycopg2.connect(url)
    env = {}
    with open("/home/bvb/bvb-info/.env") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    iurl = env["BVB_DATABASE_URL"].replace("postgresql+psycopg2://", "postgresql://")
    iconn = psycopg2.connect(iurl)
    return conn, iconn

def detect():
    conn, iconn = get_conns()
    prices = pd.read_sql("""
        SELECT symbol, trade_date, open, high, low, close, volume
        FROM historical_ohlcv_tradeville
        ORDER BY symbol, trade_date
    """, iconn)
    iconn.close()
    prices["trade_date"] = pd.to_datetime(prices["trade_date"])
    prices = prices.sort_values(["symbol", "trade_date"])
    prices["prev_close"] = prices.groupby("symbol")["close"].shift(1)
    prices["gap_pct"] = (prices["close"] / prices["prev_close"] - 1) * 100
    # detecteaza gapuri extreme (posibile split/bonus)
    prices["avg_vol"] = prices.groupby("symbol")["volume"].transform("mean")
    candidates = prices[(prices["gap_pct"].abs() > 80) & (prices["volume"] > 2 * prices["avg_vol"])].copy()
    print(f"Candidați gap >40%: {len(candidates)}")
    cur = conn.cursor()
    inserted = 0
    for _, r in candidates.iterrows():
        cur.execute("""
            INSERT INTO corporate_actions (symbol, action_type, ex_date, source, status)
            VALUES (%s, 'other', %s, 'auto_gap_detector', 'pending')
            ON CONFLICT DO NOTHING
        """, (r["symbol"], r["trade_date"].date()))
        inserted += cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    print(f"Evenimente noi inserate (pending): {inserted}")

if __name__ == "__main__":
    detect()
