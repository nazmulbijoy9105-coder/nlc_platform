"""RJSC Forms tests."""

class TestRJSCForms:
    def test_form_reference_has_all_forms(self):
        from app.models.rjsc_forms import RJSC_FORMS_REFERENCE
        assert len(RJSC_FORMS_REFERENCE) == 15

    def test_form_reference_includes_key_forms(self):
        from app.models.rjsc_forms import RJSC_FORMS_REFERENCE
        codes = [f["form_code"] for f in RJSC_FORMS_REFERENCE]
        assert "FORM_XII" in codes
        assert "FORM_XV" in codes
        assert "FORM_117" in codes
        assert "FORM_VIII" in codes
        assert "FORM_XVIII" in codes
        assert "FORM_XIX" in codes
        assert "FORM_XXVIII" in codes
        assert "FORM_X" in codes
        assert "FORM_23B" in codes

    def test_form_viii_is_special_resolution_not_charge_creation(self):
        from app.models.rjsc_forms import RJSC_FORMS_REFERENCE
        form = next(f for f in RJSC_FORMS_REFERENCE if f["form_code"] == "FORM_VIII")
        assert form["section"] == "Section 88(1)"
        assert form["deadline_days"] == 15

    def test_charge_forms_have_distinct_legal_functions(self):
        from app.models.rjsc_forms import RJSC_FORMS_REFERENCE
        forms = {f["form_code"]: f for f in RJSC_FORMS_REFERENCE}
        assert forms["FORM_XVIII"]["section"] == "Section 159(1)"
        assert forms["FORM_XIX"]["section"] == "Section 167(3)"
        assert forms["FORM_XXVIII"]["section"] == "Section 172"

    def test_each_form_has_rule_mapping_or_is_explicitly_reference_only(self):
        from app.models.rjsc_forms import RJSC_FORMS_REFERENCE
        reference_only = {"FORM_I", "FORM_X", "FORM_23B"}
        for form in RJSC_FORMS_REFERENCE:
            if form["form_code"] in reference_only:
                assert form.get("rule_id") is None
            else:
                assert form.get("rule_id"), f"Form {form['form_code']} missing rule_id"


    def test_incorporation_forms_match_rjsc_official_requirements(self):
        from app.models.rjsc_forms import RJSC_FORMS_REFERENCE
        forms = {f["form_code"]: f for f in RJSC_FORMS_REFERENCE}
        assert forms["FORM_I"]["section"] == "Section 25"
        assert forms["FORM_X"]["section"] == "Section 92"
        assert forms["FORM_X"]["rule_id"] is None

    def test_form_23b_is_separate_from_company_first_auditor_appointment(self):
        from app.models.rjsc_forms import RJSC_FORMS_REFERENCE
        form = next(f for f in RJSC_FORMS_REFERENCE if f["form_code"] == "FORM_23B")
        assert form["section"] == "Section 210(2)"
        assert form["rule_id"] is None
        assert form["deadline_days"] is None

    def test_each_form_has_section_reference(self):
        from app.models.rjsc_forms import RJSC_FORMS_REFERENCE
        for form in RJSC_FORMS_REFERENCE:
            assert form.get("section"), f"Form {form['form_code']} missing section"

    def test_model_has_correct_tablename(self):
        from app.models.rjsc_forms import RJSCFormFiling
        assert RJSCFormFiling.__tablename__ == "rjsc_form_filings"

    def test_model_has_required_fields(self):
        from app.models.rjsc_forms import RJSCFormFiling
        cols = {c.name for c in RJSCFormFiling.__table__.columns}
        assert "company_id" in cols
        assert "form_code" in cols
        assert "filing_status" in cols

    def test_deadline_days_present(self):
        from app.models.rjsc_forms import RJSC_FORMS_REFERENCE
        for form in RJSC_FORMS_REFERENCE:
            assert "deadline_days" in form
