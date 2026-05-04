from __future__ import annotations

import re


def redact_sensitive_text(text: str) -> str:
    """Best-effort redaction before persisting prompts or excerpts."""
    if not text:
        return text
    out = text
    out = re.sub(r"(?i)\b(sk-[a-z0-9]{20,})\b", "sk-[REDACTED]", out)
    out = re.sub(r"(?i)\bBearer\s+[A-Za-z0-9._\-]{16,}\b", "Bearer [REDACTED]", out)
    out = re.sub(r"(?i)(api[_-]?key\s*[=:]\s*)(['\"]?)([a-z0-9_\-/+]{16,})", r"\1\2[REDACTED]", out)
    return out
