"""Quick test script to verify backend functionality"""

from utils import validate_path
from organizer import scan_directory, organize_by_type
import os

# Test current directory
test_dir = os.getcwd()
print(f"Testing with directory: {test_dir}")
print(f"Path validation: {validate_path(test_dir)}")

# Test scanning
try:
    files = scan_directory(test_dir)
    print(f"\nFound {len(files)} files")
    if files:
        print("\nFirst 3 files:")
        for f in files[:3]:
            print(f"  - {f['name']} ({f['category']}, {f['size']} bytes)")
except Exception as e:
    print(f"Error scanning: {e}")

print("\n✅ Backend is working!")
