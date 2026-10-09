CREATE TABLE IF NOT EXISTS prices_daily (
    id BIGSERIAL PRIMARY KEY,
    trade_date DATE NOT NULL,
    symbol TEXT NOT NULL,
    name TEXT NOT NULL DEFAULT '',
    market TEXT NOT NULL,
    trades BIGINT NOT NULL,
    volume BIGINT NOT NULL,
    value NUMERIC(20, 4) NOT NULL,
    open NUMERIC(20, 10) NOT NULL,
    low NUMERIC(20, 10) NOT NULL,
    high NUMERIC(20, 10) NOT NULL,
    avg_price NUMERIC(20, 10) NOT NULL,
    close NUMERIC(20, 10) NOT NULL,
    ref_price NUMERIC(20, 10) NOT NULL,
    change_pct NUMERIC(20, 10) NOT NULL,
    source TEXT NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL,
    UNIQUE (trade_date, symbol, source)
);

CREATE TABLE IF NOT EXISTS price_adjustments (
    id BIGSERIAL PRIMARY KEY,
    corporate_action_id BIGINT NOT NULL REFERENCES corporate_actions(id),
    trade_date DATE NOT NULL,
    symbol TEXT NOT NULL,
    factor NUMERIC(30, 20) NOT NULL,
    status TEXT NOT NULL DEFAULT 'planned',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (corporate_action_id, trade_date, symbol)
);
