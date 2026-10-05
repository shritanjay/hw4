"""Offline checks: every tool answer must equal the raw database. No model calls.

Run from backend/:  .venv/bin/python test_tools.py
"""

from __future__ import annotations

import json
import sqlite3

import db
from agent import unsupported_numbers
from pydantic_ai.messages import ModelRequest, ToolReturnPart
from tools import check_stock, get_product_info, search_products


class Ctx:  # tools only need .deps
    deps = None


def raw():
    conn = sqlite3.connect(db.DB_PATH)
    cat = {r[0]: {"description": r[1], "price": r[2], "colors": json.loads(r[3]), "name": r[4]}
           for r in conn.execute("SELECT product_id, description, price, colors, name FROM catalogue")}
    stock: dict[str, dict[str, int]] = {}
    for pid, size, qty in conn.execute("SELECT product_id, size, quantity FROM inventory"):
        stock.setdefault(pid, {})[size] = qty
    return cat, stock


def main() -> None:
    cat, stock = raw()
    checks = 0
    for pid, row in cat.items():
        info = get_product_info(Ctx(), pid)
        assert info.description == row["description"], pid
        assert info.price == row["price"], pid
        assert info.colors == row["colors"], pid
        assert set(info.sold_out_sizes) == {s for s, q in stock[pid].items() if q == 0}, pid

        sc = check_stock(Ctx(), pid)
        assert {s.size: s.quantity for s in sc.sizes} == stock[pid], pid
        assert sc.total_stock == sum(stock[pid].values()), pid
        for s in sc.sizes:
            assert ("sold out" in s.status) == (s.quantity == 0), (pid, s)
            one = check_stock(Ctx(), pid, s.size.lower())
            assert one.requested_size_in_stock == (s.quantity > 0), (pid, s.size)
            if s.quantity == 0:
                assert one.summary.startswith(f"{s.size}: SOLD OUT"), one.summary
            checks += 1
        checks += 2

    # search returns real prices/sizes, and keeps items that are sold out in the requested size
    for m in search_products(Ctx(), "hoodie").results:
        assert m.price == cat[m.product_id]["price"]
        assert set(m.sold_out_sizes) == {s for s, q in stock[m.product_id].items() if q == 0}
    for size in db.SIZE_ORDER:
        for pid in [p for p in cat if stock[p].get(size) == 0]:
            found = search_products(Ctx(), cat[pid]["name"], size=size).results
            assert any(m.product_id == pid for m in found), f"{pid} hidden when searching size {size}"
            checks += 1

    # unknown ids / sizes are reported, not invented
    assert check_stock(Ctx(), "not-a-product").error == "unknown_product"
    assert get_product_info(Ctx(), "not-a-product").error == "unknown_product"
    empty = search_products(Ctx(), "zzqx unicorn")
    assert empty.total_matches == 0 and empty.results == [] and "No matches" in empty.note
    assert search_products(Ctx(), "hoodie", color="navy", max_price=70).filters == {"color": "navy", "max_price": 70}
    assert "doesn't come in size" in check_stock(Ctx(), "basic-hoodie-big-yale", "XXXL").summary

    # number guard
    msgs = [ModelRequest(parts=[ToolReturnPart(tool_name="check_stock", tool_call_id="1",
                                               content=check_stock(Ctx(), "basic-hoodie-big-yale"))])]
    assert unsupported_numbers("It's $68 and XL has only 2 left.", msgs) == []
    assert unsupported_numbers("It's $55 with 99 in stock.", msgs) == ["$55", "99 in stock"]

    print(f"OK: {len(cat)} products, {checks} tool-vs-database checks, search + guard checks passed.")





def test_name_lookup() -> None:
    """check_stock / get_product_info accept names, and refuse to guess between close matches."""
    assert check_stock(Ctx(), "Yale Grandpa Crewneck", "M").product_id == "yale-grandpa-crewneck"
    assert check_stock(Ctx(), "yale grandpa crewneck").product_id == "yale-grandpa-crewneck"
    assert get_product_info(Ctx(), "Champion Reverse Weave Hoodie 1").product_id == "champion-reverse-weave-hoodie-1"
    amb = check_stock(Ctx(), "grandpa")
    assert amb.error == "ambiguous_product" and "Yale Grandpa Hoodie" in amb.message, amb
    assert check_stock(Ctx(), "unicorn rainbow").error == "unknown_product"
    for pid in raw()[0]:  # every product resolves from its own name
        name = raw()[0][pid]["name"]
        got = check_stock(Ctx(), name)
        assert getattr(got, "product_id", None) == pid, (name, got)
    print("OK: name lookup resolves all 102 names exactly; ambiguous / unknown names are refused.")


def test_safety() -> None:
    from agent import sold_out_called_available
    from safety import redact

    t, k = redact("order it, my card is 4111 1111 1111 1111 cvv 123 and ssn 123-45-6789")
    assert "4111" not in t and "123-45-6789" not in t and "cvv [redacted]" in t, t
    assert k == ["card number", "SSN", "security code"], k
    t, k = redact("my password is hunter2!!")
    assert "hunter2" not in t and k == ["password"], t
    for safe in ["do you have 2 hoodies for $68?", "order 1234567890123 (not a card)", "size XL please"]:
        assert redact(safe) == (safe, []), safe

    # Champion: XS and XL sold out
    msgs = [ModelRequest(parts=[ToolReturnPart(tool_name="check_stock", tool_call_id="1",
                                               content=check_stock(Ctx(), "champion-reverse-weave-hoodie-1"))])]
    assert sold_out_called_available("Yes, XL is in stock!", msgs)
    assert sold_out_called_available("It's available in S, M, XL and XXL.", msgs)
    assert not sold_out_called_available("**XL is sold out**. It's in stock in S, M, L, and XXL.", msgs)
    assert not sold_out_called_available("XS and XL aren't available right now.", msgs)
    pink = search_products(Ctx(), "pink")
    assert [m.name for m in pink.results] == ["Big Yale Tri Blend T Shirt"] and "Closest shades" in pink.note, pink
    assert search_products(Ctx(), "hoodie", color="grey").total_matches > 0
    assert search_products(Ctx(), "purple").total_matches == 0
    from safety import is_crisis
    for msg in ["I keep thinking about hurting myself", "i want to die", "thinking about suicide", "self-harm"]:
        assert is_crisis(msg), msg
    for msg in ["this hoodie is to die for", "my brother hurt his knee playing hockey", "kill it at the game!"]:
        assert not is_crisis(msg), msg
    print("OK: redaction (card/SSN/CVV/password, no false positives) and sold-out claim guard.")


def test_audit_append_only() -> None:
    """audit.append keeps a valid JSON array and never changes earlier bytes (uses a temp file)."""
    import tempfile
    from pathlib import Path

    import audit

    real = audit.AUDIT_TRAIL
    with tempfile.TemporaryDirectory() as tmp:
        audit.AUDIT_TRAIL = Path(tmp) / "audit_trail.json"
        try:
            audit.append({"event": "run_started", "run_id": "t1"})
            first = audit.AUDIT_TRAIL.read_bytes()
            for i in range(5):
                audit.append({"event": "tool_call", "run_id": "t1", "step": i})
            data = audit.AUDIT_TRAIL.read_bytes()
            assert data.startswith(first.rstrip().rstrip(b"]").rstrip()), "earlier bytes changed"
            events = json.loads(data)
            assert len(events) == 6 and events[0]["event"] == "run_started" and events[-1]["step"] == 4
        finally:
            audit.AUDIT_TRAIL = real
    s = audit.summarize_result("get_customer_info", {"logged_in": True, "email": "x@y.edu", "first_name": "Ada"})
    assert "x@y.edu" not in s and "Ada" not in s, s
    print("OK: audit trail is append-only valid JSON; personal tool results are withheld.")


if __name__ == "__main__":
    main()
    test_name_lookup()
    test_safety()
    test_audit_append_only()
