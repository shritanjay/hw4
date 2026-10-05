# campus_customs.db — field guide

## `catalogue` — one row per product (102 rows)
| Field | Type | What it is |
|---|---|---|
| `product_id` | TEXT, PK | URL-style slug that uniquely identifies the product, e.g. `basic-hoodie-big-yale`. Also matches the image file name. |
| `name` | TEXT | Display name shown to shoppers, e.g. "Basic Hoodie Big Yale". |
| `garment_type` | TEXT | Kind of garment in free text, e.g. "pullover hoodie", "crewneck sweatshirt". Not standardized: the same category has variants like "t-shirt", "short-sleeve T-shirt", "short-sleeve t-shirt". |
| `description` | TEXT | One-sentence visual description: color, cut, graphics, lettering. Good for chat answers and search. |
| `colors` | TEXT (JSON list) | Colors on the garment and its graphics, e.g. `["navy blue", "white"]`. Stored as a JSON string. |
| `search_tags` | TEXT (JSON list) | Keywords for matching shopper queries, e.g. "Yale hoodie", "college rivalry". Stored as a JSON string. |
| `image_file_path` | TEXT | Path to the product photo, relative to `data/`, e.g. `products/basic-hoodie-big-yale.jpg`. All 102 files exist. |
| `price` | REAL | Price in US dollars. Tees are $32, crewnecks $58, hoodies $68, quarter-zips $72, full-zip hooded $88, jackets $98, and a few items are $45. |

## `inventory` — stock per product per size (612 rows = 102 products × 6 sizes)
| Field | Type | What it is |
|---|---|---|
| `id` | INTEGER, PK, autoincrement | Row id. |
| `product_id` | TEXT, FK → `catalogue.product_id` | Which product. |
| `size` | TEXT | One of XS, S, M, L, XL, XXL. |
| `quantity` | INTEGER | Units in stock, from 0 to 25 (average about 9.7). **0 means sold out in that size.** |

`(product_id, size)` is UNIQUE, so there is exactly one stock number per product/size.

## `users` — shopper accounts (3 rows)
| Field | Type | What it is |
|---|---|---|
| `id` | INTEGER, PK, autoincrement | User id, referenced by `chat_messages.user_id`. |
| `name` | TEXT | Full display name, e.g. "Ada Lovelace". |
| `email` | TEXT, UNIQUE | Login email. One account per email. |
| `password_hash` | TEXT | Salted hash, never plaintext. Format is `pbkdf2_sha256$<salt>$<hash>`, so we check logins by re-hashing with PBKDF2-SHA256 and the stored salt. |
| `created_at` | TEXT | When the account was created (UTC `datetime('now')` default). |
| `first_name` | TEXT, nullable | First name. Added later with ALTER TABLE, so it can be null on old rows. |
| `last_name` | TEXT, nullable | Last name. Same as above. |

## `chat_messages` — saved chat history per user (22 rows)
| Field | Type | What it is |
|---|---|---|
| `id` | INTEGER, PK, autoincrement | Message id, in order. |
| `user_id` | INTEGER, FK → `users.id` | Whose conversation this belongs to. |
| `role` | TEXT | `user` (the shopper's message) or `assistant` (the bot's reply). |
| `content` | TEXT | The message text. Assistant replies are Markdown. |
| `products_json` | TEXT (JSON), nullable | For assistant messages, a JSON list of full product objects the bot recommended (product_id, name, garment_type, description, colors, tags, …). This is what lets the page show matching items next to the chat. It's null for user messages. |
| `created_at` | TEXT | Timestamp of the message. |

## `sqlite_sequence` — internal
Used by SQLite to track the last autoincrement id per table (inventory 612, users 3, chat_messages 22). Not app data.

## How they connect
- `catalogue` 1 → many `inventory` (on `product_id`)
- `users` 1 → many `chat_messages` (on `user_id`)
- Products show up in chats only through the JSON in `chat_messages.products_json` (there's no foreign key for this).
