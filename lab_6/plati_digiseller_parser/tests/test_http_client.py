import pytest

from src.utils.http_client import HttpClient
from tests.conftest import FakeResponse


def test_http_client_get_calls_raise_for_status(monkeypatch):
    class FakeSession:
        def __init__(self):
            self.response = FakeResponse("ok")

        def get(self, url, **kwargs):
            return self.response

    fake_session = FakeSession()
    monkeypatch.setattr("requests.Session", lambda: fake_session)

    client = HttpClient(timeout=1)
    resp = client.get("http://example.com")
    assert resp.raise_called is True


def test_http_client_get_raises(monkeypatch):
    class FakeSession:
        def get(self, url, **kwargs):
            return FakeResponse(status_code=500)

    monkeypatch.setattr("requests.Session", lambda: FakeSession())
    client = HttpClient(timeout=1)
    with pytest.raises(Exception):
        client.get("http://example.com")


def test_http_client_post_and_close(monkeypatch):
    class FakeSession:
        def __init__(self):
            self.closed = False

        def post(self, url, **kwargs):
            assert kwargs["timeout"] == 5
            return FakeResponse()

        def close(self):
            self.closed = True

    fake_session = FakeSession()
    monkeypatch.setattr("requests.Session", lambda: fake_session)

    client = HttpClient(timeout=5)
    resp = client.post("http://example.com")
    assert resp.raise_called is True
    client.close()
    assert fake_session.closed is True
