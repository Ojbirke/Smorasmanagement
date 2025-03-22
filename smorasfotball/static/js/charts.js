/**
 * Charts.js - Utility functions for Chart.js visualizations
 * Smørås Fotball Team Management System
 */

// Common chart colors
const chartColors = {
    primary: 'rgba(13, 110, 253, 0.7)',
    success: 'rgba(25, 135, 84, 0.7)',
    info: 'rgba(13, 202, 240, 0.7)',
    warning: 'rgba(255, 193, 7, 0.7)',
    danger: 'rgba(220, 53, 69, 0.7)',
    secondary: 'rgba(108, 117, 125, 0.7)',
    light: 'rgba(248, 249, 250, 0.7)',
    dark: 'rgba(33, 37, 41, 0.7)',
    borderColors: {
        primary: 'rgb(13, 110, 253)',
        success: 'rgb(25, 135, 84)',
        info: 'rgb(13, 202, 240)',
        warning: 'rgb(255, 193, 7)',
        danger: 'rgb(220, 53, 69)',
        secondary: 'rgb(108, 117, 125)',
        light: 'rgb(248, 249, 250)',
        dark: 'rgb(33, 37, 41)'
    }
};

/**
 * Creates a bar chart comparing team performances (wins, draws, losses)
 * @param {string} elementId - The ID of the canvas element
 * @param {Object} data - The data for the chart
 */
function createTeamPerformanceChart(elementId, data) {
    const ctx = document.getElementById(elementId).getContext('2d');
    
    const teams = data.map(item => item.team);
    const wins = data.map(item => item.wins);
    const draws = data.map(item => item.draws);
    const losses = data.map(item => item.losses);
    
    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: teams,
            datasets: [
                {
                    label: 'Wins',
                    data: wins,
                    backgroundColor: chartColors.success
                },
                {
                    label: 'Draws',
                    data: draws,
                    backgroundColor: chartColors.secondary
                },
                {
                    label: 'Losses',
                    data: losses,
                    backgroundColor: chartColors.danger
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                x: {
                    stacked: true,
                },
                y: {
                    stacked: true,
                    beginAtZero: true,
                    ticks: {
                        precision: 0
                    }
                }
            }
        }
    });
}

/**
 * Creates a bar chart for player statistics (goals, assists)
 * @param {string} elementId - The ID of the canvas element
 * @param {Object} data - The data for the chart
 */
function createPlayerStatsChart(elementId, data) {
    const ctx = document.getElementById(elementId).getContext('2d');
    
    // Sort players by total goals
    data.sort((a, b) => (b.total_goals || 0) - (a.total_goals || 0));
    const topPlayers = data.slice(0, 5);
    
    const playerNames = topPlayers.map(player => 
        player.first_name + (player.last_name ? ' ' + player.last_name : '')
    );
    const goals = topPlayers.map(player => player.total_goals || 0);
    const assists = topPlayers.map(player => player.total_assists || 0);
    
    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: playerNames,
            datasets: [
                {
                    label: 'Goals',
                    data: goals,
                    backgroundColor: chartColors.primary
                },
                {
                    label: 'Assists',
                    data: assists,
                    backgroundColor: chartColors.info
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0
                    }
                }
            }
        }
    });
}

/**
 * Creates a doughnut chart showing match types distribution
 * @param {string} elementId - The ID of the canvas element
 * @param {Object} data - The data for the chart with match types and counts
 */
function createMatchTypeChart(elementId, data) {
    const ctx = document.getElementById(elementId).getContext('2d');
    
    const labels = Object.keys(data);
    const values = Object.values(data);
    const backgroundColors = [
        chartColors.primary,
        chartColors.success,
        chartColors.info,
        chartColors.warning
    ];
    
    return new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: backgroundColors,
                borderColor: backgroundColors.map(color => color.replace('0.7', '1')),
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

/**
 * Creates a line chart for tracking match results over time
 * @param {string} elementId - The ID of the canvas element
 * @param {Object} data - The data with dates and results
 */
function createMatchResultsOverTimeChart(elementId, data) {
    const ctx = document.getElementById(elementId).getContext('2d');
    
    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.dates,
            datasets: [
                {
                    label: 'Wins',
                    data: data.wins,
                    borderColor: chartColors.borderColors.success,
                    backgroundColor: chartColors.success,
                    tension: 0.4,
                    fill: false
                },
                {
                    label: 'Draws',
                    data: data.draws,
                    borderColor: chartColors.borderColors.secondary,
                    backgroundColor: chartColors.secondary,
                    tension: 0.4,
                    fill: false
                },
                {
                    label: 'Losses',
                    data: data.losses,
                    borderColor: chartColors.borderColors.danger,
                    backgroundColor: chartColors.danger,
                    tension: 0.4,
                    fill: false
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0
                    }
                }
            }
        }
    });
}

/**
 * Creates a radar chart for player performance metrics
 * @param {string} elementId - The ID of the canvas element
 * @param {Object} player - The player data with performance metrics
 */
function createPlayerPerformanceRadarChart(elementId, player) {
    const ctx = document.getElementById(elementId).getContext('2d');
    
    return new Chart(ctx, {
        type: 'radar',
        data: {
            labels: ['Goals', 'Assists', 'Matches Played', 'Minutes', 'Cards'],
            datasets: [{
                label: player.name,
                data: [
                    player.goals,
                    player.assists,
                    player.matches,
                    player.minutes / 90, // Convert minutes to match equivalents
                    (player.yellow_cards + (player.red_cards * 2)) // Weight red cards higher
                ],
                backgroundColor: chartColors.primary,
                borderColor: chartColors.borderColors.primary,
                borderWidth: 2
            }]
        },
        options: {
            scales: {
                r: {
                    beginAtZero: true,
                    ticks: {
                        display: false
                    }
                }
            }
        }
    });
}
