import os
import logging
import subprocess
import traceback
from typing import Dict, List, Optional, Union
import sys

from fastmcp import FastMCP
from pydantic import BaseModel, Field

from config.settings import WrapperConfig, load_config
from utils.process import ApplicationRunner

logger = logging.getLogger(__name__)


class ApplicationStatus(BaseModel):
    """Status of an application."""
    name: str
    available: bool = True  # All applications are available by default
    description: Optional[str] = None


class ApplicationsList(BaseModel):
    """List of applications and their status."""
    applications: List[ApplicationStatus]


class ApplicationExecutionResult(BaseModel):
    """Result of executing an application."""
    stdout: str
    stderr: str
    exit_code: int
    success: bool


class AppConfigManager:
    """Class to manage the MCP server with application configuration."""
    
    def __init__(self, config_path: str):
        try:
            self.config_path = config_path
            logger.info(f"Loading configuration from {config_path}")
            self.config = load_config(config_path)
            
            # 为Python应用设置虚拟环境
            self._setup_python_environments()
            
            # Create the MCP server
            self.mcp = FastMCP("Applications Wrapper")
            
            # Register tools
            self._register_tools()
            logger.info("MCP server initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize AppConfigManager: {e}")
            logger.debug(traceback.format_exc())
            raise
    
    def _setup_python_environments(self):
        """Setup and check virtual environments for each Python application"""
        try:
            logger.info("Setting up Python virtual environments...")
            for app_name, app_config in self.config.applications.items():
                # Only process Python applications
                if app_config.interpreter_type != "python":
                    continue
                
                # Get the absolute path of the working directory
                working_dir = app_config.working_directory
                if not os.path.isabs(working_dir):
                    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    working_dir = os.path.join(root_dir, working_dir)
                
                # Check if the working directory exists
                if not os.path.exists(working_dir):
                    logger.warning(f"Working directory for app {app_name} not found: {working_dir}")
                    continue
                
                # Check if a virtual environment already exists
                venv_found = False
                venv_path = None
                
                for venv_dir in ['venv', '.venv', 'env', '.env']:
                    check_path = os.path.join(working_dir, venv_dir)
                    if os.path.exists(check_path):
                        venv_found = True
                        venv_path = check_path
                        logger.info(f"Found existing Python virtual environment for {app_name}: {venv_path}")
                        break
                
                # If no virtual environment found, create one
                if not venv_found:
                    # Default venv directory name
                    venv_path = os.path.join(working_dir, 'venv')
                    logger.info(f"Creating Python virtual environment for {app_name} at {venv_path}")
                    
                    try:
                        # Use subprocess to create virtual environment
                        subprocess_env = os.environ.copy()
                        cmd = [sys.executable, "-m", "venv", venv_path]
                        logger.debug(f"Running virtual environment creation command: {' '.join(cmd)}")
                        
                        result = subprocess.run(
                            cmd,
                            cwd=working_dir,
                            env=subprocess_env,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                            check=False
                        )
                        
                        if result.returncode == 0:
                            logger.info(f"Successfully created Python virtual environment for {app_name}")
                            venv_found = True
                        else:
                            logger.warning(f"Failed to create virtual environment: {result.stderr}")
                            # Try using Python's built-in venv module
                            try:
                                import venv
                                logger.info("Trying to create venv using built-in venv module")
                                venv.create(venv_path, with_pip=True)
                                logger.info(f"Successfully created Python virtual environment using venv module")
                                venv_found = True
                            except Exception as e:
                                logger.error(f"Failed to create virtual environment with venv module: {e}")
                                logger.debug(traceback.format_exc())
                    except Exception as e:
                        logger.error(f"Error creating virtual environment: {e}")
                        logger.debug(traceback.format_exc())
                    
                    # If virtual environment created successfully, ensure pip is up to date
                    if venv_found:
                        try:
                            # Determine pip path
                            if os.name == 'nt':  # Windows
                                pip_path = os.path.join(venv_path, 'Scripts', 'pip.exe')
                                if not os.path.exists(pip_path):
                                    pip_path = os.path.join(venv_path, 'Scripts', 'pip')
                            else:  # Unix/Linux/macOS
                                pip_path = os.path.join(venv_path, 'bin', 'pip')
                            
                            # Check if pip exists
                            if os.path.exists(pip_path):
                                # Update pip
                                upgrade_cmd = [pip_path, "install", "--upgrade", "pip", "setuptools", "wheel"]
                                logger.debug(f"Upgrading pip with command: {' '.join(upgrade_cmd)}")
                                
                                upgrade_result = subprocess.run(
                                    upgrade_cmd,
                                    cwd=working_dir,
                                    env=os.environ.copy(),
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    text=True,
                                    check=False
                                )
                                
                                if upgrade_result.returncode == 0:
                                    logger.info(f"Successfully upgraded pip for {app_name}")
                                else:
                                    logger.warning(f"Failed to upgrade pip: {upgrade_result.stderr}")
                            else:
                                logger.warning(f"Pip not found in virtual environment: {pip_path}")
                        except Exception as e:
                            logger.error(f"Error upgrading pip: {e}")
                            logger.debug(traceback.format_exc())

                # Check if there's a requirements.txt file
                req_file = os.path.join(working_dir, 'requirements.txt')
                if os.path.exists(req_file):
                    logger.info(f"Found requirements.txt for {app_name}, installing dependencies...")
                    
                    # Determine pip path
                    if os.name == 'nt':  # Windows
                        pip_path = os.path.join(venv_path, 'Scripts', 'pip.exe')
                        if not os.path.exists(pip_path):
                            pip_path = os.path.join(venv_path, 'Scripts', 'pip')
                    else:  # Unix/Linux/macOS
                        pip_path = os.path.join(venv_path, 'bin', 'pip')
                    
                    if not os.path.exists(pip_path):
                        logger.warning(f"Pip not found in virtual environment, can't install requirements: {pip_path}")
                        continue
                    
                    # Clean requirements.txt content
                    try:
                        with open(req_file, 'r') as f:
                            req_content = f.readlines()
                        
                        fixed_lines = []
                        has_issues = False
                        
                        for line in req_content:
                            # Remove trailing whitespace and newlines
                            line = line.strip()
                            if not line or line.startswith('#'):
                                continue
                            
                            # Check and fix common formatting issues
                            if '%' in line:
                                has_issues = True
                                line = line.split('%')[0].strip()
                            
                            if line:
                                fixed_lines.append(line)
                        
                        # If issues found, create a fixed temporary file
                        if has_issues:
                            temp_req_file = os.path.join(working_dir, 'requirements.fixed.txt')
                            with open(temp_req_file, 'w') as f:
                                f.write('\n'.join(fixed_lines))
                            logger.info(f"Created fixed requirements file at {temp_req_file}")
                            install_req_file = temp_req_file
                        else:
                            install_req_file = req_file
                    except Exception as e:
                        logger.error(f"Error processing requirements.txt: {e}")
                        logger.debug(traceback.format_exc())
                        install_req_file = req_file
                    
                    # Install dependencies
                    try:
                        install_cmd = [pip_path, 'install', '-r', install_req_file]
                        logger.debug(f"Installing dependencies with command: {' '.join(install_cmd)}")
                        
                        install_result = subprocess.run(
                            install_cmd,
                            cwd=working_dir,
                            env=os.environ.copy(),
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                            check=False
                        )
                        
                        if install_result.returncode == 0:
                            logger.info(f"Successfully installed dependencies for {app_name}")
                        else:
                            logger.warning(f"Failed to install dependencies: {install_result.stderr}")
                            
                            # Try installing dependencies one by one
                            logger.info("Trying to install packages one by one")
                            for dep in fixed_lines if 'fixed_lines' in locals() else []:
                                if not dep.strip():
                                    continue
                                
                                try:
                                    one_cmd = [pip_path, 'install', dep.strip()]
                                    logger.debug(f"Installing single package: {dep.strip()}")
                                    
                                    one_result = subprocess.run(
                                        one_cmd,
                                        cwd=working_dir,
                                        env=os.environ.copy(),
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        text=True,
                                        check=False
                                    )
                                    
                                    if one_result.returncode == 0:
                                        logger.info(f"Installed {dep.strip()}")
                                    else:
                                        logger.warning(f"Failed to install {dep.strip()}: {one_result.stderr}")
                                except Exception as e:
                                    logger.error(f"Error installing {dep.strip()}: {e}")
                    except Exception as e:
                        logger.error(f"Error installing dependencies: {e}")
                        logger.debug(traceback.format_exc())
                    
                    # Clean up temporary files
                    if 'temp_req_file' in locals() and os.path.exists(temp_req_file):
                        try:
                            os.remove(temp_req_file)
                        except Exception as e:
                            logger.debug(f"Failed to remove temporary file: {e}")
            
            logger.info("Finished setting up Python virtual environments")
        except Exception as e:
            logger.error(f"Error setting up Python environments: {e}")
            logger.debug(traceback.format_exc())
    
    def _register_tools(self):
        """Register all the MCP tools."""
        
        @self.mcp.tool()
        def list_applications() -> ApplicationsList:
            """List all configured applications and their status."""
            try:
                logger.info("Listing applications")
                applications = []
                
                for app_name, app_config in self.config.applications.items():
                    # Check if the application is available - by default all apps are available
                    available = True
                    # If needed, add logic to check if the application is available
                    
                    applications.append(ApplicationStatus(
                        name=app_name,
                        available=available,
                        description=app_config.description
                    ))
                
                result = ApplicationsList(applications=applications)
                logger.debug(f"Returning {len(applications)} applications")
                return result
            except Exception as e:
                logger.error(f"Error listing applications: {e}")
                logger.debug(traceback.format_exc())
                # Return empty list instead of failing
                return ApplicationsList(applications=[])
        
        @self.mcp.tool()
        def get_deployment_mode() -> str:
            """Get the current deployment mode."""
            try:
                logger.info("Getting deployment mode")
                return self.config.deployment_mode.value
            except Exception as e:
                error_msg = f"Error getting deployment mode: {str(e)}"
                logger.error(error_msg)
                logger.debug(traceback.format_exc())
                return "unknown"
        
        @self.mcp.tool()
        def get_application_help(name: str) -> ApplicationExecutionResult:
            """
            Get the command-line help for an application by running it with --help flag.
            
            Args:
                name: Name of the application
                
            Returns:
                The help output from the application
            """
            try:
                logger.info(f"Getting help for application: {name}")
                if name not in self.config.applications:
                    logger.warning(f"Application {name} not found in configuration")
                    result = ApplicationExecutionResult(
                        stdout="",
                        stderr=f"Application {name} not found",
                        exit_code=1,
                        success=False
                    )
                    logger.debug(f"Returning error result: {result}")
                    return result
                
                # Get application config
                app_config = self.config.applications[name]
                
                # Working directory - ensure path is absolute
                working_dir = app_config.working_directory
                if not os.path.isabs(working_dir):
                    # Convert to absolute path relative to current directory
                    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    working_dir = os.path.join(root_dir, working_dir)
                
                # Check if directory exists
                if not os.path.exists(working_dir):
                    error_msg = f"Working directory not found: {working_dir}"
                    logger.error(error_msg)
                    return ApplicationExecutionResult(
                        stdout="",
                        stderr=error_msg,
                        exit_code=1,
                        success=False
                    )
                
                # Create a runner for this application
                runner = ApplicationRunner(app_config)
                
                # Check if there's a Python virtual environment in the working directory
                venv_paths = []
                
                # Standard virtual environment directory names
                for venv_dir in ['venv', '.venv', 'env', '.env']:
                    venv_path = os.path.join(working_dir, venv_dir)
                    if os.path.exists(venv_path):
                        venv_paths.append(venv_path)
                        logger.info(f"Found Python virtual environment: {venv_path}")
                
                # Build the command
                cmd = []
                
                # If virtual environment found, use its Python interpreter
                if venv_paths and app_config.interpreter_type == "python":
                    logger.info(f"Using Python from virtual environment: {venv_paths[0]}")
                    # Check platform to determine correct interpreter path
                    if os.name == 'nt':  # Windows
                        python_exec = os.path.join(venv_paths[0], 'Scripts', 'python.exe')
                    else:  # Unix/Linux/macOS
                        python_exec = os.path.join(venv_paths[0], 'bin', 'python')
                    
                    if os.path.exists(python_exec):
                        cmd.append(python_exec)
                        
                        # Ensure using absolute path to find Python scripts
                        app_script = app_config.command
                        if not os.path.isabs(app_script):
                            app_script = os.path.join(working_dir, app_script)
                            logger.info(f"Using absolute script path: {app_script}")
                        cmd.append(app_script)
                    else:
                        logger.warning(f"Python executable not found in virtual environment: {python_exec}")
                        # Fallback to standard command
                        cmd = runner.build_command()
                else:
                    # Use standard command
                    cmd = runner.build_command()
                
                # Add --help parameter
                cmd.append("--help")
                
                # Execute the command
                try:
                    logger.info(f"Executing help command in directory: {working_dir}")
                    logger.debug(f"Command: {' '.join(cmd)}")
                    
                    # Set current working directory
                    result = subprocess.run(
                        cmd,
                        cwd=working_dir,
                        env=os.environ.copy(),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        check=False
                    )
                    
                    logger.debug(f"Help command result: exit_code={result.returncode}")
                    result_obj = ApplicationExecutionResult(
                        stdout=result.stdout,
                        stderr=result.stderr,
                        exit_code=result.returncode,
                        success=result.returncode == 0
                    )
                    logger.debug(f"Returning result: success={result_obj.success}")
                    return result_obj
                except Exception as e:
                    error_msg = f"Error executing help command: {str(e)}"
                    logger.error(error_msg)
                    logger.debug(traceback.format_exc())
                    return ApplicationExecutionResult(
                        stdout="",
                        stderr=f"Error executing application: {str(e)}",
                        exit_code=1,
                        success=False
                    )
            except Exception as e:
                error_msg = f"Error getting help for application {name}: {str(e)}"
                logger.error(error_msg)
                logger.debug(traceback.format_exc())
                return ApplicationExecutionResult(
                    stdout="",
                    stderr=error_msg,
                    exit_code=1,
                    success=False
                )
        
        @self.mcp.tool()
        def execute_application(name: str, args: List[str] = None) -> ApplicationExecutionResult:
            """
            Execute an application with the provided arguments.
            
            Args:
                name: Name of the application
                args: List of command-line arguments to pass to the application
                
            Returns:
                The execution result including stdout, stderr, and exit code
            """
            try:
                logger.info(f"Executing application: {name} with args: {args}")
                if args is None:
                    args = []
                    
                if name not in self.config.applications:
                    logger.warning(f"Application {name} not found in configuration")
                    return ApplicationExecutionResult(
                        stdout="",
                        stderr=f"Application {name} not found",
                        exit_code=1,
                        success=False
                    )
                
                # Get application config
                app_config = self.config.applications[name]
                
                # Working directory - ensure path is absolute
                working_dir = app_config.working_directory
                if not os.path.isabs(working_dir):
                    # Convert to absolute path relative to current directory
                    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    working_dir = os.path.join(root_dir, working_dir)
                
                # Check if directory exists
                if not os.path.exists(working_dir):
                    error_msg = f"Working directory not found: {working_dir}"
                    logger.error(error_msg)
                    return ApplicationExecutionResult(
                        stdout="",
                        stderr=error_msg,
                        exit_code=1,
                        success=False
                    )
                
                # Check if there's a Python virtual environment in the working directory
                venv_paths = []
                
                # Standard virtual environment directory names
                for venv_dir in ['venv', '.venv', 'env', '.env']:
                    venv_path = os.path.join(working_dir, venv_dir)
                    if os.path.exists(venv_path):
                        venv_paths.append(venv_path)
                        logger.info(f"Found Python virtual environment: {venv_path}")
                
                # Create a runner for this application
                runner = ApplicationRunner(app_config)
                
                # Build the command
                cmd = []
                
                # If virtual environment found, use its Python interpreter
                if venv_paths and app_config.interpreter_type == "python":
                    logger.info(f"Using Python from virtual environment: {venv_paths[0]}")
                    # Check platform to determine correct interpreter path
                    if os.name == 'nt':  # Windows
                        python_exec = os.path.join(venv_paths[0], 'Scripts', 'python.exe')
                    else:  # Unix/Linux/macOS
                        python_exec = os.path.join(venv_paths[0], 'bin', 'python')
                    
                    if os.path.exists(python_exec):
                        cmd.append(python_exec)
                        
                        # Ensure using absolute path to find Python scripts
                        app_script = app_config.command
                        if not os.path.isabs(app_script):
                            app_script = os.path.join(working_dir, app_script)
                            logger.info(f"Using absolute script path: {app_script}")
                        cmd.append(app_script)
                    else:
                        logger.warning(f"Python executable not found in virtual environment: {python_exec}")
                        # Fallback to standard command
                        cmd = runner.build_command()
                else:
                    # Use standard command
                    cmd = runner.build_command()
                
                # Add user parameters
                cmd.extend(args)
                
                # Execute the command
                try:
                    logger.info(f"Executing {name} with args: {args} in directory: {working_dir}")
                    logger.debug(f"Command: {' '.join(cmd)}")
                    
                    # Set environment variables
                    env = os.environ.copy()
                    if app_config.env_vars:
                        env.update(app_config.env_vars)
                        logger.debug(f"Added environment variables: {app_config.env_vars}")
                    
                    # Get application-specific timeout if set
                    timeout_value = app_config.timeout
                    if timeout_value:
                        logger.info(f"Using application-specific timeout of {timeout_value} seconds")
                    else:
                        # Use a longer default timeout to ensure long-running applications have enough time to complete
                        timeout_value = 3600  # 1 hour default timeout
                        logger.info(f"No timeout specified for application, using default timeout of {timeout_value} seconds")
                    
                    # Use subprocess.Popen and asyncio to handle timeout
                    process = subprocess.Popen(
                        cmd,
                        cwd=working_dir,
                        env=env,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    
                    try:
                        # Set timeout
                        stdout, stderr = process.communicate(timeout=timeout_value)
                        exit_code = process.returncode
                        
                        logger.debug(f"Execution result: exit_code={exit_code}")
                        if exit_code != 0:
                            logger.warning(f"Application {name} exited with non-zero code: {exit_code}")
                            logger.debug(f"stderr: {stderr}")
                        
                        result_obj = ApplicationExecutionResult(
                            stdout=stdout,
                            stderr=stderr,
                            exit_code=exit_code,
                            success=exit_code == 0
                        )
                        logger.debug(f"Returning result: success={result_obj.success}")
                        return result_obj
                        
                    except subprocess.TimeoutExpired:
                        # Timeout occurred, terminate process
                        logger.warning(f"Application {name} execution timed out after {timeout_value} seconds")
                        process.kill()
                        
                        # Get output (may be partial output)
                        stdout, stderr = process.communicate()
                        
                        return ApplicationExecutionResult(
                            stdout=stdout,
                            stderr=f"Application execution timed out after {timeout_value} seconds\n{stderr}",
                            exit_code=124,  # Use a standard timeout exit code
                            success=False
                        )
                        
                except Exception as e:
                    error_msg = f"Error executing application command: {str(e)}"
                    logger.error(error_msg)
                    logger.debug(traceback.format_exc())
                    return ApplicationExecutionResult(
                        stdout="",
                        stderr=f"Error executing application: {str(e)}",
                        exit_code=1,
                        success=False
                    )
            except Exception as e:
                error_msg = f"Error executing application {name}: {str(e)}"
                logger.error(error_msg)
                logger.debug(traceback.format_exc())
                return ApplicationExecutionResult(
                    stdout="",
                    stderr=error_msg,
                    exit_code=1,
                    success=False
                )
    
    def run(self, transport: str = "sse", host: str = "0.0.0.0", port: int = 8000):
        """Run the MCP server."""
        try:
            logger.info(f"Starting MCP server with transport {transport} on {host}:{port}")
            
            # If SSE transport, directly call mcp.run_sse_async instead of mcp.run
            if transport == "sse":
                # Use anyio.run to run async function
                import anyio
                anyio.run(self.mcp.run_sse_async, host, port)
            else:
                # For stdio and other transports, use standard run method
                self.mcp.run(transport=transport)
        except KeyboardInterrupt:
            logger.info("MCP server stopped by user")
        except Exception as e:
            logger.error(f"Error running MCP server: {e}")
            logger.debug(traceback.format_exc())


def create_mcp_server(config_path: str) -> FastMCP:
    """Create an MCP server instance from a configuration file."""
    try:
        config_manager = AppConfigManager(config_path)
        return config_manager.mcp
    except Exception as e:
        logger.error(f"Failed to create MCP server: {e}")
        logger.debug(traceback.format_exc())
        raise


def run_mcp_server(config_path: str, host: str = "0.0.0.0", port: int = 8000, transport: str = "sse"):
    """Run an MCP server from a configuration file."""
    try:
        logger.info(f"Starting MCP server on {host}:{port}")
        # Create and run MCP server
        config_manager = AppConfigManager(config_path)
        
        # Run MCP server directly, passing host and port parameters
        config_manager.run(transport=transport, host=host, port=port)
    except Exception as e:
        logger.error(f"Failed to run MCP server: {e}")
        logger.debug(traceback.format_exc())
        raise
