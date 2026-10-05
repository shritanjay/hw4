"""Pydantic / PydanticAI structured types for the Campus Customs backend.

Sections:
  1. Products   - product cards and the single-item page
  2. Chat       - what the website sends to /api/chat and gets back
  3. Accounts   - sign-up, login, and the public User
  4. Agent      - what tools hand the agent, and the agent's structured output
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# ---- 1. Products ------------------------------------------------------------


class SizeStock(BaseModel):
    size: str
    quantity: int
    in_stock: bool


class ProductCard(BaseModel):
    """A product card: used by the Products grid and shown next to chat replies."""

    product_id: str
    name: str
    category: str
    department: str  # Classic Yale, Sports & Game Day, Residential Colleges, Grad & Professional Schools, Family
    garment_type: str
    price: float
    short_description: str
    image_url: str
    in_stock: bool
    sizes_in_stock: list[str] = Field(default_factory=list)  # for "in my size" filtering on the Products page


class ProductDetail(ProductCard):
    """Everything the single-item page shows."""

    description: str
    colors: list[str]
    search_tags: list[str]
    sizes: list[SizeStock]
    total_stock: int


# ---- 2. Chat ----------------------------------------------------------------

MAX_MESSAGE_CHARS = 1000
MAX_HISTORY_SENT = 20


class ChatMessage(BaseModel):
    """One message in the conversation (sent as context, or reloaded from chat_messages)."""

    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)
    products: list[ProductCard] = Field(default_factory=list)  # cards shown with an assistant message
    created_at: str | None = None


class PageContext(BaseModel):
    """Where the shopper is on the site when they send a message."""

    path: str = Field(default="/", max_length=200)          # e.g. "/products/yale-mom-hoodie"
    product_id: str | None = Field(default=None, max_length=120)  # set on a single-item page
    results_title: str | None = Field(default=None, max_length=120)  # "From your chat" grid, if showing


class ChatRequest(BaseModel):
    """Body of POST /api/chat from the chat widget."""

    message: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)
    history: list[ChatMessage] = Field(default_factory=list, max_length=MAX_HISTORY_SENT)  # used when logged out
    page: PageContext = Field(default_factory=PageContext)


class PageResults(BaseModel):
    """Product cards the website shows on the page (not just in the chat panel) after a search."""

    title: str                    # e.g. "T-shirts", "Navy hoodies under $70"
    query: str                    # what the shopper asked, shown as context
    total: int                    # number of cards
    products: list[ProductCard]   # built from the database, never from model text


class ChatReply(BaseModel):
    """Response of POST /api/chat.

    - reply:    the agent's text for the chat bubble
    - products: up to 6 items the reply mentions (mini cards inside the chat)
    - page:     when the shopper searched for a type of item, the full set of matches for the page grid
    """

    reply: str
    products: list[ProductCard] = Field(default_factory=list)
    page: PageResults | None = None
    redacted: list[str] = Field(default_factory=list)  # kinds of sensitive data removed from the message
    user_message: str | None = None  # the redacted message, so the widget can replace what was shown


# ---- 3. Accounts ------------------------------------------------------------


class SignupRequest(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str
    confirm_password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class User(BaseModel):
    """Public user info. Never includes the password hash."""

    id: int
    first_name: str
    last_name: str
    name: str
    email: str
    created_at: str | None = None


class ChatHistory(BaseModel):
    """GET /api/chat/history: the logged-in shopper's saved chat."""

    logged_in: bool
    messages: list[ChatMessage] = Field(default_factory=list)


# ---- 4. Agent ---------------------------------------------------------------


class CustomerProfile(BaseModel):
    """What get_customer_info tells the agent about the logged-in shopper."""

    logged_in: bool
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    member_since: str | None = None
    saved_messages: int = 0


class ViewedProduct(BaseModel):
    """The product page the shopper is looking at right now (from PageContext)."""

    product_id: str
    name: str
    price: float
    description: str
    colors: list[str]
    in_stock_sizes: list[str]
    sold_out_sizes: list[str]


class PastRecommendation(BaseModel):
    product_id: str
    name: str
    when: str
    asked: str  # the shopper's message that led to it


class ProductMatch(BaseModel):
    """One search hit. Compact on purpose: enough to recommend and quote a price, not a full page."""

    product_id: str
    name: str
    category: str
    price: float
    colors: list[str]
    short_description: str
    sizes_in_stock: list[str]
    sold_out_sizes: list[str]


class SearchResult(BaseModel):
    """What search_products returns: the hits plus what was searched, so 'no matches' is explicit."""

    query: str
    filters: dict[str, str | float]  # only the filters actually used, e.g. {"color": "navy", "max_price": 70}
    total_matches: int               # before the 6-result cap
    results: list[ProductMatch]      # top 6, with details
    all_match_ids: list[str]         # ids of every match (up to 30), for ShopReply.page_results
    note: str = ""                   # e.g. "No matches. Try fewer keywords." or "Showing 6 of 14."


class NotFound(BaseModel):
    """Returned instead of guessing when a product id or size doesn't exist."""

    error: str  # "unknown_product" | "unknown_size"
    message: str
    hint: str


class SizeStatus(BaseModel):
    """Stock for one size, with a ready-made label so 'sold out' is always stated plainly."""

    size: str
    quantity: int
    status: str  # "sold out" | "only N left" | "N in stock"


class StockCheck(BaseModel):
    """Live stock for one product, straight from the inventory table."""

    product_id: str
    name: str
    price: float
    sizes: list[SizeStatus]
    in_stock_sizes: list[str]
    sold_out_sizes: list[str]
    total_stock: int
    requested_size: str | None = None
    requested_size_in_stock: bool | None = None
    summary: str  # one line the agent can quote, e.g. "XL: sold out. In stock: S (5), M (5) ..."


class ProductInfo(BaseModel):
    """Description and price for one product, plus a stock summary."""

    product_id: str
    name: str
    category: str
    garment_type: str
    description: str
    price: float
    colors: list[str]  # garment + graphic colors of this one colorway (not color options)
    in_stock_sizes: list[str]
    sold_out_sizes: list[str]


class PageResultsRequest(BaseModel):
    """Part of the agent's output: ask the website to show search matches as product cards on the page."""

    title: str = Field(description='Short heading for the page grid, e.g. "T-shirts" or "Navy hoodies under $70".')
    product_ids: list[str] = Field(
        max_length=30,
        description="Exact product_ids to show, best first, copied from search_products all_match_ids.",
    )


class ShopReply(BaseModel):
    """The agent's structured output. product_ids are checked against the catalogue before becoming cards."""

    reply: str = Field(description="Message to the shopper, in the Campus Customs voice. Simple Markdown.")
    product_ids: list[str] = Field(
        default_factory=list,
        max_length=6,
        description="Exact product_id of every product mentioned, most relevant first. Empty if none.",
    )
    page_results: PageResultsRequest | None = Field(
        default=None,
        description="Set when the shopper is browsing a type of item (e.g. 'what t-shirts do you have'), "
        "so the website shows all matches as cards. Null for a single-item, stock, policy, or chit-chat answer.",
    )
