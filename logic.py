import pandas as pd
import numpy as np

MONTH_ORDER = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4,
    "May": 5, "Jun": 6, "Jul": 7, "Aug": 8,
    "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
}

CRITICAL_THRESHOLD = 2      # days
WARNING_THRESHOLD = 3       # days
SHORTAGE_PCT_THRESHOLD = 0.10  # 10% of required stock = critical shortage


def load_data():
    df = pd.read_csv("data/supplies.csv")
    df.columns = df.columns.str.strip()
    return df


def process_data():
    df = load_data()

    # ── Month numeric sort ──────────────────────────────────────────
    df["month_num"] = df["month"].map(MONTH_ORDER)
    df = df.sort_values("month_num")

    # ── Latest record per city ──────────────────────────────────────
    latest_df = df.groupby("city").tail(1).copy()

    # ── Days Remaining ──────────────────────────────────────────────
    latest_df["days_remaining"] = np.where(
        latest_df["consumption_rate"] > 0,
        np.round(latest_df["current_stock"] / latest_df["consumption_rate"], 2),
        0
    )

    # ── Depletion Rate (% stock consumed per day vs required) ───────
    latest_df["depletion_rate_pct"] = np.where(
        latest_df["required_stock"] > 0,
        np.round((latest_df["consumption_rate"] / latest_df["required_stock"]) * 100, 2),
        0
    )

    # ── Status Classification ────────────────────────────────────────
    latest_df["status"] = np.where(
        latest_df["days_remaining"] < CRITICAL_THRESHOLD,
        "CRITICAL",
        np.where(
            latest_df["days_remaining"] <= WARNING_THRESHOLD,
            "WARNING",
            "SAFE"
        )
    )

    # ── Critical Shortage Flag (< 10% of required stock) ────────────
    latest_df["critical_shortage_flag"] = (
        latest_df["current_stock"] < (SHORTAGE_PCT_THRESHOLD * latest_df["required_stock"])
    )

    # ── Shortage Amount ─────────────────────────────────────────────
    latest_df["shortage"] = np.maximum(
        latest_df["required_stock"] - latest_df["current_stock"], 0
    )

    # ── Resupply Priority Score (higher = more urgent) ──────────────
    # Weighted: lower days remaining + higher shortage = more urgent
    max_shortage = latest_df["shortage"].max() or 1
    max_days = latest_df["days_remaining"].max() or 1
    latest_df["priority_score"] = np.round(
        (1 - latest_df["days_remaining"] / max_days) * 60 +
        (latest_df["shortage"] / max_shortage) * 40,
        2
    )

    # ── Alerts: cities needing resupply within 3 days, sorted by urgency ──
    alerts_df = latest_df[latest_df["status"] != "SAFE"].sort_values("days_remaining")
    alerts = alerts_df[["city", "supply_type", "days_remaining", "status", "shortage"]].to_dict(orient="records")

    # ── Supply type breakdown ────────────────────────────────────────
    supply_summary = latest_df.groupby("supply_type").agg(
        total_stock=("current_stock", "sum"),
        total_required=("required_stock", "sum"),
        city_count=("city", "count")
    ).reset_index().to_dict(orient="records")

    return latest_df, alerts, supply_summary


def get_statistics(df):
    """Return aggregate statistics for the dashboard summary."""
    total_cities = df["city"].nunique()
    critical_cities = int((df["status"] == "CRITICAL").sum())
    warning_cities = int((df["status"] == "WARNING").sum())
    safe_cities = int((df["status"] == "SAFE").sum())
    total_stock = int(df["current_stock"].sum())
    total_required = int(df["required_stock"].sum())
    total_shortage = int(df["shortage"].sum())
    coverage_pct = round((total_stock / total_required) * 100, 1) if total_required else 0

    worst_idx = df["days_remaining"].idxmin()
    worst_city = df.loc[worst_idx, "city"]
    lowest_days = round(df.loc[worst_idx, "days_remaining"], 2)

    # Most common supply type in shortage
    critical_supply = (
        df[df["status"] == "CRITICAL"]["supply_type"].value_counts().idxmax()
        if critical_cities > 0 else "None"
    )

    return {
        "total_cities": total_cities,
        "critical_cities": critical_cities,
        "warning_cities": warning_cities,
        "safe_cities": safe_cities,
        "total_stock": total_stock,
        "total_required": total_required,
        "total_shortage": total_shortage,
        "coverage_pct": coverage_pct,
        "worst_city": worst_city,
        "lowest_days": lowest_days,
        "critical_supply": critical_supply,
    }
