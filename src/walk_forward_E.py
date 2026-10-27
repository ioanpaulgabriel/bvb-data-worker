import os
from dotenv import load_dotenv
load_dotenv("/home/bvb/bvb-data-worker/.env")
import pandas as pd
import numpy as np

df = pd.read_csv("output/signals.csv", parse_dates=["trade_date"])

def run_strategy(g, start, end):
    g = g[(g["trade_date"] >= start) & (g["trade_date"] <= end)].sort_values("trade_date").reset_index(drop=True)
    if g.empty:
        return None
    g["ret"] = g["close"].pct_change()
    g["position"] = 0
    in_pos = False
    trades = []
    entry_idx = None
    for i in range(len(g)):
        entry = g.loc[i, "sma_cross_up"] == 1 and g.loc[i, "close"] > g.loc[i, "sma_200"]
        if not in_pos and entry:
            in_pos = True
            entry_idx = i
        elif in_pos and g.loc[i, "sma_cross_down"] == 1:
            in_pos = False
            trades.append(g.loc[entry_idx:i, "ret"].sum())
        g.loc[i, "position"] = 1 if in_pos else 0
    if in_pos and entry_idx is not None:
        trades.append(g.loc[entry_idx:, "ret"].sum())
    strat = g["position"].shift(1) * g["ret"]
    equity = (1 + strat.fillna(0)).cumprod()
    dd = (equity / equity.cummax() - 1).min()
    wins = [t for t in trades if t > 0]
    losses = [t for t in trades if t <= 0]
    pf = (sum(wins) / abs(sum(losses))) if losses and sum(losses) != 0 else float("inf")
    return {
        "return_pct": round(100 * ((1 + strat.fillna(0)).prod() - 1), 2),
        "exposure_pct": round(100 * g["position"].mean(), 1),
        "num_trades": len(trades),
        "win_rate_pct": round(100 * len(wins) / len(trades), 1) if trades else 0,
        "profit_factor": round(pf, 2) if pf != float("inf") else "inf",
        "max_drawdown_pct": round(100 * dd, 2),
    }

periods = {"In-Sample 2021-2023": ("2021-01-01", "2023-12-31"),
           "Out-of-Sample 2024-2025": ("2024-01-01", "2025-12-31")}

rows = []
for label, (s, e) in periods.items():
    per_sym = [run_strategy(g, s, e) for _, g in df.groupby("symbol")]
    per_sym = [r for r in per_sym if r]
    agg = {
        "period": label,
        "avg_return_pct": round(np.mean([r["return_pct"] for r in per_sym]), 2),
        "avg_exposure_pct": round(np.mean([r["exposure_pct"] for r in per_sym]), 1),
        "total_trades": sum(r["num_trades"] for r in per_sym),
        "avg_win_rate_pct": round(np.mean([r["win_rate_pct"] for r in per_sym]), 1),
        "avg_profit_factor": round(np.mean([r["profit_factor"] for r in per_sym if r["profit_factor"] != "inf"]), 2),
        "avg_max_drawdown_pct": round(np.mean([r["max_drawdown_pct"] for r in per_sym]), 2),
    }
    rows.append(agg)

res = pd.DataFrame(rows)
print(res.to_string(index=False))
res.to_csv("output/walk_forward_E.csv", index=False)
print("\nSalvat in output/walk_forward_E.csv")
