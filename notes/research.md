# Research notes — Campus Customs / Yale Bulldog Blue

Source: https://yalebulldogblue.com/ (fetched 2026-10-02). Campus Customs is used as a local class setting, not a partnership.

## Visual style
- Clean collegiate look; **navy blue** is the main brand color (we'll keep our black/grey theme with navy accents).
- Horizontal top nav with category dropdowns, big seasonal hero banner, product grid (image, name, price, quick shop), "sold out" labels.
- Tone: celebratory, pride-focused, accessible.

## Store facts (for the agent prompt)
- Name: Yale Bulldog Blue by Campus Customs, 57 Broadway, New Haven, CT 06511.
- Officially licensed Yale merchandise. Categories: apparel, accessories, home goods, residential colleges (14), sports teams, grad/professional schools (law, medicine, engineering), family ("Yale Mom", "Grandpa", ...).
- Returns: 30 days from shipping; unworn with tags; final-sale and custom items (incl. Custom Alumni) not returnable. Customer pays return shipping unless store error. Refunds exclude original shipping, take 2–10 business days.
- Contact: orderdept@campuscustoms.com, (475) 301-4205.

## Given data (`data/campus_customs.db`)
- `catalogue` (102 products): product_id, name, garment_type, description, colors (JSON list), search_tags (JSON list), image_file_path (`products/<id>.jpg`), price.
  - Prices: tees $32, crewnecks $58, hoodies $68, quarter-zips $72, full-zip hooded $88, jackets/fleece $98, some hoodies/performance/mockneck $45.
- `inventory` (612 rows): product_id × size (XS–XXL), quantity. ~22–27 products sold out per size.
- `users` (3): name, first/last name, email, `password_hash` (format `pbkdf2_sha256$...`).
- `chat_messages` (22 rows): user_id, role, content, products_json — per-user chat history.
- `data/products/`: 102 product images.

## Repo rule
Public GitHub repo at the end; **never commit the database or product images** (`data/` is gitignored).
