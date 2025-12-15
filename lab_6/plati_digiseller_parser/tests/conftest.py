import sys
from pathlib import Path

# Ensure project and src are importable before tests are collected
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.append(str(path))
