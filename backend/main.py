"""Campus Customs API.

Run from HW4/backend:
  .venv/bin/uvicorn main:app --reload --port 8000

Sections:
  1. Accounts: password hashing (PBKDF2), sign-up, login, lockout, cookie sessions
  2. Routes: health, products + images, auth, chat history, and /api/chat -> the PydanticAI shop agent (agent.py)
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import re
import secrets
import sqlite3
import time

from fastapi import Cookie, FastAPI, HTTPException, Response
from fastapi.staticfiles import StaticFiles

import tools
from agent import run_chat
from models import ChatHistory, ChatReply, ChatRequest, LoginRequest, ProductDetail, ProductCard, SignupRequest, User

# =============================================================================
# 1. Accounts
# =============================================================================

PBKDF2_ITERATIONS = 600_000  # OWASP 2023 recommendation for PBKDF2-HMAC-SHA256
# The seed database was hashed with 120k iterations. The hash format has no iteration field, so
# login tries the current setting first, then the legacy one, and upgrades the hash on success.
LEGACY_ITERATIONS = 120_000
SALT_BYTES = 16              # unique random salt per user
MIN_PASSWORD_LEN = 8
MAX_PASSWORD_LEN = 128       # caps hashing cost so huge inputs can't tie up the server
MAX_FAILED_LOGINS = 5
LOCKOUT_SECONDS = 15 * 60
SESSION_COOKIE = "cc_session"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# token -> user id. In memory, so everyone is logged out when the server restarts (fine for a demo).
_sessions: dict[str, int] = {}
# email -> timestamps of recent failed logins, to slow down password guessing.
_failed: dict[str, list[float]] = {}


class AuthError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def hash_password(password: str, salt: str | None = None, iterations: int = PBKDF2_ITERATIONS) -> str:
    salt = salt or secrets.token_hex(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations).hex()
    return f"pbkdf2_sha256${salt}${digest}"


def check_password(password: str, stored: str) -> int | None:
    """Return the iteration count that matched, or None if the password is wrong."""
    try:
        algo, salt, _ = stored.split("$")
    except ValueError:
        return None
    if algo != "pbkdf2_sha256":
        return None
    for iterations in (PBKDF2_ITERATIONS, LEGACY_ITERATIONS):
        if hmac.compare_digest(hash_password(password, salt, iterations), stored):
            return iterations
    return None


def verify_password(password: str, stored: str) -> bool:
    return check_password(password, stored) is not None


_DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


def _write_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(tools.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _to_user(row: sqlite3.Row) -> User:
    first = row["first_name"] or row["name"].split(" ")[0]
    last = row["last_name"] or " ".join(row["name"].split(" ")[1:])
    return User(id=row["id"], first_name=first, last_name=last, name=row["name"], email=row["email"],
                created_at=row["created_at"])


def create_account(first_name: str, last_name: str, email: str, password: str, confirm_password: str) -> User:
    first_name, last_name, email = first_name.strip(), last_name.strip(), email.strip().lower()
    if not first_name or not last_name:
        raise AuthError(400, "Please enter your first and last name.")
    if not EMAIL_RE.match(email):
        raise AuthError(400, "Please enter a valid email address.")
    if not MIN_PASSWORD_LEN <= len(password) <= MAX_PASSWORD_LEN:
        raise AuthError(400, f"Password must be {MIN_PASSWORD_LEN}–{MAX_PASSWORD_LEN} characters.")
    if password != confirm_password:
        raise AuthError(400, "Passwords don't match.")
    with _write_conn() as conn:
        if conn.execute("SELECT 1 FROM users WHERE lower(email) = ?", (email,)).fetchone():
            raise AuthError(409, "An account with that email already exists. Try logging in.")
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash, first_name, last_name) VALUES (?, ?, ?, ?, ?)",
            (f"{first_name} {last_name}", email, hash_password(password), first_name, last_name),
        )
        row = conn.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
    return _to_user(row)


def check_login(email: str, password: str) -> User:
    email = email.strip().lower()
    now = time.time()
    recent = [t for t in _failed.get(email, []) if now - t < LOCKOUT_SECONDS]
    if len(recent) >= MAX_FAILED_LOGINS:
        raise AuthError(429, "Too many failed attempts. Please wait 15 minutes and try again.")
    with _write_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE lower(email) = ?", (email,)).fetchone()
    # Hash even when the email is unknown so response time doesn't reveal which emails exist.
    stored = row["password_hash"] if row is not None else _DUMMY_HASH
    matched = check_password(password, stored) if len(password) <= MAX_PASSWORD_LEN else None
    if matched is None or row is None:
        _failed[email] = [*recent, now]
        # Same message either way so the form doesn't reveal which emails have accounts.
        raise AuthError(401, "Incorrect email or password.")
    _failed.pop(email, None)
    if matched != PBKDF2_ITERATIONS:
        # Seed-era hash: re-store it with the stronger setting now that we know the password.
        with _write_conn() as conn:
            conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(password), row["id"]))
    return _to_user(row)


def start_session(user: User) -> str:
    token = secrets.token_urlsafe(32)
    _sessions[token] = user.id
    return token


def end_session(token: str | None) -> None:
    if token:
        _sessions.pop(token, None)


def user_for_session(token: str | None) -> User | None:
    user_id = _sessions.get(token or "")
    if user_id is None:
        return None
    with _write_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return _to_user(row) if row else None


# =============================================================================
# 2. API routes
# =============================================================================

log = logging.getLogger("campus_customs")
app = FastAPI(title="Campus Customs API")

# Product photos live in HW4/data/products (gitignored); served at /images/<file>.jpg
# check_dir=False: the server still starts without the data pack, and /api/health explains what's missing.
app.mount("/images", StaticFiles(directory=tools.DATA_DIR / "products", check_dir=False), name="images")


@app.get("/api/health")
def health() -> dict:
    missing = [str(p.relative_to(tools.DATA_DIR.parent)) for p in (tools.DB_PATH, tools.DATA_DIR / "products") if not p.exists()]
    if missing:
        return {"ok": False, "products": 0, "missing": missing,
                "hint": "Place the data pack at hw4/data/ (campus_customs.db + products/). See README."}
    return {"ok": True, "products": len(tools.list_products())}


@app.get("/api/products", response_model=list[ProductCard])
def products() -> list[ProductCard]:
    return tools.list_products()


@app.get("/api/products/{product_id}", response_model=ProductDetail)
def product(product_id: str) -> ProductDetail:
    item = tools.get_product(product_id)
    if item is None:
        raise HTTPException(404, "Product not found")
    return item



# ---- Accounts -------------------------------------------------------------

def _set_session(response: Response, user: User) -> None:
    response.set_cookie(
        SESSION_COOKIE, start_session(user),
        httponly=True, samesite="lax", max_age=60 * 60 * 24 * 7,
    )


@app.post("/api/auth/signup", response_model=User, status_code=201)
def signup(body: SignupRequest, response: Response) -> User:
    try:
        user = create_account(body.first_name, body.last_name, body.email, body.password, body.confirm_password)
    except AuthError as e:
        raise HTTPException(e.status, e.message)
    _set_session(response, user)
    return user


@app.post("/api/auth/login", response_model=User)
def login(body: LoginRequest, response: Response) -> User:
    try:
        user = check_login(body.email, body.password)
    except AuthError as e:
        raise HTTPException(e.status, e.message)
    _set_session(response, user)
    return user


@app.post("/api/auth/logout", status_code=204)
def logout(response: Response, cc_session: str | None = Cookie(default=None)) -> None:
    end_session(cc_session)
    response.delete_cookie(SESSION_COOKIE)


@app.get("/api/auth/me", response_model=User | None)
def me(cc_session: str | None = Cookie(default=None)) -> User | None:
    return user_for_session(cc_session)


@app.get("/api/chat/history", response_model=ChatHistory)
def chat_history(cc_session: str | None = Cookie(default=None)) -> ChatHistory:
    """Saved chat for the logged-in shopper (reloaded into the widget on login / page load)."""
    user = user_for_session(cc_session)
    if user is None:
        return ChatHistory(logged_in=False)
    return ChatHistory(logged_in=True, messages=tools.load_history(user.id))


@app.delete("/api/chat/history", status_code=204)
def clear_chat_history(cc_session: str | None = Cookie(default=None)) -> None:
    user = user_for_session(cc_session)
    if user is None:
        raise HTTPException(401, "Log in to manage your chat history.")
    tools.clear_history(user.id)


@app.post("/api/chat", response_model=ChatReply)
async def chat(body: ChatRequest, cc_session: str | None = Cookie(default=None)) -> ChatReply:
    """Website chat -> PydanticAI shop agent (agent.py) -> reply + product cards."""
    message = body.message.strip()  # length limits are enforced by ChatRequest
    if not message:
        raise HTTPException(400, "Message is empty.")
    user = user_for_session(cc_session)
    try:
        return await run_chat(message, body.history, user, body.page)
    except Exception as exc:  # model/network errors shouldn't crash the widget
        if "content_filter" in str(exc):
            # The model provider refused this message. Answer politely instead of "having trouble".
            log.warning("chat blocked by provider content filter")
            return ChatReply(
                reply="Sorry, I can't help with that one here. I'm happy to help you find Yale gear, check sizes "
                "and stock, or answer questions about the shop.",
                products=[],
            )
        log.exception("chat failed")
        return ChatReply(
            reply="Sorry, I'm having trouble right now. Please try again in a moment, "
            "or email orderdept@campuscustoms.com.",
            products=[],
        )
