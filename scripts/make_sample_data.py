import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from excel_llm_reader.excel_loader import ExcelLoader
from excel_llm_reader.query_engine import QueryEngine

DATA_DIR = Path(__file__).resolve().parent


def main() -> None:
    sales = pd.DataFrame(
        {
            "region": ["North", "North", "South", "South", "East", "East", "West", "West", "North", "South"],
            "product": ["Widget A", "Widget B", "Widget A", "Widget B", "Widget A", "Widget B", "Widget A", "Widget B", "Widget C", "Widget C"],
            "units": [120, 80, 90, 110, 150, 60, 70, 95, 45, 130],
            "price": [10.0, 15.0, 10.0, 15.0, 12.0, 16.0, 12.0, 16.0, 8.0, 8.0],
            "date": pd.to_datetime(
                ["2024-01-05", "2024-01-12", "2024-02-02", "2024-02-14", "2024-03-03", "2024-03-18", "2024-04-01", "2024-04-22", "2024-05-05", "2024-05-19"]
            ),
        }
    )
    employees = pd.DataFrame(
        {
            "region": ["North", "North", "South", "East", "West", "West"],
            "name": ["Alice", "Bob", "Carol", "Dan", "Eve", "Frank"],
            "role": ["Manager", "Sales", "Sales", "Manager", "Sales", "Analyst"],
            "salary": [90000, 60000, 58000, 88000, 62000, 55000],
        }
    )
    file_path = DATA_DIR / "sample_sales.xlsx"
    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        sales.to_excel(writer, sheet_name="Sales", index=False)
        employees.to_excel(writer, sheet_name="Employees", index=False)

    loader = ExcelLoader()
    loaded = loader.load(file_path)
    print(f"Created {file_path}")
    print("Loaded tables:", loaded)

    engine = QueryEngine()
    df = engine.run(
        "SELECT region, SUM(units * price) AS revenue FROM sales GROUP BY region ORDER BY revenue DESC"
    )
    print("Smoke test result:")
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()