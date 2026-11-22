import json
from datetime import datetime, timedelta, timezone
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
        from app.server_admin import private_server_ids
        private = private_server_ids()  # a 30-day ranking is a detail of the server: private ones stay out
        rows = cache.get_or_set(("servers", PODIUM_PERIOD), RANKING_CACHE_SECONDS,
                                lambda: _compute_server_ranking(PODIUM_PERIOD))
        rows = rank_with_moves([r for r in rows if int(r["server_id"]) not in private], SERVER_SORT_KEYS["hours"])
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


VOTERS_CACHE_SECONDS = 60


def _top_voters(limit: int = 3) -> list[dict]:
    """Members with the most top.gg votes over the last 30 days (number of votes, like the Supporter badge);
    whoever got there first wins a tie. Bots and private profiles are left out."""
    from app.timeline import hidden_user_ids

    def compute() -> list[dict]:
        since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=30)
        try:
            rows = db.execute_sql(
                "SELECT v.user_id, COUNT(*), u.username, u.avatar FROM topgg_votes v LEFT JOIN users u ON u.user_id = v.user_id "
                "WHERE v.created_at >= %s GROUP BY v.user_id, u.username, u.avatar "
                "ORDER BY COUNT(*) DESC, MAX(v.created_at) ASC LIMIT %s", (since, limit + 20)).fetchall()
        except Exception:
            db.rollback()
            return []
        hidden = hidden_user_ids()
        return [{"user_id": uid, "username": name or tr("Membre {id}", "Member {id}", id=uid), "avatar": avatar, "votes": int(n)}
                for uid, n, name, avatar in rows if int(uid) not in hidden][:limit]

    return cache.get_or_set(("home_top_voters", limit), VOTERS_CACHE_SECONDS, compute)


def _voice_now_podium(limit: int = 3) -> list[dict]:
    """The servers with the most people in voice right now (live, refreshed every 20 seconds)."""
    from app.routes.top import voice_now_by_server

    from app.server_admin import private_server_ids
    private = private_server_ids()  # live data of a private server stays with its members
    live = sorted(((sid, n) for sid, n in voice_now_by_server().items() if n > 0 and sid not in private), key=lambda x: -x[1])[:limit]
    if not live:
        return []
    names = {s.server_id: s for s in Servers.select(Servers.server_id, Servers.servername, Servers.avatar)
             .where(Servers.server_id.in_([sid for sid, _ in live]))}
    return [{"server_id": sid, "servername": (names[sid].servername if sid in names else None) or tr("Serveur {id}", "Server {id}", id=sid),
             "avatar": names[sid].avatar if sid in names else None, "in_voice": n} for sid, n in live]


@home_bp.route("/", methods=["GET"])
def home():
    """Render the main dashboard with global application metrics, 30-day activity, and database statistics."""
    from app.topgg_votes import VOTE_URL
    stats = load_dashboard_stats()
    # Votes move every few minutes: read apart from the dashboard figures, with their own short cache
    return render_template("home.html", stats=stats, top_voters=_top_voters(3), voice_now=_voice_now_podium(3), vote_url=VOTE_URL)


@home_bp.route("/supports", methods=["GET"])
def supports():
    """Help page in tabs: get started, commands, progression, badges, website, server management, FAQ, links."""
    from app.gamification import XP_PER_VOTE, badge_ladders, title_ladder
    from app.i18n import current_lang
    from app.topgg_votes import VOTE_URL
    from app.server_admin import MAX_MANAGERS, permission_texts
    lang = current_lang()
    return render_template("supports.html", titles=title_ladder(lang), badge_ladders=badge_ladders(lang),
                           xp_per_vote=XP_PER_VOTE, vote_url=VOTE_URL, perms=permission_texts(lang),
                           max_managers=MAX_MANAGERS)


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


def _people_on_servers() -> int | None:
    """Different people on the servers that have the bot, active or not (latest bot snapshot, every 15 min).

    Same figure as "Membres uniques" in the admin; None before bot v3.3.0 wrote its first snapshot.
    """
    try:
        row = db.execute_sql("SELECT unique_members FROM bot_member_snapshots ORDER BY recorded_at DESC LIMIT 1").fetchone()
    except Exception:
        db.rollback()
        return None
    return int(row[0]) if row else None


def load_dashboard_stats() -> dict:
    """Collect global metrics: 30-day activity delta, all-time totals, database storage sizes, and last snapshot timestamp."""
    lang = current_lang()

    # All-time totals
    nb_users = Users.select().count()
    nb_profiles = Stats.select().count()
    nb_people = _people_on_servers()
    nb_servers = Servers.select().count()  # every server Hourglass has ever tracked
    nb_servers_present = Servers.select().where(Servers.is_bot_present == True).count()  # noqa: E712
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
        "nb_people": nb_people,
        "nb_servers": nb_servers,
        "nb_servers_present": nb_servers_present,
        "nb_messages": nb_messages,
        "nb_time": nb_time,
        "nb_voice_hours_str": nb_voice_hours_str,
        # Chart & Podiums
        "daily_chart_json": daily_chart_json,
        "top_users": top_users,
        "top_servers": top_servers
    }