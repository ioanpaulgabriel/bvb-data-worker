import json
import os
from pathlib import Path

import pandas as pd
from websocket import create_connection

URL = "wss://api.TradeVille.ro:443"
SUBPROTOCOLS = ["apitv"]

SYMBOL = "BRD"
REQUESTS = [
    ("2019", "2019-01-01", "2019-12-31"),
    ("2021_2022", "2021-01-01", "2022-12-31"),
]


def fetch_daily_values(ws, symbol, start, end):
    ws.send(
        json.dumps(
            {
                "cmd": "DailyValues",
                "prm": {
                    "symbol": symbol,
                    "dstart": start,
                    "dend": end,
                },
            }
        )
    )
    response = json.loads(ws.recv())
    return response


def main():
    user = os.environ.get("TRADEVILLE_USER")
    password = os.environ.get("TRADEVILLE_PASSWORD")

    if not user or not password:
        raise SystemExit(
            "Setează TRADEVILLE_USER și TRADEVILLE_PASSWORD în mediu."
        )

    ws = create_connection(URL, subprotocols=SUBPROTOCOLS)

    ws.send(
        json.dumps(
            {
                "cmd": "login",
                "prm": {
                    "coduser": user,
                    "parola": password,
                    "demo": False,
                },
            }
        )
    )
    login = json.loads(ws.recv())
    print("LOGIN OK:", login.get("OK") == 1)

    output_dir = Path("data/tradeville_probe")
    output_dir.mkdir(parents=True, exist_ok=True)

    for label, start, end in REQUESTS:
        response = fetch_daily_values(ws, SYMBOL, start, end)

        path = output_dir / f"{SYMBOL}_{label}.json"
        path.write_text(json.dumps(response, indent=2))

        data = response.get("data")
        if not data:
            print(f"\n{label}: fără date. Răspuns: {response}")
            continue

        frame = pd.DataFrame(data)
        csv_path = output_dir / f"{SYMBOL}_{label}.csv"
        frame.to_csv(csv_path, index=False)

        print(
            f"\n{label}: {len(frame)} rânduri, "
            f"de la {frame['Date'].min()} până la {frame['Date'].max()}"
        )
        print(f"Salvat: {csv_path}")

        if label == "2021_2022":
            local_path = (
                Path("data/history") / f"{SYMBOL}_history.csv"
            )
            local = pd.read_csv(local_path)
            local.columns = [
                column.strip().lower() for column in local.columns
            ]
            local["date"] = pd.to_datetime(local["date"])

            remote = frame.copy()
            remote["Date"] = pd.to_datetime(remote["Date"])
            remote = remote.rename(
                columns={
                    "Date": "date",
                    "Open": "open",
                    "High": "high",
                    "Low": "low",
                    "Close": "close",
                    "Volume": "volume",
                }
            )

            merged = local.merge(
                remote[["date", "open", "high", "low", "close", "volume"]],
                on="date",
                how="inner",
                suffixes=("_local", "_remote"),
            )

            print(f"\nZile comune 2021-2022: {len(merged)}")

            for column in ["open", "high", "low", "close", "volume"]:
                difference = (
                    merged[f"{column}_local"]
                    - merged[f"{column}_remote"]
                ).abs()
                print(
                    f"{column}: max diff={difference.max():.6f}, "
                    f"mean diff={difference.mean():.6f}"
                )

            print(
                "\nPrimele 10 comparații Close:"
            )
            print(
                merged[
                    ["date", "close_local", "close_remote"]
                ].head(10).to_string(index=False)
            )

    ws.close()


if __name__ == "__main__":
    main()
