"""Pytest root configuration."""

import sys
from pathlib import Path

# Add project root, packages/engine, and apps/api to sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "packages" / "engine"))
sys.path.insert(0, str(ROOT / "apps" / "api"))
