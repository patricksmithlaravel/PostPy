"""
Main CLI module for PostPy.
"""

import json
from typing import Optional

import click
from pydantic import ValidationError
from rich.console import Console
from rich.json import JSON
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .. import __version__
from ..core.errors import format_validation_error
from ..core.executor import DEFAULT_TIMEOUT
from ..core.history import HistoryStore
from ..core.loader import CollectionLoader
from ..core.models import Collection
from ..core.runner import CollectionRunner, RequestResult
from .mock import mock_group

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="PostPy")
def cli() -> None:
    """PostPy - API Testing and Automation Framework

    \b
    Run collections of HTTP requests with assertions, view their history,
    and serve mock APIs from a YAML file.

    Documentation: https://github.com/patricksmithlaravel/PostPy
    """


cli.add_command(mock_group, name="mock")


def _load_collection(collection_file: str) -> Collection:
    try:
        return CollectionLoader.load_collection(collection_file)
    except ValidationError as exc:
        raise click.ClickException(
            format_validation_error(exc, f"Invalid collection {collection_file}:")
        ) from None
    except (OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from None


def _print_body(result: RequestResult) -> None:
    response = result.response
    if response is None or not response.content:
        return
    if "json" in response.headers.get("Content-Type", "").lower():
        try:
            console.print(JSON(response.text), soft_wrap=True)
            return
        except json.JSONDecodeError:
            pass
    console.print(Text(response.text), soft_wrap=True)


def _print_result(result: RequestResult, quiet: bool) -> None:
    request = result.request
    line = Text.assemble(
        (
            "PASS" if result.passed else "FAIL",
            "bold green" if result.passed else "bold red",
        ),
        "  ",
        (request.name, "bold"),
        "  ",
        (request.method, "cyan"),
        " ",
        request.endpoint,
    )
    if result.response is not None:
        elapsed_ms = result.response.elapsed.total_seconds() * 1000
        line.append(f"  -> {result.response.status_code}", style="yellow")
        line.append(f" ({elapsed_ms:.0f} ms)", style="dim")
    else:
        line.append(f"  -> error: {result.error}", style="red")
    console.print(line, soft_wrap=True)

    for assertion in result.assertions:
        console.print(
            Text.assemble(
                "    ",
                (
                    "ok  " if assertion.passed else "x   ",
                    "green" if assertion.passed else "red",
                ),
                assertion.name,
                (f"  {assertion.message}", "dim"),
            ),
            soft_wrap=True,
        )
    if not quiet:
        _print_body(result)
    console.print()


@cli.command()
@click.argument("collection_file", type=click.Path(dir_okay=False))
@click.option(
    "--env-file",
    "-e",
    type=click.Path(exists=True, dir_okay=False),
    help="Path to a .env file with variables for {{placeholders}}.",
)
@click.option("--request-name", "-r", help="Run only the request with this name.")
@click.option(
    "--timeout",
    type=click.FloatRange(min=0, min_open=True),
    default=DEFAULT_TIMEOUT,
    show_default=True,
    help="Seconds to wait for each response.",
)
@click.option("--quiet", "-q", is_flag=True, help="Do not print response bodies.")
def run_collection(
    collection_file: str,
    env_file: Optional[str],
    request_name: Optional[str],
    timeout: float,
    quiet: bool,
) -> None:
    """Run requests from a collection file and check their tests.

    Exits with status 1 if any request fails or any test does not pass.
    """
    collection = _load_collection(collection_file)
    variables = {}
    if env_file:
        variables = CollectionLoader.load_environment(env_file).variables

    runner = CollectionRunner(collection, variables, timeout=timeout)
    if request_name is not None:
        try:
            runner.get_request(request_name)
        except KeyError as exc:
            raise click.ClickException(exc.args[0]) from None

    console.print(
        Panel.fit(Text(collection.collection_name, style="bold blue"), title="PostPy")
    )
    results = []
    try:
        for result in runner.iter_run(request_name):
            results.append(result)
            _print_result(result, quiet)
    finally:
        try:
            HistoryStore(collection_file).append(runner.history)
        except OSError as exc:
            console.print(
                Text(f"Could not save request history: {exc}", style="yellow")
            )

    failed = sum(1 for result in results if not result.passed)
    summary = Text(f"{len(results) - failed} passed, {failed} failed")
    summary.stylize("bold red" if failed else "bold green")
    console.print(summary)
    if failed:
        raise click.exceptions.Exit(1)


@cli.command()
@click.argument("collection_file", type=click.Path(dir_okay=False))
def show_collection(collection_file: str) -> None:
    """Display collection details."""
    collection = _load_collection(collection_file)

    console.print(Panel(Text(collection.collection_name, style="bold blue")))
    console.print(Text(f"Base URL: {collection.base_url}"))

    table = Table(title="Requests")
    table.add_column("Name", style="cyan")
    table.add_column("Method", style="green")
    table.add_column("Endpoint", style="yellow")
    table.add_column("Tests", style="magenta")

    for request in collection.requests:
        table.add_row(
            Text(request.name),
            Text(request.method),
            Text(request.endpoint),
            "Yes" if request.tests else "No",
        )

    console.print(table)


@cli.command()
@click.argument("collection_file", type=click.Path(dir_okay=False))
@click.option(
    "--limit",
    "-n",
    type=click.IntRange(min=1),
    default=20,
    show_default=True,
    help="Number of most recent entries to show.",
)
def show_history(collection_file: str, limit: int) -> None:
    """Display request history recorded by run-collection."""
    store = HistoryStore(collection_file)
    entries = store.read(limit=limit)

    if not entries:
        console.print(Text("No request history available", style="yellow"))
        return

    table = Table(title="Request History")
    table.add_column("Time", style="magenta")
    table.add_column("Name", style="cyan")
    table.add_column("Method", style="cyan")
    table.add_column("Endpoint", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Duration", style="blue")

    for entry in reversed(entries):
        status_color = "green" if 200 <= entry.status_code < 300 else "red"
        table.add_row(
            entry.timestamp.replace("T", " "),
            Text(entry.name or ""),
            entry.method,
            Text(entry.endpoint),
            Text(str(entry.status_code), style=status_color),
            f"{entry.response_time:.2f}s",
        )

    console.print(table)


def main() -> None:
    cli()
