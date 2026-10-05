"""Input safety: strip sensitive data from shopper messages before the model or the database sees it.

Detects payment card numbers (13–19 digits that pass the Luhn check), US SSNs, CVV codes, and
"my password is …" disclosures. Each is replaced with a [redacted …] placeholder.
"""

from __future__ import annotations

import re

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
