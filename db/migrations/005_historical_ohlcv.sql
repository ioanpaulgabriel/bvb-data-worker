CREATE TABLE IF NOT EXISTS historical_ohlcv (
    id BIGSERIAL PRIMARY KEY,
    trade_date DATE NOT NULL,
    symbol TEXT NOT NULL,
    open NUMERIC(20, 10) NOT NULL,
    high NUMERIC(20, 10) NOT NULL,
    low NUMERIC(20, 10) NOT NULL,
    close NUMERIC(20, 10) NOT NULL,
    volume BIGINT NOT NULL,
    source TEXT NOT NULL,
    source_file TEXT NOT NULL,
    source_sha256 TEXT NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (trade_date, symbol, source)
);

CREATE INDEX IF NOT EXISTS idx_historical_ohlcv_symbol_date
    ON historical_ohlcv (symbol, trade_date);
