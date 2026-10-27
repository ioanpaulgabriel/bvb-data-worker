import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIMULATOR = ROOT / "src" / "atr_portfolio_simulator.py"
RUNNER = ROOT / "scripts" / "run_atr_portfolio_simulation.py"
REPORTER = ROOT / "scripts" / "build_atr_performance_report.py"

THRESHOLDS = [1.5, 1.8, 2.0, 2.5, 3.0]
RESULTS_PATH = ROOT / "data" / "atr_volume_ratio_sensitivity_results.csv"

original = SIMULATOR.read_text()
pattern = re.compile(r"^MIN_VOLUME_RATIO\s*=\s*[0-9.]+$", re.MULTILINE)

if not pattern.search(original):
    raise SystemExit("Nu am gasit MIN_VOLUME_RATIO.")

results = [
    "min_volume_ratio,trades,stopped_out,final_equity,total_pnl,"
    "total_return,win_rate,profit_factor,stopped_pnl,normal_pnl,max_drawdown"
]

for threshold in THRESHOLDS:
    text = pattern.sub(f"MIN_VOLUME_RATIO = {threshold}", original, count=1)
    SIMULATOR.write_text(text)

    subprocess.run(["python3", str(RUNNER)], check=True, cwd=ROOT)
    subprocess.run(["python3", str(REPORTER)], check=True, cwd=ROOT)

    summary = (ROOT / "data" / "atr_portfolio_performance_summary.txt").read_text()

    def value(label: str) -> str:
        for line in summary.splitlines():
            if line.startswith(label):
                return line.split(":", 1)[1].strip().replace("%", "").replace(" RON", "")
        raise ValueError(f"Nu am gasit {label}")

    row = ",".join(
        [
            str(threshold),
            value("Trades"),
            value("Stopped-out trades"),
            value("Final equity"),
            value("Total P&L"),
            value("Total return"),
            value("Win rate"),
            value("Profit factor"),
            value("Stopped-out P&L"),
            value("Normal-exit P&L"),
            value("Max drawdown"),
        ]
    )
    results.append(row)

    print(f"\n=== MIN_VOLUME_RATIO = {threshold} ===")
    print(row)

SIMULATOR.write_text(original)
RESULTS_PATH.write_text("\n".join(results) + "\n")

print(f"\nRezultate salvate in: {RESULTS_PATH}")
