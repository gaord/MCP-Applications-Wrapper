"""
Configuration utilities for the MCP Applications Wrapper.
"""

import os
import yaml
from typing import Dict, List, Optional, Any, Union

from config.settings import WrapperConfig, load_config
from dataclasses import dataclass


@dataclass
class AppConfig:
    """
    Application configuration class that wraps the WrapperConfig.
    """
    wrapper_config: WrapperConfig
    
    @classmethod
    def from_yaml(cls, config_path: str) -> 'AppConfig':
        """
        Load configuration from a YAML file.
        
        Args:
            config_path: Path to the YAML configuration file
            
        Returns:
            AppConfig instance
        """
        # Use the existing load_config function from config.settings
        wrapper_config = load_config(config_path)
        return cls(wrapper_config=wrapper_config)
    
    @property
    def applications(self) -> Dict[str, Any]:
        """
        Get the applications configuration.
        
        Returns:
            Dictionary of application configurations
        """
        return self.wrapper_config.applications
    
    @property
    def deployment_mode(self) -> str:
        """
        Get the deployment mode.
        
        Returns:
            Deployment mode as a string
        """
        return self.wrapper_config.deployment_mode.value
    
    def get_app_config(self, app_name: str) -> Any:
        """
        Get the configuration for a specific application.
        
        Args:
            app_name: Name of the application
            
        Returns:
            Application configuration or None if not found
        """
        return self.applications.get(app_name) 