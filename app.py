import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from pathlib import Path

st.set_page_config(page_title="Trading Analytics", layout="wide")

from pathlib import Path

uploaded_file = st.sidebar.file_uploader(
    "Upload Trade CSV",
    type=["csv"]
)

if uploaded_file is None:
    st.info("Please upload a trade CSV to continue.")
    st.stop()

df = pd.read_csv(uploaded_file)

st.sidebar.success(
    f"Loaded: {uploaded_file.name}"
)

st.sidebar.caption(
    f"{len(df):,} trades loaded"
)

df["EntryTime"] = pd.to_datetime(df["EntryTime"])
df["ExitTime"] = pd.to_datetime(df["ExitTime"])
df = df.sort_values("EntryTime").reset_index(drop=True)

# =========================
# AVAILABLE YEARS
# =========================

available_years = sorted(
    df["EntryTime"]
    .dt.year
    .unique()
)

# =========================
# TIME CONVERSION
# FTMO server time -> New York strategy time
# Based on verified mapping:
# 16:30 FTMO = 09:30 NY
# =========================

df["EntryTimeNY"] = df["EntryTime"] - pd.Timedelta(hours=7)
df["ExitTimeNY"] = df["ExitTime"] - pd.Timedelta(hours=7)

# =========================
# US MARKET HOLIDAYS
# =========================

market_holidays = [
    "2021-01-01","2021-01-18","2021-02-15","2021-04-02","2021-05-31",
    "2021-07-05","2021-09-06","2021-11-25","2021-12-24",

    "2022-01-17","2022-02-21","2022-04-15","2022-05-30","2022-06-20",
    "2022-07-04","2022-09-05","2022-11-24","2022-12-26",

    "2023-01-02","2023-01-16","2023-02-20","2023-04-07","2023-05-29",
    "2023-06-19","2023-07-04","2023-09-04","2023-11-23","2023-12-25",

    "2024-01-01","2024-01-15","2024-02-19","2024-03-29","2024-05-27",
    "2024-06-19","2024-07-04","2024-09-02","2024-11-28","2024-12-25",

    "2025-01-01","2025-01-20","2025-02-17","2025-04-18","2025-05-26",
    "2025-06-19","2025-07-04","2025-09-01","2025-11-27","2025-12-25",

    "2026-01-01","2026-01-19","2026-02-16","2026-04-03","2026-05-25",
    "2026-06-19","2026-07-03","2026-09-07","2026-11-26","2026-12-25"
]

market_holidays = pd.to_datetime(
    market_holidays
).date

# =========================
# SETTINGS SIDEBAR
# =========================

st.sidebar.title("SETTINGS")

account_size = st.sidebar.number_input(
    "Account Size",
    min_value=1000.0,
    value=100000.0,
    step=1000.0
)

risk_mode = st.sidebar.radio(
    "Risk Mode",
    [
        "Fixed Dollar Amount",
        "Account Risk Percentage"
    ]
)

if risk_mode == "Fixed Dollar Amount":

    risk_value = st.sidebar.number_input(
        "Risk Amount ($)",
        min_value=1.0,
        value=250.0,
        step=10.0
    )

    current_risk_per_r = risk_value

else:

    risk_value = st.sidebar.number_input(
        "Risk Percent (%)",
        min_value=0.01,
        value=0.30,
        step=0.05
    )

    current_risk_per_r = account_size * (risk_value / 100)

st.sidebar.markdown("---")

st.sidebar.metric(
    "Current Risk Per R",
    f"${current_risk_per_r:,.2f}"
)

st.sidebar.markdown("---")

exclude_holidays = st.sidebar.checkbox(
    "Exclude Market Holidays",
    value=True
)

st.sidebar.markdown("---")

selected_year = st.sidebar.selectbox(
    "MASTER Dashboard Year",
    ["All Years"] + [str(y) for y in available_years]
)

if exclude_holidays:

    trades_before = len(df)

    df = df[
        ~df["EntryTimeNY"]
            .dt.date
            .isin(market_holidays)
    ].reset_index(drop=True)

    trades_removed = (
        trades_before
        - len(df)
    )

else:

    trades_removed = 0

# =========================
# EQUITY ENGINE
# =========================

balance = account_size

balances = []
profits = []
risk_values = []

for r in df["NetResultR"]:

    if risk_mode == "Fixed Dollar Amount":
        current_risk = risk_value

    else:
        current_risk = balance * (risk_value / 100)

    profit = r * current_risk

    balance += profit

    risk_values.append(current_risk)
    profits.append(profit)
    balances.append(balance)

df["Risk$"] = risk_values
df["Profit$"] = profits
df["Balance"] = balances

# =========================
# EQUITY %
# =========================

df["ReturnPct"] = (
    (df["Balance"] - account_size)
    / account_size
) * 100

# =========================
# SHEET DRAWDOWN LOGIC
# =========================

df["PeakReturnPct"] = (
    df["ReturnPct"]
    .cummax()
)

df["DDFromPeakPct"] = (
    df["ReturnPct"]
    - df["PeakReturnPct"]
)

df["WorstDDFromPeakPct"] = (
    df["DDFromPeakPct"]
    .cummin()
)

# =========================
# MASTER DASHBOARD FILTER
# =========================

dashboard_df = df.copy()

if selected_year != "All Years":

    dashboard_df = dashboard_df[
        dashboard_df["EntryTime"]
        .dt.year.astype(str)
        == selected_year
    ].copy()

    # Recalculate equity engine for selected year only
    balance = account_size

    balances = []
    profits = []
    risk_values = []

    for r in dashboard_df["NetResultR"]:

        if risk_mode == "Fixed Dollar Amount":
            current_risk = risk_value

        else:
            current_risk = balance * (risk_value / 100)

        profit = r * current_risk
        balance += profit

        risk_values.append(current_risk)
        profits.append(profit)
        balances.append(balance)

    dashboard_df["Risk$"] = risk_values
    dashboard_df["Profit$"] = profits
    dashboard_df["Balance"] = balances

    dashboard_df["ReturnPct"] = (
        (dashboard_df["Balance"] - account_size)
        / account_size
    ) * 100

    dashboard_df["PeakReturnPct"] = (
        dashboard_df["ReturnPct"]
        .cummax()
    )

    dashboard_df["DDFromPeakPct"] = (
        dashboard_df["ReturnPct"]
        - dashboard_df["PeakReturnPct"]
    )

    dashboard_df["WorstDDFromPeakPct"] = (
        dashboard_df["DDFromPeakPct"]
        .cummin()
    )

# =========================
# CALCULATED COLUMNS
# =========================

# Trade Date

dashboard_df["TradeDateNY"] = (
    dashboard_df["EntryTimeNY"]
    .dt.date
)

# Week

iso = dashboard_df["EntryTimeNY"].dt.isocalendar()

dashboard_df["Week"] = (
    iso["year"].astype(str)
    + "-W"
    + iso["week"].astype(str).str.zfill(2)
)

# Month

dashboard_df["Month"] = (
    dashboard_df["EntryTimeNY"]
    .dt.strftime("%Y-%m")
)

# Quarter

dashboard_df["Quarter"] = (
    dashboard_df["EntryTimeNY"]
    .dt.year.astype(str)
    + "-Q"
    + dashboard_df["EntryTimeNY"]
        .dt.quarter.astype(str)
)

# Cumulative R

dashboard_df["CumulativeR"] = (
    dashboard_df["NetResultR"]
    .cumsum()
)

# Cumulative Profit $

dashboard_df["CumProfit"] = (
    dashboard_df["Profit$"]
    .cumsum()
)

# Cumulative Net R

dashboard_df["CumNetR"] = (
    dashboard_df["NetResultR"]
    .cumsum()
)

# Peak R

dashboard_df["PeakR"] = (
    dashboard_df["CumulativeR"]
    .cummax()
)

# Drawdown R From Peak

dashboard_df["DrawdownRFromPeak"] = (
    dashboard_df["CumulativeR"]
    - dashboard_df["PeakR"]
)

# Peak Profit $

dashboard_df["PeakProfitDollar"] = (
    dashboard_df["Profit$"]
    .cumsum()
    .cummax()
)

# Drawdown $ From Peak

dashboard_df["DrawdownDollarFromPeak"] = (
    dashboard_df["Profit$"]
    .cumsum()
    - dashboard_df["PeakProfitDollar"]
)

# =========================
# FORMAT HELPERS
# =========================

def format_dd(dd):

    if dd <= -9.0:
        return f"🚨 {dd:.2f}%"

    elif dd <= -7.5:
        return f"⚠️ {dd:.2f}%"

    else:
        return f"{dd:.2f}%"


def format_daily_dd(dd):

    if dd <= -4.0:
        return f"🚨 {dd:.2f}%"

    elif dd <= -3.0:
        return f"⚠️ {dd:.2f}%"

    else:
        return f"{dd:.2f}%"

# =========================
# SUMMARY TABLES
# =========================

# =========================
# MONTHLY BASE TABLE
# =========================

monthly_base = dashboard_df.copy()

daily_results_monthly = (
    monthly_base
    .groupby(["Month", "TradeDateNY"])
    ["Profit$"]
    .sum()
    .reset_index()
)

daily_results_monthly["DailyPct"] = (
    daily_results_monthly["Profit$"]
    / account_size
) * 100

daily_results_monthly["DailyPct"] = (
    daily_results_monthly["DailyPct"]
    .clip(upper=0)
)

monthly_max_daily_dd = (
    daily_results_monthly
    .groupby("Month")
    ["DailyPct"]
    .min()
    .reset_index()
)

monthly_max_daily_dd = (
    monthly_max_daily_dd.rename(
        columns={
            "DailyPct": "MaxDailyDDPct"
        }
    )
)

# =========================
# MONTHLY SUMMARY RAW
# =========================

monthly_summary_raw = (
    monthly_base
    .groupby("Month")
    .agg(
        TradingDays=("TradeDateNY", "nunique"),
        Trades=("TradeID", "count"),
        Wins=("NetResultR", lambda x: (x > 0.5).sum()),
        Losses=("NetResultR", lambda x: (x < -0.5).sum()),
        BE=("NetResultR", lambda x: ((x >= -0.5) & (x <= 0.5)).sum()),
        TotalR=("NetResultR", "sum"),
        TotalDollar=("Profit$", "sum"),
        MaxDDPct=("DDFromPeakPct", "min"),
        EndBalance=("Balance", "last")
    )
    .reset_index()
)

monthly_summary_raw["WinRate"] = (
    monthly_summary_raw["Wins"]
    /
    (
        monthly_summary_raw["Wins"]
        + monthly_summary_raw["Losses"]
    )
    * 100
).fillna(0)

monthly_summary_raw["MonthlyPct"] = (
    monthly_summary_raw["TotalDollar"]
    / account_size
    * 100
)

monthly_summary_raw["EndEquityPct"] = (
    monthly_summary_raw["EndBalance"]
    / account_size
) * 100

monthly_summary_raw = monthly_summary_raw.merge(
    monthly_max_daily_dd,
    on="Month",
    how="left"
)

# =========================
# QUARTERLY BASE TABLE
# =========================

quarterly_base = dashboard_df.copy()

daily_results_quarterly = (
    quarterly_base
    .groupby(["Quarter", "TradeDateNY"])
    ["Profit$"]
    .sum()
    .reset_index()
)

daily_results_quarterly["DailyPct"] = (
    daily_results_quarterly["Profit$"]
    / account_size
) * 100

daily_results_quarterly["DailyPct"] = (
    daily_results_quarterly["DailyPct"]
    .clip(upper=0)
)

quarterly_max_daily_dd = (
    daily_results_quarterly
    .groupby("Quarter")
    ["DailyPct"]
    .min()
    .reset_index()
)

quarterly_max_daily_dd = (
    quarterly_max_daily_dd.rename(
        columns={
            "DailyPct": "MaxDailyDDPct"
        }
    )
)

# =========================
# QUARTERLY SUMMARY RAW
# =========================

quarterly_summary_raw = (
    quarterly_base
    .groupby("Quarter")
    .agg(
        TradingDays=("TradeDateNY", "nunique"),
        Trades=("TradeID", "count"),
        Wins=("NetResultR", lambda x: (x > 0.5).sum()),
        Losses=("NetResultR", lambda x: (x < -0.5).sum()),
        BE=("NetResultR", lambda x: ((x >= -0.5) & (x <= 0.5)).sum()),
        TotalR=("NetResultR", "sum"),
        TotalDollar=("Profit$", "sum"),
        MaxDDPct=("DDFromPeakPct", "min"),
        EndBalance=("Balance", "last")
    )
    .reset_index()
)

quarterly_summary_raw["WinRate"] = (
    quarterly_summary_raw["Wins"]
    /
    (
        quarterly_summary_raw["Wins"]
        + quarterly_summary_raw["Losses"]
    )
    * 100
).fillna(0)

quarterly_summary_raw["QuarterlyPct"] = (
    quarterly_summary_raw["TotalDollar"]
    / account_size
    * 100
)

quarterly_summary_raw["EndEquityPct"] = (
    quarterly_summary_raw["EndBalance"]
    / account_size
) * 100

quarterly_summary_raw = quarterly_summary_raw.merge(
    quarterly_max_daily_dd,
    on="Quarter",
    how="left"
)

# =========================
# WEEKLY BASE TABLE
# =========================

weekly_base = dashboard_df.copy()

daily_results_weekly = (
    weekly_base
    .groupby(["Week", "TradeDateNY"])
    ["Profit$"]
    .sum()
    .reset_index()
)

daily_results_weekly["DailyPct"] = (
    daily_results_weekly["Profit$"]
    / account_size
) * 100

daily_results_weekly["DailyPct"] = (
    daily_results_weekly["DailyPct"]
    .clip(upper=0)
)

weekly_max_daily_dd = (
    daily_results_weekly
    .groupby("Week")
    ["DailyPct"]
    .min()
    .reset_index()
)

weekly_max_daily_dd = (
    weekly_max_daily_dd.rename(
        columns={
            "DailyPct": "MaxDailyDDPct"
        }
    )
)

# =========================
# WEEKLY SUMMARY RAW
# =========================

weekly_summary_raw = (
    weekly_base
    .groupby("Week")
    .agg(
        TradingDays=("TradeDateNY", "nunique"),
        Trades=("TradeID", "count"),
        Wins=("NetResultR", lambda x: (x > 0.5).sum()),
        Losses=("NetResultR", lambda x: (x < -0.5).sum()),
        BE=("NetResultR", lambda x: ((x >= -0.5) & (x <= 0.5)).sum()),
        TotalR=("NetResultR", "sum"),
        TotalDollar=("Profit$", "sum"),
        MaxDDPct=("DDFromPeakPct", "min"),
        EndBalance=("Balance", "last")
    )
    .reset_index()
)

weekly_start_dates = (
    weekly_base
    .groupby("Week")
    ["TradeDateNY"]
    .min()
    .reset_index()
    .rename(
        columns={
            "TradeDateNY": "Week Start Date"
        }
    )
)

weekly_summary_raw = (
    weekly_summary_raw
    .merge(
        weekly_start_dates,
        on="Week",
        how="left"
    )
)

weekly_summary_raw["WinRate"] = (
    weekly_summary_raw["Wins"]
    /
    (
        weekly_summary_raw["Wins"]
        + weekly_summary_raw["Losses"]
    )
    * 100
).fillna(0)

weekly_summary_raw["WeeklyPct"] = (
    weekly_summary_raw["TotalDollar"]
    / account_size
    * 100
)

weekly_summary_raw["EndEquityPct"] = (
    weekly_summary_raw["EndBalance"]
    / account_size
) * 100

weekly_summary_raw = weekly_summary_raw.merge(
    weekly_max_daily_dd,
    on="Week",
    how="left"
)

# =========================
# DAILY SUMMARY RAW
# =========================

daily_summary_raw = (
    dashboard_df
    .groupby("TradeDateNY")
    .agg(
        Trades=("TradeID", "count"),
        Wins=("NetResultR", lambda x: (x > 0.5).sum()),
        Losses=("NetResultR", lambda x: (x < -0.5).sum()),
        BE=("NetResultR", lambda x: ((x >= -0.5) & (x <= 0.5)).sum()),
        TotalR=("NetResultR", "sum"),
        TotalDollar=("Profit$", "sum"),
        EndBalance=("Balance", "last"),
        MaxDDPct=("DDFromPeakPct", "min")
    )
    .reset_index()
)

daily_summary_raw["WinRate"] = (
    daily_summary_raw["Wins"]
    /
    (
        daily_summary_raw["Wins"]
        + daily_summary_raw["Losses"]
    )
    * 100
).fillna(0)

daily_summary_raw["DailyPct"] = (
    daily_summary_raw["TotalDollar"]
    / account_size
    * 100
)

daily_summary_raw["MaxDailyDDPct"] = (
    daily_summary_raw["DailyPct"]
    .clip(upper=0)
)

daily_summary_raw["EndEquityPct"] = (
    daily_summary_raw["EndBalance"]
    / account_size
    * 100
)

# =========================
# YEARLY BASE TABLE
# =========================

yearly_base = dashboard_df.copy()

yearly_base["Year"] = (
    yearly_base["EntryTimeNY"]
    .dt.year.astype(str)
)

daily_results_yearly = (
    yearly_base
    .groupby(["Year", "TradeDateNY"])
    ["Profit$"]
    .sum()
    .reset_index()
)

daily_results_yearly["DailyPct"] = (
    daily_results_yearly["Profit$"]
    / account_size
) * 100

daily_results_yearly["DailyPct"] = (
    daily_results_yearly["DailyPct"]
    .clip(upper=0)
)

yearly_max_daily_dd = (
    daily_results_yearly
    .groupby("Year")
    ["DailyPct"]
    .min()
    .reset_index()
)

yearly_max_daily_dd = (
    yearly_max_daily_dd.rename(
        columns={
            "DailyPct": "MaxDailyDDPct"
        }
    )
)

# =========================
# YEARLY SUMMARY RAW
# =========================

yearly_summary_raw = (
    yearly_base
    .groupby("Year")
    .agg(
        TradingDays=("TradeDateNY", "nunique"),
        Trades=("TradeID", "count"),
        Wins=("NetResultR", lambda x: (x > 0.5).sum()),
        Losses=("NetResultR", lambda x: (x < -0.5).sum()),
        BE=("NetResultR", lambda x: ((x >= -0.5) & (x <= 0.5)).sum()),
        TotalR=("NetResultR", "sum"),
        TotalDollar=("Profit$", "sum"),
        MaxDDPct=("DDFromPeakPct", "min"),
        EndBalance=("Balance", "last")
    )
    .reset_index()
)

yearly_summary_raw["WinRate"] = (
    yearly_summary_raw["Wins"]
    /
    (
        yearly_summary_raw["Wins"]
        + yearly_summary_raw["Losses"]
    )
    * 100
).fillna(0)

yearly_summary_raw["YearlyPct"] = (
    yearly_summary_raw["TotalDollar"]
    / account_size
    * 100
)

yearly_summary_raw["EndEquityPct"] = (
    yearly_summary_raw["EndBalance"]
    / account_size
) * 100

yearly_summary_raw = yearly_summary_raw.merge(
    yearly_max_daily_dd,
    on="Year",
    how="left"
)

# =========================
# DASHBOARD METRICS
# =========================

# -------------------------
# TRADE METRICS
# -------------------------

# Trading Days

trading_days = (
    dashboard_df["EntryTimeNY"]
    .dt.date
    .nunique()
)

# Trade Counts

total_trades = len(dashboard_df)

wins = (
    dashboard_df["NetResultR"] > 0.5
).sum()

losses = (
    dashboard_df["NetResultR"] < -0.5
).sum()

breakeven = (
    (
        dashboard_df["NetResultR"] >= -0.5
    )
    &
    (
        dashboard_df["NetResultR"] <= 0.5
    )
).sum()

be = breakeven

# Win Rate

win_rate = (
    wins
    /
    (wins + losses)
    * 100
) if (wins + losses) > 0 else 0

# Total Net R

total_net_r = (
    dashboard_df["NetResultR"]
    .sum()
)

# -------------------------
# STRATEGY QUALITY METRICS
# -------------------------

# Profit Factor

gross_profit = (
    dashboard_df.loc[
        dashboard_df["NetResultR"] > 0,
        "NetResultR"
    ]
    .sum()
)

gross_loss = abs(
    dashboard_df.loc[
        dashboard_df["NetResultR"] < 0,
        "NetResultR"
    ]
    .sum()
)

profit_factor = (
    gross_profit / gross_loss
    if gross_loss > 0
    else 0
)
profit_factor_r = profit_factor

# Expectancy

expectancy = (
    total_net_r
    / total_trades
    if total_trades > 0
    else 0
)
expectancy_r = expectancy

# Monthly Analytics

monthly_returns = monthly_summary_raw["MonthlyPct"]

avg_monthly_return = (
    monthly_returns.mean()
    if len(monthly_returns) > 0
    else 0
)

monthly_volatility = (
    monthly_returns.std()
    if len(monthly_returns) > 0
    else 0
)

profitable_months_pct = (
    (
        monthly_returns > 0
    ).mean()
    * 100
    if len(monthly_returns) > 0
    else 0
)

# =========================
# PROP FIRM METRICS
# =========================

# Peak-to-Peak DD %

peak_to_peak_dd_pct = (
    dashboard_df["DDFromPeakPct"]
    .min()
)

# Peak-to-Peak DD in R

peak_to_peak_dd_r = (
    dashboard_df["DrawdownRFromPeak"]
    .min()
)

# Peak-to-Peak DD in $

peak_to_peak_dd_dollar = (
    dashboard_df["DrawdownDollarFromPeak"]
    .min()
)

# Worst Daily DD

daily_profit = (
    dashboard_df
    .groupby(
        dashboard_df["TradeDateNY"]
    )["Profit$"]
    .sum()
)

worst_daily_dd_pct = (
    daily_profit.min()
    / account_size
    * 100
)

worst_daily_dd_dollar = (
    worst_daily_dd_pct
    / 100
    * account_size
)

worst_daily_dd_r = (
    worst_daily_dd_dollar
    / current_risk_per_r
    if current_risk_per_r > 0
    else 0
)

# =========================
# # DRAWDOWN METRICS
# =========================

daily_equity = (
    dashboard_df
    .groupby(
        dashboard_df["EntryTimeNY"].dt.date
    )["Profit$"]
    .sum()
    .reset_index()
)

daily_equity.columns = [
    "Date",
    "DailyProfit"
]

daily_equity["DailyReturnPct"] = (
    daily_equity["DailyProfit"]
    / account_size
    * 100
)

daily_equity["DailyEquityPct"] = (
    daily_equity["DailyReturnPct"]
    .cumsum()
)

daily_equity["PeakEquityPct"] = (
    daily_equity["DailyEquityPct"]
    .cummax()
)

daily_equity["DrawdownDurationDays"] = 0

current_duration = 0

for i in range(len(daily_equity)):

    if (
        daily_equity.loc[i, "DailyEquityPct"]
        <
        daily_equity.loc[i, "PeakEquityPct"]
    ):

        current_duration += 1

    else:

        current_duration = 0

    daily_equity.loc[
        i,
        "DrawdownDurationDays"
    ] = current_duration

max_dd_duration_days = (
    daily_equity["DrawdownDurationDays"]
    .max()
)

completed_dds = []

for i in range(
    len(daily_equity) - 1
):

    current_dd = (
        daily_equity.loc[
            i,
            "DrawdownDurationDays"
        ]
    )

    next_dd = (
        daily_equity.loc[
            i + 1,
            "DrawdownDurationDays"
        ]
    )

    if (
        current_dd > 0
        and
        next_dd == 0
    ):

        completed_dds.append(
            current_dd
        )

avg_dd_duration_days = (
    sum(completed_dds)
    / len(completed_dds)
    if len(completed_dds) > 0
    else 0
)

# =========================
# CURRENT DD DURATION
# =========================

current_dd_duration_days = (
    daily_equity["DrawdownDurationDays"]
    .iloc[-1]
)

# Calendar-Day Durations

completed_dd_calendar = []

dd_start_date = None

for i in range(len(daily_equity)):

    current_dd = daily_equity.loc[
        i,
        "DrawdownDurationDays"
    ]

    if current_dd == 1:

        dd_start_date = daily_equity.loc[
            i,
            "Date"
        ]

    if (
        current_dd > 0
        and
        i < len(daily_equity) - 1
        and
        daily_equity.loc[
            i + 1,
            "DrawdownDurationDays"
        ] == 0
    ):

        dd_end_date = daily_equity.loc[
            i,
            "Date"
        ]

        completed_dd_calendar.append(
            (
                dd_end_date
                - dd_start_date
            ).days
            + 1
        )
    
# =========================
# CURRENT CALENDAR DD
# =========================

current_dd_calendar_days = 0

if current_dd_duration_days > 0:

    current_dd_start = None

    for i in range(len(daily_equity) - 1, -1, -1):

        if daily_equity.loc[i, "DrawdownDurationDays"] == 1:

            current_dd_start = daily_equity.loc[i, "Date"]
            break

    if current_dd_start is not None:

        current_dd_calendar_days = (
            daily_equity["Date"].iloc[-1]
            - current_dd_start
        ).days + 1


# =========================
# HISTORICAL CALENDAR DD
# =========================

if len(completed_dd_calendar) > 0:

    max_dd_calendar_days = max(completed_dd_calendar)

    avg_dd_calendar_days = (
        sum(completed_dd_calendar)
        / len(completed_dd_calendar)
    )

else:

    max_dd_calendar_days = 0
    avg_dd_calendar_days = 0


max_dd_calendar_weeks = (
    max_dd_calendar_days
    / 7
)

avg_dd_calendar_weeks = (
    avg_dd_calendar_days
    / 7
)

# =========================
# CURRENT PEAK-TO-PEAK DD
# =========================

current_dd_r = (
    dashboard_df["DrawdownRFromPeak"]
    .iloc[-1]
)

current_dd_pct = (
    dashboard_df["DDFromPeakPct"]
    .iloc[-1]
)

current_dd_dollar = (
    dashboard_df["DrawdownDollarFromPeak"]
    .iloc[-1]
)

# Last Equity Peak Date

last_equity_peak_date = None

if current_dd_r < 0:

    peak_row = dashboard_df[
        dashboard_df["DrawdownRFromPeak"] == 0
    ].index.max()

    if pd.notna(peak_row):

        peak_date = (
            dashboard_df.loc[
                peak_row,
                "EntryTimeNY"
            ]
            .date()
        )

        day = peak_date.day

        if 10 <= day % 100 <= 20:
            suffix = "th"
        else:
            suffix = {
                1: "st",
                2: "nd",
                3: "rd"
            }.get(day % 10, "th")

        last_equity_peak_date = (
            f"{day}{suffix} "
            f"{peak_date.strftime('%B %Y')}"
        )

# =========================
# CURRENT LOSS STREAK
# =========================

current_loss_streak_trades = 0
current_loss_streak_r = 0
current_loss_streak_dollar = 0

for i in range(
    len(dashboard_df) - 1,
    -1,
    -1
):

    trade_r = dashboard_df.iloc[i]["NetResultR"]

    # WIN beendet Serie

    if trade_r > 0.5:
        break

    # LOSS zählt

    if trade_r < -0.5:

        current_loss_streak_trades += 1
        current_loss_streak_r += trade_r
        current_loss_streak_dollar += dashboard_df.iloc[i]["Profit$"]

# Prozent aus echtem Dollar-Verlust berechnen

current_loss_streak_pct = (
    current_loss_streak_dollar
    / account_size
    * 100
)

# =========================
# CURRENT LOSS STREAK DAYS
# =========================

current_loss_streak_days = 0
current_loss_streak_start_date = None

if current_loss_streak_trades > 0:

    loss_dates = []
    streak_trade_dates = []

    for i in range(
        len(dashboard_df) - 1,
        -1,
        -1
    ):

        trade_r = dashboard_df.iloc[i]["NetResultR"]

        if trade_r > 0.5:
            break

        trade_date = (
            dashboard_df.iloc[i]["EntryTimeNY"]
            .date()
        )

        loss_dates.append(trade_date)
        streak_trade_dates.append(trade_date)

    current_loss_streak_days = len(
        set(loss_dates)
    )

    start_date = min(streak_trade_dates)

    day = start_date.day

    if 10 <= day % 100 <= 20:
        suffix = "th"
    else:
        suffix = {
            1: "st",
            2: "nd",
            3: "rd"
        }.get(day % 10, "th")

    current_loss_streak_start_date = (
        f"{day}{suffix} "
        f"{start_date.strftime('%B %Y')}"
    )

current_loss_streak_weeks = (
    current_loss_streak_days
    / 5
)

# =========================
# BEST / WORST PERIODS
# =========================

# Day

best_day_r = (
    daily_summary_raw["TotalR"]
    .max()
)

worst_day_r = (
    daily_summary_raw["TotalR"]
    .min()
)

best_day_dollar = (
    daily_summary_raw.loc[
        daily_summary_raw["TotalR"].idxmax(),
        "TotalDollar"
    ]
)

worst_day_dollar = (
    daily_summary_raw.loc[
        daily_summary_raw["TotalR"].idxmin(),
        "TotalDollar"
    ]
)

best_day_pct = (
    best_day_dollar
    / account_size
    * 100
)

worst_day_pct = (
    worst_day_dollar
    / account_size
    * 100
)

# Week

best_week_r = (
    weekly_summary_raw["TotalR"]
    .max()
)

worst_week_r = (
    weekly_summary_raw["TotalR"]
    .min()
)

best_week_dollar = (
    weekly_summary_raw.loc[
        weekly_summary_raw["TotalR"].idxmax(),
        "TotalDollar"
    ]
)

worst_week_dollar = (
    weekly_summary_raw.loc[
        weekly_summary_raw["TotalR"].idxmin(),
        "TotalDollar"
    ]
)

best_week_pct = (
    best_week_dollar
    / account_size
    * 100
)

worst_week_pct = (
    worst_week_dollar
    / account_size
    * 100
)

# Month

best_month_r = (
    monthly_summary_raw["TotalR"]
    .max()
)

worst_month_r = (
    monthly_summary_raw["TotalR"]
    .min()
)

best_month_dollar = (
    monthly_summary_raw.loc[
        monthly_summary_raw["TotalR"].idxmax(),
        "TotalDollar"
    ]
)

worst_month_dollar = (
    monthly_summary_raw.loc[
        monthly_summary_raw["TotalR"].idxmin(),
        "TotalDollar"
    ]
)

best_month_pct = (
    best_month_dollar
    / account_size
    * 100
)

worst_month_pct = (
    worst_month_dollar
    / account_size
    * 100
)

# Quarter

best_quarter_r = (
    quarterly_summary_raw["TotalR"]
    .max()
)

worst_quarter_r = (
    quarterly_summary_raw["TotalR"]
    .min()
)

best_quarter_dollar = (
    quarterly_summary_raw.loc[
        quarterly_summary_raw["TotalR"].idxmax(),
        "TotalDollar"
    ]
)

worst_quarter_dollar = (
    quarterly_summary_raw.loc[
        quarterly_summary_raw["TotalR"].idxmin(),
        "TotalDollar"
    ]
)

best_quarter_pct = (
    best_quarter_dollar
    / account_size
    * 100
)

worst_quarter_pct = (
    worst_quarter_dollar
    / account_size
    * 100
)

# =========================
# DASHBOARD UI
# =========================

st.title("Trading Analytics Dashboard")

overview1, overview2, overview3, overview4 = st.columns(4)

with overview1:

    st.markdown(
        """
        <div style="font-size:12px;">
            Strategy
        </div>
        <div style="font-size:22px;">
            NAS_ORB_V1
        </div>
        """,
        unsafe_allow_html=True
    )

with overview2:

    st.markdown(
        """
        <div style="font-size:12px;">
            Trade Window
        </div>
        <div style="font-size:22px;">
            09:45–12:00 NY
        </div>
        """,
        unsafe_allow_html=True
    )

with overview3:

    st.markdown(
        f"""
        <div style="font-size:12px;">
            Start Date
        </div>
        <div style="font-size:22px;">
            {dashboard_df['EntryTimeNY'].min().strftime('%d %b %Y')}
        </div>
        """,
        unsafe_allow_html=True
    )

with overview4:

    st.markdown(
        f"""
        <div style="font-size:12px;">
            Last Recorded Trade
        </div>
        <div style="font-size:22px;">
            {dashboard_df['EntryTimeNY'].max().strftime('%d %b %Y')}
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown("---")

ending_balance = (
    dashboard_df["Balance"]
    .iloc[-1]
)

total_gain_dollar = (
    ending_balance
    - account_size
)

total_return_pct = (
    total_gain_dollar
    / account_size
    * 100
)

max_drawdown_pct = (
    dashboard_df["DDFromPeakPct"]
    .min()
)

if max_drawdown_pct <= -9:

    dd_status = "🚨"

elif max_drawdown_pct <= -7.5:

    dd_status = "⚠️"

else:

    dd_status = "✅"



# =========================
# PERFORMANCE
# =========================

st.markdown("### PERFORMANCE")

p1, p2, p3, p4, p5 = st.columns(5)

p1.metric(
    "Total Net R",
    f"{total_net_r:.2f}R"
)

p2.metric(
    "Account Return %",
    f"{total_return_pct:.2f}%"
)

p3.metric(
    "Total Profit $",
    f"${total_gain_dollar:,.0f}"
)

p4.metric(
    "Ending Balance",
    f"${ending_balance:,.0f}"
)

with p5:

    st.markdown(
        """
        <div style="font-size:14px;">
            Peak-to-Peak DD %
        </div>
        """,
        unsafe_allow_html=True
    )

    dd_color = (
        "red"
        if max_drawdown_pct <= -7.5
        else "inherit"
    )

    st.markdown(
        f"""
        <div style="
            font-size:36px;
            font-weight:400;
            color:{dd_color};
            line-height:1.2;
        ">
            {dd_status} {max_drawdown_pct:.2f}%
        </div>
        """,
        unsafe_allow_html=True
    )

left_stats, right_stats = st.columns(2)

# =========================
# TRADE STATS
# =========================

with left_stats:

    st.markdown(
        """
        <div style="
            font-size:28px;
            font-weight:700;
            color:#8c8f99;
            margin-bottom:20px;
        ">
            TRADE STATS
        </div>
        """,
        unsafe_allow_html=True
    )

    row1_col1, row1_col2, row1_col3, spacer = st.columns([2, 2, 2, 1])

    with row1_col1:
        st.markdown(
            f"""
            <div style="line-height:1.1;">
                <div style="font-size:14px;">
                    Trading Days
                </div>
                <div style="font-size:36px; font-weight:600; color:#8c8f99;">
                    {trading_days}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with row1_col2:
        st.markdown(
            f"""
            <div style="line-height:1.1;">
                <div style="font-size:14px;">
                    Total Trades
                </div>
                <div style="font-size:36px; font-weight:600; color:#8c8f99;">
                    {total_trades}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with row1_col3:
        st.markdown(
            f"""
            <div style="line-height:1.1;">
                <div style="font-size:14px;">
                    Win Rate
                </div>
                <div style="font-size:36px; font-weight:600; color:#8c8f99;">
                    {win_rate:.2f}%
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    row2_col1, row2_col2, row2_col3, spacer = st.columns([2, 2, 2, 1])

    with row2_col1:
        st.markdown(
            f"""
            <div style="line-height:1.1;">
                <div style="font-size:14px;">
                    Wins
                </div>
                <div style="font-size:36px; font-weight:600; color:#8c8f99;">
                    {wins}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with row2_col2:
        st.markdown(
            f"""
            <div style="line-height:1.1;">
                <div style="font-size:14px;">
                    Losses
                </div>
                <div style="font-size:36px; font-weight:600; color:#8c8f99;">
                    {losses}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with row2_col3:
        st.markdown(
            f"""
            <div style="line-height:1.1;">
                <div style="font-size:14px;">
                    BE
                </div>
                <div style="font-size:36px; font-weight:600; color:#8c8f99;">
                    {be}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

# =========================
# STRATEGY QUALITY
# =========================

with right_stats:

    st.markdown(
        """
        <div style="
            font-size:28px;
            font-weight:700;
            color:#8c8f99;
            margin-bottom:20px;
        ">
            STRATEGY QUALITY
        </div>
        """,
        unsafe_allow_html=True
    )

    row1_col1, row1_col2, spacer = st.columns([2, 2, 3])

    with row1_col1:
        st.markdown(
            f"""
            <div style="line-height:1.1;">
                <div style="font-size:14px;">
                    Profit Factor
                </div>
                <div style="font-size:36px; font-weight:600; color:#8c8f99;">
                    {profit_factor:.2f}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with row1_col2:
        st.markdown(
            f"""
            <div style="line-height:1.1;">
                <div style="font-size:14px;">
                    Expectancy
                </div>
                <div style="font-size:36px; font-weight:600; color:#8c8f99;">
                    {expectancy_r:.2f}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    row2_col1, row2_col2, row2_col3, spacer = st.columns([2, 2, 2, 1])

    with row2_col1:
        st.markdown(
            f"""
            <div style="line-height:1.1;">
                <div style="font-size:14px;">
                    Avg Monthly
                </div>
                <div style="font-size:36px; font-weight:600; color:#8c8f99;">
                    {avg_monthly_return:.2f}%
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with row2_col2:
        st.markdown(
            f"""
            <div style="line-height:1.1;">
                <div style="font-size:14px;">
                    Monthly Vol
                </div>
                <div style="font-size:36px; font-weight:600; color:#8c8f99;">
                    {monthly_volatility:.2f}%
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    with row2_col3:
        st.markdown(
            f"""
            <div style="line-height:1.1;">
                <div style="font-size:14px;">
                    Profitable Mths
                </div>
                <div style="font-size:36px; font-weight:600; color:#8c8f99;">
                    {profitable_months_pct:.1f}%
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )


st.markdown("---")

if selected_year == "All Years":

    # =========================
    # CURRENT STATE
    # =========================

    st.markdown("### CURRENT STATE")

    cs_left, cs_right = st.columns(2)

    with cs_left:

        st.markdown(
            """
            <div style="font-size:16px;">
                Current Peak-to-Peak DD
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            f"""
            <div style="font-size:32px;">
                {current_dd_r:.2f}R
                &nbsp;&nbsp;&nbsp;
                {current_dd_pct:.2f}%
                &nbsp;&nbsp;&nbsp;
                ${current_dd_dollar:,.0f}
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown(
            """
            <div style="font-size:16px;">
                Last Equity Peak Date
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            f"""
            <div style="font-size:32px;">
                {last_equity_peak_date}
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown(
            """
            <div style="font-size:16px;">
                Current Peak-to-Peak DD Duration
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            f"""
            <div style="font-size:32px;">
                {current_dd_duration_days:.0f} Trading Days / {current_dd_duration_days / 5:.1f} Weeks
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown(
            """
            <div style="font-size:16px;">
                Current Calendar DD Duration
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            f"""
            <div style="font-size:32px;">
                {current_dd_calendar_days:.0f} Calendar Days / {current_dd_calendar_days / 7:.1f} Weeks
            </div>
            """,
            unsafe_allow_html=True
        )

    with cs_right:

        st.markdown(
            """
            <div style="font-size:16px;">
                Current Loss Streak
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            f"""
            <div style="font-size:32px;">
                {current_loss_streak_trades} Trades
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown(
            """
            <div style="font-size:16px;">
                Current Loss Streak Start Date
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            f"""
            <div style="font-size:32px;">
                {current_loss_streak_start_date}
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown(
            """
            <div style="font-size:16px;">
                Current Loss Streak Values
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            f"""
            <div style="font-size:32px;">
                {current_loss_streak_r:.2f}R
                &nbsp;&nbsp;&nbsp;
                {current_loss_streak_pct:.2f}%
                &nbsp;&nbsp;&nbsp;
                ${current_loss_streak_dollar:,.0f}
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown(
            """
            <div style="font-size:16px;">
                Current Loss Streak Duration
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            f"""
            <div style="font-size:32px;">
                {current_loss_streak_days} Trading Days / {current_loss_streak_weeks:.1f} Weeks
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown(
        "<div style='height:40px'></div>",
        unsafe_allow_html=True
    )

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(
    [
        "MASTER",
        "Yearly",
        "Quarterly",
        "Monthly",
        "Weekly",
        "Daily",
        "All Trades"
    ]
)


with tab1:

    st.subheader("Account Growth (%)")

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=dashboard_df.index,
            y=dashboard_df["ReturnPct"],
            mode="lines",
            name="Growth %",
            customdata=list(
                zip(
                    dashboard_df["EntryTimeNY"],
                    dashboard_df["CumNetR"],
                    dashboard_df["CumProfit"],
                    dashboard_df["Balance"]
                )
            ),
            hovertemplate=
            "<b>%{customdata[0]|%d %b %Y}</b><br><br>" +
            "<b>Trade %{x}</b><br>" +
            "Return: %{y:.2f}%<br>" +
            "Net R: %{customdata[1]:.2f}R<br>" +
            "Profit: $%{customdata[2]:,.0f}<br>" +
            "Balance: $%{customdata[3]:,.0f}<br>" +
            "<extra></extra>"
        )
    )

    # =========================
    # DD WARNING MARKERS
    # =========================

    warning_points = []
    danger_points = []

    was_warning = False
    was_danger = False

    for i in range(len(dashboard_df)):

        dd = dashboard_df.iloc[i]["DDFromPeakPct"]

        # Danger Zone (Red)

        if dd <= -8.5:

            if not was_danger:

                danger_points.append(i)

            was_danger = True
            was_warning = True

        # Warning Zone (Orange)

        elif dd <= -7.5:

            if not was_warning:

                warning_points.append(i)

            was_warning = True
            was_danger = False

        else:

            was_warning = False
            was_danger = False


    warning_df = dashboard_df.loc[warning_points]

    danger_df = dashboard_df.loc[danger_points]

    fig.add_trace(
        go.Scatter(
            x=warning_df.index,
            y=warning_df["ReturnPct"],
            mode="markers",
            name="DD ≥ 7.5%",
            marker=dict(
                color="orange",
                size=10
            ),
            hovertemplate=
            "<b>Warning Drawdown</b><br>" +
            "Peak-to-Peak DD ≥ 7.5%<br>" +
            "<extra></extra>"
        )
    )

    fig.add_trace(
        go.Scatter(
            x=danger_df.index,
            y=danger_df["ReturnPct"],
            mode="markers",
            name="DD ≥ 8.5%",
            marker=dict(
                color="red",
                size=10
            ),
            hovertemplate=
            "<b>Danger Drawdown</b><br>" +
            "Peak-to-Peak DD ≥ 8.5%<br>" +
            "<extra></extra>"
        )
    )

    fig.update_layout(
        height=500,
        hovermode="x unified",
        xaxis_title="Date",
        yaxis_title="Return %",
    )
    fig.update_yaxes(
        ticksuffix="%"
    )

    if selected_year == "All Years":

        year_starts = (
            dashboard_df
            .groupby(
                dashboard_df["EntryTimeNY"].dt.year
            )
            .head(1)
        )

        fig.update_xaxes(
            tickvals=year_starts.index,
            ticktext=year_starts["EntryTimeNY"]
                .dt.year.astype(str)
        )

    else:

        month_starts = (
                dashboard_df
                .groupby(
                    dashboard_df["EntryTimeNY"].dt.month
                )
                .head(1)
            )

        fig.update_xaxes(
                tickvals=month_starts.index,
                ticktext=month_starts["EntryTimeNY"]
                    .dt.strftime("%b")
            )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    st.markdown("---")

    # =========================
    # Best Day vs. Worst Day
    # =========================

    st.subheader("Best Day vs. Worst Day")

    # Best / Worst Day

    best_day_r_ui = best_day_r
    worst_day_r_ui = worst_day_r

    best_day_dollar_ui = best_day_dollar
    worst_day_dollar_ui = worst_day_dollar

    best_day_pct_ui = best_day_pct
    worst_day_pct_ui = worst_day_pct

    # DISPLAY

    header1, header2, header3 = st.columns([2, 3, 3])

    header1.markdown(
        "<div style='font-size:24px;'>Metric</div>",
        unsafe_allow_html=True
    )

    header2.markdown(
        "<div style='font-size:24px;'>🏆 Best</div>",
        unsafe_allow_html=True
    )

    header3.markdown(
        "<div style='font-size:24px;'>🔻 Worst</div>",
        unsafe_allow_html=True
    )

    c1, c2, c3 = st.columns([2, 3, 3])

    c1.write("")

    c2_1, c2_2, c2_3 = c2.columns(3)
    c2_1.markdown("**R Value**")
    c2_2.markdown("**Percent %**")
    c2_3.markdown("**Dollar $**")

    c3_1, c3_2, c3_3 = c3.columns(3)
    c3_1.markdown("**R Value**")
    c3_2.markdown("**Percent %**")
    c3_3.markdown("**Dollar $**")

    for metric, best_r, best_pct, best_dollar, worst_r, worst_pct, worst_dollar in [

        (
            "Day",
            best_day_r,
            best_day_pct,
            best_day_dollar,
            worst_day_r,
            worst_day_pct,
            worst_day_dollar
        ),

        (
            "Week",
            best_week_r,
            best_week_pct,
            best_week_dollar,
            worst_week_r,
            worst_week_pct,
            worst_week_dollar
        ),

        (
            "Month",
            best_month_r,
            best_month_pct,
            best_month_dollar,
            worst_month_r,
            worst_month_pct,
            worst_month_dollar
        ),

        (
            "Quarter",
            best_quarter_r,
            best_quarter_pct,
            best_quarter_dollar,
            worst_quarter_r,
            worst_quarter_pct,
            worst_quarter_dollar
        ),

    ]:

        c1, c2, c3 = st.columns([2, 3, 3])

        c1.write(metric)

        c2_1, c2_2, c2_3 = c2.columns(3)

        c2_1.write(f"{best_r:+.2f}R")
        c2_2.write(f"{best_pct:+.2f}%")
        c2_3.write(f"${best_dollar:,.0f}")

        c3_1, c3_2, c3_3 = c3.columns(3)

        c3_1.write(f"{worst_r:+.2f}R")
        c3_2.write(f"{worst_pct:+.2f}%")
        c3_3.write(f"${worst_dollar:,.0f}")

    # =========================
    # Prop Firm Compliance
    # =========================

    st.markdown("---")
    st.subheader("Prop Firm Compliance")

    peak_to_peak_dd = peak_to_peak_dd_pct

    def format_peak_dd(dd):

        if dd <= -9.0:
            return f"🚨 {dd:.2f}%", "red"

        elif dd <= -7.5:
            return f"⚠️ {dd:.2f}%", "red"

        else:
            return f"{dd:.2f}%", "black"
        
    peak_dd_text, peak_dd_color = (
        format_peak_dd(peak_to_peak_dd)
    )


    def format_ftmo_daily_dd(dd):

        if dd <= -4.0:
            return f"🚨 {dd:.2f}%"

        elif dd <= -3.5:
            return f"⚠️ {dd:.2f}%"

        else:
            return f"{dd:.2f}%"

    header1, header2, header3, header4 = st.columns([3, 1, 1, 1])

    header1.markdown("**Metric**")
    header2.markdown("**R Value**")
    header3.markdown("**Percent %**")
    header4.markdown("**Dollar $**")

    c1, c2, c3, c4 = st.columns([3, 1, 1, 1])

    c1.write("10%: Worst Peak-to-Peak DD")
    c2.write(f"{peak_to_peak_dd_r:.2f}R")
    c3.markdown(
        f"""
        <span style="color:{peak_dd_color};">
            {peak_dd_text}
        </span>
        """,
        unsafe_allow_html=True
    )
    c4.write(f"${peak_to_peak_dd_dollar:,.0f}")

    c1, c2, c3, c4 = st.columns([3, 1, 1, 1])

    c1.write("5%: Worst Daily DD")
    c2.write(f"{worst_daily_dd_r:.2f}R")
    c3.write(format_ftmo_daily_dd(worst_daily_dd_pct))
    c4.write(f"${worst_daily_dd_dollar:,.0f}")

    # =========================
    # HISTORICAL DRAWDOWN TIME
    # =========================

    st.markdown("---")
    st.subheader("Historical Drawdown Time")

    d1, d2 = st.columns(2)

    with d1:

        st.metric(
            "Max DD Duration",
            f"{max_dd_duration_days:.0f} Trading Days"
        )

        st.caption(
            f"{max_dd_calendar_days:.0f} Calendar Days / "
            f"{max_dd_calendar_weeks:.1f} Calendar Weeks"
        )

    with d2:

        st.metric(
            "Average DD Duration",
            f"{avg_dd_duration_days:.1f} Trading Days"
        )

        st.caption(
            f"{avg_dd_calendar_days:.1f} Calendar Days / "
            f"{avg_dd_calendar_weeks:.1f} Calendar Weeks"
        )

    # =========================
    # DRAWDOWN CURVE
    # =========================

    st.markdown("---")
    st.subheader("Drawdown (%)")

    fig_dd = go.Figure()

    fig_dd.add_trace(
        go.Scatter(
            x=dashboard_df["EntryTimeNY"],
            y=dashboard_df["DDFromPeakPct"],
            mode="lines",
            name="Peak-to-Peak Drawdown %",
            customdata=list(
                zip(
                    dashboard_df["TradeID"],
                    dashboard_df["DrawdownRFromPeak"],
                    dashboard_df["DrawdownDollarFromPeak"]
                )
            ),
            hovertemplate=
            "<b>Trade ID:</b> %{customdata[0]}<br>" +
            "<b>Peak-to-Peak R:</b> %{customdata[1]:.2f}R<br>" +
            "<b>From Peak:</b> %{y:.2f}%<br>" +
            "<b>Peak-to-Peak $:</b> $%{customdata[2]:,.0f}<br>" +
            "<extra></extra>"
        )
    )
    if selected_year == "All Years":

        xaxis_config = dict(
            tickformat="%Y",
            title="Date"
        )

    else:

        xaxis_config = dict(
            tickformat="%b",
            title="Date"
        )

    fig_dd.update_layout(
        height=500,
        hovermode="x unified",

        showlegend=True,

        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),

        xaxis=xaxis_config,

        yaxis=dict(
            title="Drawdown %",
            ticksuffix="%"
        )
    )

    st.plotly_chart(
        fig_dd,
        use_container_width=True
    )

with tab4:

    st.subheader("Monthly Performance")

    monthly_summary = monthly_summary_raw.copy()

    # =========================
    # FORMATTING
    # =========================

    monthly_summary["TotalR"] = (
        monthly_summary["TotalR"]
        .map(lambda x: f"{x:.2f}R")
    )

    monthly_summary["TotalDollar"] = (
        monthly_summary["TotalDollar"]
        .map(lambda x: f"${x:,.2f}")
    )

    monthly_summary["WinRate"] = (
        monthly_summary["WinRate"]
        .map(lambda x: f"{x:.2f}%")
    )

    monthly_summary["MonthlyPct"] = (
        monthly_summary["MonthlyPct"]
        .map(lambda x: f"{x:.2f}%")
    )

    monthly_summary["MaxDDPct"] = (
        monthly_summary["MaxDDPct"]
        .apply(format_dd)
    )
    monthly_summary["MaxDailyDDPct"] = (
        monthly_summary["MaxDailyDDPct"]
        .apply(format_daily_dd)
    )
    monthly_summary["EndEquityPct"] = (
        monthly_summary["EndEquityPct"]
        .map(lambda x: f"{x:.2f}%")
    )
    monthly_summary["W/L/BE"] = (
        monthly_summary["Wins"].astype(str)
        + " / "
        + monthly_summary["Losses"].astype(str)
        + " / "
        + monthly_summary["BE"].astype(str)
    )
    monthly_summary = monthly_summary.rename(
        columns={
            "TradingDays": "Trading Days",
            "TotalR": "Total Net R",
            "TotalDollar": "Total $",
            "WinRate": "Win Rate %",
            "MonthlyPct": "Monthly %",
            "MaxDDPct": "Peak-to-Peak DD %",
            "MaxDailyDDPct": "Max Daily DD %",
            "EndEquityPct": "End Equity %"
        }
    )
    monthly_summary = monthly_summary[
    [
        "Month",
        "Trading Days",
        "Trades",
        "W/L/BE",
        "Win Rate %",
        "Total Net R",
        "Total $",
        "Monthly %",
        "End Equity %",
        "Max Daily DD %",
        "Peak-to-Peak DD %"
    ]
    ]
    st.dataframe(
        monthly_summary,
        width="stretch"
    )

with tab3:

    st.subheader("Quarterly Performance")

    quarterly_summary = quarterly_summary_raw.copy()

    # =========================
    # FORMATTING
    # =========================

    quarterly_summary["TotalR"] = (
        quarterly_summary["TotalR"]
        .map(lambda x: f"{x:.2f}R")
    )

    quarterly_summary["TotalDollar"] = (
        quarterly_summary["TotalDollar"]
        .map(lambda x: f"${x:,.2f}")
    )

    quarterly_summary["WinRate"] = (
        quarterly_summary["WinRate"]
        .map(lambda x: f"{x:.2f}%")
    )

    quarterly_summary["QuarterlyPct"] = (
        quarterly_summary["QuarterlyPct"]
        .map(lambda x: f"{x:.2f}%")
    )

    quarterly_summary["EndEquityPct"] = (
        quarterly_summary["EndEquityPct"]
        .map(lambda x: f"{x:.2f}%")
    )

    quarterly_summary["MaxDDPct"] = (
        quarterly_summary["MaxDDPct"]
        .apply(format_dd)
    )

    quarterly_summary["MaxDailyDDPct"] = (
        quarterly_summary["MaxDailyDDPct"]
        .apply(format_daily_dd)
    )

    quarterly_summary["W/L/BE"] = (
        quarterly_summary["Wins"].astype(str)
        + " / "
        + quarterly_summary["Losses"].astype(str)
        + " / "
        + quarterly_summary["BE"].astype(str)
    )

    quarterly_summary = quarterly_summary.rename(
        columns={
            "TradingDays": "Trading Days",
            "TotalR": "Total Net R",
            "TotalDollar": "Total $",
            "WinRate": "Win Rate %",
            "QuarterlyPct": "Quarterly %",
            "MaxDDPct": "Peak-to-Peak DD %",
            "MaxDailyDDPct": "Max Daily DD %",
            "EndEquityPct": "End Equity %"
        }
    )

    quarterly_summary = quarterly_summary[
        [
            "Quarter",
            "Trading Days",
            "Trades",
            "W/L/BE",
            "Win Rate %",
            "Total Net R",
            "Total $",
            "Quarterly %",
            "End Equity %",
            "Max Daily DD %",
            "Peak-to-Peak DD %"
        ]
    ]

    st.dataframe(
        quarterly_summary,
        width="stretch"
    )

with tab5:

    st.subheader("Weekly Performance")

    weekly_summary = weekly_summary_raw.copy()

    # =========================
    # FORMATTING
    # =========================

    weekly_summary["TotalR"] = (
        weekly_summary["TotalR"]
        .map(lambda x: f"{x:.2f}R")
    )

    weekly_summary["TotalDollar"] = (
        weekly_summary["TotalDollar"]
        .map(lambda x: f"${x:,.2f}")
    )

    weekly_summary["WinRate"] = (
        weekly_summary["WinRate"]
        .map(lambda x: f"{x:.2f}%")
    )

    weekly_summary["WeeklyPct"] = (
        weekly_summary["WeeklyPct"]
        .map(lambda x: f"{x:.2f}%")
    )

    weekly_summary["EndEquityPct"] = (
        weekly_summary["EndEquityPct"]
        .map(lambda x: f"{x:.2f}%")
    )

    weekly_summary["MaxDDPct"] = (
        weekly_summary["MaxDDPct"]
        .apply(format_dd)
    )

    weekly_summary["MaxDailyDDPct"] = (
        weekly_summary["MaxDailyDDPct"]
        .apply(format_daily_dd)
    )

    weekly_summary["Week Start Date"] = (
        pd.to_datetime(
            weekly_summary["Week Start Date"]
        )
        .dt.strftime("%d %b %Y")
    )

    weekly_summary["W/L/BE"] = (
        weekly_summary["Wins"].astype(str)
        + " / "
        + weekly_summary["Losses"].astype(str)
        + " / "
        + weekly_summary["BE"].astype(str)
    )

    weekly_summary = weekly_summary.rename(
        columns={
            "TradingDays": "Trading Days",
            "TotalR": "Total Net R",
            "TotalDollar": "Total $",
            "WinRate": "Win Rate %",
            "WeeklyPct": "Weekly %",
            "MaxDDPct": "Peak-to-Peak DD %",
            "MaxDailyDDPct": "Max Daily DD %",
            "EndEquityPct": "End Equity %"
        }
    )

    weekly_summary = weekly_summary[
        [
            "Week",
            "Week Start Date",
            "Trading Days",
            "Trades",
            "W/L/BE",
            "Win Rate %",
            "Total Net R",
            "Total $",
            "Weekly %",
            "End Equity %",
            "Max Daily DD %",
            "Peak-to-Peak DD %"
        ]
    ]

    st.dataframe(
        weekly_summary,
        width="stretch"
    )

with tab6:

    st.subheader("Daily Performance")

    daily_summary = daily_summary_raw.copy()
        
    daily_summary["MaxDDPct"] = (
        daily_summary["MaxDDPct"]
        .apply(format_dd)
    )

    daily_summary["MaxDailyDDPct"] = (
        daily_summary["MaxDailyDDPct"]
        .apply(format_daily_dd)
    )
    # =========================
    # FORMATTING
    # =========================
    daily_summary["TotalR"] = (
        daily_summary["TotalR"]
        .map(lambda x: f"{x:.2f}R")
    )

    daily_summary["TotalDollar"] = (
        daily_summary["TotalDollar"]
        .map(lambda x: f"${x:,.2f}")
    )

    daily_summary["WinRate"] = (
        daily_summary["WinRate"]
        .map(lambda x: f"{x:.2f}%")
    )

    daily_summary["DailyPct"] = (
        daily_summary["DailyPct"]
        .map(lambda x: f"{x:.2f}%")
    )

    daily_summary["EndEquityPct"] = (
        daily_summary["EndEquityPct"]
        .map(lambda x: f"{x:.2f}%")
    )

    daily_summary["W/L/BE"] = (
        daily_summary["Wins"].astype(str)
        + " / "
        + daily_summary["Losses"].astype(str)
        + " / "
        + daily_summary["BE"].astype(str)
    )

    daily_summary = daily_summary.rename(
        columns={
            "WinRate": "Win Rate %",
            "TotalR": "Total Net R",
            "TotalDollar": "Total $",
            "DailyPct": "Daily %",
            "EndEquityPct": "End Equity %",
            "MaxDailyDDPct": "Max Daily DD %",
            "MaxDDPct": "Peak-to-Peak DD %"
        }
    )

    daily_summary = daily_summary[
        [
            "TradeDateNY",
            "Trades",
            "W/L/BE",
            "Win Rate %",
            "Total Net R",
            "Total $",
            "Daily %",
            "End Equity %",
            "Max Daily DD %",
            "Peak-to-Peak DD %"
        ]
    ]

    st.dataframe(
        daily_summary,
        width="stretch"
    )

with tab2:

    st.subheader("Yearly Performance")

    yearly_summary = yearly_summary_raw.copy()

    # =========================
    # FORMATTING
    # =========================

    yearly_summary["TotalR"] = yearly_summary["TotalR"].map(lambda x: f"{x:.2f}R")
    yearly_summary["TotalDollar"] = yearly_summary["TotalDollar"].map(lambda x: f"${x:,.2f}")
    yearly_summary["WinRate"] = yearly_summary["WinRate"].map(lambda x: f"{x:.2f}%")
    yearly_summary["YearlyPct"] = yearly_summary["YearlyPct"].map(lambda x: f"{x:.2f}%")
    yearly_summary["EndEquityPct"] = yearly_summary["EndEquityPct"].map(lambda x: f"{x:.2f}%")

    yearly_summary["MaxDDPct"] = yearly_summary["MaxDDPct"].apply(format_dd)
    yearly_summary["MaxDailyDDPct"] = yearly_summary["MaxDailyDDPct"].apply(format_daily_dd)

    yearly_summary["W/L/BE"] = (
        yearly_summary["Wins"].astype(str)
        + " / "
        + yearly_summary["Losses"].astype(str)
        + " / "
        + yearly_summary["BE"].astype(str)
    )

    yearly_summary = yearly_summary.rename(
        columns={
            "TradingDays": "Trading Days",
            "TotalR": "Total Net R",
            "TotalDollar": "Total $",
            "WinRate": "Win Rate %",
            "YearlyPct": "Yearly %",
            "MaxDDPct": "Peak-to-Peak DD %",
            "MaxDailyDDPct": "Max Daily DD %",
            "EndEquityPct": "End Equity %"
        }
    )

    yearly_summary = yearly_summary[
        [
            "Year",
            "Trading Days",
            "Trades",
            "W/L/BE",
            "Win Rate %",
            "Total Net R",
            "Total $",
            "Yearly %",
            "End Equity %",
            "Max Daily DD %",
            "Peak-to-Peak DD %"
        ]
    ]

    st.dataframe(
        yearly_summary,
        width="stretch"
    )

    with tab7:
        st.subheader("All Trades")
        st.dataframe(
            df[
                [
                    "TradeID",
                    "EntryTimeNY",
                    "ExitTimeNY",
                    "NetResultR",
                    "Risk$",
                    "Profit$",
                    "Balance"
                ]
            ],
            width="stretch"
        )