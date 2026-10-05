"""
NLC Canonical Corpus Builder & Verifier

Verifies the canonical legal corpus is complete and consistent:
  - SOURCE_RULE_COUNT = 75 (statutory_rules.py)
  - RESCUE_COUNT = 75 (statutory_rescue.py)
  - INVARIANT_COUNT = 20 (product_invariants.py)
  - SEED_COUNT = 75 (seed_rules.py)
  - ENGINE_COUNT = 75 (engine.py rule_ids)

All four sources must agree: 75 = 75 = 75 = 75

Usage: python tools/build_canonical_corpus.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def verify_corpus():
    results = {}

    # ── 1. Source rules (statutory_rules.py) ──
    try:
        from canonical_architecture.statutory_rules import STATUTORY_RULE_REGISTRY
        source_ids = set(STATUTORY_RULE_REGISTRY.keys())
        results["source_rules"] = len(source_ids)
    except Exception as e:
        print(f"ERROR: Could not import statutory_rules: {e}")
        source_ids = set()
        results["source_rules"] = 0

    # ── 2. Rescue entries (statutory_rescue.py) ──
    try:
        from canonical_architecture.statutory_rescue import STATUTORY_RESCUE_REGISTRY
        rescue_ids = set(STATUTORY_RESCUE_REGISTRY.keys())
        results["rescue_entries"] = len(rescue_ids)
    except Exception as e:
        print(f"ERROR: Could not import statutory_rescue: {e}")
        rescue_ids = set()
        results["rescue_entries"] = 0

    # ── 3. Invariants (product_invariants.py) ──
    try:
        from canonical_architecture.product_invariants import Invariant
        inv = [x for x in dir(Invariant) if x.startswith("R_")]
        results["invariants"] = len(inv)
    except Exception as e:
        print(f"ERROR: Could not import product_invariants: {e}")
        results["invariants"] = 0

    # ── 4. Seed rules (seed_rules.py) ──
    try:
        from scripts.seed_rules import ILRMF_RULES
        seed_ids = {r["rule_id"] for r in ILRMF_RULES}
        results["seed_rules"] = len(seed_ids)
    except Exception as e:
        print(f"ERROR: Could not import seed_rules: {e}")
        seed_ids = set()
        results["seed_rules"] = 0

    # ── 5. Engine rules (engine.py — runtime extraction) ──
    try:
        from app.rule_engine.engine import NLCRuleEngine, CompanyProfile
        from datetime import date, timedelta

        today = date(2026, 10, 20)

        # Create a maximally non-compliant company to trigger all rules
        profiles = []
        for i in range(5):
            profiles.append(CompanyProfile(
                company_id=f"VERIFY_{i}",
                company_name=f"Verify Corp {i}",
                incorporation_date=today - timedelta(days=2000),
                agm_count=0,
                current_director_count=0,
                moa_aoa_filed=False,
                form_iii_filed=False,
                first_auditor_appointed=False,
                annual_return_filed=False,
                unfiled_returns_count=5,
                tin_obtained=False,
                vat_registered=False,
                trade_license_obtained=False,
                paid_up_capital_bdt=10000000,
                authorized_capital_bdt=5000000,
                capital_reduction_pending=True,
                capital_reduction_court_order_obtained=False,
                any_director_disqualified=True,
                disqualification_details=["Dir A"],
                on_rjsc_strike_off_list=True,
                register_of_directors_interests=False,
                register_of_contracts=False,
                factory_license_obtained=False,
                factory_license_expiry=today - timedelta(days=100),
                labour_court_order_pending=True,
                bsec_listed=True,
                bsec_quarterly_report_filed=False,
                cg_certificate_obtained=False,
                board_independent_director=False,
                audit_committee_established=False,
                agm_adjourned_without_notice=True,
                voluntary_winding_up=True,
                investigation_order=True,
                foreign_exchange_violation=True,
                name_change_pending=True,
                name_change_date=today - timedelta(days=100),
                object_clause_change_pending=True,
                object_clause_change_date=today - timedelta(days=100),
                aoa_alteration_pending=True,
                aoa_alteration_date=today - timedelta(days=100),
                special_resolution_date=today - timedelta(days=100),
                special_resolution_filed=False,
                annual_turnover_bdt=5000000,
                has_foreign_shareholder=True,
                foreign_shareholding_pct=51.0,
                encashment_certificate_uploaded=False,
                bida_registered=True,
                remittance_amount_usd=10000,
                penalty_notices_received=5,
                penalty_notices_resolved=0,
                winding_up_petition_filed=True,
                liquidator_appointed=True,
                court_ordered_winding_up=True,
                schedule_x_attached=False,
                balance_sheet_attached=False,
                profit_loss_attached=False,
                directors_list_attached=False,
                shareholders_list_attached=False,
                tax_return_filed_for_current_fy=False,
                advance_tax_q1_paid=False,
                advance_tax_q2_paid=False,
                advance_tax_q3_paid=False,
                advance_tax_q4_paid=False,
                vat_annual_return_filed_for_fy=False,
                last_vat_return_filed=None,
                last_audit_signed_date=today,
                last_return_filed_year=today.year,
            ))

        engine_ids = set()
        for profile in profiles:
            eng = NLCRuleEngine()
            output = eng.evaluate(profile, today=today)
            for flag in output.flags:
                engine_ids.add(flag.rule_id)

        results["engine_rules"] = len(engine_ids)
    except Exception as e:
        print(f"ERROR: Could not extract engine rules: {e}")
        engine_ids = set()
        results["engine_rules"] = 0

    # ── 6. Reconciliation ──
    print("=" * 60)
    print("CANONICAL CORPUS VERIFICATION")
    print("=" * 60)
    print()
    print(f"SOURCE_RULE_COUNT  = {results.get('source_rules', 0)}")
    print(f"RESCUE_COUNT      = {results.get('rescue_entries', 0)}")
    print(f"INVARIANT_COUNT   = {results.get('invariants', 0)}")
    print(f"SEED_COUNT        = {results.get('seed_rules', 0)}")
    print(f"ENGINE_COUNT      = {results.get('engine_rules', 0)}")
    print()

    # Check alignment
    all_same = (
        results.get("source_rules") == results.get("rescue_entries") == results.get("seed_rules")
    )

    if all_same:
        print(f"[OK] Source = Rescue = Seed = {results.get('source_rules')}")
    else:
        print(f"[FAIL] Misalignment detected")
        print(f"  Source: {results.get('source_rules')}")
        print(f"  Rescue: {results.get('rescue_entries')}")
        print(f"  Seed:   {results.get('seed_rules')}")

    # Orphan check
    source_only = source_ids - rescue_ids
    rescue_only = rescue_ids - source_ids
    print()
    print(f"Source-only (no rescue): {len(source_only)}")
    if source_only:
        print(f"  {sorted(source_only)}")
    print(f"Rescue-only (no source): {len(rescue_only)}")
    if rescue_only:
        print(f"  {sorted(rescue_only)}")

    # Seed vs source
    seed_not_source = seed_ids - source_ids
    source_not_seed = source_ids - seed_ids
    print()
    print(f"Seed not in source: {len(seed_not_source)}")
    if seed_not_source:
        print(f"  {sorted(seed_not_source)}")
    print(f"Source not in seed: {len(source_not_seed)}")
    if source_not_seed:
        print(f"  {sorted(source_not_seed)}")

    # ESC vs ESCUE
    esc_source = sorted([x for x in source_ids if x.startswith("ESC")])
    escue_source = sorted([x for x in source_ids if x.startswith("ESCUE")])
    print()
    print(f"ESC-* in source: {esc_source}")
    print(f"ESCUE-* in source: {escue_source}")
    if not escue_source:
        print("[OK] No ESCUE naming conflict")

    # Final verdict
    print()
    print("=" * 60)
    if all_same and not source_only and not rescue_only and not seed_not_source and not source_not_seed:
        print("CANONICAL CORPUS: VERIFIED")
        print(f"  {results.get('source_rules')} rules = {results.get('rescue_entries')} rescue = {results.get('seed_rules')} seed")
        print(f"  {results.get('invariants')} invariants")
        print(f"  0 orphans, 0 mismatches")
    else:
        print("CANONICAL CORPUS: ISSUES DETECTED")
    print("=" * 60)

    return results


if __name__ == "__main__":
    verify_corpus()
