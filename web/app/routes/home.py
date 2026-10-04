import json
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request
from peewee import fn, SQL
from app.database import db, Users, Servers, Stats, VoiceSessions, MessageEvents, LiveServerStatus
from app.functions import (
    format_date_heure_localized, ConvertSecondsToTime, _get_activity_delta,
    get_daily_activity_last_30_days, get_top_users_podium, get_top_servers_podium,
    get_month_abbr
)

home_bp = Blueprint("home", __name__)


@home_bp.route("/", methods=["GET"])
def home():
    """Render the main dashboard with global application metrics, 30-day activity, and database statistics."""
    stats = load_dashboard_stats()
    return render_template("home.html", stats=stats)


@home_bp.route("/supports", methods=["GET"])
def supports():
    """Render the project support and help information page."""
    return render_template("supports.html")


@home_bp.route("/confidentialite", methods=["GET"])
@home_bp.route("/privacy-policy", methods=["GET"])
@home_bp.route("/privacy", methods=["GET"])
def privacy():
    """Render the Privacy Policy / RGPD compliance page."""
    return render_template("privacy.html")


@home_bp.route("/cgu", methods=["GET"])
@home_bp.route("/terms-of-services", methods=["GET"])
@home_bp.route("/terms-of-service", methods=["GET"])
@home_bp.route("/terms", methods=["GET"])
def terms():
    """Render the Terms of Service (CGU) page."""
    return render_template("terms.html")


def load_dashboard_stats() -> dict:
    """Collect global metrics: 30-day activity delta, all-time totals, database storage sizes, and last snapshot timestamp."""
    lang = request.cookies.get("lang", "fr")

    # All-time totals
    nb_users = Users.select().count()
    nb_profiles = Stats.select().count()
    nb_servers = Servers.select().count()
    nb_messages = Stats.select(fn.SUM(Stats.messages)).scalar() or 0
    active_secs = (
        VoiceSessions
        .select(fn.COALESCE(fn.SUM(SQL("GREATEST(0, EXTRACT(EPOCH FROM (NOW() - joined_at))::INT)")), 0))
        .where(VoiceSessions.left_at.is_null(True))
        .scalar() or 0
    )
    total_voice_secs = (Stats.select(fn.SUM(Stats.seconds)).scalar() or 0) + active_secs
    nb_time = ConvertSecondsToTime(total_voice_secs)
    nb_voice_hours_str = f"{(total_voice_secs // 3600):,}".replace(",", " ") + " h"

    # 30-Day Activity Delta
    delta_30d = _get_activity_delta(30)
    time_30d = ConvertSecondsToTime(delta_30d["seconds"])
    messages_30d = delta_30d["messages"]
    hours_30d_num = round(delta_30d["seconds"] / 3600.0, 1)

    # Daily Activity Chart Data for Home Dashboard
    daily_activity_data = get_daily_activity_last_30_days()
    daily_chart_json = json.dumps({
        "labels": [
            f"{datetime.strptime(row['date'], '%Y-%m-%d').day} {get_month_abbr(datetime.strptime(row['date'], '%Y-%m-%d').month, lang)}"
            for row in daily_activity_data
        ],
        "hours": [row["hours"] for row in daily_activity_data],
        "messages": [row["messages"] for row in daily_activity_data]
    })

    # Podiums (Top 3 Members & Top 3 Servers)
    top_users = get_top_users_podium(3)
    top_servers = get_top_servers_podium(3)

    return {
        # 30-day activity metrics
        "time_30d": time_30d,
        "seconds_30d": delta_30d["seconds"],
        "messages_30d": messages_30d,
        "hours_30d_num": hours_30d_num,
        # All-time global metrics
        "nb_users": nb_users,
        "nb_profiles": nb_profiles,
        "nb_servers": nb_servers,
        "nb_messages": nb_messages,
        "nb_time": nb_time,
        "nb_voice_hours_str": nb_voice_hours_str,
        # Chart & Podiums
        "daily_chart_json": daily_chart_json,
        "top_users": top_users,
        "top_servers": top_servers
    }