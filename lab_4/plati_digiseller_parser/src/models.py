from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class PlatiStats:
    sales: int
    returns: int
    positive_reviews: int
    negative_reviews: int

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "PlatiStats":
        return cls(
            sales=int(raw["sales"]),
            returns=int(raw["returns"]),
            positive_reviews=int(raw["positive_reviews"]),
            negative_reviews=int(raw["negative_reviews"]),
        )

    def to_dict(self) -> Dict[str, int]:
        return {
            "sales": self.sales,
            "returns": self.returns,
            "positive_reviews": self.positive_reviews,
            "negative_reviews": self.negative_reviews,
        }


@dataclass
class DigisellerProduct:
    name: str
    count: int
    amount: float

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "DigisellerProduct":
        return cls(
            name=raw.get("name", ""),
            count=int(raw.get("count", 0)),
            amount=float(raw.get("amount", 0.0)),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "count": self.count,
            "amount": self.amount,
        }


@dataclass
class DigisellerData:
    products: List[DigisellerProduct]

    @classmethod
    def from_api(cls, raw: Dict[str, Any]) -> "DigisellerData":
        products = [
            DigisellerProduct.from_dict(item) for item in raw.get("products", [])
        ]
        return cls(products=products)

    def total_count(self) -> int:
        return sum(p.count for p in self.products)

    def total_amount(self) -> float:
        return sum(p.amount for p in self.products)

    def to_dict(self) -> Dict[str, Any]:
        return {"products": [p.to_dict() for p in self.products]}
