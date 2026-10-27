import json
import os
from pathlib import Path

from websocket import create_connection

URL = "wss://api.TradeVille.ro:443"
SUBPROTOCOLS = ["apitv"]

FORMATS = [
    ("1ian20", "31ian20"),
    ("01ian20", "31ian20"),
    ("1ian2020", "31ian2020"),
    ("01.01.2020", "31.01.2020"),
    ("2020-01-01", "2020-01-31"),
    ("1Jan20", "31Jan20"),
    ("01/01/2020", "31/01/2020"),
]


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
    print("LOGIN:", ws.recv())

    output_dir = Path("data/tradeville_probe/date_formats")
    output_dir.mkdir(parents=True, exist_ok=True)

    for start, end in FORMATS:
        message = json.dumps(
            {
                "cmd": "DailyValues",
                "prm": {
                    "symbol": "BRD",
                    "dstart": start,
                    "dend": end,
                },
            }
        )

        ws.send(message)
        response = ws.recv()

        print(f"\n### FORMAT {start} -> {end}")
        print(response[:1000])

        safe_start = start.replace("/", "-").replace(".", "-")
        safe_end = end.replace("/", "-").replace(".", "-")
        path = output_dir / f"BRD_{safe_start}_{safe_end}.json"
        path.write_text(response)

    ws.close()


if __name__ == "__main__":
    main()
