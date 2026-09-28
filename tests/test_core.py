from pathlib import Path

import pytest


def test_schema_and_query_ok(tmp_path):
    # All modules imported without error so far in cli chain.
    import importlib

    mods = ["excel_loader", "schema", "query_engine", "exporter"]
    package = "excel_llm_reader"
    for m in mods:
        assert importlib.import_module(f"{package}.{m}") is not None


def test_exporter_roundtrip(tmp_path):
    import pandas as pd

    from excel_llm_reader.exporter import Exporter

    exp = Exporter(output_dir=tmp_path)
    df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    xlsx = exp.to_excel(df, "r")
    csv = exp.to_csv(df, "r")
    assert xlsx.exists() and csv.exists()
    assert pd.read_excel(xlsx).equals(df)
    assert pd.read_csv(csv).equals(df)


def test_loader_and_query(tmp_path):
    import pandas as pd

    from excel_llm_reader.excel_loader import ExcelLoader
    from excel_llm_reader.query_engine import QueryEngine
    from excel_llm_reader.schema import SchemaBuilder

    xlsx = tmp_path / "data.xlsx"
    pd.DataFrame({"city": ["A", "B"], "pop": [10, 20]}).to_excel(
        xlsx, sheet_name="data", index=False
    )

    loader = ExcelLoader(db_path=tmp_path / "t.db")
    loaded = loader.load(xlsx)
    assert loaded == {"data": 2}

    schema = SchemaBuilder(db_path=tmp_path / "t.db")
    text = schema.build()
    assert '"data"' in text and "city" in text and "pop" in text

    engine = QueryEngine(db_path=tmp_path / "t.db")
    out = engine.run("SELECT SUM(pop) AS total FROM data")
    assert int(out["total"].iloc[0]) == 30


def test_read_only_blocked(tmp_path):
    import sqlite3

    from excel_llm_reader.query_engine import QueryEngine

    conn = sqlite3.connect(tmp_path / "t.db")
    conn.execute("CREATE TABLE x (a INTEGER)")
    conn.execute("INSERT INTO x VALUES (1)")
    conn.commit()
    conn.close()

    engine = QueryEngine(db_path=tmp_path / "t.db")
    with pytest.raises(ValueError):
        engine.run("DELETE FROM x")


def test_messy_preamble_detected(tmp_path):
    import pandas as pd

    from excel_llm_reader.excel_loader import ExcelLoader

    xlsx = tmp_path / "messy.xlsx"
    with pd.ExcelWriter(xlsx, engine="openpyxl") as writer:
        pd.DataFrame([[None, "Title Row"], [None, None, None], ["City", "Pop", None]]).to_excel(
            writer, sheet_name="S1", index=False, header=False
        )
        pd.DataFrame([["A", 10], ["B", 20]]).to_excel(
            writer, sheet_name="S1", index=False, header=False, startrow=3
        )

    loader = ExcelLoader(db_path=tmp_path / "deep.db")
    loaded = loader.load(xlsx)
    assert loaded == {"s1": 2}


def test_extract_sql_from_fence():
    from excel_llm_reader.llm_sql import LLMSqlGenerator

    out = LLMSqlGenerator._extract_sql("```sql\nSELECT 1\n```")
    assert out == "SELECT 1"
    out = LLMSqlGenerator._extract_sql("SELECT 2")
    assert out == "SELECT 2"