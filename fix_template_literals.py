#!/usr/bin/env python3
"""
JavaScript Template Literal Checker

This script checks Django templates for places where Django template variables
might be incorrectly used inside JavaScript template literals (using backticks).

Example of a problematic pattern:
    ```html
    <script>
        // BAD - Django variable inside JS template literal
        element.textContent = `Value: ${someVar}/${{{ django_var }}}`;
        
        // GOOD - Value passed to JS context or computed separately
        element.textContent = `Value: ${someVar}/${totalPeriods}`;
    </script>
    ```

Usage:
    python fix_template_literals.py [--fix]
"""

import os
import re
import sys
import argparse
from pathlib import Path

# Pattern to look for Django variables inside JavaScript template literals
PATTERN = r'`[^`]*\${[^}]*}[^`]*/\${{\s*([^}]*)\s*}}[^`]*`'  # Specifically for Period ${var}/${django_var}
# Pattern to look for places where template vars might be mixed incorrectly with JS
DJANGO_IN_JS_PATTERN = r'`[^`]*\${{\s*([^}]*)\s*}}[^`]*`'  # Any Django var in JS template
# Optional pattern to match other suspicious template mixing
SUSPICIOUS_PATTERN = r'`[^`]*{{[^}]*}}[^`]*`'  # General pattern for any {{ }} in backticks

def find_template_literal_errors(file_path, fix=False):
    """Find and optionally fix template literal errors in a file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Track if we found any issues
    found_issues = False
    
    # Create a copy of content for modifications
    new_content = content
    
    # Check for specific pattern (period/total_periods issue)
    pattern_matches = re.finditer(PATTERN, content)
    for match in pattern_matches:
        found_issues = True
        line_num = content[:match.start()].count(os.linesep) + 1
        print(f"Found specific 'Period/total_periods' issue in {file_path}:")
        print(f"  Line: {line_num}")
        print(f"  Error: {match.group(0)}")
        print(f"  Django variable inside template literal: {match.group(1)}")
        
        # Extract the Django variable name
        django_var = match.group(1).strip()
        
        if fix:
            # Create a javascript variable before the template literal
            js_name = django_var.replace('|', '_').replace(':', '_').replace(' ', '_')
            
            # Extract the context (entire JavaScript statement or block)
            # Find the start of the line
            line_start = content.rfind('\n', 0, match.start()) + 1
            line_end = content.find('\n', match.end())
            if line_end == -1:
                line_end = len(content)
            
            line = content[line_start:line_end].strip()
            indentation = content[line_start:content.find(line.lstrip()[0], line_start)]
            
            # Create a fix by adding a JavaScript variable declaration before the problematic line
            js_var_declaration = f"{indentation}const {js_name} = {{ total_periods }};\n"
            fixed_line = line.replace(
                "${{{ total_periods }}}", 
                "${" + js_name + "}"
            )
            
            # Replace in the content
            new_content = new_content.replace(line, fixed_line)
            new_content = new_content.replace(
                indentation + fixed_line, 
                js_var_declaration + indentation + fixed_line
            )
            
            print(f"  Fixed with:\n{js_var_declaration}{indentation}{fixed_line}")
        
        print("")
    
    # Check for Django variables directly in JS template literals
    django_in_js_matches = re.finditer(DJANGO_IN_JS_PATTERN, content)
    for match in django_in_js_matches:
        found_issues = True
        line_num = content[:match.start()].count(os.linesep) + 1
        print(f"Django variable in JS template literal in {file_path}:")
        print(f"  Line: {line_num}")
        print(f"  Issue: {match.group(0)}")
        print(f"  Django variable: {match.group(1)}")
        print("  Suggestion: Move Django variable outside of template literal")
        print("")
    
    # Check for potentially problematic patterns (Django syntax in JS)
    if not found_issues:  # Only if no specific issues found
        suspicious_matches = re.finditer(SUSPICIOUS_PATTERN, content)
        for match in suspicious_matches:
            found_issues = True
            line_num = content[:match.start()].count(os.linesep) + 1
            print(f"Suspicious pattern in {file_path}:")
            print(f"  Line: {line_num}")
            print(f"  Possible issue: {match.group(0)}")
            print("  Suggestion: Double-check this line for template/JS syntax mixing")
            print("")
    
    # If fixing mode is on and issues were found, write the new content
    if fix and found_issues and new_content != content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Fixed issues in {file_path}")
    
    return found_issues

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Find and fix template literal errors in Django templates')
    parser.add_argument('--fix', action='store_true', help='Attempt to fix found issues')
    args = parser.parse_args()
    
    # Get the base directory
    if os.path.exists('./smorasfotball'):
        base_dir = './smorasfotball'
    else:
        base_dir = '.'
    
    # Find all template files
    template_files = []
    for root, _, files in os.walk(base_dir):
        for file in files:
            if file.endswith('.html'):
                template_files.append(os.path.join(root, file))
    
    # Check each template file
    found_issues = False
    for file_path in template_files:
        if find_template_literal_errors(file_path, args.fix):
            found_issues = True
    
    if not found_issues:
        print("No template literal errors found!")
        return 0
    
    return 1

if __name__ == "__main__":
    sys.exit(main())