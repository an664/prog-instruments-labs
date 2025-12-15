from src.models import DigisellerData, DigisellerProduct


def test_digiseller_data_totals():
    data = DigisellerData(products=[
        DigisellerProduct(name="a", count=1, amount=2.0),
        DigisellerProduct(name="b", count=3, amount=4.5),
    ])
    assert data.total_count() == 4
    assert data.total_amount() == 6.5
