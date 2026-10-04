"""Top leaderboard routes for users and servers."""

from datetime import datetime, timedelta
from flask import Blueprint, render_template, request
from peewee import fn, SQL
from app.database import Users, Stats, Servers, VoiceSessions, MessageEvents
from app.gamification import calculate_user_xp_and_level

top_bp = Blueprint("top", __name__)

USERS_PER_PAGE = 20
SERVERS_PER_PAGE = 20

PERIOD_MAP = {
    "24h": 1,
    "7d": 7,
    "15d": 15,
    "1m": 30,
    "6m": 182,
    "1y": 365
}


@top_bp.route("/top/users", methods=["GET"])
def top_users():
    """Render the user leaderboard with filtering by period, server, and sorting criterion."""
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


@top_bp.route("/top/servers", methods=["GET"])
def top_servers():
    """Render the server leaderboard with filtering by period and sorting criterion."""
    servers, total_pages = load_servers()
    return render_template("top_servers.html", servers=servers, total_pages=total_pages)


def load_users() -> tuple[list[dict], int]:
    """Load, filter, rank, and paginate users based on query parameters."""
    period = request.args.get("period", "all")
    sort_by = request.args.get("sort_by", "hours")
    server_id = request.args.get("server_id", "all")
    page = request.args.get("page", 1, type=int)

    search_day = PERIOD_MAP.get(period)

    # Base query for all users tracked in stats
    query = (
        Users
        .select(Users.user_id, Users.username, Users.avatar)
        .join(Stats, on=(Users.user_id == Stats.user_id))
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
    for r in results:
        xp_info = calculate_user_xp_and_level(r["seconds"], r["messages"])
        r["xp"] = xp_info["total_xp"]
        r["level"] = xp_info["level"]

    # Sort results
    if sort_by in ("xp", "level"):
        results.sort(key=lambda x: (x["xp"], x["seconds"], x["messages"]), reverse=True)
    elif sort_by == "messages":
        results.sort(key=lambda x: (x["messages"], x["seconds"]), reverse=True)
    else:
        results.sort(key=lambda x: (x["seconds"], x["messages"]), reverse=True)

    # Compute pagination
    total_items = len(results)
    total_pages = max(1, (total_items + USERS_PER_PAGE - 1) // USERS_PER_PAGE)
    page = max(1, min(page, total_pages))

    paginated_results = results[(page - 1) * USERS_PER_PAGE: page * USERS_PER_PAGE]
    return paginated_results, total_pages


def load_servers() -> tuple[list[dict], int]:
    """Load, filter, rank, and paginate servers based on query parameters."""
    period = request.args.get("period", "all")
    sort_by = request.args.get("sort_by", "hours")
    page = request.args.get("page", 1, type=int)

    search_day = PERIOD_MAP.get(period)

    # Base query for all active servers
    query = (
        Servers
        .select(Servers.server_id, Servers.servername, Servers.avatar)
        .join(Stats, on=(Servers.server_id == Stats.server_id))
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
                "seconds": curr_map.get(server.server_id, (0, 0))[0],
                "messages": curr_map.get(server.server_id, (0, 0))[1]
            }
            for server in query
        ]

    # Sort results
    if sort_by == "messages":
        results.sort(key=lambda x: x["messages"], reverse=True)
    else:
        results.sort(key=lambda x: x["seconds"], reverse=True)

    # Compute pagination
    total_items = len(results)
    total_pages = max(1, (total_items + SERVERS_PER_PAGE - 1) // SERVERS_PER_PAGE)
    page = max(1, min(page, total_pages))

    paginated_results = results[(page - 1) * SERVERS_PER_PAGE: page * SERVERS_PER_PAGE]
    return paginated_results, total_pages
