CREATE TABLE IF NOT EXISTS corporate_actions (
    id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    action_type TEXT NOT NULL,
    ex_date DATE NOT NULL,
    record_date DATE,
    payment_date DATE,
    ratio NUMERIC(20, 10),
    cash_amount NUMERIC(20, 10),
    currency TEXT,
    source TEXT NOT NULL,
    source_reference TEXT,
    raw_payload JSONB,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT corporate_actions_action_type_chk
        CHECK (
            action_type IN (
                'split',
                'reverse_split',
                'bonus_issue',
                'rights_issue',
                'dividend',
                'merger',
                'spin_off',
                'delisting',
                'other'
            )
        ),

    CONSTRAINT corporate_actions_status_chk
        CHECK (
            status IN ('pending', 'verified', 'rejected')
        )
);

CREATE INDEX IF NOT EXISTS idx_corporate_actions_symbol_ex_date
    ON corporate_actions (symbol, ex_date);

CREATE INDEX IF NOT EXISTS idx_corporate_actions_status
    ON corporate_actions (status);

CREATE UNIQUE INDEX IF NOT EXISTS uq_corporate_actions_event
    ON corporate_actions (
        symbol,
        action_type,
        ex_date,
        COALESCE(source_reference, '')
    );
