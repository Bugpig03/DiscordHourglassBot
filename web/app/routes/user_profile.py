"""User profile routes and statistics loading."""

import json
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, request
from app.functions import (
    get_user_id_by_username,
    get_user_avatar_url,
    get_global_rank_by_user_id_seconds,
    get_global_nb_user,
    ConvertSecondsToTime,
    get_total_seconds_by_user_id,
    get_total_message_by_user_id,
    get_user_join_date,
    get_user_raw_join_date,
    get_activity_sum_last_X_days,
    get_user_servers_stats,
    get_first_of_month_hours_sum,
    get_first_of_month_messages_sum,
    get_monthly_hours_diff,
    get_monthly_messages_diff,
    get_month_abbr,
)
from app.gamification import calculate_user_xp_and_level, calculate_user_badges

user_profile_bp = Blueprint("user_profile", __name__)


@user_profile_bp.route("/profile/<username>", methods=["GET"])
def profile(username: str):
    """Display the profile page, statistics, voice-sorted server list, and analytics charts for a user."""
    user_id = get_user_id_by_username(username)
    if user_id is None:
        # User not found in database; redirect to homepage
        return redirect(url_for("home.home"))

    lang = request.cookies.get("lang", "fr")
    stats = load_user_profile_stats(user_id, username)
    charts = load_user_charts_data(user_id, stats["user_servers_stats"], lang=lang)

    # Real-time gamification: XP, level, and badges without DB writes
    xp_info = calculate_user_xp_and_level(stats["total_seconds"], stats["total_message"])
    badges = calculate_user_badges(stats, lang=lang)
    unlocked_count = sum(1 for b in badges if b["unlocked"])

    gamification = {
        "xp_info": xp_info,
        "badges": badges,
        "unlocked_count": unlocked_count,
        "total_badges": len(badges),
    }

    return render_template(
        "user_profile.html",
        stats=stats,
        charts=charts,
        gamification=gamification
    )


def load_user_profile_stats(user_id: int, username: str) -> dict:
    """Compile comprehensive profile data and voice-sorted server breakdown for a user."""
    avatar_url = get_user_avatar_url(user_id)
    rank = get_global_rank_by_user_id_seconds(user_id)
    total_user = get_global_nb_user()
    total_seconds = get_total_seconds_by_user_id(user_id)
    total_time = ConvertSecondsToTime(total_seconds)
    total_messages = get_total_message_by_user_id(user_id)
    join_date = get_user_join_date(user_id)

    activity_30d = get_activity_sum_last_X_days(user_id, 30)
    total_time_last_30d = activity_30d["seconds"]

    user_servers_stats = get_user_servers_stats(user_id)

    return {
        "user_id": str(user_id),
        "avatar_url": avatar_url,
        "username": username,
        "rank": rank,
        "total_user": total_user,
        "total_time": total_time,
        "total_seconds": total_seconds or 0,
        "total_time_hours": round((total_seconds or 0) / 3600, 1),
        "total_message": total_messages,
        "total_time_last_30d": total_time_last_30d,
        "user_servers_stats": user_servers_stats,
        "join_date": join_date,
        "raw_join_date": get_user_raw_join_date(user_id),
    }


def load_user_charts_data(user_id: int, user_servers_stats: list[dict], lang: str = "fr") -> dict:
    """Compile chart data for a specific user: cumulative curves, monthly activity, and server distribution."""
    # 1. Cumulative personal voice hours progression
    hours_data = get_first_of_month_hours_sum(user_id=user_id)
    chart_data_json = json.dumps({
        "labels": [row["month"] for row in hours_data],
        "hours": [row["total_hours"] for row in hours_data]
    })

    # 2. Cumulative personal messages progression
    messages_data = get_first_of_month_messages_sum(user_id=user_id)
    messages_chart_data_json = json.dumps({
        "labels": [row["month"] for row in messages_data],
        "messages": [row["total_messages"] for row in messages_data]
    })

    # 3. Monthly voice hours deltas
    monthly_diff_data = get_monthly_hours_diff(user_id=user_id)
    monthly_chart_data_json = json.dumps({
        "labels": [
            f"{get_month_abbr(datetime.strptime(row['month'], '%Y-%m-%d').month, lang)} {datetime.strptime(row['month'], '%Y-%m-%d').year}"
            for row in monthly_diff_data
        ],
        "hours": [row["hours_this_month"] for row in monthly_diff_data]
    })

    # 4. Monthly messages deltas
    monthly_messages_diff_data = get_monthly_messages_diff(user_id=user_id)
    monthly_messages_chart_data_json = json.dumps({
        "labels": [
            f"{get_month_abbr(datetime.strptime(row['month'], '%Y-%m-%d').month, lang)} {datetime.strptime(row['month'], '%Y-%m-%d').year}"
            for row in monthly_messages_diff_data
        ],
        "messages": [row["messages_this_month"] for row in monthly_messages_diff_data]
    })

    # 5. User's servers distribution doughnut (Top 10 servers by time spent + Autres)
    top_servers = user_servers_stats[:10]
    remaining_servers = user_servers_stats[10:]

    server_labels = [s["server_name"] for s in top_servers]
    server_hours = [s["time_spent"] for s in top_servers]
    if remaining_servers:
        other_hours = round(sum(s["time_spent"] for s in remaining_servers), 1)
        other_text = f"Others ({len(remaining_servers)} servers)" if lang == "en" else f"Autres ({len(remaining_servers)} serveurs)"
        server_labels.append(other_text)
        server_hours.append(other_hours)

    user_servers_pie_json = json.dumps({
        "labels": server_labels,
        "hours": server_hours
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
        "user_servers_pie_json": user_servers_pie_json,
        "avg_hours": avg_hours,
        "avg_msgs": avg_msgs,
    }