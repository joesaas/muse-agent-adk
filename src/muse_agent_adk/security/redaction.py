"""Best-effort redaction for logs and outputs.

Not a security boundary by itself — the boundary is never storing
secrets — but a cheap second line of defence for anything printed.
"""
from __future__ import annotations

import re

_KV = re.compile(r"(?i)(api[_-]?key|token|secret|password)(\s*[:=]\s*)\S+")
_BEARER = re.compile(r"(?i)bearer\s+\S+")
_SK = re.compile(r"\bsk-[A-Za-z0-9\-_]{8,}\b")
_SURROGATE = re.compile(r"\bhsurr:[A-Za-z0-9\-_]{8,}\b")


def redact(text: str) -> str:
    out = _KV.sub(lambda m: f"{m.group(1)}{m.group(2)}[已隐藏]", text)
    out = _BEARER.sub("Bearer [已隐藏]", out)
    out = _SK.sub("[已隐藏]", out)
    out = _SURROGATE.sub("[已隐藏]", out)
    return out
