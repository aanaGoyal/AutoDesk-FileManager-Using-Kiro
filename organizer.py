"""
File organizer module for the File Management System.

This module handles automatic file organization by type, date, or project.
It provides functions to scan directories, categorize files, and move them
safely while preserving metadata.
"""

import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from utils import validate_path, setup_logging, log_operation

# Initialize logger
logger = setup_logging()

# File category mappings
CATEGORY_MAPPINGS = {
    'Documents': ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.xls', 
                  '.xlsx', '.ppt', '.pptx', '.csv', '.md'],
    'Images': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.ico', 
               '.webp', '.tiff', '.tif'],
    'Videos': ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', 
               '.m4v', '.mpg', '.mpeg'],
    'Audio': ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a', 
              '.opus'],
    'Archives': ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz', 
                 '.iso'],
}


def scan_directory(path: str) -> List[Dict]:
    """
    Scan directory and return list of files with metadata.
    
    This function recursively scans a directory and collects information
    about all files found, including their paths, sizes, and timestamps.
    
    Args:
        path: Directory path to scan
        
    Returns:
        List of dictionaries containing file information
        
    Example:
        >>> files = scan_directory("/home/user/downloads")
        >>> len(files)
        42
    """
    if not validate_path(path):
        logger.error(f"Invalid path provided: {path}")
        return []
    
    files = []
    path_obj = Path(path).resolve()
    
    try:
        for item in path_obj.iterdir():
            if item.is_file():
                try:
                    stat = item.stat()
                    file_info = {
                        'path': str(item),
                        'name': item.name,
                        'extension': item.suffix.lower(),
                        'size': stat.st_size,
                        'modified': datetime.fromtimestamp(stat.st_mtime),
                        'category': get_file_category(item.suffix.lower())
                    }
                    files.append(file_info)
                except (OSError, PermissionError) as e:
                    logger.warning(f"Cannot access file {item}: {e}")
                    continue
    
    except (OSError, PermissionError) as e:
        logger.error(f"Cannot scan directory {path}: {e}")
        return []
    
    return files


def get_file_category(extension: str) -> str:
    """
    Map file extension to category (Documents, Images, etc.).
    
    Args:
        extension: File extension including the dot (e.g., '.pdf')
        
    Returns:
        Category name as string
        
    Example:
        >>> get_file_category('.pdf')
        'Documents'
        >>> get_file_category('.unknown')
        'Others'
    """
    extension = extension.lower()
    
    for category, extensions in CATEGORY_MAPPINGS.items():
        if extension in extensions:
            return category
    
    return 'Others'



def move_file_safely(source: str, destination: str, preserve_metadata: bool = True) -> bool:
    """
    Move file with error handling and metadata preservation.
    
    This function safely moves a file from source to destination,
    preserving timestamps and handling errors gracefully.
    
    Args:
        source: Source file path
        destination: Destination file path
        preserve_metadata: Whether to preserve file timestamps
        
    Returns:
        bool: True if successful, False otherwise
        
    Example:
        >>> move_file_safely("/tmp/file.txt", "/home/user/file.txt")
        True
    """
    try:
        source_path = Path(source)
        dest_path = Path(destination)
        
        # Ensure source exists
        if not source_path.exists():
            logger.error(f"Source file does not exist: {source}")
            return False
        
        # Create destination directory if needed
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Get original timestamps before moving
        if preserve_metadata:
            stat = source_path.stat()
            atime = stat.st_atime
            mtime = stat.st_mtime
        
        # Move the file
        shutil.move(str(source_path), str(dest_path))
        
        # Restore timestamps
        if preserve_metadata:
            os.utime(str(dest_path), (atime, mtime))
        
        logger.info(f"Successfully moved: {source} -> {destination}")
        return True
    
    except (OSError, PermissionError, shutil.Error) as e:
        logger.error(f"Failed to move {source} to {destination}: {e}")
        return False


def organize_by_type(files: List[Dict], target_dir: str, preview: bool = False) -> Dict:
    """
    Organize files into folders by extension type.
    
    This function categorizes files and moves them into category-based
    folders (Documents, Images, Videos, etc.).
    
    Args:
        files: List of file information dictionaries
        target_dir: Base directory for organized files
        preview: If True, only simulate without moving files
        
    Returns:
        Dictionary with operation results
        
    Example:
        >>> result = organize_by_type(files, "/home/user/organized")
        >>> result['processed']
        42
    """
    result = {
        'success': True,
        'processed': 0,
        'errors': [],
        'summary': {}
    }
    
    if not validate_path(target_dir):
        result['success'] = False
        result['errors'].append(f"Invalid target directory: {target_dir}")
        return result
    
    # Group files by category
    category_counts = {}
    
    for file_info in files:
        category = file_info['category']
        source = file_info['path']
        filename = file_info['name']
        
        # Build destination path
        category_dir = Path(target_dir) / category
        destination = category_dir / filename
        
        # Track category counts
        category_counts[category] = category_counts.get(category, 0) + 1
        
        if preview:
            # Preview mode - don't actually move files
            result['processed'] += 1
        else:
            # Execute mode - move files
            if move_file_safely(source, str(destination)):
                result['processed'] += 1
            else:
                result['errors'].append(f"Failed to move: {filename}")
    
    result['summary'] = {
        'by_category': category_counts,
        'total_files': len(files)
    }
    
    log_operation('organize_by_type', {
        'processed': result['processed'],
        'errors': len(result['errors']),
        'preview': preview
    })
    
    return result


def organize_by_date(files: List[Dict], target_dir: str, preview: bool = False) -> Dict:
    """
    Organize files into folders by modification date.
    
    This function creates folders using YYYY-MM-DD format and moves
    files based on their modification timestamps.
    
    Args:
        files: List of file information dictionaries
        target_dir: Base directory for organized files
        preview: If True, only simulate without moving files
        
    Returns:
        Dictionary with operation results
        
    Example:
        >>> result = organize_by_date(files, "/home/user/organized")
        >>> result['processed']
        42
    """
    result = {
        'success': True,
        'processed': 0,
        'errors': [],
        'summary': {}
    }
    
    if not validate_path(target_dir):
        result['success'] = False
        result['errors'].append(f"Invalid target directory: {target_dir}")
        return result
    
    # Group files by date
    date_counts = {}
    
    for file_info in files:
        source = file_info['path']
        filename = file_info['name']
        modified_date = file_info['modified']
        
        # Format date as YYYY-MM-DD
        date_folder = modified_date.strftime('%Y-%m-%d')
        
        # Build destination path
        date_dir = Path(target_dir) / date_folder
        destination = date_dir / filename
        
        # Track date counts
        date_counts[date_folder] = date_counts.get(date_folder, 0) + 1
        
        if preview:
            # Preview mode - don't actually move files
            result['processed'] += 1
        else:
            # Execute mode - move files
            if move_file_safely(source, str(destination)):
                result['processed'] += 1
            else:
                result['errors'].append(f"Failed to move: {filename}")
    
    result['summary'] = {
        'by_date': date_counts,
        'total_files': len(files)
    }
    
    log_operation('organize_by_date', {
        'processed': result['processed'],
        'errors': len(result['errors']),
        'preview': preview
    })
    
    return result


def organize_by_project(files: List[Dict], rules: Dict, target_dir: str, 
                       preview: bool = False) -> Dict:
    """
    Organize files based on custom project rules.
    
    This function applies user-defined rules to organize files into
    project-specific folders based on filename patterns or extensions.
    
    Args:
        files: List of file information dictionaries
        rules: Dictionary mapping patterns to project folder names
        target_dir: Base directory for organized files
        preview: If True, only simulate without moving files
        
    Returns:
        Dictionary with operation results
        
    Example:
        >>> rules = {'report': 'Reports', '.py': 'Python_Projects'}
        >>> result = organize_by_project(files, rules, "/home/user/projects")
    """
    result = {
        'success': True,
        'processed': 0,
        'errors': [],
        'summary': {}
    }
    
    if not validate_path(target_dir):
        result['success'] = False
        result['errors'].append(f"Invalid target directory: {target_dir}")
        return result
    
    if not rules:
        result['success'] = False
        result['errors'].append("No organization rules provided")
        return result
    
    # Group files by project
    project_counts = {}
    unmatched_count = 0
    
    for file_info in files:
        source = file_info['path']
        filename = file_info['name']
        
        # Find matching rule
        matched_project = None
        for pattern, project_name in rules.items():
            if pattern.lower() in filename.lower():
                matched_project = project_name
                break
        
        if matched_project:
            # Build destination path
            project_dir = Path(target_dir) / matched_project
            destination = project_dir / filename
            
            # Track project counts
            project_counts[matched_project] = project_counts.get(matched_project, 0) + 1
            
            if preview:
                result['processed'] += 1
            else:
                if move_file_safely(source, str(destination)):
                    result['processed'] += 1
                else:
                    result['errors'].append(f"Failed to move: {filename}")
        else:
            # No matching rule - move to "Unmatched" folder
            unmatched_dir = Path(target_dir) / "Unmatched"
            destination = unmatched_dir / filename
            unmatched_count += 1
            
            if preview:
                result['processed'] += 1
            else:
                if move_file_safely(source, str(destination)):
                    result['processed'] += 1
                else:
                    result['errors'].append(f"Failed to move: {filename}")
    
    result['summary'] = {
        'by_project': project_counts,
        'unmatched': unmatched_count,
        'total_files': len(files)
    }
    
    log_operation('organize_by_project', {
        'processed': result['processed'],
        'errors': len(result['errors']),
        'preview': preview
    })
    
    return result
