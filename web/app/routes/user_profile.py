"""User profile routes and statistics loading."""

import json
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, request
from peewee import fn, JOIN
from app.database import Users, Stats
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
    get_daily_hours_progression,
    get_daily_messages_progression,
    get_daily_hours_diff,
    get_daily_messages_diff,
    get_month_abbr,
)
from app.gamification import calculate_user_xp_and_level, calculate_user_badges

user_profile_bp = Blueprint("user_profile", __name__)


@user_profile_bp.route("/profile/<username>", methods=["GET"])
def profile(username: str):
    """Display the profile page, statistics, voice-sorted server list, and analytics charts for a user.
    
    Supports both Discord Snowflake ID (e.g. /profile/303525237012692994)
    and username (e.g. /profile/Kiro).
    If multiple users share the exact same username, renders a disambiguation selector page.
    """
    raw_identifier = str(username).strip()
    target_user = None

    # 1. Direct lookup by numeric Discord Snowflake ID
    if raw_identifier.isdigit():
        target_user = Users.select().where(Users.user_id == int(raw_identifier)).first()

    # 2. If not found by user_id or identifier is a string, search by username
    if target_user is None:
        matching_users = list(
            Users
            .select(
                Users.user_id,
                Users.username,
                Users.avatar,
                fn.COALESCE(fn.SUM(Stats.seconds), 0).alias("total_seconds"),
                fn.COALESCE(fn.SUM(Stats.messages), 0).alias("total_messages")
            )
            .join(Stats, JOIN.LEFT_OUTER, on=(Users.user_id == Stats.user_id))
            .where(Users.username == raw_identifier)
            .group_by(Users.user_id, Users.username, Users.avatar)
            .order_by(fn.COALESCE(fn.SUM(Stats.messages), 0).desc(), fn.COALESCE(fn.SUM(Stats.seconds), 0).desc())
        )

        if not matching_users:
            # Case-insensitive fallback
            matching_users = list(
                Users
                .select(
                    Users.user_id,
                    Users.username,
                    Users.avatar,
                    fn.COALESCE(fn.SUM(Stats.seconds), 0).alias("total_seconds"),
                    fn.COALESCE(fn.SUM(Stats.messages), 0).alias("total_messages")
                )
                .join(Stats, JOIN.LEFT_OUTER, on=(Users.user_id == Stats.user_id))
                .where(fn.LOWER(Users.username) == raw_identifier.lower())
                .group_by(Users.user_id, Users.username, Users.avatar)
                .order_by(fn.COALESCE(fn.SUM(Stats.messages), 0).desc(), fn.COALESCE(fn.SUM(Stats.seconds), 0).desc())
            )

        if len(matching_users) == 0:
            # User not found in database; redirect to homepage
            return redirect(url_for("home.home"))

        # If multiple users share this exact username, render the disambiguation page!
        if len(matching_users) > 1 and not request.args.get("user_id"):
            lang = request.cookies.get("lang", "fr")
            users_list = []
            for u in matching_users:
                xp_info = calculate_user_xp_and_level(u.total_seconds, u.total_messages)
                users_list.append({
                    "user_id": str(u.user_id),
                    "username": u.username,
                    "avatar": u.avatar or url_for("static", filename="images/base_avatar_big.png"),
                    "total_messages": u.total_messages or 0,
                    "total_seconds": u.total_seconds or 0,
                    "total_hours": round((u.total_seconds or 0) / 3600, 1),
                    "level": xp_info["level"],
                    "title": xp_info["title_fr"] if lang == "fr" else xp_info["title_en"]
                })
            return render_template(
                "user_disambiguation.html",
                username=raw_identifier,
                users=users_list
            )

        # Single user found
        target_user = matching_users[0]

    # Resolve target user properties
    user_id = int(target_user.user_id)
    display_username = target_user.username or f"User {user_id}"

    lang = request.cookies.get("lang", "fr")
    stats = load_user_profile_stats(user_id, display_username)
    charts = load_user_charts_data(user_id, stats["user_servers_stats"], lang=lang)

    # Check if there are other users with the same username
    homonyms_count = (
        Users
        .select()
        .where(
            (Users.username == display_username) &
            (Users.user_id != user_id)
        )
        .count()
    )

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
        gamification=gamification,
        has_homonyms=(homonyms_count > 0),
        homonyms_count=homonyms_count
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
    # 1. Cumulative personal voice hours progression (Monthly)
    hours_data = get_first_of_month_hours_sum(user_id=user_id)
    chart_data_json = json.dumps({
        "labels": [row["month"] for row in hours_data],
        "hours": [row["total_hours"] for row in hours_data]
    })

    # 1b. Cumulative voice hours progression (Daily - last 30 days)
    daily_hours_data = get_daily_hours_progression(user_id=user_id, days=30)
    daily_chart_data_json = json.dumps({
        "labels": [row["date"] for row in daily_hours_data],
        "hours": [row["total_hours"] for row in daily_hours_data]
    })

    # 2. Cumulative personal messages progression (Monthly)
    messages_data = get_first_of_month_messages_sum(user_id=user_id)
    messages_chart_data_json = json.dumps({
        "labels": [row["month"] for row in messages_data],
        "messages": [row["total_messages"] for row in messages_data]
    })

    # 2b. Cumulative messages progression (Daily - last 30 days)
    daily_messages_data = get_daily_messages_progression(user_id=user_id, days=30)
    daily_messages_chart_data_json = json.dumps({
        "labels": [row["date"] for row in daily_messages_data],
        "messages": [row["total_messages"] for row in daily_messages_data]
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

    # 3b. Daily voice hours deltas (last 30 days)
    daily_hours_diff_data = get_daily_hours_diff(user_id=user_id, days=30)
    daily_hours_chart_data_json = json.dumps({
        "labels": [
            f"{datetime.strptime(row['date'], '%Y-%m-%d').day} {get_month_abbr(datetime.strptime(row['date'], '%Y-%m-%d').month, lang)}"
            for row in daily_hours_diff_data
        ],
        "hours": [row["hours_this_day"] for row in daily_hours_diff_data]
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

    # 4b. Daily messages deltas (last 30 days)
    daily_messages_diff_data = get_daily_messages_diff(user_id=user_id, days=30)
    daily_messages_chart_diff_data_json = json.dumps({
        "labels": [
            f"{datetime.strptime(row['date'], '%Y-%m-%d').day} {get_month_abbr(datetime.strptime(row['date'], '%Y-%m-%d').month, lang)}"
            for row in daily_messages_diff_data
        ],
        "messages": [row["messages_this_day"] for row in daily_messages_diff_data]
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

    # Average daily metrics (last 30 days)
    full_daily_hours = daily_hours_diff_data[:-1] if len(daily_hours_diff_data) > 1 else daily_hours_diff_data
    avg_daily_hours = round(sum(r["hours_this_day"] for r in full_daily_hours) / max(1, len(full_daily_hours)), 1) if full_daily_hours else 0.0

    full_daily_msgs = daily_messages_diff_data[:-1] if len(daily_messages_diff_data) > 1 else daily_messages_diff_data
    avg_daily_msgs = int(sum(r["messages_this_day"] for r in full_daily_msgs) / max(1, len(full_daily_msgs))) if full_daily_msgs else 0

    # Default to daily view if monthly data has less than 3 points (e.g. newly registered user)
    default_granularity = "day" if len(hours_data) < 3 else "month"

    return {
        "chart_data_json": chart_data_json,
        "messages_chart_data_json": messages_chart_data_json,
        "monthly_chart_data_json": monthly_chart_data_json,
        "monthly_messages_chart_data_json": monthly_messages_chart_data_json,
        "daily_chart_data_json": daily_chart_data_json,
        "daily_messages_chart_data_json": daily_messages_chart_data_json,
        "daily_hours_chart_data_json": daily_hours_chart_data_json,
        "daily_messages_chart_diff_data_json": daily_messages_chart_diff_data_json,
        "user_servers_pie_json": user_servers_pie_json,
        "avg_hours": avg_hours,
        "avg_msgs": avg_msgs,
        "avg_daily_hours": avg_daily_hours,
        "avg_daily_msgs": avg_daily_msgs,
        "default_granularity": default_granularity,
    }