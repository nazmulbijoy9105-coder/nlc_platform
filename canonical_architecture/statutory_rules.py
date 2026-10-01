"""
NLC Layer 2: Statutory Rule Registry - WHAT Bangladesh law requires.
Every provision is RECONCILE (unverified) until checked against the legal
source. Do not treat any section number here as frozen.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Tuple


class RuleState(str, Enum):
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    CONDITIONAL = "CONDITIONAL"      # defined; no evaluator emits it yet
    CONTRADICTORY = "CONTRADICTORY"


class ProvisionStatus(str, Enum):
    RECONCILE = "RECONCILE"
    VERIFIED = "VERIFIED"


class Severity(str, Enum):
    RED = "RED"
    YELLOW = "YELLOW"


_BASE_STATES = (RuleState.COMPLIANT, RuleState.NON_COMPLIANT,
                RuleState.UNKNOWN, RuleState.CONTRADICTORY)
_COMMON_INVARIANTS = ("R-001", "R-002", "R-003", "R-005", "R-007", "R-008",
                      "R-009", "R-010", "R-012", "R-014", "R-018", "R-019")


@dataclass(frozen=True)
class StatutoryRule:
    rule_id: str
    legal_domain: str
    law: str
    requirement: str
    provision: str
    provision_status: ProvisionStatus
    authority: str
    evidence_required: Tuple[str, ...]
    severity: Severity
    score_impact: int
    applies_if: Optional[str] = None      # company fact that must be True, else NOT_APPLICABLE
    exceptions: Tuple[str, ...] = ()      # company facts that, if True, make it NOT_APPLICABLE

    @property
    def evaluation_states(self) -> Tuple[RuleState, ...]:
        if self.applies_if or self.exceptions:
            return _BASE_STATES + (RuleState.NOT_APPLICABLE,)
        return _BASE_STATES

    @property
    def invariants(self) -> Tuple[str, ...]:
        extra = ("R-004",) if self.exceptions else ()
        return tuple(sorted(set(_COMMON_INVARIANTS + extra)))


_RULES = (
    StatutoryRule(
        "INC-001", "Corporate", "Companies Act 1994",
        "File Memorandum and Articles of Association", "Section 11",
        ProvisionStatus.RECONCILE, "RJSC", ("MOA_FILED", "AOA_FILED"),
        Severity.RED, 15),
    StatutoryRule(
        "AR-001", "Corporate", "Companies Act 1994",
        "Statutory annual filing obligation (Schedule X)", "Section 36",
        ProvisionStatus.RECONCILE, "RJSC",
        ("MEMBER_SHARE_DATA", "AGM_INFORMATION", "FILING_EVIDENCE"),
        Severity.YELLOW, 10, exceptions=("DORMANT_STRIKE_OFF",)),
    StatutoryRule(
        "TAX-001", "Tax", "Income Tax Act 2023",
        "Obtain Tax Identification Number (TIN)",
        "UNIDENTIFIED (NBR instrument to be located)",
        ProvisionStatus.RECONCILE, "NBR", ("TIN_CERTIFICATE",),
        Severity.RED, 10),
    StatutoryRule(
        "LBR-001", "Labour", "Labour Act 2006",
        "Factory license obtained", "Section 326",
        ProvisionStatus.RECONCILE, "LABOUR_DEPT", ("FACTORY_LICENSE",),
        Severity.RED, 10, applies_if="IS_MANUFACTURING",
        exceptions=("NON_FACTORY_OPERATIONS",)),
    StatutoryRule(
        "TL-001", "Local Authority", "Local authority trade licensing (instrument to be identified)",
        "Valid trade license from local authority", "UNIDENTIFIED",
        ProvisionStatus.RECONCILE, "CITY_CORPORATION", ("TRADE_LICENSE",),
        Severity.YELLOW, 5),
    StatutoryRule(
        "DIR-005", "Corporate", "Companies Act 1994",
        "Maintain statutory register mapped to DIR-005 (mapping under review)",
        "Section 97", ProvisionStatus.RECONCILE, "INTERNAL",
        ("REGISTER_DIR_005",), Severity.YELLOW, 5),
    StatutoryRule(
        "DIR-006", "Corporate", "Companies Act 1994",
        "Maintain statutory register mapped to DIR-006 (mapping under review)",
        "Section 98", ProvisionStatus.RECONCILE, "INTERNAL",
        ("REGISTER_DIR_006",), Severity.YELLOW, 5),
)

STATUTORY_RULE_REGISTRY: Dict[str, StatutoryRule] = {r.rule_id: r for r in _RULES}
if len(STATUTORY_RULE_REGISTRY) != len(_RULES):
    raise RuntimeError("duplicate rule_id in statutory rule registry")


def get_rule(rule_id: str) -> Optional[StatutoryRule]:
    return STATUTORY_RULE_REGISTRY.get(rule_id)
