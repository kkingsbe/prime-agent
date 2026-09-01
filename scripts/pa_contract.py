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
    calls = []          # (callee, arg_count, kwarg_names)
    instantiations = []  # class names constructed
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
        elif isinstance(node, ast.Call):
            n = safe_name(node.func)
            head = (n or "").split(".")[0]
            if n and (head == slug.split(".")[0] or head in imported_names):
                calls.append((n, len(node.args), sorted(k.arg for k in node.keywords)))
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
        lines.append("## Observed call shapes (name | arg count | keywords)")
        seen = set()
        for n, argc, kw in calls:
            key = (n, argc, tuple(kw))
            if key in seen:
                continue
            seen.add(key)
            lines.append(f"- `{n}({', '.join(['arg'] * argc + kw)})`" if kw else f"- `{n}({', '.join(['arg'] * argc)})`")
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