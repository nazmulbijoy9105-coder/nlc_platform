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

    def test_form_viii_is_special_resolution_not_charge_creation(self):
        from app.models.rjsc_forms import RJSC_FORMS_REFERENCE
        form = next(f for f in RJSC_FORMS_REFERENCE if f["form_code"] == "FORM_VIII")
        assert form["section"] == "Section 88(1)"
        assert form["deadline_days"] == 15

    def test_charge_forms_have_distinct_legal_functions(self):
        from app.models.rjsc_forms import RJSC_FORMS_REFERENCE
        forms = {f["form_code"]: f for f in RJSC_FORMS_REFERENCE}
        assert forms["FORM_XVIII"]["section"] == "Section 159"
        assert forms["FORM_XIX"]["section"] == "Section 167(3)"
        assert forms["FORM_XXVIII"]["section"] == "Section 172"

    def test_each_form_has_rule_mapping(self):
        from app.models.rjsc_forms import RJSC_FORMS_REFERENCE
        for form in RJSC_FORMS_REFERENCE:
            assert form.get("rule_id") or form.get("deadline_days") == 0, f"Form {form['form_code']} missing rule_id"

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
