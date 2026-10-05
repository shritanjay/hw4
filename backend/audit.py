"""Append-only audit trail of agent loop activity: HW4/output/audit_trail.json.

The file is always a valid JSON array. Each new event is appended by overwriting only the final "]",
so earlier events are never rewritten or wiped between runs or server restarts.

Privacy: output/ is committed to a public repo, so events hold tool names, short args/results and
stop reasons. Never chat text, names, emails, or passwords. Personal tool results are summarized.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic_core import to_jsonable_python

AUDIT_TRAIL = Path(__file__).resolve().parents[1] / "output" / "audit_trail.json"
MAX_SHORT = 160
_lock = threading.Lock()


def _short(value: Any, limit: int = MAX_SHORT) -> str:
    text = value if isinstance(value, str) else json.dumps(to_jsonable_python(value, fallback=str), ensure_ascii=False)
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def summarize_result(tool: str, content: Any) -> str:
    """One-line, PII-free summary of a tool result."""
    data = to_jsonable_python(content, fallback=str)
    if isinstance(data, dict) and "error" in data:
        return f"{data['error']}: {_short(data.get('message', ''), 120)}"
    if tool == "search_products" and isinstance(data, dict):
        names = [r["name"] for r in data.get("results", [])[:3]]
        return f"{data.get('total_matches', 0)} matches; top: {', '.join(names) or '-'}" + (
            f" | note: {_short(data['note'], 80)}" if data.get("note") else "")
    if tool == "check_stock" and isinstance(data, dict):
        return f"{data.get('name')} ${data.get('price')}: {_short(data.get('summary', ''), 120)}"
    if tool in ("get_product_info", "get_viewed_product") and isinstance(data, dict):
        return (f"{data.get('name')} ${data.get('price')}; colors {data.get('colors')}; "
                f"sold out: {data.get('sold_out_sizes') or 'none'}")
    if tool == "get_customer_info" and isinstance(data, dict):
        return ("logged-in profile returned (name/email withheld from audit)" if data.get("logged_in")
                else "guest: no profile")
    if tool == "get_past_recommendations" and isinstance(data, list):
        return f"{len(data)} past recommendations: {', '.join(r['name'] for r in data[:3])}"
    if tool == "final_result" and isinstance(data, str):
        return _short(data, 80)
    return _short(data)


def safe_args(tool: str, args: Any) -> str:
    """Tool args are shopper search words / product names / sizes, never personal fields."""
    if tool == "final_result" and isinstance(args, dict):
        page = args.get("page_results") or {}
        return _short({"product_ids": args.get("product_ids", []),
                       "page_results": page and {"title": page.get("title"), "count": len(page.get("product_ids", []))},
                       "reply_chars": len(args.get("reply", ""))})
    return _short(args)


def append(event: dict[str, Any]) -> None:
    """Append one event to the JSON array without rewriting earlier events."""
    event = {"time": datetime.now(timezone.utc).isoformat(timespec="milliseconds"), **event}
    line = json.dumps(event, ensure_ascii=False)
    with _lock:
        AUDIT_TRAIL.parent.mkdir(parents=True, exist_ok=True)
        if not AUDIT_TRAIL.exists() or AUDIT_TRAIL.stat().st_size == 0:
            AUDIT_TRAIL.write_text(f"[\n{line}\n]\n", encoding="utf-8")
            return
        with AUDIT_TRAIL.open("r+b") as f:
            f.seek(0, os.SEEK_END)
            pos = f.tell()
            # walk back to the closing bracket and overwrite from there
            while pos > 0:
                pos -= 1
                f.seek(pos)
                if f.read(1) == b"]":
                    break
            f.seek(pos)
            f.truncate()
            f.write(f",\n{line}\n]\n".encode("utf-8"))
