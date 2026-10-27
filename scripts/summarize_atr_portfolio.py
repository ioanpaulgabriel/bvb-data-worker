from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TRADES_PATH = ROOT / "data" / "atr_portfolio_simulation_trades.csv"
EQUITY_PATH = ROOT / "data" / "atr_portfolio_simulation_equity.csv"


def main():
    trades = pd.read_csv(TRADES_PATH)
    equity = pd.read_csv(EQUITY_PATH)

    if trades.empty:
        print("Nu există tranzacții de analizat.")
        return

    trades["net_return"] = pd.to_numeric(trades["net_return"])

    wins = trades[trades["net_return"] > 0]
    losses = trades[trades["net_return"] <= 0]

    initial_equity = equity["equity"].iloc[0]
    final_equity = equity["equity"].iloc[-1]

    total_return = final_equity / initial_equity - 1
    equity["peak"] = equity["equity"].cummax()
    equity["drawdown"] = equity["equity"] / equity["peak"] - 1
    max_drawdown = equity["drawdown"].min()

    print("=== Rezumat portofoliu ATR ===")
    print(f"Perioadă: {equity['date'].iloc[0]} - {equity['date'].iloc[-1]}")
    print(f"Equity inițial: {initial_equity:.2f} RON")
    print(f"Equity final: {final_equity:.2f} RON")
    print(f"Randament total: {total_return:.2%}")
    print(f"Drawdown maxim: {max_drawdown:.2%}")
    print(f"Tranzacții: {len(trades)}")
    print(f"Winners: {len(wins)}")
    print(f"Losers: {len(losses)}")

    if len(trades):
        print(f"Win rate: {len(wins) / len(trades):.2%}")

    if len(wins):
        print(f"Profit mediu: {wins['net_return'].mean():.2%}")

    if len(losses):
        print(f"Pierdere medie: {losses['net_return'].mean():.2%}")

    print(f"Randament mediu pe tranzacție: {trades['net_return'].mean():.2%}")
    print(f"Stop-out-uri: {trades['stopped_out'].sum()}")


if __name__ == "__main__":
    main()
