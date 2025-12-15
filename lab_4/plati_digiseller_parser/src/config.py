from dataclasses import dataclass
from pathlib import Path
from typing import List, Any, Dict

import yaml


@dataclass
class VisualizationConfig:
    start_date: str
    end_date: str


@dataclass
class AppConfig:
    plati_market_urls: List[str]
    digiseller_api_key: str
    digiseller_seller_id: int
    digiseller_owner: int
    database_path: Path
    parsing_interval_minutes: int
    ad_data_check_interval_hours: int
    visualization: VisualizationConfig

    @classmethod
    def from_file(cls, path: Path) -> "AppConfig":
        with path.open("r", encoding="utf-8") as f:
            raw: Dict[str, Any] = yaml.safe_load(f)

        vis = VisualizationConfig(**raw["visualization"])
        return cls(
            plati_market_urls=raw["plati_market_urls"],
            digiseller_api_key=raw["digiseller_api_key"],
            digiseller_seller_id=raw["digiseller_seller_id"],
            digiseller_owner=raw["digiseller_owner"],
            database_path=Path(raw["database_path"]),
            parsing_interval_minutes=raw["parsing_interval_minutes"],
            ad_data_check_interval_hours=raw["ad_data_check_interval_hours"],
            visualization=vis,
        )
