from pathlib import Path

from src.config import AppConfig, VisualizationConfig
from src.models import DigisellerData, DigisellerProduct
from src.parsers.digiseller import DigisellerParser
from tests.conftest import FakeResponse


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
