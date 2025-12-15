import logging

from pathlib import Path
from src.config import AppConfig, VisualizationConfig
from src.models import PlatiStats
from src.parsers.plati_market import PlatiMarketParser
from tests.conftest import FakeResponse


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

    def raising_get(url):  # pragma: no cover
        raise RuntimeError("boom")

    parser = PlatiMarketParser(client=type("C", (), {"get": raising_get})())
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
    no_stats = "<html></html>"
    parser = PlatiMarketParser(
        client=type(
            "C", (),
            {"get": lambda self, url: FakeResponse(no_stats)}
        )()
    )
    assert parser.parse_seller_page("http://example.com/seller") is None

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

    def raising_get(url):  # pragma: no cover
        raise RuntimeError("boom")

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
