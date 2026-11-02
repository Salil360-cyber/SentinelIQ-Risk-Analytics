"""
SentinelIQ configuration.

Every rule and threshold used by the data generator, the AML rule engine and
the analysis lives here, so a reviewer can read and change them in one place.
All data in this project is synthetic.
"""
from datetime import date

SEED = 42

# Reporting window. AS_OF_DATE is mid-month on purpose: September 2026 is a
# partial month, and the analysis must not treat it like a full month.
START_DATE = date(2024, 1, 1)
AS_OF_DATE = date(2026, 9, 15)

N_ACCOUNTS = 500
N_TRADES = 10_000
N_TRANSACTIONS = 10_000

# Country -> region. Every account's region is derived from its country.
COUNTRY_REGION = {
    "UK": "EMEA",
    "Switzerland": "EMEA",
    "Luxembourg": "EMEA",
    "UAE": "EMEA",
    "USA": "North America",
    "Canada": "North America",
    "Singapore": "APAC",
    "India": "APAC",
    "Hong Kong": "APAC",
    "Brazil": "LATAM",
    "Mexico": "LATAM",
    "Cayman Islands": "LATAM",
}

# Illustrative list defined for this project only. It is NOT an official
# regulatory list and does not reflect any real institution's policy.
HIGH_RISK_JURISDICTIONS = ["Cayman Islands", "Panama", "British Virgin Islands"]

# ---------------------------------------------------------------- Trades
SETTLEMENT_CYCLE_BDAYS = 2            # T+2 business days for every asset type
PROBLEM_COUNTERPARTIES = ["Counterparty 07", "Counterparty 18", "Counterparty 23"]

# ---------------------------------------------------------------- AML rules
LARGE_TXN_THRESHOLD = 1_000_000       # R1: single transaction at or above this
HRJ_MIN_AMOUNT = 100_000              # R2: wire to a high-risk jurisdiction at or above this
REPORTING_THRESHOLD = 10_000          # cash reporting threshold used by R3
STRUCTURING_BAND = (9_000, 9_999.99)  # R3: cash deposits just below the threshold...
STRUCTURING_MIN_COUNT = 3             # ...at least this many by one account...
STRUCTURING_WINDOW_DAYS = 7           # ...within this many calendar days

# ---------------------------------------------------------------- Issues
# Target resolution time (business days) by severity. Past due date = SLA breach.
SLA_BDAYS = {"Critical": 5, "High": 10, "Medium": 15, "Low": 20}

# Trade failure severity by trade amount (USD).
TRADE_SEVERITY_BANDS = [(2_000_000, "Critical"), (1_000_000, "High"), (250_000, "Medium"), (0, "Low")]

FAIL_REASON_ROOT_CAUSE = {
    "SSI mismatch": "Data Quality Issue",
    "Insufficient securities": "Third-Party Failure",
    "Counterparty failed to deliver": "Third-Party Failure",
    "Late instruction": "Manual Process Error",
    "System outage": "System/Automation Gap",
}

# ---------------------------------------------------------------- RCSA
# Risk rating is derived from control effectiveness and findings, never random.
def rcsa_rating(control_pct, findings):
    if control_pct < 70 or findings >= 5:
        return "High"
    if control_pct < 85 or findings >= 3:
        return "Moderate"
    return "Low"
