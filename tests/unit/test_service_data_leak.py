import pytest
from datetime import date
from app.services.company_service import CompanyService
from app.rule_engine.engine import NLCRuleEngine, Severity, RuleState

@pytest.mark.asyncio
async def test_missing_agm_and_directors_does_not_trigger_black(db):
    company = await CompanyService(db).create_company(
        registration_number="TEST-NO-AGM-01",
        company_name="No AGM Co",
        company_type="PRIVATE_LIMITED",
        incorporation_date=date(2020, 1, 1),
        financial_year_end=date(2020, 12, 31),
    )
    
    profile_dict = await CompanyService(db).build_company_profile(company.id)
    assert profile_dict is not None
    
    engine = NLCRuleEngine()
    from app.rule_engine.engine import CompanyProfile
    profile = CompanyProfile(**profile_dict)
    
    output = engine.evaluate(profile, today=date(2026, 10, 1))
    
    flag_ids = [f.rule_id for f in output.flags]
    
    assert "INC-003" not in flag_ids, "INC-003 fired on missing directors"
    assert "ESC-003" not in flag_ids, "ESC-003 fired on missing data"
    
    # AGM-001 should fire, but as UNKNOWN (0 points), not as a hard violation
    agm_flags = [f for f in output.flags if f.rule_id == "AGM-001"]
    assert agm_flags, "AGM-001 should have fired as UNKNOWN"
    assert agm_flags[0].state == RuleState.UNKNOWN
    assert agm_flags[0].score_impact == 0
    
    # NOTE: Risk band may be RED due to other DB defaults (moa_aoa_filed=False),
    # but the key assertion is that AGM-001 and INC-003 do not fire as BLACK violations.
