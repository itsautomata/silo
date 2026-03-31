from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from silo.scanner.scan import scan

app = typer.Typer(
    name="silo",
    help="contain. defend. deploy.",
    no_args_is_help=True,
    invoke_without_command=True,
)
console = Console()


@app.callback()
def main():
    """contain. defend. deploy."""


@app.command("scan")
def scan_cmd(
    app_path: Path = typer.Argument(..., help="path to the app to scan"),
    json_output: bool = typer.Option(False, "--json", "-j", help="output as JSON"),
    exclude: list[str] = typer.Option([], "--exclude", "-e", help="directories to skip (e.g. -e tmp -e vendor)"),
    only: list[str] = typer.Option([], "--only", help="only scan these directories (e.g. --only src --only lib)"),
):
    """analyze a codebase. detect dependencies, secrets, AI patterns."""

    if not app_path.is_dir():
        console.print(f"[red]not a directory: {app_path}[/red]")
        raise typer.Exit(1)

    exclude_set = set(exclude) if exclude else None
    only_set = set(only) if only else None

    console.print(f"[bold]scanning[/bold] {app_path.resolve()}")
    if exclude_set:
        console.print(f"[dim]excluding: {', '.join(sorted(exclude_set))}[/dim]")
    if only_set:
        console.print(f"[dim]only: {', '.join(sorted(only_set))}[/dim]")
    console.print()

    result = scan(app_path, exclude=exclude_set, include_only=only_set)

    if json_output:
        console.print(result.model_dump_json(indent=2))
        return

    # identity
    console.print(f"[bold cyan]app:[/bold cyan] {result.app_name}")
    console.print(f"[bold cyan]language:[/bold cyan] {result.language or 'unknown'}")
    console.print(f"[bold cyan]framework:[/bold cyan] {result.framework or 'none detected'}")
    console.print(f"[bold cyan]entry point:[/bold cyan] {result.entry_point or 'unknown'}")
    console.print(f"[bold cyan]dependency file:[/bold cyan] {result.dependency_file or 'none found'}")
    console.print()

    # dependencies
    if result.dependencies:
        table = Table(title="dependencies", show_lines=False)
        table.add_column("name", style="white")
        table.add_column("version", style="dim")
        table.add_column("source", style="dim")
        for dep in result.dependencies[:20]:
            table.add_row(dep.name, dep.version or "—", dep.source)
        if len(result.dependencies) > 20:
            table.add_row(f"... +{len(result.dependencies) - 20} more", "", "")
        console.print(table)
        console.print()

    # env vars
    if result.env_vars:
        table = Table(title="environment variables", show_lines=False)
        table.add_column("name", style="yellow")
        table.add_column("found in", style="dim")
        for var in result.env_vars:
            table.add_row(var.name, ", ".join(var.found_in[:3]))
        console.print(table)
        console.print()

    # exposed secrets
    if result.exposed_secrets:
        console.print("[bold red]EXPOSED SECRETS[/bold red]")
        for secret in result.exposed_secrets:
            console.print(
                f"  [red]{secret.severity}[/red] {secret.type} "
                f"in {secret.file}:{secret.line}"
            )
        console.print()
    else:
        console.print("[green]no exposed secrets found[/green]\n")

    # AI-native profile
    if result.ai:
        ai = result.ai
        label = "[bold magenta]AI-native[/bold magenta]" if ai.is_ai_native else "[magenta]AI-enhanced[/magenta]"
        console.print(f"{label}\n")

        if ai.providers:
            console.print("[bold]providers:[/bold]")
            for p in ai.providers:
                env = f" ({p.env_var})" if p.env_var else ""
                console.print(f"  {p.name}{env}")
            console.print()

        if ai.models:
            console.print("[bold]models:[/bold]")
            for m in ai.models:
                console.print(f"  {m.model_id or '?'} ({m.provider}) in {m.file}")
            console.print()

        if ai.vector_db:
            console.print(f"[bold]vector DB:[/bold] {ai.vector_db.type} ({ai.vector_db.connection_method})")

        if ai.agent_framework:
            console.print(f"[bold]agent framework:[/bold] {ai.agent_framework}")

        if ai.has_agent_loop:
            console.print("[bold]agent loop:[/bold] detected")

        if ai.prompt_locations:
            console.print(f"[bold]prompts:[/bold] {len(ai.prompt_locations)} locations")

        if ai.embedding_calls:
            console.print(f"[bold]embeddings:[/bold] {len(ai.embedding_calls)} files")

        console.print()
    else:
        console.print("[dim]no AI patterns detected[/dim]\n")

    # errors
    if result.errors:
        console.print(f"[bold yellow]warnings ({len(result.errors)})[/bold yellow]")
        for err in result.errors:
            loc = f" in {err.file}" if err.file else ""
            console.print(f"  [yellow]{err.phase}{loc}:[/yellow] {err.error}")
        console.print()

    console.print("[bold green]scan complete[/bold green]")


if __name__ == "__main__":
    app()
