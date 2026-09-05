"""Data visualization and analytics graph routes."""

import json
from datetime import datetime
from flask import Blueprint, render_template, request
from peewee import fn, JOIN
from app.database import Stats, Servers
from app.functions import (
    get_first_of_month_hours_sum,
    get_first_of_month_messages_sum,
    get_monthly_hours_diff,
    get_monthly_messages_diff,
    get_daily_activity_last_30_days,
    get_top_10_users_by_hours,
    get_vocal_vs_messages_scatter,
    get_monthly_new_users_growth,
    get_month_abbr
)

graphs_bp = Blueprint("graphs", __name__)


@graphs_bp.route("/graphs", methods=["GET"])
def graphs():
    """Render analytical charts: cumulative progressions, monthly deltas, daily activity, server and user statistics."""
    lang = request.cookies.get("lang", "fr")
    # 1. Total cumulative hours progression curve
    hours_data = get_first_of_month_hours_sum()
    chart_data_json = json.dumps({
        "labels": [row["month"] for row in hours_data],
        "hours": [row["total_hours"] for row in hours_data]
    })

    # 2. Total cumulative messages progression curve
    messages_data = get_first_of_month_messages_sum()
    messages_chart_data_json = json.dumps({
        "labels": [row["month"] for row in messages_data],
        "messages": [row["total_messages"] for row in messages_data]
    })

    # 3. Monthly delta bar chart (Hours)
    monthly_diff_data = get_monthly_hours_diff()
    monthly_chart_data_json = json.dumps({
        "labels": [
            f"{get_month_abbr(datetime.strptime(row['month'], '%Y-%m-%d').month, lang)} "
            f"{datetime.strptime(row['month'], '%Y-%m-%d').year}"
            for row in monthly_diff_data
        ],
        "hours": [row["hours_this_month"] for row in monthly_diff_data]
    })

    # 4. Monthly delta bar chart (Messages)
    monthly_messages_diff_data = get_monthly_messages_diff()
    monthly_messages_chart_data_json = json.dumps({
        "labels": [
            f"{get_month_abbr(datetime.strptime(row['month'], '%Y-%m-%d').month, lang)} "
            f"{datetime.strptime(row['month'], '%Y-%m-%d').year}"
            for row in monthly_messages_diff_data
        ],
        "messages": [row["messages_this_month"] for row in monthly_messages_diff_data]
    })

    # 5. 30-Day daily activity area chart
    daily_activity_data = get_daily_activity_last_30_days()
    daily_activity_chart_data_json = json.dumps({
        "labels": [
            f"{datetime.strptime(row['date'], '%Y-%m-%d').day} {get_month_abbr(datetime.strptime(row['date'], '%Y-%m-%d').month, lang)}"
            for row in daily_activity_data
        ],
        "hours": [row["hours"] for row in daily_activity_data],
        "messages": [row["messages"] for row in daily_activity_data]
    })

    # 6. Server breakdown (Hours): Top 10 servers + Others group
    query_hours = (
        Stats
        .select(
            Stats.server_id,
            Servers.servername,
            fn.SUM(Stats.seconds).alias("total_seconds")
        )
        .join(Servers, JOIN.LEFT_OUTER, on=(Stats.server_id == Servers.server_id))
        .group_by(Stats.server_id, Servers.servername)
        .order_by(fn.SUM(Stats.seconds).desc())
        .dicts()
    )

    all_servers = list(query_hours)
    top_10_servers = all_servers[:10]
    remaining_servers = all_servers[10:]

    server_hours_labels = []
    server_hours_vals = []
    for row in top_10_servers:
        default_name = f"Server {row['server_id']}" if lang == "en" else f"Serveur {row['server_id']}"
        server_name = row["servername"] if row["servername"] else default_name
        server_hours_labels.append(server_name)
        server_hours_vals.append(round((row["total_seconds"] or 0) / 3600, 1))

    if remaining_servers:
        other_seconds = sum((r["total_seconds"] or 0) for r in remaining_servers)
        other_text = f"Others ({len(remaining_servers)} servers)" if lang == "en" else f"Autres ({len(remaining_servers)} serveurs)"
        server_hours_labels.append(other_text)
        server_hours_vals.append(round(other_seconds / 3600, 1))

    chart_data_json_pie_server = json.dumps({
        "labels": server_hours_labels,
        "hours": server_hours_vals
    })

    # 7. Server breakdown (Messages): Top 10 servers + Others group
    query_msg = (
        Stats
        .select(
            Stats.server_id,
            Servers.servername,
            fn.SUM(Stats.messages).alias("total_messages")
        )
        .join(Servers, JOIN.LEFT_OUTER, on=(Stats.server_id == Servers.server_id))
        .group_by(Stats.server_id, Servers.servername)
        .order_by(fn.SUM(Stats.messages).desc())
        .dicts()
    )

    all_servers_msg = list(query_msg)
    top_10_msg = all_servers_msg[:10]
    remaining_msg = all_servers_msg[10:]

    server_msg_labels = []
    server_msg_vals = []
    for row in top_10_msg:
        default_name = f"Server {row['server_id']}" if lang == "en" else f"Serveur {row['server_id']}"
        server_name = row["servername"] if row["servername"] else default_name
        server_msg_labels.append(server_name)
        server_msg_vals.append(int(row["total_messages"] or 0))

    if remaining_msg:
        other_msgs = sum(int(r["total_messages"] or 0) for r in remaining_msg)
        other_text = f"Others ({len(remaining_msg)} servers)" if lang == "en" else f"Autres ({len(remaining_msg)} serveurs)"
        server_msg_labels.append(other_text)
        server_msg_vals.append(other_msgs)

    server_messages_pie_json = json.dumps({
        "labels": server_msg_labels,
        "messages": server_msg_vals
    })

    # 8. Top 10 active users horizontal leaderboard
    top_users_data = get_top_10_users_by_hours()
    top_users_chart_json = json.dumps({
        "labels": [row["username"] for row in top_users_data],
        "hours": [row["hours"] for row in top_users_data],
        "messages": [row["messages"] for row in top_users_data]
    })

    # 9. Voice vs Messages scatter matrix (Top 40 active users)
    scatter_data = get_vocal_vs_messages_scatter(40)
    scatter_chart_json = json.dumps(scatter_data)

    # 10. Community growth: new users cohort by month
    user_growth_data = get_monthly_new_users_growth()
    user_growth_chart_json = json.dumps({
        "labels": [
            f"{get_month_abbr(datetime.strptime(row['month'], '%Y-%m-%d').month, lang)} "
            f"{datetime.strptime(row['month'], '%Y-%m-%d').year}"
            for row in user_growth_data
        ],
        "new_users": [row["new_users"] for row in user_growth_data]
    })

    # Summary metrics for header KPI cards
    total_cumulative_hours = hours_data[-1]["total_hours"] if hours_data else 0
    total_cumulative_messages = messages_data[-1]["total_messages"] if messages_data else 0
    full_months = monthly_diff_data[:-1] if len(monthly_diff_data) > 1 else monthly_diff_data
    avg_monthly_hours = round(sum(r["hours_this_month"] for r in full_months) / max(1, len(full_months)), 1) if full_months else 0

    full_msg_months = monthly_messages_diff_data[:-1] if len(monthly_messages_diff_data) > 1 else monthly_messages_diff_data
    avg_monthly_messages = int(sum(r["messages_this_month"] for r in full_msg_months) / max(1, len(full_msg_months))) if full_msg_months else 0

    summary_stats = {
        "total_hours": total_cumulative_hours,
        "total_messages": total_cumulative_messages,
        "avg_monthly_hours": avg_monthly_hours,
        "avg_monthly_messages": avg_monthly_messages,
        "total_servers": len(all_servers)
    }

    return render_template(
        "graphs.html",
        chart_data_json=chart_data_json,
        messages_chart_data_json=messages_chart_data_json,
        monthly_chart_data_json=monthly_chart_data_json,
        monthly_messages_chart_data_json=monthly_messages_chart_data_json,
        daily_activity_chart_data_json=daily_activity_chart_data_json,
        chart_data_json_pie_server=chart_data_json_pie_server,
        server_messages_pie_json=server_messages_pie_json,
        top_users_chart_json=top_users_chart_json,
        scatter_chart_json=scatter_chart_json,
        user_growth_chart_json=user_growth_chart_json,
        summary_stats=summary_stats
    )
