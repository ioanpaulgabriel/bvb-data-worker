#!/usr/bin/env python3
"""Import OHLCV legacy TradeVille din fisierele technical CSV."""

from __future__ import annotations

import argparse
import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import psycopg
from dotenv import load_dotenv


DEFAULT_DATA_DIR = Path("/home/bvb/bvb_trading/data/technical")
SOURCE = "tradeville_export_legacy"
REQUIRED_COLUMNS = ["Date", "Open", "High", "Low", "Close", "Volume"]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_file(path: Path, symbol: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(path)
    except Exception as exc:
        raise ValueError(f"nu pot citi CSV: {exc}") from exc

    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"lipsesc coloanele: {', '.join(missing)}")

    data = df[REQUIRED_COLUMNS].copy()
    data["Date"] = pd.to_datetime(data["Date"], errors="coerce")

    for column in REQUIRED_COLUMNS[1:]:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    if data.isna().any().any():
        bad_rows = int(data.isna().any(axis=1).sum())
        raise ValueError(f"contine {bad_rows} randuri cu date invalide")

    if data["Date"].duplicated().any():
        raise ValueError("contine date duplicate")

    if (data[["Open", "High", "Low", "Close"]] <= 0).any().any():
        raise ValueError("contine preturi <= 0")

    if (data["Low"] > data["High"]).any():
        raise ValueError("contine Low > High")

    if (data["Volume"] < 0).any():
        raise ValueError("contine volum negativ")

    if (data["Volume"] % 1 != 0).any():
        raise ValueError("contine volum neintreg")

    data = data.sort_values("Date").reset_index(drop=True)

    return pd.DataFrame(
        {
            "trade_date": data["Date"].dt.date,
            "symbol": symbol,
            "open": data["Open"],
            "high": data["High"],
            "low": data["Low"],
            "close": data["Close"],
            "volume": data["Volume"].astype("int64"),
        }
    )


def load_symbols(data_dir: Path, values: list[str] | None) -> list[str]:
    if values:
        return sorted({value.strip().upper() for value in values if value.strip()})

    return sorted(
        path.name.removesuffix("_technical.csv")
        for path in data_dir.glob("*_technical.csv")
    )


def insert_rows(
    df: pd.DataFrame,
    source_file: str,
    source_sha256: str,
) -> int:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL nu este configurat")

    ingested_at = datetime.now(timezone.utc)

    rows = [
        (
            row.trade_date,
            row.symbol,
            row.open,
            row.high,
            row.low,
            row.close,
            row.volume,
            SOURCE,
            source_file,
            source_sha256,
            ingested_at,
        )
        for row in df.itertuples(index=False)
    ]

    query = """
        INSERT INTO historical_ohlcv (
            trade_date, symbol, open, high, low, close, volume,
            source, source_file, source_sha256, ingested_at
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s
        )
        ON CONFLICT (trade_date, symbol, source)
        DO UPDATE SET
            open = EXCLUDED.open,
            high = EXCLUDED.high,
            low = EXCLUDED.low,
            close = EXCLUDED.close,
            volume = EXCLUDED.volume,
            source_file = EXCLUDED.source_file,
            source_sha256 = EXCLUDED.source_sha256,
            ingested_at = EXCLUDED.ingested_at
    """

    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.executemany(query, rows)

    return len(rows)


def process_symbol(data_dir: Path, symbol: str, dry_run: bool) -> tuple[int, str]:
    path = data_dir / f"{symbol}_technical.csv"

    if not path.is_file():
        return 0, f"{symbol}: MISSING_FILE: {path}"

    try:
        df = normalize_file(path, symbol)
    except ValueError as exc:
        return 0, f"{symbol}: VALIDATION_ERROR: {exc}"

    first_date = df["trade_date"].iloc[0]
    last_date = df["trade_date"].iloc[-1]
    summary = (
        f"{symbol}: rows={len(df)} first={first_date} last={last_date} "
        f"sha256={sha256_file(path)[:16]}"
    )

    if dry_run:
        return len(df), f"{summary} DRY_RUN"

    try:
        inserted = insert_rows(
            df=df,
            source_file=str(path.resolve()),
            source_sha256=sha256_file(path),
        )
    except Exception as exc:
        return 0, f"{symbol}: DATABASE_ERROR: {exc}"

    return inserted, f"{summary} IMPORTED={inserted}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Importa OHLCV din exporturile legacy TradeVille."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help=f"Director CSV; implicit: {DEFAULT_DATA_DIR}",
    )
    parser.add_argument(
        "--symbols",
        nargs="+",
        help="Simboluri BVB; implicit toate fisierele *_technical.csv.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Valideaza fisierele fara inserare in PostgreSQL.",
    )
    args = parser.parse_args()

    load_dotenv(dotenv_path=".env")

    data_dir = args.data_dir.expanduser().resolve()
    if not data_dir.is_dir():
        print(f"DATA_DIR_ERROR: director inexistent: {data_dir}")
        return 2

    symbols = load_symbols(data_dir, args.symbols)
    if not symbols:
        print(f"NO_SYMBOLS: niciun fisier *_technical.csv in {data_dir}")
        return 2

    print(f"SOURCE: {SOURCE}")
    print(f"DATA_DIR: {data_dir}")
    print(f"MODE: {'DRY_RUN' if args.dry_run else 'IMPORT'}")
    print(f"SYMBOLS: {', '.join(symbols)}")

    total_rows = 0
    errors = 0

    for symbol in symbols:
        rows, message = process_symbol(data_dir, symbol, args.dry_run)
        print(message)
        total_rows += rows

        if "ERROR" in message or "MISSING_FILE" in message:
            errors += 1

    print(
        f"SUMMARY: symbols={len(symbols)} rows={total_rows} "
        f"errors={errors} mode={'DRY_RUN' if args.dry_run else 'IMPORT'}"
    )

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
