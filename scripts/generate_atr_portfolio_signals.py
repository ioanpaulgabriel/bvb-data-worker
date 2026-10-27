from pathlib import Path

import os
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
HISTORY_DIR = Path(
    os.environ.get("HISTORY_DIR", "data/history")
)
OUTPUT_PATH = ROOT / "data" / "atr_portfolio_signals.csv"

REQUIRED_COLUMNS = [
    "Date",
    "Symbol",
    "Open",
    "High",
    "Low",
    "Close",
    "Volume",
]


def load_history():
    files = sorted(HISTORY_DIR.glob("*_history.csv"))

    if not files:
        raise FileNotFoundError(f"Nu există fișiere istorice în {HISTORY_DIR}")

    frames = []

    for file_path in files:
        frames.append(pd.read_csv(file_path))

    data = pd.concat(frames, ignore_index=True)

    missing = [
        column for column in REQUIRED_COLUMNS if column not in data.columns
    ]

    if missing:
        raise ValueError(f"Coloane lipsă în istoric: {missing}")

    data["Date"] = pd.to_datetime(data["Date"]).dt.date

    for column in ["Open", "High", "Low", "Close", "Volume"]:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    data = data.dropna(
        subset=["Date", "Symbol", "Open", "High", "Low", "Close", "Volume"]
    )
    data = data.sort_values(["Symbol", "Date"])

    signal_start = os.getenv("SIGNAL_START")
    signal_end = os.getenv("SIGNAL_END")

    if signal_start:
        start_date = pd.to_datetime(signal_start).date()
        data = data[data["Date"] >= start_date]

    if signal_end:
        end_date = pd.to_datetime(signal_end).date()
        data = data[data["Date"] < end_date]

    if data.empty:
        raise ValueError(
            "Nu există date în intervalul cerut: "
            f"SIGNAL_START={signal_start}, SIGNAL_END={signal_end}"
        )

    return data


def add_indicators(data):
    data = data.copy()
    previous_close = data.groupby("Symbol")["Close"].shift(1)

    true_range = pd.concat(
        [
            data["High"] - data["Low"],
            (data["High"] - previous_close).abs(),
            (data["Low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    data["TrueRange"] = true_range

    data["ATR14"] = (
        data.groupby("Symbol")["TrueRange"]
        .transform(lambda values: values.rolling(14).mean())
    )

    data["VolumeMA20"] = (
        data.groupby("Symbol")["Volume"]
        .transform(lambda values: values.rolling(20).mean())
    )

    data["VolumeRatio"] = data["Volume"] / data["VolumeMA20"]

    return data


MIN_VOLUME_RATIO = float(os.getenv("MIN_VOLUME_RATIO", "1.5"))

def generate_signals(data):
    data = add_indicators(data)

    data["EntrySignal"] = (
        (data["ATR14"].notna())
        & (data["VolumeMA20"].notna())
        & (data["VolumeRatio"] >= MIN_VOLUME_RATIO)
        & (data["Close"] > data["Open"])
        & (data["Close"] >= 0.50)
        & (data["VolumeMA20"] >= 10000)
        & (data["Volume"] >= 10000)
    )

    signals = data[data["EntrySignal"]].copy()

    next_day = (
        data[["Symbol", "Date", "Open"]]
        .copy()
        .rename(
            columns={
                "Date": "NextDate",
                "Open": "NextOpen",
            }
        )
    )

    signals = signals.merge(
        next_day,
        on="Symbol",
        how="left",
    )

    signals = signals[signals["NextDate"] > signals["Date"]]
    signals = signals.sort_values(["Symbol", "Date"])
    signals = signals.drop_duplicates(
        subset=["Symbol", "Date"],
        keep="first",
    )

    trading_days = data[["Symbol", "Date"]].drop_duplicates().copy()
    trading_days = trading_days.sort_values(["Symbol", "Date"])
    trading_days["SessionIndex"] = trading_days.groupby("Symbol").cumcount()

    session_map = trading_days.set_index(["Symbol", "Date"])[
        "SessionIndex"
    ]

    signals["EntrySessionIndex"] = signals.set_index(
        ["Symbol", "NextDate"]
    ).index.map(session_map)

    SIGNAL_HOLDING_SESSIONS = int(os.getenv("HOLDING_DAYS", "6"))
    signals["ExitSessionIndex"] = (
        signals["EntrySessionIndex"] + SIGNAL_HOLDING_SESSIONS
    )

    exit_map = trading_days.set_index(["Symbol", "SessionIndex"])[
        "Date"
    ]

    signals["ExitDate"] = signals.set_index(
        ["Symbol", "ExitSessionIndex"]
    ).index.map(exit_map)

    signals = signals.dropna(subset=["ExitDate"])

    output = signals[
        [
            "Symbol",
            "NextDate",
            "NextOpen",
            "Date",
            "ExitDate",
            "ATR14",
            "VolumeRatio",
        ]
    ].rename(
        columns={
            "Symbol": "symbol",
            "NextDate": "entry_date",
            "NextOpen": "entry_price",
            "Date": "signal_date",
            "ExitDate": "exit_date",
        }
    )

    return output


def main():
    data = load_history()
    signals = generate_signals(data)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    signals.to_csv(OUTPUT_PATH, index=False)

    print(f"Zile de date: {data['Date'].nunique()}")
    print(f"Simboluri: {data['Symbol'].nunique()}")
    print(f"Semnale generate: {len(signals)}")
    print(f"Fișier semnale: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
