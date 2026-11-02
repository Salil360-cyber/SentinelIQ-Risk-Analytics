"""
AML transaction monitoring rules.

The same function is used to create the flags in the data and to re-check
them in the analysis, so the two can never silently disagree.

R1 LargeTransaction      amount >= LARGE_TXN_THRESHOLD
R2 HighRiskJurisdiction  wire transfer to a high-risk jurisdiction, amount >= HRJ_MIN_AMOUNT
R3 StructuringPattern    an account makes STRUCTURING_MIN_COUNT or more cash deposits,
                         each just below the reporting threshold, within
                         STRUCTURING_WINDOW_DAYS calendar days
"""
from collections import defaultdict
from datetime import timedelta

import config as C


def _structuring_ids(rows):
    """Return the transaction IDs that are part of a structuring pattern."""
    lo, hi = C.STRUCTURING_BAND
    by_account = defaultdict(list)
    for r in rows:
        if r["TransactionType"] == "Cash Deposit" and lo <= r["Amount"] <= hi:
            by_account[r["AccountID"]].append(r)

    flagged = set()
    window = timedelta(days=C.STRUCTURING_WINDOW_DAYS)
    for deposits in by_account.values():
        deposits.sort(key=lambda r: r["Timestamp"])
        j = 0
        for i in range(len(deposits)):
            while deposits[i]["Timestamp"] - deposits[j]["Timestamp"] > window:
                j += 1
            if i - j + 1 >= C.STRUCTURING_MIN_COUNT:
                for k in range(j, i + 1):
                    flagged.add(deposits[k]["TransactionID"])
    return flagged


def flag_reasons(rows):
    """
    rows: list of dicts with TransactionID, AccountID, Timestamp (datetime),
          TransactionType, Amount (float), DestinationCountry.
    Returns {TransactionID: "Reason1;Reason2"} for flagged transactions only.
    """
    structuring = _structuring_ids(rows)
    out = {}
    for r in rows:
        reasons = []
        if r["Amount"] >= C.LARGE_TXN_THRESHOLD:
            reasons.append("LargeTransaction")
        if (r["TransactionType"] == "Wire Transfer"
                and r["DestinationCountry"] in C.HIGH_RISK_JURISDICTIONS
                and r["Amount"] >= C.HRJ_MIN_AMOUNT):
            reasons.append("HighRiskJurisdiction")
        if r["TransactionID"] in structuring:
            reasons.append("StructuringPattern")
        if reasons:
            out[r["TransactionID"]] = ";".join(reasons)
    return out
