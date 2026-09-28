import sqlite3
from pathlib import Path

import pandas as pd

from .config import DB_PATH


class ExcelLoader:
    """Loads Excel sheets (xlsx/xls/csv) into SQLite tables."""

    def __init__(self, db_path: Path | str = DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def load(
        self,
        file_path: Path | str,
        sheet_names: list[str] | None = None,
        auto_header: bool = True,
    ) -> dict:
        """Load an Excel file into SQLite. Returns {table_name: row_count}."""
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        sheets = self._read_sheets(file_path, sheet_names, auto_header)
        loaded = {}
        conn = sqlite3.connect(self.db_path)
        try:
            for sheet_name, df in sheets.items():
                table_name = self._to_table_name(sheet_name)
                df.to_sql(table_name, conn, if_exists="replace", index=False)
                loaded[table_name] = int(df.shape[0])
        finally:
            conn.close()
        return loaded

    def list_tables(self) -> list[str]:
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
            return [r[0] for r in cur.fetchall()]
        finally:
            conn.close()

    def clear(self) -> None:
        """Drop all existing tables so a newly loaded file replaces them."""
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
            for (name,) in cur.fetchall():
                conn.execute(f'DROP TABLE IF EXISTS "{name}"')
            conn.commit()
        finally:
            conn.close()

    def _read_sheets(
        self,
        file_path: Path,
        sheet_names: list[str] | None,
        auto_header: bool,
    ) -> dict[str, pd.DataFrame]:
        if file_path.suffix.lower() == ".csv":
            raw = pd.read_csv(file_path, header=None)
            df = self._clean_frame(raw)
            return {file_path.stem: df}

        xl = pd.ExcelFile(file_path)
        names = sheet_names or xl.sheet_names
        frames = {}
        for name in names:
            raw = xl.parse(name, header=None)
            frames[name] = self._clean_frame(raw) if auto_header else xl.parse(name)
        return frames

    @staticmethod
    def _clean_frame(raw: pd.DataFrame) -> pd.DataFrame:
        """Detect the real header row in a messy sheet and return a tidy DataFrame.

        Skips title/blank preamble (rows with fewer than 2 filled cells),
        treats the first data-like row as the header, and drops empty
        rows/columns that pandas would leave as 'Unnamed' columns.
        """
        threshold = min(2, raw.shape[1])
        header_idx = 0
        for i in range(len(raw)):
            filled = [
                str(v).strip()
                for v in raw.iloc[i].tolist()
                if pd.notna(v) and str(v).strip() != ""
            ]
            if len(filled) >= threshold:
                header_idx = i
                break

        header = [
            str(v).strip() if pd.notna(v) and str(v).strip() != "" else f"col_{j}"
            for j, v in enumerate(raw.iloc[header_idx].tolist())
        ]
        data = raw.iloc[header_idx + 1 :].copy()
        data.columns = header
        data = data.dropna(how="all").dropna(axis=1, how="all")
        return data.reset_index(drop=True)

    @staticmethod
    def _to_table_name(sheet_name: str) -> str:
        name = sheet_name.strip().replace(" ", "_").lower()
        return "".join(c for c in name if c.isalnum() or c == "_") or "sheet"