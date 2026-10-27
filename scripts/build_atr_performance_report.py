import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

from atr_portfolio_simulator import COST_RATE

TRADES_PATH = ROOT / "data" / "atr_portfolio_simulation_trades.csv"
EQUITY_PATH = ROOT / "data" / "atr_portfolio_simulation_equity.csv"
REPORT_PATH = ROOT / "data" / "atr_portfolio_performance_report.csv"
SUMMARY_PATH = ROOT / "data" / "atr_portfolio_performance_summary.txt"

INITIAL_CASH = 100_000.0


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="") as file:
        return list(csv.DictReader(file))


def calculate_trade_pnl(row: dict) -> float:
    entry_price = float(row["entry_price"])
    exit_price = float(row["exit_price"])
    position_value = float(row["position_value"])
    quantity = position_value / entry_price

    entry_cost = position_value * (1 + COST_RATE)
    exit_proceeds = quantity * exit_price * (1 - COST_RATE)

    return exit_proceeds - entry_cost


def calculate_max_drawdown(equity_rows: list[dict]) -> float:
    peak = float("-inf")
    max_drawdown = 0.0

    for row in equity_rows:
        equity = float(row["equity"])
        peak = max(peak, equity)
        drawdown = (equity - peak) / peak
        max_drawdown = min(max_drawdown, drawdown)

    return max_drawdown


def main() -> None:
    trades = read_csv(TRADES_PATH)
    equity_rows = read_csv(EQUITY_PATH)

    report_rows = []

    for row in trades:
        pnl = calculate_trade_pnl(row)
        position_value = float(row["position_value"])

        report_rows.append(
            {
                **row,
                "pnl": f"{pnl:.2f}",
                "pnl_percent": f"{pnl / position_value:.6f}",
            }
        )

    with REPORT_PATH.open("w", newline="") as file:
        fieldnames = list(report_rows[0].keys())
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(report_rows)

    pnls = [float(row["pnl"]) for row in report_rows]
    wins = [pnl for pnl in pnls if pnl > 0]
    losses = [pnl for pnl in pnls if pnl <= 0]

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = gross_profit / gross_loss if gross_loss else float("inf")

    stopped_trades = [row for row in report_rows if row["stopped_out"].lower() == "true"]
    normal_trades = [row for row in report_rows if row["stopped_out"].lower() != "true"]

    stopped_pnl = sum(float(row["pnl"]) for row in stopped_trades)
    normal_pnl = sum(float(row["pnl"]) for row in normal_trades)

    final_equity = float(equity_rows[-1]["equity"])
    total_pnl = final_equity - INITIAL_CASH
    max_drawdown = calculate_max_drawdown(equity_rows)

    summary = f"""ATR PORTFOLIO PERFORMANCE REPORT

Initial cash: {INITIAL_CASH:.2f} RON
Final equity: {final_equity:.2f} RON
Total P&L: {total_pnl:.2f} RON
Total return: {total_pnl / INITIAL_CASH:.2%}

Trades: {len(report_rows)}
Winning trades: {len(wins)}
Losing trades: {len(losses)}
Win rate: {len(wins) / len(report_rows):.2%}

Average win: {sum(wins) / len(wins):.2f} RON
Average loss: {sum(losses) / len(losses):.2f} RON
Gross profit: {gross_profit:.2f} RON
Gross loss: {gross_loss:.2f} RON
Profit factor: {profit_factor:.2f}

Stopped-out trades: {len(stopped_trades)}
Stopped-out P&L: {stopped_pnl:.2f} RON
Normal exits: {len(normal_trades)}
Normal-exit P&L: {normal_pnl:.2f} RON

Max drawdown: {max_drawdown:.2%}

Trade report: {REPORT_PATH}
"""

    SUMMARY_PATH.write_text(summary)
    print(summary)


if __name__ == "__main__":
    main()
