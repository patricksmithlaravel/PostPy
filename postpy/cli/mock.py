"""
Mock server CLI commands.
"""
import click
from pathlib import Path
from flask import Flask, request, jsonify
from rich.console import Console
from rich.panel import Panel

console = Console()

@click.group()
def mock_group():
    """Mock Server - Create and Run Mock API Servers

    The mock server allows you to:

    1. Create mock API servers for testing
    2. Define custom endpoints and responses
    3. Simulate real API behavior locally

    Available commands:
    """
    pass

@mock_group.command()
@click.argument('config_path', type=click.Path(exists=True))
@click.option('--host', default='localhost', help='Host to run the server on')
@click.option('--port', default=5000, help='Port to run the server on')
@click.option('--debug', is_flag=True, help='Run in debug mode')
def run(config_path, host, port, debug):
    """Run a mock API server for testing.

    CONFIG_PATH: Path to the configuration file that defines endpoints and responses
    """
    try:
        from ..core.mock_server import MockServer
        server = MockServer(config_path)
        console.print(Panel.fit(
            f"[bold green]Starting Mock Server[/bold green]\n"
            f"Host: {host}\n"
            f"Port: {port}\n"
            f"Debug: {debug}\n"
            f"Config: {config_path}",
            title="Mock Server"
        ))
        server.run(host=host, port=port, debug=debug)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        raise click.Abort()

@mock_group.command()
@click.argument('output_path', type=click.Path())
def init(output_path):
    """Create a new mock server configuration file.

    OUTPUT_PATH: Path where the configuration file will be created
    """
    try:
        from ..core.mock_server import MockServer
        MockServer.create_config(output_path)
        console.print(Panel.fit(
            f"[bold green]Created Mock Server Configuration[/bold green]\n"
            f"Path: {output_path}",
            title="Mock Server"
        ))
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        raise click.Abort() 