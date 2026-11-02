"""
SentinelIQ analysis.

    python src/analysis.py

1. Re-runs the AML rules on the raw transactions and checks they match the flags in the data.
2. Builds a monthly issue trend and a simple 3-month forecast. September 2026 is a partial
   month (data runs to the 15th), so it is excluded from the trend.
3. Tests the forecast honestly: fit on all full months except the last 3, predict those 3,
   and report the mean absolute error (MAE).
4. Saves charts to outputs/ and every headline number to outputs/summary.json.
"""
import json
import os
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import config as C
from aml_rules import flag_reasons

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
OUT = os.path.join(HERE, "..", "outputs")
os.makedirs(OUT, exist_ok=True)

NAVY, TEAL, GREY, RED = "#1F3A5F", "#2A9D8F", "#9AA5B1", "#C0392B"
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})

trades = pd.read_csv(os.path.join(DATA, "trades.csv"), parse_dates=["TradeDate", "SettlementDate"])
txns = pd.read_csv(os.path.join(DATA, "transactions.csv"), parse_dates=["Timestamp"])
issues = pd.read_csv(os.path.join(DATA, "risk_issues.csv"), parse_dates=["RaisedDate", "DueDate", "ResolutionDate"])

summary = {}

# ---------------------------------------------------------------- 1. AML rule re-check
rows = txns.assign(Timestamp=txns.Timestamp.dt.to_pydatetime()).to_dict("records")
expected = flag_reasons(rows)
recomputed = txns.TransactionID.map(expected)
mismatch = (recomputed.fillna("") != txns.FlagReason.fillna("")).sum()
summary["aml_alerts"] = int((txns.Flagged == "Yes").sum())
summary["aml_alert_rate_pct"] = round(100 * (txns.Flagged == "Yes").mean(), 2)
summary["aml_flags_not_reproduced_by_rules"] = int(mismatch)

# ---------------------------------------------------------------- Headline KPIs
summary["trade_failure_rate_pct"] = round(100 * (trades.SettlementStatus == "Failed").mean(), 2)
settled = trades[trades.SettlementStatus == "Settled"]
summary["late_settlement_pct"] = round(100 * (settled.DelayDays > 0).mean(), 2)
summary["issues_total"] = int(len(issues))
summary["issues_trade_failure"] = int((issues.SourceType == "TradeFailure").sum())
summary["issues_aml"] = int((issues.SourceType == "AMLFlag").sum())
both = issues.groupby("AccountID").SourceType.nunique()
summary["cross_domain_accounts"] = int((both == 2).sum())
closed = issues[issues.Status == "Closed"]
summary["closed_within_sla_pct"] = round(100 * (closed.ResolutionDate <= closed.DueDate).mean(), 1)

# ---------------------------------------------------------------- 2. Monthly trend + forecast
monthly = issues.groupby(issues.RaisedDate.dt.to_period("M")).size()
partial = pd.Period(C.AS_OF_DATE, "M")
full = monthly[monthly.index < partial]
summary["partial_month"] = str(partial)
summary["partial_month_issues"] = int(monthly.get(partial, 0))
summary["full_months"] = int(len(full))
summary["avg_issues_per_full_month"] = round(float(full.mean()), 1)

x = np.arange(len(full))
y = full.values.astype(float)

# Back-test: fit without the last 3 full months, predict them.
k = 3
b_slope, b_int = np.polyfit(x[:-k], y[:-k], 1)
pred_test = b_slope * x[-k:] + b_int
summary["backtest_months"] = [str(p) for p in full.index[-k:]]
summary["backtest_actual"] = [int(v) for v in y[-k:]]
summary["backtest_predicted"] = [round(float(v), 1) for v in pred_test]
summary["backtest_mae"] = round(float(np.mean(np.abs(y[-k:] - pred_test))), 2)
summary["naive_mean_mae"] = round(float(np.mean(np.abs(y[-k:] - y[:-k].mean()))), 2)

# Final model on all full months, forecast the next 3 months (Sep to Nov 2026).
slope, intercept = np.polyfit(x, y, 1)
future = np.arange(len(full), len(full) + 3)
forecast = slope * future + intercept
summary["trend_issues_per_month"] = round(float(slope), 2)
summary["forecast_months"] = [str(partial + i) for i in range(3)]
summary["forecast_issues"] = [round(float(v), 1) for v in forecast]

# ---------------------------------------------------------------- 3. Charts
def save(fig, name):
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, name), dpi=150)
    plt.close(fig)


# Monthly issues by source + trend + forecast
by_src = issues[issues.RaisedDate.dt.to_period("M") < partial].groupby(
    [issues.RaisedDate.dt.to_period("M"), "SourceType"]).size().unstack(fill_value=0)
fig, ax = plt.subplots(figsize=(10, 4))
idx = np.arange(len(by_src))
ax.bar(idx, by_src["TradeFailure"], color=NAVY, label="Trade failure issues")
ax.bar(idx, by_src["AMLFlag"], bottom=by_src["TradeFailure"], color=TEAL, label="AML issues")
ax.plot(x, slope * x + intercept, color=GREY, lw=1.5, ls="--", label="Linear trend")
ax.plot(future, forecast, color=RED, marker="o", lw=1.5, label="Forecast (next 3 months)")
labels = [str(p) for p in by_src.index] + summary["forecast_months"]
ticks = list(idx) + list(future)
ax.set_xticks(ticks[::3])
ax.set_xticklabels(labels[::3], rotation=45, ha="right")
ax.set_ylabel("Issues raised")
ax.set_title(f"Monthly risk issues (full months only; {partial} is partial and excluded)", loc="left")
ax.set_ylim(0, y.max() * 1.25)
ax.legend(frameon=False, ncol=4, fontsize=8, loc="upper left")
save(fig, "monthly_issues_forecast.png")

# Failure rate by counterparty (top 10)
cp = trades.groupby("Counterparty").SettlementStatus.apply(lambda s: 100 * (s == "Failed").mean()).sort_values().tail(10)
fig, ax = plt.subplots(figsize=(7, 4))
colors = [RED if v >= 1.9 * summary["trade_failure_rate_pct"] else NAVY for v in cp.values]
ax.barh(cp.index, cp.values, color=colors)
ax.axvline(summary["trade_failure_rate_pct"], color=GREY, ls="--", lw=1)
ax.text(summary["trade_failure_rate_pct"] + 0.1, -0.6, f"overall {summary['trade_failure_rate_pct']}%", color="#555", fontsize=8)
for i, v in enumerate(cp.values):
    ax.text(v + 0.1, i, f"{v:.1f}%", va="center", fontsize=8)
ax.set_xlabel("Settlement failure rate (%)")
ax.set_title("Top 10 counterparties by settlement failure rate (red = about double the overall rate)", loc="left", fontsize=9)
save(fig, "failure_rate_by_counterparty.png")

# AML alerts by rule and outcome
fl = txns[txns.Flagged == "Yes"].groupby(["FlagReason", "AlertStatus"]).size().unstack(fill_value=0)
fl = fl.loc[fl.sum(axis=1).sort_values().index]
fig, ax = plt.subplots(figsize=(7, 3.6))
left = np.zeros(len(fl))
for col, colr in [("Escalated", RED), ("Cleared", GREY), ("Pending Review", TEAL)]:
    if col in fl:
        ax.barh(fl.index, fl[col], left=left, color=colr, label=col)
        left += fl[col].values
ax.set_xlabel("AML alerts")
ax.set_title(f"AML alerts by rule ({summary['aml_alerts']} alerts, {summary['aml_alert_rate_pct']}% of transactions)", loc="left")
ax.legend(frameon=False, fontsize=8)
save(fig, "aml_alerts_by_rule.png")

summary["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
with open(os.path.join(OUT, "summary.json"), "w") as f:
    json.dump(summary, f, indent=2)
print(json.dumps(summary, indent=2))
