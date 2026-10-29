#!/usr/bin/env python3
"""Merge per-category deduction caps into _calculate_score (100-point model v2).

- UNKNOWN / DISPUTED never count: violations list is already NON_COMPLIANT-only.
- Each category's deduction is capped before summing, so no single category
  can swamp the 100-point scale.
- The 14 existing *_ded sums are reused and capped in place, so any
  ScoreBreakdown category fields stay consistent with the capped total.
Run: python tools/merge_category_caps.py
"""
import io, re, ast

E = "app/rule_engine/engine.py"
t = io.open(E, encoding="utf-8", newline="").read()

if "CATEGORY_CAPS" in t:
    print("SKIP: CATEGORY_CAPS already present - nothing to do")
    raise SystemExit(0)

anchor = "BLACK_OVERRIDE_RULES: set[str] = set()"
assert t.count(anchor) == 1, "anchor BLACK_OVERRIDE_RULES not unique"
t = t.replace(anchor, anchor + '''

# 100-point scoring model v2 - per-category deduction caps.
# key -> (max_deduction, rule_id_prefixes). UNKNOWN states never reach the
# deduction phase (violations are NON_COMPLIANT only).
CATEGORY_CAPS: dict[str, tuple[int, tuple[str, ...]]] = {
    "TAX":  (15, ("TAX-", "VAT-")),
    "AGM":  (30, ("AGM-",)),
    "AUD":  (25, ("AUD-",)),
    "RET":  (20, ("AR-",)),
    "DIR":  (25, ("DIR-", "INC-", "DEF-", "TL-", "BOD-", "MEM-")),
    "SHR":  (20, ("SH-", "TR-")),
    "CAP":  (15, ("CAP-", "STR-", "CHG-", "ACC-")),
    "OFF":  (10, ("OFF-",)),
    "REG":  (10, ("REG-",)),
    "BNK":  (20, ("BNK-",)),
    "LBR":  (10, ("LBR-",)),
    "BSEC": (15, ("BSEC-",)),
    "FX":   (10, ("FX-",)),
    "ESC":  (15, ("ESC-",)),
}''')

old_raw = (
    '        raw = self._calculate_raw_score(flags)\n'
    '        raw = max(0, min(100, raw))'
)
assert t.count(old_raw) == 1, "raw-score anchor not unique"
new_raw = '''        # 100-point model v2: cap each category, then subtract from 100
        tax_ded = min(tax_ded, CATEGORY_CAPS["TAX"][0])
        agm_ded = min(agm_ded, CATEGORY_CAPS["AGM"][0])
        aud_ded = min(aud_ded, CATEGORY_CAPS["AUD"][0])
        ret_ded = min(ret_ded, CATEGORY_CAPS["RET"][0])
        dir_ded = min(dir_ded, CATEGORY_CAPS["DIR"][0])
        shr_ded = min(shr_ded, CATEGORY_CAPS["SHR"][0])
        cap_ded = min(cap_ded, CATEGORY_CAPS["CAP"][0])
        off_ded = min(off_ded, CATEGORY_CAPS["OFF"][0])
        reg_ded = min(reg_ded, CATEGORY_CAPS["REG"][0])
        bnk_ded = min(bnk_ded, CATEGORY_CAPS["BNK"][0])
        lbr_ded = min(lbr_ded, CATEGORY_CAPS["LBR"][0])
        bsec_ded = min(bsec_ded, CATEGORY_CAPS["BSEC"][0])
        fx_ded = min(fx_ded, CATEGORY_CAPS["FX"][0])
        esc_ded = min(esc_ded, CATEGORY_CAPS["ESC"][0])

        raw = max(0, min(100, 100 - (tax_ded + agm_ded + aud_ded + ret_ded + dir_ded
                                     + shr_ded + cap_ded + off_ded + reg_ded + bnk_ded
                                     + lbr_ded + bsec_ded + fx_ded + esc_ded)))'''
t = t.replace(old_raw, new_raw)

io.open(E, "w", encoding="utf-8", newline="").write(t)
ast.parse(t)
print("OK CATEGORY_CAPS merged, AST valid")
