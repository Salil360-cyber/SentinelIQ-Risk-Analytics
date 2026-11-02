-- SentinelIQ: table definitions (PostgreSQL). Run first.

DROP TABLE IF EXISTS rcsa, risk_issues, transactions, trades, accounts CASCADE;

CREATE TABLE accounts (
    account_id       VARCHAR(10) PRIMARY KEY,
    country          VARCHAR(40) NOT NULL,
    region           VARCHAR(20) NOT NULL,
    account_type     VARCHAR(30) NOT NULL,
    kyc_risk_rating  VARCHAR(10) NOT NULL,
    opened_date      DATE        NOT NULL
);

CREATE TABLE trades (
    trade_id                 VARCHAR(12) PRIMARY KEY,
    account_id               VARCHAR(10) NOT NULL REFERENCES accounts(account_id),
    trade_date               DATE        NOT NULL,
    asset_type               VARCHAR(20) NOT NULL,
    amount                   NUMERIC(15,2) NOT NULL,
    counterparty             VARCHAR(30) NOT NULL,
    settlement_status        VARCHAR(10) NOT NULL,   -- Settled / Failed / Pending
    expected_settlement_date DATE        NOT NULL,   -- trade date + 2 business days
    settlement_date          DATE,                   -- NULL = not settled
    delay_days               INT,                    -- business days late; 0 = on time; NULL = not settled
    fail_reason              VARCHAR(40)             -- only for Failed trades
);

CREATE TABLE transactions (
    transaction_id      VARCHAR(12) PRIMARY KEY,
    account_id          VARCHAR(10) NOT NULL REFERENCES accounts(account_id),
    txn_timestamp       TIMESTAMP   NOT NULL,
    transaction_type    VARCHAR(20) NOT NULL,
    amount              NUMERIC(15,2) NOT NULL,
    destination_country VARCHAR(40) NOT NULL,
    flagged             VARCHAR(3)  NOT NULL,       -- Yes / No
    flag_reason         VARCHAR(80),                -- rules that fired, separated by ;
    alert_status        VARCHAR(20)                 -- Escalated / Cleared / Pending Review
);

-- No foreign key from source_id: it points to either trades or transactions.
CREATE TABLE risk_issues (
    issue_id            VARCHAR(10) PRIMARY KEY,
    source_type         VARCHAR(15) NOT NULL,       -- TradeFailure / AMLFlag
    source_id           VARCHAR(12) NOT NULL,
    account_id          VARCHAR(10) NOT NULL REFERENCES accounts(account_id),
    raised_date         DATE        NOT NULL,
    description         VARCHAR(120) NOT NULL,
    severity            VARCHAR(10) NOT NULL,
    status              VARCHAR(15) NOT NULL,
    root_cause_category VARCHAR(40) NOT NULL,
    due_date            DATE        NOT NULL,
    resolution_date     DATE
);

CREATE TABLE rcsa (
    assessment_id             VARCHAR(10) PRIMARY KEY,
    business_unit             VARCHAR(40) NOT NULL,
    quarter                   VARCHAR(7)  NOT NULL,
    risk_rating               VARCHAR(10) NOT NULL,
    control_effectiveness_pct NUMERIC(5,1) NOT NULL,
    findings_count            INT         NOT NULL
);

CREATE INDEX idx_trades_account ON trades(account_id);
CREATE INDEX idx_txn_account    ON transactions(account_id, flagged);
CREATE INDEX idx_issues_source  ON risk_issues(source_type, severity);
