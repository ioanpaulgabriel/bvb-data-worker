CREATE TABLE IF NOT EXISTS prices_daily_raw (
    id BIGSERIAL PRIMARY KEY,
    trade_date DATE NOT NULL,
    source TEXT NOT NULL DEFAULT 'bvb',
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    http_status INTEGER,
    row_count INTEGER NOT NULL,
    payload JSONB NOT NULL,
    UNIQUE (trade_date, source)
);
