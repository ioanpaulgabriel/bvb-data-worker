import csv
import os
import subprocess
from pathlib import Path

HOLDINGS = [4, 6, 8, 10, 12, 14, 16]
VOLUMES = [1.5, 2.0, 2.5, 3.0]
OUT = Path("data/baseline_parameter_scan.csv")
OUT.parent.mkdir(exist_ok=True)

rows = []
for h in HOLDINGS:
    for v in VOLUMES:
        env = os.environ.copy()
        env.update({"HOLDING_DAYS": str(h), "MIN_VOLUME_RATIO": str(v), "SIMULATION_SPLIT": "train"})
        subprocess.run(["python3", "scripts/generate_atr_portfolio_signals.py"], env=env, check=True, capture_output=True)
        subprocess.run(["python3", "scripts/run_atr_portfolio_simulation.py"], env=env, check=True, capture_output=True)

        trades_path = Path("data/atr_portfolio_simulation_trades_train.csv")
        with trades_path.open() as f:
            trades = list(csv.DictReader(f))

        pnl = [float(t["net_return"]) * float(t["position_value"]) for t in trades]
        wins = [x for x in pnl if x > 0]
        losses = [x for x in pnl if x < 0]
        gross_win = sum(wins)
        gross_loss = abs(sum(losses))
        pf = gross_win / gross_loss if gross_loss else float("inf")
        total = sum(pnl)
        rows.append({
            "holding_days": h,
            "min_volume_ratio": v,
            "trades": len(trades),
            "total_pnl": round(total, 2),
            "profit_factor": round(pf, 3),
            "win_rate": round(len(wins) / len(trades), 3) if trades else 0,
        })
        print(rows[-1])

with OUT.open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)

print(f"Raport: {OUT}")
