"""
app/rule_engine/__init__.py
Package wrapper - exports NLCRuleEngine and dataclasses.
"""
from app.rule_engine.engine import (
    NLCRuleEngine,
    CompanyProfile,
    EngineOutput,
    ScoreBreakdown,
    ComplianceFlag,
    DirectorChange,
    ShareTransfer,
    LifecycleStage,
)

__all__ = [
    "NLCRuleEngine", "CompanyProfile", "EngineOutput",
    "ScoreBreakdown", "ComplianceFlag", "DirectorChange",
    "ShareTransfer", "LifecycleStage",
]
