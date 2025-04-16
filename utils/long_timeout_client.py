import datetime
import logging
from typing import Dict, List, Optional, Any

# Import the official FastMCP client
from fastmcp.client.client import Client as FastMCPClient
from fastmcp.client.transports import SSETransport, infer_transport

logger = logging.getLogger(__name__)

class LongTimeoutClient(FastMCPClient):
    """A FastMCP client with improved timeout handling for long-running operations."""
    
    def __init__(
        self,
        url: str,
        timeout_seconds: int = 1800,  # 30 minutes default timeout
        **kwargs
    ):
        """Initialize the client with improved timeout handling.
        
        Args:
            url: URL of the MCP server
            timeout_seconds: Timeout in seconds for read operations
            **kwargs: Additional arguments to pass to FastMCPClient
        """
        # Convert seconds to timedelta for read_timeout_seconds
        read_timeout = datetime.timedelta(seconds=timeout_seconds)
        
        # Add custom headers with longer timeout for SSE
        transport = infer_transport(url)
        if isinstance(transport, SSETransport):
            # Customize the SSE transport to use longer timeouts
            # This requires patching the SSE transport implementation
            logger.info(f"Using longer timeout for SSE connection: {timeout_seconds} seconds")
            
            # Create a patched version of connect_session on SSETransport
            original_connect_session = transport.connect_session
            
            # We can't set the sse_read_timeout directly, so we'll use headers
            # Some servers may honor custom timeout headers
            if not transport.headers:
                transport.headers = {}
            transport.headers["X-MCP-Timeout"] = str(timeout_seconds)
        
        # Initialize with read_timeout_seconds
        super().__init__(
            transport,
            read_timeout_seconds=read_timeout,
            **kwargs
        )
        
        logger.info(f"Initialized LongTimeoutClient with read_timeout_seconds={timeout_seconds}s") 