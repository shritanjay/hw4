"""Tools the agent can call, plus the read-only data access they use.

Sections:
  1. Catalogue + inventory access (campus_customs.db): categories, departments, product cards/detail
  2. Customer memory: save / reload each logged-in shopper's chat in chat_messages
  3. Agent tools: search_products, get_product_info, check_stock, get_viewed_product,
     get_customer_info, get_past_recommendations (all read-only on the database)

The agent never guesses price or stock; every answer comes from these queries.
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from pydantic_ai import RunContext, Tool
from pydantic_ai.tools import ToolDefinition

from models import (
    ChatMessage,
    CustomerProfile,
    NotFound,
    PageContext,
    PastRecommendation,
    ProductCard,
    ProductDetail,
    ProductInfo,
    ProductMatch,
    SearchResult,
    SizeStatus,
    SizeStock,
    StockCheck,
    User,
    ViewedProduct,
)

# =============================================================================
# 1. Catalogue + inventory access
# =============================================================================

HW4 = Path(__file__).resolve().parents[1]
DATA_DIR = HW4 / "data"
DB_PATH = DATA_DIR / "campus_customs.db"

SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]

# garment_type is free text ("t-shirt", "short-sleeve T-shirt", ...); map it to a few shop categories.
CATEGORY_RULES = [
    ("quarter-zip", "Quarter-zips"),
    ("jacket", "Jackets"),
    ("full-zip", "Jackets"),
    ("hood", "Hoodies"),
    ("crewneck", "Crewnecks"),
    ("t-shirt", "Tees"),
    ("long-sleeve", "Long sleeves"),
    ("sweatshirt", "Crewnecks"),
]


# Shop order: cheapest everyday items first (tees $32) up to outerwear ($98).
CATEGORY_ORDER = ["Tees", "Long sleeves", "Crewnecks", "Hoodies", "Quarter-zips", "Jackets"]

# Departments group the 102 products the way people shop: who it's for / what it represents.
# First matching rule wins; anything else is "Classic Yale".
DEPARTMENTS = [
    ("Grad & Professional Schools", ["school of", "law school", "divinity school", "forest school"]),
    ("Residential Colleges", ["benjamin franklin", "berkeley", "branford", "davenport", "grace hopper",
                              "jonathan edwards", "morse", "pierson", "saybrook", "silliman", "timothy dwight",
                              "trumbull", "ezra stiles", "pauli murray"]),
    ("Family", ["mom", "dad", "grandma", "grandpa", "aunt", "uncle", "brother", "sister", "cousin"]),
    ("Sports & Game Day", ["baseball", "basketball", "football", "hockey", "soccer", "tennis", "golf", "diving",
                           "swimming", "volleyball", "lacrosse", "fencing", "sailing", "squash", "track",
                           "crew left chest", "harvard", "yale bowl", "gameday"]),
]
DEPARTMENT_ORDER = ["Classic Yale", "Sports & Game Day", "Residential Colleges", "Grad & Professional Schools", "Family"]


def department_for(name: str) -> str:
    n = name.lower()
    for dept, keys in DEPARTMENTS:
        # whole words only, so "Brooks Brothers" isn't "Family" (brother)
        if any(re.search(rf"\b{re.escape(k)}\b", n) for k in keys):
            return dept
    return "Classic Yale"


def shop_order(p) -> tuple:
    """Sort key: category (tees first), then price, then name."""
    cat = CATEGORY_ORDER.index(p.category) if p.category in CATEGORY_ORDER else len(CATEGORY_ORDER)
    return (cat, p.price, p.name)


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def category_for(garment_type: str) -> str:
    g = garment_type.lower()
    return next((label for key, label in CATEGORY_RULES if key in g), "Other")


def short_description(text: str, limit: int = 110) -> str:
    first = text.split(". ")[0].rstrip(".") + "."
    return first if len(first) <= limit else first[: limit - 1].rsplit(" ", 1)[0] + "…"


def image_url(path: str) -> str:
    return f"/images/{path.removeprefix('products/')}"


def _summary(row: sqlite3.Row, total_stock: int, sizes_in_stock: list[str] | None = None) -> ProductCard:
    return ProductCard(
        product_id=row["product_id"],
        name=row["name"],
        category=category_for(row["garment_type"]),
        department=department_for(row["name"]),
        garment_type=row["garment_type"],
        price=row["price"],
        short_description=short_description(row["description"]),
        image_url=image_url(row["image_file_path"]),
        in_stock=total_stock > 0,
        sizes_in_stock=sizes_in_stock or [],
    )


def list_products() -> list[ProductCard]:
    with connect() as conn:
        rows = conn.execute(
            """SELECT c.*, COALESCE(SUM(i.quantity), 0) AS total_stock,
                      GROUP_CONCAT(CASE WHEN i.quantity > 0 THEN i.size END) AS sizes
               FROM catalogue c LEFT JOIN inventory i ON i.product_id = c.product_id
               GROUP BY c.product_id ORDER BY c.name"""
        ).fetchall()
    order = {s: i for i, s in enumerate(SIZE_ORDER)}
    cards = [
        _summary(r, r["total_stock"], sorted((r["sizes"] or "").split(",") if r["sizes"] else [], key=lambda s: order.get(s, 99)))
        for r in rows
    ]
    return sorted(cards, key=shop_order)


def get_product(product_id: str) -> ProductDetail | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM catalogue WHERE product_id = ?", (product_id,)).fetchone()
        if row is None:
            return None
        stock = conn.execute("SELECT size, quantity FROM inventory WHERE product_id = ?", (product_id,)).fetchall()
    sizes = sorted(
        (SizeStock(size=s["size"], quantity=s["quantity"], in_stock=s["quantity"] > 0) for s in stock),
        key=lambda s: SIZE_ORDER.index(s.size) if s.size in SIZE_ORDER else 99,
    )
    total = sum(s.quantity for s in sizes)
    return ProductDetail(
        **_summary(row, total, [s.size for s in sizes if s.in_stock]).model_dump(),
        description=row["description"],
        colors=json.loads(row["colors"]),
        search_tags=json.loads(row["search_tags"]),
        sizes=sizes,
        total_stock=total,
    )


# =============================================================================
# 2. Customer memory (chat_messages)
# =============================================================================

MAX_STORED_SHOWN = 50  # messages returned to the chat widget on login


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
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
    by_id = {p.product_id: p for p in list_products()}
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
    by_id = {p.product_id: p for p in list_products()}
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


# =============================================================================
# 3. Agent tools
# =============================================================================

MAX_RESULTS = 6          # detailed results sent to the agent
MAX_PAGE_RESULTS = 30    # ids the page grid can show (largest category is 28)
STOPWORDS = {
    "a", "an", "the", "and", "or", "for", "with", "in", "of", "to", "do", "you", "have", "any", "some",
    "i", "me", "my", "is", "are", "it", "this", "that", "show", "want", "need", "looking", "something",
    "yale", "campus", "customs", "please", "under", "over", "than",
}


@dataclass
class ShopDeps:
    """Per-request context the agent and its tools can read (PydanticAI dependency injection).

    Built fresh for every chat turn in agent.run_chat():
      user          the logged-in shopper (name, email, member since) or None
      page          where they are on the site: path, product_id on an item page, chat results title
      saved_count   how many of their messages are stored in chat_messages
      searched_ids  filled by search_products; used to validate page_results
    """

    user: User | None = None
    page: PageContext = field(default_factory=PageContext)
    saved_count: int = 0
    searched_ids: set[str] = field(default_factory=set)


# Shoppers say "pink" or "grey"; the catalogue says "dusty coral" or "heather charcoal gray".
COLOR_FAMILIES = {
    "pink": ["pink", "coral", "rose", "salmon", "blush"],
    "red": ["red", "crimson", "maroon", "coral"],
    "gray": ["gray", "grey", "charcoal", "heather"],
    "grey": ["gray", "grey", "charcoal", "heather"],
    "blue": ["blue", "navy", "royal"],
    "white": ["white", "ivory", "cream"],
    "yellow": ["yellow", "gold"],
    "gold": ["gold", "yellow"],
    "black": ["black", "charcoal"],
}


def _color_hits(wanted: str, colors: list[str]) -> list[str]:
    """Catalogue colors that belong to the shopper's color word (exact word first, then its family)."""
    w = wanted.lower().strip()
    family = COLOR_FAMILIES.get(w, [w])
    return [c for c in colors if any(f in c.lower() for f in family)]


def _terms(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)?", text.lower())
    return [w.rstrip("s") if len(w) > 3 else w for w in words if w not in STOPWORDS]


def _rows() -> list[dict]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM catalogue").fetchall()
        stock = conn.execute("SELECT product_id, size, quantity FROM inventory").fetchall()
    by_id: dict[str, dict[str, int]] = {}
    for s in stock:
        by_id.setdefault(s["product_id"], {})[s["size"]] = s["quantity"]
    out = []
    for r in rows:
        d = dict(r)
        d["colors"] = json.loads(d["colors"])
        d["search_tags"] = json.loads(d["search_tags"])
        d["stock"] = by_id.get(d["product_id"], {})
        d["category"] = category_for(d["garment_type"])
        d["department"] = department_for(d["name"])
        out.append(d)
    return out


def _to_match(d: dict) -> ProductMatch:
    ordered = sorted(d["stock"].items(), key=lambda kv: SIZE_ORDER.index(kv[0]) if kv[0] in SIZE_ORDER else 99)
    return ProductMatch(
        product_id=d["product_id"],
        name=d["name"],
        category=d["category"],
        price=d["price"],
        colors=d["colors"],
        short_description=short_description(d["description"]),
        sizes_in_stock=[s for s, q in ordered if q > 0],
        sold_out_sizes=[s for s, q in ordered if q == 0],
    )


def search_products(
    ctx: RunContext[ShopDeps],
    query: str,
    category: str | None = None,
    color: str | None = None,
    max_price: float | None = None,
    size: str | None = None,
    department: str | None = None,
) -> SearchResult:
    """Search the Campus Customs catalogue. Returns up to 6 best matches with price and which sizes are in stock.

    Args:
        query: what the shopper wants in a few keywords, e.g. "navy hoodie", "harvard game", "mom gift", "hockey".
        category: optional filter, one of Hoodies, Crewnecks, Quarter-zips, Tees, Jackets, Long sleeves.
        color: optional color the item must include, e.g. "navy", "gray", "white".
        max_price: optional highest price in USD.
        department: optional, one of Classic Yale, Sports & Game Day, Residential Colleges,
            Grad & Professional Schools (incl. School of Management, Law, Medicine…), Family.
        size: optional size the shopper wants (XS, S, M, L, XL, XXL). Items in stock in that size are
            listed first, but items sold out in it are still returned (check sold_out_sizes) so you can
            tell the shopper honestly rather than claim we don't carry it.
    """
    terms = _terms(query)
    # A color word in the query ("pink stuff") acts like the color filter, family-aware.
    query_colors = [t for t in terms if t in COLOR_FAMILIES]
    if not color and query_colors:
        color = query_colors[0]
    if color:
        terms = [t for t in terms if t != color.lower()]
    shades: set[str] = set()
    results = []
    for d in _rows():
        if category and d["category"].lower() != category.lower():
            continue
        if department and department.lower().split()[0] not in d["department"].lower():
            continue
        if color:
            hits = _color_hits(color, d["colors"])
            if not hits:
                continue
            shades.update(hits)
        if max_price is not None and d["price"] > max_price:
            continue
        name = d["name"].lower()
        tags = " ".join(d["search_tags"]).lower()
        body = f"{d['garment_type']} {d['description']} {' '.join(d['colors'])}".lower()
        score = sum(3 * (t in name) + 2 * (t in tags) + (t in body) for t in terms)
        if terms and score == 0:
            continue
        has_size = not size or d["stock"].get(size.upper(), 0) > 0
        results.append((has_size, score, d))
    cat_rank = {c: i for i, c in enumerate(CATEGORY_ORDER)}
    results.sort(key=lambda x: (-x[1], not x[0], cat_rank.get(x[2]["category"], 99), x[2]["price"], x[2]["name"]))
    used = {k: v for k, v in {"category": category, "department": department, "color": color,
                              "max_price": max_price, "size": size}.items()
            if v not in (None, "")}
    total = len(results)
    if total == 0:
        note = "No matches. Try fewer or simpler keywords, or drop a filter, before telling the shopper we don't carry it."
    elif total > MAX_RESULTS:
        note = f"Showing the best {MAX_RESULTS} of {total} matches."
    else:
        note = ""
    if color and shades:
        exact = {sh for sh in shades if color.lower() in sh.lower()}
        if not exact:
            note = (f"No item is listed as '{color}'. Closest shades matched: {', '.join(sorted(shades))}. "
                    f"Tell the shopper honestly that these are the closest to {color}. " + note).strip()
    all_ids = [d["product_id"] for _, _, d in results[:MAX_PAGE_RESULTS]]
    if ctx.deps is not None:
        ctx.deps.searched_ids.update(all_ids)
    return SearchResult(
        query=query, filters=used, total_matches=total,
        results=[_to_match(d) for _, _, d in results[:MAX_RESULTS]], all_match_ids=all_ids, note=note,
    )


def _resolve(product: str) -> tuple[str | None, list[str]]:
    """Exact product_id, else best name match. Returns (product_id or None, close candidates' names)."""
    if get_product(product) is not None:
        return product, []
    terms = _terms(product)
    if not terms:
        return None, []
    scored = []
    for d in _rows():
        name_terms = set(_terms(d["name"]))
        hits = sum(t in name_terms or t in d["name"].lower() for t in terms)
        if hits:
            scored.append((hits / max(len(terms), len(name_terms)), hits, d))
    scored.sort(key=lambda x: (-x[0], -x[1], x[2]["name"]))
    if not scored:
        return None, []
    best = scored[0]
    # Confident if it covers every word the shopper typed and clearly beats the runner-up.
    if best[1] == len(terms) and (len(scored) == 1 or best[0] > scored[1][0]):
        return best[2]["product_id"], []
    return None, [d["name"] for _, _, d in scored[:4]]


def _unknown_product(product_id: str, candidates: list[str] | None = None) -> NotFound:
    if candidates:
        return NotFound(
            error="ambiguous_product",
            message=f"'{product_id}' matches several products: {', '.join(candidates)}.",
            hint="Call again with the exact name, or ask the shopper which one they mean.",
        )
    return NotFound(
        error="unknown_product",
        message=f"No product with id '{product_id}'.",
        hint="Call search_products to find the exact product_id. Don't guess details.",
    )


LOW_STOCK = 3


def _status(quantity: int) -> str:
    if quantity <= 0:
        return "sold out"
    if quantity <= LOW_STOCK:
        return f"only {quantity} left"
    return f"{quantity} in stock"


def get_product_info(ctx: RunContext[ShopDeps], product: str) -> ProductInfo | NotFound:
    """Description, price, colors, and which sizes are in stock / sold out for one product (from the catalogue).

    Use it when the shopper asks what an item looks like, what it costs, or what colors it has.
    Note: `colors` lists every color on the item, garment AND graphic/lettering. The description says which
    is the garment color. Each product is one colorway, not a choice of colors.

    Args:
        product: the product_id, or the product's name as the shopper said it (e.g. "Yale Mom Hoodie").
    """
    product_id, candidates = _resolve(product)
    item = get_product(product_id) if product_id else None
    if item is None:
        return _unknown_product(product, candidates)
    return ProductInfo(
        product_id=item.product_id, name=item.name, category=item.category, garment_type=item.garment_type,
        description=item.description, price=item.price, colors=item.colors,
        in_stock_sizes=[s.size for s in item.sizes if s.in_stock],
        sold_out_sizes=[s.size for s in item.sizes if not s.in_stock],
    )


def check_stock(ctx: RunContext[ShopDeps], product: str, size: str | None = None) -> StockCheck | NotFound:
    """How many units are in stock, per size, from the inventory table.

    Always call this before saying whether a size is available or how many are left.
    Quote the `status` labels: "sold out", "only N left", "N in stock".

    Args:
        product: the product_id, or the product's name as the shopper said it (e.g. "Yale Grandpa Crewneck").
            Accepting a name saves a search_products call for named items.
        size: the size the shopper asked about (XS, S, M, L, XL, XXL). Leave empty for every size.
    """
    product_id, candidates = _resolve(product)
    item = get_product(product_id) if product_id else None
    if item is None:
        return _unknown_product(product, candidates)
    sizes = [SizeStatus(size=s.size, quantity=s.quantity, status=_status(s.quantity)) for s in item.sizes]
    in_stock = [s.size for s in sizes if s.quantity > 0]
    sold_out = [s.size for s in sizes if s.quantity <= 0]
    available = ", ".join(f"{s.size} ({s.quantity})" for s in sizes if s.quantity > 0) or "none"

    requested, requested_ok, lead = None, None, ""
    if size:
        requested = size.strip().upper()
        match = next((s for s in sizes if s.size == requested), None)
        if match is None:
            lead = f"{item.name} doesn't come in size {requested}. "
        else:
            requested_ok = match.quantity > 0
            lead = f"{requested}: {match.status.upper() if not requested_ok else match.status}. "
    summary = lead + f"In stock: {available}." + (f" Sold out: {', '.join(sold_out)}." if sold_out else "")

    return StockCheck(
        product_id=item.product_id, name=item.name, price=item.price, sizes=sizes,
        in_stock_sizes=in_stock, sold_out_sizes=sold_out, total_stock=item.total_stock,
        requested_size=requested, requested_size_in_stock=requested_ok, summary=summary,
    )


# ---- Customer + page context tools (read from ctx.deps) -------------------------


def get_customer_info(ctx: RunContext[ShopDeps]) -> CustomerProfile:
    """The shopper's own account details: first/last name, email, member-since date, saved-message count.

    Only for questions about their account ("who am I?", "what email do you have for me?"). You already
    know their name from the instructions, so don't call this to greet them or for store/policy questions.
    Returns logged_in=false for guests.
    """
    u = ctx.deps.user
    if u is None:
        return CustomerProfile(logged_in=False)
    return CustomerProfile(
        logged_in=True, first_name=u.first_name, last_name=u.last_name, email=u.email,
        member_since=(u.created_at or "")[:10] or None, saved_messages=ctx.deps.saved_count,
    )


def get_viewed_product(ctx: RunContext[ShopDeps]) -> ViewedProduct | NotFound:
    """The product page the shopper is looking at right now: name, price, description, colors, sizes.

    Call this when they say "this", "this one", "it", or "do you have this in pink?" and they're on a product page.
    """
    pid = ctx.deps.page.product_id
    if not pid:
        return NotFound(error="no_product_page", message=f"The shopper is on {ctx.deps.page.path}, not a product page.",
                        hint="Ask which item they mean, or use search_products.")
    item = get_product(pid)
    if item is None:
        return _unknown_product(pid)
    return ViewedProduct(
        product_id=item.product_id, name=item.name, price=item.price, description=item.description,
        colors=item.colors, in_stock_sizes=[s.size for s in item.sizes if s.in_stock],
        sold_out_sizes=[s.size for s in item.sizes if not s.in_stock],
    )


def get_past_recommendations(ctx: RunContext[ShopDeps], limit: int = 8) -> list[PastRecommendation] | NotFound:
    """Products this shopper was shown in earlier chats (saved in the database), newest first.

    Use for "what did you recommend last time?" or "that hoodie you showed me before". Logged-in shoppers only.

    Args:
        limit: how many to return (max 20).
    """
    if ctx.deps.user is None:
        return NotFound(error="not_logged_in", message="Chat history is only saved for logged-in shoppers.",
                        hint="Suggest logging in to keep their chat history.")
    return [PastRecommendation(**r) for r in past_recommendations(ctx.deps.user.id, min(limit, 20))]


# ---- Which tools the model is offered each turn ----------------------------------
# Hiding tools that can't help (account tools for guests, get_viewed_product off product pages) avoids
# pointless calls and sends fewer tool schemas (tokens) on every model request.


async def _only_logged_in(ctx: RunContext[ShopDeps], tool_def: ToolDefinition) -> ToolDefinition | None:
    return tool_def if ctx.deps.user is not None else None


async def _only_on_product_page(ctx: RunContext[ShopDeps], tool_def: ToolDefinition) -> ToolDefinition | None:
    return tool_def if ctx.deps.page.product_id else None


TOOLS = [
    Tool(search_products),
    Tool(get_product_info),
    Tool(check_stock),
    Tool(get_customer_info, prepare=_only_logged_in),
    Tool(get_past_recommendations, prepare=_only_logged_in),
    Tool(get_viewed_product, prepare=_only_on_product_page),
]
