"""Customer memory: save and reload each logged-in shopper's chat in the chat_messages table.

chat_messages(id, user_id, role, content, products_json, created_at)
- role is "user" or "assistant"
- products_json (assistant rows) is a JSON list of the product cards shown with that reply.
  Older seed rows hold full product objects; only product_id is relied on when reading back.
"""

from __future__ import annotations

import json
import sqlite3

import db
from models import ChatMessage, ProductCard

MAX_STORED_SHOWN = 50  # messages returned to the chat widget on login


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(db.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def save_turn(user_id: int, user_text: str, reply: str, products: list[ProductCard]) -> None:
    """Store one question + answer for this user."""
    with _conn() as conn:
        conn.execute(
            "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, 'user', ?, NULL)",
            (user_id, user_text),
        )
        conn.execute(
            "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, 'assistant', ?, ?)",
            (user_id, reply, json.dumps([p.model_dump() for p in products])),
        )


def _cards(products_json: str | None, by_id: dict[str, ProductCard]) -> list[ProductCard]:
    """Rebuild cards from the current catalogue (fresh prices/stock), skipping ids that no longer exist."""
    if not products_json:
        return []
    try:
        items = json.loads(products_json)
    except json.JSONDecodeError:
        return []
    ids = [i.get("product_id") for i in items if isinstance(i, dict)]
    return [by_id[i] for i in ids if i in by_id]


def load_history(user_id: int, limit: int = MAX_STORED_SHOWN) -> list[ChatMessage]:
    """The user's most recent messages, oldest first, with product cards rebuilt from the DB."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT role, content, products_json, created_at FROM chat_messages "
            "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    by_id = {p.product_id: p for p in db.list_products()}
    return [
        ChatMessage(role=r["role"], content=r["content"], products=_cards(r["products_json"], by_id),
                    created_at=r["created_at"])
        for r in reversed(rows)
        if r["role"] in ("user", "assistant")
    ]


def past_recommendations(user_id: int, limit: int = 10) -> list[dict]:
    """Products this user was shown in earlier chats, newest first, with when and in reply to what."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, products_json, created_at FROM chat_messages "
            "WHERE user_id = ? AND role = 'assistant' AND products_json IS NOT NULL ORDER BY id DESC",
            (user_id,),
        ).fetchall()
        asked = {
            r["id"]: r["content"]
            for r in conn.execute("SELECT id, content FROM chat_messages WHERE user_id = ? AND role = 'user'", (user_id,))
        }
    by_id = {p.product_id: p for p in db.list_products()}
    out, seen = [], set()
    for r in rows:
        question = asked.get(r["id"] - 1, "")
        for card in _cards(r["products_json"], by_id):
            if card.product_id not in seen:
                seen.add(card.product_id)
                out.append({"product_id": card.product_id, "name": card.name, "when": r["created_at"],
                            "asked": question[:120]})
        if len(out) >= limit:
            break
    return out[:limit]


def count_messages(user_id: int) -> int:
    with _conn() as conn:
        return conn.execute("SELECT COUNT(*) FROM chat_messages WHERE user_id = ?", (user_id,)).fetchone()[0]


def clear_history(user_id: int) -> int:
    with _conn() as conn:
        return conn.execute("DELETE FROM chat_messages WHERE user_id = ?", (user_id,)).rowcount
