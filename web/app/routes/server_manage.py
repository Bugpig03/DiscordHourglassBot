"""Server management page (/server/<id>/manage): for the owner of a Discord server and the managers they chose.

Anyone else gets a 404, as if the page did not exist. Every change is checked again on the server side (role,
CSRF) and written to the server's journal.
"""

from flask import Blueprint, abort, jsonify, make_response, redirect, render_template, request, url_for

from app import server_admin as sa
from app.auth import get_current_user
from app.database import Servers
from app.i18n import current_lang
from app.security import valid_csrf
from app.security_log import record as security_event

server_manage_bp = Blueprint("server_manage", __name__)

SECTIONS = ("general", "levels", "reports", "roles", "journal")


def _access(server_id: int, owner_only: bool = False) -> tuple[dict, str]:
    """(current user, their role) or a 404 for anyone who does not manage this server."""
    user = get_current_user()
    if not user:
        abort(404)
    role = sa.server_role(user.get("id"), server_id)
    if role is None or (owner_only and role != "owner"):
        abort(404)
    return user, role


def _check_csrf(user: dict, what: str) -> None:
    if not valid_csrf(request.form.get("csrf_token")):
        security_event("csrf_fail", what, user_id=int(user["id"]))
        abort(400)


def _back(server_id: int, section: str, **flags):
    return redirect(url_for("server_manage.manage", server_id=server_id, section=section, **flags) + f"#{section}")


@server_manage_bp.route("/server/<int:server_id>/manage", methods=["GET"])
def manage(server_id: int):
    user = get_current_user()
    if not user:
        return redirect(url_for("auth.login", next=request.path))
    user, role = _access(server_id)
    lang = current_lang()
    server = Servers.get_or_none(Servers.server_id == server_id)
    section = request.args.get("section", "general")
    if section not in SECTIONS:
        section = "general"
    response = make_response(render_template(
        "server_manage.html",
        server_id=str(server_id),
        server_name=(server.servername if server else None) or f"#{server_id}",
        server_avatar=server.avatar if server else None,
        role=role,
        section=section,
        settings=sa.get_settings(server_id),
        timezones=sa.timezone_choices(),
        diag=sa.diagnostics(server_id, lang),
        channels=sa.channels(server_id),
        managers=sa.managers(server_id) if role == "owner" else [],
        max_managers=sa.MAX_MANAGERS,
        journal=sa.journal(server_id),
        levelup=sa.get_levelup(server_id),
        levelup_every=sa.LEVELUP_EVERY,
        levelup_max=sa.LEVELUP_MAX_MESSAGE,
        levelup_default=sa.levelup_default_message((sa.guild_meta(server_id) or {}).get("locale")),
        preview_member=_preview_member(server_id, int(user["id"])),
        reports=sa.get_reports(server_id),
        report_history=sa.report_history(server_id),
        roles=sa.roles(server_id),
        can_embed=any(c["key"] == "embed" and c["ok"] for c in sa.diagnostics(server_id, lang)["checks"]),
        invite_url=sa.invite_url(server_id),
        notice=request.args.get("notice", ""),
    ))
    # Private page: never cached, never indexed
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


@server_manage_bp.route("/server/<int:server_id>/manage/general", methods=["POST"])
def save_general(server_id: int):
    user, _ = _access(server_id)
    _check_csrf(user, "gestion du serveur (général)")
    ok = sa.save_timezone(server_id, request.form.get("timezone", ""), int(user["id"]))
    return _back(server_id, "general", notice="saved" if ok else "error")


@server_manage_bp.route("/server/<int:server_id>/manage/levels", methods=["POST"])
def save_levels(server_id: int):
    user, _ = _access(server_id)
    _check_csrf(user, "gestion du serveur (niveaux)")
    error = sa.save_levelup(server_id, request.form, int(user["id"]))
    return _back(server_id, "levels", notice="levels_" + (error or "saved"))


def _preview_member(server_id: int, user_id: int) -> dict | None:
    """Member shown in the announcement preview: the visitor when they are active here, else the most active one."""
    from app.database import Stats, Users
    from app.gamification import calculate_user_xp_and_level

    stat = Stats.get_or_none((Stats.user_id == user_id) & (Stats.server_id == server_id))
    if not stat:
        stat = Stats.select().where(Stats.server_id == server_id).order_by(Stats.seconds.desc()).first()
    if not stat:
        return None
    member = Users.get_or_none(Users.user_id == stat.user_id)
    level = calculate_user_xp_and_level(stat.seconds or 0, stat.messages or 0, 0)["level"]
    return {"id": int(stat.user_id), "name": (member.username if member else None) or f"#{stat.user_id}", "level": level}


@server_manage_bp.route("/server/<int:server_id>/manage/levels/card.svg", methods=["GET"])
def levels_card_preview(server_id: int):
    """Example of the card posted with an announcement (the member of the preview, at their current level)."""
    from app.cards import builders

    user, _ = _access(server_id)
    member = _preview_member(server_id, int(user["id"]))
    if not member:
        abort(404)
    try:
        svg = builders.levelup_card(member["id"], server_id, None, current_lang())
    except builders.CardNotFound:
        abort(404)
    response = make_response(svg)
    response.mimetype = "image/svg+xml"
    response.headers["Cache-Control"] = "private, max-age=300"
    return response


@server_manage_bp.route("/server/<int:server_id>/manage/reports", methods=["POST"])
def save_reports(server_id: int):
    """Saves the three reports; with a "test" button, also asks the bot for a test of that report."""
    user, _ = _access(server_id)
    _check_csrf(user, "gestion du serveur (rapports)")
    error = sa.save_reports(server_id, request.form, int(user["id"]))
    if error:
        return _back(server_id, "reports", notice="reports_channel" if error.startswith("channel") else "reports_error")
    test = request.form.get("test", "")
    if test:
        test_error = sa.request_report_test(server_id, test, int(user["id"]))
        return _back(server_id, "reports", notice="reports_test_" + (test_error or "asked"))
    return _back(server_id, "reports", notice="reports_saved")


@server_manage_bp.route("/server/<int:server_id>/manage/reports/<kind>.svg", methods=["GET"])
def reports_card_preview(server_id: int, kind: str):
    """The report as it would be posted now (last finished period)."""
    from app.cards import builders
    from app.reports import KINDS, last_period_start, server_timezone

    _access(server_id)
    if kind not in KINDS:
        abort(404)
    start = last_period_start(kind, server_timezone(server_id))
    try:
        svg = builders.report_card(server_id, kind, start, current_lang())
    except builders.CardNotFound:
        abort(404)
    response = make_response(svg)
    response.mimetype = "image/svg+xml"
    response.headers["Cache-Control"] = "private, max-age=300"
    return response


@server_manage_bp.route("/server/<int:server_id>/manage/managers/add", methods=["POST"])
def add_manager(server_id: int):
    user, _ = _access(server_id, owner_only=True)
    _check_csrf(user, "gestion du serveur (gestionnaires)")
    target = request.form.get("user_id", "")
    if not target.isdigit():
        return _back(server_id, "general", notice="not_member")
    error = sa.add_manager(server_id, int(target), int(user["id"]))
    return _back(server_id, "general", notice=error or "manager_added")


@server_manage_bp.route("/server/<int:server_id>/manage/managers/remove", methods=["POST"])
def remove_manager(server_id: int):
    user, _ = _access(server_id, owner_only=True)
    _check_csrf(user, "gestion du serveur (gestionnaires)")
    target = request.form.get("user_id", "")
    ok = target.isdigit() and sa.remove_manager(server_id, int(target), int(user["id"]))
    return _back(server_id, "general", notice="manager_removed" if ok else "error")


@server_manage_bp.route("/server/<int:server_id>/manage/members", methods=["GET"])
def search_members(server_id: int):
    """Members of the server by name, to choose a manager (owner only)."""
    _access(server_id, owner_only=True)
    response = jsonify({"members": sa.search_members(server_id, request.args.get("q", ""))})
    response.headers["Cache-Control"] = "private, no-store"
    return response


@server_manage_bp.route("/me/servers", methods=["GET"])
def my_servers():
    """The servers the visitor owns or manages."""
    user = get_current_user()
    if not user:
        return redirect(url_for("auth.login", next=request.path))
    if not sa.preview_allowed(user.get("id")):
        abort(404)  # preview period: site admins only
    return render_template("my_servers.html", servers=sa.managed_servers(user.get("id")), invite_url=sa.invite_url())
