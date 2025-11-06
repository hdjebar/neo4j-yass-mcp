"""
General Utility Functions

Provides utility functions for logging configuration, port management,
and other general-purpose functionality not specific to LLM configuration.
"""

import logging
import os
import socket
from typing import List, Optional


def configure_logging():
    """
    Configure logging based on environment variables.

    Environment variables:
        LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        LOG_FORMAT: Log message format string
    """
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_format = os.getenv(
        "LOG_FORMAT",
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Convert string log level to logging constant
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }

    level = level_map.get(log_level, logging.INFO)

    # Configure root logger
    logging.basicConfig(
        level=level,
        format=log_format,
        force=True  # Override any existing configuration
    )

    return logging.getLogger(__name__)


def is_port_available(host: str, port: int) -> bool:
    """
    Check if a port is available on the given host.

    Args:
        host: Host address to check (e.g., "127.0.0.1", "0.0.0.0")
        port: Port number to check

    Returns:
        True if port is available, False otherwise
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((host, port))
            return True
    except OSError:
        return False


def find_available_port(host: str, preferred_ports: List[int], fallback_range: tuple = (8000, 9000)) -> Optional[int]:
    """
    Find an available port from a list of preferred ports or a fallback range.

    Args:
        host: Host address (e.g., "127.0.0.1", "0.0.0.0")
        preferred_ports: List of preferred port numbers to try first
        fallback_range: Tuple of (start, end) for fallback port range

    Returns:
        Available port number, or None if no port is available

    Example:
        >>> port = find_available_port("127.0.0.1", [8000, 8001, 8002])
        >>> if port:
        ...     print(f"Using port {port}")
    """
    logger = logging.getLogger(__name__)

    # Try preferred ports first
    for port in preferred_ports:
        if is_port_available(host, port):
            logger.info(f"Port {port} is available (preferred)")
            return port
        else:
            logger.debug(f"Port {port} is already in use")

    # Fall back to scanning a range
    logger.warning(f"All preferred ports are in use. Scanning range {fallback_range[0]}-{fallback_range[1]}")
    for port in range(fallback_range[0], fallback_range[1]):
        if is_port_available(host, port):
            logger.info(f"Port {port} is available (fallback)")
            return port

    logger.error(f"No available ports found in range {fallback_range[0]}-{fallback_range[1]}")
    return None


def get_preferred_ports_from_env(env_var: str = "PREFERRED_PORTS_MCP", default: str = "8000 8001 8002") -> List[int]:
    """
    Parse preferred ports from environment variable.

    Args:
        env_var: Environment variable name
        default: Default port list as space-separated string

    Returns:
        List of port numbers

    Example:
        >>> # With PREFERRED_PORTS_MCP="8000 8001 8002"
        >>> ports = get_preferred_ports_from_env()
        >>> print(ports)  # [8000, 8001, 8002]
    """
    ports_str = os.getenv(env_var, default)
    try:
        return [int(p.strip()) for p in ports_str.split() if p.strip().isdigit()]
    except ValueError:
        logging.getLogger(__name__).warning(f"Invalid port configuration in {env_var}, using defaults")
        return [int(p.strip()) for p in default.split() if p.strip().isdigit()]
