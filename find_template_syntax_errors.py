#!/usr/bin/env python3
"""
Template Syntax Error Finder

This script helps identify potential Django template syntax errors,
particularly where JavaScript template literals (${var}) might be
mixed with Django template variables ({{ var }}).
"""

import re
import sys

def find_template_syntax_errors(file_path):
    """Find potential template syntax errors in a file."""
    # Patterns to look for
    pattern1 = re.compile(r'\${.*?}\$*/{.*?}')  # JS template with Django syntax
    pattern2 = re.compile(r'\${.*?}/\$*{.*?}')  # JS template with Django syntax
    pattern3 = re.compile(r'\${.*?}/{{.*?}}')   # JS template with Django variable
    pattern4 = re.compile(r'\${.*?}/{ .*?}')    # JS template with malformed Django variable
    
    with open(file_path, 'r') as f:
        lines = f.readlines()
        
    issues_found = False
    
    for i, line in enumerate(lines):
        line_num = i + 1
        
        # Check all patterns
        for j, pattern in enumerate([pattern1, pattern2, pattern3, pattern4]):
            match = pattern.search(line)
            if match:
                print(f"Line {line_num}: Potential template syntax issue (pattern {j+1}):")
                print(f"  {line.strip()}")
                print(f"  {' ' * match.start()}{'~' * (match.end() - match.start())}")
                issues_found = True
                
        # Special check for Django variables in JS template literals
        js_template_parts = re.findall(r'`(.*?)`', line)
        for part in js_template_parts:
            if '{{' in part or '{%' in part:
                print(f"Line {line_num}: Django template syntax inside JavaScript template literal:")
                print(f"  {line.strip()}")
                issues_found = True
    
    return issues_found

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <template_file>")
        sys.exit(1)
        
    file_path = sys.argv[1]
    if not find_template_syntax_errors(file_path):
        print(f"No template syntax errors found in {file_path}")