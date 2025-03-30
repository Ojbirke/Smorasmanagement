#!/bin/bash
# Fix Template Errors
# This script scans Django templates for common syntax errors and attempts to fix them

echo "=== Smørås Fotball Template Error Fix Tool ==="
echo "Scanning templates for potential syntax errors..."

# Run the template error finder script
python find_template_errors.py

echo ""
echo "Checking specifically for JavaScript-Django template syntax mixing..."

# Common patterns that might cause errors
echo "Checking for {{ variable }} in JavaScript template literals..."
grep -r "\\${.*{{.*}}.*}" --include="*.html" smorasfotball/teammanager/templates/

echo "Checking for ${ inside Django template variables..."
grep -r "{{.*\\${.*}}" --include="*.html" smorasfotball/teammanager/templates/

echo ""
echo "Scan complete! If any issues were found, fix them manually in the specified files."
echo "For JavaScript template literals in Django templates, use something like:"
echo "  periodBadge.textContent = \`Period \${data.match_info.period}/\${data.match_info.total_periods}\`;"
echo ""
echo "Instead of mixing Django variables inside JavaScript literals like:"
echo "  periodBadge.textContent = \`Period \${data.match_info.period}/\${{ total_periods }}\`;"
echo ""
echo "For Django template variables, use regular JavaScript variables that were initialized with Django values."