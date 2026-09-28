import os
from pathlib import Path

DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "mistral:latest")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_DIR / "data"
OUTPUT_DIR = PROJECT_DIR / "output"

DB_PATH = Path(os.getenv("DB_PATH", str(PROJECT_DIR / "data" / "excel_reader.db")))
MODELS_DIR = Path(os.getenv("MODELS_DIR", str(PROJECT_DIR / "models")))

SQL_SAFETY_SETTINGS = {"query_only": True, "temp_store": "memory"}