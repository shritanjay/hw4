"""Campus Customs API.

Run from HW4/backend:
  .venv/bin/uvicorn main:app --reload --port 8000

Routes: products + images (db.py), accounts (auth.py), and /api/chat -> the PydanticAI shop agent (agent.py).
"""

from __future__ import annotations

from fastapi import Cookie, FastAPI, HTTPException, Response
from fastapi.staticfiles import StaticFiles

import logging

import auth
import db
import memory
from agent import run_chat
from models import ChatHistory, ChatReply, ChatRequest, LoginRequest, ProductDetail, ProductCard, SignupRequest, User

log = logging.getLogger("campus_customs")
app = FastAPI(title="Campus Customs API")

# Product photos live in HW4/data/products (gitignored); served at /images/<file>.jpg
# check_dir=False: the server still starts without the data pack, and /api/health explains what's missing.
app.mount("/images", StaticFiles(directory=db.DATA_DIR / "products", check_dir=False), name="images")


@app.get("/api/health")
def health() -> dict:
    missing = [str(p.relative_to(db.DATA_DIR.parent)) for p in (db.DB_PATH, db.DATA_DIR / "products") if not p.exists()]
    if missing:
        return {"ok": False, "products": 0, "missing": missing,
                "hint": "Place the data pack at hw4/data/ (campus_customs.db + products/). See README."}
    return {"ok": True, "products": len(db.list_products())}


@app.get("/api/products", response_model=list[ProductCard])
def products() -> list[ProductCard]:
    return db.list_products()


@app.get("/api/products/{product_id}", response_model=ProductDetail)
def product(product_id: str) -> ProductDetail:
    item = db.get_product(product_id)
    if item is None:
        raise HTTPException(404, "Product not found")
    return item



# ---- Accounts -------------------------------------------------------------

def _set_session(response: Response, user: User) -> None:
    response.set_cookie(
        auth.SESSION_COOKIE, auth.start_session(user),
        httponly=True, samesite="lax", max_age=60 * 60 * 24 * 7,
    )


@app.post("/api/auth/signup", response_model=User, status_code=201)
def signup(body: SignupRequest, response: Response) -> User:
    try:
        user = auth.signup(body.first_name, body.last_name, body.email, body.password, body.confirm_password)
    except auth.AuthError as e:
        raise HTTPException(e.status, e.message)
    _set_session(response, user)
    return user


@app.post("/api/auth/login", response_model=User)
def login(body: LoginRequest, response: Response) -> User:
    try:
        user = auth.login(body.email, body.password)
    except auth.AuthError as e:
        raise HTTPException(e.status, e.message)
    _set_session(response, user)
    return user


@app.post("/api/auth/logout", status_code=204)
def logout(response: Response, cc_session: str | None = Cookie(default=None)) -> None:
    auth.end_session(cc_session)
    response.delete_cookie(auth.SESSION_COOKIE)


@app.get("/api/auth/me", response_model=User | None)
def me(cc_session: str | None = Cookie(default=None)) -> User | None:
    return auth.user_for_session(cc_session)


@app.get("/api/chat/history", response_model=ChatHistory)
def chat_history(cc_session: str | None = Cookie(default=None)) -> ChatHistory:
    """Saved chat for the logged-in shopper (reloaded into the widget on login / page load)."""
    user = auth.user_for_session(cc_session)
    if user is None:
        return ChatHistory(logged_in=False)
    return ChatHistory(logged_in=True, messages=memory.load_history(user.id))


@app.delete("/api/chat/history", status_code=204)
def clear_chat_history(cc_session: str | None = Cookie(default=None)) -> None:
    user = auth.user_for_session(cc_session)
    if user is None:
        raise HTTPException(401, "Log in to manage your chat history.")
    memory.clear_history(user.id)


@app.post("/api/chat", response_model=ChatReply)
async def chat(body: ChatRequest, cc_session: str | None = Cookie(default=None)) -> ChatReply:
    """Website chat -> PydanticAI shop agent (agent.py) -> reply + product cards."""
    message = body.message.strip()  # length limits are enforced by ChatRequest
    if not message:
        raise HTTPException(400, "Message is empty.")
    user = auth.user_for_session(cc_session)
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
