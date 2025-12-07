# Design Document

## Overview

The File Management System is a Flask web application that provides three core features: automated file organization, intelligent screenshot renaming using OCR, and duplicate file detection. The system uses a simple client-server architecture where the Flask backend handles file operations and the HTML/CSS frontend provides an intuitive user interface.

The application is designed with simplicity and clarity in mind, making it accessible to developers of all skill levels. Each feature is implemented as a separate Python module with clear separation of concerns.

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────┐
│         Web Browser (Client)            │
│    HTML/CSS Interface + JavaScript      │
└──────────────┬──────────────────────────┘
               │ HTTP Requests
               ▼
┌─────────────────────────────────────────┐
│         Flask Application               │
│  ┌─────────────────────────────────┐   │
│  │      Routes (app.py)            │   │
│  └──────────┬──────────────────────┘   │
│             │                           │
│  ┌──────────▼──────────────────────┐   │
│  │   Business Logic Modules        │   │
│  │  • organizer.py                 │   │
│  │  • renamer.py                   │   │
│  │  • finder.py                    │   │
│  │  • utils.py                     │   │
│  └─────────────────────────────────┘   │
└──────────────┬──────────────────────────┘
               │ File System Operations
               ▼
┌─────────────────────────────────────────┐
│         File System                     │
│  User's directories and files           │
└─────────────────────────────────────────┘
```

### Technology Stack

- **Backend**: Python 3.8+ with Flask 2.x
- **Frontend**: HTML5, CSS3, vanilla JavaScript
- **OCR**: Tesseract OCR with pytesseract wrapper
- **File Operations**: Python standard library (os, shutil, pathlib)
- **Hashing**: hashlib (MD5 for duplicate detection)
- **Image Processing**: Pillow (PIL)

## Components and Interfaces

### 1. Flask Application (app.py)

Main application file that defines routes and initializes the Flask app.

**Routes:**
- `GET /` - Home page with feature selection
- `GET /organize` - File organizer interface
- `POST /organize/preview` - Preview organization changes
- `POST /organize/execute` - Execute file organization
- `GET /rename` - Screenshot renamer interface
- `POST /rename/preview` - Preview renamed screenshots
- `POST /rename/execute` - Execute screenshot renaming
- `GET /duplicates` - Duplicate finder interface
- `POST /duplicates/scan` - Scan for duplicates
- `POST /duplicates/remove` - Remove selected duplicates

### 2. File Organizer Module (organizer.py)

Handles automatic file organization by type, date, or project.

**Functions:**
```python
def scan_directory(path: str) -> List[Dict]:
    """Scan directory and return list of files with metadata"""
    
def organize_by_type(files: List[Dict], target_dir: str) -> Dict:
    """Organize files into folders by extension type"""
    
def organize_by_date(files: List[Dict], target_dir: str) -> Dict:
    """Organize files into folders by modification date"""
    
def organize_by_project(files: List[Dict], rules: Dict, target_dir: str) -> Dict:
    """Organize files based on custom project rules"""
    
def get_file_category(extension: str) -> str:
    """Map file extension to category (Documents, Images, etc.)"""
    
def move_file_safely(source: str, destination: str) -> bool:
    """Move file with error handling and metadata preservation"""
```

### 3. Screenshot Renamer Module (renamer.py)

Uses OCR to extract text from screenshots and generate descriptive filenames.

**Functions:**
```python
def extract_text_from_image(image_path: str) -> str:
    """Use OCR to extract text from screenshot"""
    
def generate_descriptive_name(text: str, max_length: int = 50) -> str:
    """Create clean filename from extracted text"""
    
def sanitize_filename(name: str) -> str:
    """Remove special characters and format filename"""
    
def rename_screenshots(files: List[str], preview: bool = True) -> List[Dict]:
    """Process screenshots and return rename proposals"""
    
def ensure_unique_filename(directory: str, filename: str) -> str:
    """Add numeric suffix if filename exists"""
```

### 4. Duplicate Finder Module (finder.py)

Scans directories and identifies duplicate files using content hashing.

**Functions:**
```python
def calculate_file_hash(file_path: str) -> str:
    """Calculate MD5 hash of file content"""
    
def scan_for_duplicates(directory: str, recursive: bool = True) -> Dict:
    """Scan directory and group duplicate files by hash"""
    
def get_file_info(file_path: str) -> Dict:
    """Get file metadata (size, date, path)"""
    
def remove_duplicates(duplicate_groups: Dict, keep_indices: List) -> Dict:
    """Remove selected duplicate files"""
    
def archive_duplicates(duplicate_groups: Dict, archive_dir: str) -> Dict:
    """Move duplicates to archive folder"""
```

### 5. Utility Module (utils.py)

Common helper functions used across modules.

**Functions:**
```python
def validate_path(path: str) -> bool:
    """Validate directory path exists and is accessible"""
    
def format_file_size(bytes: int) -> str:
    """Convert bytes to human-readable format"""
    
def create_progress_tracker() -> Dict:
    """Create progress tracking object for long operations"""
    
def log_operation(operation: str, details: Dict) -> None:
    """Log file operations for debugging"""
```

## Data Models

### File Information Dictionary
```python
{
    'path': str,           # Full file path
    'name': str,           # Filename with extension
    'extension': str,      # File extension
    'size': int,           # Size in bytes
    'modified': datetime,  # Last modified timestamp
    'category': str        # File category (for organizer)
}
```

### Rename Proposal Dictionary
```python
{
    'original_path': str,      # Current file path
    'original_name': str,      # Current filename
    'proposed_name': str,      # New filename
    'extracted_text': str,     # OCR extracted text
    'status': str              # 'success', 'error', 'skipped'
}
```

### Duplicate Group Dictionary
```python
{
    'hash': str,               # File content hash
    'files': List[Dict],       # List of duplicate file info
    'total_size': int,         # Combined size of duplicates
    'count': int               # Number of duplicates
}
```

### Operation Result Dictionary
```python
{
    'success': bool,           # Operation success status
    'processed': int,          # Number of files processed
    'errors': List[str],       # Error messages
    'summary': Dict            # Operation-specific summary
}
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*


### Property Reflection

Before defining properties, let's identify and eliminate redundancy:

- Properties 1.1 (scan returns all files) and 3.1 (hash all files) both verify complete file enumeration - these can be combined
- Properties 2.1 (OCR processes all files) is redundant with 2.2 (generates names from OCR) - if names are generated, OCR must have run
- Properties 6.1, 6.2, 6.3 (preview modes) all test the same concept of preview-before-execute - can be combined
- Property 4.4 (summary display) is covered by testing that operations return complete result dictionaries

After reflection, we'll focus on unique, high-value properties that provide distinct validation.

### Correctness Properties

**Property 1: Complete file enumeration**
*For any* valid directory path, scanning that directory should return a list containing all files present in that directory (no files missed, no non-existent files included)
**Validates: Requirements 1.1, 3.1**

**Property 2: File type categorization correctness**
*For any* file with a known extension, the categorization function should map it to exactly one of the predefined categories (Documents, Images, Videos, Audio, Archives, Others)
**Validates: Requirements 1.2**

**Property 3: Date folder format consistency**
*For any* file being organized by date, the target folder name should match the YYYY-MM-DD format derived from the file's modification timestamp
**Validates: Requirements 1.3**

**Property 4: Metadata preservation invariant**
*For any* file that is successfully moved, the modification and creation timestamps in the destination should equal the timestamps from the source location
**Validates: Requirements 1.5**

**Property 5: Error isolation property**
*For any* batch of files where some operations fail, the number of successfully processed files plus the number of errors should equal the total number of files, and all errors should be logged
**Validates: Requirements 1.6, 2.6, 5.1, 5.2**

**Property 6: Filename length constraint**
*For any* text extracted from OCR, the generated filename should not exceed 50 characters (excluding extension)
**Validates: Requirements 2.2**

**Property 7: Filename sanitization**
*For any* string containing special characters or spaces, the sanitized filename should contain only alphanumeric characters, underscores, hyphens, and periods
**Validates: Requirements 2.4**

**Property 8: Filename uniqueness guarantee**
*For any* target directory and proposed filename, if that filename already exists, the system should generate a variant with a numeric suffix that does not exist in that directory
**Validates: Requirements 2.5**

**Property 9: Content-based duplicate detection**
*For any* two files with identical content but different names, the duplicate detection should identify them as duplicates (same hash value)
**Validates: Requirements 3.3**

**Property 10: Duplicate preservation invariant**
*For any* group of duplicate files, after removal operation, at least one file from that group should remain in the file system
**Validates: Requirements 3.4**

**Property 11: Archive completeness**
*For any* set of files selected for archival, all selected files should exist in the archive directory after the operation completes
**Validates: Requirements 3.5**

**Property 12: Input validation before processing**
*For any* invalid directory path (non-existent, inaccessible, or malformed), the system should reject it and return an error before attempting any file operations
**Validates: Requirements 5.3**

**Property 13: Preview mode non-modification**
*For any* operation executed in preview mode, no files should be moved, renamed, or deleted on the file system
**Validates: Requirements 6.1, 6.2, 6.3**

**Property 14: Operation result completeness**
*For any* completed operation, the result dictionary should contain all required fields: success status, count of processed files, error list, and operation-specific summary
**Validates: Requirements 4.4, 6.5**

## Error Handling

### Error Categories and Responses

1. **File System Errors**
   - Permission denied: Log error, skip file, continue processing
   - File not found: Log error, skip file, continue processing
   - Disk full: Halt operation, rollback if possible, notify user
   - File locked: Skip file, add to skipped list, continue processing

2. **Input Validation Errors**
   - Invalid path: Return error immediately, do not process
   - Empty file list: Return warning, do not process
   - Invalid organization rules: Return error with details

3. **OCR Processing Errors**
   - Tesseract not installed: Display installation instructions
   - Image format not supported: Skip file, log error
   - OCR extraction fails: Use fallback naming (timestamp), log error

4. **Duplicate Detection Errors**
   - Cannot read file for hashing: Skip file, log error
   - Hash collision (extremely rare): Log warning, treat as duplicates

### Error Logging

All errors will be logged with:
- Timestamp
- Operation type
- File path (if applicable)
- Error message
- Stack trace (for debugging)

Logs stored in: `logs/file_management.log`

## Testing Strategy

### Unit Testing

We'll use Python's `unittest` framework for unit tests. Tests will cover:

1. **Utility Functions**
   - Path validation with valid/invalid paths
   - File size formatting
   - Filename sanitization with various special characters

2. **File Categorization**
   - Extension to category mapping
   - Unknown extensions default to "Others"

3. **OCR Text Processing**
   - Descriptive name generation from sample texts
   - Empty text handling
   - Special character removal

4. **Hash Calculation**
   - Consistent hashing for same content
   - Different hashes for different content

### Property-Based Testing

We'll use `Hypothesis` library for property-based testing. This allows us to test properties across randomly generated inputs.

**Configuration:**
- Minimum 100 iterations per property test
- Each test tagged with format: `**Feature: file-management-system, Property {N}: {description}**`

**Property Tests to Implement:**

1. File enumeration completeness (Property 1)
2. File type categorization (Property 2)
3. Date format consistency (Property 3)
4. Metadata preservation (Property 4)
5. Error isolation (Property 5)
6. Filename length constraints (Property 6)
7. Filename sanitization (Property 7)
8. Filename uniqueness (Property 8)
9. Content-based duplicate detection (Property 9)
10. Duplicate preservation (Property 10)
11. Archive completeness (Property 11)
12. Input validation (Property 12)
13. Preview mode safety (Property 13)
14. Result completeness (Property 14)

### Integration Testing

Test complete workflows:
- Full organization workflow (scan → preview → execute)
- Full rename workflow (select → OCR → preview → rename)
- Full duplicate workflow (scan → review → remove/archive)

### Manual Testing

- UI responsiveness and visual feedback
- Error message clarity
- Cross-browser compatibility (Chrome, Firefox, Safari)

## Implementation Notes

### Directory Structure

```
file-management-system/
├── app.py                 # Flask application and routes
├── organizer.py          # File organization logic
├── renamer.py            # Screenshot renaming with OCR
├── finder.py             # Duplicate file detection
├── utils.py              # Common utility functions
├── requirements.txt      # Python dependencies
├── README.md            # Setup and usage documentation
├── static/
│   ├── css/
│   │   └── style.css    # Application styles
│   └── js/
│       └── main.js      # Frontend JavaScript
├── templates/
│   ├── base.html        # Base template
│   ├── index.html       # Home page
│   ├── organize.html    # File organizer interface
│   ├── rename.html      # Screenshot renamer interface
│   └── duplicates.html  # Duplicate finder interface
├── logs/
│   └── file_management.log
└── tests/
    ├── test_organizer.py
    ├── test_renamer.py
    ├── test_finder.py
    ├── test_utils.py
    └── test_properties.py  # Property-based tests
```

### Key Dependencies

```
Flask==2.3.0
pytesseract==0.3.10
Pillow==10.0.0
hypothesis==6.82.0  # For property-based testing
```

### OCR Setup

Tesseract OCR must be installed on the system:
- **Windows**: Download installer from GitHub
- **macOS**: `brew install tesseract`
- **Linux**: `sudo apt-get install tesseract-ocr`

### Code Style Guidelines

- Use descriptive variable names (e.g., `source_file_path` not `sfp`)
- Add docstrings to all functions explaining purpose, parameters, and return values
- Keep functions small and focused (single responsibility)
- Use type hints for function parameters and return values
- Add inline comments for complex logic
- Follow PEP 8 formatting (4-space indentation, max 79 characters per line)

### Security Considerations

1. **Path Traversal Prevention**: Validate all user-provided paths to prevent access outside allowed directories
2. **File Size Limits**: Set maximum file size for OCR processing to prevent memory issues
3. **Input Sanitization**: Sanitize all user inputs before using in file operations
4. **Safe File Operations**: Use context managers and proper exception handling for all file I/O

### Performance Considerations

1. **Large Directory Handling**: Process files in batches, provide progress updates
2. **OCR Optimization**: Process images in parallel where possible
3. **Hash Calculation**: Use efficient chunk-based reading for large files
4. **Caching**: Cache file hashes to avoid recalculation

### User Experience Enhancements

1. **Progress Indicators**: Show progress bars for long-running operations
2. **Confirmation Dialogs**: Require confirmation before destructive operations
3. **Undo Capability**: Consider implementing operation history for undo
4. **Responsive Design**: Ensure UI works on different screen sizes
5. **Clear Feedback**: Provide immediate visual feedback for all user actions
