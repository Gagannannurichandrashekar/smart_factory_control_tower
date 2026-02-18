from __future__ import annotations
import sqlite3
from pathlib import Path
import pandas as pd

DB_PATH_DEFAULT = Path("data/factory.db")


def connect(db_path: str | Path = DB_PATH_DEFAULT) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db_path))
    con.execute("PRAGMA foreign_keys = ON;")
    return con


def read_df(con: sqlite3.Connection, query: str, params: tuple = ()) -> pd.DataFrame:
    return pd.read_sql_query(query, con, params=params)


def exec_sql(con: sqlite3.Connection, sql: str) -> None:
    con.executescript(sql)
    con.commit()


def has_tables(con: sqlite3.Connection) -> bool:
    cursor = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='machines'")
    return cursor.fetchone() is not None
