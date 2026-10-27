import os
from dotenv import load_dotenv
load_dotenv("/home/bvb/bvb-data-worker/.env")
import pandas as pd
import numpy as np

df = pd.read_csv("output/signals.csv", parse_dates=["trade_date"])

stats = []
for sym, g in df.groupby("symbol"):
    g = g.sort_values("trade_date").reset_index(drop=True)
    g["ret"] = g["close"].pct_change()
    g["position"] = 0
    in_pos = False
    trades = []
    entry_idx = None
    for i in range(len(g)):
        if not in_pos and g.loc[i, "sma_cross_up"] == 1 and g.loc[i, "vol_spike"] == 1:
            in_pos = True
            entry_idx = i
        elif in_pos and g.loc[i, "sma_cross_down"] == 1:
            in_pos = False
            trades.append(g.loc[entry_idx:i, "ret"].sum())
        g.loc[i, "position"] = 1 if in_pos else 0
    if in_pos and entry_idx is not None:
        trades.append(g.loc[entry_idx:, "ret"].sum())
    days_in = g["position"].sum()
    total_days = len(g)
    wins = sum(1 for t in trades if t > 0)
    stats.append({
        "symbol": sym,
        "num_trades": len(trades),
        "win_rate_pct": round(100*wins/len(trades), 1) if trades else 0,
        "avg_trade_ret_pct": round(100*np.mean(trades), 2) if trades else 0,
        "days_in_market_pct": round(100*days_in/total_days, 1)
    })

res = pd.DataFrame(stats)
print(res)
print("\nTotal tranzacții:", res["num_trades"].sum())
print("Win rate mediu:", res["win_rate_pct"].mean().round(1), "%")
print("Timp mediu în piață:", res["days_in_market_pct"].mean().round(1), "%")
res.to_csv("output/strategy_diagnosis.csv", index=False)
