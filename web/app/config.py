"""Application configuration module."""

import os
import re
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()


def load_app_version() -> tuple[str, str]:
    """Extract latest version and release date automatically from CHANGELOG.md.

    Returns a tuple (version, date) like ('2.7.5', '07/10/2026').
    Falls back gracefully if the changelog file is not found.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidate_paths = [
        os.path.join(base_dir, "..", "CHANGELOG.md"),
        os.path.join(base_dir, "CHANGELOG.md"),
        os.path.join(base_dir, "..", "..", "web", "CHANGELOG.md"),
    ]
    for path in candidate_paths:
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        match = re.match(
                            r"^##\s+Version\s+([0-9a-zA-Z\.\-]+)\s+-\s+.*?\s+-\s+(\d{2}/\d{2}/\d{4})",
                            line.strip(),
                        )
                        if match:
                            return match.group(1), match.group(2)
            except Exception:
                pass
    return "2.8.7", "12/10/2026"


class Config:
    """Flask application configuration settings loaded from environment variables."""

    # Stable secret key for signing session cookies
    SECRET_KEY = (
        os.environ.get("SECRET_KEY")
        or os.environ.get("FLASK_SECRET_KEY")
        or "hourglass_session_secret_v283_force_logout"
    )

    # 60-day persistent session lifetime across browser restarts
    PERMANENT_SESSION_LIFETIME = timedelta(days=60)
    SESSION_COOKIE_NAME = "hourglass_session"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    DB_NAME = os.environ.get("POSTGRESQL_DBNAME", "devhourglass")
    DB_USER = os.environ.get("POSTGRESQL_USER", "postgres")
    DB_PASSWORD = os.environ.get("POSTGRESQL_PASSWORD", "admin")
    DB_HOST = os.environ.get("POSTGRESQL_HOST", "localhost")
    DB_PORT = int(os.environ.get("POSTGRESQL_PORT", "5432"))

    # Automated versioning from CHANGELOG.md
    APP_VERSION, APP_VERSION_DATE = load_app_version()

    # Discord OAuth2 Configuration (Official Hourglass Bot: 1210665993328926750)
    DISCORD_CLIENT_ID = os.environ.get("DISCORD_CLIENT_ID", "1210665993328926750")
    DISCORD_CLIENT_SECRET = os.environ.get("DISCORD_CLIENT_SECRET", "")
    DISCORD_REDIRECT_URI = os.environ.get("DISCORD_REDIRECT_URI", "")