import pytest
"""Structured parity gate for engine, canonical registry, rescue registry and seed corpus.

The engine is parsed as Python syntax. Rule IDs and statutory bases are read
from the same ComplianceFlag constructor call, not inferred from nearby text.
"""
import ast
import re
import csv
from collections import Counter
from pathlib import Path

from canonical_architecture.statutory_rescue import STATUTORY_RESCUE_REGISTRY
from canonical_architecture.statutory_rules import STATUTORY_RULE_REGISTRY
from canonical_architecture.legal_reconciliation import LEGAL_RECONCILIATION

ROOT = Path(__file__).resolve().parents[2]
EXPECTED = 85  # ILRMF production corpus; this gate does not add or remove rules.



def test_statutory_catalog_has_no_duplicate_literal_dictionary_keys():
    """Reject silent Python dict-key overwrites in the legal rule catalogue."""
    source = (
        ROOT / "canonical_architecture" / "statutory_rules.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source, filename="canonical_architecture/statutory_rules.py")
    duplicates = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        seen = {}
        for key_node in node.keys:
            if not isinstance(key_node, ast.Constant) or not isinstance(key_node.value, str):
                continue
            key = key_node.value
            if key in seen:
                duplicates.append(
                    f"line {key_node.lineno}: duplicate key {key!r}; first at line {seen[key]}"
                )
            else:
                seen[key] = key_node.lineno

    assert not duplicates, "\n".join(duplicates)

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


def _call_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _engine_rule_data():
    """Return rule_id -> statutory bases from actual ComplianceFlag call nodes."""
    source = (ROOT / "app" / "rule_engine" / "engine.py").read_text(encoding="utf-8")
    tree = ast.parse(source, filename="app/rule_engine/engine.py")
    result = {}
    errors = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or _call_name(node.func) != "ComplianceFlag":
            continue

        keywords = {kw.arg: kw.value for kw in node.keywords if kw.arg is not None}
        rule_node = keywords.get("rule_id")
        basis_node = keywords.get("statutory_basis")

        if isinstance(rule_node, ast.Name) and rule_node.id == "rule_id":
            # BSEC candidates are declared as literal rule-ID tuples and
            # consumed by one shared ComplianceFlag constructor below.
            continue
        if not isinstance(rule_node, ast.Constant) or not isinstance(rule_node.value, str):
            errors.append(f"line {node.lineno}: ComplianceFlag rule_id must be a string literal")
            continue

        rule_id = rule_node.value
        if not _is_rule_id(rule_id):
            errors.append(f"line {node.lineno}: invalid rule_id {rule_id!r}")
            continue

        if not isinstance(basis_node, ast.Constant) or not isinstance(basis_node.value, str):
            errors.append(
                f"line {node.lineno}: {rule_id} statutory_basis must be a string literal"
            )
            continue

        basis = basis_node.value.strip()
        if not basis:
            errors.append(f"line {node.lineno}: {rule_id} statutory_basis is empty")
            continue

        result.setdefault(rule_id, set()).add(basis)

    # Resolve BSEC candidate IDs and the conditional statutory-basis
    # assignment from the function AST. Each branch must remain a literal;
    # map the exact basis to the candidate it governs.
    bsec_function = next(
        (node for node in ast.walk(tree)
         if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
         and node.name == "_run_bsec_rules"),
        None,
    )
    if bsec_function is not None:
        basis_by_rule = {}
        for child in ast.walk(bsec_function):
            if not isinstance(child, ast.Assign):
                continue
            if not any(isinstance(target, ast.Name) and target.id == "basis"
                       for target in child.targets):
                continue
            value = child.value
            if not isinstance(value, ast.IfExp):
                errors.append("_run_bsec_rules: basis assignment must be a literal conditional")
                continue
            test_node = value.test
            if not (isinstance(test_node, ast.Compare)
                    and isinstance(test_node.left, ast.Name)
                    and test_node.left.id == "rule_id"
                    and len(test_node.comparators) == 1
                    and isinstance(test_node.comparators[0], ast.Constant)
                    and isinstance(test_node.comparators[0].value, str)):
                errors.append("_run_bsec_rules: basis condition must identify a literal rule_id")
                continue
            selected_id = test_node.comparators[0].value
            for rule_id, basis_node in (
                (selected_id, value.body),
                ("BSEC-OTHER", value.orelse),
            ):
                if not isinstance(basis_node, ast.Constant) or not isinstance(basis_node.value, str) or not basis_node.value.strip():
                    errors.append(f"_run_bsec_rules: {rule_id} statutory_basis must be a non-empty string literal")
                elif rule_id != "BSEC-OTHER":
                    basis_by_rule[rule_id] = basis_node.value.strip()
                else:
                    basis_by_rule["BSEC-002"] = basis_node.value.strip()
                    basis_by_rule["BSEC-003"] = basis_node.value.strip()
                    basis_by_rule["BSEC-004"] = basis_node.value.strip()

        candidate_ids = set()
        for child in ast.walk(bsec_function):
            if (isinstance(child, ast.Tuple) and child.elts
                    and isinstance(child.elts[0], ast.Constant)
                    and isinstance(child.elts[0].value, str)
                    and _is_rule_id(child.elts[0].value)):
                candidate_ids.add(child.elts[0].value)
        for rule_id in candidate_ids:
            basis = basis_by_rule.get(rule_id)
            if not basis:
                errors.append(f"_run_bsec_rules: missing literal statutory_basis for {rule_id}")
            else:
                result.setdefault(rule_id, set()).add(basis)

    # Director Form XII evaluation selects DIR-001 or DIR-002 through a
    # literal branch assignment before a shared ComplianceFlag constructor.
    # Resolve those literal alternatives explicitly rather than silently
    # dropping the cessation rule from the canonical ID set.
    director_function = next(
        (node for node in ast.walk(tree)
         if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
         and node.name == "_run_director_rules"),
        None,
    )
    if director_function is not None:
        director_rule_ids = set()
        for child in ast.walk(director_function):
            if not isinstance(child, ast.Assign):
                continue
            if not any(isinstance(target, ast.Name) and target.id == "rule_id"
                       for target in child.targets):
                continue
            if (isinstance(child.value, ast.Constant)
                    and isinstance(child.value.value, str)
                    and _is_rule_id(child.value.value)):
                director_rule_ids.add(child.value.value)

        director_bases = set()
        for child in ast.walk(director_function):
            if not isinstance(child, ast.Call) or _call_name(child.func) != "ComplianceFlag":
                continue
            keywords = {kw.arg: kw.value for kw in child.keywords if kw.arg is not None}
            if (isinstance(keywords.get("rule_id"), ast.Name)
                    and keywords["rule_id"].id == "rule_id"):
                basis_node = keywords.get("statutory_basis")
                if isinstance(basis_node, ast.Constant) and isinstance(basis_node.value, str):
                    director_bases.add(basis_node.value.strip())
                else:
                    errors.append("_run_director_rules: dynamic rule IDs require a literal statutory_basis")

        if director_rule_ids:
            if len(director_bases) != 1:
                errors.append(
                    "_run_director_rules: expected one shared literal statutory_basis "
                    f"for dynamic rule IDs {sorted(director_rule_ids)}; found {sorted(director_bases)}"
                )
            else:
                basis = next(iter(director_bases))
                for rule_id in director_rule_ids:
                    result.setdefault(rule_id, set()).add(basis)

    return result, errors


def _engine_ids():
    data, errors = _engine_rule_data()
    assert not errors, errors
    return set(data)


def _seed_rows():
    from scripts.seed_rules import ILRMF_RULES
    return ILRMF_RULES


def _normalise_basis(value: str) -> str:
    """Normalise punctuation and whitespace while preserving all legal tokens."""
    return " ".join(
        "".join(ch.casefold() if ch.isalnum() else " " for ch in value).split()
    )


def test_engine_rule_calls_are_structurally_parseable():
    data, errors = _engine_rule_data()
    assert not errors, errors
    assert data, "No ComplianceFlag rule definitions were found"
    assert "DIR-002" in data, "Director cessation rule must be included in engine parity"


def test_counts():
    assert len(_engine_ids()) == EXPECTED
    assert len(STATUTORY_RULE_REGISTRY) == EXPECTED
    assert len(STATUTORY_RESCUE_REGISTRY) == EXPECTED


def test_engine_registry_rescue_sets_equal():
    engine = _engine_ids()
    registry = set(STATUTORY_RULE_REGISTRY)
    rescue = set(STATUTORY_RESCUE_REGISTRY)
    assert engine == registry, {
        "engine_only": sorted(engine - registry),
        "registry_only": sorted(registry - engine),
    }
    assert engine == rescue, {
        "engine_only": sorted(engine - rescue),
        "rescue_only": sorted(rescue - engine),
    }


def test_seed_matches_engine_and_has_no_duplicates():
    rows = _seed_rows()
    seed_ids = [row["rule_id"] for row in rows]
    duplicates = [rule_id for rule_id, count in Counter(seed_ids).items() if count > 1]
    assert not duplicates, duplicates
    seed_set, engine_set = set(seed_ids), _engine_ids()
    assert seed_set == engine_set, {
        "seed_only": sorted(seed_set - engine_set),
        "engine_only": sorted(engine_set - seed_set),
    }



def test_every_unapproved_seed_rule_is_fail_closed():
    rows = _seed_rows()
    assert len(rows) == EXPECTED
    unsafe = [
        {
            "rule_id": row.get("rule_id"),
            "default_severity": row.get("default_severity"),
            "score_impact": row.get("score_impact"),
            "is_black_override": row.get("is_black_override"),
        }
        for row in rows
        if row.get("default_severity") != "NOT_EVALUATED"
        or row.get("score_impact") != 0
        or row.get("is_black_override") is not False
    ]
    assert not unsafe, (
        "Unapproved legal rules must never seed severity, score impact, "
        f"or BLACK overrides: {unsafe}"
    )




def test_rescue_registry_has_no_duplicate_trigger_ids():
    import ast

    path = ROOT / "canonical_architecture" / "statutory_rescue.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    source = next(
        node.value for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "_RESCUES"
                for target in node.targets)
        and isinstance(node.value, (ast.Tuple, ast.List))
    )
    trigger_ids = [
        call.args[1].value
        for call in source.elts
        if isinstance(call, ast.Call)
        and isinstance(call.func, ast.Name)
        and call.func.id == "RescueDef"
        and len(call.args) > 1
        and isinstance(call.args[1], ast.Constant)
        and isinstance(call.args[1].value, str)
    ]
    assert trigger_ids, "no literal RescueDef trigger IDs found"
    assert len(trigger_ids) == len(set(trigger_ids)), (
        "duplicate triggered_by IDs in _RESCUES source tuple"
    )


def test_inner_ids_match_registry_keys():
    bad_rules = [
        key for key, value in STATUTORY_RULE_REGISTRY.items()
        if getattr(value, "rule_id", None) != key
    ]
    assert not bad_rules, sorted(bad_rules)

    bad_rescue = [
        key for key, value in STATUTORY_RESCUE_REGISTRY.items()
        if getattr(value, "triggered_by", None) != key
    ]
    assert not bad_rescue, sorted(bad_rescue)


def test_canonical_registry_matches_seed_basis_and_requirement_for_all_rules():
    """The canonical registry, seed corpus and engine must not drift rule-by-rule."""
    rows = _seed_rows()
    assert len(rows) == EXPECTED
    seed_by_id = {row["rule_id"]: row for row in rows}
    assert set(seed_by_id) == set(STATUTORY_RULE_REGISTRY)

    mismatches = []
    for rule_id, row in seed_by_id.items():
        rule = STATUTORY_RULE_REGISTRY[rule_id]
        seed_basis = _normalise_basis(row["statutory_basis"])
        canonical_basis = _normalise_basis(rule.law)
        if seed_basis != canonical_basis or rule.requirement != row["description"]:
            mismatches.append({
                "rule_id": rule_id,
                "seed_basis": row["statutory_basis"],
                "canonical_basis": rule.law,
                "seed_requirement": row["description"],
                "canonical_requirement": rule.requirement,
            })
    assert not mismatches, mismatches


def test_seed_statutory_basis_matches_engine_call_for_same_rule():
    engine_data, errors = _engine_rule_data()
    assert not errors, errors

    mismatches = []
    for row in _seed_rows():
        rule_id = row["rule_id"]
        seed_basis = _normalise_basis((row.get("statutory_basis") or "").strip())
        engine_bases = {
            _normalise_basis(value) for value in engine_data.get(rule_id, set())
        }

        # Keep the existing compatibility rule (exact or contained basis), but
        # compare values attached to the same AST call rather than nearby text.
        if not seed_basis or not any(
            seed_basis == engine_basis
            or seed_basis in engine_basis
            or engine_basis in seed_basis
            for engine_basis in engine_bases
        ):
            mismatches.append({
                "rule_id": rule_id,
                "seed": row.get("statutory_basis"),
                "engine": sorted(engine_data.get(rule_id, set())),
            })

    assert not mismatches, mismatches

def test_inc005_imports_with_specific_foreign_investment_evidence():
    """INC-005's multi-document evidence mapping must survive registry import."""
    rule = STATUTORY_RULE_REGISTRY["INC-005"]
    assert set(rule.evidence_required) == {
        "INC-005:SUBSCRIPTION_OR_ALLOTMENT_RECORD",
        "INC-005:AD_BANK_ENCASHMENT_CERTIFICATE_OR_PERMITTED_FC_ACCOUNT_EVIDENCE",
        "INC-005:REMITTANCE_IDENTITY_AND_BANK_PROVENANCE",
        "INC-005:CURRENT_BANGLADESH_BANK_CIRCULAR_VERSION",
    }
    assert rule.severity.value == "NOT_EVALUATED"
    assert rule.score_impact == 0


def test_affected_agm_and_charge_provenance_matches_seed_engine_and_canonical():
    """The rules changed in this remediation must share one statutory basis."""
    engine_data, errors = _engine_rule_data()
    assert not errors, errors
    seed_by_id = {row["rule_id"]: row for row in _seed_rows()}
    affected = ("AGM-001", "AGM-002", "CAP-002", "CHG-001")

    for rule_id in affected:
        seed_basis = _normalise_basis(seed_by_id[rule_id]["statutory_basis"])
        canonical_basis = _normalise_basis(STATUTORY_RULE_REGISTRY[rule_id].law)
        engine_bases = {
            _normalise_basis(value) for value in engine_data.get(rule_id, set())
        }
        assert seed_basis == canonical_basis, {
            "rule_id": rule_id,
            "seed": seed_by_id[rule_id]["statutory_basis"],
            "canonical": STATUTORY_RULE_REGISTRY[rule_id].law,
        }
        assert seed_basis in engine_bases or any(
            seed_basis in basis or basis in seed_basis for basis in engine_bases
        ), {
            "rule_id": rule_id,
            "seed": seed_by_id[rule_id]["statutory_basis"],
            "engine": sorted(engine_data.get(rule_id, set())),
        }


def test_legal_reconciliation_registry_has_exact_unique_rule_coverage():
    """Catch missing IDs and duplicate literal keys before dict construction hides them."""
    source = (
        ROOT / "canonical_architecture" / "legal_reconciliation.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source, filename="canonical_architecture/legal_reconciliation.py")
    duplicates = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        seen = {}
        for key_node in node.keys:
            if not isinstance(key_node, ast.Constant) or not isinstance(key_node.value, str):
                continue
            key = key_node.value
            if key in seen:
                duplicates.append(
                    f"line {key_node.lineno}: duplicate key {key!r}; first at line {seen[key]}"
                )
            else:
                seen[key] = key_node.lineno
    assert not duplicates, "\\n".join(duplicates)
    assert set(LEGAL_RECONCILIATION) == set(STATUTORY_RULE_REGISTRY)
    assert len(LEGAL_RECONCILIATION) == EXPECTED


def test_unreconciled_canonical_rules_cannot_affect_score():
    """All unresolved statutory provisions stay NOT_EVALUATED with zero impact."""
    unsafe = [
        {
            "rule_id": rule_id,
            "provision": rule.provision,
            "severity": rule.severity.value,
            "score_impact": rule.score_impact,
        }
        for rule_id, rule in STATUTORY_RULE_REGISTRY.items()
        if rule.provision_status.value == "RECONCILE"
        and (rule.severity.value != "NOT_EVALUATED" or rule.score_impact != 0)
    ]
    assert not unsafe, unsafe


def test_every_provision_is_explicitly_unverified_until_counsel_signoff():
    """No TBD placeholder or implied legal approval; all candidates remain non-scoring."""
    unsafe = []
    for rule_id, rule in STATUTORY_RULE_REGISTRY.items():
        if (
            not rule.provision.startswith("UNVERIFIED CANDIDATE — ")
            or "TBD" in rule.provision.upper()
            or rule.provision_status.value != "RECONCILE"
            or rule.severity.value != "NOT_EVALUATED"
            or rule.score_impact != 0
        ):
            unsafe.append({
                "rule_id": rule_id,
                "provision": rule.provision,
                "status": rule.provision_status.value,
                "severity": rule.severity.value,
                "score_impact": rule.score_impact,
            })
    assert not unsafe, unsafe


def test_legal_reconciliation_checklist_covers_all_85_unverified_rules():
    path = ROOT / "docs" / "LEGAL_RECONCILIATION_CHECKLIST.csv"
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == EXPECTED
    assert {row["Rule ID"] for row in rows} == set(STATUTORY_RULE_REGISTRY)
    assert all(row["Status"] == "RECONCILE" for row in rows)
    assert all(row["Legal Team Sign-Off"] == "PENDING" for row in rows)
    assert all(row["Candidate Provision"].startswith("UNVERIFIED CANDIDATE — ") for row in rows)


def test_counsel_docket_covers_all_85_rules_and_matches_unverified_candidates():
    path = ROOT / "docs" / "legal" / "85_RULE_COUNSEL_VALIDATION_DOCKET.md"
    content = path.read_text(encoding="utf-8")
    headings = list(re.finditer(r"^### ([A-Z]{2,5}-\\d{3}) —", content, re.MULTILINE))
    ids = [match.group(1) for match in headings]
    assert len(ids) == EXPECTED
    assert set(ids) == set(STATUTORY_RULE_REGISTRY)

    for index, match in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(content)
        block = content[match.start():end]
        rule = STATUTORY_RULE_REGISTRY[match.group(1)]
        assert f"- **Catalogue anchor:** {rule.law}" in block
        assert (
            "- **Current canonical provision candidate (unverified):** "
            f"{rule.provision}"
        ) in block
        assert "OPEN — NOT COUNSEL VALIDATED" in block
