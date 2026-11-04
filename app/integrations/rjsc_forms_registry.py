"""
NLC — RJSC Statutory Forms Registry
Maps internal compliance rules to official RJSC statutory forms.
"""
from dataclasses import dataclass


@dataclass
class RJSCForm:
    form_code: str
    form_name: str
    purpose: str
    related_rules: list[str]
    download_url: str = ""  # Populated dynamically or manually verified

# Official mapping of Bangladesh Companies Act 1994 forms
RJSC_FORMS_REGISTRY: dict[str, RJSCForm] = {
    "FORM_XII": RJSCForm(
        form_code="FORM_XII",
        form_name="Notice of Change in Directors",
        purpose="Notify appointment/resignation/removal of directors.",
        related_rules=["DIR-001", "DIR-002", "DIR-003"],
        download_url="https://app.roc.gov.bd/Guidlines/Download/Form-XII.doc"
    ),
    "FORM_X": RJSCForm(
        form_code="FORM_X",
        form_name="Annual Return",
        purpose="Statutory annual return filing (Schedule X).",
        related_rules=["AR-001", "AR-002"],
        download_url="https://app.roc.gov.bd/Guidlines/Download/Form-X.pdf"
    ),
    "FORM_VI": RJSCForm(
        form_code="FORM_VI",
        form_name="Notice of Change of Registered Office",
        purpose="Notify change of registered office address.",
        related_rules=["OFF-001"],
        download_url="https://app.roc.gov.bd/Guidlines/Download/Form-VI.doc"
    ),
    "FORM_VIII": RJSCForm(
        form_code="FORM_VIII",
        form_name="Special or Extraordinary Resolution",
        purpose="File a copy of a special or extraordinary resolution within 15 days under Section 88(1).",
        related_rules=["CAP-004", "STR-001", "STR-002", "STR-003"],
        download_url=""
    ),
    "FORM_XV": RJSCForm(
        form_code="FORM_XV",
        form_name="Return of Allotment",
        purpose="File return of allotment within 60 days under Section 151.",
        related_rules=["SH-001"],
        download_url=""
    ),
    "FORM_XVIII": RJSCForm(
        form_code="FORM_XVIII",
        form_name="Particulars of a Charge",
        purpose="Register creation of a mortgage or charge within 21 days under Section 159.",
        related_rules=["CAP-002"],
        download_url=""
    ),
    "FORM_XIX": RJSCForm(
        form_code="FORM_XIX",
        form_name="Particulars of Modification of Mortgage or Charge",
        purpose="File modification within 21 days under Section 167(3).",
        related_rules=["CHG-002"],
        download_url=""
    ),
    "FORM_XXVIII": RJSCForm(
        form_code="FORM_XXVIII",
        form_name="Memorandum of Satisfaction of Mortgage or Charge",
        purpose="File satisfaction within 21 days; Section 172 and RJSC process guidance.",
        related_rules=["CHG-001"],
        download_url=""
    )
}

def get_form_for_rule(rule_id: str) -> RJSCForm | None:
    """Find the official RJSC form required to resolve a specific compliance flag."""
    for form in RJSC_FORMS_REGISTRY.values():
        if rule_id in form.related_rules:
            return form
    return None
