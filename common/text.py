"""UTF-8 helpers for DCMTK output and Solr text that was decoded as Latin-1."""

from __future__ import annotations

from typing import Any

# UTF-8 umlauts shown as Latin-1 look like Ã¤ / Ã¶ / Â. Real names almost
# never contain these as a pair that also round-trips as UTF-8.
_MOJIBAKE_MARK = ("Ã", "Â")


def decode_dcmtk_output(data: bytes) -> str:
    """Decode findscu stderr/stdout. Prefer UTF-8, then Latin-1."""
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin-1")


def fix_utf8_mojibake(value: str) -> str:
    """Undo UTF-8 bytes that were decoded as Latin-1 (SchÃ¤del → Schädel)."""
    if not value or not any(m in value for m in _MOJIBAKE_MARK):
        return value
    try:
        return value.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value


def fix_utf8_mojibake_tree(obj: Any) -> Any:
    """Recursively repair mojibake in strings inside dicts/lists."""
    if isinstance(obj, str):
        return fix_utf8_mojibake(obj)
    if isinstance(obj, list):
        return [fix_utf8_mojibake_tree(v) for v in obj]
    if isinstance(obj, dict):
        return {k: fix_utf8_mojibake_tree(v) for k, v in obj.items()}
    return obj
