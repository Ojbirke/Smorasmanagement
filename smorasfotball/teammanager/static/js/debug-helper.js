/**
 * Debug Helper Functions for Smørås Fotball Application
 */

// Wait for DOM content to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('Debug helper loaded');
    
    // Fix for language dropdown
    fixLanguageDropdown();
});

// Function to fix the language dropdown display issues
function fixLanguageDropdown() {
    // Log the state of the language dropdown
    console.log('Fixing language dropdown');
    
    // Get the language dropdown toggle and menu
    const langDropdownToggle = document.querySelector('.navbar-nav .dropdown-toggle[data-bs-toggle="dropdown"]');
    const langDropdownMenu = document.querySelector('.navbar-nav .dropdown-menu');
    
    if (langDropdownToggle && langDropdownMenu) {
        console.log('Language dropdown elements found');
        console.log('- Toggle:', langDropdownToggle);
        console.log('- Menu:', langDropdownMenu);
        
        // Add a click event listener to ensure the dropdown works
        langDropdownToggle.addEventListener('click', function(e) {
            console.log('Language dropdown clicked');
            
            // Force the show class on the dropdown menu
            if (langDropdownMenu.classList.contains('show')) {
                console.log('Closing dropdown');
                langDropdownMenu.classList.remove('show');
            } else {
                console.log('Opening dropdown');
                langDropdownMenu.classList.add('show');
            }
        });
    } else {
        console.warn('Language dropdown elements not found');
    }
}

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
    outlineElement: outlineElement,
    fixLanguageDropdown: fixLanguageDropdown
};