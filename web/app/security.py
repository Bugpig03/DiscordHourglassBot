"""HTTP security layer: Content-Security-Policy with per-request nonces, security headers,
CSRF tokens for state-changing forms and a lightweight per-IP rate limiter."""

import hmac
import ipaddress
import logging
import os
import secrets
import threading
import time
from collections import deque

from flask import g, jsonify, request, session

log = logging.getLogger(__name__)

# Origins the pages legitimately load from (Chart.js and its date adapter, Discord avatars/icons)
SCRIPT_CDN = "https://cdn.jsdelivr.net"
IMAGE_HOSTS = "https://cdn.discordapp.com https://media.discordapp.net"

# Requests per minute and per client IP. Counters live in each Gunicorn worker: with 4 workers the
# effective ceiling is up to 4x higher, which is fine for abuse protection (not exact quotas).
RATE_LIMITS = [
    ("/csp-report", 20),
    ("/admin", 60),
    ("/api/card/", 30),
    ("/api/search", 90),
    ("/api/", 120),
    ("/auth/", 30),
    ("/server/", 120),
    ("/me/", 60),  # includes /server/<id>/members ("Voir plus" and live member search)
]
RATE_WINDOW_SECONDS = 60

# Origins of browser extensions: their blocked scripts are left out of the security journal
EXTENSION_SCHEMES = ("chrome-extension:", "moz-extension:", "safari-extension:", "safari-web-extension:", "ms-browser-extension:")

# Pages with private data: never kept by a browser or proxy cache
NO_STORE_PREFIXES = ("/admin", "/me/", "/auth/")
# HTTPS only for 6 months (no preload list: removing a site from it takes months)
HSTS = "max-age=15552000"


def csp_nonce() -> str:
    """Nonce allowing this response's own inline <script> blocks."""
    if not hasattr(g, "csp_nonce"):
        g.csp_nonce = secrets.token_urlsafe(16)
    return g.csp_nonce


def csrf_token() -> str:
    """Per-session token embedded in POST forms (logout)."""
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def valid_csrf(submitted: str | None) -> bool:
    expected = session.get("csrf_token")
    return bool(expected and submitted and hmac.compare_digest(expected, submitted))


def build_csp() -> str:
    directives = [
        "default-src 'self'",
        # 'report-sample': a report carries the first characters of the blocked script, to tell who added it
        f"script-src 'self' 'nonce-{csp_nonce()}' 'report-sample' {SCRIPT_CDN}",
        # Templates still use inline style attributes; scripts are what CSP needs to lock down
        "style-src 'self' 'unsafe-inline'",
        f"img-src 'self' data: {IMAGE_HOSTS}",
        "connect-src 'self'",
        "font-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
        # Blocked scripts are reported to /csp-report and shown in the admin security journal
        "report-uri /csp-report",
        "report-to csp",
    ]
    if request.is_secure:
        directives.append("upgrade-insecure-requests")
    return "; ".join(directives)


def _from_proxy(remote: str) -> bool:
    """True when the request comes from the reverse proxy (same machine or private Docker network)."""
    try:
        addr = ipaddress.ip_address(remote)
    except ValueError:
        return False
    return addr.is_private or addr.is_loopback


def client_ip() -> str | None:
    """Visitor IP as seen by the reverse proxy; None when it cannot be told apart from the proxy.

    X-Real-IP / X-Forwarded-For are only believed when the request comes from the proxy: if the app port
    were reachable directly, anyone could otherwise pick a new "IP" for each request and dodge the limits.
    Shared by the rate limiter, the security journal (shortened IP) and the anonymous audience measurement.
    """
    remote = request.remote_addr or ""
    if remote and not _from_proxy(remote):
        return remote
    real_ip = request.headers.get("X-Real-IP", "").strip()
    if real_ip:
        return real_ip
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        # The proxy appends the address it received the request from: the right-most entry
        return forwarded.split(",")[-1].strip()
    try:
        if ipaddress.ip_address(remote).is_private and not ipaddress.ip_address(remote).is_loopback:
            return None
    except ValueError:
        pass
    return remote or None


class RateLimiter:
    """Sliding-window counter per (client IP, rule) kept in memory, thread-safe."""

    def __init__(self):
        self._hits: dict[tuple[str, str], deque] = {}
        self._lock = threading.Lock()
        self._last_sweep = time.monotonic()
        self._warned_no_client_ip = False

    def client_ip(self) -> str | None:
        ip = client_ip()
        if ip is None and not self._warned_no_client_ip:
            # Behind a proxy that forwards no client IP: every visitor would share one bucket
            log.warning("Rate limiting disabled: proxy sends neither X-Real-IP nor X-Forwarded-For")
            self._warned_no_client_ip = True
        return ip

    def check(self) -> tuple[bool, int, str | None]:
        """Return (allowed, retry_after_seconds, rule prefix) for the current request."""
        rule = next(((prefix, limit) for prefix, limit in RATE_LIMITS if request.path.startswith(prefix)), None)
        if rule is None:
            return True, 0, None
        ip = self.client_ip()
        if ip is None:
            return True, 0, rule[0]

        now = time.monotonic()
        key = (ip, rule[0])
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and now - hits[0] > RATE_WINDOW_SECONDS:
                hits.popleft()
            if len(hits) >= rule[1]:
                return False, max(1, int(RATE_WINDOW_SECONDS - (now - hits[0])) + 1), rule[0]
            hits.append(now)
            if now - self._last_sweep > RATE_WINDOW_SECONDS:
                for k in [k for k, v in self._hits.items() if not v or now - v[-1] > RATE_WINDOW_SECONDS]:
                    del self._hits[k]
                self._last_sweep = now
        return True, 0, rule[0]


def init_security(app) -> None:
    limiter = RateLimiter()
    report_only = os.environ.get("CSP_REPORT_ONLY", "false").lower() in ("1", "true", "yes")

    @app.before_request
    def _rate_limit():
        allowed, retry_after, rule = limiter.check()
        if allowed:
            return None
        from app.security_log import record
        record("rate_limited", request.method, path=rule)  # one row per source and rule each minute
        from app.i18n import tr
        message = tr("Trop de requêtes, réessayez dans quelques secondes.", "Too many requests, please retry in a few seconds.")
        response = jsonify({"error": "rate_limited", "message": message}) if request.path.startswith("/api/") \
            else app.response_class(message, mimetype="text/plain")
        response.status_code = 429
        response.headers["Retry-After"] = str(retry_after)
        return response

    @app.after_request
    def _security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=(), usb=()")
        if request.is_secure:
            response.headers.setdefault("Strict-Transport-Security", HSTS)
        if request.path.startswith(NO_STORE_PREFIXES):
            response.headers["Cache-Control"] = "no-store"
        if response.mimetype == "text/html":
            response.headers.setdefault("X-Frame-Options", "DENY")
            response.headers.setdefault("Reporting-Endpoints", 'csp="/csp-report"')
            header = "Content-Security-Policy-Report-Only" if report_only else "Content-Security-Policy"
            response.headers[header] = build_csp()
        return response

    @app.route("/csp-report", methods=["POST"])
    def csp_report():
        """Browsers report blocked scripts here (old report-uri JSON and Reporting API lists); 204 either way."""
        from app.security_log import record
        if (request.content_length or 0) > 16384:
            return "", 413
        payload = request.get_json(force=True, silent=True)
        reports = payload if isinstance(payload, list) else [payload]
        for report in reports[:5]:
            if not isinstance(report, dict):
                continue
            body = report.get("csp-report") or report.get("body") or {}
            if not isinstance(body, dict):
                continue
            directive = body.get("violated-directive") or body.get("effectiveDirective") or body.get("effective-directive")
            if not directive:
                continue  # not a CSP report
            blocked = str(body.get("blocked-uri") or body.get("blockedURL") or "inline")
            source = str(body.get("source-file") or body.get("sourceFile") or "")
            sample = " ".join(str(body.get("script-sample") or body.get("sample") or "").split())
            # Scripts added by the visitor's browser extensions (dark mode, password managers, ad blockers...) are
            # blocked as they should be, but are not about the site: not journaled
            if any(x.startswith(EXTENSION_SCHEMES) for x in (blocked, source)):
                continue
            page = body.get("document-uri") or body.get("documentURL") or ""
            detail = f"{directive} : {blocked}" + (f" · {source}" if source and source != page else "") + (f" · « {sample[:60]} »" if sample else "")
            record("csp_violation", detail[:200], path=str(page)[:160])
        return "", 204

    @app.context_processor
    def _security_context():
        return {"csp_nonce": csp_nonce, "csrf_token": csrf_token}
