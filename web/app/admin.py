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
        if not is_admin():
            abort(404)
        return view(*args, **kwargs)
    return wrapper
