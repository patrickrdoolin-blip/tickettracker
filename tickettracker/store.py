import os
import sqlite3
import uuid
from pathlib import Path
import pandas as pd
import streamlit as st

def _secret(name, default=""):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return os.getenv(name, default)

class Store:
    def __init__(self):
        self.supabase_url = _secret("SUPABASE_URL")
        self.supabase_key = _secret("SUPABASE_KEY")
        self.remote = bool(self.supabase_url and self.supabase_key)
        if self.remote:
            from supabase import create_client
            self.client = create_client(self.supabase_url, self.supabase_key)
        else:
            self.path = Path(os.getenv("TICKETTRACKER_DB", "tickettracker.db"))
            self._init_sqlite()

    def _init_sqlite(self):
        with sqlite3.connect(self.path) as con:
            con.executescript("""
            CREATE TABLE IF NOT EXISTS events (
              id TEXT PRIMARY KEY, event_name TEXT NOT NULL, event_date TEXT,
              city TEXT, platform TEXT NOT NULL, url TEXT NOT NULL,
              target_price REAL, currency TEXT DEFAULT 'USD', created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS snapshots (
              id TEXT PRIMARY KEY, event_id TEXT NOT NULL, price REAL NOT NULL,
              currency TEXT, platform TEXT, section TEXT, notes TEXT, checked_at TEXT
            );
            CREATE TABLE IF NOT EXISTS alerts (
              id TEXT PRIMARY KEY, event_id TEXT, price REAL, message TEXT,
              email_sent INTEGER DEFAULT 0, created_at TEXT
            );
            """)

    def _read(self, table):
        if self.remote:
            result = self.client.table(table).select("*").execute()
            return pd.DataFrame(result.data or [])
        with sqlite3.connect(self.path) as con:
            return pd.read_sql_query(f"SELECT * FROM {table}", con)

    def list_events(self):
        return self._read("events")

    def list_snapshots(self):
        return self._read("snapshots")

    def list_alerts(self):
        return self._read("alerts")

    def _insert(self, table, row):
        row = dict(row)
        row["id"] = str(uuid.uuid4())
        if self.remote:
            self.client.table(table).insert(row).execute()
        else:
            columns = list(row.keys())
            values = [row[c] for c in columns]
            marks = ",".join(["?"] * len(columns))
            with sqlite3.connect(self.path) as con:
                con.execute(
                    f"INSERT INTO {table} ({','.join(columns)}) VALUES ({marks})", values
                )

    def add_event(self, row):
        self._insert("events", row)

    def add_snapshot(self, row):
        self._insert("snapshots", row)

    def add_alert(self, row):
        self._insert("alerts", row)
