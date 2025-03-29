/**
 * Debug Helper Functions for Smørås Fotball Application
 */

// Wait for DOM content to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('Debug helper loaded');
});

// Debug function to outline an element
function outlineElement(selector) {
    const elements = document.querySelectorAll(selector);
    elements.forEach(el => {
        el.classList.add('debug-outline');
        console.log('Outlined element:', el);
    });
}

// Export debug functions to global scope
window.debugHelper = {
    outlineElement: outlineElement
};