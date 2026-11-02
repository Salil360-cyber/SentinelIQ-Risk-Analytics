"""
Generate the synthetic SentinelIQ dataset into data/.

    python src/generate_data.py

Seeded, so every run produces exactly the same files.
A few data-quality problems are planted on purpose (see PLANTED below) so the
SQL data-quality checks have something real to find.
"""
import csv
import os
from datetime import date, datetime, time, timedelta

import numpy as np

import config as C
from aml_rules import flag_reasons

rng = np.random.default_rng(C.SEED)
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")

# Known, deliberate data-quality problems.
PLANTED = {
    "trades_before_account_opened": 15,
    "transactions_before_account_opened": 10,
    "settled_trades_missing_settlement_date": 5,
    "duplicate_transactions": 8,
}


def bday_offset(d, n):
    return np.busday_offset(np.datetime64(d, "D"), n, roll="forward").astype(date)


def bdays_between(a, b):
    return int(np.busday_count(np.datetime64(a, "D"), np.datetime64(b, "D")))


def random_bday(lo, hi):
    days = np.arange(np.datetime64(lo, "D"), np.datetime64(hi, "D") + np.timedelta64(1, "D"))
    days = days[np.is_busday(days)]
    return rng.choice(days).astype(date)


def write(name, header, rows):
    with open(os.path.join(DATA, name), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def fmt(v):
    if v is None:
        return ""
    if isinstance(v, float):
        return f"{v:.2f}"
    return v


# ------------------------------------------------------------------ Accounts
countries = list(C.COUNTRY_REGION)
country_w = np.array([14, 10, 7, 8, 14, 5, 12, 10, 7, 4, 3, 6], float)
types = ["Individual HNW", "Family Office", "Institutional", "Corporate Treasury"]
type_w = np.array([45, 20, 22, 13], float)

accounts = []
for i in range(C.N_ACCOUNTS):
    country = rng.choice(countries, p=country_w / country_w.sum())
    opened = date(2018, 1, 1) + timedelta(days=int(rng.integers(0, (date(2025, 12, 31) - date(2018, 1, 1)).days)))
    kyc = "High" if country in C.HIGH_RISK_JURISDICTIONS else rng.choice(["Low", "Medium", "High"], p=[0.6, 0.3, 0.1])
    accounts.append({"AccountID": f"ACC{5001 + i}", "Country": country, "Region": C.COUNTRY_REGION[country],
                     "AccountType": rng.choice(types, p=type_w / type_w.sum()), "KYCRiskRating": kyc, "OpenedDate": opened})
acc_by_id = {a["AccountID"]: a for a in accounts}


def account_open_before(d):
    eligible = [a["AccountID"] for a in accounts if a["OpenedDate"] <= d]
    return rng.choice(eligible)


def account_open_after(d):
    later = [a["AccountID"] for a in accounts if a["OpenedDate"] > d]
    return rng.choice(later) if later else None


# ------------------------------------------------------------------ Trades
asset_types = ["Equity", "Fixed Income", "FX", "Derivatives", "Commodities"]
counterparties = [f"Counterparty {i:02d}" for i in range(1, 31)]
fail_reasons = list(C.FAIL_REASON_ROOT_CAUSE)
fail_w = np.array([30, 25, 20, 15, 10], float)

trades = []
for i in range(C.N_TRADES):
    td = random_bday(C.START_DATE, C.AS_OF_DATE)
    acc = account_open_before(td)
    asset = rng.choice(asset_types)
    cp = rng.choice(counterparties)
    amount = float(np.clip(rng.lognormal(np.log(400_000), 1.0), 10_000, 5_000_000))
    expected = bday_offset(td, C.SETTLEMENT_CYCLE_BDAYS)

    status, settle, delay, reason = "Settled", expected, 0, None
    p_fail = 0.035 * (3 if cp in C.PROBLEM_COUNTERPARTIES else 1) * (1.5 if asset == "Derivatives" else 1)
    if expected > C.AS_OF_DATE:
        status, settle, delay = "Pending", None, None
    elif rng.random() < p_fail:
        status, settle, delay = "Failed", None, None
        reason = rng.choice(fail_reasons, p=fail_w / fail_w.sum())
    elif rng.random() < 0.10:
        delay = int(min(rng.geometric(0.35), 10))
        settle = bday_offset(expected, delay)
        if settle > C.AS_OF_DATE:
            status, settle, delay = "Pending", None, None

    trades.append({"TradeID": f"TRD{100000 + i}", "AccountID": acc, "TradeDate": td, "AssetType": asset,
                   "Amount": round(amount, 2), "Counterparty": cp, "SettlementStatus": status,
                   "ExpectedSettlementDate": expected, "SettlementDate": settle, "DelayDays": delay,
                   "FailReason": reason})

# Planted: trades booked before the account was opened.
last_open = max(a["OpenedDate"] for a in accounts)
early = [t for t in trades if t["TradeDate"] < last_open]
for t in rng.choice(early, PLANTED["trades_before_account_opened"], replace=False):
    t["AccountID"] = account_open_after(t["TradeDate"])
# Planted: settled trades with no settlement date.
settled = [t for t in trades if t["SettlementStatus"] == "Settled"]
for t in rng.choice(settled, PLANTED["settled_trades_missing_settlement_date"], replace=False):
    t["SettlementDate"] = None

# ------------------------------------------------------------------ Transactions
txn_types = ["Wire Transfer", "Internal Transfer", "Cash Deposit", "Cash Withdrawal", "Card Payment"]
txn_w = np.array([25, 20, 20, 15, 20], float)
amount_params = {  # (median, sigma, min, max)
    "Wire Transfer": (120_000, 1.1, 1_000, 3_000_000),
    "Internal Transfer": (80_000, 1.0, 1_000, 2_000_000),
    "Cash Deposit": (4_000, 0.8, 100, 8_999),
    "Cash Withdrawal": (3_000, 0.8, 100, 8_999),
    "Card Payment": (1_200, 1.0, 10, 25_000),
}
dest_pool = countries + ["Panama", "British Virgin Islands"]


def txn_timestamp(d, ttype):
    if ttype != "Card Payment":
        d = np.busday_offset(np.datetime64(d, "D"), 0, roll="forward").astype(date)
        hour = int(rng.integers(9, 18))
    else:
        hour = int(rng.integers(7, 23))
    return datetime.combine(d, time(hour, int(rng.integers(0, 60)), int(rng.integers(0, 60))))


txns = []
span = (C.AS_OF_DATE - C.START_DATE).days
for i in range(C.N_TRANSACTIONS - 0):
    ttype = rng.choice(txn_types, p=txn_w / txn_w.sum())
    d = C.START_DATE + timedelta(days=int(rng.integers(0, span + 1)))
    ts = txn_timestamp(d, ttype)
    if ts.date() > C.AS_OF_DATE:
        ts = txn_timestamp(C.AS_OF_DATE, ttype)
    acc = account_open_before(ts.date())
    med, sig, lo, hi = amount_params[ttype]
    amount = float(np.clip(rng.lognormal(np.log(med), sig), lo, hi))
    if ttype == "Wire Transfer":
        dest = rng.choice(dest_pool, p=None) if rng.random() < 0.35 else acc_by_id[acc]["Country"]
    else:
        dest = acc_by_id[acc]["Country"]
    txns.append({"AccountID": acc, "Timestamp": ts, "TransactionType": ttype,
                 "Amount": round(amount, 2), "DestinationCountry": dest})

# Planted (realistic) structuring: some accounts split cash into deposits just below the threshold.
lo_band, hi_band = C.STRUCTURING_BAND
for _ in range(30):
    start = C.START_DATE + timedelta(days=int(rng.integers(0, span - 10)))
    acc = account_open_before(start)
    for k in range(int(rng.integers(3, 6))):
        ts = txn_timestamp(start + timedelta(days=int(rng.integers(0, 6))), "Cash Deposit")
        txns.append({"AccountID": acc, "Timestamp": ts, "TransactionType": "Cash Deposit",
                     "Amount": round(float(rng.uniform(lo_band, hi_band)), 2), "DestinationCountry": acc_by_id[acc]["Country"]})

# Keep exactly N_TRANSACTIONS: drop random non-structuring rows to make room.
extra = len(txns) - C.N_TRANSACTIONS
drop = set(rng.choice(np.arange(C.N_TRANSACTIONS), extra, replace=False).tolist())
txns = [t for j, t in enumerate(txns) if j not in drop]
txns.sort(key=lambda t: t["Timestamp"])
for i, t in enumerate(txns):
    t["TransactionID"] = f"TXN{200000 + i}"

# Planted: activity before the account was opened (card payments only, so no AML rule is affected).
cards = [t for t in txns if t["TransactionType"] == "Card Payment" and t["Timestamp"].date() < last_open]
planted_early = set()
for t in rng.choice(cards, PLANTED["transactions_before_account_opened"], replace=False):
    t["AccountID"] = account_open_after(t["Timestamp"].date())
    planted_early.add(t["TransactionID"])

# Planted: duplicate rows (same account, time, type, amount) with a new ID, replacing card payments at the end.
card_list = [t for t in txns if t["TransactionType"] == "Card Payment" and t["TransactionID"] not in planted_early]
pick = rng.choice(len(card_list) - 50, PLANTED["duplicate_transactions"], replace=False)
dup_src = [card_list[k] for k in pick]
victims = card_list[-PLANTED["duplicate_transactions"]:]
for v, s in zip(victims, dup_src):
    v.update({k: s[k] for k in ("AccountID", "Timestamp", "TransactionType", "Amount", "DestinationCountry")})
txns.sort(key=lambda t: (t["Timestamp"], t["TransactionID"]))

# AML flags from the rule engine.
reasons = flag_reasons(txns)
escalate_p = {"LargeTransaction": 0.25, "HighRiskJurisdiction": 0.45, "StructuringPattern": 0.85}
review_cutoff = bday_offset(C.AS_OF_DATE, -3)
for t in txns:
    r = reasons.get(t["TransactionID"])
    t["Flagged"] = "Yes" if r else "No"
    t["FlagReason"] = r
    if not r:
        t["AlertStatus"] = None
    elif t["Timestamp"].date() > review_cutoff:
        t["AlertStatus"] = "Pending Review"
    else:
        parts = r.split(";")
        p = 0.9 if len(parts) > 1 else escalate_p[parts[0]]
        t["AlertStatus"] = "Escalated" if rng.random() < p else "Cleared"

# ------------------------------------------------------------------ Risk issues
def trade_severity(amount):
    for floor, sev in C.TRADE_SEVERITY_BANDS:
        if amount >= floor:
            return sev


def aml_severity(reason):
    parts = reason.split(";")
    if len(parts) > 1:
        return "Critical" if "LargeTransaction" in parts else "High"
    return {"StructuringPattern": "High", "HighRiskJurisdiction": "Medium", "LargeTransaction": "Medium"}[parts[0]]


AML_ROOT = {"StructuringPattern": "Structuring Behaviour", "HighRiskJurisdiction": "Jurisdiction Risk",
            "LargeTransaction": "Unusual Transaction Size"}

issues = []
for t in trades:
    if t["SettlementStatus"] == "Failed":
        issues.append({"SourceType": "TradeFailure", "SourceID": t["TradeID"], "AccountID": t["AccountID"],
                       "RaisedDate": t["ExpectedSettlementDate"],
                       "Description": f"Trade settlement failure: {t['FailReason']}",
                       "Severity": trade_severity(t["Amount"]),
                       "RootCauseCategory": C.FAIL_REASON_ROOT_CAUSE[t["FailReason"]]})
for t in txns:
    if t["AlertStatus"] == "Escalated":
        parts = t["FlagReason"].split(";")
        issues.append({"SourceType": "AMLFlag", "SourceID": t["TransactionID"], "AccountID": t["AccountID"],
                       "RaisedDate": bday_offset(t["Timestamp"].date(), int(rng.integers(1, 4))),
                       "Description": f"Escalated AML alert: {t['FlagReason']}",
                       "Severity": aml_severity(t["FlagReason"]),
                       "RootCauseCategory": "Multiple Rules" if len(parts) > 1 else AML_ROOT[parts[0]]})

issues.sort(key=lambda x: (x["RaisedDate"], x["SourceID"]))
for i, iss in enumerate(issues):
    iss["IssueID"] = f"ISS{i + 1:05d}"
    target = C.SLA_BDAYS[iss["Severity"]]
    iss["DueDate"] = bday_offset(iss["RaisedDate"], target)
    took = max(1, int(round(target * rng.lognormal(np.log(0.8), 0.55))))
    resolved = bday_offset(iss["RaisedDate"], took)
    if resolved <= C.AS_OF_DATE:
        iss["Status"], iss["ResolutionDate"] = "Closed", resolved
    else:
        iss["ResolutionDate"] = None
        if bdays_between(iss["RaisedDate"], C.AS_OF_DATE) <= 2:
            iss["Status"] = "Open"
        elif C.AS_OF_DATE > iss["DueDate"]:
            iss["Status"] = "Escalated"
        else:
            iss["Status"] = "Under Review"

# ------------------------------------------------------------------ RCSA
def quarter_of(d):
    return f"{d.year}-Q{(d.month - 1) // 3 + 1}"


quarters = [f"{y}-Q{q}" for y in (2024, 2025, 2026) for q in (1, 2, 3, 4)][:10]  # 2024-Q1 .. 2026-Q2
issue_q = {}
for iss in issues:
    key = ("Trade Operations" if iss["SourceType"] == "TradeFailure" else "AML & Transaction Monitoring",
           quarter_of(iss["RaisedDate"]))
    issue_q[key] = issue_q.get(key, 0) + 1

rcsa = []
units = ["Trade Operations", "AML & Transaction Monitoring", "Client Onboarding", "Settlement & Custody"]
n = 1
for bu in units:
    for q in quarters:
        if bu in ("Trade Operations", "AML & Transaction Monitoring"):
            findings = int(round(issue_q.get((bu, q), 0) / (10 if bu == "Trade Operations" else 6))) + int(rng.integers(0, 2))
        elif bu == "Settlement & Custody":
            findings = int(round(issue_q.get(("Trade Operations", q), 0) / 15)) + int(rng.integers(0, 2))
        else:
            findings = int(rng.integers(0, 5))
        control = float(np.clip(97 - 4.5 * findings + rng.normal(0, 3), 50, 99))
        rcsa.append([f"RCSA{n:04d}", bu, q, C.rcsa_rating(control, findings), round(control, 1), findings])
        n += 1

# ------------------------------------------------------------------ Write
os.makedirs(DATA, exist_ok=True)
write("accounts.csv", ["AccountID", "Country", "Region", "AccountType", "KYCRiskRating", "OpenedDate"],
      [[a[k] for k in ("AccountID", "Country", "Region", "AccountType", "KYCRiskRating", "OpenedDate")] for a in accounts])
tcols = ["TradeID", "AccountID", "TradeDate", "AssetType", "Amount", "Counterparty", "SettlementStatus",
         "ExpectedSettlementDate", "SettlementDate", "DelayDays", "FailReason"]
write("trades.csv", tcols, [[fmt(t[k]) for k in tcols] for t in trades])
xcols = ["TransactionID", "AccountID", "Timestamp", "TransactionType", "Amount", "DestinationCountry",
         "Flagged", "FlagReason", "AlertStatus"]
write("transactions.csv", xcols,
      [[fmt(t[k]) if k != "Timestamp" else t[k].strftime("%Y-%m-%d %H:%M:%S") for k in xcols] for t in txns])
icols = ["IssueID", "SourceType", "SourceID", "AccountID", "RaisedDate", "Description", "Severity", "Status",
         "RootCauseCategory", "DueDate", "ResolutionDate"]
write("risk_issues.csv", icols, [[fmt(i[k]) for k in icols] for i in issues])
write("rcsa.csv", ["AssessmentID", "BusinessUnit", "Quarter", "RiskRating", "ControlEffectivenessPct", "FindingsCount"], rcsa)

print(f"accounts {len(accounts)}, trades {len(trades)}, transactions {len(txns)}, issues {len(issues)}, rcsa {len(rcsa)}")
print("planted:", PLANTED)
