import sqlite3
from pathlib import Path


def get_connection(db_path: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_lineas_stock_code ON lineas_pedido(stock_code)"
    )
    return connection
