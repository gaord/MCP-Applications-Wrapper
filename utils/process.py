import os
import subprocess
import sys
from typing import Dict, List, Optional, Tuple, Union
import logging

from config.settings import ApplicationConfig, InterpreterType

logger = logging.getLogger(__name__)


class ApplicationRunner:
    """Utility for running applications as subprocesses."""
    
    def __init__(self, app_config: ApplicationConfig):
        self.config = app_config
        self.process = None
        
    def get_interpreter_command(self) -> str:
        """Get the interpreter command based on the configuration."""
        if self.config.interpreter_path:
            return self.config.interpreter_path
        
        if self.config.interpreter_type == InterpreterType.PYTHON:
            return sys.executable  # Use the current Python interpreter
        elif self.config.interpreter_type == InterpreterType.NODE:
            return "node"  # Assume node is in the PATH
        else:
            raise ValueError(f"Unsupported interpreter type: {self.config.interpreter_type}")
    
    def build_command(self) -> List[str]:
        """Build the command to run the application."""
        cmd = []
        
        # Add the interpreter if needed
        if self.config.interpreter_type != InterpreterType.CUSTOM:
            cmd.append(self.get_interpreter_command())
        
        # Add the main command
        cmd.append(self.config.command)
        
        # Add arguments if any
        if self.config.args:
            cmd.extend(self.config.args)
            
        return cmd
    
    def run(self) -> subprocess.Popen:
        """Run the application as a subprocess."""
        cmd = self.build_command()
        env = os.environ.copy()
        
        # Add environment variables if specified
        if self.config.env_vars:
            env.update(self.config.env_vars)
        
        logger.info(f"Starting application {self.config.name} with command: {' '.join(cmd)}")
        
        self.process = subprocess.Popen(
            cmd,
            cwd=self.config.working_directory,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1  # Line buffered
        )
        
        return self.process
    
    def stop(self) -> Optional[Tuple[str, str]]:
        """Stop the running application."""
        if not self.process:
            logger.warning(f"Application {self.config.name} is not running")
            return None
        
        logger.info(f"Stopping application {self.config.name}")
        
        try:
            # Try to terminate gracefully first
            self.process.terminate()
            try:
                # Wait for up to 5 seconds for the process to terminate
                stdout, stderr = self.process.communicate(timeout=5)
                return stdout, stderr
            except subprocess.TimeoutExpired:
                # If it doesn't terminate in time, kill it
                logger.warning(f"Application {self.config.name} did not terminate gracefully, killing it")
                self.process.kill()
                stdout, stderr = self.process.communicate()
                return stdout, stderr
        except Exception as e:
            logger.error(f"Error stopping application {self.config.name}: {e}")
            # Ensure the process is killed in case of an error
            try:
                self.process.kill()
            except:
                pass
            return None
        finally:
            self.process = None
    
    def is_running(self) -> bool:
        """Check if the application is running."""
        if not self.process:
            return False
        
        return self.process.poll() is None
    
    def get_output(self) -> Tuple[str, str]:
        """Get the current output from stdout and stderr."""
        if not self.process:
            return "", ""
        
        # Get output without blocking, might not be complete
        stdout_data = ""
        stderr_data = ""
        
        # Read from stdout if available
        if self.process.stdout and self.process.stdout.readable():
            try:
                while True:
                    line = self.process.stdout.readline()
                    if not line:
                        break
                    stdout_data += line
            except:
                pass
        
        # Read from stderr if available
        if self.process.stderr and self.process.stderr.readable():
            try:
                while True:
                    line = self.process.stderr.readline()
                    if not line:
                        break
                    stderr_data += line
            except:
                pass
        
        return stdout_data, stderr_data
