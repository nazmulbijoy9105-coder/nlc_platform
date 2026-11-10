"""Authoritative, versioned customer-facing scoring specification.

Statutory rule versions and scoring methodology versions are intentionally
independent. Category caps are applied first, then a global 100-point deduction
budget is allocated in the stable CATEGORY_ORDER. Diagnostic module scores are
not additive components of the headline score.
"""
from __future__ import annotations

from typing import Iterable

ScoringItem = tuple[str, int] | tuple[str, int, str | None]

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


def _normalise_item(item: ScoringItem) -> tuple[str, int, str | None]:
    if len(item) == 2:
        rule_id, impact = item
        event_key = None
    elif len(item) == 3:
        rule_id, impact, event_key = item
    else:
        raise ValueError("Scoring item must be (rule_id, impact[, scoring_event_key])")
    return str(rule_id), max(0, int(impact)), (
        str(event_key).strip() if event_key is not None and str(event_key).strip() else None
    )


def duplicate_event_indices(items: Iterable[ScoringItem]) -> set[int]:
    """Return suppressed indices for explicit shared scoring_event_key values.

    Only an explicit scoring_event_key deduplicates. A generic event_id is not
    sufficient because one event can create several legally distinct duties.
    For a shared key, keep the largest nominal impact; ties resolve by category
    order and then rule ID. The selection is deterministic and input-order free.
    """
    rows = [_normalise_item(item) for item in items]
    grouped: dict[str, list[int]] = {}
    for index, (_, _, event_key) in enumerate(rows):
        if event_key and category_for_rule(rows[index][0]) is not None:
            grouped.setdefault(event_key, []).append(index)

    suppressed: set[int] = set()
    category_rank = {name: index for index, name in enumerate(CATEGORY_ORDER)}
    for indices in grouped.values():
        if len(indices) < 2:
            continue
        winner = min(
            indices,
            key=lambda index: (
                -rows[index][1],
                category_rank.get(category_for_rule(rows[index][0]), len(CATEGORY_ORDER)),
                rows[index][0],
            ),
        )
        suppressed.update(index for index in indices if index != winner)
    return suppressed


def allocate_flag_deductions(items: Iterable[ScoringItem]) -> list[int]:
    """Allocate per-finding deductions, preserving input order.

    Per-category caps apply first. A single global budget of 100 then applies
    across categories in stable CATEGORY_ORDER. Explicit shared
    scoring_event_key values are deduplicated before allocation.
    """
    rows = [_normalise_item(item) for item in items]
    suppressed = duplicate_event_indices(rows)
    category_remaining = {name: cap for name, (cap, _) in CATEGORY_CAPS.items()}
    category_candidates: dict[str, list[tuple[int, int]]] = {
        name: [] for name in CATEGORY_ORDER
    }
    for index, (rule_id, impact, _) in enumerate(rows):
        if index in suppressed:
            continue
        category = category_for_rule(rule_id)
        if category is None:
            continue
        allocated = min(impact, category_remaining[category])
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


def category_deductions_from_flags(items: Iterable[ScoringItem]) -> dict[str, int]:
    rows = list(items)
    allocated = allocate_flag_deductions(rows)
    totals = {name: 0 for name in CATEGORY_ORDER}
    for item, amount in zip(rows, allocated):
        rule_id = _normalise_item(item)[0]
        category = category_for_rule(rule_id)
        if category is not None:
            totals[category] += amount
    return totals


def score_from_category_deductions(deductions: dict[str, int]) -> int:
    total = sum(max(0, int(deductions.get(name, 0))) for name in CATEGORY_ORDER)
    if total > SCORING_BASE:
        raise ValueError("Applied category deductions cannot exceed the 100-point base")
    return SCORING_BASE - total
