# Power BI build guide (planned)

The dashboard is **not built yet**. This guide describes how to build it on the CSV files in `data/`.
After building, check the numbers against the table at the end.

## 1. Load and model

1. Get Data → Text/CSV → load all five files.
2. Power Query: set dates to Date (Timestamp to Date/Time), amounts to Decimal, and keep empty `DelayDays` as null (do **not** replace with 0).
3. Add a date table: Modeling → New table → `Date = CALENDAR(DATE(2024,1,1), DATE(2026,12,31))`, mark it as a date table.
4. Relationships (one-to-many, single direction):
   - `accounts[AccountID]` → `trades`, `transactions`, `risk_issues`
   - `Date[Date]` → `risk_issues[RaisedDate]`

## 2. Measures

```
Trades = COUNTROWS(trades)
Failed Trades = CALCULATE(COUNTROWS(trades), trades[SettlementStatus] = "Failed")
Failure Rate % = DIVIDE([Failed Trades], [Trades])

Transactions = COUNTROWS(transactions)
AML Alerts = CALCULATE(COUNTROWS(transactions), transactions[Flagged] = "Yes")
Alert Rate % = DIVIDE([AML Alerts], [Transactions])
Escalation Rate % = DIVIDE(
    CALCULATE(COUNTROWS(transactions), transactions[AlertStatus] = "Escalated"),
    CALCULATE(COUNTROWS(transactions), transactions[AlertStatus] IN {"Escalated", "Cleared"}))

Issues = COUNTROWS(risk_issues)
Trade Issues = CALCULATE([Issues], risk_issues[SourceType] = "TradeFailure")
AML Issues = CALCULATE([Issues], risk_issues[SourceType] = "AMLFlag")
Open Issues = CALCULATE([Issues], risk_issues[Status] <> "Closed")
Closed Within SLA % = DIVIDE(
    CALCULATE([Issues], risk_issues[Status] = "Closed",
              FILTER(risk_issues, risk_issues[ResolutionDate] <= risk_issues[DueDate])),
    CALCULATE([Issues], risk_issues[Status] = "Closed"))

Cross-Domain Accounts =
COUNTROWS(
    FILTER(VALUES(risk_issues[AccountID]),
        CALCULATE([Trade Issues]) > 0 && CALCULATE([AML Issues]) > 0))
```

## 3. Pages

1. **Overview:** cards (Failure Rate %, Alert Rate %, Issues, Open Issues, Closed Within SLA %, Cross-Domain Accounts); monthly issues by SourceType (stacked column); slicers for Region and AccountType.
2. **Trade operations:** failure rate by Counterparty and by AssetType (bar); failures by FailReason.
3. **AML monitoring:** alerts by FlagReason split by AlertStatus; escalation rate by rule.
4. **Issues & RCSA:** issues by Severity and Status; RCSA control effectiveness by BusinessUnit over Quarter (line).
5. Optional drill-through page by AccountID showing that account's trades, transactions and issues.

Mark September 2026 as a partial month on any monthly chart (data runs to 15 Sep).

## 4. Check your numbers

| Measure (no filters) | Expected |
| --- | --- |
| Trades / Failure Rate % | 10,000 / 4.34% |
| AML Alerts / Alert Rate % | 356 / 3.56% |
| Escalation Rate % | 56.3% |
| Issues (Trade / AML) | 634 (434 / 200) |
| Open Issues | 15 |
| Closed Within SLA % | 69.6% |
| Cross-Domain Accounts | 54 |
