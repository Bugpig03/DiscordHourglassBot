"""Anonymous audience measurement for the admin page: page views, daily unique visitors, referrers,
searches, error statuses and Discord logins.

Privacy (CNIL audience-measurement exemption, Plausible-style):
  - no cookie, no IP stored: a visitor is sha256(daily salt + IP + user agent), truncated;
  - the salt changes every UTC day, is shared by the Gunicorn workers through web_daily_salt and is
    deleted the next day, so yesterday's hashes can no longer be linked to anyone, nor across days;
  - detailed rows are purged (visitor hashes after 30 days, the rest after 400 days).

Performance: requests only update in-memory counters; a background thread writes them every 60 s.
"""

import hashlib
import logging
import re
import secrets
import threading
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from flask import request
from peewee import DatabaseError

from app.database import db

log = logging.getLogger(__name__)

FLUSH_INTERVAL_SECONDS = 60
VISITOR_RETENTION_DAYS = 30
DETAIL_RETENTION_DAYS = 400
SEARCH_SETTLE_SECONDS = 8  # live search: only the final term of a typing burst is counted
LOCAL_TZ = ZoneInfo("Europe/Paris")

BOT_UA_RE = re.compile(r"bot|crawl|spider|slurp|preview|facebookexternalhit|embedly|discord|whatsapp|telegram|curl|wget|python-requests|headless", re.I)
EXCLUDED_PREFIXES = ("/static", "/api", "/admin", "/auth", "/favicon", "/robots", "/sitemap")
PAGE_KEYS = {
    "home.home": "home",
    "top.top_users": "members",
    "top.top_servers": "servers",
    "user_profile.profile": "profile",
    "server_profile.server": "server",
    "graphs.graphs": "graphs",
    "versus.versus": "versus",
    "home.supports": "help",
    "home.privacy": "privacy",
    "home.terms": "terms",
    "customize.customize_profile": "customize",
}

TABLES = [
    "CREATE TABLE IF NOT EXISTS web_daily_salt (day DATE PRIMARY KEY, salt TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS web_pageviews_daily (day DATE NOT NULL, page_key VARCHAR(32) NOT NULL, views INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (day, page_key))",
    "CREATE TABLE IF NOT EXISTS web_visitors_daily (day DATE NOT NULL, visitor_hash CHAR(16) NOT NULL, is_mobile BOOLEAN NOT NULL DEFAULT FALSE, lang VARCHAR(4) NOT NULL DEFAULT 'fr', PRIMARY KEY (day, visitor_hash))",
    "CREATE TABLE IF NOT EXISTS web_entity_views_daily (day DATE NOT NULL, kind VARCHAR(16) NOT NULL, entity_id VARCHAR(64) NOT NULL, views INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (day, kind, entity_id))",
    "CREATE TABLE IF NOT EXISTS web_referrers_daily (day DATE NOT NULL, domain VARCHAR(80) NOT NULL, views INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (day, domain))",
    "CREATE TABLE IF NOT EXISTS web_hourly_views (day DATE NOT NULL, hour SMALLINT NOT NULL, views INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (day, hour))",
    "CREATE TABLE IF NOT EXISTS web_status_daily (day DATE NOT NULL, status SMALLINT NOT NULL, path_key VARCHAR(80) NOT NULL, hits INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (day, status, path_key))",
    "CREATE TABLE IF NOT EXISTS web_searches_daily (day DATE NOT NULL, term VARCHAR(40) NOT NULL, hits INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (day, term))",
    "CREATE TABLE IF NOT EXISTS web_accounts (user_id BIGINT PRIMARY KEY, first_login_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, last_login_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, login_count INTEGER NOT NULL DEFAULT 1)",
    # Days on which a Discord-linked member logged in or browsed the site while logged in (active accounts)
    "CREATE TABLE IF NOT EXISTS web_logins_daily (day DATE NOT NULL, user_id BIGINT NOT NULL, PRIMARY KEY (day, user_id))",
]

_lock = threading.Lock()
_counters = {
    "pageviews": Counter(),   # (day, page_key)
    "entities": Counter(),    # (day, kind, entity_id)
    "referrers": Counter(),   # (day, domain)
    "hourly": Counter(),      # (day, hour)
    "status": Counter(),      # (day, status, path_key)
    "searches": Counter(),    # (day, term)
}
_visitors: dict[tuple, tuple[bool, str]] = {}           # (day, hash) -> (is_mobile, lang)
_active_accounts: set[tuple] = set()                    # (day, user_id) of logged-in members browsing the site
_pending_searches: dict[str, tuple[str, float, object]] = {}  # visitor -> (term, last_seen, day)
_salts: dict[object, str] = {}
_thread_started = False
_last_cleanup_day = None
_last_error_log = 0.0
_enabled = True


# ------------------------------------------------------------------------------
# Setup
# ------------------------------------------------------------------------------

def ensure_tables() -> None:
    """Create the tracking tables (IF NOT EXISTS) and seed web_accounts from the existing logins."""
    global _enabled
    try:
        with db.connection_context():
            had_accounts = db.table_exists("web_accounts")
            for sql in TABLES:
                db.execute_sql(sql)
            if not had_accounts and db.table_exists("user_profile_settings"):
                # Every Discord login since v3.3.0 left a user_profile_settings row: keep them as known accounts
                db.execute_sql(
                    "INSERT INTO web_accounts (user_id, first_login_at, last_login_at, login_count) "
                    "SELECT user_id, updated_at, updated_at, 1 FROM user_profile_settings ON CONFLICT DO NOTHING"
                )
    except DatabaseError as e:
        _enabled = False
        log.warning("Audience tracking disabled (tables unavailable, run the web migrations): %s", e)


def _today():
    return datetime.now(timezone.utc).date()


def _start_flusher() -> None:
    global _thread_started
    if _thread_started:
        return
    _thread_started = True

    def loop():
        while True:
            time.sleep(FLUSH_INTERVAL_SECONDS)
            flush()

    threading.Thread(target=loop, name="audience-flush", daemon=True).start()


# ------------------------------------------------------------------------------
# Recording (request thread: memory only, except one salt lookup per worker and per day)
# ------------------------------------------------------------------------------

def _client_ip() -> str:
    from app.security import client_ip
    return client_ip() or request.remote_addr or ""


def _daily_salt(day) -> str:
    salt = _salts.get(day)
    if salt:
        return salt
    candidate = secrets.token_hex(16)
    try:
        db.execute_sql("INSERT INTO web_daily_salt (day, salt) VALUES (%s, %s) ON CONFLICT (day) DO NOTHING", (day, candidate))
        salt = db.execute_sql("SELECT salt FROM web_daily_salt WHERE day = %s", (day,)).fetchone()[0]
    except DatabaseError:
        salt = candidate  # tracking still works per worker if the table is unavailable
    with _lock:
        _salts.clear()
        _salts[day] = salt
    return salt


def visitor_hash(day=None) -> str:
    day = day or _today()
    raw = f"{_daily_salt(day)}|{_client_ip()}|{request.headers.get('User-Agent', '')}"
    return hashlib.sha256(raw.encode("utf-8", "replace")).hexdigest()[:16]


def _is_bot() -> bool:
    ua = request.headers.get("User-Agent", "")
    return not ua or bool(BOT_UA_RE.search(ua))


def _referrer_domain() -> str | None:
    ref = request.referrer
    if not ref:
        return "direct"
    host = (urlsplit(ref).hostname or "").lower()
    if not host or host == (request.host or "").split(":")[0].lower():
        return None  # navigation inside the site
    host = host[4:] if host.startswith("www.") else host
    if host.endswith(("discord.com", "discordapp.com", "discord.gg")):
        return "discord"
    return host[:80]


def record_response(response) -> None:
    """after_request hook: count real page views and error statuses."""
    if not _enabled:
        return
    status = response.status_code
    path = request.path
    if status in (404, 429, 500):
        key = (_today(), status, (request.endpoint and PAGE_KEYS.get(request.endpoint)) or path[:80])
        with _lock:
            _counters["status"][key] += 1
        _start_flusher()
    if (
        status != 200
        or request.method != "GET"
        or response.mimetype != "text/html"
        or path.startswith(EXCLUDED_PREFIXES)
        or request.headers.get("Sec-Purpose", "").startswith("prefetch")
        or request.headers.get("Purpose") == "prefetch"
        or _is_bot()
    ):
        return
    day = _today()
    page_key = PAGE_KEYS.get(request.endpoint, "other")
    ua = request.headers.get("User-Agent", "")
    is_mobile = bool(re.search(r"Mobi|Android|iPhone|iPad", ua))
    lang = request.cookies.get("lang", "fr") if request.cookies.get("lang") in ("fr", "en") else "fr"
    try:
        vhash = visitor_hash(day)
    except Exception:
        vhash = None
    domain = _referrer_domain()
    hour = datetime.now(LOCAL_TZ).hour
    entity = None
    if page_key == "profile":
        entity = ("profile", str((request.view_args or {}).get("username", ""))[:64])
    elif page_key == "server":
        entity = ("server", str((request.view_args or {}).get("server_id", ""))[:64])
    from app.auth import get_current_user
    user = get_current_user()
    with _lock:
        if user and str(user.get("id", "")).isdigit():
            _active_accounts.add((day, int(user["id"])))
        _counters["pageviews"][(day, page_key)] += 1
        _counters["hourly"][(day, hour)] += 1
        if domain:
            _counters["referrers"][(day, domain)] += 1
        if entity and entity[1]:
            _counters["entities"][(day, entity[0], entity[1].lower())] += 1
        if vhash:
            _visitors.setdefault((day, vhash), (is_mobile, lang))
    _start_flusher()


def record_search(term: str) -> None:
    """Live search sends one request per keystroke: keep only the last term of each typing burst."""
    if not _enabled or _is_bot():
        return
    term = " ".join(term.lower().split())[:40]
    if len(term) < 2:
        return
    try:
        who = visitor_hash()
    except Exception:
        return
    now = time.monotonic()
    with _lock:
        prev = _pending_searches.get(who)
        if prev and now - prev[1] < SEARCH_SETTLE_SECONDS and (term.startswith(prev[0]) or prev[0].startswith(term)):
            _pending_searches[who] = (term, now, prev[2])
        else:
            if prev:
                _counters["searches"][(prev[2], prev[0])] += 1
            _pending_searches[who] = (term, now, _today())
    _start_flusher()


def record_login(user_id: int | str) -> None:
    """A Discord login (rare): written immediately."""
    if not _enabled:
        return
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    try:
        db.execute_sql(
            "INSERT INTO web_accounts (user_id, first_login_at, last_login_at, login_count) VALUES (%s, %s, %s, 1) "
            "ON CONFLICT (user_id) DO UPDATE SET last_login_at = EXCLUDED.last_login_at, login_count = web_accounts.login_count + 1",
            (int(user_id), now, now),
        )
        db.execute_sql("INSERT INTO web_logins_daily (day, user_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", (now.date(), int(user_id)))
    except (DatabaseError, ValueError) as e:
        log.warning("Could not record the login of %s: %s", user_id, e)


# ------------------------------------------------------------------------------
# Background flush
# ------------------------------------------------------------------------------

_UPSERTS = {
    "pageviews": ("INSERT INTO web_pageviews_daily (day, page_key, views) VALUES (%s, %s, %s) "
                  "ON CONFLICT (day, page_key) DO UPDATE SET views = web_pageviews_daily.views + EXCLUDED.views"),
    "entities": ("INSERT INTO web_entity_views_daily (day, kind, entity_id, views) VALUES (%s, %s, %s, %s) "
                 "ON CONFLICT (day, kind, entity_id) DO UPDATE SET views = web_entity_views_daily.views + EXCLUDED.views"),
    "referrers": ("INSERT INTO web_referrers_daily (day, domain, views) VALUES (%s, %s, %s) "
                  "ON CONFLICT (day, domain) DO UPDATE SET views = web_referrers_daily.views + EXCLUDED.views"),
    "hourly": ("INSERT INTO web_hourly_views (day, hour, views) VALUES (%s, %s, %s) "
               "ON CONFLICT (day, hour) DO UPDATE SET views = web_hourly_views.views + EXCLUDED.views"),
    "status": ("INSERT INTO web_status_daily (day, status, path_key, hits) VALUES (%s, %s, %s, %s) "
               "ON CONFLICT (day, status, path_key) DO UPDATE SET hits = web_status_daily.hits + EXCLUDED.hits"),
    "searches": ("INSERT INTO web_searches_daily (day, term, hits) VALUES (%s, %s, %s) "
                 "ON CONFLICT (day, term) DO UPDATE SET hits = web_searches_daily.hits + EXCLUDED.hits"),
}


def flush(settle_all: bool = False) -> None:
    """Write the in-memory counters to the database (called every minute, or directly by tests)."""
    global _last_error_log
    now = time.monotonic()
    with _lock:
        for who, (term, seen, day) in list(_pending_searches.items()):
            if settle_all or now - seen >= SEARCH_SETTLE_SECONDS:
                _counters["searches"][(day, term)] += 1
                del _pending_searches[who]
        batches = {name: [(*key, n) for key, n in counter.items()] for name, counter in _counters.items()}
        visitors = [(day, h, mobile, lang) for (day, h), (mobile, lang) in _visitors.items()]
        active = list(_active_accounts)
        for counter in _counters.values():
            counter.clear()
        _visitors.clear()
        _active_accounts.clear()
    if not any(batches.values()) and not visitors and not active:
        _cleanup_once_a_day()
        return
    try:
        with db.connection_context():
            with db.atomic():
                cursor = db.cursor()
                for name, rows in batches.items():
                    if rows:
                        cursor.executemany(_UPSERTS[name], rows)
                if active:
                    cursor.executemany("INSERT INTO web_logins_daily (day, user_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", active)
                if visitors:
                    cursor.executemany(
                        "INSERT INTO web_visitors_daily (day, visitor_hash, is_mobile, lang) VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
                        visitors,
                    )
    except Exception as e:  # never break the worker for statistics
        if time.monotonic() - _last_error_log > 3600:
            log.warning("Audience statistics could not be written (dropped this minute): %s", e)
            _last_error_log = time.monotonic()
    _cleanup_once_a_day()


def _cleanup_once_a_day() -> None:
    global _last_cleanup_day
    today = _today()
    if _last_cleanup_day == today:
        return
    _last_cleanup_day = today
    try:
        with db.connection_context():
            db.execute_sql("DELETE FROM web_daily_salt WHERE day < %s", (today,))
            db.execute_sql("DELETE FROM web_visitors_daily WHERE day < %s", (today - timedelta(days=VISITOR_RETENTION_DAYS),))
            old = today - timedelta(days=DETAIL_RETENTION_DAYS)
            for table in ("web_pageviews_daily", "web_entity_views_daily", "web_referrers_daily", "web_hourly_views",
                          "web_status_daily", "web_searches_daily", "web_logins_daily"):
                db.execute_sql(f"DELETE FROM {table} WHERE day < %s", (old,))
    except Exception as e:
        log.warning("Audience statistics cleanup failed: %s", e)


def init_tracking(app) -> None:
    ensure_tables()

    @app.after_request
    def _track(response):
        try:
            record_response(response)
        except Exception:
            log.exception("Audience tracking failed for %s", request.path)
        return response
