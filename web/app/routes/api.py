"""Public REST API endpoints for accessing user, server, and statistical data."""

import html
from flask import Blueprint, jsonify, request, Response
from peewee import fn, JOIN, SQL
from app.database import Servers, Users, Stats
from app.functions import (
    get_user_id_by_username,
    get_user_avatar_url,
    get_global_rank_by_user_id_seconds,
    get_total_seconds_by_user_id,
    get_total_message_by_user_id,
    ConvertSecondsToTime,
    ConvertSecondsToHours,
    get_user_servers_stats,
    get_activity_sum_last_X_days,
    get_user_join_date,
    get_user_raw_join_date,
    get_servername_by_server_id,
    get_total_seconds_by_server_id,
    get_total_message_by_server_id,
    get_user_count_by_server_id,
    get_user_rank_in_server,
    get_server_rank,
    get_server_join_date,
    get_server_avatar_url,
)
from app.gamification import calculate_user_xp_and_level, calculate_user_badges

api_bp = Blueprint("api", __name__)


@api_bp.route("/api/users", methods=["GET"])
def get_users():
    """Retrieve all users with their Discord IDs, usernames, and avatar URLs."""
    users = Users.select(Users.user_id, Users.username, Users.avatar)
    data = [
        {
            "user_id": u.user_id,
            "username": u.username,
            "avatar": u.avatar,
        }
        for u in users
    ]
    return jsonify(data)


@api_bp.route("/api/servers", methods=["GET"])
def get_servers():
    """Retrieve all servers with their IDs, names, and icon URLs."""
    servers = Servers.select(Servers.server_id, Servers.servername, Servers.avatar)
    data = [
        {
            "server_id": s.server_id,
            "servername": s.servername,
            "avatar": s.avatar,
        }
        for s in servers
    ]
    return jsonify(data)


@api_bp.route("/api/user/<int:user_id>", methods=["GET"])
def get_user(user_id: int):
    """Retrieve details for a single user by user ID."""
    try:
        user = Users.get(Users.user_id == user_id)
        return jsonify({
            "user_id": user.user_id,
            "username": user.username,
            "avatar": user.avatar,
        })
    except Users.DoesNotExist:
        return jsonify({"error": "User not found"}), 404


@api_bp.route("/api/server/<int:server_id>", methods=["GET"])
def get_server(server_id: int):
    """Retrieve details for a single server by server ID."""
    try:
        server = Servers.get(Servers.server_id == server_id)
        return jsonify({
            "server_id": server.server_id,
            "servername": server.servername,
            "avatar": server.avatar,
        })
    except Servers.DoesNotExist:
        return jsonify({"error": "Server not found"}), 404


@api_bp.route("/api/stats", defaults={"user_id": None, "server_id": None}, methods=["GET"])
@api_bp.route("/api/stats/<int:user_id>", defaults={"server_id": None}, methods=["GET"])
@api_bp.route("/api/stats/<int:user_id>/<int:server_id>", methods=["GET"])
def get_stats(user_id: int | None, server_id: int | None):
    """Retrieve cumulative statistics across global, user-specific, or server-specific scopes."""
    try:
        # Case 1: Global statistics across the entire bot
        if user_id is None and server_id is None:
            stat = (
                Stats
                .select(
                    fn.SUM(Stats.messages).alias("messages"),
                    fn.SUM(Stats.seconds).alias("seconds"),
                    fn.SUM(Stats.score).alias("score")
                )
                .dicts()
                .get()
            )
            return jsonify({
                "scope": "global",
                "messages": stat["messages"] or 0,
                "seconds": stat["seconds"] or 0,
                "score": stat["score"] or 0
            })

        # Case 2: Cross-server statistics for a specific user
        if user_id is not None and server_id is None:
            stat = (
                Stats
                .select(
                    fn.SUM(Stats.messages).alias("messages"),
                    fn.SUM(Stats.seconds).alias("seconds"),
                    fn.SUM(Stats.score).alias("score")
                )
                .where(Stats.user_id == user_id)
                .dicts()
                .get()
            )
            return jsonify({
                "scope": f"user:{user_id}",
                "user_id": user_id,
                "messages": stat["messages"] or 0,
                "seconds": stat["seconds"] or 0,
                "score": stat["score"] or 0
            })

        # Case 3: Precise stats for a user on a specific server
        stat = Stats.get((Stats.user_id == user_id) & (Stats.server_id == server_id))
        return jsonify({
            "scope": f"user:{user_id}-server:{server_id}",
            "user_id": stat.user_id,
            "server_id": stat.server_id,
            "messages": stat.messages,
            "seconds": stat.seconds,
            "score": stat.score
        })

    except Stats.DoesNotExist:
        return jsonify({"error": "Stats not found"}), 404


@api_bp.route("/api/search", methods=["GET"])
def search_global():
    """Quick search across users and servers for the global Ctrl+K palette and page search bars."""
    q = request.args.get("q", "").strip()
    target_type = request.args.get("type", "").strip().lower()
    try:
        limit = min(max(int(request.args.get("limit", 6)), 1), 20)
    except (ValueError, TypeError):
        limit = 6

    if not q:
        return jsonify({"users": [], "servers": []})

    # Search Users
    users_data = []
    if target_type in ("", "all", "users", "user"):
        matched_users = (
            Users
            .select(
                Users.user_id,
                Users.username,
                Users.avatar,
                fn.COALESCE(fn.SUM(Stats.seconds), 0).alias("total_seconds"),
                fn.COALESCE(fn.SUM(Stats.messages), 0).alias("total_messages")
            )
            .join(Stats, JOIN.LEFT_OUTER, on=(Users.user_id == Stats.user_id))
            .where(Users.username.contains(q))
            .group_by(Users.user_id, Users.username, Users.avatar)
            .order_by(Users.username)
            .limit(limit)
        )
        for u in matched_users:
            xp_info = calculate_user_xp_and_level(u.total_seconds, u.total_messages)
            users_data.append({
                "username": u.username,
                "avatar": u.avatar or "/static/images/default_avatar.png",
                "level": xp_info["level"],
                "url": f"/profile/{u.username}"
            })

    # Search Servers
    servers_data = []
    if target_type in ("", "all", "servers", "server"):
        matched_servers = (
            Servers.select(Servers.server_id, Servers.servername, Servers.avatar)
            .where(Servers.servername.contains(q))
            .order_by(Servers.servername)
            .limit(limit)
        )
        servers_data = [
            {
                "server_id": str(s.server_id),
                "servername": s.servername,
                "avatar": s.avatar or "/static/icons/server.png",
                "url": f"/server/{s.server_id}"
            }
            for s in matched_servers
        ]

    return jsonify({
        "users": users_data,
        "servers": servers_data
    })


# ==========================================
# SVG Generation Helper Utilities
# ==========================================

def _resolve_user(identifier: str) -> tuple[int | None, str | None, str | None]:
    """Resolve a user by numeric user_id or username. Returns (user_id, username, avatar_url)."""
    if not identifier:
        return None, None, None
    raw = str(identifier).strip()
    user = None
    if raw.isdigit():
        user = Users.select().where(Users.user_id == int(raw)).first()
    if not user:
        user = Users.select().where(Users.username == raw).first()
    if not user:
        user = Users.select().where(fn.LOWER(Users.username) == raw.lower()).first()
    if user:
        avatar = user.avatar or "/static/images/default_avatar.png"
        return user.user_id, user.username, avatar
    return None, None, None


def _resolve_server(server_id: int | str) -> tuple[int | None, str | None, str | None]:
    """Resolve a server by its ID. Returns (server_id, servername, avatar_url)."""
    try:
        sid = int(server_id)
    except (ValueError, TypeError):
        return None, None, None
    server = Servers.select().where(Servers.server_id == sid).first()
    if server:
        avatar = server.avatar or "/static/icons/server.png"
        return server.server_id, server.servername, avatar
    return None, None, None


def _format_time_short(seconds: int) -> str:
    """Format seconds into concise 'Xh Ym' or 'Ym'."""
    seconds = int(seconds or 0)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    if h > 0:
        return f"{h}h {m}m"
    return f"{m}m"


def _render_error_svg(title: str, message: str, width: int = 540, height: int = 180) -> Response:
    """Return a stylish standalone SVG error card with 404 status."""
    escaped_title = html.escape(title)
    escaped_msg = html.escape(message)
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
    <defs>
        <linearGradient id="errBg" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#0f172a"/>
            <stop offset="100%" stop-color="#1e293b"/>
        </linearGradient>
    </defs>
    <rect width="{width}" height="{height}" rx="18" fill="url(#errBg)" stroke="#ef4444" stroke-opacity="0.4" stroke-width="1.2"/>
    <circle cx="50" cy="{height // 2}" r="22" fill="rgba(239, 68, 68, 0.15)" stroke="#ef4444" stroke-width="1.5"/>
    <text x="50" y="{height // 2 + 7}" fill="#ef4444" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="20" font-weight="900" text-anchor="middle">✕</text>
    <text x="88" y="{height // 2 - 6}" fill="#f87171" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="16" font-weight="800">{escaped_title}</text>
    <text x="88" y="{height // 2 + 18}" fill="#94a3b8" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="12" font-weight="500">{escaped_msg}</text>
</svg>"""
    resp = Response(svg, mimetype="image/svg+xml", status=404)
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return resp


def _svg_response(svg_content: str, max_age: int = 180) -> Response:
    """Wrap SVG content into an HTTP Response with SVG mimetype and Cache-Control."""
    resp = Response(svg_content, mimetype="image/svg+xml")
    resp.headers["Cache-Control"] = f"public, max-age={max_age}"
    return resp


# ==========================================
# SVG Card Endpoints
# ==========================================

# 1. Global User Stat Card (!allstats [user])
@api_bp.route("/api/card/user/<user_identifier>", methods=["GET"])
@api_bp.route("/api/card/allstats/<user_identifier>", methods=["GET"])
def get_user_stat_card(user_identifier: str):
    """Generate and return a stylish standalone SVG stat card for a user across all servers."""
    lang = request.args.get("lang", "fr")
    user_id, username, avatar_url = _resolve_user(user_identifier)
    if user_id is None:
        return _render_error_svg(
            "Utilisateur introuvable" if lang != "en" else "User not found",
            f"Aucun utilisateur trouvé pour '{user_identifier}'" if lang != "en" else f"No user found for '{user_identifier}'"
        )

    total_seconds = get_total_seconds_by_user_id(user_id) or 0
    total_messages = get_total_message_by_user_id(user_id) or 0
    rank = get_global_rank_by_user_id_seconds(user_id)
    servers_stats = get_user_servers_stats(user_id)
    activity_30d = get_activity_sum_last_X_days(user_id, 30)
    join_date = get_user_join_date(user_id, lang=lang)

    # Gamification
    xp_info = calculate_user_xp_and_level(total_seconds, total_messages)
    badges = calculate_user_badges({
        "total_seconds": total_seconds,
        "total_message": total_messages,
        "rank": rank,
        "user_servers_stats": servers_stats,
        "total_time_last_30d": activity_30d["seconds"],
        "join_date": join_date,
        "raw_join_date": get_user_raw_join_date(user_id),
    }, lang=lang)

    unlocked_badges = [b for b in badges if b["unlocked"]]
    top_badges = unlocked_badges[:3]

    level = xp_info["level"]
    title = xp_info["title_fr"] if lang == "fr" else xp_info["title_en"]
    total_xp = xp_info["total_xp"]
    progress_pct = xp_info["progress_percent"]
    rank_num = rank if isinstance(rank, int) and rank > 0 else (int(rank) if isinstance(rank, str) and rank.strip().isdigit() else None)
    rank_str = f"#{rank_num}" if rank_num is not None else ("Non classé" if lang == "fr" else "Unranked")
    hours_val = round(total_seconds / 3600, 1)

    badge_svg_chips = []
    chip_x = 310
    for b in top_badges:
        chip = f"""<g transform="translate({chip_x}, 152)">
            <rect width="66" height="26" rx="6" fill="rgba(56, 189, 248, 0.12)" stroke="rgba(56, 189, 248, 0.35)"/>
            <g transform="translate(24, 4) scale(0.75)" stroke="#38bdf8" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{b.get('svg_path', '')}</g>
        </g>"""
        badge_svg_chips.append(chip)
        chip_x += 72

    badges_rendered = "".join(badge_svg_chips) if badge_svg_chips else f"""<text x="310" y="170" fill="#64748b" font-family="-apple-system, sans-serif" font-size="11" font-style="italic">{'Aucun badge débloqué' if lang == 'fr' else 'No badges unlocked yet'}</text>"""
    badges_label = "Badges :" if lang == "fr" else "Badges:"
    voice_label = "VOCAL" if lang == "fr" else "VOICE"
    msgs_label = "MESSAGES"
    xp_label = "XP TOTAL" if lang == "fr" else "TOTAL XP"
    next_lvl_label = f"PROCHAIN NIVEAU : {progress_pct}%" if lang == "fr" else f"NEXT LEVEL: {progress_pct}%"
    rank_label = "RANG" if lang == "fr" else "RANK"

    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" width="540" height="210" viewBox="0 0 540 210">
    <defs>
        <linearGradient id="cardBg" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#0f172a"/>
            <stop offset="100%" stop-color="#1e293b"/>
        </linearGradient>
        <linearGradient id="cyanGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#38bdf8"/>
            <stop offset="100%" stop-color="#818cf8"/>
        </linearGradient>
        <filter id="cardGlow" x="-10%" y="-10%" width="120%" height="120%">
            <feDropShadow dx="0" dy="8" stdDeviation="12" flood-color="#000000" flood-opacity="0.45"/>
        </filter>
        <clipPath id="avatarClip">
            <circle cx="65" cy="65" r="36"/>
        </clipPath>
    </defs>

    <rect width="540" height="210" rx="20" fill="url(#cardBg)" stroke="rgba(255, 255, 255, 0.12)" stroke-width="1.2" filter="url(#cardGlow)"/>
    <ellipse cx="140" cy="15" rx="130" ry="25" fill="#38bdf8" opacity="0.12"/>

    <!-- Avatar circle with glow -->
    <circle cx="65" cy="65" r="39" fill="rgba(56, 189, 248, 0.25)" stroke="#38bdf8" stroke-width="1.5"/>
    <circle cx="65" cy="65" r="36" fill="#1e293b"/>
    <image href="{html.escape(avatar_url)}" x="29" y="29" width="72" height="72" clip-path="url(#avatarClip)" preserveAspectRatio="xMidYMid slice"/>

    <!-- User Information -->
    <text x="120" y="55" fill="#ffffff" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="20" font-weight="800" letter-spacing="-0.3px">{html.escape(username)}</text>
    
    <!-- Level Badge -->
    <g transform="translate(120, 68)">
        <rect width="180" height="22" rx="6" fill="#5865F2" fill-opacity="0.25" stroke="#5865F2" stroke-width="1"/>
        <text x="90" y="15" fill="#818cf8" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="11" font-weight="800" text-anchor="middle">LVL {level} • {html.escape(title)}</text>
    </g>

    <!-- Global Rank Badge -->
    <g transform="translate(425, 36)">
        <rect width="85" height="28" rx="8" fill="rgba(255, 255, 255, 0.05)" stroke="rgba(255, 255, 255, 0.12)" stroke-width="1"/>
        <text x="12" y="18" fill="#94a3b8" font-family="-apple-system, sans-serif" font-size="10" font-weight="600">{rank_label}</text>
        <text x="70" y="19" fill="#38bdf8" font-family="-apple-system, sans-serif" font-size="13" font-weight="800" text-anchor="end">{rank_str}</text>
    </g>

    <!-- Divider -->
    <line x1="28" y1="106" x2="512" y2="106" stroke="rgba(255, 255, 255, 0.08)" stroke-width="1"/>

    <!-- Stats Grid -->
    <g transform="translate(30, 126)">
        <text x="0" y="0" fill="#94a3b8" font-family="-apple-system, sans-serif" font-size="11" font-weight="700" letter-spacing="0.5px">{voice_label}</text>
        <text x="0" y="20" fill="#ffffff" font-family="-apple-system, sans-serif" font-size="16" font-weight="800">{hours_val}h</text>
    </g>

    <g transform="translate(120, 126)">
        <text x="0" y="0" fill="#94a3b8" font-family="-apple-system, sans-serif" font-size="11" font-weight="700" letter-spacing="0.5px">{msgs_label}</text>
        <text x="0" y="20" fill="#ffffff" font-family="-apple-system, sans-serif" font-size="16" font-weight="800">{total_messages:,}</text>
    </g>

    <g transform="translate(215, 126)">
        <text x="0" y="0" fill="#94a3b8" font-family="-apple-system, sans-serif" font-size="11" font-weight="700" letter-spacing="0.5px">{xp_label}</text>
        <text x="0" y="20" fill="#ffffff" font-family="-apple-system, sans-serif" font-size="16" font-weight="800">{total_xp:,}</text>
    </g>

    <!-- XP Progress Bar -->
    <g transform="translate(30, 168)">
        <rect width="250" height="8" rx="4" fill="rgba(255, 255, 255, 0.08)"/>
        <rect width="{max(6, int(250 * (progress_pct / 100)))}" height="8" rx="4" fill="url(#cyanGrad)"/>
        <text x="0" y="22" fill="#64748b" font-family="-apple-system, sans-serif" font-size="10" font-weight="600">{next_lvl_label}</text>
    </g>

    <!-- Badges Area -->
    <text x="310" y="140" fill="#94a3b8" font-family="-apple-system, sans-serif" font-size="11" font-weight="600">{badges_label}</text>
    {badges_rendered}

    <!-- Brand Watermark -->
    <text x="512" y="196" fill="#475569" font-family="-apple-system, sans-serif" font-size="10" font-weight="700" text-anchor="end">HOURGLASS BOT</text>
</svg>"""
    return _svg_response(svg_content)


# 2. User Stat Card on a Specific Server (!stats [user])
@api_bp.route("/api/card/user/<user_identifier>/server/<int:server_id>", methods=["GET"])
@api_bp.route("/api/card/stats/<user_identifier>/<int:server_id>", methods=["GET"])
def get_user_server_stat_card(user_identifier: str, server_id: int):
    """Generate and return an SVG stat card for a user on a specific server."""
    lang = request.args.get("lang", "fr")
    user_id, username, avatar_url = _resolve_user(user_identifier)
    if user_id is None:
        return _render_error_svg(
            "Utilisateur introuvable" if lang != "en" else "User not found",
            f"Aucun utilisateur trouvé pour '{user_identifier}'" if lang != "en" else f"No user found for '{user_identifier}'"
        )

    server_id, servername, server_avatar = _resolve_server(server_id)
    if server_id is None:
        return _render_error_svg(
            "Serveur introuvable" if lang != "en" else "Server not found",
            f"Aucun serveur trouvé avec l'ID {server_id}" if lang != "en" else f"No server found with ID {server_id}"
        )

    stat = Stats.select().where((Stats.user_id == user_id) & (Stats.server_id == server_id)).first()
    seconds = stat.seconds if stat else 0
    messages = stat.messages if stat else 0
    rank = get_user_rank_in_server(user_id, server_id)
    rank_str = f"#{rank}" if rank else ("Non classé" if lang == "fr" else "Unranked")
    join_date = get_user_join_date(user_id, server_id=server_id, lang=lang)
    xp_info = calculate_user_xp_and_level(seconds, messages)

    level = xp_info["level"]
    title = xp_info["title_fr"] if lang == "fr" else xp_info["title_en"]
    total_xp = xp_info["total_xp"]
    progress_pct = xp_info["progress_percent"]
    hours_val = round(seconds / 3600, 1)

    voice_label = "VOCAL" if lang == "fr" else "VOICE"
    msgs_label = "MESSAGES"
    xp_label = "XP SERVEUR" if lang == "fr" else "SERVER XP"
    next_lvl_label = f"PROCHAIN NIVEAU : {progress_pct}%" if lang == "fr" else f"NEXT LEVEL: {progress_pct}%"
    rank_label = "RANG" if lang == "fr" else "RANK"
    active_since_label = f"Sur ce serveur depuis : {join_date}" if lang == "fr" else f"On this server since: {join_date}"

    clean_username = html.escape((username or "")[:18])
    clean_servername = html.escape((servername or "")[:24])

    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" width="540" height="215" viewBox="0 0 540 215">
    <defs>
        <linearGradient id="cardBg" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#0f172a"/>
            <stop offset="100%" stop-color="#1e293b"/>
        </linearGradient>
        <linearGradient id="cyanGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#38bdf8"/>
            <stop offset="100%" stop-color="#818cf8"/>
        </linearGradient>
        <clipPath id="avatarClip">
            <circle cx="65" cy="65" r="36"/>
        </clipPath>
        <clipPath id="srvIconClip">
            <circle cx="7" cy="7" r="7"/>
        </clipPath>
    </defs>

    <rect width="540" height="215" rx="20" fill="url(#cardBg)" stroke="rgba(255, 255, 255, 0.12)" stroke-width="1.2"/>
    <ellipse cx="140" cy="15" rx="130" ry="25" fill="#38bdf8" opacity="0.12"/>

    <!-- User Avatar -->
    <circle cx="65" cy="65" r="39" fill="rgba(56, 189, 248, 0.25)" stroke="#38bdf8" stroke-width="1.5"/>
    <circle cx="65" cy="65" r="36" fill="#1e293b"/>
    <image href="{html.escape(avatar_url)}" x="29" y="29" width="72" height="72" clip-path="url(#avatarClip)" preserveAspectRatio="xMidYMid slice"/>

    <!-- User Details -->
    <text x="120" y="48" fill="#ffffff" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="20" font-weight="800" letter-spacing="-0.3px">{clean_username}</text>
    
    <!-- Server Subtitle with Icon -->
    <g transform="translate(120, 58)">
        <circle cx="7" cy="7" r="7" fill="#1e293b" stroke="rgba(56, 189, 248, 0.4)" stroke-width="0.8"/>
        <image href="{html.escape(server_avatar)}" x="0" y="0" width="14" height="14" clip-path="url(#srvIconClip)" preserveAspectRatio="xMidYMid slice"/>
        <text x="20" y="11" fill="#38bdf8" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="12" font-weight="600">{clean_servername}</text>
    </g>

    <!-- Level Badge -->
    <g transform="translate(120, 78)">
        <rect width="180" height="20" rx="5" fill="#5865F2" fill-opacity="0.25" stroke="#5865F2" stroke-width="0.8"/>
        <text x="90" y="14" fill="#818cf8" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="10.5" font-weight="800" text-anchor="middle">LVL {level} • {html.escape(title)}</text>
    </g>

    <!-- Server Rank Badge -->
    <g transform="translate(425, 30)">
        <rect width="85" height="28" rx="8" fill="rgba(255, 255, 255, 0.05)" stroke="rgba(255, 255, 255, 0.12)" stroke-width="1"/>
        <text x="12" y="18" fill="#94a3b8" font-family="-apple-system, sans-serif" font-size="10" font-weight="600">{rank_label}</text>
        <text x="70" y="19" fill="#38bdf8" font-family="-apple-system, sans-serif" font-size="13" font-weight="800" text-anchor="end">{rank_str}</text>
    </g>

    <line x1="28" y1="112" x2="512" y2="112" stroke="rgba(255, 255, 255, 0.08)" stroke-width="1"/>

    <!-- Stats Row -->
    <g transform="translate(30, 132)">
        <text x="0" y="0" fill="#94a3b8" font-family="-apple-system, sans-serif" font-size="11" font-weight="700" letter-spacing="0.5px">{voice_label}</text>
        <text x="0" y="20" fill="#ffffff" font-family="-apple-system, sans-serif" font-size="16" font-weight="800">{hours_val}h</text>
    </g>

    <g transform="translate(140, 132)">
        <text x="0" y="0" fill="#94a3b8" font-family="-apple-system, sans-serif" font-size="11" font-weight="700" letter-spacing="0.5px">{msgs_label}</text>
        <text x="0" y="20" fill="#ffffff" font-family="-apple-system, sans-serif" font-size="16" font-weight="800">{messages:,}</text>
    </g>

    <g transform="translate(250, 132)">
        <text x="0" y="0" fill="#94a3b8" font-family="-apple-system, sans-serif" font-size="11" font-weight="700" letter-spacing="0.5px">{xp_label}</text>
        <text x="0" y="20" fill="#ffffff" font-family="-apple-system, sans-serif" font-size="16" font-weight="800">{total_xp:,}</text>
    </g>

    <!-- Progress Bar -->
    <g transform="translate(30, 172)">
        <rect width="250" height="7" rx="3.5" fill="rgba(255, 255, 255, 0.08)"/>
        <rect width="{max(6, int(250 * (progress_pct / 100)))}" height="7" rx="3.5" fill="url(#cyanGrad)"/>
        <text x="0" y="20" fill="#64748b" font-family="-apple-system, sans-serif" font-size="9.5" font-weight="600">{next_lvl_label}</text>
    </g>

    <!-- Join Date & Watermark -->
    <text x="310" y="172" fill="#64748b" font-family="-apple-system, sans-serif" font-size="10.5" font-weight="500">{active_since_label}</text>
    <text x="512" y="196" fill="#475569" font-family="-apple-system, sans-serif" font-size="10" font-weight="700" text-anchor="end">HOURGLASS BOT</text>
</svg>"""
    return _svg_response(svg_content)


# 3. Server Top 10 Vocal Leaderboard (!top)
@api_bp.route("/api/card/top/server/<int:server_id>", methods=["GET"])
@api_bp.route("/api/card/server/<int:server_id>/top", methods=["GET"])
def get_server_top_card(server_id: int):
    """Generate an SVG leaderboard card for the Top 10 voice users on a server."""
    lang = request.args.get("lang", "fr")
    server_id, servername, server_avatar = _resolve_server(server_id)
    if server_id is None:
        return _render_error_svg(
            "Serveur introuvable" if lang != "en" else "Server not found",
            f"Aucun serveur trouvé avec l'ID {server_id}" if lang != "en" else f"No server found with ID {server_id}",
            width=560, height=200
        )

    top_users = (
        Stats
        .select(Stats.user_id, Users.username, Users.avatar, Stats.seconds, Stats.messages)
        .join(Users, on=(Stats.user_id == Users.user_id))
        .where((Stats.server_id == server_id) & (Stats.seconds > 0))
        .order_by(Stats.seconds.desc())
        .limit(10)
        .dicts()
    )

    rows_xml = []
    y_start = 125
    row_height = 37

    for i, r in enumerate(top_users):
        rank = i + 1
        y = y_start + i * row_height
        medal_color = "#f59e0b" if rank == 1 else ("#94a3b8" if rank == 2 else ("#d97706" if rank == 3 else "rgba(255, 255, 255, 0.08)"))
        text_color = "#0f172a" if rank in (1, 2, 3) else "#94a3b8"
        uname = html.escape((r['username'] or 'Inconnu')[:16])
        time_str = _format_time_short(r['seconds'])
        msgs_str = f"{r['messages']:,}".replace(",", " ")
        xp_info = calculate_user_xp_and_level(r['seconds'], r['messages'])
        lvl = xp_info['level']
        bg_bar = f'<rect x="20" y="{y - 24}" width="520" height="33" rx="7" fill="rgba(255, 255, 255, 0.02)"/>' if rank % 2 == 0 else ""
        row = f"""{bg_bar}
        <g transform="translate(26, {y})">
            <circle cx="12" cy="-7" r="11" fill="{medal_color}"/>
            <text x="12" y="-3" fill="{text_color}" font-family="-apple-system, sans-serif" font-size="11" font-weight="800" text-anchor="middle">{rank}</text>
            <text x="36" y="-3" fill="#ffffff" font-family="-apple-system, sans-serif" font-size="13" font-weight="700">{uname}</text>
            <rect x="200" y="-18" width="58" height="20" rx="5" fill="rgba(88, 101, 242, 0.2)" stroke="#5865F2" stroke-width="0.8"/>
            <text x="229" y="-4" fill="#818cf8" font-family="-apple-system, sans-serif" font-size="10" font-weight="800" text-anchor="middle">LVL {lvl}</text>
            <text x="375" y="-3" fill="#38bdf8" font-family="-apple-system, sans-serif" font-size="12" font-weight="800" text-anchor="end">{time_str}</text>
            <text x="500" y="-3" fill="#94a3b8" font-family="-apple-system, sans-serif" font-size="12" font-weight="600" text-anchor="end">{msgs_str}</text>
        </g>"""
        rows_xml.append(row)

    rows_str = "".join(rows_xml) if rows_xml else f'<text x="280" y="220" fill="#64748b" font-family="-apple-system, sans-serif" font-size="13" text-anchor="middle">{"Aucune activité enregistrée sur ce serveur" if lang == "fr" else "No activity recorded on this server yet"}</text>'
    clean_srvname = html.escape((servername or '')[:30])

    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" width="560" height="535" viewBox="0 0 560 535">
    <defs>
        <linearGradient id="topBg" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#0f172a"/>
            <stop offset="100%" stop-color="#1e293b"/>
        </linearGradient>
        <clipPath id="srvTopClip">
            <circle cx="48" cy="46" r="20"/>
        </clipPath>
    </defs>
    <rect width="560" height="535" rx="20" fill="url(#topBg)" stroke="rgba(255, 255, 255, 0.12)" stroke-width="1.2"/>
    
    <!-- Server Avatar & Header -->
    <circle cx="48" cy="46" r="21" fill="none" stroke="#38bdf8" stroke-width="1.5"/>
    <image href="{html.escape(server_avatar)}" x="28" y="26" width="40" height="40" clip-path="url(#srvTopClip)" preserveAspectRatio="xMidYMid slice"/>
    <text x="80" y="42" fill="#ffffff" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="18" font-weight="800">TOP 10 • VOCAL</text>
    <text x="80" y="60" fill="#38bdf8" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="12" font-weight="600">{clean_srvname}</text>

    <!-- Table Header -->
    <rect x="20" y="78" width="520" height="28" rx="6" fill="rgba(255, 255, 255, 0.04)"/>
    <text x="36" y="96" fill="#38bdf8" font-family="-apple-system, sans-serif" font-size="11" font-weight="800">#</text>
    <text x="62" y="96" fill="#38bdf8" font-family="-apple-system, sans-serif" font-size="11" font-weight="800">{"MEMBRE" if lang == "fr" else "MEMBER"}</text>
    <text x="229" y="96" fill="#38bdf8" font-family="-apple-system, sans-serif" font-size="11" font-weight="800" text-anchor="middle">{"NIVEAU" if lang == "fr" else "LEVEL"}</text>
    <text x="375" y="96" fill="#38bdf8" font-family="-apple-system, sans-serif" font-size="11" font-weight="800" text-anchor="end">{"VOCAL" if lang == "fr" else "VOICE"}</text>
    <text x="500" y="96" fill="#38bdf8" font-family="-apple-system, sans-serif" font-size="11" font-weight="800" text-anchor="end">MESSAGES</text>

    {rows_str}

    <text x="280" y="515" fill="#475569" font-family="-apple-system, sans-serif" font-size="10" font-weight="700" text-anchor="middle">HOURGLASS BOT • CLASSEMENT SERVEUR</text>
</svg>"""
    return _svg_response(svg_content)


# 4. Global Top 10 Vocal Leaderboard (!alltop)
@api_bp.route("/api/card/top", methods=["GET"])
@api_bp.route("/api/card/top/global", methods=["GET"])
@api_bp.route("/api/card/alltop", methods=["GET"])
def get_global_top_card():
    """Generate an SVG leaderboard card for the global Top 10 voice users across all servers."""
    lang = request.args.get("lang", "fr")
    top_users = (
        Stats
        .select(
            Stats.user_id,
            Users.username,
            Users.avatar,
            fn.SUM(Stats.seconds).alias("total_seconds"),
            fn.SUM(Stats.messages).alias("total_messages")
        )
        .join(Users, on=(Stats.user_id == Users.user_id))
        .group_by(Stats.user_id, Users.username, Users.avatar)
        .order_by(SQL("total_seconds").desc())
        .limit(10)
        .dicts()
    )

    rows_xml = []
    y_start = 125
    row_height = 37

    for i, r in enumerate(top_users):
        rank = i + 1
        y = y_start + i * row_height
        medal_color = "#f59e0b" if rank == 1 else ("#94a3b8" if rank == 2 else ("#d97706" if rank == 3 else "rgba(255, 255, 255, 0.08)"))
        text_color = "#0f172a" if rank in (1, 2, 3) else "#94a3b8"
        uname = html.escape((r['username'] or 'Inconnu')[:16])
        time_str = _format_time_short(r['total_seconds'])
        msgs_str = f"{r['total_messages']:,}".replace(",", " ")
        xp_info = calculate_user_xp_and_level(r['total_seconds'], r['total_messages'])
        lvl = xp_info['level']
        bg_bar = f'<rect x="20" y="{y - 24}" width="520" height="33" rx="7" fill="rgba(255, 255, 255, 0.02)"/>' if rank % 2 == 0 else ""
        row = f"""{bg_bar}
        <g transform="translate(26, {y})">
            <circle cx="12" cy="-7" r="11" fill="{medal_color}"/>
            <text x="12" y="-3" fill="{text_color}" font-family="-apple-system, sans-serif" font-size="11" font-weight="800" text-anchor="middle">{rank}</text>
            <text x="36" y="-3" fill="#ffffff" font-family="-apple-system, sans-serif" font-size="13" font-weight="700">{uname}</text>
            <rect x="200" y="-18" width="58" height="20" rx="5" fill="rgba(88, 101, 242, 0.2)" stroke="#5865F2" stroke-width="0.8"/>
            <text x="229" y="-4" fill="#818cf8" font-family="-apple-system, sans-serif" font-size="10" font-weight="800" text-anchor="middle">LVL {lvl}</text>
            <text x="375" y="-3" fill="#38bdf8" font-family="-apple-system, sans-serif" font-size="12" font-weight="800" text-anchor="end">{time_str}</text>
            <text x="500" y="-3" fill="#94a3b8" font-family="-apple-system, sans-serif" font-size="12" font-weight="600" text-anchor="end">{msgs_str}</text>
        </g>"""
        rows_xml.append(row)

    rows_str = "".join(rows_xml)

    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" width="560" height="535" viewBox="0 0 560 535">
    <defs>
        <linearGradient id="topBg" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#0f172a"/>
            <stop offset="100%" stop-color="#1e293b"/>
        </linearGradient>
    </defs>
    <rect width="560" height="535" rx="20" fill="url(#topBg)" stroke="rgba(255, 255, 255, 0.12)" stroke-width="1.2"/>
    
    <!-- Header -->
    <g transform="translate(30, 26)">
        <rect width="36" height="36" rx="10" fill="rgba(56, 189, 248, 0.15)" stroke="rgba(56, 189, 248, 0.35)" stroke-width="1"/>
        <path d="M 12 10 L 24 10 L 19 18 L 24 26 L 12 26 L 17 18 Z" fill="none" stroke="#38bdf8" stroke-width="1.8" stroke-linejoin="round"/>
    </g>
    <text x="78" y="42" fill="#ffffff" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="18" font-weight="800">TOP 10 GLOBAL • VOCAL</text>
    <text x="78" y="60" fill="#94a3b8" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="12">{"Classement général sur l'ensemble des serveurs" if lang == "fr" else "Cross-server all-time leaderboard"}</text>

    <!-- Table Header -->
    <rect x="20" y="78" width="520" height="28" rx="6" fill="rgba(255, 255, 255, 0.04)"/>
    <text x="36" y="96" fill="#38bdf8" font-family="-apple-system, sans-serif" font-size="11" font-weight="800">#</text>
    <text x="62" y="96" fill="#38bdf8" font-family="-apple-system, sans-serif" font-size="11" font-weight="800">{"MEMBRE" if lang == "fr" else "MEMBER"}</text>
    <text x="229" y="96" fill="#38bdf8" font-family="-apple-system, sans-serif" font-size="11" font-weight="800" text-anchor="middle">{"NIVEAU" if lang == "fr" else "LEVEL"}</text>
    <text x="375" y="96" fill="#38bdf8" font-family="-apple-system, sans-serif" font-size="11" font-weight="800" text-anchor="end">{"VOCAL" if lang == "fr" else "VOICE"}</text>
    <text x="500" y="96" fill="#38bdf8" font-family="-apple-system, sans-serif" font-size="11" font-weight="800" text-anchor="end">MESSAGES</text>

    {rows_str}

    <text x="280" y="515" fill="#475569" font-family="-apple-system, sans-serif" font-size="10" font-weight="700" text-anchor="middle">HOURGLASS BOT • CLASSEMENT MONDIAL</text>
</svg>"""
    return _svg_response(svg_content)


# 5. Server Statistics Card (!server)
@api_bp.route("/api/card/server/<int:server_id>", methods=["GET"])
def get_server_stat_card(server_id: int):
    """Generate an SVG stat card summarizing global activity for a server."""
    lang = request.args.get("lang", "fr")
    server_id, servername, server_avatar = _resolve_server(server_id)
    if server_id is None:
        return _render_error_svg(
            "Serveur introuvable" if lang != "en" else "Server not found",
            f"Aucun serveur trouvé avec l'ID {server_id}" if lang != "en" else f"No server found with ID {server_id}"
        )

    total_seconds = get_total_seconds_by_server_id(server_id) or 0
    total_messages = get_total_message_by_server_id(server_id) or 0
    user_count = get_user_count_by_server_id(server_id) or 0
    server_rank = get_server_rank(server_id)
    server_rank_str = f"#{server_rank}" if server_rank else ("Non classé" if lang == "fr" else "Unranked")
    join_date = get_server_join_date(server_id, lang=lang)
    hours_val = round(total_seconds / 3600, 1)

    champ = (
        Stats
        .select(Stats.user_id, Users.username, Stats.seconds)
        .join(Users, on=(Stats.user_id == Users.user_id))
        .where((Stats.server_id == server_id) & (Stats.seconds > 0))
        .order_by(Stats.seconds.desc())
        .dicts()
        .first()
    )
    champ_name = html.escape(champ["username"][:16]) if champ else ("Aucun" if lang == "fr" else "None")
    champ_hours = round(champ["seconds"] / 3600, 1) if champ else 0

    clean_srvname = html.escape((servername or '')[:24])
    voice_lbl = "VOCAL TOTAL" if lang == "fr" else "TOTAL VOICE"
    msgs_lbl = "MESSAGES"
    members_lbl = "MEMBRES SUIVIS" if lang == "fr" else "TRACKED MEMBERS"
    rank_lbl = "RANG" if lang == "fr" else "RANK"
    tracked_lbl = f"Suivi depuis le {join_date}" if lang == "fr" else f"Tracked since {join_date}"
    champ_lbl = f"Champion vocal : {champ_name} ({champ_hours}h)" if lang == "fr" else f"Voice champion: {champ_name} ({champ_hours}h)"

    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" width="540" height="225" viewBox="0 0 540 225">
    <defs>
        <linearGradient id="srvBg" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#0f172a"/>
            <stop offset="100%" stop-color="#1e293b"/>
        </linearGradient>
        <clipPath id="srvAvatarClip">
            <circle cx="65" cy="65" r="36"/>
        </clipPath>
    </defs>
    <rect width="540" height="225" rx="20" fill="url(#srvBg)" stroke="rgba(255, 255, 255, 0.12)" stroke-width="1.2"/>
    <ellipse cx="140" cy="15" rx="130" ry="25" fill="#818cf8" opacity="0.12"/>

    <!-- Server Avatar -->
    <circle cx="65" cy="65" r="39" fill="rgba(129, 140, 248, 0.2)" stroke="#818cf8" stroke-width="1.5"/>
    <circle cx="65" cy="65" r="36" fill="#1e293b"/>
    <image href="{html.escape(server_avatar)}" x="29" y="29" width="72" height="72" clip-path="url(#srvAvatarClip)" preserveAspectRatio="xMidYMid slice"/>

    <!-- Title & Details -->
    <text x="120" y="48" fill="#ffffff" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="20" font-weight="800">{clean_srvname}</text>
    <text x="120" y="70" fill="#94a3b8" font-family="-apple-system, sans-serif" font-size="11.5">{tracked_lbl}</text>
    <text x="120" y="86" fill="#64748b" font-family="-apple-system, sans-serif" font-size="10.5">ID: {server_id}</text>

    <!-- Server Rank Badge -->
    <g transform="translate(425, 30)">
        <rect width="85" height="28" rx="8" fill="rgba(255, 255, 255, 0.05)" stroke="rgba(255, 255, 255, 0.12)" stroke-width="1"/>
        <text x="12" y="18" fill="#94a3b8" font-family="-apple-system, sans-serif" font-size="10" font-weight="600">{rank_lbl}</text>
        <text x="70" y="19" fill="#38bdf8" font-family="-apple-system, sans-serif" font-size="13" font-weight="800" text-anchor="end">{server_rank_str}</text>
    </g>

    <line x1="28" y1="106" x2="512" y2="106" stroke="rgba(255, 255, 255, 0.08)" stroke-width="1"/>

    <!-- Stats KPI -->
    <g transform="translate(30, 128)">
        <text x="0" y="0" fill="#94a3b8" font-family="-apple-system, sans-serif" font-size="11" font-weight="700" letter-spacing="0.5px">{voice_lbl}</text>
        <text x="0" y="20" fill="#ffffff" font-family="-apple-system, sans-serif" font-size="16" font-weight="800">{hours_val}h</text>
    </g>

    <g transform="translate(195, 128)">
        <text x="0" y="0" fill="#94a3b8" font-family="-apple-system, sans-serif" font-size="11" font-weight="700" letter-spacing="0.5px">{msgs_lbl}</text>
        <text x="0" y="20" fill="#ffffff" font-family="-apple-system, sans-serif" font-size="16" font-weight="800">{total_messages:,}</text>
    </g>

    <g transform="translate(360, 128)">
        <text x="0" y="0" fill="#94a3b8" font-family="-apple-system, sans-serif" font-size="11" font-weight="700" letter-spacing="0.5px">{members_lbl}</text>
        <text x="0" y="20" fill="#ffffff" font-family="-apple-system, sans-serif" font-size="16" font-weight="800">{user_count:,}</text>
    </g>

    <!-- Champion Banner -->
    <rect x="28" y="166" width="484" height="32" rx="8" fill="rgba(245, 158, 11, 0.08)" stroke="rgba(245, 158, 11, 0.25)"/>
    <text x="42" y="186" fill="#f59e0b" font-family="-apple-system, sans-serif" font-size="12" font-weight="700">👑 {champ_lbl}</text>
    <text x="512" y="214" fill="#475569" font-family="-apple-system, sans-serif" font-size="10" font-weight="700" text-anchor="end">HOURGLASS BOT</text>
</svg>"""
    return _svg_response(svg_content)


# 6. Bot Commands Card (!aide)
COMMANDS_DATA = {
    "fr": [
        ("!stats [user]", "Affiche les statistiques de l'utilisateur sur le serveur actuel (messages et heures en vocal)."),
        ("!allstats [user]", "Affiche les statistiques globales de l'utilisateur cumulées sur l'ensemble des serveurs."),
        ("!top", "Affiche le Top 10 des utilisateurs les plus actifs en vocal sur le serveur actuel."),
        ("!alltop", "Affiche le Top 10 global des utilisateurs les plus actifs sur tous les serveurs."),
        ("!server", "Affiche les métriques globales du serveur (total des messages et heures en vocal)."),
        ("!aide", "Affiche la liste d'aide et les raccourcis des commandes du bot.")
    ],
    "en": [
        ("!stats [user]", "Displays user statistics on the current server (messages and voice hours)."),
        ("!allstats [user]", "Displays global cumulative user statistics across all servers."),
        ("!top", "Displays the Top 10 most active voice users on the current server."),
        ("!alltop", "Displays the global Top 10 most active voice users across all servers."),
        ("!server", "Displays global server metrics (total messages and voice hours)."),
        ("!aide", "Displays the help guide and command shortcuts for the bot.")
    ]
}

@api_bp.route("/api/card/commands", methods=["GET"])
@api_bp.route("/api/card/help", methods=["GET"])
@api_bp.route("/api/card/aide", methods=["GET"])
def get_bot_commands_card():
    """Generate an SVG table faithfully reproducing the bot commands guide."""
    lang = request.args.get("lang", "fr")
    items = COMMANDS_DATA.get(lang, COMMANDS_DATA["fr"])
    col1_title = "Commande" if lang != "en" else "Command"
    col2_title = "Description"

    width = 960
    height = 360
    rows_svg = []
    y_start = 90
    row_height = 42

    for i, (cmd, desc) in enumerate(items):
        y = y_start + i * row_height
        bg = f'<rect x="20" y="{y - 28}" width="{width - 40}" height="{row_height}" fill="rgba(255, 255, 255, 0.015)"/>' if i % 2 == 1 else ""
        divider = f'<line x1="20" y1="{y + 14}" x2="{width - 20}" y2="{y + 14}" stroke="rgba(255, 255, 255, 0.05)" stroke-width="1"/>' if i < len(items) - 1 else ""
        
        row = f"""{bg}
        <text x="36" y="{y}" fill="#fbbf24" font-family="'Consolas', 'Courier New', monospace" font-size="14" font-weight="700">{html.escape(cmd)}</text>
        <text x="240" y="{y}" fill="#cbd5e1" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="13" font-weight="400">{html.escape(desc)}</text>
        {divider}"""
        rows_svg.append(row)

    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
    <defs>
        <linearGradient id="cmdBg" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#0b1320"/>
            <stop offset="100%" stop-color="#111d2e"/>
        </linearGradient>
    </defs>
    
    <!-- Outer Card Frame -->
    <rect width="{width}" height="{height}" rx="14" fill="url(#cmdBg)" stroke="#1e293b" stroke-width="1.5"/>
    
    <!-- Table Container Frame -->
    <rect x="20" y="20" width="{width - 40}" height="{height - 40}" rx="10" fill="#080e18" stroke="#1e293b" stroke-width="1"/>
    
    <!-- Table Header Row -->
    <path d="M 20 30 Q 20 20 30 20 L {width - 30} 20 Q {width - 20} 20 {width - 20} 30 L {width - 20} 62 L 20 62 Z" fill="#13243a"/>
    <line x1="20" y1="62" x2="{width - 20}" y2="62" stroke="#1e3a5f" stroke-width="1"/>
    <text x="36" y="46" fill="#38bdf8" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="13.5" font-weight="700">{col1_title}</text>
    <text x="240" y="46" fill="#38bdf8" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="13.5" font-weight="700">{col2_title}</text>
    
    <!-- Rows -->
    {"".join(rows_svg)}
</svg>"""
    return _svg_response(svg_content)