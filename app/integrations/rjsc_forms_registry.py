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
        form_name="Particulars of a Charge",
        purpose="Register a charge/mortgage with RJSC.",
        related_rules=["CAP-002"],
        download_url="https://app.roc.gov.bd/Guidlines/Download/Form-VIII.doc"
    ),
    "FORM_XV": RJSCForm(
        form_code="FORM_XV",
        form_name="Notice of Consolidation, Division, or Sub-division of Shares",
        purpose="Notify changes in share capital structure.",
        related_rules=["SH-001", "SH-003"],
        download_url="https://app.roc.gov.bd/Guidlines/Download/Form-XV.doc"
    )
}

def get_form_for_rule(rule_id: str) -> RJSCForm | None:
    """Find the official RJSC form required to resolve a specific compliance flag."""
    for form in RJSC_FORMS_REGISTRY.values():
        if rule_id in form.related_rules:
            return form
    return None
