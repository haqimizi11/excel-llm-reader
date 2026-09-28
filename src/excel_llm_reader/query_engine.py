import sqlite3
from pathlib import Path

import pandas as pd

from .config import DB_PATH, SQL_SAFETY_SETTINGS


class QueryEngine:
    """Executes SQL safely against the loaded SQLite database."""

    def __init__(self, db_path: Path | str = DB_PATH):
        self.db_path = str(Path(db_path))

    def run(self, sql: str) -> pd.DataFrame:
        conn = sqlite3.connect(self.db_path)
        try:
            for key, value in SQL_SAFETY_SETTINGS.items():
                conn.execute(f"PRAGMA {key}={value}")
            sql_stripped = sql.strip().rstrip(";")
            if not self._is_read_only(sql_stripped):
                raise ValueError(
                    "Only SELECT statements are allowed (write operations are blocked)."
                )
            return pd.read_sql_query(sql_stripped, conn)
        finally:
            conn.close()

    @staticmethod
    def _is_read_only(sql: str) -> bool:
        stripped_comment_sql = "\n".join(
            line
            for line in sql.splitlines()
            if not line.strip().startswith("--")
        )
        head = " ".join(stripped_comment_sql.split())[:100].upper()
        return head.startswith(("SELECT", "WITH", "PRAGMA", "EXPLAIN"))