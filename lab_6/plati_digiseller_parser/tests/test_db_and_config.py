import pytest

from src.config import AppConfig
from src.database.db_manager import DBManager
from src.models import PlatiStats


def test_app_config_from_file(tmp_path):
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(
        """
plati_market_urls: ["a"]
digiseller_api_key: "k"
digiseller_seller_id: 1
digiseller_owner: 2
database_path: "db.sqlite"
parsing_interval_minutes: 5
ad_data_check_interval_hours: 24
visualization:
  start_date: "2024-01-01"
  end_date: "2024-01-31"
"""
    )
    cfg = AppConfig.from_file(cfg_path)
    assert cfg.plati_market_urls == ["a"]
    assert cfg.visualization.start_date == "2024-01-01"
    assert cfg.database_path.name == "db.sqlite"


def test_db_manager_latest_invalid_table(tmp_path):
    db = DBManager(tmp_path / "db.sqlite")
    with pytest.raises(ValueError):
        db.get_latest_data("bad_table")


def test_db_manager_latest_valid(tmp_path):
    db = DBManager(tmp_path / "db.sqlite")
    db.save_plati_stats("url", PlatiStats(1, 0, 0, 0))
    latest = db.get_latest_data("plati_market_data")
    assert latest is not None
