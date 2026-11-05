"""Security journal for the admin page: logins, refused requests, scans, CSP reports and server errors.

Privacy: the visitor IP is kept shortened (IPv4 a.b.c.x, IPv6 first 48 bits), never in full; rows are deleted
after 90 days. Purpose: spotting attacks (brute force, scanners, forged requests) and fixing errors.

Performance: requests only append to an in-memory buffer; identical events of the same minute are merged into
one row with a count, and a background thread writes them every 30 s. A flood (a scanner firing thousands of
requests) is capped per minute so it can neither fill the database nor slow the workers down.
"""

import ipaddress
import logging
import re
import threading
import time
from collections import Counter
from datetime import datetime, timedelta, timezone

from flask import request
from peewee import DatabaseError

from app.database import create_tables, db

log = logging.getLogger(__name__)

FLUSH_INTERVAL_SECONDS = 30
RETENTION_DAYS = 90
MAX_EVENTS_PER_FLUSH = 2000  # distinct rows kept per window; the rest is only counted as "dropped"

# kind -> (French label, English label, severity) shown on the admin page
KINDS = {
    "login_ok": ("Connexion réussie", "Successful login", "info"),
    "login_fail": ("Connexion échouée", "Failed login", "warn"),
    "admin_access": ("Accès admin", "Admin access", "info"),
    "admin_denied": ("Accès admin refusé", "Admin access denied", "warn"),
    "csrf_fail": ("Formulaire refusé (CSRF)", "Form refused (CSRF)", "warn"),
    "rate_limited": ("Limite de requêtes (429)", "Rate limited (429)", "warn"),
    "scan": ("Scan de robot", "Bot scan", "warn"),
    "card_token_fail": ("Jeton de carte invalide", "Invalid card token", "high"),
    "webhook_fail": ("Webhook top.gg refusé", "top.gg webhook refused", "high"),
    "csp_violation": ("Violation CSP", "CSP violation", "warn"),
    "server_error": ("Erreur serveur (500)", "Server error (500)", "high"),
    "too_large": ("Requête trop grosse (413)", "Request too large (413)", "warn"),
}

# Paths only attack scanners ask for (the site has no PHP, no WordPress, no exposed dot-files)
SCAN_RE = re.compile(
    r"(\.php\d?$|\.asp|\.jsp|\.cgi|/\.env|/\.git|/\.aws|/\.ssh|/\.ds_store|wp-(admin|login|content|includes)|xmlrpc|"
    r"phpmyadmin|pma/|/cgi-bin|/vendor/|/config\.|/backup|\.sql$|\.bak$|\.zip$|\.tar|/actuator|/solr|/boaform|/HNAP1|"
    r"/server-status|/owa/|/autodiscover|/\.well-known/security\.txt\.php)", re.I)

TABLE = ("CREATE TABLE IF NOT EXISTS web_security_events (id BIGSERIAL PRIMARY KEY, at TIMESTAMP WITHOUT TIME ZONE NOT NULL, "
         "kind VARCHAR(24) NOT NULL, ip VARCHAR(48), path VARCHAR(160), user_id BIGINT, detail VARCHAR(200), "
         "hits INTEGER NOT NULL DEFAULT 1)")
INDEXES = [
    "CREATE INDEX IF NOT EXISTS web_security_events_at ON web_security_events (at)",
    "CREATE INDEX IF NOT EXISTS web_security_events_kind_at ON web_security_events (kind, at)",
]

_lock = threading.Lock()
_buffer: Counter = Counter()  # (minute, kind, ip, path, user_id, detail) -> hits
_dropped = 0
_thread_started = False
_last_cleanup_day = None
_last_error_log = 0.0
_enabled = True


def ensure_table() -> None:
    global _enabled
    # Retried: the 4 workers start together and race on CREATE TABLE IF NOT EXISTS for a new table
    error = create_tables([TABLE, *INDEXES])
    if error is not None:
        _enabled = False
        log.warning("Security journal disabled (table unavailable, run the web migrations): %s", error)


def short_ip(ip: str | None) -> str | None:
    """IPv4 82.64.12.x, IPv6 2a01:e0a:1f2::/48: enough to see one source coming back, not to identify a person."""
    if not ip:
        return None
    try:
        addr = ipaddress.ip_address(ip.strip())
    except ValueError:
        return None
    if addr.version == 4:
        return ".".join(str(addr).split(".")[:3]) + ".x"
    if addr.ipv4_mapped:
        return short_ip(str(addr.ipv4_mapped))
    return str(ipaddress.ip_network(f"{addr}/48", strict=False).network_address).rstrip(":") + "::/48"


def _request_ip() -> str | None:
    from app.security import client_ip
    try:
        return short_ip(client_ip() or request.remote_addr)
    except RuntimeError:  # outside a request
        return None


def record(kind: str, detail: str | None = None, user_id: int | str | None = None, path: str | None = None) -> None:
    """Note a security event of the current request (memory only; written within 30 s)."""
    global _dropped
    if not _enabled or kind not in KINDS:
        return
    try:
        path = path if path is not None else request.full_path.rstrip("?")
    except RuntimeError:
        path = path or ""
    uid = int(user_id) if user_id is not None and str(user_id).isdigit() else None
    minute = datetime.now(timezone.utc).replace(tzinfo=None, second=0, microsecond=0)
    key = (minute, kind, _request_ip(), (path or "")[:160], uid, (detail or "")[:200] or None)
    with _lock:
        if key in _buffer or len(_buffer) < MAX_EVENTS_PER_FLUSH:
            _buffer[key] += 1
        else:
            _dropped += 1
    _start_flusher()


def is_scan(path: str) -> bool:
    return bool(SCAN_RE.search(path or ""))


def _start_flusher() -> None:
    global _thread_started
    if _thread_started:
        return
    _thread_started = True

    def loop():
        while True:
            time.sleep(FLUSH_INTERVAL_SECONDS)
            flush()

    threading.Thread(target=loop, name="security-journal-flush", daemon=True).start()


def flush() -> None:
    """Write the buffered events (every 30 s, or directly by tests)."""
    global _dropped, _last_error_log
    with _lock:
        rows = [(*key, hits) for key, hits in _buffer.items()]
        dropped = _dropped
        _buffer.clear()
        _dropped = 0
    if dropped:
        now = datetime.now(timezone.utc).replace(tzinfo=None, second=0, microsecond=0)
        rows.append((now, "rate_limited", None, "", None, f"{dropped} événement(s) non détaillé(s) : trop d'événements en une minute", dropped))
    if rows:
        try:
            with db.connection_context():
                db.cursor().executemany(
                    "INSERT INTO web_security_events (at, kind, ip, path, user_id, detail, hits) VALUES (%s, %s, %s, %s, %s, %s, %s)", rows)
        except Exception as e:  # never break the worker for the journal
            if time.monotonic() - _last_error_log > 3600:
                log.warning("Security events could not be written (dropped): %s", e)
                _last_error_log = time.monotonic()
    _cleanup_once_a_day()


def _cleanup_once_a_day() -> None:
    global _last_cleanup_day
    today = datetime.now(timezone.utc).date()
    if _last_cleanup_day == today:
        return
    _last_cleanup_day = today
    try:
        with db.connection_context():
            db.execute_sql("DELETE FROM web_security_events WHERE at < %s",
                           (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=RETENTION_DAYS),))
    except Exception as e:
        log.warning("Security journal cleanup failed: %s", e)


def init_security_log(app) -> None:
    """Create the table, and journal 404 scans, 413 and 500 responses."""
    from flask import got_request_exception

    ensure_table()

    @app.after_request
    def _journal(response):
        try:
            status = response.status_code
            if status == 404 and is_scan(request.path):
                record("scan", request.method)
            elif status == 413:
                record("too_large", f"{request.content_length or '?'} octets")
        except Exception:
            log.exception("Security journal failed for %s", request.path)
        return response

    def _on_exception(sender, exception, **extra):
        try:
            record("server_error", type(exception).__name__)
        except Exception:
            pass

    got_request_exception.connect(_on_exception, app, weak=False)
