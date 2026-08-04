"""
ArunCode — Flask Backend v4
Run: python app.py  ->  http://127.0.0.1:5500
"""
import os, json, secrets, re
import urllib.parse
from datetime import datetime
from functools import wraps
from flask import Flask, jsonify, request, session, send_from_directory, redirect
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__, static_folder="static", static_url_path="")
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

app.secret_key = "aruncode-secret-key-v5-do-not-share"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
USERS_FILE  = os.path.join(WORKSPACE_ROOT, "users.json")
EMAILS_FILE = os.path.join(BASE_DIR, "emails.json")
WORKSPACE   = os.path.join(BASE_DIR, "workspace")
DOCS_FILE   = os.path.join(BASE_DIR, "docs.json")
YOUTUBE_FILE = os.path.join(BASE_DIR, "videos.json")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads", "videos")
os.makedirs(WORKSPACE, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)

# ── Users ──────────────────────────────────────
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, encoding="utf-8") as f: return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f: json.dump(users, f, indent=2)

USERS = load_users()


def refresh_users():
    global USERS
    USERS = load_users()
    return USERS

CORE_ACCOUNTS = {
    "ArunC": {
        "email":    "chandrasekarana@student.rcdsb.on.ca",
        "password": generate_password_hash("927927"),
        "pin":      "283283",
        "role":     "admin"
    },
    "VijiN": {
        "email":    "nambi.vijilaxmi@gmail.com",
        "password": generate_password_hash("865864"),
        "pin":      "438438",
        "role":     "admin"
    },
    "ParthyC": {
        "email":    "partheinstein@gmail.com",
        "password": generate_password_hash("654654"),
        "pin":      "383383",
        "role":     "security"
    },
    "SujaC": {
        "email":    "you@gmail.com",
        "password": generate_password_hash("543543"),
        "pin":      "383383",
        "role":     "security"
    },
    "SujaG": {
        "email":    "Hi@gmail.com",
        "password": generate_password_hash("543543"),
        "pin":      "383383",
        "role":     "security"
    },
    "ChandrasekaranN": {
        "email":    "natarajchand@gmail.com",
        "password": generate_password_hash("875875"),
        "pin":      "573573",
        "role":     "security"
    },
    "News": {
        "email":    "news@aruncode.com",
        "password": generate_password_hash("927927"),
        "pin":      "283293",
        "role":     "news"
    }
}

for uname, udata in CORE_ACCOUNTS.items():
    # Always overwrite core accounts to keep passwords/roles in sync
    USERS[uname] = udata

save_users(USERS)

# ── Emails ─────────────────────────────────────
def load_emails():
    if not os.path.exists(EMAILS_FILE):
        return []
    try:
        with open(EMAILS_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return []
            return json.loads(content)
    except (json.JSONDecodeError, ValueError):
        return []

def save_emails(emails):
    with open(EMAILS_FILE, "w", encoding="utf-8") as f:
        json.dump(emails, f, indent=2)


def resolve_recipient(to_raw):
    value = (to_raw or "").strip()
    if not value:
        return {"to_user": "", "to_addr": to_raw}

    normalized = value.lower()
    for uname, udata in USERS.items():
        email = (udata.get("email") or "").strip().lower()
        if uname.lower() == normalized or email == normalized:
            return {"to_user": uname, "to_addr": (udata.get("email") or "").strip()}

    if "@" in normalized:
        local_part = normalized.split("@", 1)[0]
        for uname, udata in USERS.items():
            if uname.lower() == local_part:
                return {"to_user": uname, "to_addr": (udata.get("email") or "").strip()}

    return {"to_user": "", "to_addr": value}

# ── Auth Log ───────────────────────────────────
AUTH_LOG = []

def log_event(event_type, username, detail="", ip=""):
    AUTH_LOG.append({
        "time":     datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "type":     event_type,
        "username": username,
        "detail":   detail,
        "ip":       ip
    })
    if len(AUTH_LOG) > 200:
        AUTH_LOG.pop(0)

# ── Auth decorators ────────────────────────────
def login_required(f):
    @wraps(f)
    def d(*a, **k):
        if not session.get("logged_in"):
            return jsonify({"ok": False, "error": "Not authenticated"}), 401
        return f(*a, **k)
    return d

def admin_required(f):
    @wraps(f)
    def d(*a, **k):
        if not session.get("logged_in"):
            return jsonify({"ok": False, "error": "Not authenticated"}), 401
        if session.get("role") != "admin":
            return jsonify({"ok": False, "error": "Admin only"}), 403
        return f(*a, **k)
    return d

def security_required(f):
    @wraps(f)
    def d(*a, **k):
        if not session.get("logged_in"):
            return jsonify({"ok": False, "error": "Not authenticated"}), 401
        if session.get("role") not in ("admin", "security"):
            return jsonify({"ok": False, "error": "Security access required"}), 403
        return f(*a, **k)
    return d

# ── News auth decorator ────────────────────────
def news_required(f):
    @wraps(f)
    def d(*a, **k):
        if not session.get("logged_in"):
            return jsonify({"ok": False, "error": "Not authenticated"}), 401
        if session.get("role") not in ("admin", "news"):
            return jsonify({"ok": False, "error": "News access required"}), 403
        return f(*a, **k)
    return d

@app.route("/uploads/videos/<path:filename>")
def uploaded_video(filename):
    return send_from_directory(UPLOADS_DIR, filename)

# ── Static routes ──────────────────────────────
def serve_theme_or_app_page(filename, theme_filename=None):
    theme_static_dir = os.path.abspath(os.path.join(BASE_DIR, "..", "..", "ArunCode_theme", "static"))
    target_name = theme_filename or filename
    if os.path.exists(os.path.join(theme_static_dir, target_name)):
        return send_from_directory(theme_static_dir, target_name)
    return send_from_directory(app.static_folder, filename)

@app.route("/")
def launcher():       return send_from_directory(app.static_folder, "launcher.html")
@app.route("/terminal")
@app.route("/terminal/")
@app.route("/terminal/index")
@app.route("/terminal/index/")
def terminal():
    theme_login_dir = os.path.abspath(os.path.join(BASE_DIR, "..", "..", "ArunCode_theme", "static"))
    if os.path.exists(os.path.join(theme_login_dir, "index.html")):
        return send_from_directory(theme_login_dir, "index.html")
    return send_from_directory(app.static_folder, "index.html")

@app.route("/home")
def home():           return send_from_directory(app.static_folder, "home.html")
@app.route("/ide")
@app.route("/ide/")
def ide():            return send_from_directory("ide", "index.html")
@app.route("/emails")
@app.route("/emails/")
def emails():         return send_from_directory(app.static_folder, "emails.html")
@app.route("/admin")
@app.route("/admin/")
def admin_panel():    return send_from_directory(app.static_folder, "admin.html")
@app.route("/security")
@app.route("/security/")
def security_panel(): return send_from_directory(app.static_folder, "security.html")
@app.route("/docs")
@app.route("/docs/")
def docs():           return send_from_directory(app.static_folder, "docs.html")
@app.route("/news")
@app.route("/news/")
def news():           return send_from_directory(app.static_folder, "news.html")
@app.route("/github")
@app.route("/github/")
def github():         return send_from_directory(app.static_folder, "github.html")
@app.route("/profile")
@app.route("/profile/")
def profile():        return send_from_directory(app.static_folder, "profile.html")
@app.route("/about/about")
@app.route("/about/about/")
def about():          return send_from_directory(app.static_folder, "about/about.html")
@app.route("/about/versions/version")
def version():        return send_from_directory(app.static_folder, "about/versions/version.html")
@app.route("/about/versions/versionhistory")
def versionhistory(): return send_from_directory(app.static_folder, "about/versions/versionhistory.html")

@app.route("/ptc")
@app.route("/ptc/")
def ptc_page():
    theme_static_dir = os.path.abspath(os.path.join(BASE_DIR, "..", "..", "ArunCode_theme", "static"))
    if os.path.exists(os.path.join(theme_static_dir, "ptc.html")):
        return send_from_directory(theme_static_dir, "ptc.html")
    return send_from_directory(app.static_folder, "ptc.html")

# ── Auth routes ────────────────────────────────
@app.route("/api/register", methods=["POST"])
def api_register():
    d        = request.get_json(silent=True) or {}
    username = (d.get("username") or "").strip()
    email    = (d.get("email")    or "").strip().lower()
    password = (d.get("password") or "")
    requested_role = (d.get("role") or "").strip().lower()
    ip       = request.remote_addr
    refresh_users()
    if not username or not email or not password:
        return jsonify({"ok": False, "error": "All fields required."}), 400
    if len(username) < 3:
        return jsonify({"ok": False, "error": "Username must be 3+ characters."}), 400
    if len(password) < 6:
        return jsonify({"ok": False, "error": "Password must be 6+ characters."}), 400
    if "@" not in email:
        return jsonify({"ok": False, "error": "Invalid email."}), 400
    if username in USERS:
        return jsonify({"ok": False, "error": "Username taken."}), 400
    for u in USERS.values():
        if u["email"].lower() == email:
            return jsonify({"ok": False, "error": "Email already registered."}), 400

    role = "student" if requested_role in {"student", "student-role", "student_role"} else "user"
    USERS[username] = {"email": email, "password": generate_password_hash(password), "pin": "", "role": role}
    save_users(USERS)
    log_event("REGISTER", username, "New account created", ip)
    return jsonify({"ok": True})

@app.route("/api/login", methods=["POST"])
def api_login():
    refresh_users()
    d        = request.get_json(silent=True) or {}
    username = (d.get("username") or "").strip()
    email    = (d.get("email")    or "").strip().lower()
    password = (d.get("password") or "")
    ip       = request.remote_addr
    matched  = next((u for u in USERS if u.lower() == username.lower()), None)
    if matched: username = matched
    user = USERS.get(username)
    if not user or user["email"].lower() != email.lower() or not check_password_hash(user["password"], password):
        log_event("LOGIN_FAIL", username, "Bad credentials", ip)
        return jsonify({"ok": False, "error": "Invalid credentials."}), 401
    session["pending_username"] = username
    needs_pin = (user["role"] in ("admin", "security") and bool(user.get("pin")))
    log_event("LOGIN_ATTEMPT", username, f"Step 1 passed, needs_pin={needs_pin}", ip)
    return jsonify({"ok": True, "needs_pin": needs_pin})

@app.route("/api/verify", methods=["POST"])
def api_verify():
    d        = request.get_json(silent=True) or {}
    code     = (d.get("code") or "").strip()
    username = session.get("pending_username")
    ip       = request.remote_addr
    if not username: return jsonify({"ok": False, "error": "Session expired."}), 400
    user = USERS.get(username)
    if not user: return jsonify({"ok": False, "error": "User not found."}), 400
    if user.get("pin") and code != user["pin"]:
        log_event("PIN_FAIL", username, "Wrong PIN", ip)
        return jsonify({"ok": False, "error": "Incorrect PIN."}), 401
    session["logged_in"] = True
    session["username"]  = username
    session["user"]      = username
    session["role"]      = user["role"]
    session.pop("pending_username", None)
    log_event("LOGIN_OK", username, f"Logged in as {user['role']}", ip)
    return jsonify({"ok": True, "username": username, "role": user["role"]})

@app.route("/api/complete_login", methods=["POST"])
def api_complete_login():
    username = session.get("pending_username")
    ip       = request.remote_addr
    if not username: return jsonify({"ok": False, "error": "Session expired."}), 400
    user = USERS.get(username)
    if not user or user["role"] in ("admin", "security"):
        return jsonify({"ok": False, "error": "Unauthorized."}), 403
    session["logged_in"] = True
    session["username"]  = username
    session["user"]      = username
    session["role"]      = user["role"]  # preserves "news", "user" etc
    session.pop("pending_username", None)
    log_event("LOGIN_OK", username, "Logged in as user", ip)
    return jsonify({"ok": True, "username": username, "role": "user"})

@app.route("/api/logout", methods=["POST"])
def api_logout():
    log_event("LOGOUT", session.get("username", "unknown"))
    session.clear()
    return jsonify({"ok": True})

@app.route("/api/me")
@login_required
def api_me():
    return jsonify({"ok": True, "username": session["username"], "role": session.get("role", "user")})

# ── Admin: users ───────────────────────────────
@app.route("/api/admin/users")
@security_required
def api_admin_users():
    safe = {u: {"email": d["email"], "role": d["role"]} for u, d in USERS.items()}
    return jsonify({"ok": True, "users": safe})

@app.route("/api/admin/users/<username>", methods=["DELETE"])
@security_required
def api_admin_delete_user(username):
    caller_role = session.get("role")
    if username == "ArunC":
        return jsonify({"ok": False, "error": "Cannot delete primary admin."}), 403
    if username not in USERS:
        return jsonify({"ok": False, "error": "User not found."}), 404
    target_role = USERS[username]["role"]
    if caller_role == "security" and target_role in ("admin", "security"):
        return jsonify({"ok": False, "error": "Security manager cannot delete admin accounts."}), 403
    del USERS[username]
    save_users(USERS)
    log_event("DELETE_USER", session.get("username"), f"Deleted {username}")
    return jsonify({"ok": True})

# ── Security: logs ─────────────────────────────
@app.route("/api/security/logs")
@security_required
def api_security_logs():
    return jsonify({"ok": True, "logs": list(reversed(AUTH_LOG))})

@app.route("/api/security/stats")
@security_required
def api_security_stats():
    total    = len(USERS)
    admins   = sum(1 for u in USERS.values() if u["role"] == "admin")
    security = sum(1 for u in USERS.values() if u["role"] == "security")
    regular  = sum(1 for u in USERS.values() if u["role"] == "user")
    students = sum(1 for u in USERS.values() if u["role"] == "student")
    failed   = sum(1 for l in AUTH_LOG if l["type"] in ("LOGIN_FAIL", "PIN_FAIL"))
    return jsonify({"ok": True, "stats": {
        "total_users": total, "admins": admins,
        "security": security, "regular": regular, "students": students,
        "failed_logins": failed, "log_entries": len(AUTH_LOG)
    }})

# ── Emails ─────────────────────────────────────
@app.route("/api/emails", methods=["GET"])
@login_required
def api_emails_get():
    me         = session["username"]
    emails_all = load_emails()
    user_email = USERS.get(me, {}).get("email", "").lower()
    inbox = [e for e in emails_all if e.get("to_user","").lower() == me.lower()
             or e.get("to_addr","").lower() == user_email]
    sent  = [e for e in emails_all if e.get("from_user","").lower() == me.lower()]
    return jsonify({"ok": True, "inbox": inbox, "sent": sent})

@app.route("/api/emails", methods=["POST"])
@login_required
def api_emails_send():
    d       = request.get_json(silent=True) or {}
    to_raw  = (d.get("to")      or "").strip()
    subject = (d.get("subject") or "").strip()
    body    = (d.get("body")    or "").strip()
    me      = session["username"]
    if not to_raw or not subject:
        return jsonify({"ok": False, "error": "To and Subject are required."}), 400
    resolved = resolve_recipient(to_raw)
    to_user = resolved["to_user"]
    to_addr = resolved["to_addr"]
    emails_all = load_emails()
    email = {
        "id":        len(emails_all) + 1,
        "from_user": me,
        "from_addr": USERS.get(me, {}).get("email", ""),
        "to_user":   to_user, "to_addr": to_addr,
        "subject":   subject, "body": body,
        "date":      datetime.now().strftime("%Y-%m-%d %H:%M"),
        "read": False, "starred": False,
    }
    emails_all.append(email)
    save_emails(emails_all)
    return jsonify({"ok": True, "email": email})

@app.route("/api/emails/<int:email_id>/read", methods=["POST"])
@login_required
def api_email_mark_read(email_id):
    emails_all = load_emails()
    for e in emails_all:
        if e["id"] == email_id: e["read"] = True; break
    save_emails(emails_all)
    return jsonify({"ok": True})

@app.route("/api/emails/<int:email_id>/star", methods=["POST"])
@login_required
def api_email_star(email_id):
    emails_all = load_emails()
    for e in emails_all:
        if e["id"] == email_id: e["starred"] = not e.get("starred", False); break
    save_emails(emails_all)
    return jsonify({"ok": True})

@app.route("/api/emails/<int:email_id>", methods=["DELETE"])
@login_required
def api_email_delete(email_id):
    save_emails([e for e in load_emails() if e["id"] != email_id])
    return jsonify({"ok": True})

# ── Docs ───────────────────────────────────────
@app.route("/api/docs", methods=["GET"])
@login_required
def api_docs_get():
    if os.path.exists(DOCS_FILE):
        with open(DOCS_FILE) as f: return jsonify({"ok": True, "docs": json.load(f)})
    return jsonify({"ok": True, "docs": []})

@app.route("/api/docs", methods=["POST"])
@admin_required
def api_docs_save():
    d    = request.get_json(silent=True) or {}
    docs = d.get("docs", [])
    with open(DOCS_FILE, "w") as f: json.dump(docs, f, indent=2)
    return jsonify({"ok": True})

# ── News API ───────────────────────────────────
NEWS_FILE = "news.json"

def load_news():
    if os.path.exists(NEWS_FILE):
        with open(NEWS_FILE) as f: return json.load(f)
    return []

def save_news(posts):
    with open(NEWS_FILE, "w") as f: json.dump(posts, f, indent=2)

@app.route("/api/news", methods=["GET"])
@login_required
def api_news_get():
    return jsonify({"ok": True, "posts": load_news()})

@app.route("/api/news", methods=["POST"])
@news_required
def api_news_post():
    d     = request.get_json(silent=True) or {}
    title = (d.get("title") or "").strip()
    body  = (d.get("body")  or "").strip()
    tag   = (d.get("tag")   or "general").strip()
    if not title or not body:
        return jsonify({"ok": False, "error": "Title and body required."}), 400
    posts = load_news()
    post  = {
        "id":     len(posts) + 1,
        "title":  title, "body": body, "tag": tag,
        "author": session["username"],
        "date":   datetime.now().strftime("%Y-%m-%d %H:%M"),
        "pinned": False
    }
    posts.insert(0, post)
    save_news(posts)
    return jsonify({"ok": True, "post": post})

@app.route("/api/news/<int:post_id>", methods=["PUT"])
@news_required
def api_news_edit(post_id):
    d     = request.get_json(silent=True) or {}
    posts = load_news()
    for p in posts:
        if p["id"] == post_id:
            p["title"]  = (d.get("title") or p["title"]).strip()
            p["body"]   = (d.get("body")  or p["body"]).strip()
            p["tag"]    = (d.get("tag")   or p["tag"])
            p["edited"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            break
    save_news(posts)
    return jsonify({"ok": True})

@app.route("/api/news/<int:post_id>", methods=["DELETE"])
@news_required
def api_news_delete(post_id):
    save_news([p for p in load_news() if p["id"] != post_id])
    return jsonify({"ok": True})

@app.route("/api/news/<int:post_id>/pin", methods=["POST"])
@news_required
def api_news_pin(post_id):
    posts = load_news()
    for p in posts:
        if p["id"] == post_id:
            p["pinned"] = not p.get("pinned", False)
            break
    save_news(posts)
    return jsonify({"ok": True})

# ── Profile ────────────────────────────────────
@app.route("/api/users")
def api_users():
    """Public user list with avatars — no sensitive data"""
    result = {}
    for uname, udata in USERS.items():
        result[uname] = {
            "avatar":  udata.get("avatar", ""),
            "premium": udata.get("premium", False),
            "role":    udata.get("role", "user")
        }
    return jsonify({"ok": True, "users": result})

@app.route("/api/profile")
@login_required
def api_profile_get():
    me   = session["username"]
    user = USERS.get(me, {})
    return jsonify({"ok": True, "username": me, "email": user.get("email",""), "role": user.get("role","user"), "avatar": user.get("avatar",""), "premium": user.get("premium", False), "theme": user.get("theme", "default")})

@app.route("/api/profile/oauth")
@login_required
def api_profile_oauth_get():
    if session.get("role") != "admin":
        return jsonify({"ok": False, "error": "Not authorized"}), 403
    return jsonify({
        "ok": True,
        "oauth": {
            "base_url": OAUTH_SETTINGS.get("base_url", ""),
            "providers": {
                provider: {
                    "client_id": OAUTH_CONFIG[provider].get("client_id", ""),
                    "client_secret": OAUTH_CONFIG[provider].get("client_secret", "")
                }
                for provider in OAUTH_CONFIG
            },
            "redirect_uris": {
                provider: get_redirect_uri(provider)
                for provider in OAUTH_CONFIG
            }
        }
    })

@app.route("/api/profile/oauth", methods=["POST"])
@login_required
def api_profile_oauth_save():
    if session.get("role") != "admin":
        return jsonify({"ok": False, "error": "Not authorized"}), 403
    d = request.get_json(silent=True) or {}
    if "base_url" in d:
        OAUTH_SETTINGS["base_url"] = (d.get("base_url") or "").strip()
    providers = d.get("providers", {})
    for provider, opts in providers.items():
        if provider in OAUTH_CONFIG and isinstance(opts, dict):
            if "client_id" in opts:
                OAUTH_CONFIG[provider]["client_id"] = (opts.get("client_id") or "").strip()
            if "client_secret" in opts:
                OAUTH_CONFIG[provider]["client_secret"] = (opts.get("client_secret") or "").strip()
    save_oauth_config({
        "base_url": OAUTH_SETTINGS.get("base_url", ""),
        **{
            provider: {
                "client_id": OAUTH_CONFIG[provider].get("client_id", ""),
                "client_secret": OAUTH_CONFIG[provider].get("client_secret", "")
            }
            for provider in OAUTH_CONFIG
        }
    })
    return jsonify({"ok": True})

@app.route("/api/profile/avatar", methods=["POST"])
@login_required
def api_profile_avatar():
    me   = session["username"]
    d    = request.get_json(silent=True) or {}
    av   = d.get("avatar", "").strip()
    if not av:
        return jsonify({"ok": False, "error": "No avatar provided."}), 400
    # If image upload, limit size
    if av.startswith("data:") and len(av) > 2*1024*1024:
        return jsonify({"ok": False, "error": "Image too large."}), 400
    USERS[me]["avatar"] = av
    save_users(USERS)
    return jsonify({"ok": True})

@app.route("/api/profile/username", methods=["POST"])
@login_required
def api_profile_username():
    me       = session["username"]
    d        = request.get_json(silent=True) or {}
    new_name = (d.get("username") or "").strip()
    if len(new_name) < 3:
        return jsonify({"ok": False, "error": "Username must be 3+ characters."}), 400
    if new_name in USERS and new_name != me:
        return jsonify({"ok": False, "error": "Username already taken."}), 400
    # Move user data to new key
    USERS[new_name] = USERS.pop(me)
    save_users(USERS)
    session["username"] = new_name
    return jsonify({"ok": True})

@app.route("/api/profile/email", methods=["POST"])
@login_required
def api_profile_email():
    me    = session["username"]
    d     = request.get_json(silent=True) or {}
    email = (d.get("email") or "").strip().lower()
    if "@" not in email:
        return jsonify({"ok": False, "error": "Invalid email."}), 400
    for uname, udata in USERS.items():
        if uname != me and udata["email"].lower() == email:
            return jsonify({"ok": False, "error": "Email already in use."}), 400
    USERS[me]["email"] = email
    save_users(USERS)
    return jsonify({"ok": True})

@app.route("/api/profile/password", methods=["POST"])
@login_required
def api_profile_password():
    me  = session["username"]
    d   = request.get_json(silent=True) or {}
    cur = d.get("current", "")
    nw  = d.get("newpass", "")
    if not check_password_hash(USERS[me]["password"], cur):
        return jsonify({"ok": False, "error": "Current password is incorrect."}), 401
    if len(nw) < 6:
        return jsonify({"ok": False, "error": "New password must be 6+ characters."}), 400
    USERS[me]["password"] = generate_password_hash(nw)
    save_users(USERS)
    return jsonify({"ok": True})

@app.route("/api/profile/pin", methods=["POST"])
@login_required
def api_profile_pin():
    me   = session["username"]
    role = session.get("role","user")
    if role not in ("admin","security"):
        return jsonify({"ok": False, "error": "Only privileged accounts can set a PIN."}), 403
    d   = request.get_json(silent=True) or {}
    pin = (d.get("pin") or "").strip()
    if len(pin) != 6 or not pin.isdigit():
        return jsonify({"ok": False, "error": "PIN must be exactly 6 digits."}), 400
    USERS[me]["pin"] = pin
    save_users(USERS)
    return jsonify({"ok": True})

# ── Github Repos ───────────────────────────────
REPOS_FILE = "repos.json"

def load_repos():
    if os.path.exists(REPOS_FILE):
        with open(REPOS_FILE) as f: return json.load(f)
    return []

def save_repos(r):
    with open(REPOS_FILE, "w") as f: json.dump(r, f, indent=2)

@app.route("/api/repos", methods=["GET"])
@login_required
def api_repos_get():
    return jsonify({"ok": True, "repos": load_repos()})

@app.route("/api/repos", methods=["POST"])
@login_required
def api_repos_create():
    d     = request.get_json(silent=True) or {}
    name  = (d.get("name") or "").strip()
    if not name:
        return jsonify({"ok": False, "error": "Name required."}), 400
    repos = load_repos()
    me    = session["username"]
    if any(r["owner"] == me and r["name"] == name for r in repos):
        return jsonify({"ok": False, "error": "You already have a repo with that name."}), 400
    repo = {
        "id":    int(datetime.now().timestamp() * 1000),
        "name":  name,
        "desc":  (d.get("desc") or "").strip(),
        "lang":  (d.get("lang") or "other"),
        "vis":   (d.get("vis")  or "public"),
        "owner": me,
        "av":    (d.get("av")   or ""),
        "date":  datetime.now().strftime("%Y-%m-%d"),
        "stars": 0,
        "files": d.get("files", [])
    }
    repos.insert(0, repo)
    save_repos(repos)
    return jsonify({"ok": True, "repo": repo})

@app.route("/api/repos/<int:repo_id>", methods=["DELETE"])
@login_required
def api_repos_delete(repo_id):
    repos = load_repos()
    me    = session["username"]
    repo  = next((r for r in repos if r["id"] == repo_id), None)
    if not repo:
        return jsonify({"ok": False, "error": "Not found."}), 404
    if repo["owner"] != me and session.get("role") != "admin":
        return jsonify({"ok": False, "error": "Forbidden."}), 403
    repos = [r for r in repos if r["id"] != repo_id]
    save_repos(repos)
    return jsonify({"ok": True})

@app.route("/api/repos/<int:repo_id>/files", methods=["POST"])
@login_required
def api_repos_upload(repo_id):
    repos = load_repos()
    me    = session["username"]
    repo  = next((r for r in repos if r["id"] == repo_id), None)
    if not repo:
        return jsonify({"ok": False, "error": "Not found."}), 404
    if repo["owner"] != me:
        return jsonify({"ok": False, "error": "Forbidden."}), 403
    d     = request.get_json(silent=True) or {}
    files = d.get("files", [])
    repo["files"] = repo.get("files", [])
    for f in files:
        idx = next((i for i,x in enumerate(repo["files"]) if x.get("name")==f.get("name") and x.get("folder")==f.get("folder")), None)
        if idx is not None: repo["files"][idx] = f
        else: repo["files"].append(f)
    save_repos(repos)
    return jsonify({"ok": True})

@app.route("/api/repos/<int:repo_id>/files/<path:fname>", methods=["PUT"])
@login_required
def api_repos_save_file(repo_id, fname):
    repos = load_repos()
    me    = session["username"]
    repo  = next((r for r in repos if r["id"] == repo_id), None)
    if not repo or repo["owner"] != me:
        return jsonify({"ok": False, "error": "Forbidden."}), 403
    d       = request.get_json(silent=True) or {}
    content = d.get("content", "")
    folder  = d.get("folder", "")
    for f in repo.get("files", []):
        if f.get("name") == fname and f.get("folder","") == folder:
            f["content"] = content
            break
    else:
        repo.setdefault("files", []).append({"name": fname, "content": content, "folder": folder})
    save_repos(repos)
    return jsonify({"ok": True})

@app.route("/api/repos/<int:repo_id>/folder", methods=["POST"])
@login_required
def api_repos_add_folder(repo_id):
    repos = load_repos()
    me    = session["username"]
    repo  = next((r for r in repos if r["id"] == repo_id), None)
    if not repo or repo["owner"] != me:
        return jsonify({"ok": False, "error": "Forbidden."}), 403
    d    = request.get_json(silent=True) or {}
    name = (d.get("name") or "").strip()
    if not name:
        return jsonify({"ok": False, "error": "Name required."}), 400
    repo.setdefault("files", []).append({"type": "folder", "name": name})
    save_repos(repos)
    return jsonify({"ok": True})

@app.route("/api/repos/<int:repo_id>/stars", methods=["POST"])
@login_required
def api_repos_star(repo_id):
    repos = load_repos()
    repo  = next((r for r in repos if r["id"] == repo_id), None)
    if not repo:
        return jsonify({"ok": False, "error": "Not found."}), 404
    me    = session["username"]
    repo.setdefault("starredBy", [])
    if me in repo["starredBy"]:
        repo["starredBy"].remove(me)
        repo["stars"] = max(0, repo.get("stars", 1) - 1)
        starred = False
    else:
        repo["starredBy"].append(me)
        repo["stars"] = repo.get("stars", 0) + 1
        starred = True
    save_repos(repos)
    return jsonify({"ok": True, "starred": starred, "stars": repo["stars"]})

@app.route("/api/repos/<int:repo_id>/newfile", methods=["POST"])
@login_required
def api_repos_new_file(repo_id):
    repos = load_repos()
    me    = session["username"]
    repo  = next((r for r in repos if r["id"] == repo_id), None)
    if not repo or repo["owner"] != me:
        return jsonify({"ok": False, "error": "Forbidden."}), 403
    d      = request.get_json(silent=True) or {}
    name   = (d.get("name") or "").strip()
    folder = (d.get("folder") or "").strip()
    if not name:
        return jsonify({"ok": False, "error": "Name required."}), 400
    entry = {"name": name, "content": ""}
    if folder: entry["folder"] = folder
    repo.setdefault("files", []).append(entry)
    save_repos(repos)
    return jsonify({"ok": True})

@app.route("/api/repos/<int:repo_id>/delfile", methods=["POST"])
@login_required
def api_repos_del_file(repo_id):
    repos = load_repos()
    me    = session["username"]
    repo  = next((r for r in repos if r["id"] == repo_id), None)
    if not repo or repo["owner"] != me:
        return jsonify({"ok": False, "error": "Forbidden."}), 403
    d      = request.get_json(silent=True) or {}
    name   = d.get("name","")
    folder = d.get("folder","")
    repo["files"] = [f for f in repo.get("files",[]) if not (f.get("name")==name and f.get("folder","")==folder)]
    save_repos(repos)
    return jsonify({"ok": True})

@app.route("/api/repos/<int:repo_id>/delfolder", methods=["POST"])
@login_required
def api_repos_del_folder(repo_id):
    repos = load_repos()
    me    = session["username"]
    repo  = next((r for r in repos if r["id"] == repo_id), None)
    if not repo or repo["owner"] != me:
        return jsonify({"ok": False, "error": "Forbidden."}), 403
    d    = request.get_json(silent=True) or {}
    name = d.get("name","")
    repo["files"] = [f for f in repo.get("files",[]) if not (f.get("name")==name and f.get("type")=="folder") and f.get("folder","")!=name]
    save_repos(repos)
    return jsonify({"ok": True})

# ── Files (IDE) ────────────────────────────────
def safe_path(filename):
    name = os.path.basename(filename.replace("/", os.sep).replace("..", ""))
    return os.path.join(WORKSPACE, name)

@app.route("/api/files", methods=["GET"])
@login_required
def api_files_list():
    items = []
    for entry in sorted(os.scandir(WORKSPACE), key=lambda e: (not e.is_dir(), e.name)):
        items.append({"name": entry.name, "type": "folder" if entry.is_dir() else "file",
                      "size": entry.stat().st_size if entry.is_file() else 0})
    return jsonify({"ok": True, "files": items})

@app.route("/api/files/<path:filename>", methods=["GET"])
@login_required
def api_file_read(filename):
    path = safe_path(filename)
    if not os.path.isfile(path): return jsonify({"ok": False, "error": "File not found."}), 404
    with open(path, "r", errors="replace") as f: content = f.read()
    return jsonify({"ok": True, "content": content})

@app.route("/api/files/<path:filename>", methods=["POST"])
@login_required
def api_file_save(filename):
    path = safe_path(filename)
    d    = request.get_json(silent=True) or {}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f: f.write(d.get("content", ""))
    return jsonify({"ok": True})

@app.route("/api/files/<path:filename>", methods=["DELETE"])
@login_required
def api_file_delete(filename):
    path = safe_path(filename)
    if not os.path.exists(path): return jsonify({"ok": False, "error": "Not found."}), 404
    if os.path.isdir(path):
        import shutil; shutil.rmtree(path)
    else:
        os.remove(path)
    return jsonify({"ok": True})

@app.route("/api/folders", methods=["POST"])
@login_required
def api_folder_create():
    d    = request.get_json(silent=True) or {}
    name = (d.get("name") or "").strip()
    if not name: return jsonify({"ok": False, "error": "Folder name required."}), 400
    os.makedirs(os.path.join(WORKSPACE, os.path.basename(name)), exist_ok=True)
    return jsonify({"ok": True})

@app.route("/api/unzip", methods=["POST"])
@login_required
def api_unzip():
    import zipfile, shutil
    d        = request.get_json(silent=True) or {}
    filename = (d.get("filename") or "").strip()
    dest     = (d.get("dest") or "").strip() or ""
    if not filename:
        return jsonify({"ok": False, "error": "filename required"}), 400
    zip_path = safe_path(filename)
    if not os.path.isfile(zip_path):
        return jsonify({"ok": False, "error": "File not found: " + filename}), 404
    if not zipfile.is_zipfile(zip_path):
        return jsonify({"ok": False, "error": filename + " is not a valid zip file"}), 400
    dest_path = os.path.join(WORKSPACE, os.path.basename(dest)) if dest else WORKSPACE
    os.makedirs(dest_path, exist_ok=True)
    extracted = []
    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            for member in z.namelist():
                z.extract(member, dest_path)
                extracted.append(member)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    return jsonify({"ok": True, "extracted": extracted, "count": len(extracted), "dest": dest_path})

# ── Premium ────────────────────────────────────
PREMIUM_CODES = {
    "ARUNPREM-2025":  {"used": False, "desc": "VIP code"},
    "ARUNCODE-GOLD":  {"used": False, "desc": "Gold tier"},
    "PREMIUM-LAUNCH": {"used": False, "desc": "Early access"},
    "VIP-ARUNCODE":   {"used": False, "desc": "VIP code"},
    "ACPREM-SPECIAL": {"used": False, "desc": "Special access"},
    "KYKQLLVHPX1W":   {"used": False, "desc": "VIP code"},
    "WOYONOXTSXZY":   {"used": False, "desc": "VIP code"},
    "85UURINTKRKR":   {"used": False, "desc": "VIP code"},
    "BNJYQZBA3TBH":   {"used": False, "desc": "VIP code"},
    "SJLHYFN2IBHE":   {"used": False, "desc": "VIP code"},
    "MBHMB8GCNQUN":   {"used": False, "desc": "VIP code"},
    "KN17H14MNQZF":   {"used": False, "desc": "VIP code"},
    "PIIXLEGZE9QQ":   {"used": False, "desc": "VIP code"},
    "CGFQGVNBCPET":   {"used": False, "desc": "VIP code"},
    "QQISPD277HVM":   {"used": False, "desc": "VIP code"},
    "UCYAXCVFYECT":   {"used": False, "desc": "VIP code"},
    "9M5D621ABQ6X":   {"used": False, "desc": "VIP code"},
    "EJGYCCOLXBNY":   {"used": False, "desc": "VIP code"},
    "EANL9HO1Z98J":   {"used": False, "desc": "VIP code"},
    "QQX7U2BNXITR":   {"used": False, "desc": "VIP code"},
    "WRPW2CWLT1Q4":   {"used": False, "desc": "VIP code"},
    "OMKGRROFLOIE":   {"used": False, "desc": "VIP code"},
    "XWPOYO6I6UGX":   {"used": False, "desc": "VIP code"},
    "OSRJM5FAKZAA":   {"used": False, "desc": "VIP code"},
    "FPMVBRWIMQZA":   {"used": False, "desc": "VIP code"},
    "VXOSRXYMJHNM":   {"used": False, "desc": "VIP code"},
    "16P5E3MUJLFA":   {"used": False, "desc": "VIP code"},
    "DQVEY6BNNG2X":   {"used": False, "desc": "VIP code"},
    "FK83GFLJ3VEH":   {"used": False, "desc": "VIP code"},
    "KLEUEY1JVHRU":   {"used": False, "desc": "VIP code"},
    "URB21FAJBMJ3":   {"used": False, "desc": "VIP code"},
    "HSX0Q2JXCDR5":   {"used": False, "desc": "VIP code"},
    "CT0KLTXWXHX4":   {"used": False, "desc": "VIP code"},
    "UEVYVAH4KOFY":   {"used": False, "desc": "VIP code"},
    "AFALPGIJBTHR":   {"used": False, "desc": "VIP code"},
    "AIGFYYGNE E07":  {"used": False, "desc": "VIP code"},
    "PTLYDEGA7GTU":   {"used": False, "desc": "VIP code"},
}

@app.route("/playstation")
@app.route("/playstation/")
def playstation(): return serve_theme_or_app_page("playstation.html")

@app.route("/premium")
@app.route("/premium/")
def premium_page(): return serve_theme_or_app_page("premium.html")

@app.route("/api/premium/status")
@login_required
def api_premium_status():
    me   = session["username"]
    user = USERS.get(me, {})
    return jsonify({"ok": True, "premium": user.get("premium", False), "theme": user.get("theme", "default")})

@app.route("/api/premium/redeem", methods=["POST"])
@login_required
def api_premium_redeem():
    me   = session["username"]
    d    = request.get_json(silent=True) or {}
    code = (d.get("code") or "").strip().upper()
    if not code:
        return jsonify({"ok": False, "error": "No code provided."}), 400
    if code not in PREMIUM_CODES:
        return jsonify({"ok": False, "error": "Invalid code."}), 400
    if PREMIUM_CODES[code]["used"]:
        return jsonify({"ok": False, "error": "This code has already been used."}), 400
    PREMIUM_CODES[code]["used"] = True
    USERS[me]["premium"] = True
    save_users(USERS)
    return jsonify({"ok": True, "message": "Welcome to ArunCode Premium!"})

@app.route("/api/premium/theme", methods=["POST"])
@login_required
def api_premium_theme():
    me   = session["username"]
    user = USERS.get(me, {})
    if not user.get("premium"):
        return jsonify({"ok": False, "error": "Premium required."}), 403
    d     = request.get_json(silent=True) or {}
    theme = (d.get("theme") or "default").strip()
    USERS[me]["theme"] = theme
    save_users(USERS)
    return jsonify({"ok": True, "theme": theme})

@app.route("/api/premium/revoke", methods=["POST"])
@login_required
def api_premium_revoke():
    me   = session["username"]
    role = USERS.get(me, {}).get("role","")
    if role != "admin":
        return jsonify({"ok": False, "error": "Admins only."}), 403
    d      = request.get_json(silent=True) or {}
    target = (d.get("username") or "").strip()
    if target not in USERS:
        return jsonify({"ok": False, "error": "User not found."}), 404
    USERS[target]["premium"] = False
    save_users(USERS)
    return jsonify({"ok": True})


@app.route("/api/exec", methods=["POST"])
@login_required
def api_exec():
    import subprocess
    d   = request.get_json(silent=True) or {}
    cmd = (d.get("cmd") or "").strip()
    cwd = (d.get("cwd") or WORKSPACE)
    if not cmd:
        return jsonify({"ok": False, "error": "no command"}), 400
    # Block dangerous commands
    blocked = ["rm -rf /", "mkfs", ":(){:|:&};:", "shutdown", "reboot",
               "halt", "poweroff", "chmod -R 777 /", "dd if=/dev/"]
    for b in blocked:
        if b.lower() in cmd.lower():
            return jsonify({"ok": False, "error": "operation not permitted"}), 403
    # Resolve cwd safely
    safe_cwd = os.path.abspath(cwd) if os.path.isdir(cwd) else os.path.abspath(WORKSPACE)
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=15, cwd=safe_cwd
        )
        # If cd command, return new cwd
        new_cwd = safe_cwd
        if cmd.strip().startswith("cd "):
            dest = cmd.strip()[3:].strip()
            candidate = os.path.abspath(os.path.join(safe_cwd, dest))
            if os.path.isdir(candidate):
                new_cwd = candidate
        return jsonify({
            "ok":     True,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "code":   result.returncode,
            "cwd":    new_cwd
        })
    except subprocess.TimeoutExpired:
        return jsonify({"ok": False, "error": "timeout after 15 seconds"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/mc")
@app.route("/mc/")
def mc_redirect():
    return serve_theme_or_app_page("mc.html")

# ── MESSENGER ────────────────────────────────────────────
MSGS_FILE = os.path.join(BASE_DIR, "messages.json")
ROOMS_FILE = os.path.join(BASE_DIR, "rooms.json")

def load_msgs():
    try:
        if os.path.exists(MSGS_FILE):
            with open(MSGS_FILE) as f: return json.load(f)
    except: pass
    return {}

def save_msgs(m):
    with open(MSGS_FILE, "w") as f: json.dump(m, f)

def load_rooms():
    try:
        if os.path.exists(ROOMS_FILE):
            with open(ROOMS_FILE) as f: return json.load(f)
    except: pass
    return {}

def save_rooms(r):
    with open(ROOMS_FILE, "w") as f: json.dump(r, f)

@app.route("/messenger")
@app.route("/messenger/")
def messenger(): return send_from_directory(app.static_folder, "messenger.html")

@app.route("/message")
@app.route("/message/")
def message_app(): return serve_theme_or_app_page("message.html")

@app.route("/youtube")
@app.route("/youtube/")
def youtube_app(): return serve_theme_or_app_page("youtube.html")

@app.route("/api/messenger/rooms")
@login_required
def api_get_rooms():
    me = session.get("username") or session.get("user")
    rooms = load_rooms()
    my_rooms = {rid: r for rid, r in rooms.items() if me in r.get("members", [])}
    return jsonify({"ok": True, "rooms": my_rooms})

@app.route("/api/messenger/rooms", methods=["POST"])
@login_required
def api_create_room():
    me = session.get("username") or session.get("user")
    d = request.get_json(silent=True) or {}
    name = (d.get("name") or "").strip()
    members = d.get("members", [])
    is_dm = d.get("dm", False)
    if not name: return jsonify({"ok": False, "error": "Name required"}), 400
    if me not in members: members.append(me)
    rooms = load_rooms()
    # For DMs check if already exists
    if is_dm and len(members) == 2:
        for rid, r in rooms.items():
            if r.get("dm") and set(r.get("members", [])) == set(members):
                return jsonify({"ok": True, "room": r, "id": rid})
    rid = "room_" + str(int(__import__("time").time() * 1000))
    room = {"id": rid, "name": name, "members": members, "dm": is_dm,
            "created": __import__("time").time(), "creator": me, "avatar": d.get("avatar", "")}
    rooms[rid] = room
    save_rooms(rooms)
    return jsonify({"ok": True, "room": room, "id": rid})

@app.route("/api/messenger/rooms/<rid>/messages")
@login_required
def api_get_messages(rid):
    me = session.get("username") or session.get("user")
    rooms = load_rooms()
    if rid not in rooms or me not in rooms[rid].get("members", []):
        return jsonify({"ok": False, "error": "Not a member"}), 403
    msgs = load_msgs()
    return jsonify({"ok": True, "messages": msgs.get(rid, [])})

@app.route("/api/messenger/rooms/<rid>/messages", methods=["POST"])
@login_required
def api_post_message(rid):
    me = session.get("username") or session.get("user")
    rooms = load_rooms()
    if rid not in rooms or me not in rooms[rid].get("members", []):
        return jsonify({"ok": False, "error": "Not a member"}), 403

    d = request.get_json(silent=True) or {}
    text = (d.get("text") or "").strip()
    file_data = d.get("file", "")
    file_name = d.get("fileName", "")
    file_type = d.get("fileType", "")
    if not text and not file_data:
        return jsonify({"ok": False, "error": "Empty message"}), 400

    import time
    msg = {
        "id": "m_" + str(int(time.time() * 1000)),
        "author": me,
        "authorAv": d.get("authorAv", ""),
        "text": text,
        "file": file_data,
        "fileName": file_name,
        "fileType": file_type,
        "time": time.time()
    }
    msgs = load_msgs()
    msgs.setdefault(rid, []).append(msg)
    if len(msgs[rid]) > 500:
        msgs[rid] = msgs[rid][-500:]
    save_msgs(msgs)
    return jsonify({"ok": True, "message": msg})

@app.route("/api/messenger/users")
@login_required
def api_msg_users():
    me = session.get("username") or session.get("user")
    result = {}
    for uname, udata in USERS.items():
        if uname != me:
            result[uname] = {"avatar": udata.get("avatar", ""), "role": udata.get("role", "user")}
    return jsonify({"ok": True, "users": result})

# ── SOCKET EVENTS ──────────────────────────────────────────
@socketio.on("join")
def on_join(data):
    room = data.get("room")
    if room: join_room(room)

@socketio.on("leave")
def on_leave(data):
    room = data.get("room")
    if room: leave_room(room)

@socketio.on("message")
def on_message(data):
    import time
    room   = data.get("room")
    author = data.get("author")
    text   = data.get("text", "").strip()
    file_data = data.get("file")   # base64
    file_name = data.get("fileName")
    file_type = data.get("fileType")
    if not room or not author: return
    rooms = load_rooms()
    if room not in rooms or author not in rooms[room].get("members", []): return
    msg = {
        "id": "m_" + str(int(time.time() * 1000)),
        "author": author,
        "authorAv": data.get("authorAv", ""),
        "text": text,
        "file": file_data,
        "fileName": file_name,
        "fileType": file_type,
        "time": time.time()
    }
    msgs = load_msgs()
    if room not in msgs: msgs[room] = []
    msgs[room].append(msg)
    # Keep last 500 messages per room
    if len(msgs[room]) > 500: msgs[room] = msgs[room][-500:]
    save_msgs(msgs)
    emit("message", msg, to=room)

@socketio.on("typing")
def on_typing(data):
    room = data.get("room")
    if room: emit("typing", data, to=room, include_self=False)


# ── YOUTUBE ───────────────────────────────────────────────
def normalize_youtube_url(url):
    if not url:
        return ""
    value = url.strip()
    if "youtube.com/watch?v=" in value:
        video_id = value.split("v=", 1)[1].split("&", 1)[0]
        return f"https://www.youtube.com/embed/{video_id}"
    if "youtu.be/" in value:
        video_id = value.split("youtu.be/", 1)[1].split("?", 1)[0].split("/", 1)[0]
        return f"https://www.youtube.com/embed/{video_id}"
    return value


def load_videos():
    if os.path.exists(YOUTUBE_FILE):
        try:
            with open(YOUTUBE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_videos(videos):
    with open(YOUTUBE_FILE, "w", encoding="utf-8") as f:
        json.dump(videos, f, indent=2)


def store_uploaded_video(uploaded_file):
    if not uploaded_file or not getattr(uploaded_file, "filename", ""):
        return ""

    raw_name = os.path.basename(uploaded_file.filename)
    name, ext = os.path.splitext(raw_name)
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", name) or "video"
    target_name = f"{safe_name}{ext or '.mp4'}"
    count = 1
    while os.path.exists(os.path.join(UPLOADS_DIR, target_name)):
        target_name = f"{safe_name}_{count}{ext or '.mp4'}"
        count += 1

    uploaded_file.save(os.path.join(UPLOADS_DIR, target_name))
    return f"/uploads/videos/{target_name}"


@app.route("/api/youtube/videos", methods=["GET"])
def api_youtube_videos():
    videos = load_videos()
    return jsonify({"ok": True, "videos": videos})

@app.route("/api/youtube/videos", methods=["POST"])
def api_youtube_create_video():
    if request.is_json:
        d = request.get_json(silent=True) or {}
        uploaded_file = None
    else:
        d = request.form.to_dict()
        uploaded_file = request.files.get("video")

    title = (d.get("title") or "").strip()
    desc = (d.get("description") or "").strip()
    video_url = normalize_youtube_url(d.get("videoUrl") or "")
    thumbnail_url = (d.get("thumbnailUrl") or "").strip()
    if not title:
        return jsonify({"ok": False, "error": "Title required"}), 400

    uploaded_path = store_uploaded_video(uploaded_file) if uploaded_file else ""
    if uploaded_path:
        video_url = uploaded_path

    videos = load_videos()
    video = {
        "id": len(videos) + 1,
        "title": title,
        "description": desc,
        "videoUrl": video_url or "https://www.youtube.com/embed/dQw4w9WgXcQ",
        "thumbnailUrl": thumbnail_url or "https://images.unsplash.com/photo-1516280440614-37939bbacd81?auto=format&fit=crop&w=900&q=80",
        "author": session.get("username") or session.get("user") or "guest",
        "views": 0,
        "likes": 0,
        "comments": []
    }
    videos.insert(0, video)
    save_videos(videos)
    return jsonify({"ok": True, "videos": videos})

@app.route("/api/youtube/videos/<int:video_id>/comment", methods=["POST"])
def api_youtube_comment(video_id):
    d = request.get_json(silent=True) or {}
    text = (d.get("text") or "").strip()
    if not text:
        return jsonify({"ok": False, "error": "Comment required"}), 400
    videos = load_videos()
    for video in videos:
        if video.get("id") == video_id:
            video.setdefault("comments", []).append({
                "author": session.get("username") or session.get("user") or "guest",
                "text": text
            })
            save_videos(videos)
            return jsonify({"ok": True, "video": video})
    return jsonify({"ok": False, "error": "Video not found"}), 404

# ── OAUTH ─────────────────────────────────────────────────
import urllib.parse, urllib.request, secrets

OAUTH_CONFIG_FILE = "oauth_config.json"
OAUTH_SETTINGS = {"base_url": os.environ.get("BASE_URL", "")}

def load_oauth_config():
    if os.path.exists(OAUTH_CONFIG_FILE):
        with open(OAUTH_CONFIG_FILE) as f: return json.load(f)
    return {}

def save_oauth_config(cfg):
    with open(OAUTH_CONFIG_FILE, "w") as f: json.dump(cfg, f, indent=2)

def normalize_base_url(url):
    if not url:
        return ""
    base = url.strip().rstrip("/")
    for provider in OAUTH_CONFIG:
        suffix = f"/auth/{provider}/callback"
        if base.endswith(suffix):
            base = base[: -len(suffix)].rstrip("/")
            break
        suffix2 = f"/auth/{provider}"
        if base.endswith(suffix2):
            base = base[: -len(suffix2)].rstrip("/")
            break
    return base

OAUTH_CONFIG = {
    "github": {
        "client_id":     os.environ.get("GITHUB_CLIENT_ID", ""),
        "client_secret": os.environ.get("GITHUB_CLIENT_SECRET", ""),
        "auth_url":      "https://github.com/login/oauth/authorize",
        "token_url":     "https://github.com/login/oauth/access_token",
        "api_url":       "https://api.github.com/user",
        "scope":         "read:user user:email",
    },
    "google": {
        "client_id":     os.environ.get("GOOGLE_CLIENT_ID", ""),
        "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET", ""),
        "auth_url":      "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url":     "https://oauth2.googleapis.com/token",
        "api_url":       "https://www.googleapis.com/oauth2/v3/userinfo",
        "scope":         "openid email profile",
    },
    "apple": {
        "client_id":     os.environ.get("APPLE_CLIENT_ID", ""),
        "client_secret": os.environ.get("APPLE_CLIENT_SECRET", ""),
        "auth_url":      "https://appleid.apple.com/auth/authorize",
        "token_url":     "https://appleid.apple.com/auth/token",
        "api_url":       "",
        "scope":         "name email",
    }
}

_saved_oauth_config = load_oauth_config()
if _saved_oauth_config:
    if _saved_oauth_config.get("base_url"):
        OAUTH_SETTINGS["base_url"] = normalize_base_url(_saved_oauth_config.get("base_url"))
    for provider, opts in _saved_oauth_config.items():
        if provider in OAUTH_CONFIG and isinstance(opts, dict):
            for key in ("client_id", "client_secret"):
                if opts.get(key) is not None:
                    OAUTH_CONFIG[provider][key] = opts.get(key)

def get_redirect_uri(provider):
    if OAUTH_SETTINGS.get("base_url"):
        base = normalize_base_url(OAUTH_SETTINGS.get("base_url"))
    elif os.environ.get("BASE_URL", ""):
        base = normalize_base_url(os.environ.get("BASE_URL", ""))
    else:
        scheme = request.headers.get("X-Forwarded-Proto") or request.scheme
        host = request.headers.get("X-Forwarded-Host") or request.headers.get("Host") or request.host
        base = f"{scheme}://{host}"
    return base.rstrip("/") + "/auth/" + provider + "/callback"

def oauth_get(url, token):
    import urllib.request
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token, "Accept": "application/json", "User-Agent": "ArunCode/5.0"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode())

def oauth_token_exchange(provider, code):
    import urllib.request, urllib.parse
    cfg = OAUTH_CONFIG[provider]
    data = urllib.parse.urlencode({
        "client_id":     cfg["client_id"],
        "client_secret": cfg["client_secret"],
        "code":          code,
        "redirect_uri":  get_redirect_uri(provider),
        "grant_type":    "authorization_code",
    }).encode()
    headers = {"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"}
    req = urllib.request.Request(cfg["token_url"], data=data, headers=headers)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode())

@app.route("/auth/<provider>")
def oauth_start(provider):
    if provider not in OAUTH_CONFIG:
        return jsonify({"ok": False, "error": "Unknown provider"}), 400
    cfg = OAUTH_CONFIG[provider]
    if not cfg["client_id"] or not cfg["client_secret"]:
        return jsonify({"ok": False, "error": provider.capitalize() + " OAuth not configured. Set " + provider.upper() + "_CLIENT_ID and " + provider.upper() + "_CLIENT_SECRET environment variables."}), 400
    state = secrets.token_urlsafe(16)
    session["oauth_state"] = state
    session["oauth_provider"] = provider
    # Store next URL
    next_url = request.args.get("next", "/home")
    session["oauth_next"] = next_url
    params = {
        "client_id":    cfg["client_id"],
        "redirect_uri": get_redirect_uri(provider),
        "scope":        cfg["scope"],
        "state":        state,
        "response_type": "code",
    }
    if provider == "apple":
        params["response_mode"] = "form_post"
    return redirect(cfg["auth_url"] + "?" + urllib.parse.urlencode(params))

@app.route("/auth/<provider>/callback", methods=["GET", "POST"])
def oauth_callback(provider):
    if provider not in OAUTH_CONFIG:
        return redirect("/terminal?error=unknown_provider")
    # Verify state
    state = request.args.get("state") or request.form.get("state")
    if state != session.get("oauth_state"):
        return redirect("/terminal?error=state_mismatch")
    code = request.args.get("code") or request.form.get("code")
    if not code:
        return redirect("/terminal?error=no_code")
    try:
        token_data = oauth_token_exchange(provider, code)
        access_token = token_data.get("access_token")
        if not access_token:
            return redirect("/terminal?error=no_token")
        # Get user info
        profile = {}
        if provider == "github":
            profile = oauth_get(OAUTH_CONFIG["github"]["api_url"], access_token)
            email = profile.get("email") or (profile.get("login", "") + "@github.local")
            name  = profile.get("login") or profile.get("name") or "github_user"
            uid   = "github_" + str(profile.get("id", ""))
            avatar_url = profile.get("avatar_url", "")
        elif provider == "google":
            profile = oauth_get(OAUTH_CONFIG["google"]["api_url"], access_token)
            email = profile.get("email", "")
            name  = profile.get("name") or email.split("@")[0]
            uid   = "google_" + profile.get("sub", "")
            avatar_url = profile.get("picture", "")
        elif provider == "apple":
            # Apple sends user info only on first login
            import base64
            id_token = token_data.get("id_token", "")
            payload = id_token.split(".")[1] if id_token else ""
            payload += "=" * (4 - len(payload) % 4)
            try:
                claims = json.loads(base64.b64decode(payload))
                email = claims.get("email", "")
            except:
                email = ""
            name = request.form.get("user", "")
            if name:
                try: udata = json.loads(name); name = (udata.get("name",{}).get("firstName","") + " " + udata.get("name",{}).get("lastName","")).strip() or email.split("@")[0]
                except: name = email.split("@")[0]
            else: name = email.split("@")[0]
            uid = "apple_" + email.replace("@", "_").replace(".", "_")
            avatar_url = ""
        else:
            return redirect("/terminal?error=unsupported_provider")
        USERS = load_users()
        current_user = session.get("username") or session.get("user")
        if session.get("logged_in") and current_user:
            # Linking provider to an already-authenticated account
            existing_account = None
            for uname, udata in USERS.items():
                linked = udata.get("linked_accounts", {})
                if uname != current_user and (uid in linked.values() or linked.get(provider) == uid):
                    existing_account = uname
                    break
            if existing_account:
                return redirect("/terminal?error=provider_already_linked")
            USERS.setdefault(current_user, {}).setdefault("linked_accounts", {})[provider] = uid
            if avatar_url and not USERS[current_user].get("avatar"):
                USERS[current_user]["oauth_avatar"] = avatar_url
            save_users(USERS)
            next_url = session.pop("oauth_next", "/home")
            return redirect(next_url)

        # Find or create ArunCode account for unauthenticated users
        linked_user = None
        for uname, udata in USERS.items():
            linked = udata.get("linked_accounts", {})
            if uid in linked.values() or linked.get(provider) == uid:
                linked_user = uname
                break
        # Check by email
        if not linked_user:
            for uname, udata in USERS.items():
                if udata.get("email", "").lower() == email.lower():
                    linked_user = uname
                    break
        if linked_user:
            # Log in existing user
            USERS[linked_user].setdefault("linked_accounts", {})[provider] = uid
            if avatar_url and not USERS[linked_user].get("avatar"):
                USERS[linked_user]["oauth_avatar"] = avatar_url
            save_users(USERS)
            session["logged_in"] = True
            session["username"] = linked_user
            session["user"] = linked_user
            session["role"] = USERS[linked_user].get("role", "user")
        else:
            # Create new account
            safe_name = "".join(c for c in name if c.isalnum() or c in "_-")[:20] or "user"
            base_name = safe_name
            counter = 1
            while safe_name in USERS:
                safe_name = base_name + str(counter)
                counter += 1
            new_user = {
                "email":    email,
                "password": generate_password_hash(secrets.token_urlsafe(32)),
                "pin":      str(secrets.randbelow(900000) + 100000),
                "role":     "user",
                "linked_accounts": {provider: uid},
                "oauth_avatar": avatar_url,
                "avatar": "",
            }
            USERS[safe_name] = new_user
            save_users(USERS)
            session["logged_in"] = True
            session["username"] = safe_name
            session["user"] = safe_name
            session["role"] = "user"
        next_url = session.pop("oauth_next", "/home")
        return redirect(next_url)
    except Exception as ex:
        return redirect("/terminal?error=" + urllib.parse.quote(str(ex)))

@app.route("/api/auth/linked")
@login_required
def api_linked_accounts():
    me = session.get("username") or session.get("user")
    USERS = load_users()
    linked = USERS.get(me, {}).get("linked_accounts", {})
    return jsonify({"ok": True, "linked": linked})

@app.route("/api/auth/unlink", methods=["POST"])
@login_required
def api_unlink():
    me = session.get("username") or session.get("user")
    d = request.get_json(silent=True) or {}
    provider = d.get("provider", "")
    USERS = load_users()
    if me in USERS:
        USERS[me].setdefault("linked_accounts", {}).pop(provider, None)
        save_users(USERS)
    return jsonify({"ok": True})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    print("\n  ArunCode backend starting...")
    print(f"  Open -> http://127.0.0.1:{port}\n")
    socketio.run(app, host="0.0.0.0", port=port, debug=True, allow_unsafe_werkzeug=True)