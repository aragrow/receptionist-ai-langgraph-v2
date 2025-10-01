#!/usr/bin/env python3
"""
Code Consolidator - Combines files from specified directories into a single text file
"""

import os
from pathlib import Path
from datetime import datetime


# ============ CONFIGURATION ============
# Add directories to process here - easily scalable
DIRECTORIES_TO_PROCESS = ['src', 'config','tests', 'docs','analytics']

# Optional: Add specific files from root
ROOT_FILES_TO_INCLUDE = ['main.py']

# ============ FILE PROCESSING ============

def get_file_extension_info(filepath):
    """Get a description of the file type based on extension"""
    ext = filepath.suffix.lower()
    descriptions = {
        '.py': 'Python',
        '.js': 'JavaScript',
        '.ts': 'TypeScript',
        '.html': 'HTML',
        '.css': 'CSS',
        '.json': 'JSON',
        '.md': 'Markdown',
        '.txt': 'Text',
        '.yml': 'YAML',
        '.yaml': 'YAML',
        '.xml': 'XML',
        '.sh': 'Shell Script',
        '.bat': 'Batch Script',
        '.sql': 'SQL',
        '.java': 'Java',
        '.cpp': 'C++',
        '.c': 'C',
        '.h': 'C/C++ Header',
        '.go': 'Go',
        '.rs': 'Rust',
        '.rb': 'Ruby',
        '.php': 'PHP',
        '.html': 'HTML',
    }
    return descriptions.get(ext, 'Unknown')


def should_include_file(filepath):
    """Determine if a file should be included (exclude binary and large files)"""
    # Skip common binary extensions
    binary_extensions = {'.pyc', '.pyo', '.pyd', '.so', '.dll', '.dylib', 
                         '.exe', '.bin', '.dat', '.db', '.sqlite', '.png', 
                         '.jpg', '.jpeg', '.gif', '.ico', '.pdf', '.zip', 
                         '.tar', '.gz', '.rar', '.7z'}
    
    if filepath.suffix.lower() in binary_extensions:
        return False
    
    # Skip files larger than 1MB
    try:
        if filepath.stat().st_size > 1024 * 1024:
            return False
    except:
        return False
    
    return True


def read_file_safely(filepath):
    """Attempt to read file with multiple encodings"""
    encodings = ['utf-8', 'latin-1', 'cp1252']
    
    for encoding in encodings:
        try:
            with open(filepath, 'r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
        except Exception as e:
            return f"[Error reading file: {str(e)}]"
    
    return "[Could not decode file with supported encodings]"


def consolidate_code(output_filename='consolidated_code.txt'):
    """Main function to consolidate all code files"""
    
    current_dir = Path.cwd()
    files_to_process = []
    
    # Add root files
    print(f"Scanning root files...")
    for filename in ROOT_FILES_TO_INCLUDE:
        filepath = current_dir / filename
        if filepath.exists() and filepath.is_file():
            files_to_process.append(('ROOT', filepath))
            print(f"  Found: {filename}")
    
    # Add files from configured directories
    for dir_name in DIRECTORIES_TO_PROCESS:
        dir_path = current_dir / dir_name
        
        if not dir_path.exists() or not dir_path.is_dir():
            print(f"Warning: Directory '{dir_name}' not found, skipping...")
            continue
        
        print(f"Scanning directory: {dir_name}/")
        file_count = 0
        
        for filepath in sorted(dir_path.rglob('*')):
            if filepath.is_file() and should_include_file(filepath):
                files_to_process.append((dir_name, filepath))
                file_count += 1
        
        print(f"  Found {file_count} files in {dir_name}/")
    
    if not files_to_process:
        print("No files found to process!")
        return None
    
    # Write consolidated output
    with open(output_filename, 'w', encoding='utf-8') as output:
        # Write header
        output.write("=" * 80 + "\n")
        output.write("CODE CONSOLIDATION REPORT\n")
        output.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        output.write(f"Total files: {len(files_to_process)}\n")
        output.write(f"Directories: {', '.join(DIRECTORIES_TO_PROCESS)}\n")
        output.write("=" * 80 + "\n\n")
        
        # Write each file's content
        for location, filepath in files_to_process:
            separator = "=" * 80
            output.write(f"\n{separator}\n")
            
            if location == 'ROOT':
                output.write(f"FILE: {filepath.name}\n")
                output.write(f"PATH: ./{filepath.name}\n")
            else:
                dir_path = current_dir / location
                relative_path = filepath.relative_to(dir_path)
                output.write(f"FILE: {filepath.name}\n")
                output.write(f"PATH: ./{location}/{relative_path}\n")
            
            output.write(f"TYPE: {get_file_extension_info(filepath)}\n")
            output.write(f"SIZE: {filepath.stat().st_size:,} bytes\n")
            output.write(f"{separator}\n\n")
            
            # Write file content with section marker
            if location == 'ROOT':
                output.write(f"# ==================== {filepath.name} ====================\n")
            else:
                relative_path = filepath.relative_to(current_dir / location)
                output.write(f"# ==================== {location}/{relative_path} ====================\n")
            
            content = read_file_safely(filepath)
            output.write(content)
            output.write("\n\n")
        
        # Write footer with summary
        output.write("\n" + "=" * 80 + "\n")
        output.write("END OF CONSOLIDATION\n")
        output.write("=" * 80 + "\n")
    
    print(f"\n✓ Consolidation complete!")
    print(f"✓ Output written to: {output_filename}")
    print(f"✓ Total files processed: {len(files_to_process)}")
    
    # Print breakdown by directory
    print(f"\nBreakdown by location:")
    from collections import Counter
    location_counts = Counter(loc for loc, _ in files_to_process)
    for location, count in sorted(location_counts.items()):
        print(f"  {location}: {count} files")
    
    return output_filename


if __name__ == "__main__":
    consolidate_code()