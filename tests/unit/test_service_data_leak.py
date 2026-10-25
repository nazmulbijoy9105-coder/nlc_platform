import pytest
from datetime import date
from app.services.company_service import CompanyService
from app.rule_engine.engine import NLCRuleEngine, Severity, RuleState

@pytest.mark.asyncio
async def test_unverified_zero_director_records_do_not_trigger_inc003_and_agm_unknown(db):
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
    
    # An empty NLC director-record collection is not RJSC-verified evidence
    # that the company legally has zero directors.
    assert profile.current_director_count == 0
    assert profile.directors_verified is False
    assert "INC-003" not in flag_ids
    assert "ESC-003" not in flag_ids
    
    # AGM-001 should fire, but as UNKNOWN (0 points), not as a hard violation
    agm_flags = [f for f in output.flags if f.rule_id == "AGM-001"]
    assert agm_flags, "AGM-001 should have fired as UNKNOWN"
    assert agm_flags[0].state == RuleState.UNKNOWN
    assert agm_flags[0].score_impact == 0
    
    # Other findings may still affect the risk band.
    # Missing AGM evidence remains UNKNOWN and has zero score impact.
    # INC-003 and ESC-003 require a verified director-count deficiency.
