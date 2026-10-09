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
