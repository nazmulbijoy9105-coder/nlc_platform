"""Six-state rule coverage funnel — the reporting-correction artifact.

The original fix-order table (item 9, "Reporting coverage correction") requires
the platform to distinguish registered, implemented, active, applicable,
evaluated and deferred rules instead of collapsing them into one ambiguous
"rules" count. This module is that funnel as a first-class, version-controlled
artifact with fail-closed structural invariants.

Funnel semantics::

    REGISTERED    canonical statutory registry (STATUTORY_RULE_REGISTRY keys)
    IMPLEMENTED   engine handles the rule (ComplianceFlag constructors, AST-parsed)
    ACTIVE        database row is_active=TRUE (runtime-collected; None = not collected)
    APPLICABLE    per-company applicability (run-scoped; None = not collected)
    EVALUATED     evaluated in a compliance run (run-scoped; None = not collected)
    DEFERRED      registered but deliberately NOT implemented (reason mandatory)

Every drop-out between adjacent stages must be explained explicitly:

* a registered rule that the engine does not handle must sit in ``deferred``
  with a reason (no silent implementation gaps);
* an implemented rule whose database row is not active must carry an explicit
  hold reason (e.g. migration 0115's ``QUARANTINED_LEGACY_IDENTITY`` disposition
  for INC-001) — no silent activation holds;
* applicability and evaluation are strict funnels over the active set.

Invariants (enforced by :meth:`RuleCoverageReport.validate`, each pinned by
``tests/unit/test_coverage_report.py``)::

    I1  implemented ⊆ registered                    (no phantom implementations)
    I2  registered ⊆ (implemented | deferred)       (no silent implementation gap)
    I3  deferred ⊆ registered, deferred ∩ implemented = ∅,
        every deferred ID has a non-empty reason    (deferral is explicit)
    I4  active ⊆ registered                         (no phantom active rows)
    I5  implemented - active carries an explicit
        hold reason each                            (no silent activation holds)
    I6  applicable ⊆ active                         (applicability funnel)
    I7  evaluated ⊆ applicable                      (evaluation funnel)
    I8  summary/to_dict always expose all six
        states, including empty or uncollected ones (no silent state collapse)

Run-scoped stages (active, applicable, evaluated) accept ``None`` meaning "not
collected in this scope" — the static CI artifact collects corpus stages only;
live collection can later be injected by the production-parity workflow without
changing this schema.

The engine parser mirrors the reference extractor in
``tests/unit/test_canonical_integrity.py``: rule IDs are read from the same
``ComplianceFlag`` constructor call (plus the two known shared-constructor
paths, ``_run_bsec_rules`` candidate tuples and ``_run_director_rules`` literal
assignments), never inferred from nearby text.
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Iterable, Mapping

__all__ = [
    "CoverageInvariantError",
    "CoverageStage",
    "RuleCoverageReport",
    "build_registry_coverage",
    "parse_engine_rule_ids",
]


class CoverageStage(str, Enum):
    """The six report states, in funnel order."""

    REGISTERED = "registered"
    IMPLEMENTED = "implemented"
    ACTIVE = "active"
    APPLICABLE = "applicable"
    EVALUATED = "evaluated"
    DEFERRED = "deferred"


class CoverageInvariantError(RuntimeError):
    """Raised when the coverage funnel violates a structural invariant."""

    def __init__(self, violations: list[str]) -> None:
        self.violations = violations
        joined = "\n".join(f"  - {item}" for item in violations)
        super().__init__(f"rule coverage funnel invariants violated:\n{joined}")


def _is_rule_id(value: str) -> bool:
    """Validate the repository's PREFIX-NNN rule ID format without text scraping."""
    parts = value.split("-")
    return (
        len(parts) == 2
        and bool(parts[0])
        and parts[0].isalpha()
        and parts[0].isupper()
        and len(parts[1]) == 3
        and parts[1].isdigit()
    )


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _function_def(tree: ast.Module, name: str) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    return next(
        (
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name
        ),
        None,
    )


def _literal_rule_id_elements(func_node: ast.AST) -> Iterable[str]:
    """Yield literal rule-ID strings declared as first tuple elements."""
    for child in ast.walk(func_node):
        if (
            isinstance(child, ast.Tuple)
            and child.elts
            and isinstance(child.elts[0], ast.Constant)
            and isinstance(child.elts[0].value, str)
            and _is_rule_id(child.elts[0].value)
        ):
            yield child.elts[0].value


def _literal_rule_id_assignments(func_node: ast.AST) -> Iterable[str]:
    """Yield literal rule-ID strings assigned to a variable named ``rule_id``."""
    for child in ast.walk(func_node):
        if not isinstance(child, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "rule_id" for target in child.targets):
            continue
        if isinstance(child.value, ast.Constant) and isinstance(child.value.value, str):
            yield child.value.value


def parse_engine_rule_ids(engine_source: str, filename: str = "app/rule_engine/engine.py") -> frozenset[str]:
    """Extract engine-handled rule IDs from ComplianceFlag constructor calls.

    Raises ``ValueError`` with a per-line report when a constructor call is not
    structurally parseable — the funnel must never guess.
    """
    tree = ast.parse(engine_source, filename=filename)
    rule_ids: set[str] = set()
    errors: list[str] = []
    shared_constructor_functions = ("_run_bsec_rules", "_run_director_rules")

    # Call nodes inside the known shared-constructor functions may bind rule_id
    # dynamically; their concrete IDs are resolved from literal declarations.
    shared_call_nodes: set[int] = set()
    for function_name in shared_constructor_functions:
        function_node = _function_def(tree, function_name)
        if function_node is not None:
            for child in ast.walk(function_node):
                if isinstance(child, ast.Call):
                    shared_call_nodes.add(id(child))

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or _call_name(node.func) != "ComplianceFlag":
            continue
        keywords = {kw.arg: kw.value for kw in node.keywords if kw.arg is not None}
        rule_node = keywords.get("rule_id")

        if isinstance(rule_node, ast.Name) and rule_node.id == "rule_id":
            # Shared-constructor call: the concrete IDs come from the literal
            # declarations inside the owning function (resolved below).
            if id(node) not in shared_call_nodes:
                errors.append(
                    f"line {node.lineno}: shared ComplianceFlag constructor outside a known "
                    f"shared-constructor function {sorted(shared_constructor_functions)}"
                )
            continue
        if not isinstance(rule_node, ast.Constant) or not isinstance(rule_node.value, str):
            errors.append(f"line {node.lineno}: ComplianceFlag rule_id must be a string literal")
            continue
        rule_id = rule_node.value
        if not _is_rule_id(rule_id):
            errors.append(f"line {node.lineno}: invalid rule_id {rule_id!r}")
            continue
        rule_ids.add(rule_id)

    bsec_function = _function_def(tree, "_run_bsec_rules")
    if bsec_function is not None:
        rule_ids.update(_literal_rule_id_elements(bsec_function))

    director_function = _function_def(tree, "_run_director_rules")
    if director_function is not None:
        rule_ids.update(_literal_rule_id_assignments(director_function))

    if errors:
        raise ValueError(
            "engine rule declarations are not structurally parseable:\n"
            + "\n".join(f"  - {error}" for error in errors)
        )
    if not rule_ids:
        raise ValueError("no ComplianceFlag rule declarations were found in the engine source")
    return frozenset(rule_ids)


@dataclass(frozen=True)
class RuleCoverageReport:
    """The six-state coverage funnel over one rule corpus."""

    registered: frozenset[str]
    implemented: frozenset[str]
    deferred: frozenset[str] = frozenset()
    active: frozenset[str] | None = None
    applicable: frozenset[str] | None = None
    evaluated: frozenset[str] | None = None
    deferred_reasons: Mapping[str, str] = field(default_factory=dict)
    active_hold_reasons: Mapping[str, str] = field(default_factory=dict)

    def validate(self) -> None:
        """Raise :class:`CoverageInvariantError` aggregating every violation."""
        violations: list[str] = []

        phantom_implementations = self.implemented - self.registered
        if phantom_implementations:
            violations.append(
                f"I1 phantom implementation (engine handles IDs absent from the registry): "
                f"{sorted(phantom_implementations)}"
            )

        silent_gaps = self.registered - self.implemented - self.deferred
        if silent_gaps:
            violations.append(
                f"I2 silent implementation gap (registered, neither implemented nor explicitly "
                f"deferred): {sorted(silent_gaps)}"
            )

        phantom_deferred = self.deferred - self.registered
        if phantom_deferred:
            violations.append(
                f"I3 deferred IDs absent from the registry: {sorted(phantom_deferred)}"
            )
        overlap = self.deferred & self.implemented
        if overlap:
            violations.append(
                f"I3 IDs simultaneously implemented and deferred: {sorted(overlap)}"
            )
        unexplained_deferred = {
            rule_id
            for rule_id in self.deferred
            if not str(self.deferred_reasons.get(rule_id, "")).strip()
        }
        if unexplained_deferred:
            violations.append(
                f"I3 deferred IDs without a non-empty reason: {sorted(unexplained_deferred)}"
            )
        stray_deferred_reasons = set(self.deferred_reasons) - set(self.deferred)
        if stray_deferred_reasons:
            violations.append(
                f"I3 deferred reasons recorded for IDs that are not deferred: "
                f"{sorted(stray_deferred_reasons)}"
            )

        if self.active is not None:
            phantom_active = self.active - self.registered
            if phantom_active:
                violations.append(
                    f"I4 active rows for IDs absent from the registry: {sorted(phantom_active)}"
                )
            unheld = self.implemented - self.active - set(self.active_hold_reasons)
            if unheld:
                violations.append(
                    f"I5 implemented but inactive without an explicit hold reason: {sorted(unheld)}"
                )
            stray_holds = set(self.active_hold_reasons) - (self.implemented - self.active)
            if stray_holds:
                violations.append(
                    f"I5 hold reasons recorded for IDs that are not implemented-and-inactive: "
                    f"{sorted(stray_holds)}"
                )
            empty_holds = {
                rule_id
                for rule_id, reason in self.active_hold_reasons.items()
                if not str(reason).strip()
            }
            if empty_holds:
                violations.append(f"I5 hold reasons must be non-empty: {sorted(empty_holds)}")

        if self.applicable is not None:
            if self.active is None:
                violations.append("I6 applicable collected without the active stage it funnels from")
            else:
                beyond_active = self.applicable - self.active
                if beyond_active:
                    violations.append(
                        f"I6 applicable IDs that are not active: {sorted(beyond_active)}"
                    )

        if self.evaluated is not None:
            if self.applicable is None:
                violations.append("I7 evaluated collected without the applicable stage it funnels from")
            else:
                beyond_applicable = self.evaluated - self.applicable
                if beyond_applicable:
                    violations.append(
                        f"I7 evaluated IDs that are not applicable: {sorted(beyond_applicable)}"
                    )

        if violations:
            raise CoverageInvariantError(violations)

    def summary(self) -> dict[str, int | None]:
        """Counts for all six states; ``None`` marks a run-scoped stage not collected."""
        collected = {
            CoverageStage.REGISTERED.value: len(self.registered),
            CoverageStage.IMPLEMENTED.value: len(self.implemented),
            CoverageStage.ACTIVE.value: None if self.active is None else len(self.active),
            CoverageStage.APPLICABLE.value: None if self.applicable is None else len(self.applicable),
            CoverageStage.EVALUATED.value: None if self.evaluated is None else len(self.evaluated),
            CoverageStage.DEFERRED.value: len(self.deferred),
        }
        return collected

    def to_dict(self) -> dict[str, object]:
        """JSON-safe artifact payload; all six states are always present (I8)."""
        return {
            "summary": self.summary(),
            "states": {
                CoverageStage.REGISTERED.value: sorted(self.registered),
                CoverageStage.IMPLEMENTED.value: sorted(self.implemented),
                CoverageStage.ACTIVE.value: None if self.active is None else sorted(self.active),
                CoverageStage.APPLICABLE.value: None if self.applicable is None else sorted(self.applicable),
                CoverageStage.EVALUATED.value: None if self.evaluated is None else sorted(self.evaluated),
                CoverageStage.DEFERRED.value: sorted(self.deferred),
            },
            "deferred_reasons": dict(sorted(self.deferred_reasons.items())),
            "active_hold_reasons": dict(sorted(self.active_hold_reasons.items())),
        }


def build_registry_coverage(
    engine_source: str,
    registry: Mapping[str, object],
) -> RuleCoverageReport:
    """Corpus-level static report: registry-registered vs engine-implemented."""
    implemented = parse_engine_rule_ids(engine_source)
    report = RuleCoverageReport(
        registered=frozenset(registry),
        implemented=implemented,
    )
    report.validate()
    return report


def main(argv: list[str] | None = None) -> int:
    """CLI: emit the six-state coverage artifact; exit 1 on any invariant violation."""
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        prog="canonical_architecture.coverage_report",
        description="Six-state rule coverage funnel report (registered, implemented, "
        "active, applicable, evaluated, deferred).",
    )
    parser.add_argument(
        "--engine",
        default=str(repo_root / "app" / "rule_engine" / "engine.py"),
        help="engine source path (default: app/rule_engine/engine.py under the repo root)",
    )
    parser.add_argument(
        "--output",
        default=str(repo_root / "artifacts" / "rule-coverage-report.json"),
        help="artifact JSON output path",
    )
    args = parser.parse_args(argv)

    from canonical_architecture.statutory_rules import STATUTORY_RULE_REGISTRY

    engine_path = Path(args.engine)
    try:
        engine_source = engine_path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"cannot read engine source {engine_path}: {exc}", file=sys.stderr)
        return 2

    try:
        report = build_registry_coverage(engine_source, STATUTORY_RULE_REGISTRY)
    except (ValueError, CoverageInvariantError) as exc:
        print(f"six-state rule coverage report FAILED:\n{exc}", file=sys.stderr)
        return 1

    payload = report.to_dict()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    print("six-state rule coverage report:")
    for stage in CoverageStage:
        count = payload["summary"][stage.value]
        rendered = "not collected" if count is None else str(count)
        print(f"  {stage.value:<12} {rendered}")
    print(f"artifact written: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
