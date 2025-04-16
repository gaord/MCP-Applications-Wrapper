#!/usr/bin/env python3
import asyncio
import sys
import logging
import argparse
from typing import Dict, List, Optional
import json
import datetime

# Import our custom client with improved timeout handling
import sys
import os
# Add the parent directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.long_timeout_client import LongTimeoutClient

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def get_server_tools(client, text, is_chinese, timeout):
    """Get server tools list"""
    try:
        print(f"\n{text['tools_list']}:")
        try:
            # Get tools list
            tools = await client.list_tools()
            
            # Display tools list
            if not tools:
                print(text["no_tools"])
            else:
                print(f"Found {len(tools)} tools\n")
                
                for i, tool in enumerate(tools):
                    if hasattr(tool, 'name'):
                        # Standard tool object
                        tool_name = tool.name
                        tool_desc = getattr(tool, 'description', '')
                        print(f"{i+1}. {text['tool_name']}: \033[1;36m{tool_name}\033[0m")
                        
                        if tool_desc:
                            # Handle multi-line descriptions
                            desc_lines = tool_desc.strip().split("\n")
                            if len(desc_lines) == 1:
                                print(f"   {text['tool_description']}: {tool_desc}")
                            else:
                                print(f"   {text['tool_description']}:")
                                for line in desc_lines:
                                    print(f"     {line}")
                        
                        # Display parameters
                        if hasattr(tool, 'parameters') and tool.parameters:
                            params = tool.parameters
                            print(f"   {text['tool_parameters']}:")
                            
                            # Try to parse parameters
                            try:
                                if isinstance(params, dict) and 'properties' in params:
                                    required_params = params.get('required', [])
                                    
                                    for param_name, param_info in params['properties'].items():
                                        param_type = param_info.get('type', 'unknown')
                                        param_desc = param_info.get('description', '')
                                        
                                        # Mark required parameters
                                        is_required = param_name in required_params
                                        required_mark = "\033[1;31m*\033[0m " if is_required else "  "
                                        
                                        print(f"     {required_mark}{param_name} \033[0;33m({param_type})\033[0m: {param_desc}")
                            except Exception as e:
                                logger.warning(f"Failed to parse parameters for tool {tool_name}: {e}")
                                print(f"     Raw parameters: {params}")
                    elif isinstance(tool, dict):
                        # Dictionary form of tool
                        tool_name = tool.get('name', 'Unknown')
                        tool_desc = tool.get('description', '')
                        print(f"{i+1}. {text['tool_name']}: \033[1;36m{tool_name}\033[0m")
                        
                        if tool_desc:
                            # Handle multi-line descriptions
                            desc_lines = tool_desc.strip().split("\n")
                            if len(desc_lines) == 1:
                                print(f"   {text['tool_description']}: {tool_desc}")
                            else:
                                print(f"   {text['tool_description']}:")
                                for line in desc_lines:
                                    print(f"     {line}")
                        
                        # Display parameters
                        if 'parameters' in tool:
                            params = tool['parameters']
                            print(f"   {text['tool_parameters']}:")
                            
                            if isinstance(params, dict) and 'properties' in params:
                                required_params = params.get('required', [])
                                
                                for param_name, param_info in params['properties'].items():
                                    param_type = param_info.get('type', 'unknown')
                                    param_desc = param_info.get('description', '')
                                    
                                    # Mark required parameters
                                    is_required = param_name in required_params
                                    required_mark = "\033[1;31m*\033[0m " if is_required else "  "
                                    
                                    print(f"     {required_mark}{param_name} \033[0;33m({param_type})\033[0m: {param_desc}")
                    else:
                        print(f"{i+1}. {tool}")
                    
                    # If not the last tool, add a separator
                    if i < len(tools) - 1:
                        print("\n" + "-" * 50 + "\n")
        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
            if 'tools' in locals():
                logger.debug(f"Tools result type: {type(tools)}")
    except Exception as e:
        logger.error(f"Failed to get tools list: {e}")

async def get_deployment_mode(client, text, timeout):
    """Get deployment mode"""
    try:
        deployment_mode = await asyncio.wait_for(client.call_tool("get_deployment_mode"), timeout=timeout)
        print(f"\n{text['deployment_mode']}: {deployment_mode}")
        return deployment_mode
    except asyncio.TimeoutError:
        logger.error("Timeout getting deployment mode")
        print("Operation timed out")
        return None

async def list_applications(client, text, timeout):
    """List applications"""
    try:
        apps = await asyncio.wait_for(client.call_tool("list_applications"), timeout=timeout)
        print(f"\n{text['app_list']}:")
        
        # Ensure proper handling of return results
        if hasattr(apps, "__root__"):
            # Correct Pydantic model result
            for app in apps.__root__:
                app_available = getattr(app, 'available', getattr(app, 'running', False))
                print(f"- {app.name}: {text['running'] if app_available else text['not_running']}")
        elif isinstance(apps, dict):
            # Dictionary form of result
            for app_name, app in apps.items():
                app_available = app.get('available', app.get('running', False))  # Support both attribute names
                print(f"- {app_name}: {text['running'] if app_available else text['not_running']}")
        elif isinstance(apps, list):
            # List form of result
            for app in apps:
                if isinstance(app, dict):
                    app_name = app.get('name', 'Unknown')
                    app_available = app.get('available', app.get('running', False))
                    print(f"- {app_name}: {text['running'] if app_available else text['not_running']}")
                else:
                    print(f"- {app}")
        else:
            # Other cases
            print(f"Unexpected result type: {type(apps)}")
            print(f"Result: {apps}")
        
        return apps
    except asyncio.TimeoutError:
        logger.error("Timeout listing applications")
        print("Operation timed out")
        return None

async def get_application_help(client, text, app_name, timeout):
    """Get application help information"""
    try:
        print(f"\n{text['help_info'].format(app_name)}:")
        help_result = await asyncio.wait_for(client.call_tool("get_application_help", {"name": app_name}), timeout=timeout)
        
        # Handle different types of responses
        if hasattr(help_result, 'stdout'):
            # Standard object response
            if help_result.success:
                print(f"{text['help_success']}:")
                print(help_result.stdout)
            else:
                print(f"{text['help_failed']}: {help_result.stderr}")
        elif isinstance(help_result, dict):
            # Dictionary response
            if help_result.get('success', False):
                print(f"{text['help_success']}:")
                print(help_result.get('stdout', ''))
            else:
                print(f"{text['help_failed']}: {help_result.get('stderr', '')}")
        elif isinstance(help_result, list):
            # List response (usually a list of text content)
            logger.warning("Received list instead of ApplicationExecutionResult object")
            
            # Try to extract JSON from the list
            if len(help_result) > 0:
                first_item = help_result[0]
                if hasattr(first_item, 'text'):
                    # Try to parse text as JSON
                    try:
                        json_data = json.loads(first_item.text)
                        if isinstance(json_data, dict):
                            if json_data.get('success', False):
                                print(f"{text['help_success']}:")
                                print(json_data.get('stdout', ''))
                            else:
                                print(f"{text['help_failed']}: {json_data.get('stderr', '')}")
                        else:
                            print(f"Raw result: {json_data}")
                    except json.JSONDecodeError:
                        print(f"Raw text: {first_item.text}")
                else:
                    print(f"Raw result: {help_result}")
            else:
                print(f"Empty list result")
        else:
            # Other type responses
            print(f"Unexpected result type: {type(help_result)}")
            print(f"Result: {help_result}")
    except asyncio.TimeoutError:
        logger.error(f"Timeout getting help for {app_name}")
        print("Operation timed out")
    except Exception as e:
        logger.error(f"Failed to get help for '{app_name}': {e}")

async def execute_application(client, text, app_name, args, timeout):
    """Execute application"""
    try:
        # Directly use client.call_tool, without extra asyncio.wait_for wrapping
        # LongTimeoutClient already has timeout handling
        print(f"\n{text['exec_app'].format(app_name)}:")
        exec_result = await client.call_tool("execute_application", {"name": app_name, "args": args})
        
        # Handle different types of responses
        if hasattr(exec_result, 'stdout'):
            # Standard object response
            if exec_result.success:
                print(f"{text['exec_result']}:")
                print(exec_result.stdout)
            else:
                print(f"{text['exec_failed']}: {exec_result.stderr}")
        elif isinstance(exec_result, dict):
            # Dictionary response
            if exec_result.get('success', False):
                print(f"{text['exec_result']}:")
                print(exec_result.get('stdout', ''))
            else:
                print(f"{text['exec_failed']}: {exec_result.get('stderr', '')}")
        elif isinstance(exec_result, list):
            # List response (usually a list of text content)
            logger.warning("Received list instead of ApplicationExecutionResult object")
            
            # Try to extract JSON from the list
            if len(exec_result) > 0:
                first_item = exec_result[0]
                if hasattr(first_item, 'text'):
                    # Try to parse text as JSON
                    try:
                        json_data = json.loads(first_item.text)
                        if isinstance(json_data, dict):
                            if json_data.get('success', False):
                                print(f"{text['exec_result']}:")
                                print(json_data.get('stdout', ''))
                            else:
                                print(f"{text['exec_failed']}: {json_data.get('stderr', '')}")
                        else:
                            print(f"Raw result: {json_data}")
                    except json.JSONDecodeError:
                        print(f"Raw text: {first_item.text}")
                else:
                    print(f"Raw result: {exec_result}")
            else:
                print(f"Empty list result")
        else:
            # Other type responses
            print(f"Unexpected result type: {type(exec_result)}")
            print(f"Result: {exec_result}")
    except asyncio.TimeoutError:
        logger.error(f"Execution of {app_name} application timed out")
        print("Operation timed out")
    except Exception as e:
        logger.error(f"Failed to execute '{app_name}': {e}")

async def test_mcp_client(server_url: str = "http://localhost:8000/sse", language: str = "en", timeout: int = 1800):
    """Test MCP client connection and API functionality.
    
    Args:
        server_url: URL of the MCP server
        language: Output language, 'zh' for Chinese, 'en' for English
        timeout: Operation timeout in seconds
    """
    # Set language
    is_chinese = language.lower() == "zh"
    
    # Language-related text
    text = {
        "connecting": "Connecting to MCP server...",
        "deployment_mode": "Deployment mode",
        "app_list": "Application list",
        "running": "available",
        "not_running": "not available",
        "help_info": "Getting help information for {}",
        "help_success": "Help information",
        "help_failed": "Failed to get help",
        "exec_app": "Executing {} application",
        "exec_result": "Execution result",
        "exec_failed": "Execution failed",
        "connection_error": "Error connecting to server",
        "tools_list": "MCP Server Tools List",
        "tool_name": "Tool Name",
        "tool_description": "Description",
        "tool_parameters": "Parameters",
        "no_tools": "No tools found"
    }
    
    print(text["connecting"])
    print(f"Connection timeout: {timeout} seconds")
    
    # Use our custom client with better timeout handling
    client = LongTimeoutClient(server_url, timeout_seconds=timeout)
    
    try:
        # Use async context manager as required by FastMCP client
        async with client:
            # 1. Get server tools list
            await get_server_tools(client, text, is_chinese, timeout)
            
            # 2. Get deployment mode
            await get_deployment_mode(client, text, timeout)
            
            # 3. List applications
            apps = await list_applications(client, text, timeout)
            
            # 4. Get invoice_app help information
            await get_application_help(client, text, "hello_app", timeout)
            
            # 5. Execute invoice_app
            await execute_application(client, text, "hello_app", [
                "-n", "hello Ben!",
                "-l", "cn",
                "-r", "3"
            ], timeout)
        
    except Exception as e:
        logger.error(f"{text['connection_error']}: {e}")
        print(f"{text['connection_error']}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test MCP client with SSE transport")
    parser.add_argument("--url", default="http://localhost:8000/sse", help="MCP server URL")
    parser.add_argument("--language", "-l", default="en", choices=["en", "zh"], help="Output language")
    parser.add_argument("--timeout", "-t", type=int, default=1800, help="Operation timeout in seconds")
    
    args = parser.parse_args()
    
    asyncio.run(test_mcp_client(args.url, args.language, args.timeout))