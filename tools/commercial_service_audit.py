#!/usr/bin/env python3
"""
NLC — Total Commercial Service Coverage Forensic Audit
Automates the grep/find commands to audit the entire codebase for commercial features.
"""
import os
import re
import subprocess
from pathlib import Path

def run_command(cmd):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, errors='ignore')
        return result.stdout
    except Exception:
        return ""

def recursive_grep(pattern, directories, include_exts=None):
    if include_exts is None:
        include_exts = [".py", ".ts", ".tsx", ".js", ".jsx"]
    
    results = []
    regex = re.compile(pattern, re.IGNORECASE)
    
    for directory in directories:
        if not os.path.exists(directory):
            continue
        for root, dirs, files in os.walk(directory):
            if "__pycache__" in root or "node_modules" in root or ".git" in root:
                continue
            for file in files:
                if not any(file.endswith(ext) for ext in include_exts):
                    continue
                    
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        for i, line in enumerate(f, 1):
                            if regex.search(line):
                                results.append(f"{filepath}:{i}:{line.rstrip()}")
                except Exception:
                    pass
    return results

def main():
    print("==============================================================")
    print("NLC — TOTAL COMMERCIAL SERVICE COVERAGE FORENSIC AUDIT")
    print("==============================================================")
    
    # [0] REPOSITORY BASELINE
    print("\n[0] REPOSITORY BASELINE")
    print("==============================================================")
    print(f"BRANCH={run_command(['git', 'branch', '--show-current']).strip()}")
    print(f"HEAD={run_command(['git', 'rev-parse', 'HEAD']).strip()}")
    print(f"HEAD_SHORT={run_command(['git', 'rev-parse', '--short', 'HEAD']).strip()}")
    print("\nWORKTREE:")
    print(run_command(['git', 'status', '--short']))
    
    # [1] APPLICATION STRUCTURE
    print("\n[1] APPLICATION STRUCTURE")
    print("==============================================================")
    app_files = sorted([str(p) for p in Path("app").rglob("*") if p.is_file()])
    print("\n".join(app_files))
    print(f"\n[BACKEND FILE COUNT]\n{len(app_files)}")
    
    test_files = sorted([str(p) for p in Path("tests").rglob("*") if p.is_file()])
    print("\n[TEST FILES]")
    print("\n".join(test_files))
    
    print("\n[ROUTES / ENDPOINTS]")
    routes = recursive_grep(r"APIRouter|router\.(get|post|put|patch|delete)|@app\.(get|post|put|patch|delete)|Route\(", ["app"])
    print("\n".join(routes))
    
    # [2] CUSTOMER + COMPANY ONBOARDING
    print("\n[2] CUSTOMER + COMPANY ONBOARDING")
    print("==============================================================")
    res = recursive_grep(r"register|registration|signup|sign.?up|onboard|onboarding|tenant|organization|workspace|company|company.?profile|client", ["app", "tests"])
    print("\n".join(res))

    # [3] CORPORATE COMPLIANCE SERVICE DISCOVERY
    print("\n[3] CORPORATE COMPLIANCE SERVICE DISCOVERY")
    print("==============================================================")
    res = recursive_grep(r"annual.?return|annual.?report|AGM|general.?meeting|board|director|shareholder|share.?transfer|share.?capital|auditor|registered.?office|charge|beneficial|ownership|incorporat|RJSC|filing|statutory|compliance", ["app", "tests", "canonical_architecture", "scripts"])
    print("\n".join(res))

    # [4] SPECIAL / REGULATORY SERVICE DISCOVERY
    print("\n[4] SPECIAL / REGULATORY SERVICE DISCOVERY")
    print("==============================================================")
    res = recursive_grep(r"BSEC|bank|banking|FX|foreign.?exchange|foreign.?investment|VAT|tax|labou?r|labour|strike.?off|restoration|winding.?up|liquidat|insolv|restructur|merger|acquisition|sector.?specific", ["app", "tests", "canonical_architecture", "scripts"])
    print("\n".join(res))

    # [5] MONITORING / RISK / EVALUATION
    print("\n[5] MONITORING / RISK / EVALUATION")
    print("==============================================================")
    res = recursive_grep(r"rule.?engine|evaluate|evaluation|compliance.?score|score|risk|GREEN|YELLOW|RED|BLACK|deadline|due.?date|calendar|monitor|monitoring|violation|finding|flag|applicability|exception|evidence", ["app", "tests", "canonical_architecture", "scripts"])
    print("\n".join(res))

    # [6] DOCUMENT SERVICE DISCOVERY
    print("\n[6] DOCUMENT SERVICE DISCOVERY")
    print("==============================================================")
    res = recursive_grep(r"document|document.?template|resolution|minutes|notice|certificate|draft|generate|generation|PDF|upload|download|attachment|version|approval|approve|review|release", ["app", "tests", "canonical_architecture", "scripts"])
    print("\n".join(res))

    # [7] AI / HUMAN REVIEW / APPROVAL
    print("\n[7] AI / HUMAN REVIEW / APPROVAL")
    print("==============================================================")
    res = recursive_grep(r"AI|LLM|OpenAI|model|prompt|completion|draft|human.?review|legal.?review|reviewer|approved|approval|approved.?by|released|release|publish|provenance", ["app", "tests"])
    print("\n".join(res))

    # [8] FILING / RJSC WORKFLOW
    print("\n[8] FILING / RJSC WORKFLOW")
    print("==============================================================")
    res = recursive_grep(r"RJSC|filing|submission|submitted|submit|application|form|e.?filing|filing.?status|accepted|rejected|rejection|resubmit|follow.?up|tracking|tracking.?number|receipt|challan", ["app", "tests"])
    print("\n".join(res))

    # [9] REGULARIZATION / RESCUE
    print("\n[9] REGULARIZATION / RESCUE")
    print("==============================================================")
    res = recursive_grep(r"rescue|regulari[sz]ation|remediation|remedy|corrective|recovery|corporate.?rescue|action.?plan|rescue.?plan|triggered.?by|evaluator.?finding|finding", ["app", "tests", "canonical_architecture", "scripts"])
    print("\n".join(res))

    # [10] PREMIUM SUPPORT
    print("\n[10] PREMIUM SUPPORT")
    print("==============================================================")
    res = recursive_grep(r"support|ticket|helpdesk|case|matter|request|service.?request|priority|urgent|critical|SLA|service.?level|escalat|assignment|assigned|account.?manager|relationship.?manager|dedicated", ["app", "tests"])
    print("\n".join(res))

    # [11] CUSTOMER COMMUNICATION
    print("\n[11] CUSTOMER COMMUNICATION")
    print("==============================================================")
    res = recursive_grep(r"email|SMTP|WhatsApp|Twilio|notification|alert|SMS|message|in.?app|webhook|reminder|deadline.?alert|escalation|communication", ["app", "tests"])
    print("\n".join(res))

    # [12] BILLING / SUBSCRIPTION / COMMERCIAL
    print("\n[12] BILLING / SUBSCRIPTION / COMMERCIAL")
    print("==============================================================")
    res = recursive_grep(r"billing|invoice|payment|subscription|plan|pricing|price|premium|enterprise|tier|package|entitlement|usage|quota|limit|renew|renewal|upgrade|downgrade|cancel|refund|revenue|engagement", ["app", "tests"])
    print("\n".join(res))

    # [13] REPORTING / CERTIFICATES / MANAGEMENT
    print("\n[13] REPORTING / CERTIFICATES / MANAGEMENT")
    print("==============================================================")
    res = recursive_grep(r"report|reporting|dashboard|certificate|compliance.?certificate|compliance.?report|management.?report|portfolio|export|CSV|Excel|PDF|summary|analytics|metric", ["app", "tests"])
    print("\n".join(res))

    # [14] FRONTEND / CUSTOMER-FACING SURFACES
    print("\n[14] FRONTEND / CUSTOMER-FACING SURFACES")
    print("==============================================================")
    frontend_files = []
    for root, dirs, files in os.walk("."):
        if "node_modules" in root or ".git" in root:
            continue
        for file in files:
            if file.endswith((".tsx", ".ts", ".jsx", ".js")):
                frontend_files.append(os.path.join(root, file))
    print("\n".join(sorted(frontend_files)))
    
    print("\n[CUSTOMER-FACING TERMS]")
    res = recursive_grep(r"dashboard|companies|filings|documents|rescue|profile|support|billing|subscription|settings|notification|report|compliance", ["."])
    print("\n".join(res))

    # [15] AUTHORIZATION / TENANT / OBJECT ACCESS
    print("\n[15] AUTHORIZATION / TENANT / OBJECT ACCESS")
    print("==============================================================")
    res = recursive_grep(r"permission|permissions|role|RBAC|authorize|authorization|authentication|tenant_id|organization_id|membership|super.?admin|admin|owner|staff|member|is_active|suspend|deactiv|company_id|filing_id|document_id|rescue_id|engagement_id", ["app", "tests"])
    print("\n".join(res))

    # [16] AUDIT TRAIL
    print("\n[16] AUDIT TRAIL")
    print("==============================================================")
    res = recursive_grep(r"audit|audit.?log|event|event.?log|hash|hash.?chain|previous.?hash|actor|performed.?by|created.?by|approved.?by|timestamp|immutable|tamper", ["app", "tests", "canonical_architecture"])
    print("\n".join(res))

    # [17] LEGAL MATTER / ENGAGEMENT MANAGEMENT
    print("\n[17] LEGAL MATTER / ENGAGEMENT MANAGEMENT")
    print("==============================================================")
    res = recursive_grep(r"engagement|matter|case|legal.?matter|client.?matter|work.?order|service.?order|retainer|consultation|appointment|advisory|legal.?service", ["app", "tests"])
    print("\n".join(res))

    # [18] WORKFLOW STATES
    print("\n[18] WORKFLOW STATES")
    print("==============================================================")
    res = recursive_grep(r"status.*(draft|pending|review|approved|rejected|submitted|accepted|completed|closed|cancelled|open|assigned|resolved)|DRAFT|PENDING|REVIEW|APPROVED|REJECTED|SUBMITTED|ACCEPTED|COMPLETED|RESOLVED|CLOSED", ["app", "tests"])
    print("\n".join(res))

    # [20] DATABASE MIGRATIONS
    print("\n[20] DATABASE MIGRATIONS")
    print("==============================================================")
    migrations = []
    for root, dirs, files in os.walk("."):
        if "node_modules" in root or ".git" in root:
            continue
        if "migrations" in root or "migration" in root:
            for file in files:
                if file.endswith(".py") or file.endswith(".sql"):
                    migrations.append(os.path.join(root, file))
        elif any("migration" in f for f in files):
             for file in files:
                if file.endswith(".py") or file.endswith(".sql"):
                    migrations.append(os.path.join(root, file))
    print("\n".join(sorted(migrations)))

    # [21] FRONTEND ROUTES / PAGES
    print("\n[21] FRONTEND ROUTES / PAGES")
    print("==============================================================")
    res = recursive_grep(r"path=|route|Routes|createBrowserRouter|router|/dashboard|/companies|/filings|/documents|/rescue|/support|/billing|/profile", ["."])
    print("\n".join(res))

    # [22] COMMERCIAL SERVICE TEST COVERAGE
    print("\n[22] COMMERCIAL SERVICE TEST COVERAGE")
    print("==============================================================")
    res = recursive_grep(r"test.*(company|filing|document|rescue|support|billing|subscription|payment|notification|report|compliance|annual|AGM|director|share|auditor)|support|billing|subscription|payment|document|filing|rescue|notification", ["tests"])
    print("\n".join(res))

    # [23] UNFINISHED / PLACEHOLDER COMMERCIAL FEATURES
    print("\n[23] UNFINISHED / PLACEHOLDER COMMERCIAL FEATURES")
    print("==============================================================")
    res = recursive_grep(r"TODO|FIXME|XXX|HACK|not.?implemented|NotImplemented|placeholder|coming.?soon|stub|mock|fake|temporary|pass[[:space:]]*#|raise NotImplemented", ["app", "tests"])
    print("\n".join(res))

    # [24] GIT HISTORY — COMMERCIAL SERVICE TERMS
    print("\n[24] GIT HISTORY — COMMERCIAL SERVICE TERMS")
    print("==============================================================")
    print(run_command(["git", "log", "--oneline", "--all", "--decorate", "--", "app", "tests", "canonical_architecture", "scripts"]))
    
    print("\n[SERVICE-RELATED COMMITS]")
    print(run_command(["git", "log", "--all", "--oneline", "--regexp-ignore-case", "--grep=support|billing|subscription|filing|document|rescue|compliance|company|tenant|authorization|notification|report"]))

    # [25] POTENTIAL ORPHAN / UNUSED SERVICE CODE
    print("\n[25] POTENTIAL ORPHAN / UNUSED SERVICE CODE")
    print("==============================================================")
    res = recursive_grep(r"TODO|FIXME|deprecated|obsolete|unused|dead.?code|legacy|migration.?only|deprecated", ["app", "canonical_architecture", "scripts"])
    print("\n".join(res))

if __name__ == "__main__":
    main()
