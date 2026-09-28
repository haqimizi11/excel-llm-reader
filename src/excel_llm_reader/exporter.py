from pathlib import Path

import pandas as pd

from .config import OUTPUT_DIR


class Exporter:
    """Exports query results to Excel and/or CSV."""

    def __init__(self, output_dir: Path | str = OUTPUT_DIR):
        self.output_dir = Path(output_dir)

    def to_excel(self, df: pd.DataFrame, filename: str) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_dir / self._ensure_suffix(filename, ".xlsx")
        df.to_excel(path, index=False)
        return path

    def to_csv(self, df: pd.DataFrame, filename: str) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_dir / self._ensure_suffix(filename, ".csv")
        df.to_csv(path, index=False)
        return path

    @staticmethod
    def _ensure_suffix(name: str, suffix: str) -> str:
        return name if name.lower().endswith(suffix) else f"{name}{suffix}"