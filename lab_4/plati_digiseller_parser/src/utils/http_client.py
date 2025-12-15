from typing import Any

import requests


class HttpClient:
    def __init__(self, timeout: int = 10):
        self.session = requests.Session()
        self.timeout = timeout

    def get(self, url: str, **kwargs: Any) -> requests.Response:
        kwargs.setdefault("timeout", self.timeout)
        response = self.session.get(url, **kwargs)
        response.raise_for_status()
        return response

    def post(self, url: str, **kwargs: Any) -> requests.Response:
        kwargs.setdefault("timeout", self.timeout)
        response = self.session.post(url, **kwargs)
        response.raise_for_status()
        return response

    def close(self) -> None:
        self.session.close()
