#!/usr/bin/env python
"""
Template Syntax Error Finder

This script helps identify potential Django template syntax errors,
particularly where JavaScript template literals (${var}) might be
mixed with Django template variables ({{ var }}).
"""

import re
import sys
import os

def find_template_syntax_errors(file_path):
    """Find potential template syntax errors in a file."""
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return False
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.split('\n')
    
    # Look for cases where JavaScript template literals contain Django template variables
    js_template_pattern = re.compile(r'`[^`]*\${[^}]*{{[^}]*}}[^}]*}[^`]*`')
    js_template_matches = js_template_pattern.finditer(content)
    
    found_errors = False
    for match in js_template_matches:
        start = match.start()
        # Find the line number
        line_num = content[:start].count('\n') + 1
        line = lines[line_num - 1].strip()
        print(f"Line {line_num}: Possible mix of JS template literals and Django variables:")
        print(f"  {line}")
        found_errors = True
    
    # Also look for direct cases where "${" is followed by "{{ " in the same line
    for i, line in enumerate(lines):
        if "${" in line and "{{" in line:
            js_template_parts = line.split("${")
            for part in js_template_parts[1:]:  # Skip the part before first ${ 
                if "{{" in part and "}" in part and part.find("{{") < part.find("}"):
                    print(f"Line {i+1}: Possible mix of JS template literals and Django variables:")
                    print(f"  {line.strip()}")
                    found_errors = True
                    break

    # Check for incomplete JS template literals
    for i, line in enumerate(lines):
        # Count the number of backticks in the line
        backtick_count = line.count('`')
        if backtick_count % 2 != 0 and backtick_count > 0:
            print(f"Line {i+1}: Odd number of backticks (possibly unclosed template literal):")
            print(f"  {line.strip()}")
            found_errors = True
    
    # Look for known problem patterns in our specific case
    for i, line in enumerate(lines):
        if "Period" in line and "${" in line and "total_periods" in line:
            if line.count("${") != line.count("}"):
                print(f"Line {i+1}: Unmatched template literals in period display:")
                print(f"  {line.strip()}")
                found_errors = True

    return found_errors

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python find_template_syntax_errors.py <file_path>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    found_errors = find_template_syntax_errors(file_path)
    
    if not found_errors:
        print("No obvious template syntax errors found.")