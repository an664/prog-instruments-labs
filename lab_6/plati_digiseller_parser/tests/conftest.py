import sys
from pathlib import Path

# Ensure project and src are importable before tests are collected
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.append(str(path))


class FakeResponse:
    def __init__(self, text="", json_data=None, status_code=200):
        self.text = text
        self._json = json_data or {}
        self.status_code = status_code
        self.raise_called = False

    def raise_for_status(self):
        self.raise_called = True
        if self.status_code >= 400:
            raise Exception("error")

    def json(self):
        return self._json
