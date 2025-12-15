from abc import ABC, abstractmethod
from typing import Any

from src.config import AppConfig


class Parser(ABC):
    @abstractmethod
    def fetch(self, config: AppConfig) -> Any:
        """Fetch data using provided configuration."""
        raise NotImplementedError
