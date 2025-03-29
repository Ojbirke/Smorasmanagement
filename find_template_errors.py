#!/usr/bin/env python3
"""
Template Error Detection Tool

This script scans Django templates to find potential syntax errors,
particularly focusing on template variables in JavaScript code.
"""

import re
import os
import sys
from pathlib import Path

def scan_file(file_path):
    """Scan a file for potential template syntax errors"""
    print(f"Scanning {file_path}...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.split('\n')
    
    # Patterns to search for
    js_string_with_double_braces = r'`[^`]*\{\{[^}]*\}\}[^`]*`'
    django_var_with_triple_braces = r'\{\{\{[^}]*\}\}\}'
    js_string_with_django_vars = r'`[^`]*\{[^{][^}]*\}[^`]*`'
    
    issues = []
    
    # Check each line
    for i, line in enumerate(lines):
        line_num = i + 1
        
        # Look for template variables in backtick strings
        if re.search(js_string_with_double_braces, line):
            issues.append((line_num, "Django template variable inside JavaScript template literal", line))
        
        # Look for triple braces (common mistake)
        if re.search(django_var_with_triple_braces, line):
            issues.append((line_num, "Triple braces in template syntax", line))
        
        # Look for JavaScript variables inside backtick strings that might be conflated with Django variables
        if re.search(js_string_with_django_vars, line):
            # Check if this is likely to be an issue (JS variables inside the string)
            potential_issues = re.findall(r'`[^`]*\{([^{][^}]*)\}[^`]*`', line)
            for match in potential_issues:
                if not match.strip().startswith('data.') and not match.isalnum():
                    issues.append((line_num, "Potential confusion between JS and Django template variables", line))
    
    # Report the issues
    if issues:
        print(f"Found {len(issues)} potential issues:")
        for line_num, message, text in issues:
            print(f"  - Line {line_num}: {message}")
            print(f"    {text.strip()}")
        return True
    else:
        print("No issues found.")
        return False

def main():
    """Main function"""
    if len(sys.argv) > 1:
        template_path = sys.argv[1]
    else:
        # Default to match_session_pitch.html
        template_path = os.path.join("smorasfotball", "teammanager", "templates", "teammanager", "match_session_pitch.html")
    
    if not os.path.exists(template_path):
        print(f"Error: File not found: {template_path}")
        return 1
    
    has_issues = scan_file(template_path)
    return 1 if has_issues else 0

if __name__ == "__main__":
    sys.exit(main())