"""
Utility module for the File Management System.

This module provides common helper functions used across the application,
including path validation, file size formatting, filename sanitization,
and logging setup.
"""

import os
import re
import logging
from pathlib import Path
from typing import Optional


def validate_path(path: str) -> bool:
    """
    Validate that a directory path exists and is accessible.
    
    This function checks if the provided path exists, is a directory,
    and has read permissions. It prevents path traversal attacks and
    ensures the path is safe to use for file operations.
    
    Args:
        path: The directory path to validate
        
    Returns:
        bool: True if the path is valid and accessible, False otherwise
        
    Examples:
        >>> validate_path("/home/user/documents")
        True
        >>> validate_path("/nonexistent/path")
        False
    """
    if not path or not isinstance(path, str):
        return False
    
    # Strip whitespace and quotes
    path = path.strip().strip('"').strip("'")
    
    if not path:
        return False
    
    try:
        # Convert to Path object for safer handling
        path_obj = Path(path).expanduser().resolve()
        
        # Check if path exists and is a directory
        if not path_obj.exists():
            return False
        
        if not path_obj.is_dir():
            return False
        
        # Check if we have read access
        if not os.access(str(path_obj), os.R_OK):
            return False
        
        return True
    
    except (OSError, ValueError, RuntimeError, PermissionError) as e:
        # Handle any path-related errors
        return False


def format_file_size(bytes: int) -> str:
    """
    Convert bytes to human-readable format (KB, MB, GB, TB).
    
    This function takes a file size in bytes and converts it to a
    human-readable string with appropriate units.
    
    Args:
        bytes: File size in bytes
        
    Returns:
        str: Formatted file size string (e.g., "1.5 MB", "500 KB")
        
    Examples:
        >>> format_file_size(1024)
        '1.0 KB'
        >>> format_file_size(1048576)
        '1.0 MB'
        >>> format_file_size(500)
        '500 B'
    """
    if not isinstance(bytes, (int, float)) or bytes < 0:
        return "0 B"
    
    # Define size units
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    size = float(bytes)
    unit_index = 0
    
    # Convert to appropriate unit
    while size >= 1024.0 and unit_index < len(units) - 1:
        size /= 1024.0
        unit_index += 1
    
    # Format with appropriate precision
    if unit_index == 0:  # Bytes - no decimal places
        return f"{int(size)} {units[unit_index]}"
    else:
        return f"{size:.1f} {units[unit_index]}"


def sanitize_filename(name: str) -> str:
    """
    Remove special characters and replace spaces with underscores.
    
    This function cleans a filename by removing or replacing characters
    that could cause issues in file systems. It preserves alphanumeric
    characters, underscores, hyphens, and periods.
    
    Args:
        name: The filename to sanitize
        
    Returns:
        str: Sanitized filename safe for use in file systems
        
    Examples:
        >>> sanitize_filename("My File (2023).txt")
        'My_File_2023.txt'
        >>> sanitize_filename("hello@world#test.pdf")
        'helloworld_test.pdf'
    """
    if not name or not isinstance(name, str):
        return "unnamed"
    
    # Replace spaces with underscores
    name = name.replace(' ', '_')
    
    # Remove or replace special characters
    # Keep only alphanumeric, underscores, hyphens, and periods
    name = re.sub(r'[^\w\-.]', '', name)
    
    # Remove multiple consecutive underscores
    name = re.sub(r'_+', '_', name)
    
    # Remove leading/trailing underscores and periods
    name = name.strip('_.')
    
    # If the name is empty after sanitization, return a default
    if not name:
        return "unnamed"
    
    return name


def setup_logging(log_file: str = "logs/file_management.log", 
                  level: int = logging.INFO) -> logging.Logger:
    """
    Set up logging configuration for operation tracking.
    
    This function configures the logging system to write to both
    a file and the console, with timestamps and appropriate formatting.
    
    Args:
        log_file: Path to the log file (default: "logs/file_management.log")
        level: Logging level (default: logging.INFO)
        
    Returns:
        logging.Logger: Configured logger instance
        
    Examples:
        >>> logger = setup_logging()
        >>> logger.info("Operation started")
    """
    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    # Create logger
    logger = logging.getLogger('file_management_system')
    logger.setLevel(level)
    
    # Avoid adding duplicate handlers
    if logger.handlers:
        return logger
    
    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_formatter = logging.Formatter(
        '%(levelname)s - %(message)s'
    )
    
    # File handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(level)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)  # Only warnings and errors to console
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    return logger


def log_operation(operation: str, details: dict, logger: Optional[logging.Logger] = None) -> None:
    """
    Log file operations for debugging and tracking.
    
    This is a convenience function that logs operation details in a
    structured format.
    
    Args:
        operation: Type of operation (e.g., "organize", "rename", "duplicate_scan")
        details: Dictionary containing operation details
        logger: Logger instance (if None, uses default logger)
        
    Examples:
        >>> log_operation("organize", {"files_processed": 10, "errors": 0})
    """
    if logger is None:
        logger = logging.getLogger('file_management_system')
    
    log_message = f"Operation: {operation}"
    if details:
        detail_str = ", ".join([f"{k}={v}" for k, v in details.items()])
        log_message += f" | {detail_str}"
    
    logger.info(log_message)
