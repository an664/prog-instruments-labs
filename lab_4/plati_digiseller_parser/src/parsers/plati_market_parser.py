import logging
from pathlib import Path

import requests
from bs4 import BeautifulSoup

LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=str(LOG_DIR / 'plati_market_parser.log'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)


def parse_product_page(url):
    try:
        response = requests.get(url + "?lang=ru-RU", timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        sales_node = soup.select_one('.goods-sell-count')
        if not sales_node:
            logging.warning("No sell-count block on %s", url)
            return None
        parts = sales_node.text.split(':')
        if len(parts) < 3:
            logging.warning(
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
            logging.warning("No reviewCount block on %s", url)
            return None
        positive_reviews = reviews.contents[0].strip()
        neg_span = reviews.select_one('span')
        if not neg_span:
            logging.warning("No negative review span on %s", url)
            return None
        negative_reviews = neg_span.text.strip()

        return {
            'sales': int(sales),
            'returns': int(returns),
            'positive_reviews': int(positive_reviews),
            'negative_reviews': int(negative_reviews)
        }
    except requests.RequestException as e:
        logging.error(f"Network error while parsing {url}: {str(e)}")
        return None


def parse_seller_page(url):
    try:
        response = requests.get(url + "?lang=ru-RU", timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        stats = soup.select('.merchant-statistic ol li')
        if len(stats) < 2:
            logging.warning("Unexpected seller stats layout on %s", url)
            return None
        sales = int(stats[0].text.split(':')[1].strip())
        returns = int(stats[1].text.split(':')[1].strip())

        reviews = soup.select_one('.goods_reviews span')
        if not reviews or not reviews.contents:
            logging.warning("No reviews block on seller page %s", url)
            return None
        positive_reviews = int(reviews.contents[0].strip())
        neg_span = reviews.select_one('span')
        if not neg_span:
            logging.warning("No negative review span on seller page %s", url)
            return None
        negative_reviews = int(neg_span.text.strip())

        return {
            'sales': sales,
            'returns': returns,
            'positive_reviews': positive_reviews,
            'negative_reviews': negative_reviews
        }
    except requests.RequestException as e:
        logging.error(
            f"Network error while parsing seller page {url}: {str(e)}"
        )
        return None
    except Exception as e:
        logging.error(f"Error parsing seller page {url}: {str(e)}")
        return None


def parse_plati_market(config):
    results = []
    for url in config['plati_market_urls']:
        if 'seller' in url:
            result = parse_seller_page(url)
        else:
            result = parse_product_page(url)
        if result:
            results.append({'url': url, 'data': result})
            logging.info(f"Successfully parsed {url}")
        else:
            logging.warning(f"Failed to parse {url}")
    return results
