import ollama

from .config import DEFAULT_MODEL, OLLAMA_HOST


class LLMSummarizer:
    """Produces a short plain-English summary of query results."""

    def __init__(self, model: str = DEFAULT_MODEL, host: str = OLLAMA_HOST):
        self.model = model
        self.client = ollama.Client(host=host)

    def summarize(self, question: str, sql: str, columns: list[str], rows: list[list]) -> str:
        preview = (
            f"Columns: {columns}\nRows (max 10 of {len(rows)}):\n"
            + "\n".join([", ".join(str(v) for v in r) for r in rows[:10]])
        )
        system = (
            "You summarize SQL query results for a non-technical person. "
            "Be concise (2-4 sentences), highlight key numbers and trends. "
            "Only output the summary, no preamble."
        )
        user = (
            f"Question: {question}\n\nSQL: {sql}\n\nQuery results preview:\n{preview}\n\n"
            "Give a short, clear summary."
        )
        response = self.client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response["message"]["content"].strip()