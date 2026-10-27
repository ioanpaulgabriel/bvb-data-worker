import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
HISTORY_DIR = ROOT / "data" / "history"
HISTORY_DIR.mkdir(parents=True, exist_ok=True)

def load_symbols():
    clean_files = sorted((ROOT / "data" / "clean").glob("*_regs.csv"))

    if not clean_files:
        raise FileNotFoundError("Nu există fișiere BVB curate")

    latest = pd.read_csv(clean_files[-1])
    latest.columns = [column.strip().lower() for column in latest.columns]

    symbols = (
        latest["symbol"]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )

    return sorted(symbols)

START_DATE = date(2021, 1, 1)


def main():
    start = START_DATE.isoformat()
    end = (date.today() + timedelta(days=1)).isoformat()

    for symbol in load_symbols():
        yahoo_symbol = f"{symbol}.RO"

        try:
            frame = yf.download(
                yahoo_symbol,
                start=start,
                end=end,
                interval="1d",
                auto_adjust=True,
                progress=False,
            )

            if frame.empty:
                print(f"{symbol}: NO_DATA")
                continue

            if isinstance(frame.columns, pd.MultiIndex):
                frame.columns = frame.columns.get_level_values(0)

            frame = frame.reset_index()
            frame["Symbol"] = symbol

            output = frame[
                [
                    "Date",
                    "Symbol",
                    "Open",
                    "High",
                    "Low",
                    "Close",
                    "Volume",
                ]
            ].copy()

            output["Date"] = pd.to_datetime(output["Date"]).dt.date
            output = output.dropna(
                subset=["Open", "High", "Low", "Close", "Volume"]
            )

            output_path = HISTORY_DIR / f"{symbol}_history.csv"
            output.to_csv(output_path, index=False)

            print(
                f"{symbol}: {len(output)} zile, "
                f"{output['Date'].min()} - {output['Date'].max()}"
            )

        except Exception as exc:
            print(f"{symbol}: ERROR {exc}")


if __name__ == "__main__":
    main()
