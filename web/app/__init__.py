"""Flask application factory and blueprint registration."""

import mimetypes
import os
import re
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from markupsafe import Markup
from werkzeug.middleware.proxy_fix import ProxyFix
from app.config import Config
from app.database import init_app
from app.security import init_security
from app.translations import get_text
from app.routes.home import home_bp
from app.routes.top import top_bp
from app.routes.users import users_bp
from app.routes.user_profile import user_profile_bp
from app.routes.server_profile import server_profile_bp
from app.routes.graphs import graphs_bp
from app.routes.api import api_bp
from app.routes.versus import versus_bp
from app.routes.customize import customize_bp
from app.profile_settings import ensure_table as ensure_profile_settings_table
from app.auth import (
    auth_bp,
    get_current_user,
    is_authenticated,
    can_view_user_sessions,
    can_view_user_presence,
    can_view_server_private_data,
)


# The bot stores Discord avatars at 1024px while the site shows them at 32-160px:
# serve a 256px variant (sharp on retina, ~16x lighter) and let the browser load off-screen images lazily.
DISCORD_AVATAR_SIZE_RE = re.compile(r"(https://cdn\.discordapp\.com/(?:avatars|icons|embed/avatars)/[^\"'\s?]+)\?size=(?:512|1024|2048|4096)")
# Only remote Discord images are lazy-loaded: local icons are tiny, cached and often above the fold
IMG_WITHOUT_LOADING_RE = re.compile(r"<img(?=[^>]*\bsrc=[\"']https://cdn\.discordapp\.com/)(?![^>]*\bloading=)")


def optimize_response_images(body: str) -> str:
    """Downsize Discord CDN avatar URLs and add native lazy-loading to <img> tags."""
    body = DISCORD_AVATAR_SIZE_RE.sub(r"\1?size=256", body)
    return IMG_WITHOUT_LOADING_RE.sub('<img loading="lazy"', body)


# Gallery pictures are WebP: not every OS mime table knows it (served as octet-stream otherwise)
mimetypes.add_type("image/webp", ".webp")


def create_app():
    """Create, configure, and return the Flask application instance."""
    app = Flask(__name__)

    # Behind the openresty reverse proxy: honour X-Forwarded-Proto so absolute URLs (og:image, og:url) use https
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=0, x_proto=1, x_host=0, x_port=0, x_prefix=0)

    # Load configuration from Config class
    app.config.from_object(Config)

    # Initialize database connection hooks with Flask request lifecycle
    init_app(app)

    # CSP with nonces, security headers, rate limiting, CSRF helpers
    init_security(app)

    # Profile customization table (created if the migration was not applied; never blocks startup)
    ensure_profile_settings_table()

    @app.before_request
    def ensure_persistent_session():
        """Ensure authenticated user sessions stay persistent for 60 days across browser restarts."""
        from flask import session
        if session.get("user"):
            session.permanent = True

    @app.after_request
    def optimize_images(response):
        """Apply avatar downsizing and lazy-loading to HTML pages and JSON API payloads."""
        if response.direct_passthrough or response.status_code != 200:
            return response
        if response.mimetype in ("text/html", "application/json"):
            body = response.get_data(as_text=True)
            optimized = optimize_response_images(body)
            if optimized != body:
                response.set_data(optimized)
        return response

    def page_url(page: int) -> str:
        """URL of the current page with another ?page=, keeping every active filter (period, sort, search...)."""
        args = request.args.to_dict(flat=True)
        args.pop("page", None)
        if page > 1:
            args["page"] = page
        return url_for(request.endpoint, **(request.view_args or {}), **args)

    def pagination_items(current: int, total: int) -> list[int | None]:
        """Page numbers to display: first, last and a window around the current page; None marks a gap (…)."""
        if total <= 7:
            return list(range(1, total + 1))
        left, right = max(2, current - 1), min(total - 1, current + 1)
        if current <= 3:
            left, right = 2, 4
        elif current >= total - 2:
            left, right = total - 3, total - 1
        items = [1]
        if left > 2:
            items.append(None)
        items.extend(range(left, right + 1))
        if right < total - 1:
            items.append(None)
        items.append(total)
        return items

    def asset_version(filename: str) -> int:
        """Cache-busting token for a static file: changes whenever the file changes on disk."""
        try:
            return int(os.path.getmtime(os.path.join(app.static_folder, filename)))
        except OSError:
            return 0

    @app.context_processor
    def inject_i18n():
        """Inject current language, detected timezone, and translation helper into all templates."""
        from app.functions import get_user_timezone
        lang = request.cookies.get("lang", "fr")
        if lang not in ("fr", "en"):
            lang = "fr"
        return {
            "current_lang": lang,
            "user_tz": get_user_timezone(),
            "app_version": Config.APP_VERSION,
            "asset_version": asset_version,
            "page_url": page_url,
            "pagination_items": pagination_items,
            "app_version_date": Config.APP_VERSION_DATE,
            "current_user": get_current_user(),
            "is_authenticated": is_authenticated(),
            "can_view_user_sessions": can_view_user_sessions,
            "can_view_user_presence": can_view_user_presence,
            "can_view_server_private_data": can_view_server_private_data,
            "t": lambda key, **kwargs: get_text(key, lang=lang, **kwargs)
        }

    @app.route("/favicon.ico")
    def favicon():
        """Serve the multi-size icon at the root URL requested by Google and legacy clients."""
        return send_from_directory(
            os.path.join(app.static_folder, "icons"), "favicon.ico", mimetype="image/vnd.microsoft.icon", max_age=7 * 24 * 3600
        )

    @app.route("/set_language/<lang>")
    def set_language(lang):
        """Set user language cookie (fr or en) and redirect back to previous page."""
        if lang not in ("fr", "en"):
            lang = "fr"
        referrer = request.referrer or "/"
        response = redirect(referrer)
        response.set_cookie("lang", lang, max_age=365 * 24 * 3600, samesite="Lax")
        return response

    @app.route("/login")
    def login_shortcut():
        """Shortcut redirect to the unified auth.login page."""
        return redirect(url_for("auth.login", **request.args))

    @app.template_filter("safe_json")
    def safe_json(value):
        """Embed a pre-serialized JSON string in a <script type="application/json"> block.

        json.dumps leaves "<", ">" and "&" as-is, so a server, channel or member name containing
        "</script>" could close the block and inject markup; escaping them keeps the JSON identical once parsed.
        """
        text = str(value or "")
        for char, escaped in (("<", r"\u003c"), (">", r"\u003e"), ("&", r"\u0026"), ("\u2028", "\\u2028"), ("\u2029", "\\u2029")):
            text = text.replace(char, escaped)
        return Markup(text)

    @app.template_filter("num")
    def format_number(value, decimals: int = 0):
        """Locale-aware number: '1 826,8' in French, '1,826.8' in English (same output as HG.fmt in JS)."""
        try:
            number = float(value or 0)
        except (ValueError, TypeError):
            return str(value)
        formatted = f"{number:,.{decimals}f}"
        if request.cookies.get("lang", "fr") == "en":
            return formatted
        # Narrow no-break space for thousands and comma for decimals, as Intl.NumberFormat('fr-FR') does
        return formatted.replace(",", " ").replace(".", ",")

    @app.template_filter("thousands_fr")
    def thousands_fr(value):
        """Legacy alias of `num` that keeps the number of decimals of its input (e.g. 12345.6 -> '12 345,6' / '12,345.6')."""
        if value is None or value == "":
            return ""
        val_str = str(value).strip()
        sep = "." if "." in val_str else ("," if "," in val_str else None)
        decimals = len(val_str.split(sep, 1)[1]) if sep else 0
        try:
            float(val_str.replace(",", "."))
        except ValueError:
            return str(value)
        return format_number(val_str.replace(",", "."), decimals)

    @app.template_filter("date_localized")
    def filter_date_localized(dt):
        """Format a datetime into localized date based on current language cookie and user timezone."""
        from app.functions import format_date_localized
        lang = request.cookies.get("lang", "fr")
        return format_date_localized(dt, lang=lang)

    @app.template_filter("date_heure_localized")
    def filter_date_heure_localized(dt):
        """Format a datetime into localized date and time based on current language cookie and user timezone."""
        from app.functions import format_date_heure_localized
        lang = request.cookies.get("lang", "fr")
        return format_date_heure_localized(dt, lang=lang)

    @app.template_filter("date_fr")
    def filter_date_fr(dt):
        """Legacy filter alias redirecting to localized date formatter."""
        from app.functions import format_date_localized
        lang = request.cookies.get("lang", "fr")
        return format_date_localized(dt, lang=lang)

    @app.template_filter("date_heure_fr")
    def filter_date_heure_fr(dt):
        """Legacy filter alias redirecting to localized datetime formatter."""
        from app.functions import format_date_heure_localized
        lang = request.cookies.get("lang", "fr")
        return format_date_heure_localized(dt, lang=lang)

    @app.errorhandler(404)
    def page_not_found(e):
        """Render a custom 404 error page for unmatched routes."""
        return render_template("404.html"), 404

    # Register blueprints for modular routing
    app.register_blueprint(home_bp)
    app.register_blueprint(top_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(user_profile_bp)
    app.register_blueprint(server_profile_bp)
    app.register_blueprint(graphs_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(versus_bp)
    app.register_blueprint(customize_bp)
    app.register_blueprint(auth_bp)

    return app