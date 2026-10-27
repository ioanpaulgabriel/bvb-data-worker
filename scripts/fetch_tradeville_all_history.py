import json
import os
import time
from pathlib import Path

import pandas as pd
from websocket import create_connection

URL = "wss://api.TradeVille.ro:443"
SUBPROTOCOLS = ["apitv"]

LOCAL_HISTORY_DIR = Path("data/history")
OUTPUT_DIR = Path("data/history_tradeville")

START = os.environ.get("TV_START", "2019-01-01")
END = os.environ.get("TV_END", "2026-12-31")
DELAY_SECONDS = float(os.environ.get("TV_DELAY_SECONDS", "1.0"))


def load_symbols():
    symbols = []

    for path in sorted(LOCAL_HISTORY_DIR.glob("*_history.csv")):
        frame = pd.read_csv(path, usecols=["Symbol"])
        symbol = str(frame["Symbol"].iloc[0]).strip()
        symbols.append(symbol)

    return sorted(set(symbols))


def main():
    user = os.environ.get("TRADEVILLE_USER")
    password = os.environ.get("TRADEVILLE_PASSWORD")

    if not user or not password:
        raise SystemExit(
            "Setează TRADEVILLE_USER și TRADEVILLE_PASSWORD în mediu."
        )

    symbols = load_symbols()
    print(f"Simboluri de preluat: {len(symbols)}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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

    results = []

    for index, symbol in enumerate(symbols, start=1):
        output_path = OUTPUT_DIR / f"{symbol}_history.csv"

        if output_path.exists():
            print(f"[{index}/{len(symbols)}] {symbol}: există deja, skip")
            continue

        print(f"[{index}/{len(symbols)}] {symbol}: preluare...")

        ws.send(
            json.dumps(
                {
                    "cmd": "DailyValues",
                    "prm": {
                        "symbol": symbol,
                        "dstart": START,
                        "dend": END,
                    },
                }
            )
        )

        try:
            response = json.loads(ws.recv())
        except Exception as error:
            print(f"EROARE {symbol}: {error}")
            results.append(
                {"symbol": symbol, "status": "ERROR", "rows": 0}
            )
            continue

        data = response.get("data")

        if not data:
            print(f"FĂRĂ DATE {symbol}: {response.get('err', response)}")
            results.append(
                {"symbol": symbol, "status": "NO_DATA", "rows": 0}
            )
            time.sleep(DELAY_SECONDS)
            continue

        frame = pd.DataFrame(data)
        frame["Date"] = pd.to_datetime(frame["Date"])
        frame = frame.sort_values("Date")
        frame = frame.drop_duplicates(subset=["Date"])
        frame.to_csv(output_path, index=False)

        print(
            f"OK {symbol}: {len(frame)} rânduri, "
            f"{frame['Date'].min().date()} -> {frame['Date'].max().date()}"
        )

        results.append(
            {
                "symbol": symbol,
                "status": "OK",
                "rows": len(frame),
            }
        )

        time.sleep(DELAY_SECONDS)

    ws.close()

    report = pd.DataFrame(results)
    report.to_csv(OUTPUT_DIR / "fetch_report.csv", index=False)

    print("\n### REZUMAT")
    print(report["status"].value_counts().to_string())
    print(f"\nRaport salvat: {OUTPUT_DIR / 'fetch_report.csv'}")


if __name__ == "__main__":
    main()
