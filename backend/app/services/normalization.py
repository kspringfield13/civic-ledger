"""Deterministic normalization used before matching. Never destroys raw values."""

import re

_SUFFIXES = r"\b(llc|inc|incorporated|corp|corporation|co|ltd|lp|llp|pllc)\b\.?"


def normalize_vendor_name(name: str) -> str:
    """Lowercase, strip punctuation and common corporate suffixes, collapse spaces."""
    s = name.lower()
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(_SUFFIXES, " ", s)
    return re.sub(r"\s+", " ", s).strip()


def normalize_address(raw: str) -> str:
    """Lowercase, expand nothing (v0), strip punctuation, collapse whitespace."""
    s = re.sub(r"[^\w\s]", " ", raw.lower())
    return re.sub(r"\s+", " ", s).strip()
