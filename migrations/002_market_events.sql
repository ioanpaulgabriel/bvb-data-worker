CREATE TABLE IF NOT EXISTS market_events (
    id            BIGSERIAL PRIMARY KEY,
    symbol        VARCHAR(16)  NOT NULL,
    event_type    VARCHAR(32)  NOT NULL,
    event_source  VARCHAR(16)  NOT NULL,  -- 'CALENDAR' | 'AD_HOC'
    title         TEXT         NOT NULL,
    effective_date DATE        NOT NULL,
    source_url    TEXT,
    raw_payload   JSONB,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    UNIQUE (symbol, event_type, effective_date, source_url)
);
CREATE INDEX IF NOT EXISTS idx_market_events_symbol_date
    ON market_events (symbol, effective_date DESC);
CREATE INDEX IF NOT EXISTS idx_market_events_type
    ON market_events (event_type);
