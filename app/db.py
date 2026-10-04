from __future__ import annotations
import os, sqlite3
from contextlib import contextmanager
from pathlib import Path
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

DB_PATH = Path(os.getenv('DATABASE_PATH', './data/ahmed_tv.db'))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def _fernet() -> Fernet:
    key = os.getenv('FERNET_KEY')
    if not key:
        raise RuntimeError('FERNET_KEY is required; generate one with Fernet.generate_key()')
    return Fernet(key.encode())


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    return _fernet().decrypt(value.encode()).decode()


@contextmanager
def connect():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys = ON')
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db() -> None:
    with connect() as con:
        con.executescript('''
        CREATE TABLE IF NOT EXISTS servers (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT NOT NULL UNIQUE,
          url TEXT NOT NULL,
          username_enc TEXT NOT NULL,
          password_enc TEXT NOT NULL,
          enabled INTEGER NOT NULL DEFAULT 1,
          last_sync TEXT,
          last_error TEXT,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS categories (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          server_id INTEGER NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
          category_id TEXT NOT NULL,
          name TEXT NOT NULL,
          kind TEXT NOT NULL DEFAULT 'live',
          UNIQUE(server_id, category_id, kind)
        );
        CREATE TABLE IF NOT EXISTS channels (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          server_id INTEGER NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
          stream_id INTEGER NOT NULL,
          name TEXT NOT NULL,
          icon TEXT,
          category_id TEXT,
          category_name TEXT,
          stream_type TEXT NOT NULL DEFAULT 'live',
          container_extension TEXT,
          updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(server_id, stream_id)
        );
        CREATE TABLE IF NOT EXISTS app_settings (
          key TEXT PRIMARY KEY,
          value TEXT NOT NULL,
          updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        ''')


def server_row(server_id: int):
    with connect() as con:
        return con.execute('SELECT * FROM servers WHERE id=?', (server_id,)).fetchone()


def server_credentials(row):
    return row['url'].rstrip('/'), decrypt(row['username_enc']), decrypt(row['password_enc'])
