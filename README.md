# Campus Customs Shop + Chatbot (HW4)

A customer website for **Yale Bulldog Blue by Campus Customs** with a shop assistant chatbot. Shoppers can browse 102 products, create an account, chat about merch, see matching items appear on the page, and get honest price and stock answers from a local database.

> Class project for Yale SOM. Campus Customs is used as a local setting, not a partnership with the shop.

- **Frontend:** React + Vite + TypeScript (`frontend/`)
- **Backend:** Python FastAPI (`backend/main.py`, run with Uvicorn)
- **Agent:** PydanticAI, model `gpt-5.6-luna` via Portkey

## Repo layout

```
hw4/
├── AI_prompts.md          # every prompt used to build this, by problem
├── requirements.txt       # backend Python dependencies
├── .env.example           # placeholder env vars (copy to .env)
├── .gitignore
├── README.md
├── frontend/              # Vite React TypeScript app
├── backend/
│   ├── main.py            # FastAPI app; run with: uvicorn main:app
│   ├── agent.py           # ┐
│   ├── models.py          # │ the agent: four files
│   ├── tools.py           # │
│   ├── prompts/
│   │   └── prompt.md      # ┘
│   └── db.py · auth.py · memory.py · safety.py · audit.py · test_tools.py · bench.py   (supporting code)
└── output/
    ├── harness.md         # how the whole system works (start at §0 and §11)
    ├── design.md
    ├── usability.md
    ├── app_check.html     # live-site checks; double-click to open
    ├── app_check_images/  # screenshots linked from app_check.html
    └── audit_trail.json   # append-only agent loop log
```

### The agent (four files under `backend/`)

| File | Role |
|---|---|
| `prompts/prompt.md` | System prompt: Campus Customs voice, which tool to call, honesty rules, 12 safety rules, store facts, output format |
| `agent.py` | Builds the PydanticAI agent (model, prompt, tools, output type), runs each chat turn step by step, checks numbers against tool results, writes the audit trail |
| `tools.py` | Tools the agent can call, all read-only on the database: `search_products`, `get_product_info`, `check_stock`, `get_viewed_product`, `get_customer_info`, `get_past_recommendations` |
| `models.py` | Pydantic / PydanticAI types: API shapes, tool results, and the agent's structured output `ShopReply` |

`main.py` exposes the agent at `POST /api/chat` next to the product and account routes.

## Local-only data pack (not in git)

The database and product images come with the course materials and are **not** committed. Place them at the repo root like this:

```
hw4/
└── data/
    ├── campus_customs.db
    └── products/          # images referenced by the catalogue (image_file_path)
```

If you have the course `data.zip`, put it in `hw4/` and run `unzip -n data.zip`. That creates exactly this folder. The backend reads `data/campus_customs.db` and serves `data/products/` at `/images/…`, so nothing else needs configuring. The `data/` folder, `*.db`, `*.zip`, and `.env` are all in `.gitignore`.

## Run it (after placing the data pack)

**1. API key**

```bash
cp .env.example .env          # then replace the placeholder with your own PORTKEY_API_KEY
```

**2. Backend (FastAPI, port 8000)**

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r ../requirements.txt
uvicorn main:app --reload --port 8000
```

Check it at http://127.0.0.1:8000/api/health. It should return `{"ok": true, "products": 102}`. Without the data pack the server still starts, but health returns `"ok": false` and lists what's missing (e.g. `data/campus_customs.db`).

**3. Frontend (Vite, port 5173), in a second terminal**

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. The Vite dev server proxies `/api` and `/images` to the backend on port 8000, so keep both terminals running.

Next time, just run `source .venv/bin/activate && uvicorn main:app --reload --port 8000` in `backend/` and `npm run dev` in `frontend/`.

**Seed test login:** `test@campuscustoms.yale.edu` (password given with the assignment). You can also create your own account on the site.

## Tests

```bash
cd backend
.venv/bin/python test_tools.py   # offline, no model calls: 961 tool-vs-database checks + safety tests
.venv/bin/python bench.py        # live cost/latency benchmark (about 14 model calls)
```

## What to look at

| Feature | Try it | Docs |
|---|---|---|
| Honest stock + price | Open a product, ask the chat "how many of this are left in each size?" | `harness.md` §5 |
| Chat puts cards on the page | Ask "what hoodies do you have?" | §6 |
| Customer memory | Log in, chat, log out, log back in | §7 |
| Usability | Products → "My size" + sort; page-aware chat chips | §8, `usability.md` |
| Design | Departments, tees first, Yale-style type | §9, `design.md` |
| Audit trail + safety | `output/audit_trail.json`; safety rules in `backend/prompts/prompt.md` | §10–11 |
| Live checks | Double-click `output/app_check.html` | `app_check.html` |
