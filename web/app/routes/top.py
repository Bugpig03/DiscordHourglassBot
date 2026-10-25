"""Members and servers pages (v3): one ranked, searchable list each, replacing the former directories."""

from datetime import datetime, timedelta
from flask import Blueprint, redirect, render_template, request, url_for
from peewee import fn, SQL, JOIN
from app.database import Users, Stats, Servers, VoiceSessions, MessageEvents
from app.cache import cache
from app.gamification import calculate_user_xp_and_level

top_bp = Blueprint("top", __name__)

USERS_PER_PAGE = 20
SERVERS_PER_PAGE = 20

# Full rankings are recomputed at most once a minute per (period, server); search, sort and
# pagination then run in memory, so live search keystrokes and page changes cost no SQL.
RANKING_CACHE_SECONDS = 60

PERIOD_MAP = {
    "24h": 1,
    "7d": 7,
    "15d": 15,
    "1m": 30,
    "6m": 182,
    "1y": 365
}

# Rank movement (▲ / ▼ next to each row): the same ranking computed as it stood N days ago.
# A period window is shifted back by N days; the all-time totals lose the activity of the last N days.
MOVE_DAYS = {"24h": 1}
DEFAULT_MOVE_DAYS = 7

# Sort keys of each ranking, current and previous figures (the first value decides who is ranked at all)
USER_SORT_KEYS = {
    "hours": (("seconds", "messages"), ("prev_seconds", "prev_messages")),
    "messages": (("messages", "seconds"), ("prev_messages", "prev_seconds")),
    "xp": (("xp", "seconds", "messages"), ("prev_xp", "prev_seconds", "prev_messages")),
}
USER_SORT_KEYS["level"] = USER_SORT_KEYS["xp"]
SERVER_SORT_KEYS = {
    "hours": (("seconds",), ("prev_seconds",)),
    "messages": (("messages",), ("prev_messages",)),
}


def move_days(period: str) -> int:
    return MOVE_DAYS.get(period, DEFAULT_MOVE_DAYS)


def _activity_maps(group_by: str, start: datetime, end: datetime | None, server_id: str = "all") -> tuple[dict, dict]:
    """Voice seconds and messages per user or server (group_by "user_id" / "server_id") between start and end."""
    v_key, m_key = getattr(VoiceSessions, group_by), getattr(MessageEvents, group_by)
    voice_q = VoiceSessions.select(v_key, fn.COALESCE(fn.SUM(VoiceSessions.duration_seconds), 0).alias("sec")).where(VoiceSessions.joined_at >= start)
    msg_q = MessageEvents.select(m_key, fn.COALESCE(fn.SUM(MessageEvents.count), 0).alias("msg")).where(MessageEvents.created_at >= start)
    if end is not None:
        voice_q = voice_q.where(VoiceSessions.joined_at < end)
        msg_q = msg_q.where(MessageEvents.created_at < end)
    if server_id != "all":
        voice_q = voice_q.where(VoiceSessions.server_id == int(server_id))
        msg_q = msg_q.where(MessageEvents.server_id == int(server_id))
    voice = {getattr(r, group_by): int(r.sec or 0) for r in voice_q.group_by(v_key)}
    msgs = {getattr(r, group_by): int(r.msg or 0) for r in msg_q.group_by(m_key)}
    return voice, msgs


def _add_previous(results: list[dict], key: str, period: str, server_id: str = "all") -> None:
    """Fill prev_seconds / prev_messages: the figures of each row move_days() ago."""
    search_day = PERIOD_MAP.get(period)
    shift = move_days(period)
    now = datetime.utcnow()
    group_by = "user_id" if key == "user_id" else "server_id"
    if search_day:
        voice, msgs = _activity_maps(group_by, now - timedelta(days=search_day + shift), now - timedelta(days=shift), server_id)
        for r in results:
            rid = int(r[key])
            r["prev_seconds"], r["prev_messages"] = voice.get(rid, 0), msgs.get(rid, 0)
    else:
        voice, msgs = _activity_maps(group_by, now - timedelta(days=shift), None, server_id)
        for r in results:
            rid = int(r[key])
            r["prev_seconds"] = max(0, (r["seconds"] or 0) - voice.get(rid, 0))
            r["prev_messages"] = max(0, (r["messages"] or 0) - msgs.get(rid, 0))


def rank_with_moves(results: list[dict], sort_keys: tuple) -> list[dict]:
    """Copies of the rows sorted by the current figures, with rank, move (places gained) and is_new.

    The cached rows are shared between requests, so they are never modified here.
    """
    cur_keys, prev_keys = sort_keys
    rows = sorted((dict(r) for r in results), key=lambda r: tuple(r.get(k) or 0 for k in cur_keys), reverse=True)
    prev_order = sorted(
        (r for r in rows if (r.get(prev_keys[0]) or 0) > 0),
        key=lambda r: tuple(r.get(k) or 0 for k in prev_keys), reverse=True,
    )
    prev_rank = {id(r): i for i, r in enumerate(prev_order, 1)}
    for i, r in enumerate(rows, 1):
        r["rank"] = i
        r["move"], r["is_new"] = 0, False
        if (r.get(cur_keys[0]) or 0) <= 0:
            continue
        if id(r) in prev_rank:
            r["move"] = prev_rank[id(r)] - i
        else:
            r["is_new"] = True
    return rows


@top_bp.route("/members", methods=["GET"])
def top_users():
    """Members page: ranking by voice/messages/XP or A–Z, with search, period and server filters."""
    users, total_pages = load_users()
    servers = list(Servers.select().order_by(Servers.servername))
    selected_server = None
    server_id = request.args.get("server_id", "all")
    if server_id and server_id != "all":
        try:
            selected_server = next((s for s in servers if str(s.server_id) == str(server_id)), None)
        except Exception:
            selected_server = None

    return render_template(
        "top_users.html",
        users=users,
        servers=servers,
        total_pages=total_pages,
        selected_server=selected_server
    )


@top_bp.route("/servers", methods=["GET"])
def top_servers():
    """Servers page: ranking by voice/messages or A–Z, with search and period filters."""
    servers, total_pages = load_servers()
    return render_template("top_servers.html", servers=servers, total_pages=total_pages)


@top_bp.route("/top", methods=["GET"])
@top_bp.route("/top/users", methods=["GET"])
def legacy_top_users():
    """Former leaderboard URL: permanent redirect keeping every filter."""
    return redirect(url_for("top.top_users", **request.args.to_dict()), code=301)


@top_bp.route("/top/servers", methods=["GET"])
def legacy_top_servers():
    """Former leaderboard URL: permanent redirect keeping every filter."""
    return redirect(url_for("top.top_servers", **request.args.to_dict()), code=301)


def _compute_user_ranking(period: str, server_id: str) -> list[dict]:
    """Every member with voice time, messages and XP for a period / server (cached by load_users)."""
    search_day = PERIOD_MAP.get(period)

    # Every known user (members without tracked activity rank last with 0)
    query = (
        Users
        .select(Users.user_id, Users.username, Users.avatar)
        .join(Stats, JOIN.LEFT_OUTER, on=(Users.user_id == Stats.user_id))
    )

    if server_id != "all":
        query = query.where(Stats.server_id == int(server_id))

    query = query.group_by(Users.user_id)

    # Fast batch aggregation when a period filter is requested
    if search_day:
        now = datetime.utcnow()
        since_days = now - timedelta(days=search_day)

        voice_q = (
            VoiceSessions
            .select(
                VoiceSessions.user_id,
                fn.COALESCE(fn.SUM(VoiceSessions.duration_seconds), 0).alias("delta_sec")
            )
            .where(VoiceSessions.joined_at >= since_days)
        )
        if server_id != "all":
            voice_q = voice_q.where(VoiceSessions.server_id == int(server_id))
        voice_map = {row.user_id: int(row.delta_sec or 0) for row in voice_q.group_by(VoiceSessions.user_id)}

        msg_q = (
            MessageEvents
            .select(
                MessageEvents.user_id,
                fn.COALESCE(fn.SUM(MessageEvents.count), 0).alias("delta_msg")
            )
            .where(MessageEvents.created_at >= since_days)
        )
        if server_id != "all":
            msg_q = msg_q.where(MessageEvents.server_id == int(server_id))
        msg_map = {row.user_id: int(row.delta_msg or 0) for row in msg_q.group_by(MessageEvents.user_id)}

        # Add active voice sessions in real time
        try:
            active_q = (
                VoiceSessions
                .select(
                    VoiceSessions.user_id,
                    fn.COALESCE(fn.SUM(SQL("GREATEST(0, EXTRACT(EPOCH FROM (NOW() - joined_at))::INT)")), 0).alias("active_sec")
                )
                .where(VoiceSessions.left_at.is_null(True))
            )
            if server_id != "all":
                active_q = active_q.where(VoiceSessions.server_id == int(server_id))
            for row in active_q.group_by(VoiceSessions.user_id):
                voice_map[row.user_id] = voice_map.get(row.user_id, 0) + int(row.active_sec or 0)
        except Exception:
            pass

        results = []
        for user in query:
            u_sec = voice_map.get(user.user_id, 0)
            u_msg = msg_map.get(user.user_id, 0)
            results.append({
                "user_id": str(user.user_id),
                "username": user.username,
                "avatar_url": user.avatar,
                "seconds": u_sec,
                "messages": u_msg
            })
    else:
        # All-time stats queried in bulk
        curr_cond = (Stats.server_id == int(server_id)) if server_id != "all" else None
        curr_query = (
            Stats
            .select(
                Stats.user_id,
                fn.SUM(Stats.seconds).alias("curr_sec"),
                fn.SUM(Stats.messages).alias("curr_msg")
            )
        )
        if curr_cond is not None:
            curr_query = curr_query.where(curr_cond)
        curr_data = curr_query.group_by(Stats.user_id)
        curr_map = {row.user_id: (row.curr_sec or 0, row.curr_msg or 0) for row in curr_data}

        results = [
            {
                "user_id": str(user.user_id),
                "username": user.username,
                "avatar_url": user.avatar,
                "seconds": curr_map.get(user.user_id, (0, 0))[0],
                "messages": curr_map.get(user.user_id, (0, 0))[1]
            }
            for user in query
        ]

    # Compute XP and level for all users
    _add_previous(results, "user_id", period, server_id)
    for r in results:
        xp_info = calculate_user_xp_and_level(r["seconds"], r["messages"])
        r["xp"] = xp_info["total_xp"]
        r["level"] = xp_info["level"]
        r["prev_xp"] = calculate_user_xp_and_level(r["prev_seconds"], r["prev_messages"])["total_xp"]

    return results


def load_users() -> tuple[list[dict], int]:
    """Load, filter, rank, and paginate users based on query parameters."""
    period = request.args.get("period", "all")
    sort_by = request.args.get("sort_by", "hours")
    server_id = request.args.get("server_id", "all")
    if not str(server_id).isdigit():
        server_id = "all"
    if period not in PERIOD_MAP:
        period = "all"
    page = request.args.get("page", 1, type=int)
    search_query = request.args.get("q", "").strip()

    results = cache.get_or_set(
        ("members", period, server_id), RANKING_CACHE_SECONDS, lambda: _compute_user_ranking(period, server_id)
    )
    # Rank the whole list first, so a search still shows each member's real rank and movement
    if sort_by == "name":
        results = sorted(results, key=lambda x: (x["username"] or "").lower())
    else:
        results = rank_with_moves(results, USER_SORT_KEYS.get(sort_by, USER_SORT_KEYS["hours"]))
    if search_query:
        needle = search_query.lower()
        results = [r for r in results if needle in (r["username"] or "").lower()]

    # Compute pagination
    total_items = len(results)
    total_pages = max(1, (total_items + USERS_PER_PAGE - 1) // USERS_PER_PAGE)
    page = max(1, min(page, total_pages))

    paginated_results = results[(page - 1) * USERS_PER_PAGE: page * USERS_PER_PAGE]
    return paginated_results, total_pages


def _compute_server_ranking(period: str) -> list[dict]:
    """Every server with voice time and messages for a period (cached by load_servers)."""
    search_day = PERIOD_MAP.get(period)

    # Every known server, including those the bot has left (flagged in the list)
    query = (
        Servers
        .select(Servers.server_id, Servers.servername, Servers.avatar, Servers.is_bot_present)
        .join(Stats, JOIN.LEFT_OUTER, on=(Servers.server_id == Stats.server_id))
        .group_by(Servers.server_id)
    )

    if search_day:
        now = datetime.utcnow()
        since_days = now - timedelta(days=search_day)

        voice_q = (
            VoiceSessions
            .select(
                VoiceSessions.server_id,
                fn.COALESCE(fn.SUM(VoiceSessions.duration_seconds), 0).alias("delta_sec")
            )
            .where(VoiceSessions.joined_at >= since_days)
            .group_by(VoiceSessions.server_id)
        )
        voice_map = {row.server_id: int(row.delta_sec or 0) for row in voice_q}

        msg_q = (
            MessageEvents
            .select(
                MessageEvents.server_id,
                fn.COALESCE(fn.SUM(MessageEvents.count), 0).alias("delta_msg")
            )
            .where(MessageEvents.created_at >= since_days)
            .group_by(MessageEvents.server_id)
        )
        msg_map = {row.server_id: int(row.delta_msg or 0) for row in msg_q}

        # Add active voice sessions in real time
        try:
            active_q = (
                VoiceSessions
                .select(
                    VoiceSessions.server_id,
                    fn.COALESCE(fn.SUM(SQL("GREATEST(0, EXTRACT(EPOCH FROM (NOW() - joined_at))::INT)")), 0).alias("active_sec")
                )
                .where(VoiceSessions.left_at.is_null(True))
                .group_by(VoiceSessions.server_id)
            )
            for row in active_q:
                voice_map[row.server_id] = voice_map.get(row.server_id, 0) + int(row.active_sec or 0)
        except Exception:
            pass

        results = []
        for server in query:
            s_sec = voice_map.get(server.server_id, 0)
            s_msg = msg_map.get(server.server_id, 0)
            results.append({
                "server_id": server.server_id,
                "servername": server.servername,
                "avatar_url": server.avatar,
                "is_bot_present": server.is_bot_present,
                "seconds": s_sec,
                "messages": s_msg
            })
    else:
        curr_data = (
            Stats
            .select(
                Stats.server_id,
                fn.SUM(Stats.seconds).alias("curr_sec"),
                fn.SUM(Stats.messages).alias("curr_msg")
            )
            .group_by(Stats.server_id)
        )
        curr_map = {row.server_id: (row.curr_sec or 0, row.curr_msg or 0) for row in curr_data}

        results = [
            {
                "server_id": server.server_id,
                "servername": server.servername,
                "avatar_url": server.avatar,
                "is_bot_present": server.is_bot_present,
                "seconds": curr_map.get(server.server_id, (0, 0))[0],
                "messages": curr_map.get(server.server_id, (0, 0))[1]
            }
            for server in query
        ]

    _add_previous(results, "server_id", period)
    return results


def load_servers() -> tuple[list[dict], int]:
    """Load, filter, rank, and paginate servers based on query parameters."""
    period = request.args.get("period", "all")
    sort_by = request.args.get("sort_by", "hours")
    if period not in PERIOD_MAP:
        period = "all"
    page = request.args.get("page", 1, type=int)
    search_query = request.args.get("q", "").strip()

    results = cache.get_or_set(("servers", period), RANKING_CACHE_SECONDS, lambda: _compute_server_ranking(period))
    # Rank the whole list first, so a search still shows each server's real rank and movement
    if sort_by == "name":
        results = sorted(results, key=lambda x: (x["servername"] or "").lower())
    else:
        results = rank_with_moves(results, SERVER_SORT_KEYS.get(sort_by, SERVER_SORT_KEYS["hours"]))
    if search_query:
        needle = search_query.lower()
        results = [r for r in results if needle in (r["servername"] or "").lower()]

    # Compute pagination
    total_items = len(results)
    total_pages = max(1, (total_items + SERVERS_PER_PAGE - 1) // SERVERS_PER_PAGE)
    page = max(1, min(page, total_pages))

    paginated_results = results[(page - 1) * SERVERS_PER_PAGE: page * SERVERS_PER_PAGE]
    return paginated_results, total_pages
