"""Admin access: Discord user IDs listed in ADMIN_USER_IDS. Anyone else gets a 404 (the page does not appear to exist)."""

from functools import wraps

from flask import abort

from app.auth import get_current_user
from app.config import Config


def is_admin() -> bool:
    user = get_current_user()
    return bool(user and str(user.get("id")) in Config.ADMIN_USER_IDS)


def admin_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        from flask import request
        from app.security_log import record
        user = get_current_user()
        if not is_admin():
            record("admin_denied", "connecté" if user else "visiteur", user_id=user.get("id") if user else None)
            abort(404)
        if request.endpoint == "admin.admin_page":  # the page itself, not each data call it makes
            record("admin_access", user_id=user.get("id"))
        return view(*args, **kwargs)
    return wrapper
