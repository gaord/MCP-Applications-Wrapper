# MCP Applications Wrapper

An MCP (Model Context Protocol) server wrapper for various applications, built with FastMCP. This tool allows you to wrap Python, Node.js, and custom applications with an MCP interface, making them accessible to AI assistants like Claude.

## Features

- Run Python and Node.js applications through an MCP server
- Manage multiple applications with a centralized configuration
- Support for different deployment modes:
  - Local (subprocess) [Experimental - in progress]
  - Docker (containerized) [Experimental - in progress]
  - Remote (SSE deployment)
- Automatic virtual environment setup for Python applications
- Installation of dependencies from requirements.txt
- Command-line interface for creating, validating, and running configurations
- Rich logging with detailed output

## Installation

### Prerequisites

- Python 3.10+
- Docker (for Docker deployment mode)
- SSH access (for remote deployment mode)

### Setup

1. Clone the repository:

```bash
git clone https://github.com/gaord/MCP-Applications-Wrapper.git
cd MCP-Applications-Wrapper
```

2. Create a virtual environment and install dependencies:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Configuration

Create a configuration file (YAML or JSON) to define your applications:

```bash
python main.py create-config config.yaml
```

This will create a sample configuration file that you can modify.

Each application is configured with the following properties:

- `name`: The display name of the application
- `description`: A description of what the application does
- `working_directory`: The directory where the application is located
- `interpreter_type`: The type of interpreter (`python`, `node`, or `custom`)
- `interpreter_path`: (Optional) Path to the interpreter executable
- `command`: The command to execute
- `args`: (Optional) Default arguments for the application
- `env_vars`: (Optional) Environment variables to set
- `resources_limit`: (Optional) CPU and memory limits
- `timeout`: (Optional) Timeout in seconds for application execution

Example configuration:

```yaml
applications:
  echo_app:
    name: Echo Service
    description: Simple service that echoes back the input
    working_directory: /path/to/echo_app
    interpreter_type: python
    command: echo.py
    timeout: 120  # 2 minutes timeout

  hello_app:
    name: Hello World
    description: A simple hello world application
    working_directory: examples/hello_app
    interpreter_type: node
    command: hello.js
    timeout: 60  # 1 minute timeout

deployment_mode: local

# Docker configuration (for deployment_mode: docker)
docker_config:
  base_image: python:3.11-slim
  network: bridge
  volumes:
    /host/path: /container/path

# Remote configuration (for deployment_mode: remote)
# remote_config:
#   host: example.com
#   port: 22
#   username: user
#   password: pass
#   # Or use key authentication
#   # key_path: /path/to/private/key
#   deploy_path: /remote/path
```

### Configuration Parameters

#### Application Configuration

- `name`: Display name for the application
- `description`: Optional description
- `working_directory`: Directory where the application is located
- `interpreter_type`: Type of interpreter (`python`, `node`, or `custom`)
- `interpreter_path`: Path to interpreter (required for `custom` type, optional for others)
- `command`: The main script or command to run
- `args`: Optional list of arguments to pass to the command
- `env_vars`: Optional environment variables
- `resources_limit`: Optional resource limits (for Docker deployment)
- `timeout`: Optional timeout in seconds for application execution

#### Deployment Modes

- `local`: Run applications as subprocesses on the local machine (Note: This mode is experimental and has not been thoroughly tested)
- `docker`: Run applications in Docker containers (Note: This mode is experimental and has not been thoroughly tested)
- `remote`: Deploy and run applications on a remote server via SSE

## Usage

### Validate Configuration

Before running the server, you can validate your configuration:

```bash
python main.py validate config.yaml
```

### Run the Server

Start the MCP server:

```bash
python main.py run config.yaml
```

modify the existing config.yaml to your needs with additional options customization:

```bash
python main.py run examples/config.yaml --transport sse --log-level DEBUG --port 8001
```
then you can access the server via the following url:

```bash
http://localhost:8001/sse
```
> Note: FastMCP automatically runs on port 8000 by default.

### MCP Tools

The following MCP tools are available through the server:

- `list_applications`: List all configured applications and their status
- `get_deployment_mode`: Get the current deployment mode
- `get_application_help`: Get help information for an application with --help argument
- `execute_application`: Execute an application with optional arguments

## Docker Deployment(in progress)

To use Docker deployment mode (Note: Currently experimental and in progress):

1. Set `deployment_mode: docker` in your configuration file
2. Configure the `docker_config` section with appropriate settings
3. Ensure Docker is installed and running on your system

The system will automatically:
- Build containers for your applications
- Mount volumes as specified in the configuration
- Set up networking according to your settings

## Remote Deployment

To use remote deployment mode:

1. Set `deployment_mode: remote` in your configuration file
2. Configure the `remote_config` section with SSE connection details
3. Ensure you have network access to the remote server

The system will:
- Connect to the remote server via SSE
- Execute applications on the remote machine
- Stream results back to the client

## Development

### Adding New Interpreter Types

To add support for a new interpreter type:

1. Update `InterpreterType` enum in `config/settings.py`
2. Modify the `ApplicationRunner` class to handle the new type appropriately

### Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [FastMCP](https://github.com/jlowin/fastmcp) - The fast, Pythonic way to build MCP servers and clients
