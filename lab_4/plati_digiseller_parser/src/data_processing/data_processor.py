import logging
import json
from pathlib import Path

import pandas as pd
import yaml

from src.database.db_manager import DBManager
from src.parsers.plati_market_parser import parse_plati_market
from src.parsers.digiseller_api import process_digiseller_data

LOG_DIR = Path("logs")
DATA_PROCESSED_DIR = Path("data/processed")
for path in (LOG_DIR, DATA_PROCESSED_DIR):
    path.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=str(LOG_DIR / "data_processor.log"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def process_data():
    logging.info("Starting data processing")
    try:
        with open('config/config.yaml', 'r') as config_file:
            config = yaml.safe_load(config_file)

        with DBManager(config['database_path']) as db:
            plati_market_data = parse_plati_market(config)
            for item in plati_market_data:
                db.insert_plati_market_data(item['url'], item['data'])

            digiseller_data = process_digiseller_data(config)
            if digiseller_data:
                db.insert_digiseller_data(digiseller_data)

            plati_changes, digiseller_changes = calculate_daily_changes(
                db,
                config['visualization']['start_date'],
                config['visualization']['end_date'],
            )

        pd.DataFrame(plati_changes).to_csv(
            DATA_PROCESSED_DIR / 'plati_market_changes.csv',
            index=False,
        )
        pd.DataFrame(digiseller_changes).to_csv(
            DATA_PROCESSED_DIR / 'digiseller_changes.csv',
            index=False,
        )
        logging.info("Data processing completed")
    except Exception:
        logging.exception("Error during data processing")


def calculate_daily_changes(db, start_date, end_date):
    plati_rows = db.get_plati_market_data(start_date, end_date)
    plati_rows.sort(key=lambda r: (r[1], r[3]))  # url, date
    plati_changes = []
    prev_by_url = {}
    for _, url, data_json, date in plati_rows:
        curr = json.loads(data_json)
        prev = prev_by_url.get(url)
        if prev:
            plati_changes.append({
                'date': date,
                'url': url,
                'sales_change': curr['sales'] - prev['sales'],
                'reviews_change': (
                    curr['positive_reviews'] + curr['negative_reviews']
                ) - (prev['positive_reviews'] + prev['negative_reviews'])
            })
        prev_by_url[url] = curr

    digi_rows = db.get_digiseller_data(start_date, end_date)
    digi_rows.sort(key=lambda r: r[2])  # date
    digiseller_changes = []
    prev_products = None
    for _, data_json, date in digi_rows:
        curr_products = json.loads(data_json).get('products', [])
        curr_count = sum(p.get('count', 0) for p in curr_products)
        curr_amount = sum(p.get('amount', 0) for p in curr_products)
        if prev_products is not None:
            prev_count = sum(p.get('count', 0) for p in prev_products)
            prev_amount = sum(p.get('amount', 0) for p in prev_products)
            digiseller_changes.append({
                'date': date,
                'sales_change': curr_count - prev_count,
                'amount_change': curr_amount - prev_amount
            })
        prev_products = curr_products

    return plati_changes, digiseller_changes


if __name__ == "__main__":
    process_data()
