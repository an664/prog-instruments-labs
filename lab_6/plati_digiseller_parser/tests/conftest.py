import sys
from pathlib import Path

import pytest


@pytest.fixture(scope="session", autouse=True)
def add_project_root():
    root = Path(__file__).resolve().parents[1]
    sys.path.append(str(root))
    yield
    sys.path.remove(str(root))
