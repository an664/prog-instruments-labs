import runpy
import sys

from src.config import AppConfig, VisualizationConfig
from src.data_processing.data_processor import (
    calculate_daily_changes,
    process_data,
)
from src.database.db_manager import DBManager
from src.models import DigisellerData, DigisellerProduct, PlatiStats


def test_calculate_daily_changes_plati(tmp_path):
    db_path = tmp_path / "db.sqlite"
    with DBManager(db_path) as db:
        db.save_plati_stats("url1", PlatiStats(10, 1, 3, 2))
        db.save_plati_stats("url1", PlatiStats(15, 2, 5, 4))

        plati_changes, digiseller_changes = calculate_daily_changes(
            db,
            "2000-01-01",
            "2100-12-31",
        )

    assert len(plati_changes) == 1
    assert plati_changes[0]["sales_change"] == 5
    assert plati_changes[0]["reviews_change"] == (5 + 4) - (3 + 2)
    assert digiseller_changes == []


def test_calculate_daily_changes_digiseller(tmp_path):
    db_path = tmp_path / "db.sqlite"
    with DBManager(db_path) as db:
        db.save_digiseller_data(DigisellerData([
            DigisellerProduct("a", 1, 2.0)
        ]))
        db.save_digiseller_data(DigisellerData([
            DigisellerProduct("a", 3, 5.0)
        ]))

        plati_changes, digiseller_changes = calculate_daily_changes(
            db,
            "2000-01-01",
            "2100-12-31",
        )

    assert plati_changes == []
    assert len(digiseller_changes) == 1
    assert digiseller_changes[0]["sales_change"] == 2
    assert digiseller_changes[0]["amount_change"] == 3.0


def test_process_data_full_flow(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    config = AppConfig(
        plati_market_urls=["https://plati.market/itm/1"],
        digiseller_api_key="k",
        digiseller_seller_id=1,
        digiseller_owner=1,
        database_path=tmp_path / "db.sqlite",
        parsing_interval_minutes=5,
        ad_data_check_interval_hours=24,
        visualization=VisualizationConfig(
            start_date="2023-01-01",
            end_date="2023-12-31",
        ),
    )

    (tmp_path / "data/processed").mkdir(parents=True, exist_ok=True)
    (tmp_path / "logs").mkdir(parents=True, exist_ok=True)

    fake_plati_stats = PlatiStats(5, 1, 2, 1)
    fake_digi = DigisellerData([DigisellerProduct("a", 3, 4.0)])

    monkeypatch.setattr(
        "src.parsers.plati_market.PlatiMarketParser.fetch",
        lambda self, cfg: [("url1", fake_plati_stats)],
    )
    monkeypatch.setattr(
        "src.parsers.digiseller.DigisellerParser.fetch",
        lambda self, cfg: fake_digi,
    )

    plati_changes, digiseller_changes = process_data(config)

    assert isinstance(plati_changes, list)
    assert isinstance(digiseller_changes, list)
    assert (tmp_path / "data/processed/plati_market_changes.csv").exists()
    assert (tmp_path / "data/processed/digiseller_changes.csv").exists()


def test_data_processor_main_guard(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    cfg_file = cfg_dir / "config.yaml"
    cfg_file.write_text(
        """
plati_market_urls: ["u"]
digiseller_api_key: "k"
digiseller_seller_id: 1
digiseller_owner: 1
database_path: "db.sqlite"
parsing_interval_minutes: 5
ad_data_check_interval_hours: 24
visualization:
  start_date: "2023-01-01"
  end_date: "2023-01-02"
"""
    )

    (tmp_path / "data/processed").mkdir(parents=True, exist_ok=True)
    (tmp_path / "logs").mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        "src.parsers.plati_market.PlatiMarketParser.fetch",
        lambda self, cfg: [("u", PlatiStats(1, 0, 0, 0))],
    )
    monkeypatch.setattr(
        "src.parsers.digiseller.DigisellerParser.fetch",
        lambda self, cfg: DigisellerData([DigisellerProduct("a", 1, 2.0)]),
    )

    sys.modules.pop("src.data_processing.data_processor", None)
    runpy.run_module("src.data_processing.data_processor", run_name="__main__")
