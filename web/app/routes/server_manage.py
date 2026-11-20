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
    return render_template("my_servers.html", servers=sa.managed_servers(user.get("id")), invite_url=sa.invite_url())
