import ast
import sys

tree = ast.parse(open(sys.argv[1], encoding="utf-8").read())
for node in ast.walk(tree):
    if isinstance(node, ast.Dict):
        seen = {}
        for k, v in zip(node.keys, node.values, strict=True):
            if isinstance(k, ast.Constant) and isinstance(k.value, str):
                seen.setdefault(k.value, []).append((k.lineno, ast.unparse(v)))
        for key, occ in seen.items():
            if len(occ) > 1:
                tag = "SAME" if len({o[1] for o in occ}) == 1 else "DIFF"
                print(f"{tag} {key}")
                for ln, val in occ:
                    print(f"    L{ln}: {val}")
