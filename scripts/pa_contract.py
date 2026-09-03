#!/usr/bin/env python3
"""pa_contract.py — deterministically extract the IMPORT CONTRACT from a polyglot test file.

Q2 capability: the driver (not the model) reads the test file with ast and emits a
CONTRACT.md describing every imported symbol and observed call shape, so the root never
has to guess the interface. Usage:
  pa_contract.py <test_file.py> <slug> > CONTRACT.md
"""
import ast
import sys


def safe_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = safe_name(node.value)
        return (base + "." + node.attr) if base else None
    return None


def main():
    test_path, slug = sys.argv[1], sys.argv[2]
    tree = ast.parse(open(test_path, encoding="utf-8").read())

    imports = []
    imported_names = set()
    calls = []            # (callee, arg_count, star_unpack, kwarg_names, kw_values)
    instances = {}        # assigned instance name -> imported class (e.g. n -> PhoneNumber)
    methods = set()       # class method surfaces: "PhoneNumber.number(arg)"
    instantiations = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.ImportFrom) and node.module == slug:
                for a in node.names:
                    imports.append(("import", a.name, a.asname or ""))
                    imported_names.add(a.asname or a.name)
            elif isinstance(node, ast.Import):
                for a in node.names:
                    if a.name == slug:
                        imports.append(("import", a.name, a.asname or ""))
        elif isinstance(node, ast.Assign):
            # n = PhoneNumber(...) -> later calls n.number() ∈ class surface
            if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                v = node.value
                if isinstance(v, ast.Call):
                    fname = safe_name(v.func)
                    if fname in imported_names:
                        instances[node.targets[0].id] = fname
        elif isinstance(node, ast.Call):
            n = safe_name(node.func)
            head = (n or "").split(".")[0]
            if n and (head == slug.split(".")[0] or head in imported_names):
                star = any(isinstance(a, ast.Starred) for a in node.args)
                kwvals = {}
                for k in node.keywords:
                    if isinstance(k.value, ast.Constant):
                        kwvals[k.arg or "*"] = type(k.value.value).__name__  # str/NoneType/int...
                calls.append((n, len(node.args), star, sorted(kwvals), kwvals))
            elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) \
                    and node.func.value.id in instances:
                methods.add(f"{instances[node.func.value.id]}.{node.func.attr}"
                            f"({len(node.args)} args)")
            elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Call):
                base = safe_name(node.func.value.func)
                if base in imported_names:  # PhoneNumber("...").number() chained form
                    methods.add(f"{base}.{node.func.attr}({len(node.args)} args)")
        elif isinstance(node, ast.Attribute):
            # PhoneNumber("...").number — property access on a constructed instance
            # InputCell(5).value (chained) or inp.value (assigned instance)
            if isinstance(node.value, ast.Call):
                base = safe_name(node.value.func)
                if base in imported_names:
                    methods.add(f"{base}.{node.attr} (property)")
            elif isinstance(node.value, ast.Name) and node.value.id in instances:
                methods.add(f"{instances[node.value.id]}.{node.attr} (property)")
        elif isinstance(node, ast.ClassDef):
            if not node.name.endswith("Test"):  # skip the pytest class itself
                instantiations.append(node.name)

    lines = []
    lines.append(f"# CONTRACT — the test file imports from `{slug}`. Implement ONLY this surface:")
    lines.append("")
    if imports:
        lines.append("## Exact imports")
        for kind, name, asname in imports:
            lines.append(f"- `from {slug} import {name}`" + (f" as {asname}" if asname else ""))
    if calls:
        lines.append("## Observed call shapes (*args = called with STAR-UNPACKING — variadic)")
        for n, argc, star, kw, kwvals in calls:
            pos = "*args" if star else ", ".join(["arg"] * argc)
            kwtxt = ""
            if kw:
                kws = []
                for k in kw:
                    kws.append(k + (f":{kwvals[k]}" if k in kwvals else ""))
                kwtxt = "," + ",".join(kws)
            lines.append(f"- `{n}({pos}{kwtxt})`")
    if methods:
        lines.append("## Class method surfaces (called on instances in tests)")
        for m in sorted(methods):
            lines.append(f"- `{m}` — implement with matching behavior")
    if instantiations:
        lines.append("## Classes constructed in tests")
        for c in instantiations:
            lines.append(f"- `{c}(...)` must be constructible and expose the tested methods")
    lines.append("")
    lines.append("Implement ONLY these names. Keep their signatures EXACTLY as called above.")
    lines.append("No CLI, no __main__, no argparse, no sys.argv, no stdin reads.")
    print("\n".join(lines))


if __name__ == "__main__":
    main()