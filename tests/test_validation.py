from pathlib import Path

import pandas as pd
import pytest

import retry_raw


REQUIRED_COLUMNS = [
    "Symbol",
    "Name",
    "Market",
    "Trades",
    "Volume",
    "Value",
    "Open",
    "Low",
    "High",
    "Avg.",
    "Close",
    "Ref. price",
    "Var (%)",
]


def make_csv(rows, columns=REQUIRED_COLUMNS):
    frame = pd.DataFrame(rows, columns=columns)
    return frame.to_csv(index=False)


def valid_row(symbol="TEST"):
    return {
        "Symbol": symbol,
        "Name": "Test company",
        "Market": "REGS",
        "Trades": 10,
        "Volume": 1000,
        "Value": 12345.5,
        "Open": 12.0,
        "Low": 11.5,
        "High": 12.5,
        "Avg.": 12.1,
        "Close": 12.2,
        "Ref. price": 12.0,
        "Var (%)": 1.67,
    }


def test_ingest_raw_file_filters_only_regs_and_persists_clean_rows(
    tmp_path, monkeypatch
):
    raw_path = tmp_path / "2026-10-08_bvb.csv"
    rows = [
        valid_row("REGS1"),
        {**valid_row("OTHER1"), "Market": "DEALS"},
    ]
    raw_path.write_text(make_csv(rows), encoding="utf-8")

    persisted_raw = []
    persisted_clean = []

    monkeypatch.setattr(
        retry_raw,
        "persist_raw_to_postgres",
        lambda **kwargs: persisted_raw.append(kwargs),
    )
    monkeypatch.setattr(
        retry_raw,
        "persist_clean_prices_to_postgres",
        lambda frame: persisted_clean.append(frame.copy()) or len(frame),
    )

    retry_raw.ingest_raw_file_to_postgres(raw_path)

    assert len(persisted_raw) == 1
    assert persisted_raw[0]["trade_date"] == "2026-10-08"
    assert persisted_raw[0]["row_count"] == 2

    assert len(persisted_clean) == 1
    clean = persisted_clean[0]
    assert len(clean) == 1
    assert clean.iloc[0]["symbol"] == "REGS1"
    assert clean.iloc[0]["market"] == "REGS"


def test_ingest_raw_file_rejects_missing_columns(tmp_path):
    raw_path = tmp_path / "2026-10-08_bvb.csv"
    columns = [column for column in REQUIRED_COLUMNS if column != "High"]
    raw_path.write_text(make_csv([valid_row()], columns), encoding="utf-8")

    with pytest.raises(ValueError, match="Coloane lipsa"):
        retry_raw.ingest_raw_file_to_postgres(raw_path)


def test_ingest_raw_file_rejects_empty_file(tmp_path):
    raw_path = tmp_path / "2026-10-08_bvb.csv"
    raw_path.write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="WAL gol"):
        retry_raw.ingest_raw_file_to_postgres(raw_path)


def test_ingest_raw_file_rejects_invalid_numeric_value(tmp_path):
    raw_path = tmp_path / "2026-10-08_bvb.csv"
    row = valid_row()
    row["Low"] = "not-a-number"
    raw_path.write_text(make_csv([row]), encoding="utf-8")

    with pytest.raises(ValueError):
        retry_raw.ingest_raw_file_to_postgres(raw_path)


def test_ingest_raw_file_rejects_file_without_regs(tmp_path):
    raw_path = tmp_path / "2026-10-08_bvb.csv"
    row = {**valid_row(), "Market": "DEALS"}
    raw_path.write_text(make_csv([row]), encoding="utf-8")

    with pytest.raises(ValueError, match="Nu exista randuri REGS"):
        retry_raw.ingest_raw_file_to_postgres(raw_path)


class FakeResponse:
    def __init__(self, text="", status_code=200, error=None):
        self.text = text
        self.status_code = status_code
        self.error = error

    def raise_for_status(self):
        if self.error is not None:
            raise self.error


def test_fetch_rejects_invalid_date():
    import fetch_bvb

    assert fetch_bvb.fetch_and_validate_bvb("2026-10-08") == "VALIDATION_ERROR"


def test_fetch_returns_no_data_for_empty_response(monkeypatch):
    import fetch_bvb

    monkeypatch.setattr(
        fetch_bvb.requests,
        "get",
        lambda *args, **kwargs: FakeResponse(text=""),
    )

    assert fetch_bvb.fetch_and_validate_bvb("20261008") == "NO_DATA"


def test_fetch_returns_http_error(monkeypatch):
    import requests
    import fetch_bvb

    monkeypatch.setattr(
        fetch_bvb.requests,
        "get",
        lambda *args, **kwargs: FakeResponse(
            error=requests.RequestException("network error")
        ),
    )

    assert fetch_bvb.fetch_and_validate_bvb("20261008") == "HTTP_ERROR"


def test_fetch_returns_parse_error(monkeypatch):
    import fetch_bvb

    monkeypatch.setattr(
        fetch_bvb.requests,
        "get",
        lambda *args, **kwargs: FakeResponse(text="some content"),
    )

    def fail_read_csv(*args, **kwargs):
        raise ValueError("invalid csv")

    monkeypatch.setattr(fetch_bvb.pd, "read_csv", fail_read_csv)

    assert fetch_bvb.fetch_and_validate_bvb("20261008") == "PARSE_ERROR"


def test_fetch_returns_database_error(monkeypatch, tmp_path):
    import fetch_bvb

    monkeypatch.setattr(fetch_bvb, "RAW_DIR", str(tmp_path))
    monkeypatch.setattr(fetch_bvb, "CLEAN_DIR", str(tmp_path))
    monkeypatch.setattr(
        fetch_bvb.requests,
        "get",
        lambda *args, **kwargs: FakeResponse(
            text=make_csv([valid_row()])
        ),
    )
    monkeypatch.setattr(
        fetch_bvb,
        "persist_raw_to_postgres",
        lambda **kwargs: (_ for _ in ()).throw(
            RuntimeError("database unavailable")
        ),
    )

    assert fetch_bvb.fetch_and_validate_bvb("20261008") == "DATABASE_ERROR"


def test_fetch_validates_and_persists_valid_csv(monkeypatch, tmp_path):
    import fetch_bvb

    monkeypatch.setattr(fetch_bvb, "RAW_DIR", str(tmp_path))
    monkeypatch.setattr(fetch_bvb, "CLEAN_DIR", str(tmp_path))
    monkeypatch.setattr(
        fetch_bvb.requests,
        "get",
        lambda *args, **kwargs: FakeResponse(
            text=make_csv([valid_row("VALID1")])
        ),
    )

    raw_calls = []
    clean_calls = []

    monkeypatch.setattr(
        fetch_bvb,
        "persist_raw_to_postgres",
        lambda **kwargs: raw_calls.append(kwargs),
    )
    monkeypatch.setattr(
        fetch_bvb,
        "persist_clean_prices_to_postgres",
        lambda frame: clean_calls.append(frame.copy()) or len(frame),
    )

    result = fetch_bvb.fetch_and_validate_bvb("20261008")

    assert result == "SUCCESS"
    assert len(raw_calls) == 1
    assert raw_calls[0]["trade_date"] == "2026-10-08"
    assert raw_calls[0]["row_count"] == 1
    assert len(clean_calls) == 1
    assert clean_calls[0].iloc[0]["symbol"] == "VALID1"

def test_ingest_same_raw_file_twice_is_idempotent(tmp_path, monkeypatch):
    raw_path = tmp_path / "2026-10-08_bvb.csv"
    raw_path.write_text(
        make_csv([valid_row("IDEMP1")]),
        encoding="utf-8",
    )

    persisted_raw = []
    persisted_clean = []

    monkeypatch.setattr(
        retry_raw,
        "persist_raw_to_postgres",
        lambda **kwargs: persisted_raw.append(kwargs),
    )
    monkeypatch.setattr(
        retry_raw,
        "persist_clean_prices_to_postgres",
        lambda frame: persisted_clean.append(frame.copy()) or len(frame),
    )

    retry_raw.ingest_raw_file_to_postgres(raw_path)
    retry_raw.ingest_raw_file_to_postgres(raw_path)

    assert len(persisted_raw) == 2
    assert len(persisted_clean) == 2
    assert len(persisted_clean[0]) == 1
    assert len(persisted_clean[1]) == 1
    assert persisted_clean[0].iloc[0]["symbol"] == "IDEMP1"
    assert persisted_clean[1].iloc[0]["symbol"] == "IDEMP1"

def test_ingest_same_raw_file_twice_is_idempotent(tmp_path, monkeypatch):
    raw_path = tmp_path / "2026-10-08_bvb.csv"
    raw_path.write_text(
        make_csv([valid_row("IDEMP1")]),
        encoding="utf-8",
    )

    persisted_raw = []
    persisted_clean = []

    monkeypatch.setattr(
        retry_raw,
        "persist_raw_to_postgres",
        lambda **kwargs: persisted_raw.append(kwargs),
    )
    monkeypatch.setattr(
        retry_raw,
        "persist_clean_prices_to_postgres",
        lambda frame: persisted_clean.append(frame.copy()) or len(frame),
    )

    retry_raw.ingest_raw_file_to_postgres(raw_path)
    retry_raw.ingest_raw_file_to_postgres(raw_path)

    assert len(persisted_raw) == 2
    assert len(persisted_clean) == 2
    assert len(persisted_clean[0]) == 1
    assert len(persisted_clean[1]) == 1
    assert persisted_clean[0].iloc[0]["symbol"] == "IDEMP1"
    assert persisted_clean[1].iloc[0]["symbol"] == "IDEMP1"


def test_retry_pending_raw_files_when_directory_is_empty(
    monkeypatch, tmp_path, capsys
):
    monkeypatch.setattr(retry_raw, "RAW_DIR", tmp_path)

    retry_raw.retry_pending_raw_files()

    captured = capsys.readouterr()
    assert f"NU_EXISTĂ_WAL: {tmp_path}" in captured.out


def test_retry_pending_raw_files_continues_after_failure(
    monkeypatch, tmp_path, capsys
):
    first = tmp_path / "2026-10-07_bvb.csv"
    second = tmp_path / "2026-10-08_bvb.csv"

    first.write_text("first", encoding="utf-8")
    second.write_text("second", encoding="utf-8")

    processed = []
    failed_path = first

    def fake_ingest(raw_path):
        processed.append(raw_path)
        if raw_path == failed_path:
            raise ValueError("invalid raw file")

    monkeypatch.setattr(retry_raw, "RAW_DIR", tmp_path)
    monkeypatch.setattr(
        retry_raw,
        "ingest_raw_file_to_postgres",
        fake_ingest,
    )

    retry_raw.retry_pending_raw_files()

    captured = capsys.readouterr()

    assert processed == [first, second]
    assert f"RETRY_FAILED: {first}" in captured.out
    assert f"RETRY_SUCCESS: {second}" in captured.out


import os


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL nu este configurat",
)
def test_persist_clean_prices_is_idempotent():
    import fetch_bvb

    frame = pd.DataFrame(
        [
            {
                "date": "2026-10-08",
                "symbol": "INTEGRATION1",
                "name": "Integration test",
                "market": "REGS",
                "trades": 1,
                "volume": 100,
                "value": 1000.0,
                "open": 10.0,
                "low": 9.5,
                "high": 10.5,
                "avg_price": 10.0,
                "close": 10.0,
                "ref_price": 10.0,
                "change_pct": 0.0,
                "source": "pytest_integration",
                "ingested_at": "2026-10-08T00:00:00+00:00",
            }
        ]
    )

    database_url = os.environ["DATABASE_URL"]

    import psycopg

    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM prices_daily
                WHERE trade_date = %s
                  AND symbol = %s
                  AND source = %s
                """,
                ("2026-10-08", "INTEGRATION1", "pytest_integration"),
            )

    fetch_bvb.persist_clean_prices_to_postgres(frame)
    fetch_bvb.persist_clean_prices_to_postgres(frame)

    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM prices_daily
                WHERE trade_date = %s
                  AND symbol = %s
                  AND source = %s
                """,
                ("2026-10-08", "INTEGRATION1", "pytest_integration"),
            )
            count = cursor.fetchone()[0]

            cursor.execute(
                """
                DELETE FROM prices_daily
                WHERE trade_date = %s
                  AND symbol = %s
                  AND source = %s
                """,
                ("2026-10-08", "INTEGRATION1", "pytest_integration"),
            )

    assert count == 1
