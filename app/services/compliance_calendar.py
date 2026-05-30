"""NEUM LEX COUNSEL - Compliance Calendar Service"""
from __future__ import annotations
import uuid
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.company import Company
from app.models.enums import CompanyStatus, CompanyType
import logging
logger = logging.getLogger("nlc.calendar")
RJSC_DAYS = {"agm": 180, "schedule_x": 21, "balance_sheet": 30}
TAX_RETURN_MONTHS_AFTER_FY = 6
ADVANCE_TAX_QUARTERS = [("Q1", 9, 15), ("Q2", 12, 15), ("Q3", 3, 15), ("Q4", 6, 15)]
RJSC_DAILY_FINE_BDT = 500
RJSC_FINE_CAP_PER_FY_BDT = 50_000
def _fmt(d): return d.strftime("%d-%b-%Y")
def _fmt_month(d): return d.strftime("%b %Y")
def _fy_label(s, e): return str(s.year) + "-" + str(e.year)[-2:]
def _priority(event_type, days_remaining):
    if days_remaining < 0: return "OVERDUE"
    if days_remaining <= 7: return "URGENT"
    if days_remaining <= 30: return "HIGH"
    if event_type in ("agm", "corporate_tax_return", "cg_certificate"): return "HIGH"
    return "MEDIUM"
def _get_fiscal_years(incorporation_date, fy_end_str):
    mm, dd = map(int, fy_end_str.split("-"))
    today = date.today()
    fiscal_years = []
    first_fy_end = date(incorporation_date.year, mm, dd)
    if first_fy_end < incorporation_date:
        first_fy_end = date(incorporation_date.year + 1, mm, dd)
    fy_start = incorporation_date
    fy_end = first_fy_end
    while fy_start <= today:
        fiscal_years.append((fy_start, fy_end))
        fy_start = fy_end + timedelta(days=1)
        next_year = fy_start.year + (1 if mm < fy_start.month or (mm == fy_start.month and dd < fy_start.day) else 0)
        try: fy_end = date(next_year, mm, dd)
        except ValueError: fy_end = date(next_year, mm, 28)
    return fiscal_years
def _rjsc_events(fy):
    fy_start, fy_end = fy
    label = _fy_label(fy_start, fy_end)
    agm_due = fy_end + timedelta(days=RJSC_DAYS["agm"])
    sx_due = agm_due + timedelta(days=RJSC_DAYS["schedule_x"])
    bs_due = agm_due + timedelta(days=RJSC_DAYS["balance_sheet"])
    today = date.today()
    return [
        {"event_type": "agm", "category": "RJSC", "title": "Annual General Meeting FY " + label,
         "description": "AGM within 6 months of FY end (" + _fmt(fy_end) + "). s.81 Companies Act 1994.",
         "due_date": datetime.combine(agm_due, datetime.min.time()), "fiscal_year": label, "form": None,
         "priority": _priority("agm", (agm_due - today).days),
         "penalty_per_day_bdt": RJSC_DAILY_FINE_BDT, "penalty_cap_bdt": RJSC_FINE_CAP_PER_FY_BDT,
         "statutory_ref": "s.81 Companies Act 1994"},
        {"event_type": "schedule_x", "category": "RJSC", "title": "Annual Return (Schedule X) FY " + label,
         "description": "Filed within 21 days of AGM. s.190 CA 1994.",
         "due_date": datetime.combine(sx_due, datetime.min.time()), "fiscal_year": label, "form": "Schedule X",
         "priority": _priority("schedule_x", (sx_due - today).days),
         "penalty_per_day_bdt": RJSC_DAILY_FINE_BDT, "penalty_cap_bdt": RJSC_FINE_CAP_PER_FY_BDT,
         "statutory_ref": "s.190 Companies Act 1994"},
        {"event_type": "balance_sheet", "category": "RJSC", "title": "Audited Financial Statements FY " + label,
         "description": "Balance Sheet and P&L within 30 days of AGM. Requires DVC. s.190 CA 1994.",
         "due_date": datetime.combine(bs_due, datetime.min.time()), "fiscal_year": label, "form": "Balance Sheet & P&L",
         "priority": _priority("balance_sheet", (bs_due - today).days),
         "penalty_per_day_bdt": RJSC_DAILY_FINE_BDT, "penalty_cap_bdt": RJSC_FINE_CAP_PER_FY_BDT,
         "statutory_ref": "s.190 Companies Act 1994"},
    ]
def _tax_events(fy, *, has_vat):
    fy_start, fy_end = fy
    label = _fy_label(fy_start, fy_end)
    today = date.today()
    events = []
    tax_due = fy_end + relativedelta(months=TAX_RETURN_MONTHS_AFTER_FY)
    tax_due = (tax_due.replace(day=1) + relativedelta(months=1)) - timedelta(days=1)
    events.append({"event_type": "corporate_tax_return", "category": "NBR",
        "title": "Corporate Income Tax Return FY " + label,
        "description": "IT-11G due " + _fmt(tax_due) + ". Penalty: 2% monthly interest.",
        "due_date": datetime.combine(tax_due, datetime.min.time()), "fiscal_year": label, "form": "IT-11G",
        "priority": _priority("corporate_tax_return", (tax_due - today).days),
        "penalty_per_day_bdt": None, "penalty_cap_bdt": None, "statutory_ref": "Income Tax Act 2023 s.166"})
    for q_label, month, day in ADVANCE_TAX_QUARTERS:
        for year_offset in range(2):
            try: adv_date = date(fy_start.year + year_offset, month, day)
            except ValueError: continue
            if fy_start <= adv_date <= fy_end + timedelta(days=90):
                events.append({"event_type": "advance_tax_" + q_label.lower(), "category": "NBR",
                    "title": "Advance Tax " + q_label + " FY " + label,
                    "description": "Quarterly advance tax due " + _fmt(adv_date) + ".",
                    "due_date": datetime.combine(adv_date, datetime.min.time()), "fiscal_year": label, "form": "Challan",
                    "priority": _priority("advance_tax", (adv_date - today).days),
                    "penalty_per_day_bdt": None, "penalty_cap_bdt": None, "statutory_ref": "Income Tax Act 2023 s.185"})
                break
    if has_vat:
        current_month = fy_start.replace(day=1)
        future_limit = today + timedelta(days=60)
        while current_month <= min(fy_end, future_limit):
            vat_due = (current_month + relativedelta(months=1)).replace(day=15)
            events.append({"event_type": "vat_return", "category": "NBR",
                "title": "VAT Return (Mushak 9.1) - " + _fmt_month(current_month),
                "description": "Monthly VAT return due by 15th. Penalty: BDT 10,000 or 5% of VAT due.",
                "due_date": datetime.combine(vat_due, datetime.min.time()), "fiscal_year": label, "form": "Mushak 9.1",
                "priority": _priority("vat_return", (vat_due - today).days),
                "penalty_per_day_bdt": None, "penalty_cap_bdt": 10_000, "statutory_ref": "VAT and SD Act 2012 s.71"})
            current_month += relativedelta(months=1)
    return events
def _bsec_events(fy):
    fy_start, fy_end = fy
    label = _fy_label(fy_start, fy_end)
    today = date.today()
    events = []
    for q_label, month, day in [("Q1", 9, 30), ("Q2", 12, 31), ("Q3", 3, 31)]:
        year = fy_start.year if month > 6 else fy_end.year
        try: q_end = date(year, month, day)
        except ValueError: q_end = date(year, month, 28)
        report_due = q_end + timedelta(days=45)
        events.append({"event_type": "bsec_" + q_label.lower() + "_report", "category": "BSEC",
            "title": q_label + " Financial Report FY " + label,
            "description": "Quarterly report due within 45 days of quarter end (" + _fmt(q_end) + ").",
            "due_date": datetime.combine(report_due, datetime.min.time()), "fiscal_year": label, "form": "BSEC Quarterly Report",
            "priority": _priority("bsec_report", (report_due - today).days),
            "penalty_per_day_bdt": None, "penalty_cap_bdt": 100_000, "statutory_ref": "BSEC Corporate Governance Code 2023"})
    agm_due = fy_end + timedelta(days=RJSC_DAYS["agm"])
    cg_due = agm_due + timedelta(days=30)
    events.append({"event_type": "cg_certificate", "category": "BSEC",
        "title": "Corporate Governance Certificate FY " + label,
        "description": "Certified by practicing accountant/CS. BSEC CG Code 2023 para 9.",
        "due_date": datetime.combine(cg_due, datetime.min.time()), "fiscal_year": label, "form": "CG Certificate",
        "priority": _priority("cg_certificate", (cg_due - today).days),
        "penalty_per_day_bdt": None, "penalty_cap_bdt": 100_000, "statutory_ref": "BSEC Corporate Governance Code 2023 para 9"})
    return events
def _trade_license_event(company):
    expiry = getattr(company, "trade_license_expiry", None)
    if not expiry: return None
    if isinstance(expiry, datetime): expiry = expiry.date()
    today = date.today()
    return {"event_type": "trade_license_renewal", "category": "TRADE_LICENSE",
        "title": "Trade License Renewal - " + str(getattr(company, "trade_license_number", "N/A")),
        "description": "Expires " + _fmt(expiry) + ". Renew before expiry.",
        "due_date": datetime.combine(expiry, datetime.min.time()), "fiscal_year": None, "form": "Trade License Application",
        "priority": _priority("trade_license", (expiry - today).days),
        "penalty_per_day_bdt": None, "penalty_cap_bdt": None, "statutory_ref": "City Corporation Ordinance"}
def _generate_calendar(company):
    if not company.incorporation_date: return []
    fy_end_date = company.financial_year_end
    fy_end_str = ("%02d-%02d" % (fy_end_date.month, fy_end_date.day)) if fy_end_date else "12-31"
    is_dormant = company.company_status == CompanyStatus.DORMANT
    has_vat = bool(getattr(company, "vat_number", None))
    is_listed = bool(getattr(company, "is_listed", False))
    fiscal_years = _get_fiscal_years(company.incorporation_date, fy_end_str)
    all_events = []
    for fy in fiscal_years:
        if not is_dormant: all_events.extend(_rjsc_events(fy))
        all_events.extend(_tax_events(fy, has_vat=has_vat))
        if is_listed: all_events.extend(_bsec_events(fy))
    tl = _trade_license_event(company)
    if tl: all_events.append(tl)
    return all_events
class ComplianceCalendarService:
    def __init__(self, db): self.db = db
    async def get_calendar(self, company_id, *, include_past_days=365, include_future_days=365):
        result = await self.db.execute(select(Company).where(Company.id == company_id))
        company = result.scalar_one_or_none()
        if not company: return []
        events = _generate_calendar(company)
        cutoff_past = datetime.now() - timedelta(days=include_past_days)
        cutoff_future = datetime.now() + timedelta(days=include_future_days)
        filtered = [e for e in events if cutoff_past <= e["due_date"] <= cutoff_future]
        filtered.sort(key=lambda x: x["due_date"])
        return filtered
    async def get_upcoming(self, company_id, days_ahead=30):
        return await self.get_calendar(company_id, include_past_days=0, include_future_days=days_ahead)
    async def get_overdue(self, company_id):
        events = await self.get_calendar(company_id, include_past_days=365, include_future_days=0)
        return [e for e in events if e["due_date"] < datetime.now()]
def calculate_penalty(event_type, days_overdue, fy_count=1):
    if days_overdue <= 0: return 0
    if event_type in ("schedule_x", "balance_sheet", "agm"):
        return min(days_overdue * RJSC_DAILY_FINE_BDT, RJSC_FINE_CAP_PER_FY_BDT) * max(fy_count, 1)
    if event_type == "corporate_tax_return": return days_overdue * 100
    if event_type == "vat_return": return 10_000
    if event_type.startswith("bsec_"): return 100_000
    return 0