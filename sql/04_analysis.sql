-- SentinelIQ: analysis queries. Run after 03_data_quality_checks.sql.
-- Business date of the data: 2026-09-15 (September 2026 is a partial month).

-- Q1. Headline KPIs
SELECT
    COUNT(*)                                                                    AS trades,
    ROUND(100.0 * COUNT(*) FILTER (WHERE settlement_status = 'Failed') / COUNT(*), 2) AS failure_rate_pct,
    ROUND(100.0 * COUNT(*) FILTER (WHERE delay_days > 0)
          / COUNT(*) FILTER (WHERE settlement_status = 'Settled'), 2)           AS late_settlement_pct,
    ROUND(AVG(delay_days) FILTER (WHERE delay_days > 0), 2)                    AS avg_bdays_late_when_late
FROM trades;

SELECT
    COUNT(*)                                                                      AS transactions,
    COUNT(*) FILTER (WHERE flagged = 'Yes')                                       AS alerts,
    ROUND(100.0 * COUNT(*) FILTER (WHERE flagged = 'Yes') / COUNT(*), 2)          AS alert_rate_pct,
    COUNT(*) FILTER (WHERE alert_status = 'Escalated')                            AS escalated,
    ROUND(100.0 * COUNT(*) FILTER (WHERE alert_status = 'Escalated')
          / NULLIF(COUNT(*) FILTER (WHERE alert_status IN ('Escalated', 'Cleared')), 0), 1) AS escalation_rate_pct
FROM transactions;

-- Q2. Failure rate by counterparty (top 5, at least 100 trades)
SELECT counterparty, COUNT(*) AS trades,
       COUNT(*) FILTER (WHERE settlement_status = 'Failed') AS failed,
       ROUND(100.0 * COUNT(*) FILTER (WHERE settlement_status = 'Failed') / COUNT(*), 2) AS failure_rate_pct
FROM trades
GROUP BY counterparty
HAVING COUNT(*) >= 100
ORDER BY failure_rate_pct DESC
LIMIT 5;

-- Q3. Failure rate by asset type
SELECT asset_type, COUNT(*) AS trades,
       ROUND(100.0 * COUNT(*) FILTER (WHERE settlement_status = 'Failed') / COUNT(*), 2) AS failure_rate_pct
FROM trades
GROUP BY asset_type
ORDER BY failure_rate_pct DESC;

-- Q4. Why trades fail
SELECT fail_reason, COUNT(*) AS failed_trades,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS share_pct
FROM trades
WHERE settlement_status = 'Failed'
GROUP BY fail_reason
ORDER BY failed_trades DESC;

-- Q5. AML alerts by rule: how many are escalated vs cleared
SELECT flag_reason,
       COUNT(*) AS alerts,
       COUNT(*) FILTER (WHERE alert_status = 'Escalated') AS escalated,
       COUNT(*) FILTER (WHERE alert_status = 'Cleared')   AS cleared,
       ROUND(100.0 * COUNT(*) FILTER (WHERE alert_status = 'Escalated')
             / NULLIF(COUNT(*) FILTER (WHERE alert_status IN ('Escalated', 'Cleared')), 0), 1) AS escalation_rate_pct
FROM transactions
WHERE flagged = 'Yes'
GROUP BY flag_reason
ORDER BY alerts DESC;

-- Q6. Cross-domain risk: accounts with BOTH a trade-failure issue and an AML issue
SELECT i.account_id, a.country, a.account_type, a.kyc_risk_rating,
       COUNT(*) FILTER (WHERE i.source_type = 'TradeFailure') AS trade_issues,
       COUNT(*) FILTER (WHERE i.source_type = 'AMLFlag')      AS aml_issues
FROM risk_issues i
JOIN accounts a ON a.account_id = i.account_id
GROUP BY i.account_id, a.country, a.account_type, a.kyc_risk_rating
HAVING COUNT(*) FILTER (WHERE i.source_type = 'TradeFailure') > 0
   AND COUNT(*) FILTER (WHERE i.source_type = 'AMLFlag') > 0
ORDER BY COUNT(*) DESC, i.account_id;

-- Q7. SLA: were issues resolved by their due date? Open issues past due?
SELECT severity,
       COUNT(*) AS issues,
       COUNT(*) FILTER (WHERE status = 'Closed') AS closed,
       ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'Closed' AND resolution_date <= due_date)
             / NULLIF(COUNT(*) FILTER (WHERE status = 'Closed'), 0), 1) AS closed_within_sla_pct,
       COUNT(*) FILTER (WHERE status <> 'Closed') AS open_issues,
       COUNT(*) FILTER (WHERE status <> 'Closed' AND due_date < DATE '2026-09-15') AS open_past_due
FROM risk_issues
GROUP BY severity
ORDER BY CASE severity WHEN 'Critical' THEN 1 WHEN 'High' THEN 2 WHEN 'Medium' THEN 3 ELSE 4 END;

-- Q8. Monthly issue volume (full months only; September 2026 is partial)
SELECT DATE_TRUNC('month', raised_date)::date AS month,
       COUNT(*) AS issues,
       COUNT(*) FILTER (WHERE source_type = 'TradeFailure') AS trade_issues,
       COUNT(*) FILTER (WHERE source_type = 'AMLFlag')      AS aml_issues
FROM risk_issues
WHERE raised_date < DATE '2026-09-01'
GROUP BY 1
ORDER BY 1;

-- Q9. Issues per 100 accounts by region (fair comparison across regions of different size)
SELECT a.region,
       COUNT(DISTINCT a.account_id) AS accounts,
       COUNT(i.issue_id) AS issues,
       ROUND(100.0 * COUNT(i.issue_id) / COUNT(DISTINCT a.account_id), 1) AS issues_per_100_accounts
FROM accounts a
LEFT JOIN risk_issues i ON i.account_id = a.account_id
GROUP BY a.region
ORDER BY issues_per_100_accounts DESC;

-- Q10. RCSA: latest assessment per business unit and change vs previous quarter
SELECT business_unit, quarter, risk_rating, control_effectiveness_pct, findings_count, change_vs_prev_qtr
FROM (
    SELECT r.*,
           control_effectiveness_pct
             - LAG(control_effectiveness_pct) OVER (PARTITION BY business_unit ORDER BY quarter) AS change_vs_prev_qtr,
           ROW_NUMBER() OVER (PARTITION BY business_unit ORDER BY quarter DESC) AS rn
    FROM rcsa r
) x
WHERE rn = 1
ORDER BY control_effectiveness_pct;
