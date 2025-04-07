"""
Generate PDF Technical Documentation

This script generates a PDF file containing technical documentation for
the Smørås Fotball application.
"""

import os
import sys
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.platypus.flowables import HRFlowable

# Set up styles
styles = getSampleStyleSheet()
title_style = styles["Title"]
heading1_style = styles["Heading1"] 
heading2_style = styles["Heading2"]
normal_style = styles["Normal"]

# Create custom styles
code_style = ParagraphStyle(
    name='Code',
    parent=styles['Normal'],
    fontName='Courier',
    fontSize=8,
    leading=10,
    firstLineIndent=0,
    leftIndent=20,
    rightIndent=20,
    spaceAfter=10,
    spaceBefore=10,
    backColor=colors.lightgrey,
)

def create_pdf_documentation(output_path):
    """Create the technical documentation PDF"""
    doc = SimpleDocTemplate(
        output_path, 
        pagesize=letter,
        leftMargin=inch*0.75,
        rightMargin=inch*0.75,
        topMargin=inch*0.75,
        bottomMargin=inch*0.75
    )
    
    # Initialize story list (all content goes here)
    story = []
    
    # Create title
    story.append(Paragraph("Smørås Fotball Technical Documentation", title_style))
    story.append(Spacer(1, 0.25*inch))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y')}", normal_style))
    story.append(Spacer(1, 0.25*inch))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.black))
    story.append(Spacer(1, 0.25*inch))
    
    # Table of Contents
    story.append(Paragraph("Table of Contents", heading1_style))
    story.append(Spacer(1, 0.1*inch))
    toc_data = [
        ["1. Project Overview"],
        ["2. Project Structure"],
        ["3. Key Technologies"],
        ["4. Database Schema"],
        ["5. Key Features"],
        ["6. Technical Implementation Details"],
        ["7. Code Execution Flow"],
    ]
    toc_table = Table(toc_data, colWidths=[5.5*inch])
    toc_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(toc_table)
    story.append(Spacer(1, 0.5*inch))
    
    # 1. Project Overview
    story.append(PageBreak())
    story.append(Paragraph("1. Project Overview", heading1_style))
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph(
        "The Smørås Fotball application is a comprehensive team management platform "
        "designed for youth football teams. It provides tools for managing teams, "
        "players, matches, and formations, as well as detailed statistics and reporting. "
        "The application is built using the Django web framework and employs a PostgreSQL "
        "database for data persistence.", normal_style))
    story.append(Spacer(1, 0.2*inch))
    
    # 2. Project Structure
    story.append(PageBreak())
    story.append(Paragraph("2. Project Structure", heading1_style))
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph("The application follows the standard Django project structure with some customizations:", normal_style))
    story.append(Spacer(1, 0.1*inch))
    
    dirs_data = [
        ["Directory/File", "Description"],
        ["smorasfotball/", "Main Django project directory"],
        ["smorasfotball/smorasfotball/", "Core project settings and configuration"],
        ["smorasfotball/teammanager/", "Primary application module"],
        ["smorasfotball/teammanager/models.py", "Database models"],
        ["smorasfotball/teammanager/views_*.py", "View functions organized by feature"],
        ["smorasfotball/teammanager/urls.py", "URL routing configuration"],
        ["smorasfotball/templates/", "HTML templates"],
        ["smorasfotball/static/", "Static assets (CSS, JS, images)"],
    ]
    dirs_table = Table(dirs_data, colWidths=[2.5*inch, 3.5*inch])
    dirs_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(dirs_table)
    story.append(Spacer(1, 0.2*inch))
    
    # 3. Key Technologies
    story.append(PageBreak())
    story.append(Paragraph("3. Key Technologies", heading1_style))
    story.append(Spacer(1, 0.1*inch))
    
    tech_data = [
        ["Technology", "Version", "Purpose"],
        ["Django", "5.1.x", "Web framework"],
        ["PostgreSQL", "Latest", "Database"],
        ["Bootstrap", "5.x", "Frontend UI framework"],
        ["JavaScript", "ES6+", "Client-side interactivity"],
        ["jQuery", "Latest", "DOM manipulation"],
        ["Chart.js", "Latest", "Data visualization"],
    ]
    tech_table = Table(tech_data, colWidths=[1.5*inch, 1.2*inch, 3.3*inch])
    tech_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(tech_table)
    story.append(Spacer(1, 0.2*inch))
    
    # 4. Database Schema
    story.append(PageBreak())
    story.append(Paragraph("4. Database Schema", heading1_style))
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph("The application uses the following main models:", normal_style))
    story.append(Spacer(1, 0.1*inch))
    
    models_data = [
        ["Model", "Description", "Key Relationships"],
        ["Team", "Football team", "Players, Matches"],
        ["Player", "Individual player", "Team, MatchAppearance"],
        ["Match", "Football match", "Teams, MatchAppearances"],
        ["MatchAppearance", "Player's appearance in a match", "Player, Match"],
        ["Formation", "Team formation template", "Positions"],
        ["Position", "Player position in a formation", "Formation"],
        ["User", "Application user", "UserProfile"],
        ["UserProfile", "Extended user information", "User"],
    ]
    models_table = Table(models_data, colWidths=[1.3*inch, 2.2*inch, 2.5*inch])
    models_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(models_table)
    story.append(Spacer(1, 0.2*inch))
    
    story.append(Paragraph("Model Relationships Example:", heading2_style))
    story.append(Paragraph(
        "A Team has many Players (one-to-many relationship). "
        "A Match involves two Teams (many-to-many through a foreign key). "
        "A Player appears in Matches through MatchAppearance (many-to-many with additional data).", normal_style))
    story.append(Spacer(1, 0.2*inch))
    
    # 5. Key Features
    story.append(PageBreak())
    story.append(Paragraph("5. Key Features", heading1_style))
    story.append(Spacer(1, 0.1*inch))
    
    features_data = [
        ["Feature", "Description"],
        ["Team Management", "Create and edit teams, assign players to teams"],
        ["Player Management", "Track player information, skills, and statistics"],
        ["Match Management", "Schedule matches, record results, and track statistics"],
        ["Formation Builder", "Create and edit team formations with different team sizes (5er, 7er, 9er, 11er)"],
        ["Match Session", "Real-time match tracking with player substitutions and timer"],
        ["Statistics Dashboard", "Visual display of player and team statistics"],
        ["Player Matrix", "Visualization showing which players have played together"],
        ["Multi-language Support", "Support for English and Norwegian languages"],
        ["User Authentication", "Role-based access control (Admin, Coach, Player)"],
    ]
    features_table = Table(features_data, colWidths=[2*inch, 4*inch])
    features_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(features_table)
    story.append(Spacer(1, 0.2*inch))
    
    # 6. Technical Implementation Details
    story.append(PageBreak())
    story.append(Paragraph("6. Technical Implementation Details", heading1_style))
    story.append(Spacer(1, 0.1*inch))
    
    # Match Timer Logic
    story.append(Paragraph("Match Timer Implementation", heading2_style))
    story.append(Paragraph(
        "The match timer is implemented using JavaScript for client-side counting and AJAX "
        "for synchronization with the server. The timer state is persisted in the database "
        "to allow resuming matches after page reloads.", normal_style))
    story.append(Spacer(1, 0.1*inch))
    
    story.append(Paragraph("Client-side Timer Code Example:", normal_style))
    timer_code = """
// Match Timer JavaScript
let matchTimer;
let elapsedSeconds = 0;
let elapsedSecondsPreviousPeriods = 0;
let isRunning = false;

function startTimer() {
    isRunning = true;
    matchTimer = setInterval(function() {
        elapsedSeconds++;
        updateTimerDisplay();
        
        // Sync with server every 5 seconds
        if (elapsedSeconds % 5 === 0) {
            syncTimerWithServer();
        }
    }, 1000);
}

function stopTimer() {
    isRunning = false;
    clearInterval(matchTimer);
    syncTimerWithServer();
}
"""
    story.append(Paragraph(timer_code, code_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Authentication System
    story.append(Paragraph("Authentication System", heading2_style))
    story.append(Paragraph(
        "The application uses Django's built-in authentication system with customizations "
        "for role-based access control. Users can have Admin, Coach, or Player roles, each "
        "with different permissions.", normal_style))
    story.append(Spacer(1, 0.2*inch))
    
    # 7. Code Execution Flow
    story.append(PageBreak())
    story.append(Paragraph("7. Code Execution Flow", heading1_style))
    story.append(Spacer(1, 0.1*inch))
    
    story.append(Paragraph("Match Session Flow", heading2_style))
    story.append(Paragraph(
        "1. User creates a new match session or opens an existing one", normal_style))
    story.append(Paragraph(
        "2. Server loads match data and player assignments", normal_style))
    story.append(Paragraph(
        "3. Client initializes the match view with pitch visualization", normal_style))
    story.append(Paragraph(
        "4. User starts the match timer", normal_style))
    story.append(Paragraph(
        "5. Client-side JavaScript updates the timer and player statuses", normal_style))
    story.append(Paragraph(
        "6. Periodic AJAX requests sync data with the server", normal_style))
    story.append(Paragraph(
        "7. User makes substitutions by dragging players between active and bench areas", normal_style))
    story.append(Paragraph(
        "8. Server records player participation times", normal_style))
    story.append(Paragraph(
        "9. User ends the match, and final statistics are saved", normal_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Build the PDF
    doc.build(story)
    
    print(f"PDF documentation created at: {output_path}")

if __name__ == "__main__":
    # Define output path
    output_path = "SmorasFotball_Technical_Documentation.pdf"
    create_pdf_documentation(output_path)