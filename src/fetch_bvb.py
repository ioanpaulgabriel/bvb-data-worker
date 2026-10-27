import json
import os
from datetime import datetime, timezone
from io import StringIO

import pandas as pd
import psycopg
import requests
from dotenv import load_dotenv


RAW_DIR = "data/raw"
CLEAN_DIR = "data/clean"

os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(CLEAN_DIR, exist_ok=True)


load_dotenv(dotenv_path=".env")


def persist_raw_to_postgres(
    trade_date: str,
    content: str,
    http_status: int,
    row_count: int,
) -> None:
    database_url = os.getenv("BVB_DATABASE_URL")
    if not database_url:
        raise RuntimeError("BVB_DATABASE_URL nu este configurat")

    payload = {
        "format": "csv",
        "content": content,
    }

    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO prices_daily_raw (
                    trade_date,
                    source,
                    http_status,
                    row_count,
                    payload
                )
                VALUES (%s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (trade_date, source)
                DO UPDATE SET
                    fetched_at = now(),
                    http_status = EXCLUDED.http_status,
                    row_count = EXCLUDED.row_count,
                    payload = EXCLUDED.payload
                """,
                (
                    trade_date,
                    "bvb_public_csv",
                    http_status,
                    row_count,
                    json.dumps(payload),
                ),
            )

def persist_clean_prices_to_postgres(df_clean: pd.DataFrame) -> int:
    database_url = os.getenv("BVB_DATABASE_URL")
    if not database_url:
        raise RuntimeError("BVB_DATABASE_URL nu este configurat")

    rows = [
        (
            row["date"],
            row["symbol"],
            row["name"],
            row["market"],
            row["trades"],
            row["volume"],
            row["value"],
            row["open"],
            row["low"],
            row["high"],
            row["avg_price"],
            row["close"],
            row["ref_price"],
            row["change_pct"],
            row["source"],
            row["ingested_at"],
        )
        for _, row in df_clean.iterrows()
    ]

    query = """
        INSERT INTO prices_daily (
            trade_date, symbol, name, market, trades, volume,
            value, open, low, high, avg_price, close,
            ref_price, change_pct, source, ingested_at
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (trade_date, symbol, source)
        DO UPDATE SET
            name = EXCLUDED.name,
            market = EXCLUDED.market,
            trades = EXCLUDED.trades,
            volume = EXCLUDED.volume,
            value = EXCLUDED.value,
            open = EXCLUDED.open,
            low = EXCLUDED.low,
            high = EXCLUDED.high,
            avg_price = EXCLUDED.avg_price,
            close = EXCLUDED.close,
            ref_price = EXCLUDED.ref_price,
            change_pct = EXCLUDED.change_pct,
            ingested_at = EXCLUDED.ingested_at
    """

    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.executemany(query, rows)

    return len(rows)


REQUIRED_RAW_COLUMNS = [
    "Symbol",
    "Name",
    "Market",
    "Trades",
    "Volume",
    "Value",
    "Open",
    "Low",
    "High",
    "Avg.",
    "Close",
    "Ref. price",
    "Var (%)",
]


def fetch_and_validate_bvb(date_str: str) -> str:
    try:
        parsed_date = datetime.strptime(date_str, "%Y%m%d")
        formatted_date = parsed_date.strftime("%Y-%m-%d")
    except ValueError:
        print(f"[{date_str}] VALIDATION_ERROR: formatul trebuie să fie YYYYMMDD")
        return "VALIDATION_ERROR"

    url = (
        "https://m.bvb.ro/TradingAndStatistics/Trading/"
        f"HistoricalTradingInfo.ashx?day={date_str}"
    )

    raw_path = os.path.join(RAW_DIR, f"{formatted_date}_bvb.csv")
    clean_path = os.path.join(CLEAN_DIR, f"{formatted_date}_regs.csv")

    try:
        response = requests.get(
            url,
            headers={"User-Agent": "HomelabBVBWorker/1.0"},
            timeout=30,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"[{date_str}] HTTP_ERROR: {exc}")
        return "HTTP_ERROR"

    content = response.text.strip()

    if not content:
        print(f"[{date_str}] NO_DATA: răspuns gol")
        return "NO_DATA"

    with open(raw_path, "w", encoding="utf-8") as file:
        file.write(content + "\n")

    try:
        df_raw = pd.read_csv(StringIO(content))
    except Exception as exc:
        print(f"[{date_str}] PARSE_ERROR: {exc}")
        return "PARSE_ERROR"

    df_raw.columns = [str(column).strip() for column in df_raw.columns]

    try:
        persist_raw_to_postgres(
            trade_date=formatted_date,
            content=content,
            http_status=response.status_code,
            row_count=len(df_raw),
        )
    except Exception as exc:
        print(f"[{date_str}] DATABASE_ERROR: {exc}")
        return "DATABASE_ERROR"

    missing = [
        column for column in REQUIRED_RAW_COLUMNS
        if column not in df_raw.columns
    ]

    if missing:
        print(f"[{date_str}] VALIDATION_ERROR: lipsesc {missing}")
        return "VALIDATION_ERROR"

    df_raw["Symbol"] = df_raw["Symbol"].fillna("").astype(str).str.strip()
    df_raw["Market"] = df_raw["Market"].fillna("").astype(str).str.strip()

    df_regs = df_raw[df_raw["Market"] == "REGS"].copy()

    if df_regs.empty:
        print(f"[{date_str}] VALIDATION_ERROR: nu există rânduri REGS")
        return "VALIDATION_ERROR"

    try:
        integer_columns = ["Trades", "Volume"]
        numeric_columns = [
            "Value",
            "Open",
            "Low",
            "High",
            "Avg.",
            "Close",
            "Ref. price",
            "Var (%)",
        ]

        for column in integer_columns:
            df_regs[column] = pd.to_numeric(
                df_regs[column],
                errors="raise",
            ).astype("int64")

        for column in numeric_columns:
            df_regs[column] = pd.to_numeric(
                df_regs[column],
                errors="raise",
            )

    except Exception as exc:
        print(f"[{date_str}] VALIDATION_ERROR: conversie numerică: {exc}")
        return "VALIDATION_ERROR"

    prices = ["Open", "Low", "High", "Close"]

    if (df_regs[prices] <= 0).any().any():
        print(f"[{date_str}] VALIDATION_ERROR: preț <= 0")
        return "VALIDATION_ERROR"

    if (df_regs["Low"] > df_regs["High"]).any():
        print(f"[{date_str}] VALIDATION_ERROR: Low > High")
        return "VALIDATION_ERROR"

    if df_regs.duplicated(subset=["Symbol"]).any():
        print(f"[{date_str}] VALIDATION_ERROR: simbol REGS duplicat")
        return "VALIDATION_ERROR"

    ingested_at = datetime.now(timezone.utc).isoformat()

    df_clean = pd.DataFrame({
        "date": formatted_date,
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
        "ingested_at": ingested_at,
    })

    df_clean.to_csv(clean_path, index=False, encoding="utf-8")

    try:
        db_rows = persist_clean_prices_to_postgres(df_clean)
    except Exception as exc:
        print(f"[{date_str}] DATABASE_ERROR: prices_daily: {exc}")
        return "DATABASE_ERROR"

    print(f"DB_ROWS: {db_rows}")

    targets = {"TLV", "SNP", "SNG", "H2O", "BRD", "TTS"}
    found = sorted(targets.intersection(set(df_clean["symbol"])))

    print(f"DATE: {formatted_date}")
    print("STATUS: SUCCESS")
    print(f"RAW_ROWS: {len(df_raw)}")
    print(f"REGS_ROWS: {len(df_clean)}")
    print(f"FOUND_TARGETS: {found}")
    print(f"RAW_FILE: {raw_path}")
    print(f"CLEAN_FILE: {clean_path}")

    return "SUCCESS"


if __name__ == "__main__":
    import argparse
    import sys
    from datetime import datetime

    parser = argparse.ArgumentParser(
        description="Descarcă și validează datele BVB pentru o zi."
    )
    parser.add_argument(
        "date",
        nargs="?",
        default=datetime.now().strftime("%Y%m%d"),
        help="Data în format YYYYMMDD; implicit: data curentă",
    )
    args = parser.parse_args()

    status = fetch_and_validate_bvb(args.date)
    print(f"STATUS: {status}")

    if status not in {"SUCCESS", "NO_DATA"}:
        sys.exit(1)
