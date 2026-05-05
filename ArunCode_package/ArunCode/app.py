from flask import Flask, send_from_directory, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash
import os
import json

app = Flask(
    __name__,
    static_folder="static",
    static_url_path="/static"
)

app.secret_key = os.environ.get("ARUNCODE_SECRET", "aruncode-secret-key-v5-do-not-share")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(BASE_DIR, "users.json")


def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)


def ensure_default_users():
    users = load_users()
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
    save_users(users)
    return users


USERS = ensure_default_users()


def find_user(username, email):
    user = USERS.get(username)
    if user and user.get("email", "").lower() == email.lower():
        return user
    return None


def find_user_by_username(username):
    return USERS.get(username)


def current_user():
    username = session.get("user")
    return find_user_by_username(username) if username else None


# -------------------------
# MAIN PAGES (optional)
# -------------------------
@app.route("/")
def home():
    return send_from_directory("static", "index.html")


# -------------------------
# DOWNLOAD ROUTE (FIX)
# -------------------------
@app.route("/download/rover")
def download_rover():
    file_dir = os.path.join(app.static_folder, "projects/ArdiunoRover")
    return send_from_directory(
        file_dir,
        "Rover.ino",
        as_attachment=True
    )


# -------------------------
# OPTIONAL: direct static fallback test route
# -------------------------
@app.route("/test/rover")
def test_rover():
    file_dir = os.path.join(app.static_folder, "projects/ArdiunoRover")
    return send_from_directory(file_dir, "Rover.ino")


# -------------------------
# RUN SERVER
# -------------------------
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )

print(app.url_map)