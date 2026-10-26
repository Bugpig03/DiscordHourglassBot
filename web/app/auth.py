"""Discord OAuth2 Authentication and privacy access control module."""

import os
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
)
from app.config import Config
from app.database import Users, Stats
from app.security import valid_csrf
from app.profile_settings import remember_discord_identity
from app.analytics_tracking import record_login
from app.i18n import tr

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

DISCORD_API_BASE = "https://discord.com/api"
# Documented address without /api (the /api/ variant kept Android from opening the authorization in the Discord app)
DISCORD_OAUTH_AUTHORIZE_URL = "https://discord.com/oauth2/authorize"
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


def can_view_user_presence(target_user_id: int | str) -> bool:
    """Determine if current visitor can view Discord presence status of a user.

    Strict privacy rule:
    - Only visible if the viewer is the user themselves, OR
    - If the viewer is authenticated AND shares at least one mutual server with the target user.
    """
    if not is_authenticated():
        return False
    current_user = get_current_user()
    if not current_user:
        return False

    try:
        int_target = int(target_user_id)
        int_current = int(current_user.get("id", 0))
    except (ValueError, TypeError):
        return False

    # 1. User viewing their own profile
    if int_current == int_target:
        return True

    # 2. Check mutual servers between viewer and target
    viewer_guilds = get_current_user_guild_ids()
    try:
        viewer_db_guilds = {
            int(r.server_id)
            for r in Stats.select(Stats.server_id).where(Stats.user_id == int_current)
        }
        viewer_guilds |= viewer_db_guilds
    except Exception:
        pass

    if not viewer_guilds:
        return False

    try:
        target_guilds = {
            int(r.server_id)
            for r in Stats.select(Stats.server_id).where(Stats.user_id == int_target)
        }
    except Exception:
        target_guilds = set()

    return bool(viewer_guilds & target_guilds)


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
    """Return target only if it is a path on this site, otherwise "/" (prevents open redirects).

    Browsers treat a backslash like a slash ("/<backslash>evil.com" opens //evil.com) and ignore tabs/newlines
    inside URLs, so those are rejected along with anything carrying a scheme or a host.
    """
    if not target or not isinstance(target, str):
        return "/"
    if not target.startswith("/") or target.startswith("//") or "\\" in target:
        return "/"
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in target):
        return "/"
    parsed = urllib.parse.urlsplit(target)
    if parsed.scheme or parsed.netloc:
        return "/"
    return target


def get_discord_redirect_uri() -> str:
    """Return configured or auto-detected Discord OAuth2 redirect URI.
    
    Normalizes 127.0.0.1 to localhost for consistency with Discord Developer Portal whitelists.
    """
    # 1. Check if running on production domain
    if "hourglassbot.net" in request.host:
        return "https://hourglassbot.net/auth/callback"

    # 2. Explicit environment override
    configured = current_app.config.get("DISCORD_REDIRECT_URI") or os.environ.get("DISCORD_REDIRECT_URI")
    if configured:
        return configured

    # 3. Dynamic detection from incoming request
    host = request.host
    if host.startswith("127.0.0.1"):
        host = "localhost" + host[len("127.0.0.1"):]

    is_https = (
        request.is_secure
        or request.headers.get("X-Forwarded-Proto", "").lower() == "https"
    )
    scheme = "https" if is_https else "http"
    return f"{scheme}://{host}/auth/callback"


def _authenticate_with_discord_token(access_token: str) -> bool:
    """Fetch user profile and guild memberships directly from Discord API and save to session."""
    auth_headers = {"Authorization": f"Bearer {access_token}"}
    try:
        user_resp = requests.get(f"{DISCORD_API_BASE}/users/@me", headers=auth_headers, timeout=10)
        if user_resp.status_code != 200:
            current_app.logger.error(f"Failed to fetch user from Discord: status {user_resp.status_code}")
            return False

        user_json = user_resp.json()
        user_id = str(user_json["id"])

        avatar_hash = user_json.get("avatar")
        if avatar_hash:
            ext = "gif" if avatar_hash.startswith("a_") else "png"
            avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.{ext}"
        else:
            discrim = user_json.get("discriminator", "0")
            if discrim and discrim != "0":
                default_index = int(discrim) % 5
            else:
                default_index = (int(user_id) >> 22) % 6
            avatar_url = f"https://cdn.discordapp.com/embed/avatars/{default_index}.png"

        # Retrieve guilds user belongs to
        guild_ids = []
        try:
            guilds_resp = requests.get(f"{DISCORD_API_BASE}/users/@me/guilds", headers=auth_headers, timeout=10)
            if guilds_resp.status_code == 200:
                guilds_json = guilds_resp.json()
                guild_ids = [int(g["id"]) for g in guilds_json if "id" in g]
        except Exception as e:
            current_app.logger.warning(f"Failed to fetch user guilds: {e}")

        # Complement guild_ids with any servers where the user has recorded stats in our database
        try:
            int_uid = int(user_id)
            db_guilds = [
                int(r.server_id)
                for r in Stats.select(Stats.server_id).where(Stats.user_id == int_uid)
            ]
            guild_ids = list(set(guild_ids) | set(db_guilds))
        except Exception:
            pass

        # Store authenticated user session (permanent 60-day cookie)
        session.permanent = True
        session["user"] = {
            "id": user_id,
            "username": user_json.get("username", "DiscordUser"),
            "global_name": user_json.get("global_name"),
            "avatar": avatar_url,
        }
        session["guild_ids"] = guild_ids

        # Discord banner and profile color, offered as profile customization options
        remember_discord_identity(user_id, user_json.get("banner"), user_json.get("accent_color"))
        record_login(user_id, user_json.get("username"), avatar_url)
        return True
    except Exception as e:
        current_app.logger.error(f"Error authenticating with Discord token: {e}")
        return False


# ==============================================================================
# OAuth2 & Session Routes
# ==============================================================================

@auth_bp.route("/login", methods=["GET"])
def login():
    """Render the official Discord authentication portal."""
    next_url = _safe_redirect_target(
        request.args.get("next") or session.get("oauth_next_url") or request.referrer or "/"
    )
    session["oauth_next_url"] = next_url

    error_code = request.args.get("error")
    error_message = None
    if error_code in ("access_denied", "access-denied"):
        error_message = tr("Connexion annulée : vous avez refusé l'autorisation sur Discord.", "Login cancelled: you declined the authorization on Discord.")
    elif error_code == "invalid_state":
        error_message = tr("La session de sécurité a expiré. Veuillez cliquer à nouveau pour vous connecter.", "The security session has expired. Please click again to log in.")
    elif error_code == "token_failed":
        error_message = tr("Impossible de valider la session auprès de Discord. Veuillez réessayer.", "Could not validate the session with Discord. Please try again.")
    elif error_code:
        error_message = tr("Erreur d'authentification Discord ({code}).", "Discord authentication error ({code}).", code=error_code)

    return render_template(
        "login.html",
        next_url=next_url,
        error_message=error_message,
        current_user=get_current_user(),
    )


@auth_bp.route("/oauth")
def oauth_start():
    """Initiate official Discord OAuth2 authorization flow directly with Discord API."""
    is_popup = request.args.get("popup") in ("1", "true")
    session["oauth_is_popup"] = is_popup

    next_url = _safe_redirect_target(
        request.args.get("next") or session.get("oauth_next_url") or request.referrer or "/"
    )
    session["oauth_next_url"] = next_url

    client_id = current_app.config.get("DISCORD_CLIENT_ID", Config.DISCORD_CLIENT_ID)
    client_secret = current_app.config.get("DISCORD_CLIENT_SECRET", Config.DISCORD_CLIENT_SECRET)
    redirect_uri = get_discord_redirect_uri()

    state = secrets.token_urlsafe(24)
    session["oauth_state"] = state

    # If client_secret is configured, use standard authorization_code flow.
    # Otherwise, use Discord's official Implicit Grant (response_type=token)
    response_type = "code" if client_secret else "token"

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": response_type,
        "scope": DISCORD_SCOPES,
        "state": state,
    }
    discord_login_url = f"{DISCORD_OAUTH_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"
    return redirect(discord_login_url)


@auth_bp.route("/callback", methods=["GET"])
def callback():
    """Handle Discord OAuth2 authorization callback for both Code and Implicit Grant flows."""
    next_url = session.get("oauth_next_url", "/")
    is_popup = session.get("oauth_is_popup", False)

    error = request.args.get("error")
    if error:
        if is_popup:
            return render_template("auth_callback.html", next_url=next_url, is_popup=True, error=error)
        return redirect(url_for("auth.login", error=error))

    code = request.args.get("code")

    # 1. Authorization Code Grant (Discord provided ?code=...)
    if code:
        state = request.args.get("state")
        expected_state = session.pop("oauth_state", None)

        if not state or state != expected_state:
            if is_popup:
                return render_template("auth_callback.html", next_url=next_url, is_popup=True, error="invalid_state")
            return redirect(url_for("auth.login", error="invalid_state"))

        client_id = current_app.config.get("DISCORD_CLIENT_ID", Config.DISCORD_CLIENT_ID)
        client_secret = current_app.config.get("DISCORD_CLIENT_SECRET", Config.DISCORD_CLIENT_SECRET)
        redirect_uri = get_discord_redirect_uri()

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
            if token_resp.status_code == 200:
                token_json = token_resp.json()
                access_token = token_json.get("access_token")
                if access_token and _authenticate_with_discord_token(access_token):
                    destination = session.pop("oauth_next_url", "/")
                    if is_popup:
                        session.pop("oauth_is_popup", None)
                        return render_template("auth_callback.html", next_url=destination, is_popup=True, auto_close=True)
                    return redirect(destination)
        except Exception as e:
            current_app.logger.error(f"Discord OAuth2 code exchange error: {e}")

        if is_popup:
            return render_template("auth_callback.html", next_url=next_url, is_popup=True, error="token_failed")
        return redirect(url_for("auth.login", error="token_failed"))

    # 2. Implicit Grant: Discord returned #access_token=... in URL fragment.
    # Render callback page which will read the fragment in JS and POST to /auth/token-login.
    return render_template("auth_callback.html", next_url=next_url, is_popup=is_popup)


@auth_bp.route("/token-login", methods=["POST"])
def token_login():
    """Process access token received from Discord API via Implicit Grant flow."""
    data = request.get_json(silent=True) or {}
    access_token = data.get("access_token", "").strip()
    state = data.get("state")
    expected_state = session.get("oauth_state")

    # The state must always be present and match the one issued by /auth/oauth (CSRF / login injection)
    if not expected_state or not state or not secrets.compare_digest(str(state), expected_state):
        return {"success": False, "error": "Invalid state"}, 400

    if not access_token:
        return {"success": False, "error": "Missing access token"}, 400

    success = _authenticate_with_discord_token(access_token)
    if not success:
        return {"success": False, "error": "Discord authentication failed"}, 401

    session.pop("oauth_state", None)
    destination = session.pop("oauth_next_url", "/")
    is_popup = session.pop("oauth_is_popup", False)
    return {"success": True, "redirect": destination, "is_popup": is_popup}


@auth_bp.route("/logout", methods=["GET", "POST"])
def logout():
    """Log out (POST with CSRF token only) and go back to the home page.

    Not to the previous page: some only exist for a logged-in member (/admin answers 404 to visitors).
    A plain GET does not log out, so a third-party page cannot disconnect visitors with an <img> or a link.
    """
    if request.method == "POST" and valid_csrf(request.form.get("csrf_token")):
        for key in ("user", "guild_ids", "oauth_state", "oauth_next_url", "oauth_is_popup", "csrf_token"):
            session.pop(key, None)
    return redirect(url_for("home.home"))


@auth_bp.route("/dev-login")
@auth_bp.route("/dev-login/<path:subpath>")
def dev_login(subpath=None):
    """Legacy redirect: redirect any dev-login attempt to the unified Discord login."""
    return redirect(url_for("auth.login"))
