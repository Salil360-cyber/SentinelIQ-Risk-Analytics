# Data dictionary

All data is synthetic. Business date (as-of): **2026-09-15**. Dates are YYYY-MM-DD.

## accounts.csv (500 rows)

| Column | Meaning |
| --- | --- |
| AccountID | Unique account ID (ACC5001–ACC5500) |
| Country | Account domicile |
| Region | Derived from Country (see `COUNTRY_REGION` in `src/config.py`) |
| AccountType | Individual HNW, Family Office, Institutional, Corporate Treasury |
| KYCRiskRating | Low / Medium / High (accounts domiciled in a listed high-risk jurisdiction are always High) |
| OpenedDate | Date the account was opened |

## trades.csv (10,000 rows)

| Column | Meaning |
| --- | --- |
| TradeID | Unique trade ID |
| AccountID | Account that placed the trade |
| TradeDate | Business day only (no weekends) |
| AssetType | Equity, Fixed Income, FX, Derivatives, Commodities |
| Amount | Trade value (USD) |
| Counterparty | Counterparty 01–30 |
| SettlementStatus | Settled, Failed or Pending (expected date after the business date, or late and not yet settled) |
| ExpectedSettlementDate | TradeDate + 2 business days |
| SettlementDate | Actual settlement date; empty if not settled |
| DelayDays | Business days between expected and actual settlement. **0 = on time. Empty = not settled.** |
| FailReason | Only for Failed trades: SSI mismatch, Insufficient securities, Counterparty failed to deliver, Late instruction, System outage |

## transactions.csv (10,000 rows)

| Column | Meaning |
| --- | --- |
| TransactionID | Unique transaction ID |
| AccountID | Account |
| Timestamp | Date and time. Non-card transactions happen on business days, 09:00–18:00 |
| TransactionType | Wire Transfer, Internal Transfer, Cash Deposit, Cash Withdrawal, Card Payment |
| Amount | USD |
| DestinationCountry | Where the money went (domestic unless a cross-border wire) |
| Flagged | Yes if at least one AML rule fired |
| FlagReason | Rules that fired, separated by `;` |
| AlertStatus | For flagged rows: Escalated (became an issue), Cleared (reviewed, explained) or Pending Review (last 3 business days) |

## risk_issues.csv (634 rows)

One issue for every **failed trade** and every **escalated AML alert**.

| Column | Meaning |
| --- | --- |
| IssueID | Unique issue ID |
| SourceType | TradeFailure or AMLFlag |
| SourceID | TradeID or TransactionID that caused the issue |
| AccountID | Same account as the source record |
| RaisedDate | Trade failure: the expected settlement date. AML: 1–3 business days after the transaction |
| Description | Short text with the fail reason or rules |
| Severity | Trade failure by amount (≥2M Critical, ≥1M High, ≥250k Medium, else Low). AML: two rules incl. large value = Critical, other two-rule = High, Structuring = High, single HRJ or Large = Medium |
| Status | Closed, Open (raised in the last 2 business days), Under Review, Escalated (open and past due date) |
| RootCauseCategory | Trade failures: mapped from FailReason. AML: the rule behind the alert |
| DueDate | RaisedDate + SLA (Critical 5, High 10, Medium 15, Low 20 business days) |
| ResolutionDate | Only for Closed issues |

## rcsa.csv (40 rows)

Quarterly Risk & Control Self-Assessment for 4 business units, 2024-Q1 to 2026-Q2.

| Column | Meaning |
| --- | --- |
| AssessmentID | Unique ID |
| BusinessUnit | Trade Operations, AML & Transaction Monitoring, Client Onboarding, Settlement & Custody |
| Quarter | e.g. 2026-Q2 |
| RiskRating | **Derived**: High if control effectiveness < 70% or findings ≥ 5; Moderate if < 85% or findings ≥ 3; else Low |
| ControlEffectivenessPct | Share of controls tested as effective |
| FindingsCount | Control findings; for Trade Operations and AML it rises with that quarter's issue volume |

## Planted data-quality problems

| Problem | Count | Found by |
| --- | --- | --- |
| Trades before the account opened | 15 | DQ check 1 |
| Transactions before the account opened | 10 | DQ check 2 |
| Settled trades with no settlement date | 5 | DQ check 3 |
| Duplicate transactions | 8 | DQ check 4 |
