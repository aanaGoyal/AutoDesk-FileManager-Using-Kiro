"""
Flask application for the File Management System.

This is the main application file that defines routes and initializes
the Flask app.
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
import os
from pathlib import Path
import logging

# Import our modules
from utils import setup_logging, validate_path, format_file_size
from organizer import scan_directory, organize_by_type, organize_by_date, organize_by_project
from renamer import rename_screenshots
from finder import scan_for_duplicates, remove_duplicates, archive_duplicates


# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Setup logging
logger = setup_logging()


@app.route('/')
def index():
    """Home page with feature selection."""
    return render_template('index.html')


@app.route('/test-path', methods=['POST'])
def test_path():
    """Test endpoint to debug path validation."""
    try:
        data = request.get_json()
        path = data.get('path', '')
        
        result = {
            'received_path': path,
            'path_type': type(path).__name__,
            'path_length': len(path) if path else 0,
            'is_valid': validate_path(path),
            'current_dir': os.getcwd()
        }
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/organize/preview', methods=['POST'])
def organize_preview():
    """Preview organization changes."""
    try:
        data = request.get_json()
        directory = data.get('directory', '')
        mode = data.get('mode', 'type')  # type, date, or project
        
        logger.info(f"Preview request - Directory: '{directory}', Mode: {mode}")
        
        # Validate directory
        if not validate_path(directory):
            logger.error(f"Path validation failed for: '{directory}'")
            return jsonify({
                'success': False,
                'error': f'Invalid or inaccessible directory path: {directory}'
            }), 400
        
        # Scan directory
        files = scan_directory(directory)
        
        # Generate preview based on mode
        preview_data = []
        
        if mode == 'type':
            for file_info in files:
                preview_data.append({
                    'original': file_info['name'],
                    'destination': f"{file_info['category']}/{file_info['name']}",
                    'size': format_file_size(file_info['size'])
                })
        
        elif mode == 'date':
            for file_info in files:
                date_str = file_info['modified'].strftime('%Y-%m-%d')
                preview_data.append({
                    'original': file_info['name'],
                    'destination': f"{date_str}/{file_info['name']}",
                    'size': format_file_size(file_info['size'])
                })
        
        elif mode == 'project':
            rules = data.get('rules', {})
            # For preview, we'll just show uncategorized
            for file_info in files:
                preview_data.append({
                    'original': file_info['name'],
                    'destination': f"Uncategorized/{file_info['name']}",
                    'size': format_file_size(file_info['size'])
                })
        
        return jsonify({
            'success': True,
            'preview': preview_data,
            'total_files': len(files)
        })
    
    except Exception as e:
        logger.error(f"Preview error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/organize/execute', methods=['POST'])
def organize_execute():
    """Execute file organization."""
    try:
        data = request.get_json()
        directory = data.get('directory', '')
        mode = data.get('mode', 'type')
        target_dir = data.get('target_dir', directory)
        
        # Validate directory
        if not validate_path(directory):
            return jsonify({
                'success': False,
                'error': 'Invalid or inaccessible directory path'
            }), 400
        
        # Scan directory
        files = scan_directory(directory)
        
        # Execute organization based on mode
        if mode == 'type':
            result = organize_by_type(files, target_dir)
        elif mode == 'date':
            result = organize_by_date(files, target_dir)
        elif mode == 'project':
            rules = data.get('rules', {})
            result = organize_by_project(files, rules, target_dir)
        else:
            return jsonify({
                'success': False,
                'error': 'Invalid organization mode'
            }), 400
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Organization error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/rename/upload', methods=['POST'])
def rename_upload():
    """Handle file uploads for renaming - saves to uploads folder temporarily."""
    try:
        if 'files[]' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No files uploaded'
            }), 400
        
        files = request.files.getlist('files[]')
        uploaded_paths = []
        
        for file in files:
            if file.filename:
                # Save uploaded file temporarily
                filename = file.filename
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                uploaded_paths.append(filepath)
        
        # Get rename proposals (preview mode)
        results = rename_screenshots(uploaded_paths, preview=True)
        
        return jsonify({
            'success': True,
            'results': results,
            'uploaded_count': len(uploaded_paths),
            'mode': 'upload'  # Indicate this is upload mode
        })
    
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/rename/execute-upload', methods=['POST'])
def rename_execute_upload():
    """Execute renaming for uploaded files and provide download."""
    try:
        data = request.get_json()
        files = data.get('files', [])
        
        if not files:
            return jsonify({
                'success': False,
                'error': 'No files provided'
            }), 400
        
        # Execute renaming in uploads folder
        results = rename_screenshots(files, preview=False)
        
        # Count successes
        success_count = sum(1 for r in results if r['status'] == 'renamed')
        error_count = sum(1 for r in results if r['status'] == 'error')
        
        # Prepare download info
        download_files = []
        for result in results:
            if result['status'] == 'renamed':
                # File was renamed in uploads folder
                new_filename = result['proposed_name']
                download_files.append({
                    'filename': new_filename,
                    'original': result['original_name']
                })
        
        return jsonify({
            'success': error_count == 0,
            'results': results,
            'summary': {
                'renamed': success_count,
                'errors': error_count
            },
            'download_files': download_files
        })
    
    except Exception as e:
        logger.error(f"Rename execution error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/rename/preview', methods=['POST'])
def rename_preview():
    """Preview renamed screenshots."""
    try:
        data = request.get_json()
        files = data.get('files', [])
        
        if not files:
            return jsonify({
                'success': False,
                'error': 'No files provided'
            }), 400
        
        # Get rename proposals
        results = rename_screenshots(files, preview=True)
        
        return jsonify({
            'success': True,
            'results': results
        })
    
    except Exception as e:
        logger.error(f"Rename preview error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/rename/execute', methods=['POST'])
def rename_execute():
    """Execute screenshot renaming."""
    try:
        data = request.get_json()
        files = data.get('files', [])
        download = data.get('download', False)
        
        if not files:
            return jsonify({
                'success': False,
                'error': 'No files provided'
            }), 400
        
        # Execute renaming
        results = rename_screenshots(files, preview=False)
        
        # Count successes and errors
        success_count = sum(1 for r in results if r['status'] == 'renamed')
        error_count = sum(1 for r in results if r['status'] == 'error')
        
        # If download requested, provide download links
        download_links = []
        if download:
            for result in results:
                if result['status'] == 'renamed':
                    # Get the new file path
                    original_dir = os.path.dirname(result['original_path'])
                    new_path = os.path.join(original_dir, result['proposed_name'])
                    if os.path.exists(new_path):
                        download_links.append({
                            'filename': result['proposed_name'],
                            'path': new_path
                        })
        
        return jsonify({
            'success': error_count == 0,
            'results': results,
            'summary': {
                'renamed': success_count,
                'errors': error_count
            },
            'download_links': download_links
        })
    
    except Exception as e:
        logger.error(f"Rename execution error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/download/<path:filename>')
def download_file(filename):
    """Download renamed file."""
    try:
        upload_folder = app.config['UPLOAD_FOLDER']
        file_path = os.path.join(upload_folder, filename)
        
        logger.info(f"Download request for: {filename}")
        logger.info(f"Looking in: {upload_folder}")
        logger.info(f"Full path: {file_path}")
        logger.info(f"File exists: {os.path.exists(file_path)}")
        
        if os.path.exists(file_path):
            return send_from_directory(upload_folder, filename, as_attachment=True)
        else:
            logger.error(f"File not found: {file_path}")
            return jsonify({'error': f'File not found: {filename}'}), 404
    except Exception as e:
        logger.error(f"Download error: {e}")
        return jsonify({'error': str(e)}), 500



@app.route('/duplicates/scan', methods=['POST'])
def duplicates_scan():
    """Scan for duplicates."""
    try:
        data = request.get_json()
        directory = data.get('directory', '')
        recursive = data.get('recursive', True)
        
        # Validate directory
        if not validate_path(directory):
            return jsonify({
                'success': False,
                'error': 'Invalid or inaccessible directory path'
            }), 400
        
        # Scan for duplicates
        duplicate_groups = scan_for_duplicates(directory, recursive)
        
        # Format for response
        formatted_groups = []
        total_space = 0
        
        for group_hash, group_data in duplicate_groups.items():
            # Calculate space that could be saved (all but one file)
            space_saveable = sum(f['size'] for f in group_data['files'][1:])
            total_space += space_saveable
            
            formatted_groups.append({
                'hash': group_hash,
                'count': group_data['count'],
                'files': [{
                    'path': f['path'],
                    'name': f['name'],
                    'size': format_file_size(f['size']),
                    'size_bytes': f['size'],
                    'modified': f['modified'].strftime('%Y-%m-%d %H:%M:%S')
                } for f in group_data['files']],
                'space_saveable': format_file_size(space_saveable)
            })
        
        return jsonify({
            'success': True,
            'groups': formatted_groups,
            'total_groups': len(formatted_groups),
            'total_space_saveable': format_file_size(total_space)
        })
    
    except Exception as e:
        logger.error(f"Duplicate scan error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/duplicates/remove', methods=['POST'])
def duplicates_remove():
    """Remove selected duplicates."""
    try:
        data = request.get_json()
        action = data.get('action', 'remove')  # remove or archive
        duplicate_groups = data.get('groups', {})
        archive_dir = data.get('archive_dir', 'duplicates_archive')
        
        if action == 'archive':
            result = archive_duplicates(duplicate_groups, archive_dir)
        else:
            # For remove, keep first file of each group
            keep_indices = [0]
            result = remove_duplicates(duplicate_groups, keep_indices)
        
        # Format space saved
        if 'space_saved' in result['summary']:
            result['summary']['space_saved_formatted'] = format_file_size(result['summary']['space_saved'])
        if 'space_moved' in result['summary']:
            result['summary']['space_moved_formatted'] = format_file_size(result['summary']['space_moved'])
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Duplicate removal error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return render_template('index.html'), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal error: {error}")
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
