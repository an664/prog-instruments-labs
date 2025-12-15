from pathlib import Path
import logging
import runpy

import pytest

from src.config import AppConfig, VisualizationConfig
from src.data_processing.data_processor import (
    calculate_daily_changes,
    process_data,
)
from src.database.db_manager import DBManager
from src.models import DigisellerData, DigisellerProduct, PlatiStats
from src.parsers.digiseller import DigisellerParser
from src.parsers.plati_market import PlatiMarketParser
from src.utils.http_client import HttpClient


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


def test_plati_product_page_parses_values():
    html = """
    <div class="goods-sell-count">Продажи: 10 : 2</div>
    <div class="goods_reviews">
      <span itemprop="reviewCount">7<span>3</span></span>
    </div>
    """
    fake_client = type(
        "C", (), {"get": lambda self, url: FakeResponse(html)}
    )()
    parser = PlatiMarketParser(client=fake_client)

    stats = parser.parse_product_page("http://example.com/item")

    assert stats == PlatiStats(
        sales=10,
        returns=2,
        positive_reviews=7,
        negative_reviews=3,
    )


def test_plati_product_page_missing_blocks():
    parser = PlatiMarketParser(
        client=type(
            "C", (),
            {"get": lambda self, url: FakeResponse("<html></html>")}
        )()
    )
    assert parser.parse_product_page("http://example.com") is None

    missing_reviews = """
    <div class="goods-sell-count">a:b:c</div>
    """
    parser = PlatiMarketParser(
        client=type(
            "C", (),
            {"get": lambda self, url: FakeResponse(missing_reviews)}
        )()
    )
    assert parser.parse_product_page("http://example.com") is None

    def raising_get(url):
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        raising_get("x")

    parser = PlatiMarketParser(client=type("C", (), {"get": raising_get})())
    assert parser.parse_product_page("http://example.com") is None

    bad_html = '<div class="goods-sell-count">only:one</div>'
    parser = PlatiMarketParser(
        client=type(
            "C", (),
            {"get": lambda self, url: FakeResponse(bad_html)}
        )()
    )
    assert parser.parse_product_page("http://example.com") is None

    no_negative = """
    <div class="goods-sell-count">a:b:c</div>
    <div class="goods_reviews"><span itemprop="reviewCount">1</span></div>
    """
    parser = PlatiMarketParser(
        client=type(
            "C", (),
            {"get": lambda self, url: FakeResponse(no_negative)}
        )()
    )
    assert parser.parse_product_page("http://example.com") is None


def test_plati_seller_page_parses_values():
    html = """
    <div class="merchant-statistic">
      <ol>
        <li>Продажи: 5</li>
        <li>Возвраты: 1</li>
      </ol>
    </div>
    <div class="goods_reviews">
      <span>4<span>2</span></span>
    </div>
    """
    fake_client = type(
        "C", (), {"get": lambda self, url: FakeResponse(html)}
    )()
    parser = PlatiMarketParser(client=fake_client)

    stats = parser.parse_seller_page("http://example.com/seller")

    assert stats == PlatiStats(
        sales=5,
        returns=1,
        positive_reviews=4,
        negative_reviews=2,
    )


def test_plati_seller_page_missing_blocks():
    bad_html = (
        "<div class='merchant-statistic'><ol><li>Продажи: 1</li></ol></div>"
    )
    parser = PlatiMarketParser(
        client=type(
            "C", (),
            {"get": lambda self, url: FakeResponse(bad_html)}
        )()
    )
    assert parser.parse_seller_page("http://example.com/seller") is None

    no_negative = (
        "<div class='merchant-statistic'><ol><li>Продажи: 1</li>"
        "<li>Возвраты: 0</li></ol></div>"
        "<div class='goods_reviews'><span>2</span></div>"
    )
    parser = PlatiMarketParser(
        client=type(
            "C", (),
            {"get": lambda self, url: FakeResponse(no_negative)}
        )()
    )
    assert parser.parse_seller_page("http://example.com/seller") is None

    def raising_get(url):
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        raising_get("x")

    parser = PlatiMarketParser(client=type("C", (), {"get": raising_get})())
    assert parser.parse_seller_page("http://example.com/seller") is None

    missing_reviews_html = """
    <div class="merchant-statistic">
      <ol><li>Продажи: 1</li><li>Возвраты: 0</li></ol>
    </div>
    """
    parser = PlatiMarketParser(
        client=type(
            "C", (),
            {"get": lambda self, url: FakeResponse(missing_reviews_html)}
        )()
    )
    assert parser.parse_seller_page("http://example.com/seller") is None


def test_plati_fetch_routes_and_logs():
    config = AppConfig(
        plati_market_urls=[
            "https://plati.market/itm/1",
            "https://plati.market/seller/123",
        ],
        digiseller_api_key="k",
        digiseller_seller_id=1,
        digiseller_owner=1,
        database_path=Path("db.sqlite"),
        parsing_interval_minutes=5,
        ad_data_check_interval_hours=24,
        visualization=VisualizationConfig(
            start_date="2023-01-01",
            end_date="2023-01-02",
        ),
    )

    parser = PlatiMarketParser(
        client=None,
        logger=logging.getLogger("test_plati_fetch"),
    )
    parser.parse_product_page = lambda url: PlatiStats(1, 0, 0, 0)
    parser.parse_seller_page = lambda url: None

    results = parser.fetch(config)
    assert len(results) == 1


def test_digiseller_parser_fetch_returns_data():
    token_response = FakeResponse(json_data={"token": "abc"})
    ad_response = FakeResponse(
        json_data={
            "products": [{"name": "x", "count": 2, "amount": 5.5}]
        }
    )

    class FakeClient:
        def post(self, *args, **kwargs):
            return token_response

        def get(self, *args, **kwargs):
            return ad_response

    config = AppConfig(
        plati_market_urls=[],
        digiseller_api_key="key",
        digiseller_seller_id=1,
        digiseller_owner=1,
        database_path=Path("tmp.sqlite"),
        parsing_interval_minutes=5,
        ad_data_check_interval_hours=24,
        visualization=VisualizationConfig(
            start_date="2023-01-01",
            end_date="2023-01-02",
        ),
    )

    parser = DigisellerParser(client=FakeClient())
    data = parser.fetch(config)

    assert isinstance(data, DigisellerData)
    assert data.total_count() == 2
    assert data.total_amount() == 5.5


def test_digiseller_parser_fetch_token_fail():
    class FakeClient:
        def post(self, *args, **kwargs):
            raise RuntimeError("fail")

    config = AppConfig(
        plati_market_urls=[],
        digiseller_api_key="key",
        digiseller_seller_id=1,
        digiseller_owner=1,
        database_path=Path("tmp.sqlite"),
        parsing_interval_minutes=5,
        ad_data_check_interval_hours=24,
        visualization=VisualizationConfig(
            start_date="2023-01-01",
            end_date="2023-01-02",
        ),
    )

    parser = DigisellerParser(client=FakeClient())
    assert parser.fetch(config) is None


def test_digiseller_parser_get_ad_data_error():
    class FakeClient:
        def post(self, *args, **kwargs):
            return FakeResponse(json_data={"token": "abc"})

        def get(self, *args, **kwargs):
            raise RuntimeError("fail")

    config = AppConfig(
        plati_market_urls=[],
        digiseller_api_key="key",
        digiseller_seller_id=1,
        digiseller_owner=1,
        database_path=Path("tmp.sqlite"),
        parsing_interval_minutes=5,
        ad_data_check_interval_hours=24,
        visualization=VisualizationConfig(
            start_date="2023-01-01",
            end_date="2023-01-02",
        ),
    )
    parser = DigisellerParser(client=FakeClient())
    assert parser.fetch(config) is None


def test_digiseller_data_totals():
    data = DigisellerData(products=[
        DigisellerProduct(name="a", count=1, amount=2.0),
        DigisellerProduct(name="b", count=3, amount=4.5),
    ])
    assert data.total_count() == 4
    assert data.total_amount() == 6.5


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
    # keep outputs in temp cwd
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

    # ensure data/processed exists for CSV outputs
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


def test_base_parser_not_implemented():
    from src.parsers.base import Parser

    with pytest.raises(NotImplementedError):
        Parser.fetch(None, None)


def test_db_manager_latest_invalid_table(tmp_path):
    db = DBManager(tmp_path / "db.sqlite")
    with pytest.raises(ValueError):
        db.get_latest_data("bad_table")


def test_db_manager_latest_valid(tmp_path):
    db = DBManager(tmp_path / "db.sqlite")
    db.save_plati_stats("url", PlatiStats(1, 0, 0, 0))
    latest = db.get_latest_data("plati_market_data")
    assert latest is not None


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

    import sys
    sys.modules.pop("src.data_processing.data_processor", None)
    runpy.run_module("src.data_processing.data_processor", run_name="__main__")
