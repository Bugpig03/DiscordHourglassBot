"""Discord OAuth2 Authentication and privacy access control module."""

import secrets
import urllib.parse
import requests
from flask import (
    Blueprint,
    current_app,
    redirect,
    render_template,
    request,
    session,
    url_for,
    flash,
    abort,
)
from app.config import Config
from app.database import Users, Stats, Servers
from peewee import fn

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

DISCORD_API_BASE = "https://discord.com/api"
DISCORD_OAUTH_AUTHORIZE_URL = "https://discord.com/api/oauth2/authorize"
DISCORD_OAUTH_TOKEN_URL = "https://discord.com/api/oauth2/token"
DISCORD_SCOPES = "identify guilds"


# ==============================================================================
# Helper Functions (Usable across routes and Jinja2 templates)
# ==============================================================================

def get_current_user() -> dict | None:
    """Return the currently authenticated Discord user from session, or None."""
    return session.get("user")


def is_authenticated() -> bool:
    """Check if the visitor is currently logged in with a Discord account."""
    return bool(session.get("user"))


def get_current_user_guild_ids() -> set[int]:
    """Return the set of Discord guild IDs the logged-in user is a member of."""
    raw_guilds = session.get("guild_ids", [])
    result = set()
    for g in raw_guilds:
        try:
            result.add(int(g))
        except (ValueError, TypeError):
            pass
    return result


def can_view_user_sessions(target_user_id: int | str) -> bool:
    """Determine if current visitor can view individual voice sessions on a user profile.

    Strict rule: Only the account owner logged in with matching Discord user ID can view.
    """
    if not is_authenticated():
        return False
    current_user = get_current_user()
    if not current_user:
        return False
    return str(current_user.get("id")) == str(target_user_id)


def can_view_server_private_data(server_id: int | str) -> bool:
    """Determine if current visitor can view private server details (voice sessions & live presence).

    Strict rule: Must be authenticated AND present on the target server.
    Verified via Discord OAuth2 guilds list, with cross-check in database Stats table.
    """
    if not is_authenticated():
        return False
    current_user = get_current_user()
    if not current_user:
        return False

    try:
        int_server_id = int(server_id)
    except (ValueError, TypeError):
        return False

    # 1. Verification via Discord OAuth2 guilds retrieved on login
    guild_ids = get_current_user_guild_ids()
    if int_server_id in guild_ids:
        return True

    # 2. Database cross-check: has the user recorded activity on this server?
    try:
        int_user_id = int(current_user.get("id", 0))
        return Stats.select().where(
            (Stats.user_id == int_user_id) & (Stats.server_id == int_server_id)
        ).exists()
    except Exception:
        return False


def _safe_redirect_target(target: str | None) -> str:
    """Ensure redirect URL is local to prevent open-redirect vulnerabilities."""
    if not target or target.startswith("//") or "://" in target:
        return "/"
    return target


# ==============================================================================
# OAuth2 & Session Routes
# ==============================================================================

@auth_bp.route("/login")
def login():
    """Initiate Discord OAuth2 authorization flow or redirect to dev-login if unconfigured."""
    # Store return destination in session
    next_url = _safe_redirect_target(request.args.get("next") or request.referrer or "/")
    session["oauth_next_url"] = next_url

    client_id = current_app.config.get("DISCORD_CLIENT_ID", Config.DISCORD_CLIENT_ID)
    client_secret = current_app.config.get("DISCORD_CLIENT_SECRET", Config.DISCORD_CLIENT_SECRET)
    redirect_uri = current_app.config.get("DISCORD_REDIRECT_URI", Config.DISCORD_REDIRECT_URI)

    # If secret is missing or explicit dev parameter, use dev-login
    if not client_secret or request.args.get("dev") == "1":
        if current_app.config.get("AUTH_DEV_MODE", Config.AUTH_DEV_MODE):
            return redirect(url_for("auth.dev_login"))
        flash("Discord OAuth2 secret non configuré sur ce serveur.", "error")
        return redirect(next_url)

    state = secrets.token_urlsafe(24)
    session["oauth_state"] = state

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": DISCORD_SCOPES,
        "state": state,
        "prompt": "consent",
    }
    discord_login_url = f"{DISCORD_OAUTH_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"
    return redirect(discord_login_url)


@auth_bp.route("/callback")
def callback():
    """Handle Discord OAuth2 authorization code callback."""
    next_url = session.pop("oauth_next_url", "/")

    error = request.args.get("error")
    if error:
        return redirect(next_url)

    code = request.args.get("code")
    state = request.args.get("state")
    expected_state = session.pop("oauth_state", None)

    if not code or not state or state != expected_state:
        return redirect(next_url)

    client_id = Config.DISCORD_CLIENT_ID
    client_secret = Config.DISCORD_CLIENT_SECRET
    redirect_uri = Config.DISCORD_REDIRECT_URI

    # Exchange authorization code for access token
    token_data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    try:
        token_resp = requests.post(DISCORD_OAUTH_TOKEN_URL, data=token_data, headers=headers, timeout=10)
        if token_resp.status_code != 200:
            return redirect(next_url)
        token_json = token_resp.json()
        access_token = token_json.get("access_token")
        if not access_token:
            return redirect(next_url)

        # Retrieve user profile from Discord API
        auth_headers = {"Authorization": f"Bearer {access_token}"}
        user_resp = requests.get(f"{DISCORD_API_BASE}/users/@me", headers=auth_headers, timeout=10)
        if user_resp.status_code != 200:
            return redirect(next_url)
        user_json = user_resp.json()

        # Build avatar URL
        avatar_hash = user_json.get("avatar")
        user_id = str(user_json["id"])
        if avatar_hash:
            ext = "gif" if avatar_hash.startswith("a_") else "png"
            avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.{ext}"
        else:
            default_index = (int(user_id) >> 22) % 6
            avatar_url = f"https://cdn.discordapp.com/embed/avatars/{default_index}.png"

        # Retrieve user guilds from Discord API
        guilds_resp = requests.get(f"{DISCORD_API_BASE}/users/@me/guilds", headers=auth_headers, timeout=10)
        guild_ids = []
        if guilds_resp.status_code == 200:
            guilds_json = guilds_resp.json()
            guild_ids = [int(g["id"]) for g in guilds_json if "id" in g]

        # Store authenticated user session
        session["user"] = {
            "id": user_id,
            "username": user_json.get("username", "DiscordUser"),
            "global_name": user_json.get("global_name"),
            "avatar": avatar_url,
        }
        session["guild_ids"] = guild_ids

    except Exception:
        pass

    return redirect(next_url)


@auth_bp.route("/logout")
def logout():
    """Clear user session and redirect back."""
    session.pop("user", None)
    session.pop("guild_ids", None)
    session.pop("oauth_state", None)
    session.pop("oauth_next_url", None)
    next_url = _safe_redirect_target(request.referrer or "/")
    return redirect(next_url)


# ==============================================================================
# Development / Local Simulation Login (Active in AUTH_DEV_MODE)
# ==============================================================================

@auth_bp.route("/dev-login")
def dev_login():
    """Provide a quick one-click local login selector for testing privacy rules in dev mode."""
    if not current_app.config.get("AUTH_DEV_MODE", Config.AUTH_DEV_MODE):
        abort(404)

    next_url = session.get("oauth_next_url", request.args.get("next") or request.referrer or "/")
    session["oauth_next_url"] = next_url

    # Fetch top active users from DB for convenient one-click testing
    top_users = (
        Users.select(Users.user_id, Users.username, Users.avatar)
        .join(Stats, on=(Users.user_id == Stats.user_id))
        .group_by(Users.user_id, Users.username, Users.avatar)
        .order_by(fn.SUM(Stats.seconds).desc())
        .limit(15)
    )

    current_u = get_current_user()
    current_guilds = get_current_user_guild_ids()

    return render_template(
        "dev_login.html",
        top_users=top_users,
        current_user=current_u,
        current_guilds=current_guilds,
        next_url=next_url,
    )


@auth_bp.route("/dev-login/<int:user_id>")
def dev_login_as(user_id: int):
    """Authenticate immediately as a specified user ID in local dev mode."""
    if not current_app.config.get("AUTH_DEV_MODE", Config.AUTH_DEV_MODE):
        abort(404)

    next_url = session.pop("oauth_next_url", "/")

    user = Users.get_or_none(Users.user_id == user_id)
    username = user.username if user else f"User_{user_id}"
    avatar = user.avatar if (user and user.avatar) else f"https://cdn.discordapp.com/embed/avatars/0.png"

    # Automatically load all servers this user belongs to from the Stats table
    user_servers = [
        int(row.server_id)
        for row in Stats.select(Stats.server_id).where(Stats.user_id == user_id)
    ]

    session["user"] = {
        "id": str(user_id),
        "username": username,
        "avatar": avatar,
    }
    session["guild_ids"] = user_servers

    return redirect(next_url)
