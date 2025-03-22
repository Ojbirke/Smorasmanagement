/**
 * Debug Helper - A simple script to debug the Smørås Fotball application
 */

// Log debug information when the page loads
document.addEventListener('DOMContentLoaded', function() {
    console.log('**** DEBUG HELPER ****');
    console.log('Page loaded at ' + new Date().toISOString());
    console.log('Current URL: ' + window.location.href);
    console.log('Page path: ' + window.location.pathname);
    
    // Log all script elements
    console.log('Scripts loaded on this page:');
    document.querySelectorAll('script').forEach((script, index) => {
        console.log(`Script ${index + 1}: ${script.src || 'Inline script'}`);
    });
    
    // Check if matrix.js is loaded
    const matrixScriptLoaded = Array.from(document.querySelectorAll('script')).some(
        script => script.src && script.src.includes('matrix.js')
    );
    console.log('matrix.js loaded: ' + matrixScriptLoaded);
    
    // Check for key elements
    console.log('Key elements:');
    const keyElements = [
        'matrixContainer', 
        'matrixLoading',
        'matrixContent',
        'playerMatrix',
        'noDataMessage'
    ];
    
    keyElements.forEach(elementId => {
        const element = document.getElementById(elementId);
        console.log(`Element #${elementId}: ${element ? 'Found' : 'Not found'}`);
        if (element) {
            console.log(`  - Display: ${window.getComputedStyle(element).display}`);
            console.log(`  - Visibility: ${window.getComputedStyle(element).visibility}`);
            console.log(`  - Classes: ${element.className}`);
        }
    });
    
    // Check if window.initPlayerMatrix exists
    console.log('initPlayerMatrix function exists: ' + (typeof window.initPlayerMatrix === 'function'));
    
    console.log('**** END DEBUG INFO ****');
});