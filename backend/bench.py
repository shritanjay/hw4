"""Cost/latency benchmark: runs a fixed set of guest questions and prints the audit rows.

Run from backend/:  .venv/bin/python bench.py   (makes real model calls, about 6 turns)
"""

from __future__ import annotations

import asyncio
import json
import statistics

from agent import AUDIT_PATH, run_chat
from models import ChatMessage, PageContext

CASES = [
    ("what t shirts do you have?", PageContext(path="/")),
    ("do you have this in pink?", PageContext(path="/products/basic-hoodie-big-yale", product_id="basic-hoodie-big-yale")),
    ("is the Yale Grandpa Crewneck in M?", PageContext(path="/")),
    ("how many Champion Reverse Weave Hoodie 1 are left in each size?", PageContext(path="/")),
    ("gift for a yale mom under $60", PageContext(path="/")),
    ("what's your return policy?", PageContext(path="/about")),
]


async def main() -> None:
    start = AUDIT_PATH.stat().st_size if AUDIT_PATH.exists() else 0
    for q, page in CASES:
        r = await run_chat(q, [], None, page)
        print(f"Q: {q}\\nA: {r.reply[:160]}\\n")
    with AUDIT_PATH.open() as f:
        f.seek(start)
        rows = [json.loads(line) for line in f if line.strip()]
    for q, row in zip([c[0] for c in CASES], rows):
        print(f"{row['seconds']:>5}s  req={row['requests']}  in={row['input_tokens']:>6}  out={row['output_tokens']:>4}  "
              f"retries={row['retries']}  tools={row['tools']}  | {q[:40]}")
    print(f"TOTAL in={sum(r['input_tokens'] for r in rows)}  out={sum(r['output_tokens'] for r in rows)}  "
          f"median {statistics.median(r['seconds'] for r in rows)}s  requests={sum(r['requests'] for r in rows)}")


if __name__ == "__main__":
    asyncio.run(main())
