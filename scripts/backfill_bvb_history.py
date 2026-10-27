import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

from fetch_bvb import fetch_and_validate_bvb


def main():
    days = 60
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    current_date = start_date

    while current_date <= end_date:
        if current_date.weekday() < 5:
            date_str = current_date.strftime("%Y%m%d")
            status = fetch_and_validate_bvb(date_str)
            print(f"{current_date.isoformat()}: {status}")

        current_date += timedelta(days=1)


if __name__ == "__main__":
    main()
