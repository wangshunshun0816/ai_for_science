"""Static import rules; rationale and limits: docs/implementation/p1-1-delivery.md."""

import argparse
import ast
import importlib.util
from pathlib import Path

# B01: architecture 6.3; guide 3.1/3.3. Local implementation policy:
# direct children of danus_ai are components; only bootstrap.py composes them.
# B02: architecture 6.3/6.4: contracts cannot depend on implementation or I/O.
# Pure dependencies are explicitly admitted; additions require rule review.
PURE_CONTRACT_IMPORTS = {
    "__future__",
    "abc",
    "collections",
    "dataclasses",
    "datetime",
    "decimal",
    "enum",
    "fractions",
    "hashlib",
    "json",
    "math",
    "re",
    "typing",
    "unicodedata",
    "uuid",
    "pydantic",
    "rfc8785",  # A 5.2; dependency approved by A0 on 2026-11-12
    "typing_extensions",
}


def imports(tree: ast.AST, package: str) -> list[tuple[int, str]]:
    result: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.extend((node.lineno, alias.name) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                base = importlib.util.resolve_name("." * node.level + base, package)
            result.append((node.lineno, base))
            result.extend((node.lineno, base + "." + alias.name) for alias in node.names)
        elif isinstance(node, ast.Call):
            func = node.func
            if (isinstance(func, ast.Name) and func.id == "__import__") or (
                isinstance(func, ast.Attribute) and func.attr == "import_module"
            ):
                # B03: fail closed for these dynamic forms, pending plugin policy.
                result.append((node.lineno, "!dynamic"))
    return result


def check(root: Path) -> list[str]:
    errors: list[str] = []
    for path in sorted(root.rglob("*.py")):
        relative = path.relative_to(root)
        module = "danus_ai." + ".".join(relative.with_suffix("").parts)
        package = module.rsplit(".", 1)[0]
        if path.name == "__init__.py":
            package = module.removesuffix(".__init__")
        component = relative.parts[0].removesuffix(".py")
        try:
            entries = imports(ast.parse(path.read_text(encoding="utf-8")), package)
        except (SyntaxError, ImportError, ValueError) as exc:
            errors.append(f"{path}: B00 invalid Python/import: {exc}")
            continue
        for line, target in entries:
            rule = ""
            if target == "!dynamic":
                rule = "B03 dynamic imports need explicit review"
            elif target.startswith("danus_ai."):
                other = target.split(".")[1]
                if relative.as_posix() != "bootstrap.py" and other not in {
                    component,
                    "contracts",
                }:
                    rule = "B01 cross-component implementation import"
            elif component == "contracts" and target.split(".")[0] not in (
                PURE_CONTRACT_IMPORTS | {"danus_ai"}
            ):
                rule = "B02 contracts dependency is not admitted"
            if rule:
                errors.append(f"{path}:{line}: {rule}: {target}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path("danus_ai"))
    args = parser.parse_args()
    if not args.root.is_dir() or not list(args.root.rglob("*.py")):
        parser.error("root must contain Python source files")
    errors = check(args.root)
    for error in errors:
        print(error)
    if not errors:
        print("Import boundaries: PASS")
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
