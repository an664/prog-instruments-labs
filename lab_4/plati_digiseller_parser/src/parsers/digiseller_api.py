import hashlib
import logging
import time
from typing import Optional

from src.config import AppConfig
from src.models import DigisellerData
from src.parsers.base import Parser
from src.utils.http_client import HttpClient
from src.utils.logging_config import setup_logging


class DigisellerParser(Parser):
    def __init__(self, client: Optional[HttpClient] = None, logger: Optional[logging.Logger] = None):
        self.client = client or HttpClient()
        self.logger = logger or setup_logging("digiseller_api")

    def _sign(self, api_key: str) -> tuple[int, str]:
        timestamp = int(time.time())
        sign = hashlib.sha256((api_key + str(timestamp)).encode()).hexdigest()
        return timestamp, sign

    def get_token(self, seller_id: int, api_key: str) -> Optional[str]:
        timestamp, sign = self._sign(api_key)
        data = {
            "seller_id": seller_id,
            "timestamp": timestamp,
            "sign": sign
        }

        try:
            response = self.client.post(
                "https://api.digiseller.ru/api/apilogin",
                json=data,
            )
            return response.json().get('token')
        except Exception as exc:
            self.logger.error("Failed to get token: %s", exc)
            return None

    def get_ad_data(self, token: str, owner: int) -> Optional[DigisellerData]:
        headers = {
            'Accept': 'application/json'
        }
        params = {
            'token': token,
            'owner': owner,
            'lang': 'ru-RU'
        }
        try:
            response = self.client.get(
                "https://api.digiseller.ru/api/rekl",
                headers=headers,
                params=params,
            )
            return DigisellerData.from_api(response.json())
        except Exception as exc:
            self.logger.error("Failed to get ad data: %s", exc)
            return None

    def fetch(self, config: AppConfig) -> Optional[DigisellerData]:
        self.logger.info("Attempting to get token for seller_id: %s", config.digiseller_seller_id)
        token = self.get_token(config.digiseller_seller_id, config.digiseller_api_key)
        if token:
            self.logger.info("Successfully obtained token, fetching ad data")
            return self.get_ad_data(token, config.digiseller_owner)
        self.logger.error("Failed to obtain token")
        return None
