"""Authoritative, versioned customer-facing scoring specification.

Statutory rule versions and scoring methodology versions are intentionally
independent. Category caps are applied first, then a global 100-point deduction
budget is allocated in the stable CATEGORY_ORDER. Diagnostic module scores are
not additive components of the headline score.
"""
from __future__ import annotations

from typing import Iterable

SCORING_SPEC_VERSION = "2.0.0"
SCORING_BASE = 100
CATEGORY_ORDER = (
    "TAX", "AGM", "AUD", "RET", "DIR", "SHR", "CAP",
    "OFF", "REG", "BNK", "LBR", "BSEC", "FX", "ESC",
)

# key -> (maximum deduction, matching rule-ID prefixes)
CATEGORY_CAPS: dict[str, tuple[int, tuple[str, ...]]] = {
    "TAX": (15, ("TAX-", "VAT-")),
    "AGM": (30, ("AGM-",)),
    "AUD": (25, ("AUD-",)),
    "RET": (20, ("AR-",)),
    "DIR": (25, ("DIR-", "INC-", "DEF-", "TL-", "BOD-", "MEM-")),
    "SHR": (20, ("SH-", "TR-")),
    "CAP": (15, ("CAP-", "STR-", "CHG-", "ACC-")),
    "OFF": (10, ("OFF-",)),
    "REG": (10, ("REG-",)),
    "BNK": (20, ("BNK-",)),
    "LBR": (10, ("LBR-",)),
    "BSEC": (15, ("BSEC-",)),
    "FX": (10, ("FX-",)),
    "ESC": (15, ("ESC-",)),
}

if tuple(CATEGORY_CAPS) != CATEGORY_ORDER:
    raise RuntimeError("CATEGORY_CAPS must follow the immutable CATEGORY_ORDER")


def category_for_rule(rule_id: str) -> str | None:
    matches = [
        name for name, (_, prefixes) in CATEGORY_CAPS.items()
        if rule_id.startswith(prefixes)
    ]
    if len(matches) > 1:
        raise ValueError(f"Rule {rule_id} maps to multiple scoring categories: {matches}")
    return matches[0] if matches else None


def allocate_flag_deductions(items: Iterable[tuple[str, int]]) -> list[int]:
    """Allocate per-finding deductions, preserving input order.

    Per-category caps apply first. A single global budget of 100 then applies
    across categories in CATEGORY_ORDER. Each finding is allocated at most
    once. Unknown, excluded, inactive and otherwise ineligible findings must
    be filtered by the caller before calling this function.
    """
    rows = list(items)
    category_remaining = {name: cap for name, (cap, _) in CATEGORY_CAPS.items()}
    category_candidates: dict[str, list[tuple[int, int]]] = {
        name: [] for name in CATEGORY_ORDER
    }
    for index, (rule_id, impact) in enumerate(rows):
        category = category_for_rule(rule_id)
        if category is None:
            continue
        requested = max(0, int(impact))
        allocated = min(requested, category_remaining[category])
        category_remaining[category] -= allocated
        category_candidates[category].append((index, allocated))

    applied = [0] * len(rows)
    global_remaining = SCORING_BASE
    for category in CATEGORY_ORDER:
        for index, category_amount in category_candidates[category]:
            amount = min(category_amount, global_remaining)
            applied[index] = amount
            global_remaining -= amount
            if global_remaining == 0:
                break
        if global_remaining == 0:
            break
    return applied


def category_deductions_from_flags(items: Iterable[tuple[str, int]]) -> dict[str, int]:
    rows = list(items)
    allocated = allocate_flag_deductions(rows)
    totals = {name: 0 for name in CATEGORY_ORDER}
    for (rule_id, _), amount in zip(rows, allocated):
        category = category_for_rule(rule_id)
        if category is not None:
            totals[category] += amount
    return totals


def score_from_category_deductions(deductions: dict[str, int]) -> int:
    total = sum(max(0, int(deductions.get(name, 0))) for name in CATEGORY_ORDER)
    if total > SCORING_BASE:
        raise ValueError("Applied category deductions cannot exceed the 100-point base")
    return SCORING_BASE - total
