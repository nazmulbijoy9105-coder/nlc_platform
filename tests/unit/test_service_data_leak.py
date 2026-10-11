import pytest
from datetime import date
from app.services.company_service import CompanyService
from app.rule_engine.engine import NLCRuleEngine, Severity, RuleState

@pytest.mark.asyncio
async def test_missing_agm_and_directors_does_not_trigger_black(db_session):
    """
    Fix 5: A company with no AGM or Director records must not trigger BLACK flags.
    The service must pass None, and the engine must evaluate as UNKNOWN.
    """
    # 1. Create a company with no AGMs and no Directors
    company = await CompanyService(db_session).create_company(
        registration_number="TEST-NO-AGM-01",
        company_name="No AGM Co",
        company_type="PRIVATE_LIMITED",
        incorporation_date=date(2020, 1, 1),
        financial_year_end=date(2020, 12, 31),
    )
    
    # 2. Build profile via the service
    profile_dict = await CompanyService(db_session).build_company_profile(company.id)
    assert profile_dict is not None
    
    # 3. Evaluate
    engine = NLCRuleEngine()
    from app.rule_engine.engine import CompanyProfile
    profile = CompanyProfile(**profile_dict)
    
    output = engine.evaluate(profile, today=date(2026, 10, 1))
    
    # 4. Assertions: No BLACK, no ESC flags, band NOT_EVALUATED
    flag_ids = [f.rule_id for f in output.flags]
    
    assert "INC-003" not in flag_ids, "INC-003 fired on missing directors"
    assert "AGM-001" not in flag_ids, "AGM-001 fired on missing AGM history"
    assert "ESC-003" not in flag_ids, "ESC-003 fired on missing data"
    
    assert output.score_breakdown.risk_band == Severity.NOT_EVALUATED, "Band should be NOT_EVALUATED for missing data"
    
    # Check that AGM-001 is UNKNOWN if it fired
    agm_flags = [f for f in output.flags if f.rule_id == "AGM-001"]
    for f in agm_flags:
        assert f.state == RuleState.UNKNOWN
        assert f.score_impact == 0
