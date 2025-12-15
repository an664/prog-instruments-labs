import sqlite3
import json
from datetime import datetime
from pathlib import Path

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
            self.conn.execute('CREATE INDEX IF NOT EXISTS idx_plati_market_date ON plati_market_data(date)')
            self.conn.execute('CREATE INDEX IF NOT EXISTS idx_digiseller_date ON digiseller_data(date)')

    def insert_plati_market_data(self, url, data):
        with self.conn:
            self.conn.execute('''
                INSERT INTO plati_market_data (url, data, date)
                VALUES (?, ?, ?)
            ''', (url, json.dumps(data), datetime.now().date()))

    def insert_digiseller_data(self, data):
        with self.conn:
            self.conn.execute('''
                INSERT INTO digiseller_data (data, date)
                VALUES (?, ?)
            ''', (json.dumps(data), datetime.now().date()))

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
