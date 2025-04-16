#!/usr/bin/env python3
import logging
import os
import sys
from typing import Optional

import typer
from rich.console import Console
from rich.logging import RichHandler

from app.server import run_mcp_server, create_mcp_server
from config.settings import load_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger("mcp_wrapper")

# Create Typer app
app = typer.Typer(name="mcp-wrapper", help="MCP Applications Wrapper")
console = Console()

# Create default MCP instance for use with fastmcp install
# Use a default config path for demonstration
default_config_path = os.path.join(os.path.dirname(__file__), "examples", "config.yaml")
if os.path.exists(default_config_path):
    mcp = create_mcp_server(default_config_path)
else:
    # If default config doesn't exist, create a basic MCP instance
    from fastmcp import FastMCP
    mcp = FastMCP("Applications Wrapper")


@app.command()
def run(
    config_path: str = typer.Argument(..., help="Path to configuration file (YAML or JSON)"),
    host: str = typer.Option("0.0.0.0", help="Host to bind the server to (not currently supported by FastMCP)"),
    port: int = typer.Option(8000, help="Port to run the server on (not currently supported by FastMCP)"),
    transport: str = typer.Option(
        "sse", help="Transport to use (sse, stdio)"
    ),
    log_level: str = typer.Option(
        "INFO", help="Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    ),
):
    """Run the MCP applications wrapper server."""
    # Set log level
    log_level_num = getattr(logging, log_level.upper(), None)
    if not isinstance(log_level_num, int):
        console.print(f"[bold red]Invalid log level: {log_level}[/bold red]")
        raise typer.Exit(1)
    
    logging.root.setLevel(log_level_num)
    
    # Validate config file
    if not os.path.exists(config_path):
        console.print(f"[bold red]Config file not found: {config_path}[/bold red]")
        raise typer.Exit(1)
    
    try:
        # Load config to validate it
        config = load_config(config_path)
        console.print(f"[bold green]Configuration loaded with {len(config.applications)} applications[/bold green]")
        
        # Print deployment mode
        console.print(f"[bold blue]Deployment mode: {config.deployment_mode}[/bold blue]")
        
        # Inform user about host/port not being used
        if host != "0.0.0.0" or port != 8000:
            console.print("[bold yellow]Note: Host and port options are not currently supported by FastMCP[/bold yellow]")
        
        # Run the server
        console.print(f"[bold]Starting MCP server with {transport} transport...[/bold]")
        run_mcp_server(config_path, host, port, transport)
        
    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        logger.exception("Error running MCP server")
        raise typer.Exit(1)


@app.command()
def validate(
    config_path: str = typer.Argument(..., help="Path to configuration file (YAML or JSON)"),
):
    """Validate a configuration file without running the server."""
    if not os.path.exists(config_path):
        console.print(f"[bold red]Config file not found: {config_path}[/bold red]")
        raise typer.Exit(1)
    
    try:
        config = load_config(config_path)
        
        # Print deployment mode
        console.print(f"[bold blue]Deployment mode: {config.deployment_mode}[/bold blue]")
        
        # Print application info
        console.print(f"[bold green]Configuration is valid with {len(config.applications)} applications:[/bold green]")
        
        for name, app_config in config.applications.items():
            console.print(f"  [blue]{name}[/blue]: {app_config.interpreter_type} | {app_config.working_directory}")
            
        console.print("[bold green]✓ Configuration is valid[/bold green]")
        
    except Exception as e:
        console.print(f"[bold red]Error validating configuration: {e}[/bold red]")
        logger.exception("Error validating configuration")
        raise typer.Exit(1)


@app.command()
def create_config(
    output_path: str = typer.Argument(..., help="Path to output configuration file"),
    format: str = typer.Option("yaml", help="Output format (yaml or json)"),
):
    """Create a sample configuration file."""
    import json
    import yaml
    
    # Sample configuration
    sample_config = {
        "applications": {
            "sample_python_app": {
                "name": "Sample Python App",
                "description": "A sample Python application",
                "working_directory": "/path/to/python/app",
                "interpreter_type": "python",
                "command": "app.py",
                "args": ["--arg1", "value1"],
                "env_vars": {
                    "ENV_VAR1": "value1",
                    "ENV_VAR2": "value2"
                },
                "timeout": 600  # 10 minutes timeout
            },
            "sample_node_app": {
                "name": "Sample Node App",
                "description": "A sample Node.js application",
                "working_directory": "/path/to/node/app",
                "interpreter_type": "node",
                "command": "server.js",
                "env_vars": {
                    "NODE_ENV": "production"
                },
                "timeout": 300  # 5 minutes timeout
            }
        },
        "deployment_mode": "local",
        "docker_config": {
            "base_image": "python:3.11-slim",
            "network": "bridge",
            "volumes": {
                "/host/path": "/container/path"
            }
        }
    }
    
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        
        # Write the configuration
        with open(output_path, 'w') as f:
            if format.lower() == 'json':
                json.dump(sample_config, f, indent=2)
            else:
                yaml.dump(sample_config, f, default_flow_style=False)
        
        console.print(f"[bold green]Sample configuration created at {output_path}[/bold green]")
        
    except Exception as e:
        console.print(f"[bold red]Error creating sample configuration: {e}[/bold red]")
        logger.exception("Error creating sample configuration")
        raise typer.Exit(1)


def main():
    """Main entry point for the application."""
    try:
        app()
    except Exception as e:
        console.print(f"[bold red]Unexpected error: {e}[/bold red]")
        logger.exception("Unexpected error")
        sys.exit(1)


if __name__ == "__main__":
    main()
