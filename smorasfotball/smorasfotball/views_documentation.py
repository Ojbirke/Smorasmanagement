"""
Documentation Views for Smørås Fotball
"""

import os
from pathlib import Path

from django.http import FileResponse, Http404
from django.shortcuts import render
from django.conf import settings


def documentation_index(request):
    """Documentation index page"""
    return render(request, 'documentation/index.html')


def download_pdf_documentation(request):
    """Serve the technical documentation PDF"""
    # Define the PDF file path - adjust as needed based on your project structure
    pdf_path = Path(settings.BASE_DIR.parent) / "SmorasFotball_Technical_Documentation.pdf"
    
    if not pdf_path.exists():
        # Check for alternative location in the project root
        pdf_path = Path(settings.BASE_DIR) / "SmorasFotball_Technical_Documentation.pdf"
        
        if not pdf_path.exists():
            raise Http404("Documentation PDF not found")
    
    # Serve the PDF file
    return FileResponse(
        open(pdf_path, 'rb'),
        as_attachment=True,
        filename='SmorasFotball_Technical_Documentation.pdf'
    )