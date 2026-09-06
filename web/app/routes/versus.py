"""Versus (Duel) comparison routes for users and servers."""

import json
from datetime import datetime
from flask import Blueprint, render_template, request
from peewee import fn
from app.database import Users, Stats, Servers
from app.functions import (
    get_global_rank_by_user_id_seconds,
    get_global_nb_user,
    get_global_nb_server,
    get_total_seconds_by_user_id,
    get_total_seconds_by_server_id,
    get_total_message_by_user_id,
    get_total_message_by_server_id,
    get_activity_sum_last_X_days,
    get_server_activity_sum_last_X_days,
    get_user_avatar_url,
    get_server_avatar_url,
    get_servername_by_server_id,
    get_server_rank,
    get_user_join_date,
    get_user_raw_join_date,
    get_server_join_date,
    get_user_servers_stats,
    get_user_rank_in_server,
    get_user_count_by_server_id,
    get_first_of_month_hours_sum,
    ConvertSecondsToTime,
)
from app.gamification import calculate_user_xp_and_level, calculate_user_badges
from app.routes.server_profile import load_users_from_server

versus_bp = Blueprint("versus", __name__)


@versus_bp.route("/versus", methods=["GET"])
def versus():
    """Render the Head-to-Head Versus page comparing either two users or two servers."""
    lang = request.cookies.get("lang", "fr")
    if lang not in ("fr", "en"):
        lang = "fr"

    tab = request.args.get("tab", "users").strip().lower()
    if tab not in ("users", "servers"):
        tab = "users"

    all_users = [
        row.username for row in (
            Users.select(Users.username)
            .where(Users.username.is_null(False))
            .order_by(Users.username.asc())
            .limit(300)
        )
    ]
    all_servers = [
        {"id": str(row.server_id), "name": row.servername or f"Serveur {row.server_id}"}
        for row in Servers.select().order_by(Servers.servername.asc())
    ]

    if tab == "users":
        return render_users_versus(lang, all_users, all_servers)
    else:
        return render_servers_versus(lang, all_users, all_servers)


def get_common_servers(user_id1: int, user_id2: int) -> list[dict]:
    """Retrieve all Discord servers where both users have recorded stats."""
    s1 = {row.server_id for row in Stats.select(Stats.server_id).where(Stats.user_id == user_id1)}
    s2 = {row.server_id for row in Stats.select(Stats.server_id).where(Stats.user_id == user_id2)}
    common_ids = s1.intersection(s2)
    if not common_ids:
        return []

    servers = (
        Servers
        .select(Servers.server_id, Servers.servername, Servers.avatar)
        .where(Servers.server_id.in_(list(common_ids)))
        .order_by(Servers.servername.asc())
    )
    return [
        {
            "id": str(srv.server_id),
            "name": srv.servername or f"Serveur {srv.server_id}",
            "avatar": srv.avatar,
        }
        for srv in servers
    ]


def render_users_versus(lang: str, all_users: list[str], all_servers: list[dict]):
    """Handle User vs User comparison with optional common-server scoping."""
    u1_query = request.args.get("u1", "").strip()
    u2_query = request.args.get("u2", "").strip()
    srv_query = request.args.get("srv", "").strip()

    top_two = list(
        Stats.select(Stats.user_id, fn.SUM(Stats.seconds).alias("tot"))
        .group_by(Stats.user_id)
        .order_by(fn.SUM(Stats.seconds).desc())
        .limit(2)
    )

    user1 = resolve_user(u1_query) if u1_query else (Users.get_or_none(Users.user_id == top_two[0].user_id) if top_two else None)

    if user1 and not u2_query:
        if top_two:
            if str(top_two[0].user_id) != str(user1.user_id):
                user2 = Users.get_or_none(Users.user_id == top_two[0].user_id)
            elif len(top_two) > 1:
                user2 = Users.get_or_none(Users.user_id == top_two[1].user_id)
            else:
                user2 = None
        else:
            user2 = None
    else:
        user2 = resolve_user(u2_query) if u2_query else None

    # Detect common servers between user1 and user2
    common_servers = []
    selected_server_obj = None
    selected_server_id = None

    if user1 and user2 and user1.user_id != user2.user_id:
        common_servers = get_common_servers(user1.user_id, user2.user_id)
        if srv_query:
            for cs in common_servers:
                if cs["id"] == srv_query:
                    selected_server_obj = cs
                    selected_server_id = int(cs["id"])
                    break

    data1 = load_user_versus_data(user1, lang, server_id=selected_server_id) if user1 else None
    data2 = load_user_versus_data(user2, lang, server_id=selected_server_id) if user2 else None

    comparison = None
    chart_json = "{}"
    if data1 and data2:
        comparison = compare_user_metrics(data1, data2)
        chart_json = build_versus_chart_json(
            data1["username"], data1["hours_curve"],
            data2["username"], data2["hours_curve"]
        )

    return render_template(
        "versus.html",
        tab="users",
        entity1=data1,
        entity2=data2,
        comparison=comparison,
        chart_json=chart_json,
        u1_val=user1.username if user1 else u1_query,
        u2_val=user2.username if user2 else u2_query,
        s1_val="",
        s2_val="",
        common_servers=common_servers,
        selected_server=selected_server_obj,
        srv_val=selected_server_obj["id"] if selected_server_obj else "",
        all_users=all_users,
        all_servers=all_servers,
    )


def render_servers_versus(lang: str, all_users: list[str], all_servers: list[dict]):
    """Handle Server vs Server comparison."""
    s1_query = request.args.get("s1", "").strip()
    s2_query = request.args.get("s2", "").strip()

    top_two = list(
        Stats.select(Stats.server_id, fn.SUM(Stats.seconds).alias("tot"))
        .group_by(Stats.server_id)
        .order_by(fn.SUM(Stats.seconds).desc())
        .limit(2)
    )

    server1 = resolve_server(s1_query) if s1_query else (Servers.get_or_none(Servers.server_id == top_two[0].server_id) if top_two else None)

    if server1 and not s2_query:
        if top_two:
            if str(top_two[0].server_id) != str(server1.server_id):
                server2 = Servers.get_or_none(Servers.server_id == top_two[0].server_id)
            elif len(top_two) > 1:
                server2 = Servers.get_or_none(Servers.server_id == top_two[1].server_id)
            else:
                server2 = None
        else:
            server2 = None
    else:
        server2 = resolve_server(s2_query) if s2_query else None

    data1 = load_server_versus_data(server1, lang) if server1 else None
    data2 = load_server_versus_data(server2, lang) if server2 else None

    comparison = None
    chart_json = "{}"
    if data1 and data2:
        comparison = compare_server_metrics(data1, data2)
        chart_json = build_versus_chart_json(
            data1["name"], data1["hours_curve"],
            data2["name"], data2["hours_curve"]
        )

    return render_template(
        "versus.html",
        tab="servers",
        entity1=data1,
        entity2=data2,
        comparison=comparison,
        chart_json=chart_json,
        u1_val="",
        u2_val="",
        s1_val=server1.servername if server1 else s1_query,
        s2_val=server2.servername if server2 else s2_query,
        common_servers=[],
        selected_server=None,
        srv_val="",
        all_users=all_users,
        all_servers=all_servers,
    )


def resolve_user(query: str) -> Users | None:
    """Find a user record by exact Discord ID or case-insensitive username."""
    if not query:
        return None
    s = query.strip()
    if s.isdigit():
        u = Users.get_or_none(Users.user_id == int(s))
        if u:
            return u
    u = Users.get_or_none(Users.username ** s)
    if u:
        return u
    return Users.select().where(Users.username.contains(s)).first()


def resolve_server(query: str) -> Servers | None:
    """Find a server record by exact server ID or name contains query."""
    if not query:
        return None
    s = query.strip()
    if s.isdigit():
        srv = Servers.get_or_none(Servers.server_id == int(s))
        if srv:
            return srv
    srv = Servers.get_or_none(Servers.servername ** s)
    if srv:
        return srv
    return Servers.select().where(Servers.servername.contains(s)).first()


def load_user_versus_data(user: Users, lang: str = "fr", server_id: int | None = None) -> dict:
    """Compile comprehensive profile metrics for user comparison, globally or per server."""
    uid = user.user_id
    uname = user.username or f"User {uid}"

    if server_id:
        stat = Stats.select().where(Stats.user_id == uid, Stats.server_id == server_id).first()
        tot_sec = (stat.seconds if stat else 0) or 0
        tot_msg = (stat.messages if stat else 0) or 0
        rank = get_user_rank_in_server(uid, server_id)
        total_scope_users = get_user_count_by_server_id(server_id)
        act_30d_raw = get_activity_sum_last_X_days(uid, 30, server_id=server_id)
        act_30d = act_30d_raw.get("seconds", 0) if isinstance(act_30d_raw, dict) else (act_30d_raw or 0)
        join_date = get_user_join_date(uid, server_id=server_id, lang=lang)
        hours_curve = get_first_of_month_hours_sum(server_id=server_id, user_id=uid)
        is_server_scoped = True
    else:
        tot_sec = get_total_seconds_by_user_id(uid) or 0
        tot_msg = get_total_message_by_user_id(uid) or 0
        rank = get_global_rank_by_user_id_seconds(uid)
        total_scope_users = get_global_nb_user()
        act_30d_raw = get_activity_sum_last_X_days(uid, 30)
        act_30d = act_30d_raw.get("seconds", 0) if isinstance(act_30d_raw, dict) else (act_30d_raw or 0)
        join_date = get_user_join_date(uid, lang=lang)
        hours_curve = get_first_of_month_hours_sum(user_id=uid)
        is_server_scoped = False

    servers_stats = get_user_servers_stats(uid) or []
    stats_dict = {
        "user_id": uid,
        "username": uname,
        "total_seconds": tot_sec,
        "total_message": tot_msg,
        "rank": rank,
        "user_servers_stats": servers_stats,
        "total_time_last_30d": act_30d,
        "join_date_raw": get_user_raw_join_date(uid),
    }

    badges = calculate_user_badges(stats_dict, lang=lang)
    unlocked_badges = sum(1 for b in badges if b.get("unlocked"))
    xp_info = calculate_user_xp_and_level(tot_sec, tot_msg)

    return {
        "type": "user",
        "id": str(uid),
        "username": uname,
        "avatar": get_user_avatar_url(uid),
        "rank": rank,
        "total_user": total_scope_users,
        "seconds": tot_sec,
        "hours": round(tot_sec / 3600, 1),
        "formatted_time": ConvertSecondsToTime(tot_sec),
        "messages": tot_msg,
        "activity_30d_seconds": act_30d,
        "activity_30d_hours": round(act_30d / 3600, 1),
        "level": xp_info["level"],
        "total_xp": xp_info["total_xp"],
        "tier_name": xp_info.get("title_en") if lang == "en" else xp_info.get("title_fr", "Membre"),
        "progress_percent": xp_info["progress_percent"],
        "unlocked_badges": unlocked_badges,
        "total_badges": len(badges),
        "servers_count": len(servers_stats),
        "join_date": join_date,
        "hours_curve": hours_curve,
        "is_server_scoped": is_server_scoped,
    }


def load_server_versus_data(server: Servers, lang: str = "fr") -> dict:
    """Compile comprehensive server metrics for server comparison."""
    sid = server.server_id
    sname = server.servername or f"Server {sid}"
    rank = get_server_rank(sid)
    tot_sec = get_total_seconds_by_server_id(sid) or 0
    tot_msg = get_total_message_by_server_id(sid) or 0
    act_30d_raw = get_server_activity_sum_last_X_days(sid, 30)
    if isinstance(act_30d_raw, dict):
        act_30d_sec = act_30d_raw.get("seconds", 0) or 0
    elif hasattr(act_30d_raw, "seconds"):
        act_30d_sec = act_30d_raw.seconds or 0
    else:
        act_30d_sec = act_30d_raw or 0

    members = load_users_from_server(sid, lang=lang) or []

    return {
        "type": "server",
        "id": str(sid),
        "name": sname,
        "avatar": get_server_avatar_url(sid),
        "rank": rank,
        "total_server": get_global_nb_server(),
        "seconds": tot_sec,
        "hours": round(tot_sec / 3600, 1),
        "formatted_time": ConvertSecondsToTime(tot_sec),
        "messages": tot_msg,
        "activity_30d_seconds": act_30d_sec,
        "activity_30d_hours": round(act_30d_sec / 3600, 1),
        "members_count": len(members),
        "join_date": get_server_join_date(sid, lang=lang),
        "hours_curve": get_first_of_month_hours_sum(server_id=sid),
    }


def compare_user_metrics(u1: dict, u2: dict) -> dict:
    """Evaluate metric comparisons between two users and declare category winners."""
    metrics = []

    def make_comp(key, label_key, v1, v2, higher_is_better=True, is_float=False, unit=""):
        if higher_is_better:
            if v1 > v2:
                w = "1"
            elif v2 > v1:
                w = "2"
            else:
                w = "tie"
        else:
            num1 = v1 if isinstance(v1, int) else 999999
            num2 = v2 if isinstance(v2, int) else 999999
            if num1 < num2:
                w = "1"
            elif num2 < num1:
                w = "2"
            else:
                w = "tie"

        tot = (v1 + v2) if (isinstance(v1, (int, float)) and isinstance(v2, (int, float))) else 0
        pct1 = round((v1 / tot) * 100, 1) if tot > 0 else 50.0
        pct2 = round(100.0 - pct1, 1)

        diff = abs(v1 - v2) if isinstance(v1, (int, float)) and isinstance(v2, (int, float)) else 0
        if is_float:
            diff = round(diff, 1)

        return {
            "key": key,
            "label_key": label_key,
            "v1": v1,
            "v2": v2,
            "diff": diff,
            "pct1": pct1,
            "pct2": pct2,
            "winner": w,
            "unit": unit,
        }

    is_server = u1.get("is_server_scoped", False)

    metrics.append(make_comp("hours", "versus.stat_voice", u1["hours"], u2["hours"], is_float=True, unit="h"))
    metrics.append(make_comp("messages", "versus.stat_messages", u1["messages"], u2["messages"]))
    metrics.append(make_comp("level", "versus.stat_level", u1["level"], u2["level"]))
    metrics.append(make_comp("activity_30d", "versus.stat_activity_30d", u1["activity_30d_hours"], u2["activity_30d_hours"], is_float=True, unit="h"))
    rank_label = "versus.stat_server_rank" if is_server else "versus.stat_rank"
    metrics.append(make_comp("rank", rank_label, u1["rank"], u2["rank"], higher_is_better=False))
    metrics.append(make_comp("badges", "versus.stat_badges", u1["unlocked_badges"], u2["unlocked_badges"]))
    if not is_server:
        metrics.append(make_comp("servers", "versus.stat_servers", u1["servers_count"], u2["servers_count"]))

    score1 = sum(1 for m in metrics if m["winner"] == "1")
    score2 = sum(1 for m in metrics if m["winner"] == "2")

    if score1 > score2:
        overall_winner = "1"
    elif score2 > score1:
        overall_winner = "2"
    else:
        overall_winner = "tie"

    return {
        "metrics": metrics,
        "score1": score1,
        "score2": score2,
        "total_categories": len(metrics),
        "overall_winner": overall_winner,
    }


def compare_server_metrics(s1: dict, s2: dict) -> dict:
    """Evaluate metric comparisons between two servers and declare category winners."""
    metrics = []

    def make_comp(key, label_key, v1, v2, higher_is_better=True, is_float=False, unit=""):
        if higher_is_better:
            if v1 > v2:
                w = "1"
            elif v2 > v1:
                w = "2"
            else:
                w = "tie"
        else:
            num1 = v1 if isinstance(v1, int) else 999999
            num2 = v2 if isinstance(v2, int) else 999999
            if num1 < num2:
                w = "1"
            elif num2 < num1:
                w = "2"
            else:
                w = "tie"

        tot = (v1 + v2) if (isinstance(v1, (int, float)) and isinstance(v2, (int, float))) else 0
        pct1 = round((v1 / tot) * 100, 1) if tot > 0 else 50.0
        pct2 = round(100.0 - pct1, 1)

        diff = abs(v1 - v2) if isinstance(v1, (int, float)) and isinstance(v2, (int, float)) else 0
        if is_float:
            diff = round(diff, 1)

        return {
            "key": key,
            "label_key": label_key,
            "v1": v1,
            "v2": v2,
            "diff": diff,
            "pct1": pct1,
            "pct2": pct2,
            "winner": w,
            "unit": unit,
        }

    metrics.append(make_comp("hours", "versus.stat_voice", s1["hours"], s2["hours"], is_float=True, unit="h"))
    metrics.append(make_comp("messages", "versus.stat_messages", s1["messages"], s2["messages"]))
    metrics.append(make_comp("activity_30d", "versus.stat_activity_30d", s1["activity_30d_hours"], s2["activity_30d_hours"], is_float=True, unit="h"))
    metrics.append(make_comp("members", "versus.stat_members", s1["members_count"], s2["members_count"]))
    metrics.append(make_comp("rank", "versus.stat_rank", s1["rank"], s2["rank"], higher_is_better=False))

    score1 = sum(1 for m in metrics if m["winner"] == "1")
    score2 = sum(1 for m in metrics if m["winner"] == "2")

    if score1 > score2:
        overall_winner = "1"
    elif score2 > score1:
        overall_winner = "2"
    else:
        overall_winner = "tie"

    return {
        "metrics": metrics,
        "score1": score1,
        "score2": score2,
        "total_categories": len(metrics),
        "overall_winner": overall_winner,
    }


def build_versus_chart_json(name1: str, curve1: list[dict], name2: str, curve2: list[dict]) -> str:
    """Build Chart.js datasets superimposing two curves along a shared timeline."""
    data1_points = [{"x": row["month"], "y": row["total_hours"]} for row in curve1]
    data2_points = [{"x": row["month"], "y": row["total_hours"]} for row in curve2]

    return json.dumps({
        "name1": name1,
        "data1": data1_points,
        "name2": name2,
        "data2": data2_points,
    })
