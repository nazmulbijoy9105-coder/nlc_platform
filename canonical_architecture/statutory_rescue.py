"""
NLC Layer 3: Statutory Rescue Registry - WHAT must be corrected when a rule is
breached, overdue, unsupported or unknown. Derived only from findings (R-014).
Deadlines are RECONCILE (unverified) and not to be presented as settled law.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Iterable, List, Tuple

from .evaluator import Finding
from .statutory_rules import (ProvisionStatus, RuleState, Severity,
                              STATUTORY_RULE_REGISTRY)


class RescueState(str, Enum):
    NOT_REQUIRED = "NOT_REQUIRED"
    IDENTIFIED = "IDENTIFIED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    BLOCKED = "BLOCKED"
    WAITING_EVIDENCE = "WAITING_EVIDENCE"
    FAILED = "FAILED"
    SUPERSEDED = "SUPERSEDED"


class RescueMode(str, Enum):
    REMEDIATE = "REMEDIATE"                    # established breach
    ESTABLISH_EVIDENCE = "ESTABLISH_EVIDENCE"  # UNKNOWN / CONTRADICTORY: no penalty


RESCUE_TRIGGER_STATES = frozenset({RuleState.NON_COMPLIANT, RuleState.CONDITIONAL,
                                   RuleState.CONTRADICTORY, RuleState.UNKNOWN})


@dataclass(frozen=True)
class RescueDef:
    rescue_id: str
    triggered_by: str
    objective: str
    statutory_actions: Tuple[str, ...]
    authority: str
    service_workflow: str
    deadline_basis: str
    deadline_status: ProvisionStatus
    notification_required: bool
    verification: str
    prerequisites: Tuple[str, ...] = ()

    @property
    def closure_condition(self) -> str:
        return f"{self.triggered_by} == COMPLIANT and {self.verification} recorded"


_R = ProvisionStatus.RECONCILE

_RESCUES = (
    RescueDef("INC-RESCUE-001", "INC-001", "File missing MOA/AOA",
              ("draft MOA/AOA", "obtain subscriber signatures", "submit to RJSC",
               "capture acknowledgement", "verify closure"),
              "RJSC", "RJSC_FILING", "IMMEDIATE", _R, True, "RJSC_CERTIFICATE"),
    RescueDef("AR-RESCUE-001", "AR-001", "Regularize statutory annual filing deficiency",
              ("reconstruct missing information", "prepare statutory filing",
               "obtain required approval/signature", "submit to authority",
               "capture acknowledgement", "verify closure"),
              "RJSC", "RJSC_FILING", "21_DAYS_FROM_AGM", _R, True,
              "FILING_ACKNOWLEDGEMENT", prerequisites=("AGM_HELD",)),
    RescueDef("TAX-RESCUE-001", "TAX-001", "Obtain TIN from NBR",
              ("apply for TIN via NBR portal", "verify entity details",
               "capture TIN certificate", "verify closure"),
              "NBR", "NBR_TAX", "IMMEDIATE", _R, True, "TIN_CERTIFICATE"),
    RescueDef("LBR-RESCUE-001", "LBR-001", "Obtain factory license",
              ("prepare factory license application", "submit to labour authority",
               "capture license", "verify closure"),
              "LABOUR_DEPT", "LABOUR_DEPT", "IMMEDIATE", _R, True, "FACTORY_LICENSE"),
    RescueDef("TL-RESCUE-001", "TL-001", "Obtain or renew trade license",
              ("apply or renew with local authority", "capture license", "verify closure"),
              "CITY_CORPORATION", "CITY_CORPORATION", "IMMEDIATE", _R, True, "TRADE_LICENSE"),
    RescueDef("DIR5-RESCUE-001", "DIR-005", "Establish or update DIR-005 register",
              ("prepare register", "obtain required signatures",
               "capture register evidence", "verify closure"),
              "INTERNAL", "AUDIT_LEGAL", "IMMEDIATE", _R, True, "REGISTER_DIR_005"),
    RescueDef("DIR6-RESCUE-001", "DIR-006", "Establish or update DIR-006 register",
              ("prepare register", "obtain required signatures",
               "capture register evidence", "verify closure"),
              "INTERNAL", "AUDIT_LEGAL", "IMMEDIATE", _R, True, "REGISTER_DIR_006"),
)

STATUTORY_RESCUE_REGISTRY: Dict[str, RescueDef] = {r.triggered_by: r for r in _RESCUES}
if len(STATUTORY_RESCUE_REGISTRY) != len(_RESCUES):
    raise RuntimeError("duplicate triggered_by in rescue registry")


@dataclass(frozen=True)
class RescueStep:
    rescue_id: str
    triggered_by: str
    mode: RescueMode
    state: RescueState
    actions: Tuple[str, ...]
    authority: str
    service: str
    deadline_basis: str
    deadline_status: ProvisionStatus
    notification_required: bool
    verification: str
    closure_condition: str
    blocked_by: Tuple[str, ...] = ()


@dataclass(frozen=True)
class RescuePlan:
    steps: Tuple[RescueStep, ...]
    unmapped: Tuple[str, ...]   # R-013: surfaced for review, never auto-rescued


def _rank(rule_id: str) -> int:
    rule = STATUTORY_RULE_REGISTRY.get(rule_id)
    if rule is None:
        return 2
    return 0 if rule.severity is Severity.RED else 1


def get_rescue_plan(findings: Iterable[Finding],
                    satisfied_prerequisites=frozenset()) -> RescuePlan:
    """R-012/R-013/R-014/R-015."""
    active: List[Finding] = sorted(
        (f for f in findings if f.state in RESCUE_TRIGGER_STATES),
        key=lambda f: (_rank(f.rule_id), f.rule_id))
    steps: List[RescueStep] = []
    unmapped: List[str] = []
    for f in active:
        rd = STATUTORY_RESCUE_REGISTRY.get(f.rule_id)
        if rd is None:
            unmapped.append(f.rule_id)
            continue
        rule = STATUTORY_RULE_REGISTRY[f.rule_id]
        evidence = ", ".join(rule.evidence_required)
        if f.state in (RuleState.UNKNOWN, RuleState.CONTRADICTORY):
            verb = ("resolve conflicting evidence: " if f.state is RuleState.CONTRADICTORY
                    else "collect and verify required evidence: ")
            steps.append(RescueStep(
                rd.rescue_id, f.rule_id, RescueMode.ESTABLISH_EVIDENCE,
                RescueState.WAITING_EVIDENCE, (verb + evidence,), rd.authority,
                rd.service_workflow, "NONE", rd.deadline_status,
                rd.notification_required, rd.verification, rd.closure_condition))
            continue
        blocked = tuple(p for p in rd.prerequisites if p not in satisfied_prerequisites)
        steps.append(RescueStep(
            rd.rescue_id, f.rule_id, RescueMode.REMEDIATE,
            RescueState.BLOCKED if blocked else RescueState.IDENTIFIED,
            rd.statutory_actions, rd.authority, rd.service_workflow,
            rd.deadline_basis, rd.deadline_status, rd.notification_required,
            rd.verification, rd.closure_condition, blocked))
    return RescuePlan(tuple(steps), tuple(unmapped))


def can_close(rule_state: RuleState, verification_recorded: bool) -> bool:
    """R-019: close only on verified evidence that yields COMPLIANT."""
    return rule_state is RuleState.COMPLIANT and verification_recorded
