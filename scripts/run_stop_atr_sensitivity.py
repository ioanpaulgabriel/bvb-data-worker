import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIMULATOR = ROOT / "src" / "atr_portfolio_simulator.py"
RUNNER = ROOT / "scripts" / "run_atr_portfolio_simulation.py"
REPORTER = ROOT / "scripts" / "build_atr_performance_report.py"

MULTIPLIERS = [1.5, 2.0, 2.5, 3.0]
RESULTS_PATH = ROOT / "data" / "atr_stop_sensitivity_results.csv"

original = SIMULATOR.read_text()
pattern = re.compile(r"^STOP_ATR_MULTIPLIER\s*=\s*(?:[0-9.]+|ATR_MULTIPLIER)$", re.MULTILINE)

if not pattern.search(original):
    raise SystemExit("Nu am gasit STOP_ATR_MULTIPLIER.")

results = ["stop_atr_multiplier,trades,stopped_out,final_equity,total_pnl,total_return,win_rate,profit_factor,stopped_pnl,normal_pnl,max_drawdown"]

for multiplier in MULTIPLIERS:
    text = pattern.sub(f"STOP_ATR_MULTIPLIER = {multiplier}", original, count=1)
    SIMULATOR.write_text(text)

    subprocess.run(["python3", str(RUNNER)], check=True, cwd=ROOT)
    subprocess.run(["python3", str(REPORTER)], check=True, cwd=ROOT)

    summary = (ROOT / "data" / "atr_portfolio_performance_summary.txt").read_text()

    def value(label: str) -> str:
        for line in summary.splitlines():
            if line.startswith(label):
                return line.split(":", 1)[1].strip().replace("%", "").replace(" RON", "")
        raise ValueError(f"Nu am gasit {label}")

    trades = value("Trades")
    stopped = value("Stopped-out trades")
    final_equity = value("Final equity")
    total_pnl = value("Total P&L")
    total_return = value("Total return")
    win_rate = value("Win rate")
    profit_factor = value("Profit factor")
    stopped_pnl = value("Stopped-out P&L")
    normal_pnl = value("Normal-exit P&L")
    max_drawdown = value("Max drawdown")

    results.append(
        f"{multiplier},{trades},{stopped},{final_equity},{total_pnl},"
        f"{total_return},{win_rate},{profit_factor},{stopped_pnl},"
        f"{normal_pnl},{max_drawdown}"
    )

    print(f"\n=== STOP_ATR_MULTIPLIER = {multiplier} ===")
    print(
        f"equity={final_equity} pnl={total_pnl} "
        f"win_rate={win_rate} pf={profit_factor} "
        f"stops={stopped} stop_pnl={stopped_pnl} dd={max_drawdown}"
    )

SIMULATOR.write_text(original)
RESULTS_PATH.write_text("\n".join(results) + "\n")

print(f"\nRezultate salvate in: {RESULTS_PATH}")
