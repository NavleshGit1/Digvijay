#!/usr/bin/env python3
"""
AST Clock Linter for AirOps Nexus.
Enforces ADR 0006 and Phase 1 requirement P1-10:
Bans direct calls to datetime.now(), datetime.utcnow(), and time.time()
in business logic (outside of app/core/clock.py).
"""

import ast
import os
import sys
from pathlib import Path


class ClockLinterVisitor(ast.NodeVisitor):
    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.violations: list[tuple[int, str]] = []

    def visit_Call(self, node: ast.Call) -> None:
        # Check for datetime.now() or datetime.utcnow()
        if isinstance(node.func, ast.Attribute):
            attr_name = node.func.attr
            if attr_name in ("now", "utcnow"):
                # Check if caller is datetime or datetime.datetime
                caller = node.func.value
                if isinstance(caller, ast.Name) and caller.id == "datetime":
                    self.violations.append(
                        (
                            node.lineno,
                            f"Direct call to datetime.{attr_name}() is prohibited. Use injected Clock.now() instead.",
                        )
                    )
                elif isinstance(caller, ast.Attribute) and caller.attr == "datetime":
                    self.violations.append(
                        (
                            node.lineno,
                            f"Direct call to datetime.datetime.{attr_name}() is prohibited. Use injected Clock.now() instead.",
                        )
                    )
            elif attr_name == "time":
                # Check if caller is time.time()
                caller = node.func.value
                if isinstance(caller, ast.Name) and caller.id == "time":
                    self.violations.append(
                        (
                            node.lineno,
                            "Direct call to time.time() is prohibited. Use injected Clock.now() instead.",
                        )
                    )
        self.generic_visit(node)


def lint_file(filepath: Path) -> list[str]:
    # Exempt the clock definition itself
    if "app/core/clock.py" in filepath.as_posix() or "app\\core\\clock.py" in filepath.as_posix():
        return []

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(filepath))
    except SyntaxError as e:
        return [f"{filepath}:{e.lineno}: Syntax error while parsing: {e}"]

    visitor = ClockLinterVisitor(str(filepath))
    visitor.visit(tree)

    return [f"{filepath}:{lineno}: {msg}" for lineno, msg in visitor.violations]


def main() -> int:
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "backend/app"
    path = Path(target_dir)

    if not path.exists():
        print(f"Target directory {target_dir} does not exist.")
        return 0

    violations: list[str] = []
    for root, _, files in os.walk(path):
        for file in files:
            if file.endswith(".py"):
                file_violations = lint_file(Path(root) / file)
                violations.extend(file_violations)

    if violations:
        print(f"FAILED: Found {len(violations)} forbidden direct clock calls:")
        for v in violations:
            print(f"  {v}")
        return 1

    print("SUCCESS: AST Clock Linter passed. Zero direct clock calls found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
