"""Tests for the AML rules and for the generated data. Run: python -m pytest -q"""
import os
import sys
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import config as C  # noqa: E402
from aml_rules import flag_reasons  # noqa: E402

DATA = os.path.join(os.path.dirname(__file__), "..", "data")


def txn(i, acc="A1", ts=datetime(2025, 3, 3, 10), ttype="Wire Transfer", amount=5_000, dest="UK"):
    return {"TransactionID": f"T{i}", "AccountID": acc, "Timestamp": ts, "TransactionType": ttype,
            "Amount": amount, "DestinationCountry": dest}


# ---------------------------------------------------------------- rule tests
def test_large_transaction_threshold_is_inclusive():
    out = flag_reasons([txn(1, amount=C.LARGE_TXN_THRESHOLD), txn(2, amount=C.LARGE_TXN_THRESHOLD - 0.01)])
    assert out == {"T1": "LargeTransaction"}


def test_high_risk_jurisdiction_needs_wire_and_minimum_amount():
    hrj = C.HIGH_RISK_JURISDICTIONS[0]
    out = flag_reasons([
        txn(1, dest=hrj, amount=C.HRJ_MIN_AMOUNT),                                  # flagged
        txn(2, dest=hrj, amount=C.HRJ_MIN_AMOUNT - 1),                              # too small
        txn(3, dest=hrj, amount=C.HRJ_MIN_AMOUNT, ttype="Internal Transfer"),       # not a wire
    ])
    assert out == {"T1": "HighRiskJurisdiction"}


def test_structuring_three_deposits_within_window():
    base = datetime(2025, 3, 3, 10)
    rows = [txn(i, ttype="Cash Deposit", amount=9_500, ts=base + timedelta(days=d)) for i, d in enumerate([0, 2, 6])]
    assert set(flag_reasons(rows)) == {"T0", "T1", "T2"}


def test_structuring_not_flagged_when_spread_out_or_too_few():
    base = datetime(2025, 3, 3, 10)
    spread = [txn(i, ttype="Cash Deposit", amount=9_500, ts=base + timedelta(days=d)) for i, d in enumerate([0, 5, 10])]
    two = [txn(i, ttype="Cash Deposit", amount=9_500, ts=base + timedelta(days=d)) for i, d in enumerate([0, 1])]
    below_band = [txn(i, ttype="Cash Deposit", amount=5_000, ts=base + timedelta(days=d)) for i, d in enumerate([0, 1, 2])]
    assert flag_reasons(spread) == {} and flag_reasons(two) == {} and flag_reasons(below_band) == {}


# ---------------------------------------------------------------- data tests
def load():
    a = pd.read_csv(os.path.join(DATA, "accounts.csv"))
    t = pd.read_csv(os.path.join(DATA, "trades.csv"), parse_dates=["TradeDate", "ExpectedSettlementDate", "SettlementDate"])
    x = pd.read_csv(os.path.join(DATA, "transactions.csv"), parse_dates=["Timestamp"])
    i = pd.read_csv(os.path.join(DATA, "risk_issues.csv"), parse_dates=["RaisedDate", "ResolutionDate"])
    return a, t, x, i


def test_region_always_matches_country():
    a, *_ = load()
    assert (a.Country.map(C.COUNTRY_REGION) == a.Region).all()


def test_no_weekend_trades_or_settlements():
    _, t, _, _ = load()
    assert (t.TradeDate.dt.weekday < 5).all()
    assert (t.SettlementDate.dropna().dt.weekday < 5).all()


def test_delay_days_zero_vs_null():
    _, t, _, _ = load()
    s = t[t.SettlementDate.notna()]
    late = np.busday_count(s.ExpectedSettlementDate.values.astype("datetime64[D]"),
                           s.SettlementDate.values.astype("datetime64[D]"))
    assert (late == s.DelayDays.values).all()                       # 0 = on time, >0 = late
    assert t.loc[t.SettlementStatus.isin(["Failed", "Pending"]), "DelayDays"].isna().all()


def test_flags_match_rules_and_rate_is_realistic():
    _, _, x, _ = load()
    rows = x.assign(Timestamp=x.Timestamp.dt.to_pydatetime()).to_dict("records")
    assert x.TransactionID.map(flag_reasons(rows)).fillna("").equals(x.FlagReason.fillna(""))
    assert (x.Flagged == "Yes").mean() < 0.06


def test_every_issue_has_a_valid_source():
    _, t, x, i = load()
    tf = i[i.SourceType == "TradeFailure"].merge(t, left_on="SourceID", right_on="TradeID")
    aml = i[i.SourceType == "AMLFlag"].merge(x, left_on="SourceID", right_on="TransactionID")
    assert len(tf) + len(aml) == len(i)
    assert (tf.SettlementStatus == "Failed").all() and (aml.AlertStatus == "Escalated").all()
    assert (tf.AccountID_x == tf.AccountID_y).all() and (aml.AccountID_x == aml.AccountID_y).all()
