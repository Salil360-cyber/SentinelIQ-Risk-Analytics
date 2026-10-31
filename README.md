# SentinelIQ-Risk-Analytics
Financial risk and trade operations analytics project using SQL, Python, Excel, and Power BI to analyze transactions, identify risk patterns, monitor AML flags, and study operational trends.
# SentinelIQ – Enterprise Risk, Trade Operations & AML Intelligence

## Project Overview

SentinelIQ is a financial risk and trade operations analytics project focused on analyzing account, trade, transaction, and risk issue data.

The project explores how SQL, Python, Excel, and Power BI can support transaction analysis, operational risk monitoring, trend identification, and AML-related issue investigation.

## Problem Statement

Financial operations involve large volumes of trades and transactions. Monitoring these records is important for identifying unusual patterns, understanding operational issues, and highlighting accounts associated with multiple risk indicators.

## Project Objectives

- Analyze account, trade, transaction, and risk issue datasets.
- Identify monthly trends and unusual patterns.
- Examine accounts associated with multiple risk flags.
- Develop a short-term issue trend forecast.
- Design reporting views for operational and AML monitoring.

## STAR Analysis

### Situation
The project involved analyzing financial operations data containing multiple accounts, trades, transactions, and risk issue records.

### Task
Analyze the available data to understand operational issue patterns, identify accounts with multiple risk indicators, and summarize trends.

### Action
- Analyzed a dataset covering **500 accounts, 10,000 trades, 10,000 transactions, and 2,429 risk issues**.
- Used Python with Pandas and NumPy for monthly trend analysis and a three-month forecast.
- Accounted for an incomplete reporting month while interpreting monthly issue trends.
- Used SQL conditional aggregation to identify accounts containing both TradeFailure and AMLFlag records.
- Outlined Power BI reporting views for Trade Operations, AML monitoring, and combined issues.
- Proposed drill-through and region-based row-level security for reporting.

### Result
- Identified **21 issues in September 2026**, an incomplete month, compared with approximately 70–80 issues in typical full months.
- Developed structured insights into transaction patterns, operational issues, and risk indicators.
- Outlined reporting views to improve risk visibility and issue monitoring.

## Tools & Technologies

- Microsoft Excel
- SQL
- Python
- Pandas
- NumPy
- Power BI

## Key Skills Demonstrated

- Data Analysis
- Data Validation
- Transaction Analysis
- Trend Analysis
- Anomaly Identification
- Financial Risk Monitoring
- SQL Aggregation
- AML Flag Analysis
- Reporting and Data Interpretation

## Project Limitations

- The analysis is based on the available project dataset.
- September 2026 represents an incomplete reporting month and should not be directly compared with full-month totals without considering the reporting period.
- Power BI drill-through and region-based row-level security were outlined as reporting design features.

## Disclaimer

This is a portfolio analytics project for learning and demonstration purposes. It does not represent the systems, data, or internal processes of any financial institution.
