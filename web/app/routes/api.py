"""Public REST API endpoints for accessing user, server, and statistical data."""

import html
from flask import Blueprint, jsonify, request, Response
from peewee import fn, JOIN
from app.database import Servers, Users, Stats
from app.functions import (
    get_user_id_by_username,
    get_user_avatar_url,
    get_global_rank_by_user_id_seconds,
    get_total_seconds_by_user_id,
    get_total_message_by_user_id,
    ConvertSecondsToTime,
    get_user_servers_stats,
    get_activity_sum_last_X_days,
    get_user_join_date,
    get_user_raw_join_date,
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


@api_bp.route("/api/card/user/<username>", methods=["GET"])
def get_user_stat_card(username: str):
    """Generate and return a stylish standalone SVG stat card for a user."""
    user_id = get_user_id_by_username(username)
    if user_id is None:
        error_svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="500" height="150" viewBox="0 0 500 150">
            <rect width="500" height="150" rx="16" fill="#15202e" stroke="#334155"/>
            <text x="250" y="80" fill="#ef4444" font-family="-apple-system, sans-serif" font-size="16" font-weight="bold" text-anchor="middle">Utilisateur '{html.escape(username)}' introuvable</text>
        </svg>"""
        return Response(error_svg, mimetype="image/svg+xml", status=404)

    lang = request.args.get("lang", "fr")
    total_seconds = get_total_seconds_by_user_id(user_id) or 0
    total_messages = get_total_message_by_user_id(user_id) or 0
    rank = get_global_rank_by_user_id_seconds(user_id)
    avatar_url = get_user_avatar_url(user_id) or ""
    servers_stats = get_user_servers_stats(user_id)
    activity_30d = get_activity_sum_last_X_days(user_id, 30)
    join_date = get_user_join_date(user_id)

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

    <!-- Top decorative glow -->
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
        <text x="12" y="18" fill="#94a3b8" font-family="-apple-system, sans-serif" font-size="10" font-weight="600">RANG</text>
        <text x="70" y="19" fill="#38bdf8" font-family="-apple-system, sans-serif" font-size="13" font-weight="800" text-anchor="end">{rank_str}</text>
    </g>

    <!-- Divider -->
    <line x1="28" y1="106" x2="512" y2="106" stroke="rgba(255, 255, 255, 0.08)" stroke-width="1"/>

    <!-- Stats Grid -->
    <!-- Voice -->
    <g transform="translate(30, 126)">
        <text x="0" y="0" fill="#94a3b8" font-family="-apple-system, sans-serif" font-size="11" font-weight="700" letter-spacing="0.5px">{voice_label}</text>
        <text x="0" y="20" fill="#ffffff" font-family="-apple-system, sans-serif" font-size="16" font-weight="800">{hours_val}h</text>
    </g>

    <!-- Messages -->
    <g transform="translate(120, 126)">
        <text x="0" y="0" fill="#94a3b8" font-family="-apple-system, sans-serif" font-size="11" font-weight="700" letter-spacing="0.5px">{msgs_label}</text>
        <text x="0" y="20" fill="#ffffff" font-family="-apple-system, sans-serif" font-size="16" font-weight="800">{total_messages:,}</text>
    </g>

    <!-- Total XP -->
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

    response = Response(svg_content, mimetype="image/svg+xml")
    response.headers["Cache-Control"] = "public, max-age=300"
    return response