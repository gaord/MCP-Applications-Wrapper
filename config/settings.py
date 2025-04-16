from enum import Enum
from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field, model_validator


class InterpreterType(str, Enum):
    PYTHON = "python"
    NODE = "node"
    CUSTOM = "custom"


class DeploymentMode(str, Enum):
    LOCAL = "local"
    DOCKER = "docker"
    REMOTE = "remote"


class ApplicationConfig(BaseModel):
    """Configuration for a single application."""
    name: str
    description: Optional[str] = None
    working_directory: str
    interpreter_type: InterpreterType
    interpreter_path: Optional[str] = None  # If None, use system default
    command: str
    args: Optional[List[str]] = None
    env_vars: Optional[Dict[str, str]] = None
    resources_limit: Optional[Dict[str, str]] = None  # CPU, memory limits
    timeout: Optional[int] = None  # Timeout in seconds for application execution
    
    @model_validator(mode='after')
    def validate_custom_interpreter(self):
        """Ensure custom interpreter has a path."""
        if self.interpreter_type == InterpreterType.CUSTOM and not self.interpreter_path:
            raise ValueError("Custom interpreter type requires interpreter_path")
        return self


class DockerConfig(BaseModel):
    """Docker-specific configuration."""
    base_image: str = Field(default="python:3.11-slim")
    network: Optional[str] = None
    volumes: Optional[Dict[str, str]] = None  # host_path: container_path
    additional_args: Optional[List[str]] = None


class RemoteConfig(BaseModel):
    """Remote deployment configuration."""
    host: str
    port: int = 22
    username: str
    password: Optional[str] = None
    key_path: Optional[str] = None
    deploy_path: str


class WrapperConfig(BaseModel):
    """Main configuration for the MCP application wrapper."""
    applications: Dict[str, ApplicationConfig]
    deployment_mode: DeploymentMode = DeploymentMode.LOCAL
    docker_config: Optional[DockerConfig] = None
    remote_config: Optional[RemoteConfig] = None
    
    @model_validator(mode='after')
    def validate_config(self):
        """Validate configuration based on deployment mode."""
        if self.deployment_mode == DeploymentMode.DOCKER and not self.docker_config:
            raise ValueError("Docker deployment mode requires docker_config")
        if self.deployment_mode == DeploymentMode.REMOTE and not self.remote_config:
            raise ValueError("Remote deployment mode requires remote_config")
        return self


def load_config(config_path: str) -> WrapperConfig:
    """Load configuration from a YAML or JSON file."""
    import yaml
    import json
    import os
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    if config_path.endswith('.yaml') or config_path.endswith('.yml'):
        with open(config_path, 'r') as file:
            config_data = yaml.safe_load(file)
    elif config_path.endswith('.json'):
        with open(config_path, 'r') as file:
            config_data = json.load(file)
    else:
        raise ValueError("Config file must be YAML or JSON")
    
    return WrapperConfig(**config_data)
