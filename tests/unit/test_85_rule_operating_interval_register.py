"""Fail-closed structural checks for the 85-rule operative interval register."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTER = ROOT / "docs/legal/85_rule_operating_interval_register_v1.json"


def load_register() -> dict:
    return json.loads(REGISTER.read_text(encoding="utf-8"))


def test_register_contains_exactly_85_unique_rules() -> None:
    payload = load_register()
    rules = payload["rules"]
    ids = [rule["rule_id"] for rule in rules]
    assert payload["canonical_rule_count"] == 85
    assert len(rules) == 85
    assert len(ids) == len(set(ids)) == 85


def test_every_rule_fails_closed_until_interval_review_is_complete() -> None:
    payload = load_register()
    for rule in payload["rules"]:
        interval = rule["operative_interval"]
        assert interval["from"] is None
        assert interval["to_exclusive"] is None
        assert interval["status"] == "UNRESOLVED_RULE_SPECIFIC_INTERVAL"
        assert rule["amendment_completeness"] == "OPEN_NOT_EXHAUSTIVE"
        assert rule["issuer_document_authentication_status"] == "NOT_INDEPENDENTLY_VERIFIED"
        assert rule["legal_effect_status"] == "REQUIRES_INDEPENDENT_BANGLADESH_COUNSEL_REVIEW"


def test_missing_provision_candidates_are_explicit() -> None:
    payload = load_register()
    missing = [r["rule_id"] for r in payload["rules"] if r["missing_provision_candidate"]]
    assert len(missing) == payload["coverage"]["rules_missing_provision_candidates"]
    assert len(missing) == 2
    assert set(missing) == {"FX-001", "TR-002"}
    for rule in payload["rules"]:
        assert rule["missing_provision_candidate"] is (len(rule["candidate_provisions"]) == 0)


def test_primary_record_anchors_have_issuer_and_gazette_provenance() -> None:
    payload = load_register()
    anchors = {item["source_id"]: item for item in payload["located_primary_record_anchors"]}
    assert set(anchors) == {"BD_DPP_SRO_321_LAW_1994", "BD_ACT_7_2020", "BD_ACT_24_2020", "BD_ACT_16_2015_FINANCIAL_REPORTING", "BD_BSEC_CGC_2018", "BD_BSEC_CGC_AMENDMENT_2023", "BD_BSEC_CGC_AMENDMENT_2024", "BD_BSEC_FEMALE_ID_EXTENSION_2026", "BD_BB_GFET_2018", "BD_BB_FE_CIRCULAR_10_2023", "BD_BB_FEID_CIRCULAR_01_2025", "BD_BB_FEID_CIRCULAR_03_2025", "BD_BB_FEFD2_CIRCULAR_12_2026", "BD_CITY_CORP_MODEL_TAX_SCHEDULE_2016", "BD_PAURASHAVA_MODEL_TAX_SCHEDULE_2014", "BD_CITY_CORP_SRO_200_LAW_2017", "BD_PAURASHAVA_AMENDMENT_ACT_60_2026", "BD_CITY_CORP_AMENDMENT_ACT_61_2026", "BD_VAT_AMENDMENT_ACT_77_2026", "BD_FINANCE_ACT_96_2026", "BD_VAT_AMENDMENT_ORDINANCE_38_2026", "BD_BSEC_FINANCIAL_REPORTING_NOTIFICATION_2018", "BD_BIDA_GUIDELINE_2023_21_MAY_COPY", "BD_BB_FEID_CIRCULAR_LETTER_06_2023"}
    for anchor in anchors.values():
        assert anchor["issuer"]
        if anchor.get("gazette_index_url"):
            assert anchor["gazette_index_url"].startswith("https://www.dpp.gov.bd/")
            assert anchor["gazette_pdf_url"].startswith("https://www.dpp.gov.bd/")
        else:
            assert anchor["official_issuer_host"] in {"sec.gov.bd", "bb.org.bd", "www.bb.org.bd", "dpp.gov.bd", "www.dpp.gov.bd", "scs.ssd.gov.bd"}
            assert anchor["issuer_official_url"].startswith("https://" + anchor["official_issuer_host"] + "/")
        assert anchor["publication_date"]
        assert anchor["document_authentication_status"] != "FULLY_AUTHENTICATED"
        assert anchor["artifact_sha256"] is None


def test_bida_usd_50000_requirement_is_conditional_and_version_sensitive() -> None:
    payload = load_register()
    rule = next(r for r in payload["rules"] if r["rule_id"] == "INC-006")
    assert len(rule["candidate_provisions"]) == 3
    assert rule["rule_claim_assessment"]["status"] == "CONDITIONAL_ADMINISTRATIVE_APPLICATION_REQUIREMENT; NOT_GENERAL_COMPANY_STATUTORY_MINIMUM"
    assert "not a universal minimum capital rule" in rule["rule_claim_assessment"]["assessment"]
    update = [e for e in rule["amendment_candidates"] if "29-May-2023" in e["instrument_title"]]
    assert len(update) == 1
    assert update[0]["claimed_effective_from"] is None
    assert update[0]["source_claim_status"] == "UPDATED_VERSION_REFERENCE_CONFIRMED_BY_BB; ORIGINAL_BIDA_PDF_NOT_RETRIEVED"


def test_bsec_quarterly_reporting_uses_financial_reporting_condition_4_not_cgc_condition_8() -> None:
    payload = load_register()
    rule = next(r for r in payload["rules"] if r["rule_id"] == "BSEC-001")
    assert rule["candidate_provisions"] == ["BSEC Notification No. BSEC/CMRRCD/2006-158/208/Admin/81 dated 20 June 2018, Conditions 4(1)–(3)"]
    event = rule["amendment_candidates"][0]
    assert event["primary_record_id"] == "BD_BSEC_FINANCIAL_REPORTING_NOTIFICATION_2018"
    assert event["claimed_effective_from"] is None
    assert "45 days" in event["commencement_or_effect_note"]
    assert "one month" in event["commencement_or_effect_note"]
    assert rule["rule_claim_assessment"]["non_binding_policy_watch"]["status"] == "PUBLIC_ANNOUNCEMENT_ONLY_NOT_LEGAL_AMENDMENT"


def test_vat_section_64_chain_rejects_universal_annual_return_claim() -> None:
    payload = load_register()
    rule = next(r for r in payload["rules"] if r["rule_id"] == "VAT-003")
    assert rule["rule_claim_assessment"]["status"] == "NO_UNIVERSAL_ANNUAL_RETURN_OBLIGATION_IDENTIFIED; CURRENT_S64_IS_PERIODIC"
    events = {e["primary_record_id"]: e for e in rule["amendment_candidates"]}
    assert events["BD_FINANCE_ACT_96_2026"]["claimed_effective_from"] == "2026-07-01"
    assert events["BD_FINANCE_ACT_96_2026"]["claimed_effective_to"] == "2026-10-01"
    assert events["BD_VAT_AMENDMENT_ORDINANCE_38_2026"]["claimed_effective_from"] == "2026-10-01"
    assert "each tax period" in events["BD_VAT_AMENDMENT_ORDINANCE_38_2026"]["commencement_or_effect_note"]
    assert events["BD_VAT_AMENDMENT_ACT_77_2026"]["rule_effect_status"] == "NO_DIRECT_CHANGE_TO_S64_RETURN_FREQUENCY"


def test_trade_license_claim_does_not_assume_31_march_expiry() -> None:
    payload = load_register()
    by_id = {rule["rule_id"]: rule for rule in payload["rules"]}
    for rule_id in ("TL-001", "TL-002"):
        assert len(by_id[rule_id]["candidate_provisions"]) == 2
    tl2 = by_id["TL-002"]
    assert tl2["rule_claim_assessment"]["status"] == "UNSUPPORTED_AS_UNIVERSAL_DEADLINE"
    city = next(e for e in tl2["amendment_candidates"] if e["primary_record_id"] == "BD_CITY_CORP_MODEL_TAX_SCHEDULE_2016")
    paur = next(e for e in tl2["amendment_candidates"] if e["primary_record_id"] == "BD_PAURASHAVA_MODEL_TAX_SCHEDULE_2014")
    assert "five years" in city["commencement_or_effect_note"]
    assert "30 September" in paur["commencement_or_effect_note"]
    assert "not necessarily the licence expiry date" in paur["compliance_deadline"]


def test_bangladesh_bank_2026_circular_supersedes_account_instructions() -> None:
    payload = load_register()
    rule = next(r for r in payload["rules"] if r["rule_id"] == "INC-005")
    assert len(rule["candidate_provisions"]) == 6
    events = [e for e in rule["amendment_candidates"] if e["primary_record_id"] == "BD_BB_FEFD2_CIRCULAR_12_2026"]
    assert len(events) == 1
    event = events[0]
    assert event["claimed_effective_from"] == "2026-11-12"
    assert "repeals existing GFET-2018 Vol.1" in event["commencement_or_effect_note"]
    assert "Chapter 9 share-issuance reporting" in event["commencement_or_effect_note"]


def test_bsec_code_provisions_and_current_female_director_deadline_are_traced() -> None:
    payload = load_register()
    by_id = {rule["rule_id"]: rule for rule in payload["rules"]}
    assert by_id["BSEC-002"]["candidate_provisions"] == ["Corporate Governance Code 2018 Condition 9(1)–(3)"]
    assert by_id["BSEC-003"]["candidate_provisions"] == ["Corporate Governance Code 2018 Condition 1(2)(a), as amended"]
    assert by_id["BSEC-004"]["candidate_provisions"] == ["Corporate Governance Code 2018 Condition 5(1)(a)"]
    bsec3 = by_id["BSEC-003"]["amendment_candidates"]
    latest = [event for event in bsec3 if event["primary_record_id"] == "BD_BSEC_FEMALE_ID_EXTENSION_2026"]
    assert len(latest) == 1
    assert latest[0]["compliance_deadline"] == "2026-12-31"
    assert "not the existence" in latest[0]["commencement_or_effect_note"]
    assert "Foreign Exchange Regulation Act 1947" in by_id["BSEC-004"]["unresolved_items"][0]


def test_2005_companies_amendment_is_only_an_unresolved_lead() -> None:
    payload = load_register()
    candidates = payload["unresolved_instrument_candidates"]
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate["publication_date"] is None
    assert candidate["commencement_date"] is None
    assert candidate["primary_gazette_status"] == "NOT_LOCATED"
    assert candidate["status"].startswith("SECONDARY_CONSOLIDATED_FOOTNOTE_ONLY")


def test_companies_act_2020_amendments_are_not_conflated() -> None:
    payload = load_register()
    by_id = {r["rule_id"]: r for r in payload["rules"]}
    agm3_events = by_id["AGM-003"]["amendment_candidates"]
    act7 = [e for e in agm3_events if e["primary_record_id"] == "BD_ACT_7_2020"]
    act24 = [e for e in agm3_events if e["primary_record_id"] == "BD_ACT_24_2020"]
    assert act7 and act24
    assert "seal wording" in (act7[0]["commencement_or_effect_note"] or "")
    assert act7[0]["claimed_effective_from"] == "2020-02-25"
    assert act24[0]["claimed_effective_from"] == "2020-11-26"
    assert 85 in act24[0]["amended_provisions"]


def test_financial_reporting_act_2015_is_scoped_to_public_interest_entities() -> None:
    payload = load_register()
    rule = next(r for r in payload["rules"] if r["rule_id"] == "ACC-002")
    events = [
        event for event in rule["amendment_candidates"]
        if event["primary_record_id"] == "BD_ACT_16_2015_FINANCIAL_REPORTING"
    ]
    assert len(events) == 1
    event = events[0]
    assert event["amendment_clause_reference"] == "Financial Reporting Act 2015 s.62(b)"
    assert event["amended_provisions"] == [190]
    assert event["claimed_effective_from"] == "2015-09-09"
    assert "public interest entity" in event["commencement_or_effect_note"]
    assert event["rule_effect_status"] == "REQUIRES_PUBLIC_INTEREST_ENTITY_SCOPE_TEST_AND_COUNSEL_APPROVAL"


def test_all_non_null_candidate_dates_are_iso_calendar_dates() -> None:
    payload = load_register()
    for rule in payload["rules"]:
        for candidate in rule["amendment_candidates"]:
            for key in ("publication_date", "claimed_effective_from", "claimed_effective_to"):
                value = candidate[key]
                if value is not None:
                    date.fromisoformat(value)


def test_provision_gap_records_explain_missing_legal_mapping() -> None:
    payload = load_register()
    by_id = {rule["rule_id"]: rule for rule in payload["rules"]}
    expected = {
        "BSEC-001": "exact current operative paragraph",
        "FX-001": "exact enabling section",
        "INC-006": "exact guideline PDF/version",
        "TR-002": "exact Schedule I article",
    }
    for rule_id, required_detail in expected.items():
        rule = by_id[rule_id]
        assert rule["missing_provision_candidate"] is True
        assert any(
            item.startswith("PROVISION GAP:") and required_detail in item
            for item in rule["unresolved_items"]
        )


def test_vat_bill_passage_is_only_a_watch_item_not_an_enacted_source() -> None:
    payload = load_register()
    vat = next(rule for rule in payload["rules"] if rule["rule_id"] == "VAT-003")
    assert any(
        item.startswith("CURRENT-LAW WATCH:")
        and "No authenticated assent/Gazette artifact" in item
        and "not legal authority" in item
        for item in vat["unresolved_items"]
    )


def test_amendment_history_coverage_counters_match_rule_records() -> None:
    payload = load_register()
    rules = payload["rules"]
    coverage = payload["coverage"]
    assert coverage["located_primary_record_anchors"] == len(payload["located_primary_record_anchors"]) == 21
    assert coverage["amendment_candidate_entries"] == sum(len(rule["amendment_candidates"]) for rule in rules) == 74
    assert coverage["rules_with_amendment_candidates"] == sum(bool(rule["amendment_candidates"]) for rule in rules) == 27
    assert coverage["rules_without_amendment_candidates"] == sum(not rule["amendment_candidates"] for rule in rules) == 58
