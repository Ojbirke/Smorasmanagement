from flask import Flask, send_file

app = Flask(__name__)

@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Smørås Fotball Documentation</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                line-height: 1.5;
            }
            h1 {
                color: #2c3e50;
                border-bottom: 2px solid #3498db;
                padding-bottom: 10px;
            }
            .download-btn {
                display: inline-block;
                background-color: #3498db;
                color: white;
                padding: 10px 20px;
                text-decoration: none;
                border-radius: 5px;
                font-weight: bold;
                margin-top: 20px;
            }
            .download-btn:hover {
                background-color: #2980b9;
            }
            .content {
                background-color: #f8f9fa;
                padding: 20px;
                border-radius: 8px;
                margin: 20px 0;
            }
        </style>
    </head>
    <body>
        <h1>Smørås Fotball Technical Documentation</h1>
        
        <div class="content">
            <h2>About the Documentation</h2>
            <p>This technical documentation provides a comprehensive overview of the Smørås Fotball application.</p>
            
            <h3>Document Contents:</h3>
            <ul>
                <li><strong>Project Overview</strong>: Introduction to the application and its core functionality</li>
                <li><strong>Project Structure</strong>: Detailed description of the Django project organization</li>
                <li><strong>Key Technologies</strong>: Overview of the technologies used in the application</li>
                <li><strong>Database Schema</strong>: Explanation of all database models and their relationships</li>
                <li><strong>Key Features</strong>: Comprehensive list of application features</li>
                <li><strong>Technical Implementation Details</strong>: In-depth explanation of important technical components</li>
                <li><strong>Code Execution Flow</strong>: Step-by-step description of how key processes work</li>
            </ul>
        </div>
        
        <a href="/download" class="download-btn">Download PDF Documentation</a>
    </body>
    </html>
    '''

@app.route('/download')
def download():
    return send_file('SmorasFotball_Technical_Documentation.pdf', 
                     as_attachment=True,
                     download_name='SmorasFotball_Technical_Documentation.pdf')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)