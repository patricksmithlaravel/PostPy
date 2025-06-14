"""
CLI module.
"""
from .mock import mock_group
import click

@click.group()
def cli():
    """PostPy CLI tools."""
    pass

cli.add_command(mock_group, name='mock')

__all__ = ['cli', 'mock_group'] 