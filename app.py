from flask import Flask, render_template, request, redirect, url_for, jsonify
from logic import process_data, get_statistics
import pandas as pd

app = Flask(__name__)

MONTH_ORDER = ["Jan","Feb","Mar","Apr","May","Jun",
               "Jul","Aug","Sep","Oct","Nov","Dec"]


def build_chart_data(df):
    cities = df["city"].tolist()
    stocks = df["current_stock"].tolist()
    consumption_rates = df["consumption_rate"].tolist()
    days_remaining = df["days_remaining"].tolist()
    shortage = df["shortage"].tolist()
    statuses = df["status"].tolist()

    # Color map per status
    status_colors = {
        "CRITICAL": "rgba(239,68,68,0.85)",
        "WARNING":  "rgba(251,146,60,0.85)",
        "SAFE":     "rgba(34,197,94,0.85)",
    }
    bar_colors = [status_colors.get(s, "#94a3b8") for s in statuses]

    # Monthly allocation
    monthly_allocated = (
        df.groupby("month")["allocated"].sum()
        .reindex(MONTH_ORDER, fill_value=0)
    )
    months = monthly_allocated.index.tolist()
    monthly_values = monthly_allocated.values.tolist()

    # City monthly stock
    city_month_data = {}
    all_df = pd.read_csv("data/supplies.csv")
    for city in df["city"].unique():
        city_df = all_df[all_df["city"] == city]
        city_month = (
            city_df.groupby("month")["current_stock"].sum()
            .reindex(MONTH_ORDER, fill_value=0)
        )
        city_month_data[city] = city_month.values.tolist()

    # Supply type totals
    supply_totals = df.groupby("supply_type")["current_stock"].sum()
    supply_labels = supply_totals.index.tolist()
    supply_values = supply_totals.values.tolist()

    return dict(
        cities=cities,
        stocks=stocks,
        consumption_rates=consumption_rates,
        days_remaining=days_remaining,
        shortage=shortage,
        bar_colors=bar_colors,
        months=months,
        monthly_values=monthly_values,
        city_month_data=city_month_data,
        supply_labels=supply_labels,
        supply_values=supply_values,
    )


@app.route("/", methods=["GET"])
def dashboard():
    df, alerts, supply_summary = process_data()

    # ── Filters ──────────────────────────────────────────────────────
    supply_filter  = request.args.get("supply_filter", "")
    critical_only  = request.args.get("critical_only")
    sort_option    = request.args.get("sort_option", "")
    search_city    = request.args.get("search_city", "").strip()

    display_df = df.copy()

    if supply_filter:
        display_df = display_df[display_df["supply_type"] == supply_filter]

    if critical_only:
        display_df = display_df[display_df["status"] == "CRITICAL"]

    if search_city:
        display_df = display_df[
            display_df["city"].str.contains(search_city, case=False)
        ]

    if sort_option == "days_remaining":
        display_df = display_df.sort_values("days_remaining")
    elif sort_option == "priority":
        display_df = display_df.sort_values("priority_score", ascending=False)
    elif sort_option == "city":
        display_df = display_df.sort_values("city")
    elif sort_option == "shortage":
        display_df = display_df.sort_values("shortage", ascending=False)

    data = display_df.to_dict(orient="records")
    stats = get_statistics(df)  # always use full df for stats
    chart = build_chart_data(display_df)

    return render_template(
        "dashboard.html",
        data=data,
        alerts=alerts,
        supply_summary=supply_summary,
        stats=stats,
        **chart,
        # filter state
        supply_filter=supply_filter,
        critical_only=critical_only,
        sort_option=sort_option,
        search_city=search_city,
    )


@app.route("/add", methods=["POST"])
def add_data():
    new_data = {
        "city":             request.form["city"].strip().title(),
        "supply_type":      request.form["supply_type"],
        "month":            request.form["month"],
        "allocated":        int(request.form["allocated"]),
        "current_stock":    int(request.form["current_stock"]),
        "consumption_rate": int(request.form["consumption_rate"]),
        "required_stock":   int(request.form["required_stock"]),
    }
    df = pd.read_csv("data/supplies.csv")
    df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
    df.to_csv("data/supplies.csv", index=False)
    return redirect(url_for("dashboard"))


@app.route("/delete/<city>", methods=["POST"])
def delete_city(city):
    df = pd.read_csv("data/supplies.csv")
    df = df[df["city"] != city]
    df.to_csv("data/supplies.csv", index=False)
    return redirect(url_for("dashboard"))


@app.route("/api/data")
def api_data():
    df, alerts, supply_summary = process_data()
    return jsonify({
        "cities": df["city"].tolist(),
        "alerts": alerts,
        "supply_summary": supply_summary,
        "data": df.to_dict(orient="records"),
    })


if __name__ == "__main__":
    app.run(debug=True)
