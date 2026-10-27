import os
from dotenv import load_dotenv
load_dotenv("/home/bvb/bvb-data-worker/.env")
import pandas as pd
import numpy as np

df = pd.read_csv("output/signals.csv", parse_dates=["trade_date"])

def run_strategy(g, entry_fn):
    g = g.sort_values("trade_date").reset_index(drop=True)
    g["ret"] = g["close"].pct_change()
    g["position"] = 0
    in_pos = False
    for i in range(len(g)):
        if not in_pos and entry_fn(g, i):
            in_pos = True
        elif in_pos and g.loc[i, "sma_cross_down"] == 1:
            in_pos = False
        g.loc[i, "position"] = 1 if in_pos else 0
    g["strategy_ret"] = g["position"].shift(1) * g["ret"]
    return (1 + g["strategy_ret"].fillna(0)).prod() - 1, g["position"].mean()

variants = {
    "A_baseline": lambda g, i: g.loc[i, "sma_cross_up"] == 1 and g.loc[i, "vol_spike"] == 1,
    "B_sma_only": lambda g, i: g.loc[i, "sma_cross_up"] == 1,
    "C_sma_or_macd": lambda g, i: g.loc[i, "sma_cross_up"] == 1 or g.loc[i, "macd_bullish"] == 1,
}

for name, fn in variants.items():
    rets, exposures = [], []
    for sym, g in df.groupby("symbol"):
        r, exp = run_strategy(g, fn)
        rets.append(r)
        exposures.append(exp)
    print(f"{name}: randament mediu {100*np.mean(rets):.2f}%, expunere medie {100*np.mean(exposures):.1f}%")
