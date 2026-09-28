# Excel LLM Reader

Ask natural-language questions over your Excel data — powered by a local LLM (Ollama).

Pipeline: **Excel → SQLite → your question → Ollama (SQL) → result → plain-English summary → export (.xlsx / .csv)**

## Requirements

- Python 3.11+
- [Ollama](https://ollama.com) running locally with a model pulled (e.g. `ollama pull mistral`)

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Generate sample data (optional):

```powershell
python scripts\make_sample_data.py
```

## Usage

```powershell
.\.venv\Scripts\python -m excel_llm_reader            # default model (mistral:latest)
.\.venv\Scripts\python -m excel_llm_reader qwen2.5:7b  # or pick another model
```

Interactive menu:

```
1. Ask a question        -> ask in plain English, get SQL + result table + summary
2. Change Excel file     -> load a different .xlsx / .xls / .csv (replaces previous data)
e  Export last result    -> save as .xlsx and .csv (works right after a question)
h  Help
q  Quit
```

While at the `Q>` prompt also use: `back` (return to menu), `file`, `export`, `exit`.

### Messy files

The loader auto-detects messy sheets: title/blank rows before the header are
skipped, the first data-like row is used as the header, and empty columns are
dropped. Files with a normal first-row header work unchanged.

## Project layout

```
src/excel_llm_reader/
  config.py         settings (model, DB path, output dir)
  excel_loader.py   Excel/CSV -> SQLite tables
  schema.py         schema + sample rows for the LLM prompt
  llm_sql.py        Ollama: question -> SQL
  llm_summarizer.py Ollama: results -> short summary
  query_engine.py   safe read-only SQL execution
  exporter.py       DataFrame -> .xlsx / .csv
  cli.py            interactive menu app
tests/              pytest suite
```

## Tests

```powershell
.\.venv\Scripts\python -m pytest
```

## Configuration (env vars)

| Variable       | Default               |
|----------------|-----------------------|
| `OLLAMA_MODEL` | `mistral:latest`       |
| `OLLAMA_HOST`  | `http://localhost:11434` |
| `DB_PATH`      | `<project>/data/excel_reader.db` |