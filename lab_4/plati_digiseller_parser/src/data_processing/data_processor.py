import logging

logging.basicConfig(filename='logs/data_processor.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

from src.database.db_manager import DBManager
from src.parsers.plati_market_parser import parse_plati_market
from src.parsers.digiseller_api import process_digiseller_data
import yaml
import json
import pandas as pd

def process_data():
    logging.info("Starting data processing")
    try:
        with open('config/config.yaml', 'r') as config_file:
            config = yaml.safe_load(config_file)

        db = DBManager(config['database_path'])

        plati_market_data = parse_plati_market(config)
        for item in plati_market_data:
            db.insert_plati_market_data(item['url'], item['data'])

        digiseller_data = process_digiseller_data(config)
        if digiseller_data:
            db.insert_digiseller_data(digiseller_data)

        plati_changes, digiseller_changes = calculate_daily_changes(db, config['visualization']['start_date'], config['visualization']['end_date'])

        pd.DataFrame(plati_changes).to_csv('data/processed/plati_market_changes.csv', index=False)
        pd.DataFrame(digiseller_changes).to_csv('data/processed/digiseller_changes.csv', index=False)
        logging.info("Data processing completed")
        db.close_connection()
    except Exception as e:
        logging.error(f"Error during data processing: {str(e)}")

def calculate_daily_changes(db, start_date, end_date):
    plati_data = db.get_plati_market_data(start_date, end_date)
    digiseller_data = db.get_digiseller_data(start_date, end_date)
    
    # Расчет изменений для Plati Market
    plati_changes = []
    for i in range(1, len(plati_data)):
        prev_data = json.loads(plati_data[i-1][2])
        curr_data = json.loads(plati_data[i][2])
        changes = {
            'date': plati_data[i][3],
            'url': plati_data[i][1],
            'sales_change': curr_data['sales'] - prev_data['sales'],
            'reviews_change': (curr_data['positive_reviews'] + curr_data['negative_reviews']) - 
                              (prev_data['positive_reviews'] + prev_data['negative_reviews'])
        }
        plati_changes.append(changes)
    
    # Расчет изменений для Digiseller
    digiseller_changes = []
    for i in range(1, len(digiseller_data)):
        prev_data = json.loads(digiseller_data[i-1][1])
        curr_data = json.loads(digiseller_data[i][1])
        changes = {
            'date': digiseller_data[i][2],
            'sales_change': sum(p['count'] for p in curr_data['products']) - 
                            sum(p['count'] for p in prev_data['products']),
            'amount_change': sum(p['amount'] for p in curr_data['products']) - 
                             sum(p['amount'] for p in prev_data['products'])
        }
        digiseller_changes.append(changes)
    
    return plati_changes, digiseller_changes

if __name__ == "__main__":
    process_data()
