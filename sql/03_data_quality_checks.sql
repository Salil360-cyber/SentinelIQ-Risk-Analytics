-- SentinelIQ: data-quality checks. Run after loading.
-- One view lists every exception; the summary counts them per check.

DROP VIEW IF EXISTS v_dq_exceptions;
CREATE VIEW v_dq_exceptions AS

-- 1. Trade booked before the account was opened
SELECT 'Trade before account opened' AS check_name, t.trade_id AS record_id,
       t.account_id, 'Trade ' || t.trade_date || ', opened ' || a.opened_date AS detail
FROM trades t JOIN accounts a ON a.account_id = t.account_id
WHERE t.trade_date < a.opened_date

UNION ALL
-- 2. Transaction before the account was opened
SELECT 'Transaction before account opened', x.transaction_id, x.account_id,
       'Txn ' || x.txn_timestamp::date || ', opened ' || a.opened_date
FROM transactions x JOIN accounts a ON a.account_id = x.account_id
WHERE x.txn_timestamp::date < a.opened_date

UNION ALL
-- 3. Trade marked Settled but no settlement date
SELECT 'Settled trade missing settlement date', trade_id, account_id, 'Status Settled, settlement_date NULL'
FROM trades
WHERE settlement_status = 'Settled' AND settlement_date IS NULL

UNION ALL
-- 4. Duplicate transactions: same account, time, type and amount under different IDs
SELECT 'Duplicate transaction', transaction_id, account_id, 'Same as ' || first_id
FROM (
    SELECT transaction_id, account_id,
           MIN(transaction_id) OVER (PARTITION BY account_id, txn_timestamp, transaction_type, amount) AS first_id
    FROM transactions
) d
WHERE transaction_id <> first_id

UNION ALL
-- 5. Flag and reason disagree
SELECT 'Flag without reason (or reason without flag)', transaction_id, account_id, 'flagged=' || flagged
FROM transactions
WHERE (flagged = 'Yes' AND flag_reason IS NULL) OR (flagged = 'No' AND flag_reason IS NOT NULL)

UNION ALL
-- 6. Closed issue without a resolution date, or open issue with one
SELECT 'Issue status and resolution date disagree', issue_id, account_id, 'status=' || status
FROM risk_issues
WHERE (status = 'Closed') <> (resolution_date IS NOT NULL)

UNION ALL
-- 7. Issue resolved before it was raised
SELECT 'Issue resolved before raised', issue_id, account_id, raised_date || ' > ' || resolution_date
FROM risk_issues
WHERE resolution_date < raised_date

UNION ALL
-- 8. Issue points to a trade or transaction that does not exist
SELECT 'Issue source not found', i.issue_id, i.account_id, i.source_type || ' ' || i.source_id
FROM risk_issues i
LEFT JOIN trades t       ON i.source_type = 'TradeFailure' AND t.trade_id = i.source_id
LEFT JOIN transactions x ON i.source_type = 'AMLFlag'      AND x.transaction_id = i.source_id
WHERE t.trade_id IS NULL AND x.transaction_id IS NULL;

-- Summary: one row per check, including checks that found nothing
SELECT c.check_name, COUNT(d.record_id) AS exceptions
FROM (VALUES ('Trade before account opened'), ('Transaction before account opened'),
             ('Settled trade missing settlement date'), ('Duplicate transaction'),
             ('Flag without reason (or reason without flag)'), ('Issue status and resolution date disagree'),
             ('Issue resolved before raised'), ('Issue source not found')) AS c(check_name)
LEFT JOIN v_dq_exceptions d ON d.check_name = c.check_name
GROUP BY c.check_name
ORDER BY exceptions DESC, c.check_name;
