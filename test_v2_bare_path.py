#!/usr/bin/env python3
"""
Test that the v2 helper accepts BOTH bare path strings AND full
'@router.patch(...' strings as the route_marker.

This is critical because the previous run failed with "route marker
not found" — likely because the actual files use single-line decorator
or single quotes, and our v2 marker assumed multi-line + double quotes.
"""
import re

def add_current_user_to_endpoint(src: str, route_marker: str, description: str):
    # Strip leading '@router.xxx(' and surrounding quotes — work with bare path
    bare_path = route_marker
    if bare_path.startswith("@router"):
        m = re.search(r'"([^"]+)"|\'([^\']+)\'', bare_path)
        if m:
            bare_path = m.group(1) or m.group(2)
        else:
            bare_path = re.sub(r'^@router\.\w+\(\s*', '', bare_path)
            bare_path = bare_path.strip('"\'').strip()

    route_idx = src.find(bare_path)
    if route_idx == -1:
        route_idx = src.find(bare_path.replace("\\{", "{").replace("\\}", "}"))
    if route_idx == -1:
        return src, None

    fn_idx = src.find("async def ", route_idx)
    if fn_idx == -1:
        return src, None

    db_marker = "db: AsyncSession = Depends(get_db_for_user)"
    db_idx = src.find(db_marker, fn_idx)
    if db_idx == -1:
        m = re.compile(r'db:\s*AsyncSession\s*=\s*Depends\([^)]*\)').search(src, fn_idx)
        if m:
            db_idx = m.start()
            db_marker = m.group(0)
        else:
            return src, None

    sig_close_re = re.compile(r'\n\s*\):')
    sig_close_m = sig_close_re.search(src, db_idx)
    if not sig_close_m:
        return src, None
    sig_end = sig_close_m.start()
    sig_block = src[fn_idx:sig_end]
    if "current_user" in sig_block:
        return src, None

    line_start = src.rfind('\n', 0, db_idx) + 1
    indent = src[line_start:db_idx]
    insertion = f"current_user = Depends(get_current_user),\n{indent}"
    new_src = src[:db_idx] + insertion + src[db_idx:]
    return new_src, f"{description}: +current_user"


# Test case A: code uses single quotes for path
SAMPLE_SINGLE_QUOTE = """@router.patch('/agm/{agm_id}/held', response_model=AGMResponse)
async def mark_agm_held(
    agm_id: uuid.UUID,
    body: AGMHeldRequest,
    db: AsyncSession = Depends(get_db_for_user),
):
    pass
"""

# Test case B: code uses multi-line decorator with newline after paren
SAMPLE_MULTILINE = """@router.patch(
    "/agm/{agm_id}/held",
    response_model=AGMResponse,
    dependencies=[Depends(require_roles("ADMIN_STAFF"))],
    summary="Mark AGM as held")
async def mark_agm_held(
    agm_id: uuid.UUID,
    body: AGMHeldRequest,
    db: AsyncSession = Depends(get_db_for_user),
):
    pass
"""

# Test case C: code uses double quotes, single-line decorator (most common)
SAMPLE_DOUBLE_QUOTE = '''@router.patch("/agm/{agm_id}/held", response_model=AGMResponse)
async def mark_agm_held(
    agm_id: uuid.UUID,
    body: AGMHeldRequest,
    db: AsyncSession = Depends(get_db_for_user),
):
    pass
'''

print("=== Test A: code with SINGLE QUOTES — pass bare path ===")
r, label = add_current_user_to_endpoint(SAMPLE_SINGLE_QUOTE, "/agm/{agm_id}/held", "test A")
assert label is not None, "Test A FAILED"
assert "current_user = Depends(get_current_user)" in r, "Test A FAILED: not inserted"
print("[PASS] A: bare path matched single-quoted code")

print("\n=== Test B: code with MULTI-LINE decorator (newline after paren) — pass bare path ===")
r, label = add_current_user_to_endpoint(SAMPLE_MULTILINE, "/agm/{agm_id}/held", "test B")
assert label is not None, "Test B FAILED"
assert "current_user = Depends(get_current_user)" in r, "Test B FAILED: not inserted"
print("[PASS] B: bare path matched multi-line decorator")

print("\n=== Test C: code with DOUBLE QUOTES, single-line — pass bare path ===")
r, label = add_current_user_to_endpoint(SAMPLE_DOUBLE_QUOTE, "/agm/{agm_id}/held", "test C")
assert label is not None, "Test C FAILED"
assert "current_user = Depends(get_current_user)" in r, "Test C FAILED: not inserted"
print("[PASS] C: bare path matched double-quoted single-line code")

print("\n=== Test D: pass full '@router.patch(...' marker — should still work ===")
r, label = add_current_user_to_endpoint(SAMPLE_DOUBLE_QUOTE, '@router.patch("/agm/{agm_id}/held"', "test D")
assert label is not None, "Test D FAILED"
assert "current_user = Depends(get_current_user)" in r, "Test D FAILED: not inserted"
print("[PASS] D: full decorator marker still works (backward compatible)")

print("\n=== ALL TESTS PASSED ===")