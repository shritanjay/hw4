"""Read-only catalogue + inventory access for campus_customs.db."""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

from models import ProductDetail, ProductCard, SizeStock

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
