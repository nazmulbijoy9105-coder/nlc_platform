import ast, re, sys, pathlib
read = lambda p: pathlib.Path(p).read_text(encoding="utf-8")
et = ast.parse(read("app/rule_engine/engine.py"))
_src = read("app/services/company_service.py")
_t = ast.parse(_src)
svc = "\n".join(ast.get_source_segment(_src, f) for f in ast.walk(_t)
    if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)) and f.name in ("build_company_profile", "_build_company_profile"))
assert svc, "profile builder not found"
model = read("app/models/company.py")

fields, cf_required = {}, set()
for n in ast.walk(et):
    if isinstance(n, ast.ClassDef) and n.name == "CompanyProfile":
        for b in n.body:
            if isinstance(b, ast.AnnAssign) and isinstance(b.target, ast.Name):
                fields[b.target.id] = ast.unparse(b.value) if b.value else "<required>"
    if isinstance(n, ast.ClassDef) and n.name == "ComplianceFlag":
        cf_required = {b.target.id for b in n.body
                       if isinstance(b, ast.AnnAssign) and isinstance(b.target, ast.Name) and b.value is None}

parent = {c: p for p in ast.walk(et) for c in ast.iter_child_nodes(p)}
attrs = lambda n: {a.attr for a in ast.walk(n) if isinstance(a, ast.Attribute) and a.attr in fields}
def func_of(n):
    while n in parent:
        n = parent[n]
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)): return n
def resolve(test, fn):
    s = attrs(test)
    for nm in {x.id for x in ast.walk(test) if isinstance(x, ast.Name)}:
        for a in ast.walk(fn):
            if isinstance(a, ast.Assign) and any(isinstance(t, ast.Name) and t.id == nm for t in a.targets):
                s |= attrs(a.value)
    return s
is_flag = lambda c: isinstance(c, ast.Call) and getattr(c.func, "id", getattr(c.func, "attr", "")) == "ComplianceFlag"

rule_fields, problems = {}, 0
print("=== [4] ComplianceFlag call integrity ===")
print("required fields per dataclass:", sorted(cf_required))
for c in ast.walk(et):
    if not is_flag(c): continue
    kw = {k.arg: k.value for k in c.keywords}
    rid = kw["rule_id"].value if isinstance(kw.get("rule_id"), ast.Constant) else f"?line{c.lineno}"
    if None in kw: print(f"  {rid}: uses **kwargs, cannot verify"); problems += 1
    if c.args: print(f"  {rid}: positional args, cannot verify (line {c.lineno})"); problems += 1
    miss = cf_required - set(kw)
    if miss and not c.args: print(f"  {rid}: MISSING {sorted(miss)}"); problems += 1
    sb = kw.get("statutory_basis")
    if isinstance(sb, ast.Constant) and not re.search(r"Section|Act|Rule|Order|Regulation|Article", str(sb.value)):
        print(f"  {rid}: weak statutory_basis -> {sb.value!r}"); problems += 1
    fn = func_of(c); s = attrs(c); n = c
    while n in parent and parent[n] is not fn:
        p = parent[n]
        if isinstance(p, ast.If) and (n in p.body or n in p.orelse): s |= resolve(p.test, fn)
        n = p
    rule_fields.setdefault(rid, set()).update(s)

setk = lambda f: bool(re.search(rf'["\']{f}["\']|\b{f}\s*=', svc))
print("\n=== per-rule wiring ===")
dead = []
for rid in sorted(rule_fields):
    fs = rule_fields[rid]
    unset = sorted(f for f in fs if not setk(f))
    if not fs: print(f"{rid}: reads NO profile field (constant rule?)"); problems += 1
    elif len(unset) == len(fs): dead.append(rid); print(f"{rid}: DEAD - all inputs unset: {unset}")
    elif unset: print(f"{rid}: partial - unset {unset}")
print(f"\nDEAD rules (can never react to real data): {len(dead)} -> {', '.join(dead) or 'none'}")
print("unset fields with a DB column (fixable in service):",
      sorted(f for f in {x for v in rule_fields.values() for x in v} if not setk(f) and re.search(rf'^\s+{f}\s*:', model, re.M)))
sys.exit(1 if (dead or problems) else 0)
