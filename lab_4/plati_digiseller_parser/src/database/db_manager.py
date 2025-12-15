import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

from src.models import DigisellerData, PlatiStats


class DBManager:
    def __init__(self, db_path):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.create_tables()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_connection()

    def create_tables(self):
        with self.conn:
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS plati_market_data (
                    id INTEGER PRIMARY KEY,
                    url TEXT,
                    data TEXT,
                    date DATE
                )
            ''')
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS digiseller_data (
                    id INTEGER PRIMARY KEY,
                    data TEXT,
                    date DATE
                )
            ''')
            self.conn.execute(
                'CREATE INDEX IF NOT EXISTS idx_plati_market_date '
                'ON plati_market_data(date)'
            )
            self.conn.execute(
                'CREATE INDEX IF NOT EXISTS idx_digiseller_date '
                'ON digiseller_data(date)'
            )

    def insert_plati_market_data(self, url: str, data: PlatiStats):
        with self.conn:
            self.conn.execute('''
                INSERT INTO plati_market_data (url, data, date)
                VALUES (?, ?, ?)
            ''', (url, json.dumps(data.to_dict()), datetime.now().date()))

    def insert_digiseller_data(self, data: DigisellerData):
        with self.conn:
            self.conn.execute('''
                INSERT INTO digiseller_data (data, date)
                VALUES (?, ?)
            ''', (json.dumps(data.to_dict()), datetime.now().date()))

    def save_plati_stats(self, url: str, stats: PlatiStats) -> None:
        self.insert_plati_market_data(url, stats)

    def save_digiseller_data(self, data: DigisellerData) -> None:
        self.insert_digiseller_data(data)

    def get_plati_market_data(self, start_date, end_date):
        with self.conn:
            cursor = self.conn.execute('''
                SELECT * FROM plati_market_data
                WHERE date BETWEEN ? AND ?
                ORDER BY url, date, id
            ''', (start_date, end_date))
            return cursor.fetchall()

    def get_digiseller_data(self, start_date, end_date):
        with self.conn:
            cursor = self.conn.execute('''
                SELECT * FROM digiseller_data
                WHERE date BETWEEN ? AND ?
                ORDER BY date, id
            ''', (start_date, end_date))
            return cursor.fetchall()

    def fetch_plati_history(
        self, start_date, end_date
    ) -> List[Tuple[str, PlatiStats, str]]:
        rows = self.get_plati_market_data(start_date, end_date)
        result = []
        for _, url, data_json, date in rows:
            stats = PlatiStats.from_dict(json.loads(data_json))
            result.append((url, stats, date))
        return result

    def fetch_digiseller_history(
        self, start_date, end_date
    ) -> List[Tuple[DigisellerData, str]]:
        rows = self.get_digiseller_data(start_date, end_date)
        result = []
        for _, data_json, date in rows:
            data = DigisellerData.from_api(json.loads(data_json))
            result.append((data, date))
        return result

    def get_latest_data(self, table_name):
        if table_name not in ('plati_market_data', 'digiseller_data'):
            raise ValueError("Invalid table name")
        with self.conn:
            cursor = self.conn.execute(f'''
                SELECT * FROM {table_name}
                ORDER BY date DESC
                LIMIT 1
            ''')
            return cursor.fetchone()

    def close_connection(self):
        self.conn.close()
