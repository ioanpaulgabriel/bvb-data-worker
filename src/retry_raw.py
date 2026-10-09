from pathlib import Path
from datetime import datetime
from io import StringIO
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fetch_bvb import persist_raw_to_postgres, persist_clean_prices_to_postgres


RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


def ingest_raw_file_to_postgres(raw_path: Path) -> None:
    content = raw_path.read_text(encoding="utf-8").strip()

    if not content:
        raise ValueError(f"Fișier WAL gol: {raw_path}")

    date_part = raw_path.name.removesuffix("_bvb.csv")
    trade_date = datetime.strptime(date_part, "%Y-%m-%d").date()

    df_raw = pd.read_csv(StringIO(content))
    df_raw.columns = [str(column).strip() for column in df_raw.columns]

    required_columns = [
        "Symbol", "Name", "Market", "Trades", "Volume", "Value",
        "Open", "Low", "High", "Avg.", "Close", "Ref. price", "Var (%)",
    ]

    missing = [column for column in required_columns if column not in df_raw.columns]
    if missing:
        raise ValueError(f"Coloane lipsa: {missing}")

    df_raw["Symbol"] = df_raw["Symbol"].fillna("").astype(str).str.strip()
    df_raw["Market"] = df_raw["Market"].fillna("").astype(str).str.strip()
    df_regs = df_raw[df_raw["Market"] == "REGS"].copy()

    if df_regs.empty:
        raise ValueError("Nu exista randuri REGS")

    for column in ["Trades", "Volume"]:
        df_regs[column] = pd.to_numeric(
            df_regs[column],
            errors="raise",
        ).astype("int64")

    for column in [
        "Value", "Open", "Low", "High", "Avg.",
        "Close", "Ref. price", "Var (%)",
    ]:
        df_regs[column] = pd.to_numeric(df_regs[column], errors="raise")

    df_clean = pd.DataFrame({
        "date": trade_date.isoformat(),
        "symbol": df_regs["Symbol"].values,
        "name": df_regs["Name"].fillna("").astype(str).str.strip().values,
        "market": df_regs["Market"].values,
        "trades": df_regs["Trades"].values,
        "volume": df_regs["Volume"].values,
        "value": df_regs["Value"].values,
        "open": df_regs["Open"].values,
        "low": df_regs["Low"].values,
        "high": df_regs["High"].values,
        "avg_price": df_regs["Avg."].values,
        "close": df_regs["Close"].values,
        "ref_price": df_regs["Ref. price"].values,
        "change_pct": df_regs["Var (%)"].values,
        "source": "bvb_public_csv",
        "ingested_at": datetime.now().astimezone().isoformat(),
    })

    persist_raw_to_postgres(
        trade_date=trade_date.isoformat(),
        content=content,
        http_status=200,
        row_count=len(df_raw),
    )

    persist_clean_prices_to_postgres(df_clean)


def retry_pending_raw_files() -> None:
    files = sorted(RAW_DIR.glob("*_bvb.csv"))

    if not files:
        print(f"NU_EXISTĂ_WAL: {RAW_DIR}")
        return

    for raw_path in files:
        try:
            ingest_raw_file_to_postgres(raw_path)
            print(f"RETRY_SUCCESS: {raw_path}")
        except Exception as exc:
            print(f"RETRY_FAILED: {raw_path}: {exc}")


if __name__ == "__main__":
    retry_pending_raw_files()
