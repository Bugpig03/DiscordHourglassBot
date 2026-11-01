"""Security test battery of the website, run in-process against the local app (Flask test client, no server needed).

    cd web
    python scripts/security_check.py            every check, PASS / FAIL / INFO
    python scripts/security_check.py --quiet    only the failures and the total

Uses the database of the .env (read only: the audience counters and the security journal are switched off during
the run). Exit code 1 when a check fails, so it can run before each release.

Covers: HTTP headers and CSP, session cookie, access control (admin, owner-only data, bot card token), CSRF,
open redirects, OAuth state, reflected XSS, SQL injection, path traversal, HTTP methods, request size, error pages,
rate limiting and IP spoofing, Host header.
"""

import hashlib
import json
import os
import re
import sys
import time
from urllib.parse import quote

TEST_ADMIN_ID = "100000000000000001"  # fake admin of the run, not a real account
os.environ["ADMIN_USER_IDS"] = TEST_ADMIN_ID
os.environ.setdefault("CARD_TOKEN", "security-check-card-token")
os.environ.pop("HSTS_FROM_PROXY", None)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from itsdangerous import URLSafeTimedSerializer  # noqa: E402

from app import analytics_tracking, create_app, security_log  # noqa: E402
from app.auth import _safe_redirect_target, get_discord_redirect_uri  # noqa: E402
from app.database import db  # noqa: E402
from app.translations import TRANSLATIONS  # noqa: E402

app = create_app()
analytics_tracking._enabled = False  # attacks of the run are not visits
security_log._enabled = False        # nor journal entries


@app.route("/__security_check_boom")
def _boom():
    raise RuntimeError("security-check secret detail 1234")


RESULTS = []
XSS = ['"><script>alert(1)</script>', "<img src=x onerror=alert(1)>", "';alert(1);//", "</script><svg onload=alert(1)>"]
SQLI = ["' OR '1'='1", "1;DROP TABLE users--", "1 UNION SELECT passwd FROM pg_shadow--", "'||pg_sleep(3)||'", "9999999999999999999999"]


def check(area, name, ok, detail=""):
    RESULTS.append((area, name, "PASS" if ok is True else "FAIL" if ok is False else "INFO", str(detail)))


def client(user=None, ip="198.51.100.10"):
    """A visitor behind the reverse proxy (private peer + X-Real-IP), logged in as `user` if given."""
    c = app.test_client()
    c.environ_base.update({"REMOTE_ADDR": "172.18.0.2", "HTTP_X_REAL_IP": ip, "HTTP_USER_AGENT": "security-check"})
    if user:
        with c.session_transaction() as s:
            s["user"] = {"id": user, "username": "security-check", "avatar": None}
    return c


def sample_member() -> str | None:
    """A member with recorded voice sessions (to check that only they can see them)."""
    row = db.execute_sql("SELECT user_id FROM voice_sessions GROUP BY user_id ORDER BY COUNT(*) DESC LIMIT 1").fetchone()
    return str(row[0]) if row else None


def headers(anon):
    r = anon.get("/")
    csp = r.headers.get("Content-Security-Policy", "")
    check("Headers", "CSP on pages", bool(csp))
    script_src = (re.search(r"script-src ([^;]+)", csp) or [None, ""])[1]
    check("Headers", "script-src without 'unsafe-inline' / 'unsafe-eval'", "'unsafe-inline'" not in script_src and "'unsafe-eval'" not in script_src, script_src)
    check("Headers", "script-src with a nonce", "'nonce-" in script_src)
    for directive in ("default-src 'self'", "object-src 'none'", "frame-ancestors 'none'", "base-uri 'self'", "form-action 'self'"):
        check("Headers", f"CSP {directive}", directive in csp)
    check("Headers", "style-src 'unsafe-inline'", None, "accepted: low risk, scripts stay blocked")
    check("Headers", "X-Frame-Options DENY", r.headers.get("X-Frame-Options") == "DENY")
    check("Headers", "X-Content-Type-Options nosniff", r.headers.get("X-Content-Type-Options") == "nosniff")
    check("Headers", "Referrer-Policy", r.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin")
    check("Headers", "Permissions-Policy", "camera=()" in (r.headers.get("Permissions-Policy") or ""))
    check("Headers", "No open CORS", "Access-Control-Allow-Origin" not in anon.get("/api/search?q=ab").headers)
    check("Headers", "No X-Powered-By", "X-Powered-By" not in r.headers)
    rs = anon.get("/", base_url="https://localhost", headers={"X-Forwarded-Proto": "https"})
    check("Headers", "HSTS over HTTPS", "max-age=" in (rs.headers.get("Strict-Transport-Security") or ""))
    check("Headers", "No HSTS over HTTP", "Strict-Transport-Security" not in r.headers)
    other = anon.get("/").headers.get("Content-Security-Policy", "")
    check("Headers", "New CSP nonce on every page", script_src and script_src not in other)


def session_cookie():
    rr = client().get("/auth/oauth")
    cookie = next((v for k, v in rr.headers.items() if k == "Set-Cookie" and app.config["SESSION_COOKIE_NAME"] in v), "")
    check("Session", "Cookie HttpOnly", "HttpOnly" in cookie)
    check("Session", "Cookie Secure", "Secure" in cookie)
    check("Session", "Cookie SameSite=Lax", "SameSite=Lax" in cookie)
    name = app.config["SESSION_COOKIE_NAME"]
    forged = app.test_client()
    forged.set_cookie(name, "eyJ1c2VyIjp7ImlkIjoiMSJ9fQ.AAAAAA.forgedsignature", domain="localhost")
    check("Session", "Cookie with a bad signature refused", forged.get("/me/profile").status_code == 302)
    other_key = URLSafeTimedSerializer("another-key", salt="cookie-session",
                                       signer_kwargs={"key_derivation": "hmac", "digest_method": hashlib.sha1})
    forged.set_cookie(name, other_key.dumps({"user": {"id": TEST_ADMIN_ID}}), domain="localhost")
    check("Session", "Cookie signed with another key refused", forged.get("/admin").status_code == 404)


def access(anon):
    check("Access", "/admin anonymous -> 404", anon.get("/admin").status_code == 404)
    check("Access", "/admin/data anonymous -> 404", anon.get("/admin/data").status_code == 404)
    member = client(user="123456789012345678")
    check("Access", "/admin non-admin member -> 404", member.get("/admin").status_code == 404)
    check("Access", "/admin/data non-admin member -> 404", member.get("/admin/data").status_code == 404)
    check("Access", "/admin admin -> 200", client(user=TEST_ADMIN_ID).get("/admin").status_code == 200)
    check("Access", "/me/profile anonymous -> login", anon.get("/me/profile").status_code == 302)
    check("Access", "/internal/card without token -> 404", anon.get("/internal/card/member.png?user=1").status_code == 404)
    check("Access", "/internal/card wrong token -> 404",
          anon.get("/internal/card/member.png?user=1", headers={"X-Card-Token": "nope"}).status_code == 404)
    owner = sample_member()
    if not owner:
        check("Access", "Voice sessions shown to their owner only", None, "no voice session in this database")
        return
    label = TRANSLATIONS["fr"].get("channels.th_duration", "Durée")
    seen = {who: label in c.get(f"/profile/{owner}").get_data(as_text=True)
            for who, c in (("owner", client(user=owner)), ("other member", member), ("visitor", anon))}
    check("Access", "Voice sessions shown to their owner only", seen == {"owner": True, "other member": False, "visitor": False}, seen)


def csrf():
    user = client(user=TEST_ADMIN_ID)
    check("CSRF", "POST /me/profile without token -> 400", user.post("/me/profile", data={"accent_color": "gold"}).status_code == 400)
    check("CSRF", "POST /me/profile wrong token -> 400",
          user.post("/me/profile", data={"accent_color": "gold", "csrf_token": "x"}).status_code == 400)
    user.get("/auth/logout")
    with user.session_transaction() as s:
        kept = "user" in s
    check("CSRF", "GET /auth/logout does not log out", kept)
    user.post("/auth/logout", data={"csrf_token": "wrong"})
    with user.session_transaction() as s:
        kept = "user" in s
    check("CSRF", "POST /auth/logout with a wrong token does not log out", kept)


def redirects(anon):
    payloads = ["//evil.com", "https://evil.com", "/\\evil.com", "\\\\evil.com", "/\t/evil.com", "javascript:alert(1)",
                "http:evil.com", "///evil.com", " //evil.com", "/%2F%2Fevil.com"]
    bad = [p for p in payloads if _safe_redirect_target(p) not in ("/", "/%2F%2Fevil.com")]
    check("Redirects", f"{len(payloads)} malicious targets neutralized", not bad, ", ".join(bad))
    c = client()
    c.get("/auth/oauth?next=//evil.com/x")
    with c.session_transaction() as s:
        check("Redirects", "next=//evil.com at login -> /", s.get("oauth_next_url") == "/", s.get("oauth_next_url"))
    c.get("/auth/oauth", headers={"Referer": "https://evil.com/phish"})
    with c.session_transaction() as s:
        check("Redirects", "External Referer ignored", s.get("oauth_next_url") == "/", s.get("oauth_next_url"))


def oauth():
    c = client()
    c.get("/auth/oauth")
    r = c.get("/auth/callback?code=abc&state=wrong")
    check("OAuth", "Callback with a wrong state refused", r.status_code == 302 and "invalid_state" in r.headers.get("Location", ""))
    r = client().get("/auth/callback?code=abc&state=")
    check("OAuth", "Callback without state refused", r.status_code == 302 and "invalid_state" in r.headers.get("Location", ""))
    check("OAuth", "token-login without state -> 400", client().post("/auth/token-login", json={"access_token": "x"}).status_code == 400)


def xss(anon):
    targets = ["/members?q={p}", "/servers?q={p}", "/members?server_id={p}", "/members?period={p}", "/members?sort_by={p}",
               "/profile/{p}", "/server/{p}", "/versus?u1={p}&u2={p}", "/versus?tab={p}", "/{p}", "/graphs?tab={p}",
               "/api/search?q={p}", "/supports?lang={p}", "/members?q={p}&bots={p}&page={p}", "/admin?days={p}"]
    reflected = set()
    for t in targets:
        for p in XSS:
            resp = anon.get(t.format(p=quote(p, safe="")))
            body = resp.get_data(as_text=True)
            if p not in body:
                continue
            if resp.mimetype == "application/json":
                try:
                    json.loads(body)  # the text inside a JSON string is inert
                    continue
                except ValueError:
                    pass
            reflected.add(f"{t} ({resp.status_code})")
    check("XSS", f"{len(targets) * len(XSS)} reflected injections", not reflected, "; ".join(sorted(reflected)[:6]))
    c = app.test_client()
    c.set_cookie("lang", '"><script>alert(1)</script>', domain="localhost")
    check("XSS", "Malicious lang cookie not reflected", "<script>alert(1)</script>" not in c.get("/").get_data(as_text=True))


def sql_injection(anon):
    users_before = db.execute_sql("SELECT COUNT(*) FROM users").fetchone()[0]
    errors, slow = set(), set()
    for t in ["/members?server_id={p}", "/members?q={p}", "/servers?q={p}", "/profile/{p}", "/server/{p}", "/server/{p}/members",
              "/api/search?q={p}", "/api/user/{p}", "/versus?u1={p}&u2={p}", "/members?sort_by={p}&period={p}", "/api/graphs/data?days={p}"]:
        for p in SQLI:
            start = time.time()
            resp = anon.get(t.format(p=quote(p, safe="")))
            if time.time() - start > 2.5:
                slow.add(t)
            body = resp.get_data(as_text=True).lower()
            if resp.status_code >= 500 or "syntax error" in body or "psycopg" in body or "traceback" in body:
                errors.add(f"{t} -> {resp.status_code}")
    check("SQL injection", "Malicious parameters: no 500 nor SQL error", not errors, "; ".join(sorted(errors)[:6]))
    check("SQL injection", "No time-based injection (pg_sleep)", not slow, ", ".join(slow))
    c = app.test_client()
    c.set_cookie("user_tz", "UTC'); DROP TABLE users;--", domain="localhost")
    owner = sample_member() or "1"
    ok = c.get(f"/profile/{owner}").status_code in (200, 404)
    check("SQL injection", "Malicious user_tz cookie has no effect",
          ok and db.execute_sql("SELECT COUNT(*) FROM users").fetchone()[0] == users_before)


def files_methods_errors(anon):
    leaks = []
    for path in ["/static/../app/config.py", "/static/%2e%2e/app/config.py", "/static/..%2f..%2fapp%2fconfig.py",
                 "/static/....//app/config.py", "/static/%252e%252e/app/config.py", "/.env", "/.git/config",
                 "/app/config.py", "/run.py", "/static/../.flask_secret_key"]:
        resp = anon.get(path)
        text = resp.get_data(as_text=True)
        if resp.status_code == 200 and ("SECRET" in text or "import " in text):
            leaks.append(path)
    check("Files", "Path traversal and sensitive files out of reach", not leaks, ", ".join(leaks))
    refused = [m for m in ("PUT", "DELETE", "PATCH", "TRACE") if anon.open("/", method=m).status_code not in (404, 405)]
    check("Methods", "PUT / DELETE / PATCH / TRACE refused", not refused, ", ".join(refused))
    check("Size", "300 KB body refused (413)",
          anon.post("/auth/token-login", data="x" * (300 * 1024), content_type="application/json").status_code == 413)
    boom = anon.get("/__security_check_boom")
    text = boom.get_data(as_text=True)
    check("Errors", "500 page without technical detail", boom.status_code == 500 and "secret detail" not in text and "Traceback" not in text)
    check("Errors", "Debug mode off", not app.debug)
    check("Errors", "404 page without technical detail", "Traceback" not in anon.get("/no-such-page-xyz").get_data(as_text=True))


def limits():
    codes = [client(ip="198.51.100.99").get("/api/search?q=ab").status_code for _ in range(95)]
    check("Limits", "/api/search limited (429 after 90/min)", 429 in codes, f"first 429 at request {codes.index(429) + 1}" if 429 in codes else "")
    direct = app.test_client()
    spoofed = [direct.get("/auth/login", environ_base={"REMOTE_ADDR": "8.8.8.8"}, headers={"X-Real-IP": f"10.0.0.{i}"}).status_code
               for i in range(35)]
    check("Limits", "Forged X-Real-IP from a direct client ignored", 429 in spoofed)


def host_header(anon):
    r = anon.get("/", headers={"Host": "evil.example"})
    check("Host", "og:url follows the Host header", None,
          "reflected (harmless while the proxy only serves hourglassbot.net)" if "evil.example" in r.get_data(as_text=True) else "not reflected")
    with app.test_request_context("/", headers={"Host": "hourglassbot.net.evil.example"}):
        uri = get_discord_redirect_uri()
    check("Host", "Fixed Discord redirect URI in production", uri == "https://hourglassbot.net/auth/callback", uri)


def main() -> int:
    quiet = "--quiet" in sys.argv
    anon = client()
    for step in (lambda: headers(anon), session_cookie, lambda: access(anon), csrf, lambda: redirects(anon), oauth,
                 lambda: xss(anon), lambda: sql_injection(anon), lambda: files_methods_errors(anon), limits, lambda: host_header(anon)):
        step()
    width = max(len(name) for _, name, _, _ in RESULTS)
    area = None
    for a, name, status, detail in RESULTS:
        if quiet and status != "FAIL":
            continue
        if a != area:
            print(f"\n== {a}")
            area = a
        print(f"  {status:4}  {name.ljust(width)}  {detail}")
    totals = {k: sum(1 for r in RESULTS if r[2] == k) for k in ("PASS", "FAIL", "INFO")}
    print(f"\n{totals['PASS']} passed, {totals['FAIL']} failed, {totals['INFO']} to note")
    return 1 if totals["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())
