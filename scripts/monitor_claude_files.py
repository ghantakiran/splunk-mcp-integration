#!/usr/bin/env python3
"""
CLAUDE.md File Size and Token Monitor

This script monitors the size and estimated token count of CLAUDE.md files
across the project to ensure they stay within manageable limits.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

def estimate_tokens(text: str) -> int:
    """
    Estimate token count using a simple heuristic.
    Approximately 4 characters per token for English text.
    """
    return len(text) // 4

def get_file_info(file_path: Path) -> Dict:
    """Get file size and token information."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        char_count = len(content)
        line_count = content.count('\n') + 1
        word_count = len(content.split())
        token_estimate = estimate_tokens(content)
        
        return {
            'path': str(file_path),
            'exists': True,
            'char_count': char_count,
            'line_count': line_count,
            'word_count': word_count,
            'token_estimate': token_estimate,
            'size_mb': char_count / (1024 * 1024),
            'status': 'OK' if token_estimate < 20000 else 'WARNING' if token_estimate < 25000 else 'CRITICAL'
        }
    except FileNotFoundError:
        return {
            'path': str(file_path),
            'exists': False,
            'char_count': 0,
            'line_count': 0,
            'word_count': 0,
            'token_estimate': 0,
            'size_mb': 0,
            'status': 'MISSING'
        }

def find_claude_files(project_root: Path) -> List[Path]:
    """Find all CLAUDE.md files in the project."""
    claude_files = []
    
    # Main CLAUDE.md
    main_claude = project_root / "CLAUDE.md"
    if main_claude.exists():
        claude_files.append(main_claude)
    
    # Service-specific CLAUDE.md files
    services_dir = project_root / "services"
    if services_dir.exists():
        for service_dir in services_dir.iterdir():
            if service_dir.is_dir():
                claude_file = service_dir / "CLAUDE.md"
                if claude_file.exists():
                    claude_files.append(claude_file)
    
    # Frontend CLAUDE.md
    frontend_claude = project_root / "frontend" / "CLAUDE.md"
    if frontend_claude.exists():
        claude_files.append(frontend_claude)
    
    # Infrastructure CLAUDE.md
    infrastructure_claude = project_root / "infrastructure" / "CLAUDE.md"
    if infrastructure_claude.exists():
        claude_files.append(infrastructure_claude)
    
    return claude_files

def print_file_report(file_info: Dict):
    """Print a report for a single file."""
    status_colors = {
        'OK': '\033[92m',       # Green
        'WARNING': '\033[93m',  # Yellow
        'CRITICAL': '\033[91m', # Red
        'MISSING': '\033[90m'   # Gray
    }
    reset_color = '\033[0m'
    
    status = file_info['status']
    color = status_colors.get(status, '')
    
    print(f"{color}[{status}]{reset_color} {file_info['path']}")
    
    if file_info['exists']:
        print(f"  📄 Lines: {file_info['line_count']:,}")
        print(f"  📝 Words: {file_info['word_count']:,}")
        print(f"  🔤 Characters: {file_info['char_count']:,}")
        print(f"  🎯 Estimated Tokens: {file_info['token_estimate']:,}")
        print(f"  💾 Size: {file_info['size_mb']:.2f} MB")
        
        if status == 'WARNING':
            print(f"  ⚠️  File is approaching token limit (25,000)")
        elif status == 'CRITICAL':
            print(f"  🚨 File exceeds recommended token limit!")
    else:
        print(f"  ❌ File does not exist")
    
    print()

def print_summary(all_files: List[Dict]):
    """Print a summary of all files."""
    total_tokens = sum(f['token_estimate'] for f in all_files if f['exists'])
    total_files = len([f for f in all_files if f['exists']])
    missing_files = len([f for f in all_files if not f['exists']])
    warning_files = len([f for f in all_files if f['status'] == 'WARNING'])
    critical_files = len([f for f in all_files if f['status'] == 'CRITICAL'])
    
    print("=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    print(f"Total files found: {total_files}")
    print(f"Missing files: {missing_files}")
    print(f"Warning files (>20k tokens): {warning_files}")
    print(f"Critical files (>25k tokens): {critical_files}")
    print(f"Total estimated tokens: {total_tokens:,}")
    print(f"Average tokens per file: {total_tokens // total_files if total_files > 0 else 0:,}")
    print()
    
    if critical_files > 0:
        print("🚨 CRITICAL: Some files exceed the 25,000 token limit!")
        print("   Consider splitting these files or reducing content.")
    elif warning_files > 0:
        print("⚠️  WARNING: Some files are approaching the token limit.")
        print("   Monitor these files and consider content optimization.")
    else:
        print("✅ All files are within acceptable token limits.")

def main():
    """Main function to run the monitor."""
    # Get project root directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    print("🔍 CLAUDE.md File Monitor")
    print("=" * 60)
    print(f"Project root: {project_root}")
    print()
    
    # Find all CLAUDE.md files
    claude_files = find_claude_files(project_root)
    
    if not claude_files:
        print("❌ No CLAUDE.md files found in the project.")
        sys.exit(1)
    
    print(f"Found {len(claude_files)} CLAUDE.md files:")
    print()
    
    # Analyze each file
    all_file_info = []
    for file_path in claude_files:
        file_info = get_file_info(file_path)
        all_file_info.append(file_info)
        print_file_report(file_info)
    
    # Print summary
    print_summary(all_file_info)
    
    # Exit with appropriate code
    critical_files = [f for f in all_file_info if f['status'] == 'CRITICAL']
    if critical_files:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()