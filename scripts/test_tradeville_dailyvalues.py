import json
import os
import sys
from pathlib import Path

from websocket import create_connection

URL = "wss://api.TradeVille.ro:443"
SUBPROTOCOLS = ["apitv"]

SYMBOL = os.environ.get("TV_SYMBOL", "BRD")
START = os.environ.get("TV_START", "1ian20")
END = os.environ.get("TV_END", "31ian20")


def main():
    user = os.environ.get("TRADEVILLE_USER")
    password = os.environ.get("TRADEVILLE_PASSWORD")

    if not user or not password:
        raise SystemExit(
            "Setează TRADEVILLE_USER și TRADEVILLE_PASSWORD în mediu."
        )

    ws = create_connection(URL, subprotocols=SUBPROTOCOLS)

    login_message = json.dumps(
        {
            "cmd": "login",
            "prm": {
                "coduser": user,
                "parola": password,
                "demo": False,
            },
        }
    )

    ws.send(login_message)
    login_response = ws.recv()
    print("LOGIN RESPONSE:")
    print(login_response)

    daily_message = json.dumps(
        {
            "cmd": "DailyValues",
            "prm": {
                "symbol": SYMBOL,
                "dstart": START,
                "dend": END,
            },
        }
    )

    ws.send(daily_message)
    daily_response = ws.recv()
    print("\nDAILY VALUES RESPONSE:")
    print(daily_response)

    output_dir = Path("data/tradeville_probe")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"{SYMBOL}_{START}_{END}.json"
    output_path.write_text(daily_response)

    print(f"\nRăspuns salvat în: {output_path}")

    ws.close()


if __name__ == "__main__":
    main()
