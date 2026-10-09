#!/usr/bin/env python3
"""Backfill istoric BVB, zi cu zi, prin workerul validat fetch_bvb.py."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FETCH_SCRIPT = PROJECT_ROOT / "src" / "fetch_bvb.py"


def parse_date(value: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y%m%d")
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Data invalida: {value!r}. Foloseste formatul YYYYMMDD."
        ) from exc


def classify_result(returncode: int, output: str) -> str:
    if returncode == 0 and "STATUS: SUCCESS" in output:
        return "SUCCESS"

    if returncode == 0 and "STATUS: NO_DATA" in output:
        return "NO_DATA"

    return "ERROR"


def run_backfill(start_date: datetime, end_date: datetime, delay: float) -> int:
    if start_date > end_date:
        print("Eroare: --start-date trebuie sa fie <= --end-date.")
        return 2

    if delay < 0:
        print("Eroare: --delay trebuie sa fie zero sau pozitiv.")
        return 2

    if not FETCH_SCRIPT.is_file():
        print(f"Eroare: workerul nu exista: {FETCH_SCRIPT}")
        return 2

    total_days = (end_date - start_date).days + 1
    stats = {"SUCCESS": 0, "NO_DATA": 0, "ERROR": 0}

    print(
        "[BACKFILL] Interval: "
        f"{start_date:%Y-%m-%d} -> {end_date:%Y-%m-%d} "
        f"({total_days} zile calendaristice)"
    )
    print(f"[BACKFILL] Interpreter: {sys.executable}")
    print(f"[BACKFILL] Worker: {FETCH_SCRIPT}")
    print(f"[BACKFILL] Pauza intre cereri: {delay:.2f}s")

    current_date = start_date

    while current_date <= end_date:
        day_param = current_date.strftime("%Y%m%d")
        print(f"\n[+] Procesez {current_date:%Y-%m-%d} ({day_param})")

        try:
            result = subprocess.run(
                [sys.executable, str(FETCH_SCRIPT), day_param],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            output = (result.stdout or "") + (result.stderr or "")
            status = classify_result(result.returncode, output)

            stats[status] += 1
            print(f"    STATUS: {status}; exit_code={result.returncode}")

            if status == "ERROR":
                print("    Ultimele loguri ale workerului:")
                print(output[-1200:].rstrip() or "    (fara output)")

        except OSError as exc:
            stats["ERROR"] += 1
            print(f"    STATUS: ERROR; nu pot porni workerul: {exc}")

        current_date += timedelta(days=1)

        if current_date <= end_date and delay > 0:
            time.sleep(delay)

    print("\n" + "=" * 52)
    print("RAPORT FINAL BACKFILL")
    print(f"SUCCESS : {stats['SUCCESS']}")
    print(f"NO_DATA : {stats['NO_DATA']}")
    print(f"ERROR   : {stats['ERROR']}")
    print(f"TOTAL   : {sum(stats.values())}")
    print("=" * 52)

    return 0 if stats["ERROR"] == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Recupereaza istoric BVB prin src/fetch_bvb.py."
    )
    parser.add_argument(
        "--start-date",
        required=True,
        type=parse_date,
        help="Data de inceput in format YYYYMMDD.",
    )
    parser.add_argument(
        "--end-date",
        required=True,
        type=parse_date,
        help="Data de sfarsit in format YYYYMMDD.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Pauza in secunde intre zile; implicit 1.0.",
    )
    args = parser.parse_args()

    return run_backfill(args.start_date, args.end_date, args.delay)


if __name__ == "__main__":
    raise SystemExit(main())
