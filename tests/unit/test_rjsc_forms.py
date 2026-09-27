"""RJSC Forms tests"""

class TestRJSCForms:
    """Verify RJSC form management."""

    def test_form_reference_has_all_forms(self):
        """Reference should contain all 13 RJSC forms."""
        from app.models.rjsc_forms import RJSC_FORMS_REFERENCE
        assert len(RJSC_FORMS_REFERENCE) == 13, f"Expected 13 forms, got {len(RJSC_FORMS_REFERENCE)}"

    def test_form_reference_includes_key_forms(self):
        """Key forms (XII, XV, 117, VIII) should be in reference."""
        from app.models.rjsc_forms import RJSC_FORMS_REFERENCE
        codes = [f["form_code"] for f in RJSC_FORMS_REFERENCE]
        assert "FORM_XII" in codes, "Annual Return (Form XII) missing"
        assert "FORM_XV" in codes, "Return of Allotment (Form XV) missing"
        assert "FORM_117" in codes, "Transfer Instrument (Form 117) missing"
        assert "FORM_VIII" in codes, "Charge Registration (Form VIII) missing"

    def test_each_form_has_rule_mapping(self):
        """Each form should map to a rule_id."""
        from app.models.rjsc_forms import RJSC_FORMS_REFERENCE
        for form in RJSC_FORMS_REFERENCE:
            assert form["rule_id"], f"Form {form['form_code']} missing rule_id"

    def test_each_form_has_section_reference(self):
        """Each form should reference a Companies Act section."""
        from app.models.rjsc_forms import RJSC_FORMS_REFERENCE
        for form in RJSC_FORMS_REFERENCE:
            assert form["section"], f"Form {form['form_code']} missing section reference"

    def test_model_has_correct_tablename(self):
        """RJSCFormFiling should have correct table name."""
        from app.models.rjsc_forms import RJSCFormFiling
        assert RJSCFormFiling.__tablename__ == "rjsc_form_filings"

    def test_model_has_required_fields(self):
        """Model should have all required fields."""
        from app.models.rjsc_forms import RJSCFormFiling
        cols = {c.name for c in RJSCFormFiling.__table__.columns}
        required = {"id", "company_id", "form_code", "form_number", "form_name",
                    "section_reference", "filing_status", "due_date", "filed_date"}
        missing = required - cols
        assert not missing, f"Missing columns: {missing}"

    def test_deadline_days_present(self):
        """Each form should have deadline_days."""
        from app.models.rjsc_forms import RJSC_FORMS_REFERENCE
        for form in RJSC_FORMS_REFERENCE:
            assert "deadline_days" in form, f"Form {form['form_code']} missing deadline_days"
