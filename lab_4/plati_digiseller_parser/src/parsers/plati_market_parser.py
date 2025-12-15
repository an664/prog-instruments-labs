import requests
from bs4 import BeautifulSoup

import requests
from bs4 import BeautifulSoup
import logging

logging.basicConfig(filename='logs/plati_market_parser.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

def parse_product_page(url):
    try:
        response = requests.get(url + "?lang=ru-RU", timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        sales = soup.select_one('.goods-sell-count').text.split(':')[1].strip()
        returns = soup.select_one('.goods-sell-count').text.split(':')[2].strip()
        
        reviews = soup.select_one('.goods_reviews span[itemprop="reviewCount"]')
        positive_reviews = reviews.contents[0].strip()
        negative_reviews = reviews.select_one('span').text.strip()
        
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
        response = requests.get(url + "?lang=ru-RU")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        stats = soup.select('.merchant-statistic ol li')
        sales = int(stats[0].text.split(':')[1].strip())
        returns = int(stats[1].text.split(':')[1].strip())
        
        reviews = soup.select_one('.goods_reviews span')
        positive_reviews = int(reviews.contents[0].strip())
        negative_reviews = int(reviews.select_one('span').text.strip())
        
        return {
            'sales': sales,
            'returns': returns,
            'positive_reviews': positive_reviews,
            'negative_reviews': negative_reviews
        }
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
