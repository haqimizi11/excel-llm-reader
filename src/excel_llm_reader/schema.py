import sqlite3
from pathlib import Path

from .config import DB_PATH


class SchemaBuilder:
    """Builds a human-readable schema description for the LLM prompt."""

    def __init__(self, db_path: Path | str = DB_PATH):
        self.db_path = str(db_path)

    def build(self, sample_rows: int = 3) -> str:
        conn = sqlite3.connect(self.db_path)
        try:
            tables = [
                r[0]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
                ).fetchall()
            ]
            if not tables:
                return "No tables found in the database."

            parts = []
            for table in tables:
                cols = conn.execute(f'PRAGMA table_info("{table}")').fetchall()
                col_sql = [
                    f'"{row[1]}" {row[2] or "TEXT"}' + (" PRIMARY KEY" if row[5] else "")
                    for row in cols
                ]
                parts.append(f'CREATE TABLE "{table}" (\n  ' + ",\n  ".join(col_sql) + "\n);")

                try:
                    cur = conn.execute(
                        f'SELECT * FROM "{table}" LIMIT ?', (sample_rows,)
                    )
                    rows = cur.fetchall()
                    headers = [d[0] for d in cur.description]
                    parts.append(
                        f"-- Sample rows (max {sample_rows}) from {table}:\n"
                        + "\n".join(
                            "INSERT INTO "
                            + f'"{table}"'
                            + " VALUES "
                            + "("
                            + ", ".join(repr(v) if v is not None else "NULL" for v in row)
                            + ");"
                            for row in rows
                        )
                    )
                except sqlite3.Error:
                    pass

            return "\n\n".join(parts)
        finally:
            conn.close()

    def build_short(self) -> str:
        """Comma-separated table list + column names, one line per table."""
        return "\n".join(line.strip().rstrip(";") for line in self.build(0).splitlines() if line.strip())