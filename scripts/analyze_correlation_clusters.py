from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
HISTORY_DIR = ROOT / "data" / "history"
OUTPUT_PATH = (
    ROOT / "data" / "walk_forward_risk" / "correlation_clusters_2024.csv"
)

START = "2024-01-01"
END = "2025-01-01"
CORRELATION_THRESHOLD = 0.60
MIN_OBSERVATIONS = 60


def main():
    frames = []

    for path in HISTORY_DIR.glob("*_history.csv"):
        frame = pd.read_csv(path)
        frame.columns = [column.strip().lower() for column in frame.columns]

        if not {"date", "symbol", "close"}.issubset(frame.columns):
            continue

        frames.append(frame[["date", "symbol", "close"]])

    if not frames:
        raise FileNotFoundError("Nu există fișiere istoric valide.")

    data = pd.concat(frames, ignore_index=True)
    data["date"] = pd.to_datetime(data["date"])
    data = data[
        (data["date"] >= START) & (data["date"] < END)
    ].drop_duplicates(subset=["symbol", "date"])

    prices = data.pivot(index="date", columns="symbol", values="close")
    prices = prices.dropna(axis=1, thresh=int(len(prices) * 0.8))
    returns = prices.pct_change().dropna(how="all")

    correlation = returns.corr(min_periods=MIN_OBSERVATIONS)
    symbols = list(correlation.columns)

    visited = set()
    clusters = []

    for symbol in symbols:
        if symbol in visited:
            continue

        cluster = set(
            correlation.index[
                correlation.loc[symbol] >= CORRELATION_THRESHOLD
            ]
        )

        changed = True
        while changed:
            changed = False
            for member in list(cluster):
                connected = set(
                    correlation.index[
                        correlation.loc[member] >= CORRELATION_THRESHOLD
                    ]
                )
                if not cluster.issuperset(connected):
                    cluster.update(connected)
                    changed = True

        visited.update(cluster)

        if len(cluster) < 2:
            continue

        values = correlation.loc[sorted(cluster), sorted(cluster)]
        mask = pd.DataFrame(
            False, index=values.index, columns=values.columns
        )

        for i, row_symbol in enumerate(values.index):
            for j, column_symbol in enumerate(values.columns):
                if j > i:
                    mask.iloc[i, j] = True

        pair_values = values[mask].dropna()
        average_correlation = (
            float(pair_values.mean()) if len(pair_values) else 0.0
        )

        clusters.append(
            {
                "cluster_id": len(clusters) + 1,
                "symbols": ", ".join(sorted(cluster)),
                "size": len(cluster),
                "average_correlation": average_correlation,
            }
        )

    clusters.sort(
        key=lambda item: item["average_correlation"], reverse=True
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(clusters).to_csv(OUTPUT_PATH, index=False)

    print(f"Perioadă: {START} -> {END}")
    print(f"Simboluri analizate: {len(symbols)}")
    print(f"Prag corelație: {CORRELATION_THRESHOLD}")
    print(f"Clustere găsite: {len(clusters)}")

    for cluster in clusters:
        print(
            f"\nCluster {cluster['cluster_id']} "
            f"({cluster['size']} simboluri, "
            f"corelație medie={cluster['average_correlation']:.2f}):"
        )
        print(cluster["symbols"])

    print(f"\nRaport salvat în: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
