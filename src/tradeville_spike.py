#!/usr/bin/env python3
"""TradeVille read-only connection spike."""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from websocket import create_connection

RAW_DIR = Path("data/raw/tradeville")
WS_URL = "wss://api.tradeville.ro:443"


def recv_until(ws, wanted_cmd, timeout=15):
    ws.settimeout(timeout)
    while True:
        message = json.loads(ws.recv())
        serialized = json.dumps(message)
        if message.get("cmd") == wanted_cmd or wanted_cmd in serialized:
            return message


def mask(obj):
    if isinstance(obj, dict):
        masked = {}
        for key, value in obj.items():
            sensitive = any(
                word in key.lower()
                for word in ("pass", "user", "token", "session")
            )
            masked[key] = "***" if sensitive else mask(value)
        return masked
    if isinstance(obj, list):
        return [mask(item) for item in obj]
    return obj


def main():
    load_dotenv()

    user = os.getenv("TRADEVILLE_USER")
    password = os.getenv("TRADEVILLE_PASSWORD")
    demo = os.getenv("TRADEVILLE_DEMO", "true").lower() == "true"

    if not user or not password:
        print(
            "Lipsesc TRADEVILLE_USER sau TRADEVILLE_PASSWORD din .env",
            file=sys.stderr,
        )
        return 1

    ws = create_connection(WS_URL, subprotocols=["apitv"], timeout=15)

    login = {
        "cmd": "login",
        "prm": {
            "coduser": user,
            "parola": password,
            "demo": demo,
        },
    }

    ws.send(json.dumps(login))
    login_response = recv_until(ws, "login")

    print("Chei răspuns login:", list(login_response.keys()))
    print(
        "Răspuns login mascat:",
        json.dumps(mask(login_response), indent=2)[:2000],
    )

    requests = {
        "daily_values": {
            "cmd": "DailyValues",
            "prm": {
                "symbol": "BRD",
                "dstart": "1jan24",
                "dend": "31jan24",
            },
        },
        "portfolio": {
            "cmd": "Portfolio",
            "prm": {"data": "null"},
        },
    }

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    for name, request in requests.items():
        ws.send(json.dumps(request))
        response = recv_until(ws, request["cmd"])

        path = RAW_DIR / f"spike_{name}.json"
        path.write_text(
            json.dumps(response, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        print(f"Salvat: {path}")
        print(f"Chei răspuns {name}: {list(response.keys())}")

    ws.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
