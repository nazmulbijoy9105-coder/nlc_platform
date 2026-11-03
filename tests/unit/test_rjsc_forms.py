"""RJSC Forms tests."""

class TestRJSCForms:
    def test_form_reference_has_all_forms(self):
        from app.models.rjsc_forms import RJSC_FORMS_REFERENCE
        assert len(RJSC_FORMS_REFERENCE) == 14

    def test_form_reference_includes_key_forms(self):
        from app.models.rjsc_forms import RJSC_FORMS_REFERENCE
        codes = [f["form_code"] for f in RJSC_FORMS_REFERENCE]
        assert "FORM_XII" in codes
        assert "FORM_XV" in codes
        assert "FORM_117" in codes

    def test_verified_form_sections_and_deadlines(self):
        from app.models.rjsc_forms import RJSC_FORMS_REFERENCE
        forms = {item["form_code"]: item for item in RJSC_FORMS_REFERENCE}
        expected = {
            "FORM_I": ("Section 25", 0),
            "FORM_IV": ("Section 56", 15),
            "FORM_VIII": ("Section 88(1)", 15),
            "FORM_IX": ("Section 92", 30),
            "FORM_X": ("Section 92", 0),
            "FORM_XII": ("Section 115", 14),
            "FORM_XV": ("Section 151", 60),
            "FORM_XVIII": ("Section 159(1)", 21),
            "FORM_XIX": ("Section 167(3)", 21),
            "FORM_XXVIII": ("Section 172", 21),
            "SCHEDULE_X": ("Section 36", 21),
        }
        for code, (section, days) in expected.items():
            assert forms[code]["section"] == section
            assert forms[code]["deadline_days"] == days

    def test_each_form_has_rule_mapping(self):
        from app.models.rjsc_forms import RJSC_FORMS_REFERENCE
        for form in RJSC_FORMS_REFERENCE:
            if form["form_code"] in {"FORM_X", "FORM_XIX"}:
                assert form.get("rule_id") is None  # reference-only until CHG-002 is implemented
            else:
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
