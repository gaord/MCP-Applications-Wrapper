import os
import logging
import tempfile
from typing import Dict, List, Optional, Tuple

import docker
from docker.errors import DockerException, ImageNotFound, BuildError

from config.settings import ApplicationConfig, DockerConfig

logger = logging.getLogger(__name__)


class DockerRunner:
    """Utility for running applications in Docker containers."""
    
    def __init__(self, app_config: ApplicationConfig, docker_config: DockerConfig):
        self.app_config = app_config
        self.docker_config = docker_config
        self.container = None
        self.client = docker.from_env()
        self.container_name = f"mcp-{self.app_config.name.lower().replace(' ', '-')}"
    
    def _create_dockerfile(self) -> str:
        """Create a temporary Dockerfile for the application."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.Dockerfile') as f:
            # Start with the base image
            f.write(f"FROM {self.docker_config.base_image}\n")
            
            # Set working directory
            f.write(f"WORKDIR /app\n")
            
            # Install dependencies based on interpreter type
            if self.app_config.interpreter_type == "python":
                # If a requirements.txt exists in the app's working directory, copy and install it
                requirements_path = os.path.join(self.app_config.working_directory, "requirements.txt")
                if os.path.exists(requirements_path):
                    f.write("COPY requirements.txt .\n")
                    f.write("RUN pip install -r requirements.txt\n")
            elif self.app_config.interpreter_type == "node":
                # If package.json exists in the app's working directory, copy and install dependencies
                package_path = os.path.join(self.app_config.working_directory, "package.json")
                if os.path.exists(package_path):
                    f.write("COPY package*.json .\n")
                    f.write("RUN npm install\n")
            
            # Copy the application to the container
            f.write("COPY . .\n")
            
            # Set environment variables
            if self.app_config.env_vars:
                for key, value in self.app_config.env_vars.items():
                    f.write(f"ENV {key}={value}\n")
            
            # Set the command to run the application
            cmd_parts = []
            
            # Add the interpreter if needed
            if self.app_config.interpreter_type == "python":
                cmd_parts.append("python")
            elif self.app_config.interpreter_type == "node":
                cmd_parts.append("node")
            elif self.app_config.interpreter_path:
                cmd_parts.append(self.app_config.interpreter_path)
            
            # Add the main command
            cmd_parts.append(self.app_config.command)
            
            # Add arguments if any
            if self.app_config.args:
                cmd_parts.extend(self.app_config.args)
            
            # Format the command for the Dockerfile
            cmd_str = ', '.join([f'"{part}"' for part in cmd_parts])
            f.write(f"CMD [{cmd_str}]\n")
            
            return f.name
    
    def build_image(self) -> str:
        """Build a Docker image for the application."""
        try:
            # Create a Dockerfile
            dockerfile_path = self._create_dockerfile()
            
            # Image name
            image_name = f"mcp-app-{self.app_config.name.lower().replace(' ', '-')}"
            
            logger.info(f"Building Docker image for {self.app_config.name}")
            
            # Build the image
            image, logs = self.client.images.build(
                path=self.app_config.working_directory,
                dockerfile=dockerfile_path,
                tag=image_name,
                rm=True  # Remove intermediate containers
            )
            
            # Clean up the temporary Dockerfile
            try:
                os.unlink(dockerfile_path)
            except:
                pass
            
            logger.info(f"Docker image {image_name} built successfully")
            return image_name
            
        except (DockerException, BuildError) as e:
            logger.error(f"Error building Docker image: {e}")
            raise
    
    def run(self) -> str:
        """Run the application in a Docker container."""
        try:
            # Build the image if needed
            image_name = self.build_image()
            
            # Prepare container configuration
            container_config = {
                "image": image_name,
                "name": self.container_name,
                "detach": True,  # Run in the background
            }
            
            # Add network configuration if specified
            if self.docker_config.network:
                container_config["network"] = self.docker_config.network
            
            # Add volume mounts if specified
            if self.docker_config.volumes:
                volumes = {}
                for host_path, container_path in self.docker_config.volumes.items():
                    volumes[host_path] = {"bind": container_path, "mode": "rw"}
                container_config["volumes"] = volumes
            
            # Add resource limits if specified
            if self.app_config.resources_limit:
                container_config["mem_limit"] = self.app_config.resources_limit.get("memory")
                container_config["cpu_quota"] = int(float(self.app_config.resources_limit.get("cpu", 1)) * 100000)
                container_config["cpu_period"] = 100000
            
            # Add environment variables
            if self.app_config.env_vars:
                container_config["environment"] = self.app_config.env_vars
            
            # Run the container
            logger.info(f"Starting Docker container for {self.app_config.name}")
            self.container = self.client.containers.run(**container_config)
            
            logger.info(f"Docker container {self.container_name} started with ID: {self.container.id}")
            return self.container.id
            
        except (DockerException, ImageNotFound) as e:
            logger.error(f"Error running Docker container: {e}")
            raise
    
    def stop(self) -> None:
        """Stop the running Docker container."""
        if not self.container:
            try:
                # Try to find the container by name
                self.container = self.client.containers.get(self.container_name)
            except:
                logger.warning(f"Container {self.container_name} not found")
                return
        
        try:
            logger.info(f"Stopping container {self.container_name}")
            self.container.stop(timeout=10)  # Give it 10 seconds to stop gracefully
            self.container.remove()  # Remove the container
            logger.info(f"Container {self.container_name} stopped and removed")
        except Exception as e:
            logger.error(f"Error stopping container {self.container_name}: {e}")
            # Try to force remove if stopping failed
            try:
                self.container.remove(force=True)
            except:
                pass
        finally:
            self.container = None
    
    def is_running(self) -> bool:
        """Check if the container is running."""
        if not self.container:
            try:
                # Try to find the container by name
                self.container = self.client.containers.get(self.container_name)
            except:
                return False
        
        try:
            self.container.reload()  # Update container data
            return self.container.status == "running"
        except:
            return False
    
    def get_logs(self) -> str:
        """Get the logs from the container."""
        if not self.container:
            try:
                # Try to find the container by name
                self.container = self.client.containers.get(self.container_name)
            except:
                return ""
        
        try:
            return self.container.logs().decode('utf-8')
        except Exception as e:
            logger.error(f"Error getting logs for container {self.container_name}: {e}")
            return ""
