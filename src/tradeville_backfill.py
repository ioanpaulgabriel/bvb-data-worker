#!/usr/bin/env python3
"""Incremental TradeVille OHLCV backfill for one symbol."""

import argparse
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from websocket import create_connection

HISTORY_DIR = Path("data/history_tradeville")
RAW_DIR = Path("data/raw/tradeville")
WS_URL = "wss://api.tradeville.ro:443"


def recv_until(ws, wanted_cmd, timeout=30):
    ws.settimeout(timeout)
    while True:
        message = json.loads(ws.recv())
        if message.get("cmd") == wanted_cmd or wanted_cmd in json.dumps(message):
            return message


def fetch(ws, symbol, start, end):
    request = {
        "cmd": "DailyValues",
        "prm": {
            "symbol": symbol,
            "dstart": start,
            "dend": end,
        },
    }
    ws.send(json.dumps(request))
    response = recv_until(ws, "DailyValues")

    raw_path = RAW_DIR / f"{symbol}_{start}_{end}.json"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(
        json.dumps(response, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    data = response.get("data")
    if not data:
        raise RuntimeError(f"Răspuns fără date pentru {symbol}: {response}")

    frame = pd.DataFrame(data)
    frame["Date"] = pd.to_datetime(frame["Date"])
    frame = frame.sort_values("Date").drop_duplicates(subset=["Date"])
    return frame, raw_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--start", required=True, help="Ex: 1feb24")
    parser.add_argument("--end", required=True, help="Ex: 29feb24")
    args = parser.parse_args()

    load_dotenv()

    user = os.getenv("TRADEVILLE_USER")
    password = os.getenv("TRADEVILLE_PASSWORD")
    demo = os.getenv("TRADEVILLE_DEMO", "false").lower() == "true"

    if not user or not password:
        print("Lipsesc TRADEVILLE_USER sau TRADEVILLE_PASSWORD.", file=sys.stderr)
        return 1

    history_path = HISTORY_DIR / f"{args.symbol}_history.csv"

    ws = create_connection(WS_URL, subprotocols=["apitv"], timeout=30)

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

    if not login_response.get("OK"):
        print(f"Login eșuat: {login_response}", file=sys.stderr)
        ws.close()
        return 1

    frame, raw_path = fetch(ws, args.symbol, args.start, args.end)
    ws.close()

    print(f"API: {len(frame)} zile primite pentru {args.symbol}.")
    print(f"Raw salvat: {raw_path}")

    if history_path.exists():
        backup = history_path.with_suffix(
            f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        shutil.copy2(history_path, backup)
        print(f"Backup creat: {backup}")

        local = pd.read_csv(history_path)
        local["Date"] = pd.to_datetime(local["Date"])
        combined = pd.concat([local, frame], ignore_index=True)
        combined = combined.sort_values("Date").drop_duplicates(subset=["Date"])
    else:
        combined = frame

    combined["Date"] = combined["Date"].dt.strftime("%Y-%m-%d")
    combined.to_csv(history_path, index=False)

    print(f"Fișier actualizat: {history_path}")
    print(f"Total zile în istoric: {len(combined)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
