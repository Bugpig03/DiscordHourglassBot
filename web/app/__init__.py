"""Flask application factory and blueprint registration."""

from flask import Flask, render_template, request, redirect
from app.config import Config
from app.database import init_app
from app.translations import get_text
from app.routes.home import home_bp
from app.routes.top import top_bp
from app.routes.users import users_bp
from app.routes.servers import servers_bp
from app.routes.user_profile import user_profile_bp
from app.routes.server_profile import server_profile_bp
from app.routes.graphs import graphs_bp
from app.routes.api import api_bp
from app.routes.versus import versus_bp



def create_app():
    """Create, configure, and return the Flask application instance."""
    app = Flask(__name__)

    # Load configuration from Config class
    app.config.from_object(Config)

    # Initialize database connection hooks with Flask request lifecycle
    init_app(app)

    @app.context_processor
    def inject_i18n():
        """Inject current language and translation helper into all templates."""
        lang = request.cookies.get("lang", "fr")
        if lang not in ("fr", "en"):
            lang = "fr"
        return {
            "current_lang": lang,
            "t": lambda key, **kwargs: get_text(key, lang=lang, **kwargs)
        }

    @app.route("/set_language/<lang>")
    def set_language(lang):
        """Set user language cookie (fr or en) and redirect back to previous page."""
        if lang not in ("fr", "en"):
            lang = "fr"
        referrer = request.referrer or "/"
        response = redirect(referrer)
        response.set_cookie("lang", lang, max_age=365 * 24 * 3600, samesite="Lax")
        return response

    @app.template_filter("thousands_fr")
    def thousands_fr(value):
        """Format an integer, float, or numeric string with spaces as thousand separators (e.g. 1 234 567 or 12 345.6)."""
        if value is None or value == "":
            return ""
        try:
            val_str = str(value).strip()
            if "." in val_str:
                parts = val_str.split(".", 1)
                int_part = int(parts[0] or 0)
                formatted_int = f"{int_part:,}".replace(",", " ")
                return f"{formatted_int}.{parts[1]}"
            elif "," in val_str:
                parts = val_str.split(",", 1)
                int_part = int(parts[0] or 0)
                formatted_int = f"{int_part:,}".replace(",", " ")
                return f"{formatted_int},{parts[1]}"
            else:
                val = int(float(val_str))
                return f"{val:,}".replace(",", " ")
        except (ValueError, TypeError):
            return str(value)

    @app.template_filter("date_localized")
    def filter_date_localized(dt):
        """Format a datetime into localized date based on current language cookie."""
        from app.functions import format_date_localized
        lang = request.cookies.get("lang", "fr")
        return format_date_localized(dt, lang=lang)

    @app.template_filter("date_heure_localized")
    def filter_date_heure_localized(dt):
        """Format a datetime into localized date and time based on current language cookie."""
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
    app.register_blueprint(servers_bp)
    app.register_blueprint(user_profile_bp)
    app.register_blueprint(server_profile_bp)
    app.register_blueprint(graphs_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(versus_bp)

    return app