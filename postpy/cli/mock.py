"""
Mock server CLI commands.
"""

import os

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .output import printable

console = Console()

LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}


@click.group()
def mock_group() -> None:
    """Mock Server - Create and Run Mock API Servers

    \b
    The mock server allows you to:
    1. Create mock API servers for testing
    2. Define custom endpoints and responses
    3. Simulate real API behavior locally
    """


@mock_group.command()
@click.argument("config_path", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--host", default="localhost", show_default=True, help="Host to run the server on"
)
@click.option(
    "--port",
    default=5000,
    show_default=True,
    type=click.IntRange(0, 65535),
    help="Port to run the server on",
)
@click.option(
    "--debug",
    is_flag=True,
    help="Debug mode: verbose errors and reload when the config file changes",
)
def run(config_path: str, host: str, port: int, debug: bool) -> None:
    """Run a mock API server for testing.

    CONFIG_PATH: Path to the configuration file that defines endpoints and responses
    """
    from ..core.mock_server import MockConfigError, MockServer

    try:
        server = MockServer(config_path)
    except MockConfigError as exc:
        raise click.ClickException(str(exc)) from None

    # With the reloader on, this process only supervises a child that does the
    # serving, so let the child print the banner (again after each reload).
    if not debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        console.print(
            Panel.fit(
                Text(
                    f"Starting Mock Server\n"
                    f"Host: {host}\n"
                    f"Port: {port}\n"
                    f"Debug: {debug}\n"
                    f"Config: {config_path}"
                ),
                title="Mock Server",
                style="bold green",
            )
        )
        table = Table(title="Endpoints")
        table.add_column("Method", style="cyan")
        table.add_column("Path", style="green")
        table.add_column("Status", style="yellow")
        table.add_column("Conditions", style="magenta")
        for endpoint in server.endpoints:
            table.add_row(
                endpoint.method,
                Text(printable(endpoint.path)),
                str(endpoint.response.status_code),
                str(len(endpoint.conditions)) if endpoint.conditions else "",
            )
        console.print(table)
        if host not in LOOPBACK_HOSTS:
            console.print(
                Text(
                    f"Warning: listening on {host} makes the mock server reachable "
                    f"from other machines.",
                    style="bold yellow",
                ),
                soft_wrap=True,
            )

    server.run(host=host, port=port, debug=debug)


@mock_group.command()
@click.argument("output_path", type=click.Path(dir_okay=False))
@click.option(
    "--force", "-f", is_flag=True, help="Overwrite the file if it already exists"
)
def init(output_path: str, force: bool) -> None:
    """Create a new mock server configuration file.

    OUTPUT_PATH: Path where the configuration file will be created
    """
    from ..core.mock_server import MockServer

    try:
        MockServer.create_config(output_path, overwrite=force)
    except FileExistsError:
        raise click.ClickException(
            f"{output_path} already exists. Use --force to overwrite it."
        ) from None
    except OSError as exc:
        raise click.ClickException(str(exc)) from None
    console.print(
        Panel.fit(
            Text(f"Created Mock Server Configuration\nPath: {output_path}"),
            title="Mock Server",
            style="bold green",
        )
    )
