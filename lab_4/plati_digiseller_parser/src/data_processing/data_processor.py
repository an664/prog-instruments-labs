import json
from pathlib import Path
from typing import Optional, Tuple, List

import pandas as pd

from src.config import AppConfig
from src.database.db_manager import DBManager
from src.models import DigisellerData, PlatiStats
from src.parsers.digiseller_api import DigisellerParser
from src.parsers.plati_market_parser import PlatiMarketParser
from src.utils.http_client import HttpClient
from src.utils.logging_config import setup_logging

LOG_DIR = Path("logs")
DATA_PROCESSED_DIR = Path("data/processed")
for path in (LOG_DIR, DATA_PROCESSED_DIR):
    path.mkdir(parents=True, exist_ok=True)

logger = setup_logging("data_processor")


def process_data(
    config: AppConfig,
    client: Optional[HttpClient] = None,
) -> Tuple[List[dict], List[dict]]:
    own_client = client is None
    http_client = client or HttpClient()
    plati_parser = PlatiMarketParser(http_client)
    digiseller_parser = DigisellerParser(http_client)

    logger.info("Starting data processing")
    with DBManager(config.database_path) as db:
        for url, stats in plati_parser.fetch(config):
            db.save_plati_stats(url, stats)

        digiseller_data = digiseller_parser.fetch(config)
        if digiseller_data:
            db.save_digiseller_data(digiseller_data)

        plati_changes, digiseller_changes = calculate_daily_changes(
            db,
            config.visualization.start_date,
            config.visualization.end_date,
        )

    pd.DataFrame(plati_changes).to_csv(
        DATA_PROCESSED_DIR / 'plati_market_changes.csv',
        index=False,
    )
    pd.DataFrame(digiseller_changes).to_csv(
        DATA_PROCESSED_DIR / 'digiseller_changes.csv',
        index=False,
    )
    logger.info("Data processing completed")
    if own_client:
        http_client.close()
    return plati_changes, digiseller_changes


def calculate_daily_changes(db: DBManager, start_date: str, end_date: str) -> Tuple[
    list[dict], list[dict]
]:
    plati_rows = db.fetch_plati_history(start_date, end_date)
    plati_changes = []
    prev_by_url = {}
    for url, stats, date in plati_rows:
        prev = prev_by_url.get(url)
        if prev:
            plati_changes.append({
                'date': date,
                'url': url,
                'sales_change': stats.sales - prev.sales,
                'reviews_change': (
                    stats.positive_reviews + stats.negative_reviews
                ) - (prev.positive_reviews + prev.negative_reviews)
            })
        prev_by_url[url] = stats

    digi_rows = db.fetch_digiseller_history(start_date, end_date)
    digiseller_changes = []
    prev_data: Optional[DigisellerData] = None
    for data, date in digi_rows:
        curr_count = data.total_count()
        curr_amount = data.total_amount()
        if prev_data is not None:
            digiseller_changes.append({
                'date': date,
                'sales_change': curr_count - prev_data.total_count(),
                'amount_change': curr_amount - prev_data.total_amount()
            })
        prev_data = data

    return plati_changes, digiseller_changes


if __name__ == "__main__":
    config_path = Path("config/config.yaml")
    app_config = AppConfig.from_file(config_path)
    process_data(app_config)
