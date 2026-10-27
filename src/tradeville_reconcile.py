#!/usr/bin/env python3
"""Daily TradeVille portfolio reconciliation."""

import json
import os
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
from dotenv import load_dotenv
import psycopg
from websocket import create_connection

BVB_INFO_PATH = Path('/home/bvb/bvb-info')
load_dotenv(BVB_INFO_PATH / '.env')
sys.path.insert(0, str(BVB_INFO_PATH))

from bvb_scraper.mqtt_client import publish_json

RAW_DIR = Path("data/raw/tradeville")
WS_URL = "wss://api.tradeville.ro:443"


def recv_until(ws, wanted_cmd, timeout=30):
    ws.settimeout(timeout)
    while True:
        message = json.loads(ws.recv())
        if message.get("cmd") == wanted_cmd or wanted_cmd in json.dumps(message):
            return message


def fetch_portfolio(ws):
    ws.send(json.dumps({"cmd": "Portfolio", "prm": {"data": "null"}}))
    response = recv_until(ws, "Portfolio")

    today = date.today().isoformat()
    raw_path = RAW_DIR / f"portfolio_{today}.json"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(
        json.dumps(response, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return response, raw_path


def main():
    load_dotenv()

    tv_user = os.getenv("TRADEVILLE_USER")
    tv_password = os.getenv("TRADEVILLE_PASSWORD")
    tv_demo = os.getenv("TRADEVILLE_DEMO", "false").lower() == "true"

    db_url = os.getenv("BVB_DATABASE_URL")
    if not db_url:
        load_dotenv("/home/bvb/bvb-info/.env")
        db_url = os.getenv("BVB_DATABASE_URL")

    if not tv_user or not tv_password or not db_url:
        print("Lipsesc credențialele TradeVille sau BVB_DATABASE_URL.", file=sys.stderr)
        return 1

    db_url = db_url.replace("postgresql+psycopg2://", "postgresql://")
    parsed = urlparse(db_url)

    ws = create_connection(WS_URL, subprotocols=["apitv"], timeout=30)

    ws.send(
        json.dumps(
            {
                "cmd": "login",
                "prm": {
                    "coduser": tv_user,
                    "parola": tv_password,
                    "demo": tv_demo,
                },
            }
        )
    )
    login_response = recv_until(ws, "login")

    if not login_response.get("OK"):
        print(f"Login TradeVille eșuat: {login_response}", file=sys.stderr)
        ws.close()
        return 1

    portfolio_response, raw_path = fetch_portfolio(ws)
    ws.close()

    portfolio = pd.DataFrame(portfolio_response["data"]).to_dict("records")
    reconciliation_date = date.today()

    conn = psycopg.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        user=parsed.username,
        password=parsed.password,
        dbname=parsed.path.lstrip("/"),
        connect_timeout=5,
    )

    with conn.cursor() as cur:
        for position in portfolio:
            cur.execute(
                """
                INSERT INTO paper.reconciliation (
                    reconciliation_date,
                    symbol,
                    source,
                    quantity,
                    avg_price,
                    market_price
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (reconciliation_date, symbol, source)
                DO UPDATE SET
                    quantity = EXCLUDED.quantity,
                    avg_price = EXCLUDED.avg_price,
                    market_price = EXCLUDED.market_price,
                    created_at = now()
                """,
                (
                    reconciliation_date,
                    position["Symbol"],
                    f"tradeville_{position['PType']}",
                    position["Quantity"],
                    position["AvgPrice"],
                    position["MarketPrice"],
                ),
            )

        cur.execute(
            """
            SELECT symbol, quantity, avg_price, market_price
            FROM paper.reconciliation
            WHERE reconciliation_date = %s
              AND source = 'tradeville_A'
            ORDER BY symbol
            """,
            (reconciliation_date,),
        )
        real_rows = cur.fetchall()

        cur.execute(
            """
            SELECT symbol, quantity, entry_price
            FROM paper.positions
            WHERE status = 'open'
            ORDER BY symbol
            """
        )
        paper_rows = cur.fetchall()

    conn.close()

    real = pd.DataFrame(
        real_rows,
        columns=["symbol", "real_quantity", "real_avg_price", "market_price"],
    )
    paper = pd.DataFrame(
        paper_rows,
        columns=["symbol", "paper_quantity", "paper_entry_price"],
    )

    report = real.merge(
        paper,
        on="symbol",
        how="outer",
        suffixes=("", "_paper"),
    )

    report["real_quantity"] = report["real_quantity"].fillna(0)
    report["paper_quantity"] = report["paper_quantity"].fillna(0)
    report["quantity_diff"] = (
        report["paper_quantity"] - report["real_quantity"]
    )

    differences = report[report["quantity_diff"] != 0]

    print(f"### RECONCILIERE {reconciliation_date}")
    print(f"Raw salvat: {raw_path}")
    print(f"Poziții reale: {len(real)}")
    print(f"Poziții paper: {len(paper)}")
    print(f"Poziții cu diferențe: {len(differences)}")

    if not differences.empty:
        print("\n### DIFERENȚE")
        print(
            differences[
                [
                    "symbol",
                    "real_quantity",
                    "paper_quantity",
                    "quantity_diff",
                ]
            ].to_string(index=False)
        )

    reconciliation_payload = {
        "date": reconciliation_date.isoformat(),
        "real_positions": len(real),
        "paper_positions": len(paper),
        "differences": len(differences),
        "status": "ok" if differences.empty else "mismatch",
        "symbols_with_differences": differences["symbol"].tolist(),
    }

    publish_json("portfolio/reconciliation", reconciliation_payload)

    return 0


if __name__ == "__main__":
    sys.exit(main())
