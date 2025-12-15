import matplotlib.pyplot as plt
import pandas as pd
from src.database.db_manager import DBManager
import json
import yaml
import os
import logging

logging.basicConfig(filename='logs/data_visualisation.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

def plot_sales_data(db_path, start_date, end_date):
    db = DBManager(db_path)
    data = db.get_plati_market_data(start_date, end_date)
    
    df = pd.DataFrame([(row[1], json.loads(row[2])['sales'], row[3]) for row in data],
                      columns=['url', 'sales', 'date'])
    
    plt.figure(figsize=(12, 6))
    for url in df['url'].unique():
        url_data = df[df['url'] == url]
        plt.plot(url_data['date'], url_data['sales'], label=url)
    
    plt.title('Продажи за период')
    plt.xlabel('Дата')
    plt.ylabel('Количество продаж')
    plt.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('data/processed/sales_chart.png')
    plt.close()

def create_data_table(db_path, start_date, end_date):
    db = DBManager(db_path)
    plati_data = db.get_plati_market_data(start_date, end_date)
    digiseller_data = db.get_digiseller_data(start_date, end_date)
    
    df_plati = pd.DataFrame([(row[1], json.loads(row[2]), row[3]) for row in plati_data],
                            columns=['url', 'data', 'date'])
    df_digiseller = pd.DataFrame([(json.loads(row[1]), row[2]) for row in digiseller_data],
                                 columns=['data', 'date'])
    
    # Здесь можно добавить дополнительную обработку и объединение данных
    
    return df_plati, df_digiseller

def plot_comparison(db_path, start_date, end_date):
    df_plati, df_digiseller = create_data_table(db_path, start_date, end_date)
    
    plt.figure(figsize=(12, 6))
    plt.plot(df_plati['date'], df_plati['data'].apply(lambda x: x['sales']), label='Plati Market')
    plt.plot(df_digiseller['date'], df_digiseller['data'].apply(lambda x: x['products'][0]['count']), label='Digiseller')
    
    plt.title('Сравнение продаж Plati Market и Digiseller')
    plt.xlabel('Дата')
    plt.ylabel('Количество продаж')
    plt.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('data/processed/comparison_chart.png')
    plt.close()

def plot_changes(config):
    try:
        start_date = pd.to_datetime(config['visualization']['start_date'])
        end_date = pd.to_datetime(config['visualization']['end_date'])
        
        plati_changes = pd.read_csv('data/processed/plati_market_changes.csv', parse_dates=['date'])
        digiseller_changes = pd.read_csv('data/processed/digiseller_changes.csv', parse_dates=['date'])

        plati_changes = plati_changes[(plati_changes['date'] >= start_date) & (plati_changes['date'] <= end_date)]
        digiseller_changes = digiseller_changes[(digiseller_changes['date'] >= start_date) & (digiseller_changes['date'] <= end_date)]

        if plati_changes.empty and digiseller_changes.empty:
            logging.warning("No data available for plotting changes in the specified date range")
            return

        plt.figure(figsize=(12, 6))
        if not plati_changes.empty:
            plt.plot(plati_changes['date'], plati_changes['sales_change'], label='Plati Market')
        if not digiseller_changes.empty:
            plt.plot(digiseller_changes['date'], digiseller_changes['sales_change'], label='Digiseller')

        plt.title('Изменения в продажах')
        plt.xlabel('Дата')
        plt.ylabel('Изменение количества продаж')
        plt.legend()
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.gca().xaxis.set_major_formatter(plt.DateFormatter('%Y-%m-%d'))
        plt.gcf().autofmt_xdate()
        plt.tight_layout()
        plt.savefig('data/processed/sales_changes_chart.png')
        plt.close()
        logging.info("Changes plot created successfully")

        # Сохранение отфильтрованных данных
        plati_changes.to_csv('data/processed/filtered_plati_market_changes.csv', index=False)
        digiseller_changes.to_csv('data/processed/filtered_digiseller_changes.csv', index=False)
        
    except FileNotFoundError as e:
        logging.error(f"File not found: {str(e)}")
    except Exception as e:
        logging.error(f"Error in plot_changes: {str(e)}")

if __name__ == "__main__":
    with open('config/config.yaml', 'r') as config_file:
        config = yaml.safe_load(config_file)
    
    db_path = config['database_path']
    start_date = config['visualization']['start_date']
    end_date = config['visualization']['end_date']
    
    plot_sales_data(db_path, start_date, end_date)
    df_plati, df_digiseller = create_data_table(db_path, start_date, end_date)
    df_plati.to_csv('data/processed/plati_market_data.csv', index=False)
    df_digiseller.to_csv('data/processed/digiseller_data.csv', index=False)
    plot_comparison(db_path, start_date, end_date)
    plot_changes(config)
