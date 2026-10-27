import json
import os
from pathlib import Path

import pandas as pd
from websocket import create_connection

URL = "wss://api.TradeVille.ro:443"
SUBPROTOCOLS = ["apitv"]

SYMBOL = os.environ.get("TV_SYMBOL", "BRD")
START = os.environ.get("TV_START", "2019-01-01")
END = os.environ.get("TV_END", "2026-12-31")
OUTPUT_DIR = Path(
    os.environ.get(
        "TV_OUTPUT_DIR",
        "data/history_tradeville",
    )
)


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

    if login.get("OK") != 1:
        raise SystemExit(f"Login eșuat: {login}")

    print("Login reușit.")

    ws.send(
        json.dumps(
            {
                "cmd": "DailyValues",
                "prm": {
                    "symbol": SYMBOL,
                    "dstart": START,
                    "dend": END,
                },
            }
        )
    )
    response = json.loads(ws.recv())

    data = response.get("data")
    if not data:
        raise SystemExit(f"Nu există date: {response}")

    frame = pd.DataFrame(data)
    frame = frame.rename(
        columns={
            "Date": "Date",
            "Open": "Open",
            "High": "High",
            "Low": "Low",
            "Close": "Close",
            "Volume": "Volume",
        }
    )

    frame["Date"] = pd.to_datetime(frame["Date"])
    frame = frame.sort_values("Date")
    frame = frame.drop_duplicates(subset=["Date"])

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{SYMBOL}_history.csv"
    frame.to_csv(output_path, index=False)

    print(
        f"{SYMBOL}: {len(frame)} rânduri, "
        f"{frame['Date'].min().date()} -> {frame['Date'].max().date()}"
    )
    print(f"Salvat: {output_path}")

    ws.close()


if __name__ == "__main__":
    main()
