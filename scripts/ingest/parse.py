"""CSV / NA helpers shared by schedule and line loaders."""

from __future__ import annotations

from math import isfinite


NA_TOKENS = {"", "na", "nan", "none", "null", "nat"}


def blank(value) -> bool:
    if value is None:
        return True
    return str(value).strip().lower() in NA_TOKENS


def as_str(value) -> str | None:
    if blank(value):
        return None
    text = str(value).strip()
    if text.endswith(".0") and text[:-2].lstrip("-").isdigit():
        return text[:-2]
    return text


def as_int(value) -> int | None:
    if blank(value):
        return None
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None


def as_float(value) -> float | None:
    if blank(value):
        return None
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    if not isfinite(number):
        return None
    return number


def as_bool(value) -> bool | None:
    if blank(value):
        return None
    key = str(value).strip().lower()
    if key in {"true", "t", "1", "yes"}:
        return True
    if key in {"false", "f", "0", "no"}:
        return False
    return None


def median(values: list[float]) -> float | None:
    nums = sorted(float(v) for v in values if v is not None)
    if not nums:
        return None
    mid = len(nums) // 2
    if len(nums) % 2:
        return nums[mid]
    return (nums[mid - 1] + nums[mid]) / 2.0


def is_fbs(division: str | None) -> bool:
    return (division or "").strip().lower() == "fbs"
