import sys
from dataclasses import dataclass, field

import pandas as pd
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .config import DEFAULT_MODEL
from .excel_loader import ExcelLoader
from .exporter import Exporter
from .llm_sql import LLMSqlGenerator
from .llm_summarizer import LLMSummarizer
from .query_engine import QueryEngine
from .schema import SchemaBuilder


@dataclass
class AppState:
    db_loaded: bool = False
    current_file: str = ""
    last_sql: str = ""
    last_result: pd.DataFrame = field(default_factory=pd.DataFrame)
    last_question: str = ""


class App:
    def __init__(self, model: str = DEFAULT_MODEL):
        self.console = Console()
        self.loader = ExcelLoader()
        self.schema_builder = SchemaBuilder()
        self.engine = QueryEngine()
        self.exporter = Exporter()
        self.generator = LLMSqlGenerator(model=model)
        self.summarizer = LLMSummarizer(model=model)
        self.state = AppState()

    def run(self) -> None:
        self._banner()
        while True:
            try:
                self._menu()
            except KeyboardInterrupt:
                self.console.print("\n[yellow]Interrupted. Press Enter to continue...[/yellow]")
                input()
            except (EOFError, SystemExit):
                break

    def _menu(self) -> None:
        self.console.print(Panel.fit(
            "[bold cyan]1.[/bold cyan] Ask a question\n"
            "[bold cyan]2.[/bold cyan] Change Excel file\n"
            "[bold magenta]e[/bold magenta] Export last result\n"
            "[bold magenta]h[/bold magenta] Help\n"
            "[bold magenta]q[/bold magenta] Quit",
            title="Main Menu",
            border_style="green",
        ))
        choice = self.console.input("Your choice: ").strip().lower()
        if choice in ("1", "ask"):
            self._ask_loop()
        elif choice == "2":
            self._change_file()
        elif choice in ("e", "export"):
            self._export()
        elif choice in ("h", "help"):
            self._show_help()
        elif choice in ("q", "exit", "quit"):
            raise SystemExit

    def _ask_loop(self) -> None:
        if not self.state.db_loaded:
            self.console.print("[yellow]No Excel file loaded yet. Loading one now...[/yellow]")
            if not self._choose_file():
                return
        self.console.print(
            "[green]Ask a question. Commands:[/green] [cyan]file[/cyan] (change Excel), "
            "[cyan]export[/cyan] (save result), [cyan]back[/cyan] (menu), [cyan]exit[/cyan] (quit)"
        )
        while True:
            try:
                question = self.console.input("[bold cyan]Q>[/bold cyan] ").strip()
            except (EOFError, KeyboardInterrupt):
                return
            if not question:
                continue
            if not self._run_q_command(question):
                return

    def _run_q_command(self, question: str) -> bool:
        """Handle a Q> input. Returns False when the user returns to the menu."""
        cmd = question.lower()
        if cmd == "back":
            return False
        if cmd in ("exit", "quit", "q"):
            raise SystemExit
        if cmd in ("e", "export"):
            self._export()
        elif cmd in ("2", "f", "file", "change"):
            self._change_file()
        elif cmd == "help":
            self._show_help()
        else:
            self._answer(question)
        return True

    def _answer(self, question: str) -> None:
        self.console.print("[dim]Generating SQL...[/dim]")
        try:
            schema = self.schema_builder.build()
            sql = self.generator.generate_sql(question, schema)
        except Exception as exc:
            self.console.print(f"[red]SQL generation failed: {exc}[/red]")
            return
        self.console.print(f"[dim]SQL:[/dim] [cyan]{sql}[/cyan]")
        try:
            df = self.engine.run(sql)
        except Exception as exc:
            self.console.print(f"[yellow]Query failed, retrying with correction...[/yellow]")
            try:
                sql = self.generator.generate_sql(question, schema, feedback=str(exc))
                self.console.print(f"[dim]SQL:[/dim] [cyan]{sql}[/cyan]")
                df = self.engine.run(sql)
            except Exception as exc2:
                self.console.print(f"[red]Query failed: {exc2}[/red]")
                return
        self.state.last_question = question
        self.state.last_sql = sql
        self.state.last_result = df
        self._show_result(df)
        try:
            summary = self.summarizer.summarize(
                question, sql, list(df.columns), df.head(10).values.tolist()
            )
            self.console.print(Panel(f"[green]{summary}[/green]", title="Summary", border_style="cyan"))
        except Exception as exc:
            self.console.print(f"[dim]Summary skipped: {exc}[/dim]")
        self._show_result_hint()

    def _show_result_hint(self) -> None:
        self.console.print(
            "[dim]Options:[/dim] [cyan]export[/cyan] (save .xlsx/.csv) | "
            "[cyan]file[/cyan] (change Excel) | [cyan]back[/cyan] (menu) | "
            "[cyan]exit[/cyan] (quit) | or ask another question"
        )

    def _show_result(self, df: pd.DataFrame) -> None:
        if df.empty:
            self.console.print("[yellow]Query returned no rows.[/yellow]")
            return
        table = Table(title=f"{len(df)} row(s) x {len(df.columns)} column(s)")
        cols = [str(c) for c in df.columns]
        for c in cols:
            table.add_column(c, overflow="fold")
        for _, row in df.head(50).iterrows():
            table.add_row(*[str(v) for v in row])
        if len(df) > 50:
            table.caption = f"Showing first 50 of {len(df)} rows (export for full data)"
        self.console.print(table)

    def _change_file(self) -> None:
        self._choose_file()

    def _choose_file(self) -> bool:
        path = self.console.input(
            "Path to Excel/CSV file (or [cyan]back[/cyan]): "
        ).strip().strip('"')
        if not path:
            return False
        path = self._expand_user(path)
        if not __import__("os").path.exists(path):
            self.console.print(f"[red]File not found: {path}[/red]")
            return False
        self.console.print("[dim]Loading sheets into SQLite...[/dim]")
        try:
            self.loader.clear()
            loaded = self.loader.load(path)
        except Exception as exc:
            self.console.print(f"[red]Failed to load: {exc}[/red]")
            return False
        self.state.db_loaded = True
        self.state.current_file = path
        tables = ", ".join(f"[green]{t}[/green]({n})" for t, n in loaded.items())
        self.console.print(f"[bold]Loaded[/bold] {path}")
        self.console.print(f"Tables: {tables}")
        return True

    def _export(self) -> None:
        if self.state.last_result.empty:
            self.console.print("[yellow]Nothing to export yet. Run a question first.[/yellow]")
            return
        name = self.console.input("Export filename (without extension): ").strip() or "query_result"
        try:
            xlsx_path = self.exporter.to_excel(self.state.last_result, name)
            csv_path = self.exporter.to_csv(self.state.last_result, name)
        except Exception as exc:
            self.console.print(f"[red]Export failed: {exc}[/red]")
            return
        self.console.print(f"[green]Exported:[/green] {xlsx_path}")
        self.console.print(f"[green]Exported:[/green] {csv_path}")

    def _show_help(self) -> None:
        self.console.print(Panel(
            "[bold cyan]1[/bold cyan] / [bold cyan]ask[/bold cyan]  - Ask a natural-language question.\n"
            "[bold cyan]2[/bold cyan] - Load/change an Excel or CSV file.\n"
            "[bold magenta]e[/bold magenta] / [bold magenta]export[/bold magenta] - Save the last result as .xlsx / .csv.\n"
            "[bold magenta]h[/bold magenta] / [bold magenta]help[/bold magenta] - Show this help.\n"
            "[bold magenta]q[/bold magenta] / [bold magenta]exit[/bold magenta] / [bold magenta]quit[/bold magenta] - Quit.\n"
            "At [bold cyan]Q>[/bold cyan] also use: [cyan]file[/cyan] (change Excel file), "
            "[cyan]back[/cyan] (return to menu), [cyan]export[/cyan] (save result).",
            title="Help",
            border_style="magenta",
        ))

    def _banner(self) -> None:
        self.console.print(Panel.fit(
            "[bold]Excel LLM Reader[/bold]\n"
            "Natural-language questions over your Excel data "
            "(Ollama -> SQL -> result -> export)",
            border_style="cyan",
        ))

    @staticmethod
    def _expand_user(path: str) -> str:
        import os

        return os.path.expanduser(path)


def main() -> int:
    model = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_MODEL
    App(model=model).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())