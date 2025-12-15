import logging
from typing import List, Optional, Tuple

from bs4 import BeautifulSoup

from src.config import AppConfig
from src.models import PlatiStats
from src.parsers.base import Parser
from src.utils.http_client import HttpClient
from src.utils.logging_config import setup_logging


class PlatiMarketParser(Parser):
    def __init__(
        self,
        client: Optional[HttpClient] = None,
        logger: Optional[logging.Logger] = None
    ):
        self.client = client or HttpClient()
        self.logger = logger or setup_logging("plati_market_parser")

    def parse_product_page(self, url: str) -> Optional[PlatiStats]:
        try:
            response = self.client.get(url + "?lang=ru-RU")
            soup = BeautifulSoup(response.text, 'html.parser')

            sales_node = soup.select_one('.goods-sell-count')
            if not sales_node:
                self.logger.warning("No sell-count block on %s", url)
                return None
            parts = sales_node.text.split(':')
            if len(parts) < 3:
                self.logger.warning(
                    "Unexpected sell-count format on %s: %s",
                    url,
                    sales_node.text,
                )
                return None
            sales = parts[1].strip()
            returns = parts[2].strip()

            reviews = soup.select_one(
                '.goods_reviews span[itemprop="reviewCount"]'
            )
            if not reviews or not reviews.contents:
                self.logger.warning("No reviewCount block on %s", url)
                return None
            positive_reviews = reviews.contents[0].strip()
            neg_span = reviews.select_one('span')
            if not neg_span:
                self.logger.warning("No negative review span on %s", url)
                return None
            negative_reviews = neg_span.text.strip()

            return PlatiStats(
                sales=int(sales),
                returns=int(returns),
                positive_reviews=int(positive_reviews),
                negative_reviews=int(negative_reviews),
            )
        except Exception as exc:
            self.logger.error("Error parsing product page %s: %s", url, exc)
            return None

    def parse_seller_page(self, url: str) -> Optional[PlatiStats]:
        try:
            response = self.client.get(url + "?lang=ru-RU")
            soup = BeautifulSoup(response.text, 'html.parser')

            stats = soup.select('.merchant-statistic ol li')
            if len(stats) < 2:
                self.logger.warning(
                    "Unexpected seller stats layout on %s",
                    url,
                )
                return None
            sales = int(stats[0].text.split(':')[1].strip())
            returns = int(stats[1].text.split(':')[1].strip())

            reviews = soup.select_one('.goods_reviews span')
            if not reviews or not reviews.contents:
                self.logger.warning(
                    "No reviews block on seller page %s",
                    url,
                )
                return None
            positive_reviews = int(reviews.contents[0].strip())
            neg_span = reviews.select_one('span')
            if not neg_span:
                self.logger.warning(
                    "No negative review span on seller page %s",
                    url,
                )
                return None
            negative_reviews = int(neg_span.text.strip())

            return PlatiStats(
                sales=sales,
                returns=returns,
                positive_reviews=positive_reviews,
                negative_reviews=negative_reviews,
            )
        except Exception as exc:
            self.logger.error("Error parsing seller page %s: %s", url, exc)
            return None

    def fetch(self, config: AppConfig) -> List[Tuple[str, PlatiStats]]:
        results: List[Tuple[str, PlatiStats]] = []
        for url in config.plati_market_urls:
            if 'seller' in url:
                stats = self.parse_seller_page(url)
            else:
                stats = self.parse_product_page(url)
            if stats:
                results.append((url, stats))
                self.logger.info("Successfully parsed %s", url)
            else:
                self.logger.warning("Failed to parse %s", url)
        return results
