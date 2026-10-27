import os
from dotenv import load_dotenv
load_dotenv("/home/bvb/bvb-data-worker/.env")
import psycopg2
import pandas as pd
import numpy as np

def get_conn():
    url = os.environ["BVB_DATABASE_URL"].replace("postgresql+psycopg2://", "postgresql://")
    return psycopg2.connect(url)

def rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def atr(high, low, close, period=14):
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def main():
    conn = get_conn()
    df = pd.read_sql("SELECT symbol, trade_date, open, high, low, close, volume FROM historical_ohlcv ORDER BY symbol, trade_date", conn)
    conn.close()
    print(f"Randuri incarcate: {len(df)}")

    out = []
    for sym, g in df.groupby("symbol"):
        g = g.sort_values("trade_date").copy()
        g["rsi_14"] = rsi(g["close"])
        g["sma_20"] = g["close"].rolling(20).mean()
        g["sma_50"] = g["close"].rolling(50).mean()
        g["sma_200"] = g["close"].rolling(200).mean()
        g["vol_rel_20"] = g["volume"] / g["volume"].rolling(20).mean()
        g["atr_14"] = atr(g["high"], g["low"], g["close"])
        macd_line = g["close"].ewm(span=12).mean() - g["close"].ewm(span=26).mean()
        g["macd"] = macd_line
        g["macd_signal"] = macd_line.ewm(span=9).mean()
        out.append(g)

    result = pd.concat(out)
    result.to_csv("output/indicators.csv", index=False)
    print(f"Indicatori calculati pentru {result['symbol'].nunique()} simboluri.")
    print("Salvat in output/indicators.csv")

if __name__ == "__main__":
    main()
