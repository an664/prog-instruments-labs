from pathlib import Path

from src.config import AppConfig, VisualizationConfig
from src.data_processing.data_processor import calculate_daily_changes
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


def test_digiseller_parser_fetch_returns_data():
    token_response = FakeResponse(json_data={"token": "abc"})
    ad_response = FakeResponse(
        json_data={"products": [{"name": "x", "count": 2, "amount": 5.5}]}
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
            "2023-01-01",
            "2023-12-31",
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
            "2023-01-01",
            "2023-12-31",
        )

    assert plati_changes == []
    assert len(digiseller_changes) == 1
    assert digiseller_changes[0]["sales_change"] == 2
    assert digiseller_changes[0]["amount_change"] == 3.0
