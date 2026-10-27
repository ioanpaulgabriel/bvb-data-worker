import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = ROOT / "data" / "walk_forward_results.csv"
ROBUST_PATH = ROOT / "data" / "walk_forward" / "walk_forward_summary.csv"
REPORT_PATH = ROOT / "data" / "walk_forward_comparison.csv"


def compounded_return(rows, return_column):
    product = 1.0
    for value in rows[return_column]:
        product *= 1.0 + float(value)
    return product - 1.0


def main():
    baseline = pd.read_csv(BASELINE_PATH)
    robust = pd.read_csv(ROBUST_PATH)

    baseline_return = compounded_return(baseline, "total_return")
    robust_return = compounded_return(robust, "test_total_return")

    report = []

    for fold_id in sorted(baseline["fold"].unique()):
        base_row = baseline[baseline["fold"] == fold_id].iloc[0]
        robust_row = robust[robust["fold_id"] == fold_id].iloc[0]

        report.append(
            {
                "fold_id": fold_id,
                "test_start": base_row["test_start"],
                "test_end": base_row["test_end"],
                "baseline_return": base_row["total_return"],
                "robust_return": robust_row["test_total_return"],
                "improvement": robust_row["test_total_return"]
                - base_row["total_return"],
                "robust_holding_days": robust_row["holding_days"],
                "robust_min_volume_ratio": robust_row["min_volume_ratio"],
                "robust_test_trades": robust_row["test_trades"],
            }
        )

    report_df = pd.DataFrame(report)
    report_df.to_csv(REPORT_PATH, index=False)

    print("### COMPARAȚIE WALK-FORWARD")
    print(report_df.to_string(index=False))

    print("\n### REZULTAT COMPUS")
    print(f"Baseline: {baseline_return:.2%}")
    print(f"Robust:   {robust_return:.2%}")
    print(f"Diferență: {robust_return - baseline_return:.2%}")

    print(f"\nRaport salvat în: {REPORT_PATH}")


if __name__ == "__main__":
    main()
