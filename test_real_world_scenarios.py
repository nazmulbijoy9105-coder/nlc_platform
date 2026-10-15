"""Real-world compliance scenarios — tests against actual RJSC situations."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import date, timedelta
from app.rule_engine.engine import CompanyProfile, NLCRuleEngine, Severity, ShareTransfer

today = date.today()
engine = NLCRuleEngine()

def run(name, company):
    result = engine.evaluate(company, today=today)
    flags = result.flags
    score = result.score_breakdown
    flag_ids = [f.rule_id for f in flags]
    print(f"\n{'='*60}")
    print(f"SCENARIO: {name}")
    print(f"  Score: {score.final_score} | Band: {score.risk_band} | Exposure: {score.exposure_band}")
    print(f"  Override: {score.override_applied} | Coverage: {score.coverage:.0%}")
    print(f"  Flags ({len(flags)}): {', '.join(flag_ids) if flag_ids else 'NONE'}")
    if score.override_reason:
        print(f"  Reason: {score.override_reason}")
    return result

# ── Scenario 1: Brand new company (30 days old, all filings done) ──
new_company = CompanyProfile(
    company_id="S1", company_name="Newly Incorporated Ltd",
    incorporation_date=today - timedelta(days=30),
    agm_count=0, current_director_count=3,
    moa_aoa_filed=True, form_iii_filed=True,
    first_auditor_appointed=True,
    tin_obtained=True, vat_registered=False,
    tax_return_filed_for_current_fy=True,
    advance_tax_q1_paid=True, advance_tax_q2_paid=True,
    advance_tax_q3_paid=True, advance_tax_q4_paid=True,
    trade_license_obtained=True, trade_license_expiry=today + timedelta(days=365),
    paid_up_capital_bdt=1000000, authorized_capital_bdt=5000000,
    register_of_directors_interests=True, register_of_contracts=True,
    factory_license_obtained=True,
    last_audit_signed_date=today, last_return_filed_year=today.year,
)
r1 = run("Brand new company (30 days, all filings done)", new_company)
assert r1.score_breakdown.final_score == 100, f"Should score 100, got {r1.score_breakdown.final_score}"
assert r1.score_breakdown.risk_band == Severity.GREEN, f"Should be GREEN, got {r1.score_breakdown.risk_band}"
print("  [PASS] Score 100, GREEN")

# ── Scenario 2: 2-year-old company, no AGM ever held ──
no_agm = CompanyProfile(
    company_id="S2", company_name="No AGM Corp",
    incorporation_date=today - timedelta(days=730),
    agm_count=0, current_director_count=3,
    moa_aoa_filed=True, form_iii_filed=True,
    first_auditor_appointed=True,
    tin_obtained=True, vat_registered=True, vat_annual_return_filed_for_fy=True,
    tax_return_filed_for_current_fy=True,
    advance_tax_q1_paid=True, advance_tax_q2_paid=True,
    advance_tax_q3_paid=True, advance_tax_q4_paid=True,
    trade_license_obtained=True, trade_license_expiry=today + timedelta(days=90),
    paid_up_capital_bdt=1000000, authorized_capital_bdt=5000000,
    register_of_directors_interests=True, register_of_contracts=True,
    factory_license_obtained=True,
    last_audit_signed_date=today, last_return_filed_year=today.year,
)
r2 = run("2-year-old company, no AGM ever held", no_agm)
assert "AGM-001" in [f.rule_id for f in r2.flags], "AGM-001 should fire"
agm001 = [f for f in r2.flags if f.rule_id == "AGM-001"][0]
assert agm001.severity == Severity.BLACK, f"AGM-001 should be BLACK, got {agm001.severity}"
assert r2.score_breakdown.final_score == 0, "Should score 0"
print("  [PASS] AGM-001 BLACK, score 0")

# ── Scenario 3: 3 unfiled annual returns ──
backlog = CompanyProfile(
    company_id="S3", company_name="Return Backlog Ltd",
    incorporation_date=today - timedelta(days=1460),
    agm_count=4, last_agm_date=today - timedelta(days=400),
    current_director_count=3,
    moa_aoa_filed=True, form_iii_filed=True,
    first_auditor_appointed=True,
    tin_obtained=True, vat_registered=True, vat_annual_return_filed_for_fy=True,
    tax_return_filed_for_current_fy=True,
    advance_tax_q1_paid=True, advance_tax_q2_paid=True,
    advance_tax_q3_paid=True, advance_tax_q4_paid=True,
    trade_license_obtained=True, trade_license_expiry=today + timedelta(days=90),
    paid_up_capital_bdt=1000000, authorized_capital_bdt=5000000,
    register_of_directors_interests=True, register_of_contracts=True,
    factory_license_obtained=True,
    last_audit_signed_date=today, last_return_filed_year=today.year - 4,
    unfiled_returns_count=3,
)
r3 = run("3 unfiled annual returns", backlog)
assert "AR-003" in [f.rule_id for f in r3.flags], "AR-003 should fire"
ar003 = [f for f in r3.flags if f.rule_id == "AR-003"][0]
assert ar003.severity == Severity.BLACK, "AR-003 should be BLACK"
print("  [PASS] AR-003 BLACK fires")

# ── Scenario 4: Void share transfer ──
void_transfer = CompanyProfile(
    company_id="S4", company_name="Void Transfer Ltd",
    incorporation_date=today - timedelta(days=365),
    agm_count=1, last_agm_date=today - timedelta(days=100),
    agm_held_this_cycle=True, members_present_at_agm=5,
    agm_minutes_prepared=True, audit_complete=True,
    auditor_reappointed_at_agm=True, first_auditor_appointed=True,
    annual_return_filed=True, current_director_count=3,
    moa_aoa_filed=True, form_iii_filed=True,
    tin_obtained=True, vat_registered=True, vat_annual_return_filed_for_fy=True,
    tax_return_filed_for_current_fy=True,
    advance_tax_q1_paid=True, advance_tax_q2_paid=True,
    advance_tax_q3_paid=True, advance_tax_q4_paid=True,
    trade_license_obtained=True,
    register_of_directors_interests=True, register_of_contracts=True,
    factory_license_obtained=True,
    last_audit_signed_date=today, last_return_filed_year=today.year,
    aoa_transfer_restriction=True,
    share_transfers=[ShareTransfer(
        transfer_id="T1", transfer_date=today - timedelta(days=30),
        instrument_recorded=True, stamp_duty_paid=True,
        board_approval_obtained=False, share_register_updated=False,
        form_117_filed=True,
    )],
    paid_up_capital_bdt=1000000, authorized_capital_bdt=5000000,
)
r4 = run("Void share transfer", void_transfer)
tr_flags = [f.rule_id for f in r4.flags if f.rule_id.startswith("TR-")]
assert "TR-005" in tr_flags, "TR-005 should fire"
assert "TR-003" not in tr_flags, "TR-003 should NOT fire"
assert "TR-004" not in tr_flags, "TR-004 should NOT fire"
print("  [PASS] TR-005 fires, TR-003/TR-004 suppressed")

# ── Scenario 5: Company on strike-off list ──
strike_off = CompanyProfile(
    company_id="S5", company_name="Strike-Off Corp",
    incorporation_date=today - timedelta(days=1825),
    agm_count=5, last_agm_date=today - timedelta(days=200),
    current_director_count=3,
    moa_aoa_filed=True, form_iii_filed=True,
    first_auditor_appointed=True, annual_return_filed=True,
    tin_obtained=True, vat_registered=True, vat_annual_return_filed_for_fy=True,
    tax_return_filed_for_current_fy=True,
    advance_tax_q1_paid=True, advance_tax_q2_paid=True,
    advance_tax_q3_paid=True, advance_tax_q4_paid=True,
    trade_license_obtained=True,
    register_of_directors_interests=True, register_of_contracts=True,
    factory_license_obtained=True,
    last_audit_signed_date=today, last_return_filed_year=today.year,
    on_rjsc_strike_off_list=True, rjsc_status="STRUCK_OFF",
    paid_up_capital_bdt=1000000, authorized_capital_bdt=5000000,
)
r5 = run("Company on RJSC strike-off list", strike_off)
assert "ESC-002" in [f.rule_id for f in r5.flags], "ESC-002 should fire"
esc002 = [f for f in r5.flags if f.rule_id == "ESC-002"][0]
assert esc002.is_black_override == True, "ESC-002 should be override"
assert r5.score_breakdown.final_score == 0, "Should score 0"
print("  [PASS] ESC-002 BLACK override, score 0")

# ── Scenario 6: Routine RED flag, no BLACK ──
routine_red = CompanyProfile(
    company_id="S6", company_name="Late Auditor Ltd",
    incorporation_date=today - timedelta(days=400),
    agm_count=1, last_agm_date=today - timedelta(days=100),
    current_director_count=3,
    moa_aoa_filed=True, form_iii_filed=True,
    first_auditor_appointed=False,
    annual_return_filed=True,
    tin_obtained=True, vat_registered=True, vat_annual_return_filed_for_fy=True,
    tax_return_filed_for_current_fy=True,
    advance_tax_q1_paid=True, advance_tax_q2_paid=True,
    advance_tax_q3_paid=True, advance_tax_q4_paid=True,
    trade_license_obtained=True,
    register_of_directors_interests=True, register_of_contracts=True,
    factory_license_obtained=True,
    last_audit_signed_date=today, last_return_filed_year=today.year,
    paid_up_capital_bdt=1000000, authorized_capital_bdt=5000000,
)
r6 = run("Routine RED flag (AUD-001, no BLACK)", routine_red)
assert "AUD-001" in [f.rule_id for f in r6.flags], "AUD-001 should fire"
assert r6.score_breakdown.risk_band == Severity.RED, f"Should be RED, got {r6.score_breakdown.risk_band}"
print("  [PASS] RED flag escalates band to RED")

print(f"\n{'='*60}")
print("ALL REAL-WORLD SCENARIOS PASSED")
print(f"{'='*60}")
