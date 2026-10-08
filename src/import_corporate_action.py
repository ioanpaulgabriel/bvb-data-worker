import argparse
import json
import os
from datetime import date
from decimal import Decimal

import psycopg
from dotenv import load_dotenv


ALLOWED_ACTION_TYPES = {
    "split",
    "reverse_split",
    "bonus_issue",
    "rights_issue",
    "dividend",
    "merger",
    "spin_off",
    "delisting",
    "other",
}

load_dotenv(".env")


def import_corporate_action(
    symbol,
    action_type,
    ex_date,
    source,
    source_reference,
    ratio=None,
    cash_amount=None,
    currency=None,
    raw_payload=None,
):
    symbol = symbol.strip().upper()
    action_type = action_type.strip().lower()
    source = source.strip()
    source_reference = source_reference.strip()

    if not symbol:
        raise ValueError("symbol este obligatoriu")

    if action_type not in ALLOWED_ACTION_TYPES:
        raise ValueError(f"action_type invalid: {action_type}")

    parsed_date = date.fromisoformat(ex_date)

    if not source:
        raise ValueError("source este obligatoriu")

    if not source_reference:
        raise ValueError("source_reference este obligatoriu")

    parsed_ratio = Decimal(ratio) if ratio is not None else None
    parsed_cash = Decimal(cash_amount) if cash_amount is not None else None

    database_url = os.environ["DATABASE_URL"]

    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO corporate_actions (
                    symbol,
                    action_type,
                    ex_date,
                    ratio,
                    cash_amount,
                    currency,
                    source,
                    source_reference,
                    raw_payload,
                    status
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, 'pending'
                )
                ON CONFLICT (
                    symbol,
                    action_type,
                    ex_date,
                    COALESCE(source_reference, '')
                )
                DO UPDATE SET
                    ratio = EXCLUDED.ratio,
                    cash_amount = EXCLUDED.cash_amount,
                    currency = EXCLUDED.currency,
                    source = EXCLUDED.source,
                    raw_payload = EXCLUDED.raw_payload,
                    updated_at = now()
                """,
                (
                    symbol,
                    action_type,
                    parsed_date,
                    parsed_ratio,
                    parsed_cash,
                    currency,
                    source,
                    source_reference,
                    json.dumps(raw_payload or {}),
                ),
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Importa un Corporate Action în PostgreSQL."
    )
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--action-type", required=True)
    parser.add_argument("--ex-date", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--source-reference", required=True)
    parser.add_argument("--ratio")
    parser.add_argument("--cash-amount")
    parser.add_argument("--currency")
    parser.add_argument("--raw-payload", default="{}")

    args = parser.parse_args()

    import_corporate_action(
        symbol=args.symbol,
        action_type=args.action_type,
        ex_date=args.ex_date,
        source=args.source,
        source_reference=args.source_reference,
        ratio=args.ratio,
        cash_amount=args.cash_amount,
        currency=args.currency,
        raw_payload=json.loads(args.raw_payload),
    )

    print("IMPORT_SUCCESS")
