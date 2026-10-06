"""Shop agent entry point: builds the PydanticAI agent and runs one chat turn.

Sections:
  1. Input safety: redact card numbers / SSNs / passwords; crisis messages get a fixed caring reply
  2. Audit trail: append-only output/audit_trail.json of every agent loop step (no personal data)
  3. Agent: model via Portkey + prompts/prompt.md + tools.py + ShopReply output, output checks, run_chat()

main.py calls run_chat(); the agent uses tools.py and returns a models.ShopReply.
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
import uuid
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits
from pydantic_core import to_jsonable_python
from models import ChatMessage, ChatReply, PageContext, PageResults, ShopReply, User
import tools
from tools import TOOLS, ShopDeps

# =============================================================================
# 1. Input safety
# =============================================================================

CARD_RE = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")
SSN_RE = re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)")
CVV_RE = re.compile(r"\b(cvv|cvc|security code)\b\s*(?:is|:|=)?\s*\d{3,4}\b", re.I)
PASSWORD_RE = re.compile(r"\b(password|passcode|pin)\b(\s*(?:is|:|=)\s*)(\S+)", re.I)


def _luhn_ok(digits: str) -> bool:
    total, alt = 0, False
    for ch in reversed(digits):
        d = int(ch)
        if alt:
            d = d * 2 - 9 if d > 4 else d * 2
        total += d
        alt = not alt
    return total % 10 == 0


def redact(text: str) -> tuple[str, list[str]]:
    """Return (safe_text, kinds_removed)."""
    found: list[str] = []

    def card(m: re.Match) -> str:
        digits = re.sub(r"\D", "", m.group())
        if 13 <= len(digits) <= 19 and _luhn_ok(digits):
            found.append("card number")
            return "[redacted card number]"
        return m.group()

    text = CARD_RE.sub(card, text)
    if SSN_RE.search(text):
        found.append("SSN")
        text = SSN_RE.sub("[redacted SSN]", text)
    if CVV_RE.search(text):
        found.append("security code")
        text = CVV_RE.sub(lambda m: f"{m.group(1)} [redacted]", text)
    if PASSWORD_RE.search(text):
        found.append("password")
        text = PASSWORD_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}[redacted]", text)
    return text, list(dict.fromkeys(found))


# ---- Crisis messages -------------------------------------------------------------
# Handled before the model: an instant, consistent, caring reply that the provider's content
# filter can't block, and the message is not saved to chat history.
CRISIS_RE = re.compile(
    r"\b(suicid\w*|kill(ing)? myself|end(ing)? my life|take my (own )?life|hurt(ing)? myself|harm(ing)? myself|"
    r"self[- ]?harm\w*|want to die|don'?t want to (live|be alive)|no reason to live|cut(ting)? myself)\b",
    re.I,
)

CRISIS_REPLY = (
    "I'm really sorry you're feeling this way, and I'm glad you said something. You don't have to go through it "
    "alone. Please reach out to someone now:\n\n"
    "- **Call or text 988** (Suicide & Crisis Lifeline, 24/7, free and confidential)\n"
    "- **Yale Mental Health & Counseling** through Yale Health, if you're a Yale student\n"
    "- If you're in immediate danger, **call 911**\n\n"
    "If it helps, tell a friend or someone you trust how you're feeling. I'm here to help with the shop whenever "
    "you want, but your safety comes first."
)


def is_crisis(text: str) -> bool:
    return bool(CRISIS_RE.search(text))


# =============================================================================
# 2. Audit trail (output/audit_trail.json)
# =============================================================================

AUDIT_TRAIL = Path(__file__).resolve().parents[1] / "output" / "audit_trail.json"
MAX_SHORT = 160
_audit_lock = threading.Lock()


def _audit_short(value: Any, limit: int = MAX_SHORT) -> str:
    text = value if isinstance(value, str) else json.dumps(to_jsonable_python(value, fallback=str), ensure_ascii=False)
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def summarize_result(tool: str, content: Any) -> str:
    """One-line, PII-free summary of a tool result."""
    data = to_jsonable_python(content, fallback=str)
    if isinstance(data, dict) and "error" in data:
        return f"{data['error']}: {_audit_short(data.get('message', ''), 120)}"
    if tool == "search_products" and isinstance(data, dict):
        names = [r["name"] for r in data.get("results", [])[:3]]
        return f"{data.get('total_matches', 0)} matches; top: {', '.join(names) or '-'}" + (
            f" | note: {_audit_short(data['note'], 80)}" if data.get("note") else "")
    if tool == "check_stock" and isinstance(data, dict):
        return f"{data.get('name')} ${data.get('price')}: {_audit_short(data.get('summary', ''), 120)}"
    if tool in ("get_product_info", "get_viewed_product") and isinstance(data, dict):
        return (f"{data.get('name')} ${data.get('price')}; colors {data.get('colors')}; "
                f"sold out: {data.get('sold_out_sizes') or 'none'}")
    if tool == "get_customer_info" and isinstance(data, dict):
        return ("logged-in profile returned (name/email withheld from audit)" if data.get("logged_in")
                else "guest: no profile")
    if tool == "get_past_recommendations" and isinstance(data, list):
        return f"{len(data)} past recommendations: {', '.join(r['name'] for r in data[:3])}"
    if tool == "final_result" and isinstance(data, str):
        return _audit_short(data, 80)
    return _audit_short(data)


def safe_args(tool: str, args: Any) -> str:
    """Tool args are shopper search words / product names / sizes, never personal fields."""
    if tool == "final_result" and isinstance(args, dict):
        page = args.get("page_results") or {}
        return _audit_short({"product_ids": args.get("product_ids", []),
                       "page_results": page and {"title": page.get("title"), "count": len(page.get("product_ids", []))},
                       "reply_chars": len(args.get("reply", ""))})
    return _audit_short(args)


def audit_append(event: dict[str, Any]) -> None:
    """Append one event to the JSON array without rewriting earlier events."""
    event = {"time": datetime.now(timezone.utc).isoformat(timespec="milliseconds"), **event}
    line = json.dumps(event, ensure_ascii=False)
    with _audit_lock:
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


# =============================================================================
# 3. Agent
# =============================================================================

HERE = Path(__file__).resolve().parent
# HW4/.env first, then the workspace root .env that holds PORTKEY_API_KEY.
for folder in [HERE, *HERE.parents][:5]:
    load_dotenv(folder / ".env")

MODEL_NAME = os.getenv("MODEL_NAME", "gpt-5.6-luna")
PORTKEY_BASE_URL = os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1").rstrip("/")
PROMPT_PATH = HERE / "prompts" / "prompt.md"
log = logging.getLogger("campus_customs.agent")
MAX_HISTORY = 10          # earlier messages sent back to the model (cost cap)
AUDIT_PATH = tools.DATA_DIR / "chat_audit.jsonl"  # per-turn cost/latency log (data/ is gitignored)
MAX_MODEL_REQUESTS = 6    # model round-trips per turn (tool calls included)


def _model() -> OpenAIChatModel:
    key = os.getenv("PORTKEY_API_KEY", "").strip()
    if not key:
        raise RuntimeError("PORTKEY_API_KEY is not set (put it in a .env file).")
    client = AsyncOpenAI(api_key=key, base_url=PORTKEY_BASE_URL, default_headers={"x-portkey-api-key": key})
    return OpenAIChatModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))


@lru_cache(maxsize=1)
def build_agent() -> Agent[ShopDeps, ShopReply]:
    agent = Agent(
        _model(),
        deps_type=ShopDeps,
        output_type=ShopReply,
        instructions=PROMPT_PATH.read_text(encoding="utf-8"),
        tools=TOOLS,
        retries=2,  # room to fix a reply the number guard rejects (also covers bad tool args)
    )

    @agent.instructions
    def who_is_chatting(ctx: RunContext[ShopDeps]) -> str:
        u = ctx.deps.user
        if u is None:
            return "## Who is chatting\nA guest (not logged in). Their chat is not saved."
        return (
            "## Who is chatting\n"
            f"Logged in: {u.first_name} {u.last_name} <{u.email}>, member since {(u.created_at or '?')[:10]}. "
            f"{ctx.deps.saved_count} earlier messages are saved; the most recent ones are in this conversation's "
            "history. Use get_customer_info / get_past_recommendations for more."
        )

    @agent.instructions
    def where_they_are(ctx: RunContext[ShopDeps]) -> str:
        page = ctx.deps.page
        lines = [f"## Where they are on the site\nPage: {page.path}"]
        if page.product_id:
            name = next((p.name for p in tools.list_products() if p.product_id == page.product_id), None)
            if name:
                lines.append(
                    f'Viewing product: "{name}" (product_id: {page.product_id}). "This", "it", or "this one" '
                    "means this product unless they say otherwise. Call get_viewed_product for its details."
                )
        if page.results_title:
            lines.append(f'The "From your chat" grid on the page is showing: {page.results_title}.')
        return "\n".join(lines)

    @agent.output_validator
    def numbers_come_from_database(ctx: RunContext[ShopDeps], output: ShopReply) -> ShopReply:
        problems = unsupported_numbers(output.reply, ctx.messages) + sold_out_called_available(
            output.reply, ctx.messages
        )
        if problems:
            log.warning("number guard rejected reply: %s", problems)
            raise ModelRetry(
                "Your reply has problems: " + "; ".join(problems) + ". Use only the prices, quantities and "
                "size availability that tools returned this turn (call check_stock / get_product_info if needed). "
                "Sold-out sizes must be described as sold out."
            )
        return output

    return agent


# ---- Guard: prices and stock counts in a reply must come from the database ----

PRICE_RE = re.compile(r"\$\s?(\d+(?:\.\d{1,2})?)")
QTY_RE = re.compile(r"\b(\d+)\s+(?:left|in stock|available|remaining|units?)\b|\bonly\s+(\d+)\b", re.I)


def _walk(value: Any, prices: set[float], quantities: set[int]) -> None:
    if isinstance(value, dict):
        for k, v in value.items():
            if k == "price" and isinstance(v, (int, float)):
                prices.add(round(float(v), 2))
            elif k in ("quantity", "total_stock") and isinstance(v, int):
                quantities.add(v)
            else:
                _walk(v, prices, quantities)
    elif isinstance(value, list):
        for v in value:
            _walk(v, prices, quantities)
    elif isinstance(value, str):
        # Tool summaries like "S (8)" or "only 2 left", and prices the shopper typed ("under $70").
        prices.update(round(float(m), 2) for m in PRICE_RE.findall(value))
        quantities.update(int(m) for m in re.findall(r"\((\d+)\)", value))
        quantities.update(int(a or b) for a, b in QTY_RE.findall(value))


def unsupported_numbers(reply: str, messages: list[ModelMessage]) -> list[str]:
    """Prices / quantities in `reply` that no tool result (or the shopper) mentioned in this conversation."""
    prices: set[float] = set()
    quantities: set[int] = set()
    for msg in messages:
        if isinstance(msg, ModelRequest):
            for part in msg.parts:
                if isinstance(part, ToolReturnPart):
                    _walk(to_jsonable_python(part.content, fallback=str), prices, quantities)
                elif isinstance(part, UserPromptPart) and isinstance(part.content, str):
                    _walk(part.content, prices, quantities)
    problems = [f"${p}" for p in PRICE_RE.findall(reply) if round(float(p), 2) not in prices]
    problems += [f"{a or b} in stock" for a, b in QTY_RE.findall(reply) if int(a or b) not in quantities]
    return problems


async def _run_with_audit(message: str, deps: ShopDeps, history: list[ChatMessage], redacted: list[str]) -> Any:
    """Run the agent step by step (agent.iter) and append each loop event to output/audit_trail.json.

    Events: run_started → model_request → tool_call / tool_result / retry → … → run_finished (stop_reason).
    No chat text, names or emails are written (see section 2).
    """
    run_id = uuid.uuid4().hex[:12]
    base = {"run_id": run_id}
    audit_append({**base, "event": "run_started", "logged_in": deps.user is not None,
                  "page": deps.page.path, "on_product_page": bool(deps.page.product_id),
                  "message_chars": len(message), "history_messages": len(history),
                  "redacted": redacted or None, "model": MODEL_NAME})
    started = time.perf_counter()
    step = 0
    stop_reason = "unknown"
    try:
        async with build_agent().iter(
            message,
            deps=deps,
            message_history=_to_history(history),
            usage_limits=UsageLimits(request_limit=MAX_MODEL_REQUESTS),
        ) as run:
            async for node in run:
                if Agent.is_model_request_node(node):
                    step += 1
                    for part in node.request.parts:
                        if isinstance(part, ToolReturnPart):
                            audit_append({**base, "event": "tool_result", "step": step, "tool": part.tool_name,
                                          "result": summarize_result(part.tool_name, part.content)})
                        elif getattr(part, "part_kind", "") == "retry-prompt":
                            audit_append({**base, "event": "retry", "step": step,
                                          "tool": getattr(part, "tool_name", None),
                                          "reason": _audit_short(part.content, 200)})
                    audit_append({**base, "event": "model_request", "step": step})
                elif Agent.is_call_tools_node(node):
                    resp = node.model_response
                    calls = [p for p in resp.parts if getattr(p, "part_kind", "") == "tool-call"]
                    for c in calls:
                        audit_append({**base, "event": "tool_call", "step": step, "tool": c.tool_name,
                                      "args": safe_args(c.tool_name, c.args_as_dict())})
                    audit_append({**base, "event": "model_response", "step": step,
                                  "finish_reason": resp.finish_reason,
                                  "tool_calls": [c.tool_name for c in calls],
                                  "input_tokens": resp.usage.input_tokens, "output_tokens": resp.usage.output_tokens})
                elif Agent.is_end_node(node):
                    stop_reason = "final_result"
            result = run.result
    except Exception as exc:
        name = type(exc).__name__
        stop_reason = ("usage_limit" if name == "UsageLimitExceeded"
                       else "content_filter" if "content_filter" in str(exc) else "error")
        audit_append({**base, "event": "run_finished", "stop_reason": stop_reason, "error": name,
                      "seconds": round(time.perf_counter() - started, 2), "steps": step})
        raise
    usage = result.usage
    out = result.output
    audit_append({**base, "event": "run_finished", "stop_reason": stop_reason,
                  "seconds": round(time.perf_counter() - started, 2), "steps": step,
                  "requests": usage.requests, "input_tokens": usage.input_tokens,
                  "output_tokens": usage.output_tokens, "reply_chars": len(out.reply),
                  "product_ids": out.product_ids[:6],
                  "page_results": len(out.page_results.product_ids) if out.page_results else 0})
    return result


def _audit(result: Any, started: float, user: User | None, page: PageContext) -> None:
    """Append one line per turn: tokens, model requests, tools used, retries, seconds. No message text."""
    usage = result.usage
    tools: list[str] = []
    retries = 0
    for msg in result.new_messages():
        for part in getattr(msg, "parts", []):
            kind = getattr(part, "part_kind", "")
            if kind == "tool-call":
                tools.append(part.tool_name)
            elif kind == "retry-prompt":
                retries += 1
    row = {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "seconds": round(time.perf_counter() - started, 2),
        "requests": usage.requests,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "tools": tools,
        "retries": retries,
        "logged_in": user is not None,
        "on_product_page": bool(page.product_id),
    }
    log.info("chat turn %s", row)
    try:
        with AUDIT_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
    except OSError:
        pass


SIZE_RE = re.compile(r"(?<![A-Za-z])(XXL|XL|XS|S|M|L)(?![A-Za-z])")
AVAILABLE_RE = re.compile(r"\b(in stock|available|have (?:it|them|one) in|comes? in)\b", re.I)
NEGATION_RE = re.compile(r"sold out|out of stock|not (?:in stock|available)|unavailable|isn'?t|aren'?t|no longer|doesn'?t|don'?t", re.I)


def _stock_maps(messages: list[ModelMessage]) -> dict[str, set[str]]:
    """product_id -> sold-out sizes, from tool results this run that report per-product sizes."""
    out: dict[str, set[str]] = {}
    for msg in messages:
        if not isinstance(msg, ModelRequest):
            continue
        for part in msg.parts:
            if not isinstance(part, ToolReturnPart):
                continue
            data = to_jsonable_python(part.content, fallback=str)
            if isinstance(data, dict) and "product_id" in data and "sold_out_sizes" in data:
                out.setdefault(data["product_id"], set()).update(data["sold_out_sizes"])
    return out


def sold_out_called_available(reply: str, messages: list[ModelMessage]) -> list[str]:
    """Flag sentences that call a sold-out size available. Only checked when the turn looked up exactly one
    product (so a size can't belong to a different item); multi-product lists are left to the prompt rules."""
    maps = _stock_maps(messages)
    if len(maps) != 1:
        return []
    sold_out = next(iter(maps.values()))
    problems = []
    for sentence in re.split(r"(?<=[.!?;])\s+|\n+", reply):
        if AVAILABLE_RE.search(sentence) and not NEGATION_RE.search(sentence):
            bad = [s for s in SIZE_RE.findall(sentence) if s in sold_out]
            if bad:
                problems.append(f"says {', '.join(bad)} is available but the tool says it is sold out")
    return problems


def _to_history(history: list[ChatMessage]) -> list[ModelMessage]:
    out: list[ModelMessage] = []
    for m in history[-MAX_HISTORY:]:
        if m.role == "user":
            out.append(ModelRequest(parts=[UserPromptPart(content=m.content)]))
        elif m.role == "assistant":
            text = m.content
            if m.products:  # so "that one" / "the second hoodie" can be resolved to an id
                shown = ", ".join(f"{p.name} ({p.product_id})" for p in m.products[:8])
                text += f"\n[Cards shown: {shown}]"
            out.append(ModelResponse(parts=[TextPart(content=text)]))
    return out


async def run_chat(
    message: str, history: list[ChatMessage], user: User | None, page: PageContext | None = None
) -> ChatReply:
    """One chat turn: build deps, run the agent, turn its product ids into real cards, and save the turn.

    Logged in: history comes from the chat_messages table (the browser's copy is ignored), and the
    turn is saved there afterwards. Guest: the browser's in-memory history is used and nothing is saved.
    """
    message, redacted = redact(message)
    if is_crisis(message):
        # No model call and nothing saved: a fixed, caring reply with crisis resources.
        run_id = uuid.uuid4().hex[:12]
        audit_append({"run_id": run_id, "event": "run_started", "logged_in": user is not None,
                      "page": (page or PageContext()).path, "message_chars": len(message), "model": None})
        audit_append({"run_id": run_id, "event": "run_finished", "stop_reason": "crisis_response",
                      "steps": 0, "requests": 0, "note": "is_crisis matched; model not called; not saved"})
        return ChatReply(reply=CRISIS_REPLY)
    history = [m.model_copy(update={"content": redact(m.content)[0]}) for m in history]
    page = page or PageContext()
    if page.product_id and tools.get_product(page.product_id) is None:
        page = page.model_copy(update={"product_id": None})  # ignore ids that aren't real products
    saved_count = 0
    if user is not None:
        history = tools.load_history(user.id, limit=MAX_HISTORY)
        saved_count = tools.count_messages(user.id)
    deps = ShopDeps(user=user, page=page, saved_count=saved_count)
    started = time.perf_counter()
    result = await _run_with_audit(message, deps, history, redacted)
    out = result.output
    _audit(result, started, user, page)
    by_id = {p.product_id: p for p in tools.list_products()}

    def real(ids: list[str], limit: int, only_searched: bool = False) -> list[str]:
        """Keep ids that exist (drops anything made up), de-duplicated, capped."""
        kept: list[str] = []
        for pid in ids:
            if pid in by_id and pid not in kept and (not only_searched or pid in deps.searched_ids):
                kept.append(pid)
        return kept[:limit]

    page_results = None
    if out.page_results:
        # Page cards must come from a search this turn, so the grid is a real catalogue result.
        ids = real(out.page_results.product_ids, 30, only_searched=True)
        if ids:
            page_results = PageResults(
                title=out.page_results.title.strip() or "Results",
                query=message,
                total=len(ids),
                products=[by_id[p] for p in ids],
            )
    reply = ChatReply(
        reply=out.reply, products=[by_id[p] for p in real(out.product_ids, 6)], page=page_results,
        redacted=redacted, user_message=message if redacted else None,
    )
    if user is not None:
        tools.save_turn(user.id, message, reply.reply, reply.products)
    return reply
