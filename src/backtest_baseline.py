import os
from dotenv import load_dotenv
load_dotenv("/home/bvb/bvb-data-worker/.env")
import pandas as pd
import numpy as np

df = pd.read_csv("output/signals.csv", parse_dates=["trade_date"])

results = []
for sym, g in df.groupby("symbol"):
    g = g.sort_values("trade_date").reset_index(drop=True)
    g["ret"] = g["close"].pct_change()
    # Strategie: long cand sma_cross_up & vol_spike, iesire la sma_cross_down
    g["position"] = 0
    in_pos = False
    for i in range(len(g)):
        if not in_pos and g.loc[i, "sma_cross_up"] == 1 and g.loc[i, "vol_spike"] == 1:
            in_pos = True
        elif in_pos and g.loc[i, "sma_cross_down"] == 1:
            in_pos = False
        g.loc[i, "position"] = 1 if in_pos else 0
    g["strategy_ret"] = g["position"].shift(1) * g["ret"]
    total_strategy = (1 + g["strategy_ret"].fillna(0)).prod() - 1
    total_buyhold = (1 + g["ret"].fillna(0)).prod() - 1
    results.append({"symbol": sym, "strategy_return_pct": round(total_strategy*100, 2), "buyhold_return_pct": round(total_buyhold*100, 2)})

res = pd.DataFrame(results)
print(res)
print("\nMedie strategie:", res["strategy_return_pct"].mean().round(2), "%")
print("Medie buy&hold:", res["buyhold_return_pct"].mean().round(2), "%")
res.to_csv("output/backtest_baseline.csv", index=False)
