"""RJSC Forms tests."""

class TestRJSCForms:
    def test_form_reference_has_all_forms(self):
                from app.models.rjsc_forms import RJSC_FORMS_REFERENCE
        assert len(RJSC_FORMS_REFERENCE) == 13


    def test_form_reference_includes_key_forms(self):
                from app.models.rjsc_forms import RJSC_FORMS_REFERENCE
        codes = [f["form_code"] for f in RJSC_FORMS_REFERENCE]
        assert "FORM_XII" in codes
        assert "FORM_XV" in codes
        assert "FORM_117" in codes


    def test_each_form_has_rule_mapping(self):
                from app.models.rjsc_forms import RJSC_FORMS_REFERENCE
        for form in RJSC_FORMS_REFERENCE:
            assert form.get("rule_id"), f"Form {form['form_code']} missing rule_id"


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

