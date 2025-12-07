"""
Screenshot renamer module for the File Management System.

This module uses OCR to extract text from screenshots and generate
descriptive filenames.
"""

import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict
import logging

try:
    import pytesseract
    from PIL import Image, ImageEnhance, ImageFilter
    TESSERACT_AVAILABLE = True
    
    # Configure Tesseract path for Windows
    # Update this path if Tesseract is installed elsewhere
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
except ImportError:
    TESSERACT_AVAILABLE = False

try:
    import easyocr
    EASYOCR_AVAILABLE = True
    # Initialize EasyOCR reader (will be lazy-loaded on first use)
    _easyocr_reader = None
except ImportError:
    EASYOCR_AVAILABLE = False
    _easyocr_reader = None


def preprocess_image(image):
    """Enhance image for better OCR results."""
    try:
        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Resize if image is too small (upscale for better OCR)
        width, height = image.size
        if width < 1000 or height < 1000:
            scale_factor = max(1000 / width, 1000 / height)
            new_size = (int(width * scale_factor), int(height * scale_factor))
            image = image.resize(new_size, Image.Resampling.LANCZOS)
        
        # Enhance contrast
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.5)
        
        # Enhance sharpness
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(2.0)
        
        # Apply slight blur to reduce noise
        image = image.filter(ImageFilter.MedianFilter(size=3))
        
        return image
    except Exception as e:
        # If preprocessing fails, return original
        return image


def get_easyocr_reader():
    """Lazy-load EasyOCR reader to avoid startup delay."""
    global _easyocr_reader
    if _easyocr_reader is None and EASYOCR_AVAILABLE:
        _easyocr_reader = easyocr.Reader(['en'], gpu=False)
    return _easyocr_reader


def extract_text_with_easyocr(image_path: str) -> str:
    """Extract text using EasyOCR (often better for screenshots)."""
    logger = logging.getLogger('file_management_system')
    
    try:
        reader = get_easyocr_reader()
        if reader is None:
            return ""
        
        # Read text from image with optimized settings for speed
        results = reader.readtext(
            image_path, 
            detail=0, 
            paragraph=True,
            batch_size=1,  # Process one at a time for lower memory
            workers=0      # Disable multiprocessing for faster single images
        )
        
        if results:
            # Join all detected text
            text = ' '.join(results)
            logger.info(f"EasyOCR extracted {len(text)} characters from {image_path}")
            return text.strip()
        
        return ""
    except Exception as e:
        logger.error(f"EasyOCR failed for {image_path}: {e}")
        return ""


def extract_text_from_image(image_path: str) -> str:
    """Use OCR to extract text from screenshot - FAST mode (Tesseract only)."""
    if not TESSERACT_AVAILABLE:
        raise ImportError("pytesseract is required for OCR functionality")
    
    logger = logging.getLogger('file_management_system')
    
    # Use Tesseract only for speed (EasyOCR is too slow on CPU)
    try:
        # Load image
        original_image = Image.open(image_path)
        
        # Fast strategy: Just use Tesseract with best settings
        text = pytesseract.image_to_string(original_image, config='--psm 3 --oem 3')
        if text and len(text.strip()) > 3:
            logger.info(f"OCR extracted {len(text)} chars from {image_path}")
            return text.strip()
        
        # Fallback: Try with different mode if first attempt failed
        text = pytesseract.image_to_string(original_image, config='--psm 6 --oem 3')
        return text.strip() if text else ""
        
    except Exception as e:
        logger.error(f"OCR failed for {image_path}: {e}")
        return ""


def generate_descriptive_name(text: str, max_length: int = 60) -> str:
    """Create clean, meaningful filename from extracted text."""
    from utils import sanitize_filename
    import re
    
    if not text or not text.strip():
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"screenshot_{timestamp}"
    
    # Clean the text
    text = ' '.join(text.split())
    
    # Find important keywords (capitalized words often indicate titles/headers)
    words = text.split()
    
    # Categorize words
    important_words = []  # Capitalized or long words
    regular_words = []    # Other words
    
    # Common filler words to skip
    skip_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
        'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
        'this', 'that', 'these', 'those', 'it', 'its', 'will', 'can', 'may',
        'has', 'have', 'had', 'do', 'does', 'did', 'not', 'no', 'yes'
    }
    
    for word in words:
        # Clean the word
        clean_word = re.sub(r'[^\w]', '', word)
        
        # Skip if too short or only numbers
        if len(clean_word) < 2 or (clean_word.isdigit() and len(clean_word) < 4):
            continue
        
        # Skip common filler words
        if clean_word.lower() in skip_words:
            continue
        
        # Skip words with too many uppercase (likely OCR errors like "CERTIFICATE")
        uppercase_ratio = sum(1 for c in clean_word if c.isupper()) / len(clean_word)
        
        # Prioritize words that are:
        # 1. Title case (first letter capital)
        # 2. Longer words (more meaningful)
        # 3. Not all caps (unless it's a short acronym)
        
        if clean_word[0].isupper() and not clean_word.isupper():
            # Title case word - likely important
            important_words.append(clean_word)
        elif len(clean_word) >= 5 and uppercase_ratio < 0.8:
            # Long word that's not all caps
            important_words.append(clean_word)
        elif len(clean_word) <= 4 and clean_word.isupper():
            # Short acronym (like PDF, PNG, etc.)
            important_words.append(clean_word)
        elif uppercase_ratio < 0.3:
            # Mostly lowercase - regular word
            regular_words.append(clean_word)
    
    # Detect document type
    text_lower = text.lower()
    doc_prefix = None
    if 'certificate' in text_lower:
        doc_prefix = 'Certificate'
    elif 'invoice' in text_lower or 'receipt' in text_lower:
        doc_prefix = 'Invoice'
    elif 'ticket' in text_lower or 'boarding' in text_lower:
        doc_prefix = 'Ticket'
    
    # Build filename: prioritize important words, then add regular words if space
    meaningful_words = []
    
    # Add document type prefix if detected
    if doc_prefix:
        meaningful_words.append(doc_prefix)
    
    # Add important words first (limit to 4)
    for word in important_words[:4]:
        # Skip if it's the same as doc_prefix
        if doc_prefix and word.lower() == doc_prefix.lower():
            continue
        if len('_'.join(meaningful_words + [word])) <= max_length:
            meaningful_words.append(word)
    
    # Add regular words if we have space (limit to 2 more)
    for word in regular_words[:2]:
        if len('_'.join(meaningful_words + [word])) <= max_length:
            meaningful_words.append(word)
        if len(meaningful_words) >= 5:  # Max 5 words total
            break
    
    # If no meaningful words found, try to extract any recognizable pattern
    if not meaningful_words:
        # Look for any word with 4+ letters
        for word in words:
            clean_word = re.sub(r'[^\w]', '', word)
            if len(clean_word) >= 4 and not clean_word.isdigit():
                meaningful_words.append(clean_word)
                if len(meaningful_words) >= 4:
                    break
    
    # Still nothing? Use timestamp
    if not meaningful_words:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"screenshot_{timestamp}"
    
    # Join words with underscores
    descriptive_name = '_'.join(meaningful_words)
    
    # Sanitize the filename
    sanitized = sanitize_filename(descriptive_name)
    
    # Final check
    if not sanitized or len(sanitized) < 3:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"screenshot_{timestamp}"
    
    return sanitized


def ensure_unique_filename(directory: str, filename: str) -> str:
    """Add numeric suffix if filename exists."""
    path = Path(directory)
    name_stem = Path(filename).stem
    extension = Path(filename).suffix
    
    # Check if file exists
    target = path / filename
    if not target.exists():
        return filename
    
    # Add numeric suffix
    counter = 1
    while True:
        new_filename = f"{name_stem}_{counter}{extension}"
        target = path / new_filename
        if not target.exists():
            return new_filename
        counter += 1


def rename_screenshots(files: List[str], preview: bool = True) -> List[Dict]:
    """Process screenshots and return rename proposals."""
    logger = logging.getLogger('file_management_system')
    
    if not TESSERACT_AVAILABLE:
        logger.error("Tesseract OCR is not installed")
        return [{
            'original_path': '',
            'original_name': '',
            'proposed_name': '',
            'extracted_text': '',
            'status': 'error',
            'error': 'Tesseract OCR is not installed. Please install pytesseract and Pillow.'
        }]
    
    results = []
    
    for file_path in files:
        try:
            path_obj = Path(file_path)
            
            if not path_obj.exists():
                results.append({
                    'original_path': file_path,
                    'original_name': path_obj.name,
                    'proposed_name': '',
                    'extracted_text': '',
                    'status': 'error',
                    'error': 'File not found'
                })
                continue
            
            # Extract text using OCR
            extracted_text = extract_text_from_image(file_path)
            
            # Generate descriptive name
            new_name_stem = generate_descriptive_name(extracted_text)
            new_name = new_name_stem + path_obj.suffix
            
            # Ensure uniqueness
            unique_name = ensure_unique_filename(str(path_obj.parent), new_name)
            
            result = {
                'original_path': file_path,
                'original_name': path_obj.name,
                'proposed_name': unique_name,
                'extracted_text': extracted_text[:200] if extracted_text else '(no text found)',
                'status': 'success'
            }
            
            # If not preview mode, perform the rename
            if not preview:
                try:
                    new_path = path_obj.parent / unique_name
                    path_obj.rename(new_path)
                    result['status'] = 'renamed'
                except Exception as e:
                    result['status'] = 'error'
                    result['error'] = str(e)
                    logger.error(f"Failed to rename {file_path}: {e}")
            
            results.append(result)
        
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            results.append({
                'original_path': file_path,
                'original_name': Path(file_path).name if Path(file_path).exists() else '',
                'proposed_name': '',
                'extracted_text': '',
                'status': 'error',
                'error': str(e)
            })
    
    return results
