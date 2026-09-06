"""Server profile routes and member list loading."""

import json
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for
from peewee import JOIN, fn
from app.database import Users, Stats
from app.gamification import calculate_user_xp_and_level
from app.functions import (
    get_servername_by_server_id,
    get_server_avatar_url,
    get_server_rank,
    get_global_nb_server,
    ConvertSecondsToTime,
    get_total_seconds_by_server_id,
    get_total_message_by_server_id,
    get_server_activity_sum_last_X_days,
    get_server_join_date,
    get_first_of_month_hours_sum,
    get_first_of_month_messages_sum,
    get_monthly_hours_diff,
    get_monthly_messages_diff,
    get_month_abbr,
)

server_profile_bp = Blueprint("server_profile", __name__)

# User ID of the Hourglass bot used to track server join dates
HOURGLASS_BOT_ID = 1210665993328926750


@server_profile_bp.route("/server/<server_id>", methods=["GET"])
def server(server_id: str):
    """Display the profile page, statistics, ranked member directory, and analytics charts for a server."""
    servername = get_servername_by_server_id(server_id)
    if servername is None:
        # Server not found or invalid ID; redirect to homepage
        return redirect(url_for("home.home"))

    lang = request.cookies.get("lang", "fr")
    search_query = request.args.get("q", "").strip()
    stats = load_server_profile_stats(server_id, search_query=search_query, lang=lang)
    charts = load_server_charts_data(server_id, lang=lang)

    return render_template(
        "server_profile.html",
        stats=stats,
        charts=charts
    )


def load_server_profile_stats(server_id: str | int, search_query: str = "", lang: str = "fr") -> dict:
    """Compile aggregated metrics and member leaderboard for a given server."""
    return {
        "server_id": str(server_id),
        "avatar_url": get_server_avatar_url(server_id),
        "servername": get_servername_by_server_id(server_id),
        "rank": get_server_rank(server_id),
        "total_server": get_global_nb_server(),
        "total_time": ConvertSecondsToTime(get_total_seconds_by_server_id(server_id)),
        "total_time_hours": round((get_total_seconds_by_server_id(server_id) or 0) / 3600, 1),
        "total_message": get_total_message_by_server_id(server_id),
        "total_time_last_30d": get_server_activity_sum_last_X_days(server_id, 30),
        "users": load_users_from_server(server_id, search_query, lang=lang),
        "join_date": get_server_join_date(server_id, lang=lang),
    }


def load_users_from_server(server_id: str | int, search_query: str = "", lang: str = "fr") -> list[dict]:
    """Retrieve members with activity on a server, ranked by voice time descending."""
    query = (
        Stats
        .select(
            Stats.user_id,
            Stats.seconds,
            Stats.messages,
            Users.username,
            Users.avatar
        )
        .join(Users, JOIN.LEFT_OUTER, on=(Stats.user_id == Users.user_id))
        .where(
            (Stats.server_id == int(server_id)) &
            (Stats.user_id != HOURGLASS_BOT_ID)
        )
        .order_by(Stats.seconds.desc())
        .dicts()
    )

    all_members = list(query)
    if search_query:
        query_lower = search_query.lower()
        filtered = [
            u for u in all_members
            if u["username"] and query_lower in u["username"].lower()
        ]
    else:
        filtered = all_members

    user_ids = [row["user_id"] for row in filtered if row.get("user_id")]
    global_map = {}
    if user_ids:
        global_stats = (
            Stats
            .select(
                Stats.user_id,
                fn.SUM(Stats.seconds).alias("tot_sec"),
                fn.SUM(Stats.messages).alias("tot_msg")
            )
            .where(Stats.user_id.in_(user_ids))
            .group_by(Stats.user_id)
        )
        global_map = {g.user_id: (g.tot_sec or 0, g.tot_msg or 0) for g in global_stats}

    result = []
    for rank, row in enumerate(filtered, start=1):
        default_username = f"Member {row['user_id']}" if lang == "en" else f"Membre {row['user_id']}"
        username = row["username"] if row["username"] else default_username
        seconds = row["seconds"] or 0
        messages = row["messages"] or 0
        g_sec, g_msg = global_map.get(row["user_id"], (seconds, messages))
        xp_info = calculate_user_xp_and_level(g_sec, g_msg)

        result.append({
            "rank": rank,
            "user_id": row["user_id"],
            "username": username,
            "avatar": row["avatar"],
            "time_spent": round(seconds / 3600, 1),
            "formatted_time": ConvertSecondsToTime(seconds),
            "messages_count": messages,
            "level": xp_info["level"],
            "total_xp": xp_info["total_xp"]
        })
    return result


def load_server_charts_data(server_id: str | int, lang: str = "fr") -> dict:
    """Compile chart data for a specific server: cumulative curves, monthly deltas, and top members doughnut."""
    int_server_id = int(server_id)

    # 1. Cumulative voice hours progression
    hours_data = get_first_of_month_hours_sum(server_id=int_server_id)
    chart_data_json = json.dumps({
        "labels": [row["month"] for row in hours_data],
        "hours": [row["total_hours"] for row in hours_data]
    })

    # 2. Cumulative messages progression
    messages_data = get_first_of_month_messages_sum(server_id=int_server_id)
    messages_chart_data_json = json.dumps({
        "labels": [row["month"] for row in messages_data],
        "messages": [row["total_messages"] for row in messages_data]
    })

    # 3. Monthly voice hours deltas
    monthly_diff_data = get_monthly_hours_diff(server_id=int_server_id)
    monthly_chart_data_json = json.dumps({
        "labels": [
            f"{get_month_abbr(datetime.strptime(row['month'], '%Y-%m-%d').month, lang)} {datetime.strptime(row['month'], '%Y-%m-%d').year}"
            for row in monthly_diff_data
        ],
        "hours": [row["hours_this_month"] for row in monthly_diff_data]
    })

    # 4. Monthly messages deltas
    monthly_messages_diff_data = get_monthly_messages_diff(server_id=int_server_id)
    monthly_messages_chart_data_json = json.dumps({
        "labels": [
            f"{get_month_abbr(datetime.strptime(row['month'], '%Y-%m-%d').month, lang)} {datetime.strptime(row['month'], '%Y-%m-%d').year}"
            for row in monthly_messages_diff_data
        ],
        "messages": [row["messages_this_month"] for row in monthly_messages_diff_data]
    })

    # 5. Top 10 members distribution doughnut
    all_members = load_users_from_server(server_id, lang=lang)
    top_10 = all_members[:10]
    remaining = all_members[10:]

    member_labels = [m["username"] for m in top_10]
    member_hours = [m["time_spent"] for m in top_10]
    if remaining:
        other_hours = round(sum(m["time_spent"] for m in remaining), 1)
        other_text = f"Others ({len(remaining)} members)" if lang == "en" else f"Autres ({len(remaining)} membres)"
        member_labels.append(other_text)
        member_hours.append(other_hours)

    top_members_pie_json = json.dumps({
        "labels": member_labels,
        "hours": member_hours
    })

    # Average monthly metrics
    full_hours = monthly_diff_data[:-1] if len(monthly_diff_data) > 1 else monthly_diff_data
    avg_hours = round(sum(r["hours_this_month"] for r in full_hours) / max(1, len(full_hours)), 1) if full_hours else 0

    full_msgs = monthly_messages_diff_data[:-1] if len(monthly_messages_diff_data) > 1 else monthly_messages_diff_data
    avg_msgs = int(sum(r["messages_this_month"] for r in full_msgs) / max(1, len(full_msgs))) if full_msgs else 0

    return {
        "chart_data_json": chart_data_json,
        "messages_chart_data_json": messages_chart_data_json,
        "monthly_chart_data_json": monthly_chart_data_json,
        "monthly_messages_chart_data_json": monthly_messages_chart_data_json,
        "top_members_pie_json": top_members_pie_json,
        "avg_hours": avg_hours,
        "avg_msgs": avg_msgs,
    }