"""
app/rule_engine/__init__.py
Package wrapper - exports NLCRuleEngine and dataclasses.
"""
from app.rule_engine.engine import (
    CompanyProfile,
    ComplianceFlag,
    DirectorChange,
    EngineOutput,
    LifecycleStage,
    NLCRuleEngine,
    ScoreBreakdown,
    ShareTransfer,
)

__all__ = [
    "CompanyProfile",
    "ComplianceFlag",
    "DirectorChange",
    "EngineOutput",
    "LifecycleStage",
    "NLCRuleEngine",
    "ScoreBreakdown",
    "ShareTransfer",
]
