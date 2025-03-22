/**
 * Matrix.js - Functions for player matrix visualization
 * Smørås Fotball Team Management System
 */

/**
 * Fetches player matrix data for a specific team
 * @param {number} teamId - The ID of the team
 * @returns {Promise} - A promise with the matrix data
 */
function fetchPlayerMatrixData(teamId) {
    return fetch(`/team/api/player-stats/?team_id=${teamId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        });
}

/**
 * Calculates the color shade based on the value and maximum value
 * @param {number} value - The current value
 * @param {number} max - The maximum value
 * @returns {string} - A CSS color string
 */
function getColorShade(value, max) {
    if (value === 0) return '#f8f9fa';
    const intensity = Math.min(Math.max(value / max, 0.1), 1);
    return `rgba(13, 110, 253, ${intensity})`;
}

/**
 * Renders the player matrix on the page
 * @param {Object} data - The matrix data
 * @param {string} tableElementId - The ID of the table element
 */
function renderPlayerMatrix(data, tableElementId) {
    const playerMatrix = document.getElementById(tableElementId);
    const players = data.players;
    const matrix = data.matrix;
    const maxValue = data.max_value || 1;
    
    // Generate table HTML
    let tableHTML = '<thead><tr><th></th>';
    
    // Add header row with player names
    players.forEach(player => {
        tableHTML += `<th>${player.first_name}</th>`;
    });
    tableHTML += '</tr></thead><tbody>';
    
    // Add rows for each player
    players.forEach((player, rowIndex) => {
        tableHTML += `<tr><th>${player.first_name}</th>`;
        
        // Add cells for each player
        players.forEach((_, colIndex) => {
            const value = matrix[rowIndex][colIndex];
            const bgColor = getColorShade(value, maxValue);
            tableHTML += `<td style="background-color: ${bgColor};" title="${value} matches together">${value}</td>`;
        });
        
        tableHTML += '</tr>';
    });
    
    tableHTML += '</tbody>';
    playerMatrix.innerHTML = tableHTML;
}

/**
 * Initializes the player matrix functionality
 * @param {string} selectElementId - The ID of the team select element
 * @param {string} containerElementId - The ID of the matrix container element
 * @param {string} loadingElementId - The ID of the loading indicator element
 * @param {string} contentElementId - The ID of the content container element
 * @param {string} tableElementId - The ID of the table element
 * @param {string} noDataElementId - The ID of the no data message element
 * @param {string} titleElementId - The ID of the matrix title element
 */
function initPlayerMatrix(
    selectElementId, 
    containerElementId, 
    loadingElementId, 
    contentElementId, 
    tableElementId, 
    noDataElementId,
    titleElementId
) {
    const teamSelect = document.getElementById(selectElementId);
    const matrixContainer = document.getElementById(containerElementId);
    const matrixLoading = document.getElementById(loadingElementId);
    const matrixContent = document.getElementById(contentElementId);
    const noDataMessage = document.getElementById(noDataElementId);
    const matrixTitle = document.getElementById(titleElementId);
    
    if (!teamSelect) return;
    
    teamSelect.addEventListener('change', function() {
        const teamId = this.value;
        
        if (teamId === '') {
            matrixContainer.classList.add('d-none');
            noDataMessage.classList.add('d-none');
            return;
        }
        
        // Show matrix container and loading
        matrixContainer.classList.remove('d-none');
        matrixLoading.classList.remove('d-none');
        matrixContent.classList.add('d-none');
        noDataMessage.classList.add('d-none');
        
        // Get team name
        const teamName = teamSelect.options[teamSelect.selectedIndex].text;
        matrixTitle.textContent = `Player Matrix - ${teamName}`;
        
        // Fetch data and render matrix
        fetchPlayerMatrixData(teamId)
            .then(data => {
                if (!data.players || data.players.length === 0) {
                    matrixContainer.classList.add('d-none');
                    noDataMessage.classList.remove('d-none');
                    return;
                }
                
                renderPlayerMatrix(data, tableElementId);
                
                // Show matrix content
                matrixLoading.classList.add('d-none');
                matrixContent.classList.remove('d-none');
            })
            .catch(error => {
                console.error('Error fetching matrix data:', error);
                matrixContainer.classList.add('d-none');
                noDataMessage.classList.remove('d-none');
            });
    });
}

// Export functions for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        fetchPlayerMatrixData,
        getColorShade,
        renderPlayerMatrix,
        initPlayerMatrix
    };
}
