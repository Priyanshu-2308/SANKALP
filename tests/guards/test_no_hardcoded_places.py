"""Hardcoding Guard Test: Verifies zero city/station names in application code.

Mandate from Section 2 & 10 of Specification:
- "No city, station, train number or venue may be hardcoded in application logic."
- "A test that fails if application code contains hardcoded city or station names."
"""

import ast
from pathlib import Path

# Target source directories to guard
GUARD_DIRECTORIES = [
    Path("packages/engine/sankalp_engine"),
    Path("apps/api/app"),
]

# Sensitive place names and station codes that must NEVER appear in application logic
FORBIDDEN_PLACE_TERMS = {
    "mumbai", "delhi", "pune", "bangalore", "bengaluru", "kolkata",
    "chennai", "hyderabad", "ahmedabad", "jaipur", "lucknow", "kanpur",
    "varanasi", "patna", "bhopal", "nagpur", "gorakhpur", "bhubaneswar",
    "chandigarh", "amritsar", "guwahati", "surat", "vadodara", "indore",
    "ndls", "csmt", "hwh", "mas", "sbc", "ddu", "ngl", "bza", "et", "mmct",
}


def test_no_hardcoded_places_in_application_logic() -> None:
    violations = []

    for directory in GUARD_DIRECTORIES:
        if not directory.exists():
            continue

        for py_file in directory.rglob("*.py"):
            with open(py_file, "r", encoding="utf-8") as f:
                content = f.read()

            try:
                tree = ast.parse(content, filename=str(py_file))
            except SyntaxError as e:
                violations.append(f"Syntax error parsing {py_file}: {e}")
                continue

            # Extract docstrings to exclude documentation explanations
            docstrings = set()
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Module)):
                    ds = ast.get_docstring(node)
                    if ds:
                        docstrings.add(ds)

            # Inspect AST string literals
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    val = node.value.strip()
                    if val in docstrings:
                        continue  # Skip docstrings

                    val_lower = val.lower()
                    # Check for whole-word or token matches against forbidden place names
                    for forbidden in FORBIDDEN_PLACE_TERMS:
                        # Skip timezone strings like "Asia/Kolkata"
                        if "asia/kolkata" in val_lower:
                            continue

                        # Word boundary match
                        tokens = val_lower.replace("_", " ").replace("-", " ").replace("/", " ").split()
                        if forbidden in tokens:
                            violations.append(
                                f"{py_file}:{node.lineno} contains hardcoded place term '{forbidden}' in literal: '{val}'"
                            )

    assert not violations, "HARDCODING GUARD VIOLATION:\n" + "\n".join(violations)
