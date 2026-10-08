from pathlib import Path
from datetime import datetime
from io import StringIO
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fetch_bvb import persist_raw_to_postgres


RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


def ingest_raw_file_to_postgres(raw_path: Path) -> None:
    content = raw_path.read_text(encoding="utf-8").strip()

    if not content:
        raise ValueError(f"Fișier WAL gol: {raw_path}")

    df_raw = pd.read_csv(StringIO(content))
    df_raw.columns = [str(column).strip() for column in df_raw.columns]

    date_part = raw_path.name.removesuffix("_bvb.csv")
    trade_date = datetime.strptime(date_part, "%Y-%m-%d").date()

    persist_raw_to_postgres(
        trade_date=trade_date.isoformat(),
        content=content,
        http_status=200,
        row_count=len(df_raw),
    )


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
