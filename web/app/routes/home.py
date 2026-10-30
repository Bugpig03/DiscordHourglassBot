import json
from datetime import datetime, timedelta
from flask import Blueprint, render_template
from peewee import fn, SQL
from app.database import db, Users, Servers, Stats, VoiceSessions, MessageEvents, LiveServerStatus
from app.functions import (
    format_date_heure_localized, ConvertSecondsToTime, _get_activity_delta,
    get_daily_activity_last_30_days, get_partial_period,
)
from app.i18n import current_lang, day_month, format_number, month_abbr, tr
from app.cache import cache
from app.routes.top import (
    RANKING_CACHE_SECONDS, SERVER_SORT_KEYS, USER_SORT_KEYS, _compute_server_ranking, _compute_user_ranking, rank_with_moves,
    without_bots,
)

home_bp = Blueprint("home", __name__)

PODIUM_PERIOD = "1m"  # last 30 days
HOURGLASS_BOT_ID = 1210665993328926750


def _podium(kind: str, limit: int) -> list[dict]:
    """Top members ("members") or servers ("servers") by voice time over the last 30 days, messages breaking ties."""
    if kind == "members":
        rows = cache.get_or_set(("members", PODIUM_PERIOD, "all"), RANKING_CACHE_SECONDS,
                                lambda: _compute_user_ranking(PODIUM_PERIOD, "all"))
        # Real members only: Discord bots and apps (and Hourglass itself) are left out
        rows = rank_with_moves([r for r in without_bots(rows) if int(r["user_id"]) != HOURGLASS_BOT_ID], USER_SORT_KEYS["hours"])
    else:
        rows = cache.get_or_set(("servers", PODIUM_PERIOD), RANKING_CACHE_SECONDS,
                                lambda: _compute_server_ranking(PODIUM_PERIOD))
        rows = rank_with_moves(rows, SERVER_SORT_KEYS["hours"])
    podium = []
    for r in rows:
        if len(podium) == limit or not (r["seconds"] or r["messages"]):
            break
        entry = {"avatar": r["avatar_url"], "hours": round((r["seconds"] or 0) / 3600.0, 1), "messages": int(r["messages"] or 0)}
        if kind == "members":
            entry.update(user_id=r["user_id"], username=r["username"] or tr("Membre {id}", "Member {id}", id=r["user_id"]))
        else:
            entry.update(server_id=r["server_id"], servername=r["servername"] or tr("Serveur {id}", "Server {id}", id=r["server_id"]))
        podium.append(entry)
    return podium


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
    lang = current_lang()

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
    nb_voice_hours_str = format_number(total_voice_secs // 3600) + " h"

    # 30-Day Activity Delta
    delta_30d = _get_activity_delta(30)
    time_30d = ConvertSecondsToTime(delta_30d["seconds"])
    messages_30d = delta_30d["messages"]
    hours_30d_num = round(delta_30d["seconds"] / 3600.0, 1)

    # Daily Activity Chart Data for Home Dashboard
    daily_activity_data = get_daily_activity_last_30_days()
    days = [datetime.strptime(row['date'], '%Y-%m-%d') for row in daily_activity_data]
    daily_chart_json = json.dumps({
        "labels": [day_month(d.day, d.month, lang) for d in days],
        # Axis: every day number, with the month under the first day shown and under each 1st of the month
        "ticks": [
            [str(d.day), month_abbr(d.month, lang) if i == 0 or d.day == 1 else ""]
            for i, d in enumerate(days)
        ],
        "weekend": [d.weekday() >= 5 for d in days],
        "hours": [row["hours"] for row in daily_activity_data],
        "messages": [row["messages"] for row in daily_activity_data],
        "partial": get_partial_period(daily_activity_data, "day"),
    })

    # Podiums: the 3 most active members and servers of the last 30 days (same figures as the "30 days"
    # filter of the Members and Servers pages, whose cached rankings are reused)
    top_users = _podium("members", 3)
    top_servers = _podium("servers", 3)

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