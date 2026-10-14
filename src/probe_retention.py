#!/usr/bin/env python3
"""Probe read-only pentru disponibilitatea istoricului OHLCV BVB."""

from __future__ import annotations

from io import StringIO

import pandas as pd
import requests


TARGET_DATES = [
    ("20261008", "Zi recenta, deja validata"),
    ("20260708", "Aproximativ 3 luni in urma"),
    ("20260408", "Aproximativ 6 luni in urma"),
    ("20260108", "Aproximativ 9 luni in urma"),
]

URL_TEMPLATE = (
    "https://m.bvb.ro/TradingAndStatistics/Trading/"
    "HistoricalTradingInfo.ashx?day={date}"
)

HEADERS = {"User-Agent": "HomelabBVBWorker/1.0"}


def classify_payload(content: str) -> tuple[str, int | None, int | None]:
    if not content:
        return "NO_DATA", None, None

    try:
        df = pd.read_csv(StringIO(content))
    except Exception:
        return "NOT_VALID_CSV", None, None

    df.columns = [str(column).strip() for column in df.columns]

    required = {"Symbol", "Market", "Open", "Low", "High", "Close"}
    missing = sorted(required - set(df.columns))
    if missing:
        return f"CSV_MISSING_COLUMNS: {', '.join(missing)}", len(df), None

    regs_rows = int(
        (df["Market"].fillna("").astype(str).str.strip() == "REGS").sum()
    )
    if regs_rows == 0:
        return "CSV_NO_REGS", len(df), 0

    return "AVAILABLE", len(df), regs_rows


def probe_dates() -> None:
    print("[PROBE] Read-only: nu se scriu fisiere si nu se atinge PostgreSQL.")

    for date_param, description in TARGET_DATES:
        url = URL_TEMPLATE.format(date=date_param)
        print(f"\n[?] {date_param} — {description}")

        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
        except requests.RequestException as exc:
            print(f"    STATUS: HTTP_ERROR: {exc}")
            continue

        content = response.text.strip()
        print(f"    HTTP: {response.status_code}")
        print(f"    Payload: {len(content)} caractere")

        if response.status_code != 200:
            print("    STATUS: HTTP_ERROR")
            continue

        status, total_rows, regs_rows = classify_payload(content)
        print(f"    STATUS: {status}")

        if total_rows is not None:
            print(f"    RAW_ROWS: {total_rows}")

        if regs_rows is not None:
            print(f"    REGS_ROWS: {regs_rows}")


if __name__ == "__main__":
    probe_dates()
