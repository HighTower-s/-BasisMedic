"""Pure functions: strip noise, cap length, extract key tokens (R-10, 04_system_flow.md B2)."""

import re

_TIMESTAMP_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}\b|\b\d{2}:\d{2}:\d{2}\b")
_MEMORY_ADDR_RE = re.compile(r"\b0x[0-9A-Fa-f]+\b")
_BLANK_LINES_RE = re.compile(r"\n{3,}")

_RUNTIME_ERROR_RE = re.compile(r"Runtime Errors?\s+(\w+)")
_RC_RE = re.compile(r"\bRC\s*=?\s*(\d+)")
_TCODE_CANDIDATE_RE = re.compile(r"\b([A-Z][A-Z0-9_/]{1,19})\b")
_JOB_NAME_RE = re.compile(r"\b(?i:job)\s+([A-Z][A-Z0-9_]{2,30})\b")
_FIRST_ENGLISH_LINE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9 ,.'\"/_\-]{9,}$")


def strip_noise(text: str) -> str:
    """Remove timestamps, 0x memory addresses, and collapse repeated blank lines."""
    text = _TIMESTAMP_RE.sub("", text)
    text = _MEMORY_ADDR_RE.sub("", text)
    return _BLANK_LINES_RE.sub("\n\n", text)


def cap_length(text: str, limit: int = 2000) -> tuple[str, bool]:
    """Truncate to `limit` chars. Returns (text, was_truncated) — never raises."""
    if len(text) <= limit:
        return text, False
    return text[:limit], True


def extract_key_tokens(text: str) -> list[str]:
    """Runtime-error name, RC code, a T-code-shaped token, a job name, and the first
    English-looking error line — in that order, de-duplicated."""
    tokens: list[str] = []

    match = _RUNTIME_ERROR_RE.search(text)
    if match:
        tokens.append(match.group(1))

    match = _RC_RE.search(text)
    if match:
        tokens.append(f"RC={match.group(1)}")

    for match in _TCODE_CANDIDATE_RE.finditer(text):
        candidate = match.group(1)
        if candidate.isupper() and any(c.isdigit() for c in candidate) and len(candidate) <= 8:
            tokens.append(candidate)

    match = _JOB_NAME_RE.search(text)
    if match:
        tokens.append(match.group(1))

    for line in text.splitlines():
        stripped = line.strip()
        if _FIRST_ENGLISH_LINE_RE.match(stripped):
            tokens.append(stripped)
            break

    seen: set[str] = set()
    ordered = []
    for token in tokens:
        if token not in seen:
            seen.add(token)
            ordered.append(token)
    return ordered
