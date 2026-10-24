"""Application configuration module."""

import hashlib
import os
import re
import secrets
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
    return "3.0.0", "17/10/2026"


# Where the session key came from (shown on the admin page): "env", "discord", "database", "file" or "random"
SECRET_KEY_SOURCE = "random"


def _database_secret_key() -> str | None:
    """Session key kept in web_settings: created once, then read by every Gunicorn worker and every restart.

    All workers must end up with the SAME key, or a member is logged in on some pages and not on others.
    The 4 workers start together: concurrent CREATE TABLE IF NOT EXISTS can fail in PostgreSQL (unique
    violation on pg_type), so the table creation is a separate step whose error is ignored, and the whole
    read is retried before giving up.
    """
    import time
    try:
        import psycopg2
    except ImportError:
        return None
    for attempt in range(8):
        conn = None
        try:
            conn = psycopg2.connect(
                dbname=os.environ.get("POSTGRESQL_DBNAME", "devhourglass"), user=os.environ.get("POSTGRESQL_USER", "postgres"),
                password=os.environ.get("POSTGRESQL_PASSWORD", "admin"), host=os.environ.get("POSTGRESQL_HOST", "localhost"),
                port=int(os.environ.get("POSTGRESQL_PORT", "5432")), connect_timeout=5,
            )
            conn.autocommit = True
            with conn.cursor() as cur:
                try:
                    cur.execute("CREATE TABLE IF NOT EXISTS web_settings (key VARCHAR(64) PRIMARY KEY, value TEXT NOT NULL)")
                except psycopg2.Error:
                    pass  # another worker created it at the same moment
                cur.execute("INSERT INTO web_settings (key, value) VALUES ('session_secret', %s) ON CONFLICT (key) DO NOTHING",
                            (secrets.token_hex(32),))
                cur.execute("SELECT value FROM web_settings WHERE key = 'session_secret'")
                row = cur.fetchone()
                if row and row[0]:
                    return row[0]
        except Exception:
            pass
        finally:
            if conn is not None:
                conn.close()
        time.sleep(0.25 * (attempt + 1))
    import logging
    logging.getLogger(__name__).warning(
        "Session key: database unreachable, falling back to a local key (members may be logged out between pages)")
    return None


def load_secret_key() -> str:
    """Return the session signing key without ever falling back to a value published in the source code.

    Priority: SECRET_KEY / FLASK_SECRET_KEY env var, then a key derived from DISCORD_CLIENT_SECRET
    (stable across Gunicorn workers), then a random key stored once in the database (survives the
    container being recreated by an update, so members stay logged in), then web/.flask_secret_key.
    """
    global SECRET_KEY_SOURCE
    configured = os.environ.get("SECRET_KEY") or os.environ.get("FLASK_SECRET_KEY")
    if configured:
        SECRET_KEY_SOURCE = "env"
        return configured

    client_secret = os.environ.get("DISCORD_CLIENT_SECRET")
    if client_secret:
        SECRET_KEY_SOURCE = "discord"
        return hashlib.sha256(f"hourglass-session:{client_secret}".encode()).hexdigest()

    stored = _database_secret_key()
    if stored:
        SECRET_KEY_SOURCE = "database"
        return stored

    key_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".flask_secret_key")
    try:
        # O_EXCL: the first Gunicorn worker creates the key, the others read the same one
        fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(secrets.token_hex(32))
    except FileExistsError:
        pass
    try:
        with open(key_path, "r", encoding="utf-8") as f:
            key = f.read().strip()
        if key:
            SECRET_KEY_SOURCE = "file"
            return key
    except OSError:
        pass
    return secrets.token_hex(32)


class Config:
    """Flask application configuration settings loaded from environment variables."""

    # Secret key for signing session cookies (set FLASK_SECRET_KEY in production)
    SECRET_KEY = load_secret_key()

    # 60-day persistent session lifetime across browser restarts
    PERMANENT_SESSION_LIFETIME = timedelta(days=60)
    SESSION_COOKIE_NAME = "hourglass_session"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # HTTPS-only session cookie (browsers also accept it on http://localhost); set SESSION_COOKIE_SECURE=false
    # in .env only for a local setup served over plain HTTP on another host name.
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "true").lower() not in ("0", "false", "no")

    # Discord user IDs allowed on /admin, comma separated (empty: nobody)
    ADMIN_USER_IDS = frozenset(i.strip() for i in os.environ.get("ADMIN_USER_IDS", "").split(",") if i.strip().isdigit())

    # Secret shared with the Discord bot to fetch its card images from /internal/card/... (empty: disabled)
    CARD_TOKEN = os.environ.get("CARD_TOKEN", "").strip()

    # Static assets: styles.css is cache-busted with ?v=<app version>, icons/images almost never change
    SEND_FILE_MAX_AGE_DEFAULT = timedelta(days=7)
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