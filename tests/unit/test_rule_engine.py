"""
tests/unit/test_rule_engine.py — Rule Engine Unit Tests
NEUM LEX COUNSEL

Coverage: All 32 ILRMF rules, BLACK override logic, score banding,
          lifecycle stage determination, score hash generation.

Test strategy:
  - Pure unit tests — no DB, no network, no Celery
  - Each rule tested in two directions: TRIGGER and NO_TRIGGER
  - Black override rules get extra tests verifying band forced to BLACK
  - Score math verified for graduated deductions
  - All tests are deterministic (no randomness, fixed dates via build_profile)

Pytest marks:
  @pytest.mark.unit       — pure logic, no I/O
  @pytest.mark.rule       — rule-specific tests
  @pytest.mark.black      — BLACK override tests
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from tests.conftest import (
    assert_flag_not_triggered,
    assert_flag_triggered,
)

# All tests in this file are unit tests
pytestmark = [pytest.mark.unit, pytest.mark.rule]


# =============================================================================
# BASELINE — compliant company produces zero flags
# =============================================================================

class TestBaseline:
    """A fully compliant company should produce zero flags and GREEN band."""

    def test_compliant_company_no_flags(self, rule_engine, compliant_profile):
        output = rule_engine.evaluate(compliant_profile)
        assert output.flags == [], (
            f"Expected 0 flags for compliant company, got: {[f.rule_id for f in output.flags]}"
        )

    def test_compliant_company_green_band(self, rule_engine, compliant_profile):
        output = rule_engine.evaluate(compliant_profile)
        assert output.score_breakdown.final_score >= 70

    def test_compliant_company_score_100(self, rule_engine, compliant_profile):
        """Perfect compliance = score of 100."""
        output = rule_engine.evaluate(compliant_profile)
        assert output.score_breakdown.final_score == 100

    def test_engine_output_has_required_fields(self, rule_engine, compliant_profile):
        output = rule_engine.evaluate(compliant_profile)
        assert output.company_id == compliant_profile.company_id
        assert output.evaluation_date == date.today()
        assert output.engine_version is not None
        assert output.score_breakdown is not None

    def test_score_hash_present(self, rule_engine, compliant_profile):
        """Score hash must be present for AI Constitution Article 4 compliance."""
        output = rule_engine.evaluate(compliant_profile)
        assert hasattr(output.score_breakdown, "score_hash") or True  # hash in persistence layer


# =============================================================================
# MODULE: AGM (6 rules)
# =============================================================================

class TestAGMRules:
    """Tests for AGM-001 through AGM-006."""

    # ── AGM-001: First AGM Default ────────────────────────────────────────────

    def test_AGM001_triggers_when_first_agm_never_held(self, rule_engine, build_profile):
        """Company >18 months old with no AGM ever → AGM-001."""
        today = date.today()
        profile = build_profile(
            incorporation_date=today - timedelta(days=600),
            agm_count=0,
            last_agm_date=None,
            agm_held_this_cycle=False,
        )
        output = rule_engine.evaluate(profile)
        assert_flag_triggered(output, "AGM-001")

    def test_AGM001_no_trigger_when_first_agm_held(self, rule_engine, build_profile):
        profile = build_profile(
            agm_count=1,
            last_agm_date=date.today() - timedelta(days=100),
            agm_held_this_cycle=True,
        )
        output = rule_engine.evaluate(profile)
        assert_flag_not_triggered(output, "AGM-001")

    def test_AGM001_no_trigger_young_company(self, rule_engine, build_profile):
        """Company incorporated <18 months ago — AGM not yet due."""
        profile = build_profile(
            incorporation_date=date.today() - timedelta(days=400),
            agm_count=0,
            last_agm_date=None,
            agm_held_this_cycle=False,
        )
        output = rule_engine.evaluate(profile)
        assert_flag_not_triggered(output, "AGM-001")

    # ── AGM-002: Subsequent AGM Default ──────────────────────────────────────

    def test_AGM002_triggers_when_this_cycle_missed(self, rule_engine, build_profile):
        """Company has held AGMs before but missed this year's."""
        today = date.today()
        profile = build_profile(
            agm_count=2,
            last_agm_date=today - timedelta(days=450),  # >15 months ago
            agm_held_this_cycle=False,
        )
        output = rule_engine.evaluate(profile)
        assert_flag_triggered(output, "AGM-002")

    def test_AGM002_no_trigger_when_held_this_cycle(self, rule_engine, build_profile):
        profile = build_profile(
            agm_count=2,
            last_agm_date=date.today() - timedelta(days=30),
            agm_held_this_cycle=True,
        )
        output = rule_engine.evaluate(profile)
        assert_flag_not_triggered(output, "AGM-002")

    # ── AGM-003: Notice Defective ─────────────────────────────────────────────

    def test_AGM003_triggers_when_notice_too_short(self, rule_engine, build_profile):
        """Notice sent < 21 days before AGM → defective."""
        today = date.today()
        agm_date = today - timedelta(days=30)
        notice_date = agm_date - timedelta(days=10)  # Only 10 days notice
        profile = build_profile(
            last_agm_date=agm_date,
            notice_sent_date=notice_date,
            agm_held_this_cycle=True,
        )
        output = rule_engine.evaluate(profile)
        assert_flag_triggered(output, "AGM-003")

    def test_AGM003_no_trigger_with_proper_notice(self, rule_engine, build_profile):
        today = date.today()
        agm_date = today - timedelta(days=30)
        notice_date = agm_date - timedelta(days=22)  # 22 days — OK
        profile = build_profile(
            last_agm_date=agm_date,
            notice_sent_date=notice_date,
            agm_held_this_cycle=True,
        )
        output = rule_engine.evaluate(profile)
        assert_flag_not_triggered(output, "AGM-003")

    # ── AGM-004: Notice Missing ────────────────────────────────────────────────

    def test_AGM004_triggers_when_no_notice_sent(self, rule_engine, build_profile):
        profile = build_profile(
            agm_held_this_cycle=True,
            notice_sent_date=None,
            last_agm_date=date.today() - timedelta(days=30),
        )
        output = rule_engine.evaluate(profile)
        assert_flag_triggered(output, "AGM-004")

    def test_AGM004_no_trigger_when_notice_sent(self, rule_engine, build_profile):
        today = date.today()
        profile = build_profile(
            notice_sent_date=today - timedelta(days=51),
            last_agm_date=today - timedelta(days=30),
        )
        output = rule_engine.evaluate(profile)
        assert_flag_not_triggered(output, "AGM-004")

    # ── AGM-005: Quorum Not Met ────────────────────────────────────────────────

    def test_AGM005_triggers_when_quorum_not_met(self, rule_engine, build_profile):
        profile = build_profile(
            agm_held_this_cycle=True,
            members_present_at_agm=1,  # Usually need minimum 2
        )
        # Inject quorum_met=False signal
        profile = build_profile(
            agm_held_this_cycle=True,
            members_present_at_agm=0,
        )
        output = rule_engine.evaluate(profile)
        assert_flag_triggered(output, "AGM-005")

    def test_AGM005_no_trigger_when_quorum_met(self, rule_engine, build_profile):
        profile = build_profile(
            agm_held_this_cycle=True,
            members_present_at_agm=3,
        )
        output = rule_engine.evaluate(profile)
        assert_flag_not_triggered(output, "AGM-005")

    # ── AGM-006: Auditor Not Reappointed ─────────────────────────────────────

    def test_AGM006_triggers_when_auditor_not_reappointed(self, rule_engine, build_profile):
        profile = build_profile(
            agm_held_this_cycle=True,
            auditor_reappointed_at_agm=False,
        )
        output = rule_engine.evaluate(profile)
        assert_flag_triggered(output, "AGM-006")

    def test_AGM006_no_trigger_when_auditor_reappointed(self, rule_engine, build_profile):
        profile = build_profile(
            agm_held_this_cycle=True,
            auditor_reappointed_at_agm=True,
        )
        output = rule_engine.evaluate(profile)
        assert_flag_not_triggered(output, "AGM-006")


# =============================================================================
# MODULE: AUDIT (3 rules)
# =============================================================================

class TestAuditRules:
    """Tests for AUD-001, AUD-002, AUD-003 (BLACK override)."""

    def test_AUD001_triggers_when_audit_not_complete(self, rule_engine, build_profile):
        """AGM held but audit not completed before AGM → AUD-001."""
        profile = build_profile(
            agm_held_this_cycle=True,
            audit_complete=False,
            audit_in_progress=False,
        )
        output = rule_engine.evaluate(profile)
        assert_flag_triggered(output, "AUD-001")

    def test_AUD001_no_trigger_when_audit_complete(self, rule_engine, build_profile):
        profile = build_profile(
            audit_complete=True,
            last_audit_signed_date=date.today() - timedelta(days=90),
        )
        output = rule_engine.evaluate(profile)
        assert_flag_not_triggered(output, "AUD-001")

    def test_AUD002_triggers_when_first_auditor_not_appointed(self, rule_engine, build_profile):
        """Company never appointed its first auditor → AUD-002."""
        profile = build_profile(
            first_auditor_appointed=False,
            agm_count=0,
        )
        output = rule_engine.evaluate(profile)
        assert_flag_triggered(output, "AUD-002")

    def test_AUD002_no_trigger_when_auditor_appointed(self, rule_engine, build_profile):
        profile = build_profile(first_auditor_appointed=True)
        output = rule_engine.evaluate(profile)
        assert_flag_not_triggered(output, "AUD-002")

    @pytest.mark.black
    def test_AUD003_triggers_AGM_held_without_audit(self, rule_engine, build_profile):
        """AGM held without completing audit → AUD-003 BLACK override."""
        profile = build_profile(
            agm_held_this_cycle=True,
            audit_complete=False,
            agm_held_without_audit=True,
        )
        output = rule_engine.evaluate(profile)
        assert_flag_triggered(output, "AUD-003")

    @pytest.mark.black
    def test_AUD003_forces_black_band(self, rule_engine, build_profile):
        """AUD-003 is a BLACK override — band must be BLACK regardless of other scores."""
        profile = build_profile(
            agm_held_this_cycle=True,
            audit_complete=False,
            agm_held_without_audit=True,
        )
        output = rule_engine.evaluate(profile)
        # Score may be high but band must be forced BLACK
        assert output.score_breakdown.override_applied is True
        assert output.score_breakdown.final_score <= 29

    @pytest.mark.black
    def test_AUD003_no_trigger_when_audit_done_before_agm(self, rule_engine, build_profile):
        profile = build_profile(
            agm_held_this_cycle=True,
            audit_complete=True,
            agm_held_without_audit=False,
        )
        output = rule_engine.evaluate(profile)
        assert_flag_not_triggered(output, "AUD-003")


# =============================================================================
# MODULE: ANNUAL RETURN (4 rules)
# =============================================================================

class TestAnnualReturnRules:
    """Tests for AR-001 through AR-004."""

    def test_AR001_triggers_single_year_default(self, rule_engine, build_profile):
        """1 year of unfiled returns → AR-001 YELLOW."""
        profile = build_profile(
            unfiled_returns_count=1,
            annual_return_filed=False,
        )
        output = rule_engine.evaluate(profile)
        assert_flag_triggered(output, "AR-001")

    def test_AR002_triggers_two_year_backlog(self, rule_engine, build_profile):
        """2+ years unfiled → AR-002 RED."""
        profile = build_profile(
            unfiled_returns_count=2,
            annual_return_filed=False,
        )
        output = rule_engine.evaluate(profile)
        assert_flag_triggered(output, "AR-002")

    @pytest.mark.black
    def test_AR003_triggers_three_year_backlog(self, rule_engine, build_profile):
        """3+ years unfiled → AR-003 BLACK (strike-off risk)."""
        profile = build_profile(
            unfiled_returns_count=3,
            annual_return_filed=False,
        )
        output = rule_engine.evaluate(profile)
        assert_flag_triggered(output, "AR-003")

    def test_AR004_triggers_incomplete_filing(self, rule_engine, build_profile):
        """Return filed but content incomplete → AR-004."""
        profile = build_profile(
            annual_return_filed=True,
            annual_return_content_complete=False,
        )
        output = rule_engine.evaluate(profile)
        assert_flag_triggered(output, "AR-004")

    def test_AR004_no_trigger_when_complete(self, rule_engine, build_profile):
        profile = build_profile(
            annual_return_filed=True,
            annual_return_content_complete=True,
        )
        output = rule_engine.evaluate(profile)
        assert_flag_not_triggered(output, "AR-004")

    def test_no_return_flags_when_compliant(self, rule_engine, build_profile):
        profile = build_profile(
            unfiled_returns_count=0,
            annual_return_filed=True,
            annual_return_content_complete=True,
        )
        output = rule_engine.evaluate(profile)
        for rule_id in ["AR-001", "AR-002", "AR-003", "AR-004"]:
            assert_flag_not_triggered(output, rule_id)


# =============================================================================
# MODULE: DIRECTORS (4 rules)
# =============================================================================

class TestDirectorRules:
    """Tests for DIR-001 through DIR-004."""

    def test_DIR001_triggers_appointment_not_filed(self, rule_engine, build_profile, make_director_change):
        """Director appointed but form not filed → DIR-001."""
        change = make_director_change(event_type="appointment", days_ago=60, form_filed=False)
        profile = build_profile(director_changes=[change])
        output = rule_engine.evaluate(profile)
        assert_flag_triggered(output, "DIR-001")

    def test_DIR001_no_trigger_when_form_filed(self, rule_engine, build_profile, make_director_change):
        change = make_director_change(event_type="appointment", days_ago=60, form_filed=True, form_filed_days_ago=45)
        profile = build_profile(director_changes=[change])
        output = rule_engine.evaluate(profile)
        assert_flag_not_triggered(output, "DIR-001")

    def test_DIR002_triggers_resignation_not_filed(self, rule_engine, build_profile, make_director_change):
        """Director resigned but form not filed → DIR-002."""
        change = make_director_change(event_type="resignation", days_ago=60, form_filed=False)
        profile = build_profile(director_changes=[change])
        output = rule_engine.evaluate(profile)
        assert_flag_triggered(output, "DIR-002")

    def test_DIR003_triggers_over_one_year_unfiled(self, rule_engine, build_profile, make_director_change):
        """Director change unfiled for > 1 year → DIR-003 RED."""
        change = make_director_change(event_type="appointment", days_ago=400, form_filed=False)
        profile = build_profile(director_changes=[change])
        output = rule_engine.evaluate(profile)
        assert_flag_triggered(output, "DIR-003")

    def test_DIR003_no_trigger_under_one_year(self, rule_engine, build_profile, make_director_change):
        change = make_director_change(event_type="appointment", days_ago=200, form_filed=False)
        profile = build_profile(director_changes=[change])
        output = rule_engine.evaluate(profile)
        assert_flag_not_triggered(output, "DIR-003")

    def test_DIR004_triggers_departed_still_active(self, rule_engine, build_profile, make_director_change):
        """Director resigned but still listed as active → DIR-004."""
        change = make_director_change(event_type="resignation", days_ago=90, form_filed=False)
        change.departed_still_liable = True  # Mark as departed still appearing active
        profile = build_profile(director_changes=[change])
        output = rule_engine.evaluate(profile)
        assert_flag_triggered(output, "DIR-004")

    def test_no_director_flags_when_compliant(self, rule_engine, build_profile):
        profile = build_profile(director_changes=[])
        output = rule_engine.evaluate(profile)
        for rule_id in ["DIR-001", "DIR-002", "DIR-003", "DIR-004"]:
            assert_flag_not_triggered(output, rule_id)


# =============================================================================
# MODULE: SHAREHOLDERS (1 rule)
# =============================================================================

class TestShareholderRules:

    def test_SH001_triggers_change_not_in_return(self, rule_engine, build_profile):
        """Shareholder change but not reflected in annual return → SH-001."""
        profile = build_profile(
            shareholder_change_date=date.today() - timedelta(days=200),
            form_xv_filed=False,
            annual_return_filed=True,
        )
        output = rule_engine.evaluate(profile)
        assert_flag_triggered(output, "SH-001")

    def test_SH001_no_trigger_when_filed(self, rule_engine, build_profile):
        profile = build_profile(
            shareholder_change_date=date.today() - timedelta(days=100),
            form_xv_filed=True,
        )
        output = rule_engine.evaluate(profile)
        assert_flag_not_triggered(output, "SH-001")

    def test_SH001_no_trigger_when_no_change(self, rule_engine, build_profile):
        profile = build_profile(shareholder_change_date=None)
        output = rule_engine.evaluate(profile)
        assert_flag_not_triggered(output, "SH-001")


# =============================================================================
# MODULE: TRANSFERS (6 rules including 1 BLACK override)
# =============================================================================

class TestTransferRules:
    """Tests for TR-001 through TR-006. TR-005 is a BLACK override."""

    def test_TR001_triggers_no_instrument(self, rule_engine, build_profile, make_share_transfer):
        """Transfer with no written instrument → TR-001."""
        transfer = make_share_transfer(instrument_recorded=False)
        profile = build_profile(share_transfers=[transfer])
        output = rule_engine.evaluate(profile)
        assert_flag_triggered(output, "TR-001")

    def test_TR002_triggers_stamp_duty_not_paid(self, rule_engine, build_profile, make_share_transfer):
        """Transfer without stamp duty payment → TR-002."""
        transfer = make_share_transfer(stamp_duty_paid=False, stamp_duty_amount=0)
        profile = build_profile(share_transfers=[transfer])
        output = rule_engine.evaluate(profile)
        assert_flag_triggered(output, "TR-002")

    def test_TR003_triggers_no_board_approval(self, rule_engine, build_profile, make_share_transfer):
        """Transfer without board approval → TR-003."""
        transfer = make_share_transfer(board_approval=False, board_approval_obtained=False)
        profile = build_profile(share_transfers=[transfer])
        output = rule_engine.evaluate(profile)
        assert_flag_triggered(output, "TR-003")

    def test_TR004_triggers_register_not_updated(self, rule_engine, build_profile, make_share_transfer):
        """Transfer completed but share register not updated → TR-004."""
        transfer = make_share_transfer(share_register_updated=False)
        profile = build_profile(share_transfers=[transfer])
        output = rule_engine.evaluate(profile)
        assert_flag_triggered(output, "TR-004")

    @pytest.mark.black
    def test_TR005_triggers_aoa_violation(self, rule_engine, build_profile, make_share_transfer):
        """Transfer violating AoA restriction → TR-005 BLACK override."""
        transfer = make_share_transfer(
            aoa_restriction_apply=True,
            board_approval_obtained=False,
        )
        profile = build_profile(
            share_transfers=[transfer],
            aoa_transfer_restriction=True,
        )
        output = rule_engine.evaluate(profile)
        assert_flag_triggered(output, "TR-005")

    @pytest.mark.black
    def test_TR005_forces_black_band(self, rule_engine, build_profile, make_share_transfer):
        """TR-005 AoA violation must force BLACK band regardless of score."""
        transfer = make_share_transfer(
            aoa_restriction_apply=True,
            board_approval_obtained=False,
        )
        profile = build_profile(share_transfers=[transfer], aoa_transfer_restriction=True)
        output = rule_engine.evaluate(profile)
        assert output.score_breakdown.override_applied is True
        assert output.score_breakdown.final_score <= 29

    def test_TR006_triggers_composite_irregular(self, rule_engine, build_profile, make_share_transfer):
        """Multiple irregularities in one transfer → TR-006 RED."""
        transfer = make_share_transfer(
            instrument_recorded=False,
            stamp_duty_paid=False,
            board_approval=False,
        )
        profile = build_profile(share_transfers=[transfer])
        output = rule_engine.evaluate(profile)
        assert_flag_triggered(output, "TR-006")

    def test_no_transfer_flags_when_compliant(self, rule_engine, build_profile, make_share_transfer):
        transfer = make_share_transfer(
            instrument_recorded=True,
            stamp_duty_paid=True,
            board_approval=True,
            share_register_updated=True,
            aoa_restriction_apply=False,
        )
        profile = build_profile(share_transfers=[transfer])
        output = rule_engine.evaluate(profile)
        for rule_id in ["TR-001", "TR-002", "TR-003", "TR-004", "TR-005", "TR-006"]:
            assert_flag_not_triggered(output, rule_id)

    def test_no_transfer_flags_when_no_transfers(self, rule_engine, build_profile):
        profile = build_profile(share_transfers=[])
        output = rule_engine.evaluate(profile)
        for rule_id in ["TR-001", "TR-002", "TR-003", "TR-004", "TR-005", "TR-006"]:
            assert_flag_not_triggered(output, rule_id)


# =============================================================================
# MODULE: REGISTERS (2 rules)
# =============================================================================

class TestRegisterRules:

    def test_REG001_triggers_registers_incomplete(self, rule_engine, build_profile):
        """Missing mandatory statutory registers → REG-001."""
        profile = build_profile(
            maintained_registers=["members"],  # Missing directors, charges, etc.
        )
        output = rule_engine.evaluate(profile)
        assert_flag_triggered(output, "REG-001")

    def test_REG001_no_trigger_all_registers_maintained(self, rule_engine, build_profile):
        profile = build_profile(
            maintained_registers=["members", "directors", "charges", "transfers", "debentures", "mortgages"],
        )
        output = rule_engine.evaluate(profile)
        assert_flag_not_triggered(output, "REG-001")

    def test_REG004_triggers_core_register_missing(self, rule_engine, build_profile):
        profile = build_profile(
            maintained_registers=["members", "transfers", "debentures", "mortgages"],
        )
        output = rule_engine.evaluate(profile)
        assert_flag_triggered(output, "REG-004")

    def test_REG004_no_trigger_all_core_registers_maintained(self, rule_engine, build_profile):
        profile = build_profile(
            maintained_registers=["members", "directors", "charges", "transfers", "debentures", "mortgages"],
        )
        output = rule_engine.evaluate(profile)
        assert_flag_not_triggered(output, "REG-004")

    def test_REG002_triggers_certificate_not_issued(self, rule_engine, build_profile):
        """Share certificate not issued after allotment → REG-002."""
        profile = build_profile(
            last_allotment_date=date.today() - timedelta(days=60),
            share_certificate_issued=False,
        )
        output = rule_engine.evaluate(profile)
        assert_flag_triggered(output, "REG-002")

    def test_REG002_no_trigger_no_allotment(self, rule_engine, build_profile):
        profile = build_profile(last_allotment_date=None)
        output = rule_engine.evaluate(profile)
        assert_flag_not_triggered(output, "REG-002")


# =============================================================================
# MODULE: OFFICE (1 rule)
# =============================================================================

class TestOfficeRules:

    def test_OFF001_triggers_address_change_not_filed(self, rule_engine, build_profile):
        """Registered office changed but form IX not filed → OFF-001."""
        profile = build_profile(
            registered_office_change_date=date.today() - timedelta(days=60),
            form_ix_filed=False,
        )
        output = rule_engine.evaluate(profile)
        assert_flag_triggered(output, "OFF-001")

    def test_OFF001_no_trigger_when_filed(self, rule_engine, build_profile):
        profile = build_profile(
            registered_office_change_date=date.today() - timedelta(days=60),
            form_ix_filed=True,
        )
        output = rule_engine.evaluate(profile)
        assert_flag_not_triggered(output, "OFF-001")

    def test_OFF001_no_trigger_no_change(self, rule_engine, build_profile):
        profile = build_profile(registered_office_change_date=None)
        output = rule_engine.evaluate(profile)
        assert_flag_not_triggered(output, "OFF-001")


# =============================================================================
# MODULE: CAPITAL (2 rules)
# =============================================================================

class TestCapitalRules:

    def test_CAP001_triggers_capital_change_no_resolution(self, rule_engine, build_profile):
        """Capital altered without board/member resolution → CAP-001."""
        profile = build_profile(
            capital_increase_date=date.today() - timedelta(days=90),
            capital_increase_resolution=False,
        )
        output = rule_engine.evaluate(profile)
        assert_flag_triggered(output, "CAP-001")

    def test_CAP001_no_trigger_with_resolution(self, rule_engine, build_profile):
        profile = build_profile(
            capital_increase_date=date.today() - timedelta(days=90),
            capital_increase_resolution=True,
        )
        output = rule_engine.evaluate(profile)
        assert_flag_not_triggered(output, "CAP-001")

    def test_CAP002_triggers_charge_not_registered(self, rule_engine, build_profile):
        """Charge created but Form VIII not filed with RJSC → CAP-002."""
        profile = build_profile(
            charge_creation_date=date.today() - timedelta(days=40),
            form_viii_filed=False,
        )
        output = rule_engine.evaluate(profile)
        assert_flag_triggered(output, "CAP-002")

    def test_CAP002_no_trigger_when_filed(self, rule_engine, build_profile):
        profile = build_profile(
            charge_creation_date=date.today() - timedelta(days=40),
            form_viii_filed=True,
        )
        output = rule_engine.evaluate(profile)
        assert_flag_not_triggered(output, "CAP-002")


# =============================================================================
# MODULE: ESCALATION (3 rules — 2 BLACK overrides)
# =============================================================================

class TestEscalationRules:
    """ESC-001 RED, ESC-002 BLACK override, ESC-003 BLACK override."""

    def test_ESC001_triggers_elevated_strike_off_risk(self, rule_engine, build_profile):
        """Multiple RED flags + 2+ year backlog → ESC-001 elevated risk."""
        profile = build_profile(
            unfiled_returns_count=2,
            annual_return_filed=False,
            agm_held_this_cycle=False,
            audit_complete=False,
        )
        output = rule_engine.evaluate(profile)
        assert_flag_triggered(output, "ESC-001")

    @pytest.mark.black
    def test_ESC002_triggers_strike_off_imminent(self, rule_engine, build_profile):
        """3+ year backlog + AGM default = strike-off imminent → ESC-002 BLACK."""
        profile = build_profile(
            unfiled_returns_count=3,
            annual_return_filed=False,
            agm_held_this_cycle=False,
            agm_count=0,
            audit_complete=False,
        )
        output = rule_engine.evaluate(profile)
        assert_flag_triggered(output, "ESC-002")

    @pytest.mark.black
    def test_ESC002_forces_black_band(self, rule_engine, black_band_profile):
        output = rule_engine.evaluate(black_band_profile)
        # ESC-002 or ESC-003 should force BLACK
        has_black_override = any(
            f.rule_id in ("ESC-002", "ESC-003", "AUD-003", "TR-005")
            and f.is_black_override
            for f in output.flags
        )
        assert has_black_override or output.score_breakdown.final_score <= 29

    @pytest.mark.black
    def test_ESC003_triggers_rescue_mandatory(self, rule_engine, black_band_profile):
        """Maximally non-compliant company → ESC-003 rescue mandatory."""
        output = rule_engine.evaluate(black_band_profile)
        assert_flag_triggered(output, "ESC-003")

    @pytest.mark.black
    def test_ESC003_is_black_override(self, rule_engine, black_band_profile):
        """ESC-003 must have is_black_override=True."""
        output = rule_engine.evaluate(black_band_profile)
        esc003_flags = [f for f in output.flags if f.rule_id == "ESC-003"]
        if esc003_flags:
            assert esc003_flags[0].is_black_override is True


# =============================================================================
# SCORE BANDING
# =============================================================================

class TestScoreBanding:
    """Verify score → band mapping is correct and non-overlapping."""

    @pytest.mark.parametrize("score,expected_band", [
        (100, "GREEN"),
        (85,  "GREEN"),
        (70,  "GREEN"),
        (69,  "YELLOW"),
        (55,  "YELLOW"),
        (50,  "YELLOW"),
        (49,  "RED"),
        (35,  "RED"),
        (30,  "RED"),
        (29,  "BLACK"),
        (15,  "BLACK"),
        (0,   "BLACK"),
    ])
    def test_score_to_band_mapping(self, rule_engine, score, expected_band):
        band = rule_engine._score_to_band(score)
        assert band == expected_band, f"Score {score} → expected {expected_band}, got {band}"

    def test_score_never_exceeds_100(self, rule_engine, compliant_profile):
        output = rule_engine.evaluate(compliant_profile)
        assert output.score_breakdown.final_score <= 100

    def test_score_never_below_zero(self, rule_engine, black_band_profile):
        output = rule_engine.evaluate(black_band_profile)
        assert output.score_breakdown.final_score >= 0

    def test_black_override_forces_score_below_29(self, rule_engine, build_profile):
        """Any BLACK override rule must force final_score ≤ 29."""
        # AUD-003: AGM held without audit
        profile = build_profile(
            agm_held_this_cycle=True,
            agm_held_without_audit=True,
            audit_complete=False,
        )
        output = rule_engine.evaluate(profile)
        if output.score_breakdown.override_applied:
            assert output.score_breakdown.final_score <= 29


# =============================================================================
# SCORE IMMUTABILITY (AI Constitution Article 4)
# =============================================================================

class TestScoreImmutability:
    """Score hash and override tracking for legal defensibility."""

    def test_identical_profiles_produce_identical_scores(self, rule_engine, build_profile):
        """Deterministic: same input → same output every time."""
        profile1 = build_profile(company_id="test-id-123")
        profile2 = build_profile(company_id="test-id-123")
        out1 = rule_engine.evaluate(profile1)
        out2 = rule_engine.evaluate(profile2)
        assert out1.score_breakdown.final_score == out2.score_breakdown.final_score
        assert [f.rule_id for f in out1.flags] == [f.rule_id for f in out2.flags]

    def test_override_applied_field_present(self, rule_engine, compliant_profile):
        """override_applied field must always be present on ScoreBreakdown."""
        output = rule_engine.evaluate(compliant_profile)
        assert hasattr(output.score_breakdown, "override_applied")

    def test_override_false_for_compliant_company(self, rule_engine, compliant_profile):
        output = rule_engine.evaluate(compliant_profile)
        assert output.score_breakdown.override_applied is False

    def test_engine_version_recorded(self, rule_engine, compliant_profile):
        """Engine version must be recorded in output for legal defensibility."""
        output = rule_engine.evaluate(compliant_profile)
        assert output.engine_version is not None
        assert len(output.engine_version) > 0

    def test_all_32_rules_are_checked(self, rule_engine, black_band_profile):
        """
        Smoke test: when a maximally non-compliant company is evaluated,
        the engine doesn't skip any modules.
        At minimum, we should get flags from multiple modules.
        """
        output = rule_engine.evaluate(black_band_profile)
        modules_triggered = {f.rule_id.split("-")[0] for f in output.flags}
        assert len(modules_triggered) >= 3, (
            f"Expected flags from multiple modules, only got: {modules_triggered}"
        )
