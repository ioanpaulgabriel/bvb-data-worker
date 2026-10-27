import os
from dotenv import load_dotenv
load_dotenv("/home/bvb/bvb-data-worker/.env")
import pandas as pd
import numpy as np

df = pd.read_csv("output/indicators.csv", parse_dates=["trade_date"])
df = df[(df["trade_date"] >= "2021-01-01") & (df["trade_date"] <= "2025-12-31")].copy()

# Semnale binare
df["rsi_oversold"] = (df["rsi_14"] < 30).astype(int)
df["rsi_overbought"] = (df["rsi_14"] > 70).astype(int)
df["sma_cross_up"] = ((df["sma_20"] > df["sma_50"]) & (df["sma_20"].shift() <= df["sma_50"].shift())).astype(int)
df["sma_cross_down"] = ((df["sma_20"] < df["sma_50"]) & (df["sma_20"].shift() >= df["sma_50"].shift())).astype(int)
df["vol_spike"] = (df["vol_rel_20"] > 1.5).astype(int)
df["macd_bullish"] = ((df["macd"] > df["macd_signal"]) & (df["macd"].shift() <= df["macd_signal"].shift())).astype(int)
df["macd_bearish"] = ((df["macd"] < df["macd_signal"]) & (df["macd"].shift() >= df["macd_signal"].shift())).astype(int)

df.to_csv("output/signals.csv", index=False)
print(f"Semnale calculate pentru {df['symbol'].nunique()} simboluri, {len(df)} randuri (2021-2025).")
print(df[["rsi_oversold","sma_cross_up","vol_spike","macd_bullish"]].sum())
