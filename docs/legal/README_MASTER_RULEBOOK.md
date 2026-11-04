# Bangladesh Companies Law Master Rulebook — file map

**Version:** 1.0.0  
**Prepared:** 4 November 2026  
**Status:** Counsel-validation draft; not approved for legal determinations.

## Canonical source files in this repository

| File | Format | Purpose |
|---|---|---|
| `NLC_BD_COMPANIES_LAW_MASTER_RULEBOOK_v1.0.md` | Markdown | Human-readable master rulebook; canonical editable source |
| `NLC_BD_COMPANIES_LAW_RULES_v1.0.json` | JSON | Machine-readable 85-rule catalogue and governance metadata |
| `NLC_BD_COMPANIES_LAW_RULES_v1.0.csv` | CSV | Counsel review / spreadsheet import |
| `COUNSEL_VALIDATION_CHECKLIST_v1.0.md` | Markdown | Rule-by-rule senior counsel sign-off checklist |
| `AMENDMENT_AND_EFFECTIVE_DATE_REGISTER_v1.0.md` | Markdown | Chronological amendment and commencement register template |

## PDF

The 9-page PDF was generated as a review copy for this conversation:
`NLC_Bangladesh_Companies_Law_Master_Rulebook_v1.0_Counsel_Draft.pdf`

It is not committed as a binary in this repository. The GitHub integration used for this task supports text-file commits, not binary PDF uploads. The Markdown master is the editable source; the PDF must be regenerated from the approved source when the build pipeline is added.

## Rule status and activation policy

All 85 records are marked `SOURCE_STATUS=ENGINE_ALIGNED_NOT_COUNSEL_VALIDATED` and `legal_validation=PENDING`. Existing severity, score and override values are copied from the current legal-basis matrix solely for traceability; they are not counsel-approved legal consequences. Do not activate these records for autonomous legal determinations until the senior counsel checklist is signed and effective-date, company-type, Articles and company-fact applicability have been resolved.

## Recommended repository layout

- Markdown: authoritative human-readable source and review narrative.
- JSON: canonical machine-readable data contract for future loader/migrations.
- CSV: review convenience only; never use CSV as the production source of truth.
- PDF: generated publication artifact, not the canonical editable source.
- Counsel checklist and amendment register: signed governance evidence.

**Coverage limitation:** 85 entries represent the rules currently present in NLC's matrix. This does not establish exhaustive coverage of Bangladesh company law or all sectoral obligations.
