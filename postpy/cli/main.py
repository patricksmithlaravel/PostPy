"""
Main CLI module for PostPy.
"""
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
import json
from datetime import datetime
from .mock import mock_group

from ..core.loader import CollectionLoader
from ..core.executor import RequestExecutor

console = Console()

@click.group()
@click.version_option(version="1.1.0", prog_name="PostPy")
def cli():
    """[bold blue]PostPy[/bold blue] - API Testing and Automation Framework

    A powerful tool for API testing, automation, and mock server development. PostPy helps you:
    
    • Test APIs with ease using a simple configuration
    • Instantly serve mock API responses for development and testing
    • Automate API workflows with a flexible framework
    
    For more information, visit: https://github.com/yourusername/postpy
    """
    pass

cli.add_command(mock_group, name='mock')

@cli.command()
@click.argument('collection_file')
@click.option('--env-file', '-e', help='Path to environment file')
@click.option('--request-name', '-r', help='Run specific request by name')
def run_collection(collection_file: str, env_file: str, request_name: str):
    """Run requests from a collection file."""
    try:
        # Load collection
        collection = CollectionLoader.load_collection(collection_file)
        
        # Load environment if provided
        env_vars = {}
        if env_file:
            env = CollectionLoader.load_environment(env_file)
            env_vars = env.variables
        
        # Initialize executor
        executor = RequestExecutor(str(collection.base_url), env_vars)
        
        # Filter requests if name specified
        requests = [r for r in collection.requests if not request_name or r.name == request_name]
        
        if not requests:
            console.print(f"[red]No requests found{' matching ' + request_name if request_name else ''}[/red]")
            return
        
        for req in requests:
            response = executor.execute(req)
            console.print(f"[green]Request:[/green] {req.name}")
            console.print(f"[cyan]Status:[/cyan] {response.status_code}")
            console.print(f"[yellow]Response:[/yellow] {response.text}")
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")

@cli.command()
@click.argument('collection_file')
def show_collection(collection_file: str):
    """Display collection details."""
    try:
        collection = CollectionLoader.load_collection(collection_file)
        
        console.print(Panel(f"[bold blue]{collection.collection_name}[/bold blue]"))
        console.print(f"Base URL: {collection.base_url}")
        
        table = Table(title="Requests")
        table.add_column("Name", style="cyan")
        table.add_column("Method", style="green")
        table.add_column("Endpoint", style="yellow")
        table.add_column("Tests", style="magenta")
        
        for request in collection.requests:
            has_tests = "Yes" if request.tests else "No"
            table.add_row(
                request.name,
                request.method,
                request.endpoint,
                has_tests
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")

@cli.command()
@click.argument('collection_file')
def show_history(collection_file: str):
    """Display request history."""
    try:
        collection = CollectionLoader.load_collection(collection_file)
        executor = RequestExecutor(str(collection.base_url))
        
        if not executor.history:
            console.print("[yellow]No request history available[/yellow]")
            return
        
        table = Table(title="Request History")
        table.add_column("Method", style="cyan")
        table.add_column("Endpoint", style="green")
        table.add_column("Status", style="yellow")
        table.add_column("Time", style="magenta")
        table.add_column("Duration", style="blue")
        
        for entry in executor.history:
            status_color = "green" if 200 <= entry.status_code < 300 else "red"
            table.add_row(
                entry.method,
                entry.endpoint,
                f"[{status_color}]{entry.status_code}[/{status_color}]",
                entry.timestamp,
                f"{entry.response_time:.2f}s"
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")

def main():
    cli() 