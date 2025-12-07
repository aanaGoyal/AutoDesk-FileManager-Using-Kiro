"""
Duplicate file finder module for the File Management System.

This module scans directories and identifies duplicate files using
content hashing.
"""

import os
import hashlib
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import logging


def calculate_file_hash(file_path: str) -> str:
    """Calculate MD5 hash of file content."""
    hash_md5 = hashlib.md5()
    
    try:
        with open(file_path, 'rb') as f:
            # Read in chunks for memory efficiency
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        logger = logging.getLogger('file_management_system')
        logger.error(f"Failed to hash {file_path}: {e}")
        return ""


def get_file_info(file_path: str) -> Dict:
    """Get file metadata (size, date, path)."""
    try:
        path_obj = Path(file_path)
        stat = path_obj.stat()
        
        return {
            'path': str(path_obj.resolve()),
            'name': path_obj.name,
            'size': stat.st_size,
            'modified': datetime.fromtimestamp(stat.st_mtime)
        }
    except Exception as e:
        logger = logging.getLogger('file_management_system')
        logger.error(f"Failed to get info for {file_path}: {e}")
        return None


def scan_for_duplicates(directory: str, recursive: bool = True) -> Dict:
    """Scan directory and group duplicate files by hash."""
    from utils import validate_path
    
    logger = logging.getLogger('file_management_system')
    
    if not validate_path(directory):
        raise ValueError(f"Invalid or inaccessible path: {directory}")
    
    # Dictionary to store hash -> list of files
    hash_map = {}
    path_obj = Path(directory).resolve()
    
    # Get all files
    if recursive:
        files = path_obj.rglob('*')
    else:
        files = path_obj.glob('*')
    
    # First pass: Group files by size (faster pre-filter)
    size_map = {}
    
    for file_path in files:
        if file_path.is_file():
            try:
                stat = file_path.stat()
                file_size = stat.st_size
                
                # Skip empty files (they're not useful duplicates)
                if file_size == 0:
                    continue
                
                # Skip very small files (< 100 bytes) - likely not real duplicates
                if file_size < 100:
                    continue
                
                if file_size not in size_map:
                    size_map[file_size] = []
                
                size_map[file_size].append(str(file_path))
            
            except Exception as e:
                logger.warning(f"Error processing {file_path}: {e}")
                continue
    
    # Second pass: Only hash files that have the same size (potential duplicates)
    for file_size, file_paths in size_map.items():
        # Only hash if there are multiple files with the same size
        if len(file_paths) > 1:
            for file_path in file_paths:
                try:
                    file_hash = calculate_file_hash(file_path)
                    
                    if file_hash:
                        if file_hash not in hash_map:
                            hash_map[file_hash] = []
                        
                        file_info = get_file_info(file_path)
                        if file_info:
                            hash_map[file_hash].append(file_info)
                
                except Exception as e:
                    logger.warning(f"Error hashing {file_path}: {e}")
                    continue
    
    # Filter to only duplicates (hash with more than one file)
    duplicate_groups = {}
    
    for file_hash, files in hash_map.items():
        if len(files) > 1:
            total_size = sum(f['size'] for f in files)
            duplicate_groups[file_hash] = {
                'hash': file_hash,
                'files': files,
                'count': len(files),
                'total_size': total_size
            }
    
    return duplicate_groups


def remove_duplicates(duplicate_groups: Dict, keep_indices: List) -> Dict:
    """Remove selected duplicate files."""
    logger = logging.getLogger('file_management_system')
    
    result = {
        'success': True,
        'processed': 0,
        'errors': [],
        'summary': {
            'removed': 0,
            'kept': 0,
            'space_saved': 0
        }
    }
    
    for group_hash, group_data in duplicate_groups.items():
        files = group_data['files']
        
        # Ensure at least one file is kept
        if not keep_indices or len(keep_indices) == 0:
            # Keep the first file by default
            keep_indices = [0]
        
        for idx, file_info in enumerate(files):
            try:
                if idx not in keep_indices:
                    # Remove this file
                    file_path = Path(file_info['path'])
                    if file_path.exists():
                        # Ensure file_size is an integer
                        file_size = int(file_info.get('size_bytes', file_info.get('size', 0)))
                        file_path.unlink()
                        result['summary']['removed'] += 1
                        result['summary']['space_saved'] += file_size
                        logger.info(f"Removed duplicate: {file_path}")
                else:
                    result['summary']['kept'] += 1
                
                result['processed'] += 1
            
            except Exception as e:
                result['errors'].append(f"Failed to remove {file_info['path']}: {str(e)}")
                logger.error(f"Failed to remove {file_info['path']}: {e}")
    
    if result['errors']:
        result['success'] = False
    
    return result


def archive_duplicates(duplicate_groups: Dict, archive_dir: str) -> Dict:
    """Move duplicates to archive folder."""
    logger = logging.getLogger('file_management_system')
    
    result = {
        'success': True,
        'processed': 0,
        'errors': [],
        'summary': {
            'archived': 0,
            'kept': 0,
            'space_moved': 0
        }
    }
    
    # Create archive directory
    archive_path = Path(archive_dir)
    archive_path.mkdir(parents=True, exist_ok=True)
    
    for group_hash, group_data in duplicate_groups.items():
        files = group_data['files']
        
        # Keep the first file, archive the rest
        for idx, file_info in enumerate(files):
            try:
                if idx > 0:  # Archive all except first
                    source = Path(file_info['path'])
                    
                    if source.exists():
                        # Create unique filename in archive
                        dest_name = source.name
                        dest = archive_path / dest_name
                        
                        # Ensure unique name in archive
                        counter = 1
                        while dest.exists():
                            stem = source.stem
                            suffix = source.suffix
                            dest_name = f"{stem}_{counter}{suffix}"
                            dest = archive_path / dest_name
                            counter += 1
                        
                        # Move file
                        shutil.move(str(source), str(dest))
                        result['summary']['archived'] += 1
                        # Ensure size is an integer
                        file_size = int(file_info.get('size_bytes', file_info.get('size', 0)))
                        result['summary']['space_moved'] += file_size
                        logger.info(f"Archived duplicate: {source} -> {dest}")
                else:
                    result['summary']['kept'] += 1
                
                result['processed'] += 1
            
            except Exception as e:
                result['errors'].append(f"Failed to archive {file_info['path']}: {str(e)}")
                logger.error(f"Failed to archive {file_info['path']}: {e}")
    
    if result['errors']:
        result['success'] = False
    
    return result
