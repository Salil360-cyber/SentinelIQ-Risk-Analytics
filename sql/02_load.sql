-- SentinelIQ: load the CSV files.
--
-- Option A (psql): run from the repository root:
--     psql -d sentineliq -f sql/01_schema.sql -f sql/02_load.sql
--
-- Option B (pgAdmin): right-click each table -> Import/Export Data -> Import,
--     choose the matching file in data/, Format csv, Header ON, NULL string empty.
--     Load in this order: accounts, trades, transactions, risk_issues, rcsa.

\copy accounts     FROM 'data/accounts.csv'     WITH (FORMAT csv, HEADER true)
\copy trades       FROM 'data/trades.csv'       WITH (FORMAT csv, HEADER true)
\copy transactions FROM 'data/transactions.csv' WITH (FORMAT csv, HEADER true)
\copy risk_issues  FROM 'data/risk_issues.csv'  WITH (FORMAT csv, HEADER true)
\copy rcsa         FROM 'data/rcsa.csv'         WITH (FORMAT csv, HEADER true)

-- Expected row counts: accounts 500, trades 10000, transactions 10000, risk_issues 634, rcsa 40
SELECT 'accounts' AS table_name, COUNT(*) FROM accounts
UNION ALL SELECT 'trades', COUNT(*) FROM trades
UNION ALL SELECT 'transactions', COUNT(*) FROM transactions
UNION ALL SELECT 'risk_issues', COUNT(*) FROM risk_issues
UNION ALL SELECT 'rcsa', COUNT(*) FROM rcsa;
