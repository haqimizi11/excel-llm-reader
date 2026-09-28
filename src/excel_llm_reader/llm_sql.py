import re

import ollama

from .config import DEFAULT_MODEL, OLLAMA_HOST


class LLMSqlGenerator:
    """Converts a natural-language question into executable SQL via Ollama."""

    SYSTEM_PROMPT = (
        "You are a data analyst. Convert the user's question into a single SQLite SELECT query. "
        "Only produce SQL, no explanation, no markdown fences. "
        "Use the table and column names exactly as given in the schema. "
        "Use SQLite syntax ONLY: never use backticks; if a column or table name contains "
        "spaces or special characters, wrap it in double quotes, e.g. SELECT AVG(\"CSAT Score\"). "
        "The answer must contain ONLY the SQL statement. "
        "Aggregate data with GROUP BY where appropriate and ORDER BY results meaningfully. "
        "Limit results to 500 rows unless the question asks for all rows."
    )

    def __init__(self, model: str = DEFAULT_MODEL, host: str = OLLAMA_HOST):
        self.model = model
        self.host = host
        self.client = ollama.Client(host=host)

    def generate_sql(self, question: str, schema: str, feedback: str = "") -> str:
        user_content = (
            f"-- Database schema:\n{schema}\n\n"
            f"-- Question:\n{question}\n\n"
        )
        if feedback:
            user_content += (
                "-- Your previous SQL failed with:\n"
                f"{feedback}\n\n"
                "-- Try again, output only a corrected single SQLite SELECT query.\n\n"
            )
        user_content += "-- SQL:"
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]
        response = self.client.chat(model=self.model, messages=messages)
        sql = response["message"]["content"].strip()
        return self._normalize_sql(self._extract_sql(sql), self._identifiers_from_schema(schema))

    @staticmethod
    def _identifiers_from_schema(schema: str) -> set[str]:
        """Extract quoted table/column names from the schema description."""
        return set(re.findall(r'"([^"]+)"', schema))

    @classmethod
    def _normalize_sql(cls, sql: str, identifiers: set[str]) -> str:
        """Convert MySQL-style backticks to double quotes, quote unquoted
        function-call arguments with spaces, and quote any schema identifier
        (column/table) that contains spaces or parentheses."""
        sql = re.sub(r"`([^`]+)`", r'"\1"', sql)

        def quote_arg(match: re.Match) -> str:
            func, arg = match.group(1), match.group(2).strip()
            return f'{func}("{arg}")' if " " in arg else match.group(0)

        sql = re.sub(r"(\w+)\(\s*([\w ]+?)\s*\)", quote_arg, sql)

        for ident in sorted(identifiers, key=len, reverse=True):
            if " " not in ident and "(" not in ident:
                continue
            pattern = re.compile(
                r'(?<!["\'`\w])' + re.escape(ident) + r'(?!["\'`\w])',
                re.IGNORECASE,
            )
            sql = pattern.sub(f'"{ident}"', sql)
        return sql.strip()

    @staticmethod
    def _extract_sql(text: str) -> str:
        fence = re.search(r"```(?:sql)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
        if fence:
            text = fence.group(1)
        text = text.strip()
        if text.startswith(("SELECT", "WITH", "select", "with")):
            text = text.split(";")[0]
        return text.strip().rstrip(";")