/**
 * Score UI Components - Frontend display for property scoring
 *
 * Provides reusable components for displaying scores, badges, and personas
 */

// Score badge colors and labels
const SCORE_BADGES = {
    excellent: { min: 90, label: 'Excellent', color: '#2ecc71', bg: '#e8f8f5' },
    very_good: { min: 80, label: 'Very Good', color: '#27ae60', bg: '#e8f8f5' },
    good: { min: 70, label: 'Good Value', color: '#f39c12', bg: '#fef5e7' },
    fair: { min: 60, label: 'Fair', color: '#e67e22', bg: '#fdeae6' },
    poor: { min: 0, label: 'Below Average', color: '#e74c3c', bg: '#fadbd8' }
};

/**
 * Get badge info for a score
 */
function getScoreBadge(score) {
    for (const [key, badge] of Object.entries(SCORE_BADGES)) {
        if (score >= badge.min) {
            return { ...badge, key };
        }
    }
    return SCORE_BADGES.poor;
}

/**
 * Create HTML for score badge
 */
function createScoreBadgeHTML(score) {
    const badge = getScoreBadge(score);
    return `
        <div class="score-badge" style="background: ${badge.bg}; border-left: 4px solid ${badge.color};">
            <div class="score-badge-value" style="color: ${badge.color};">${score.toFixed(1)}</div>
            <div class="score-badge-label" style="color: ${badge.color};">${badge.label}</div>
        </div>
    `;
}

/**
 * Create HTML for persona selector dropdown
 */
async function createPersonaSelectorHTML() {
    try {
        const response = await fetch('/api/personas');
        const data = await response.json();

        if (!data.personas) return '';

        return `
            <div class="persona-selector">
                <label for="persona-select">📊 Scoring Persona:</label>
                <select id="persona-select" onchange="handlePersonaChange()">
                    ${data.personas.map(p => `
                        <option value="${p.id}">${p.name}</option>
                    `).join('')}
                </select>
                <div class="persona-description" id="persona-desc"></div>
            </div>
        `;
    } catch (e) {
        console.error('Error loading personas:', e);
        return '';
    }
}

/**
 * Update persona description when selection changes
 */
async function handlePersonaChange() {
    const selector = document.getElementById('persona-select');
    const personaId = selector.value;

    try {
        const response = await fetch('/api/personas');
        const data = await response.json();
        const persona = data.personas.find(p => p.id === personaId);

        if (persona) {
            const desc = document.getElementById('persona-desc');
            if (desc) {
                desc.textContent = persona.description;
                desc.style.display = 'block';
            }

            // Re-fetch scores with new persona
            refetchScoresWithNewPersona();
        }
    } catch (e) {
        console.error('Error updating persona:', e);
    }
}

/**
 * Create factor breakdown HTML
 */
function createFactorBreakdownHTML(factors) {
    if (!factors || Object.keys(factors).length === 0) {
        return '<p>No factor breakdown available</p>';
    }

    return `
        <div class="factor-breakdown">
            <h4>Factor Breakdown</h4>
            <div class="factors-grid">
                ${Object.entries(factors).map(([factorName, factor]) => `
                    <div class="factor-item">
                        <div class="factor-name">${factorName.replace(/_/g, ' ')}</div>
                        <div class="factor-score-bar">
                            <div class="factor-bar-bg">
                                <div class="factor-bar-fill" style="width: ${factor.score || 0}%;"></div>
                            </div>
                            <span class="factor-score-value">${(factor.score || 0).toFixed(0)}</span>
                        </div>
                        <div class="factor-weight">${((factor.weight || 0) * 100).toFixed(0)}% weight</div>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

/**
 * Create comparison info HTML
 */
function createComparisonHTML(score, municipality) {
    return `
        <div class="comparison-section">
            <h4>Score Interpretation</h4>
            <div class="comparison-item">
                <span class="comparison-label">Your Score:</span>
                <span class="comparison-value">${score.toFixed(1)} / 100</span>
            </div>
            <div class="comparison-item">
                <span class="comparison-label">Municipality:</span>
                <span class="comparison-value">${municipality || 'N/A'}</span>
            </div>
            ${score >= 85 ? `
                <div class="interpretation-box" style="background: #e8f8f5; border-left: 4px solid #2ecc71;">
                    <p>💡 This is an excellent property! It scores in the top tier across most factors.</p>
                </div>
            ` : score >= 75 ? `
                <div class="interpretation-box" style="background: #fef5e7; border-left: 4px solid #f39c12;">
                    <p>💡 This is a good property with solid fundamentals. Above average value.</p>
                </div>
            ` : score >= 60 ? `
                <div class="interpretation-box" style="background: #fdeae6; border-left: 4px solid #e67e22;">
                    <p>💡 This is a fair property. Has some strong factors but also some weaknesses.</p>
                </div>
            ` : `
                <div class="interpretation-box" style="background: #fadbd8; border-left: 4px solid #e74c3c;">
                    <p>💡 This property scores below average. Consider comparing with other options.</p>
                </div>
            `}
        </div>
    `;
}

/**
 * Add score badge to property card
 */
function addScoreToCard(cardElement, score) {
    if (!cardElement) return;

    const badge = getScoreBadge(score);

    // Create score badge overlay
    const scoreOverlay = document.createElement('div');
    scoreOverlay.className = 'score-overlay';
    scoreOverlay.innerHTML = `
        <div class="score-badge-overlay" style="background: ${badge.bg}; border: 2px solid ${badge.color};">
            <div style="font-size: 1.5em; font-weight: bold; color: ${badge.color};">${score.toFixed(1)}</div>
            <div style="font-size: 0.8em; color: ${badge.color}; margin-top: 3px;">${badge.label}</div>
        </div>
    `;

    // Add to card
    const imageContainer = cardElement.querySelector('.property-image-container');
    if (imageContainer) {
        imageContainer.appendChild(scoreOverlay);
    }
}

/**
 * Fetch and display score for a property card
 */
async function loadScoreForCard(cardElement, propertyId, persona = 'space_conscious') {
    try {
        const response = await fetch(`/api/property/${propertyId}/score?persona=${persona}`);
        const data = await response.json();

        if (data.success && data.score) {
            addScoreToCard(cardElement, data.score.composite_score);

            // Store score data on card for later access
            cardElement.dataset.score = data.score.composite_score;
            cardElement.dataset.scoreData = JSON.stringify(data);
        }
    } catch (e) {
        console.error(`Error loading score for property ${propertyId}:`, e);
    }
}

/**
 * Open detailed score modal
 */
async function openScoreModal(propertyId, persona = 'space_conscious') {
    try {
        const response = await fetch(`/api/property/${propertyId}/score?persona=${persona}`);
        const data = response.json();

        if (!data.success) {
            alert('Error loading score');
            return;
        }

        const modal = createScoreModal(data);
        document.body.appendChild(modal);

    } catch (e) {
        console.error('Error opening score modal:', e);
        alert('Error loading score details');
    }
}

/**
 * Create detailed score modal HTML
 */
function createScoreModal(data) {
    const modal = document.createElement('div');
    modal.className = 'score-modal-overlay';
    modal.onclick = (e) => {
        if (e.target === modal) modal.remove();
    };

    const content = `
        <div class="score-modal">
            <button class="modal-close" onclick="this.closest('.score-modal-overlay').remove()">✕</button>

            <div class="score-modal-header">
                <h2>${data.property.address}</h2>
                <p>${data.property.municipality}</p>
            </div>

            <div class="score-modal-body">
                <div class="score-display">
                    ${createScoreBadgeHTML(data.score.composite_score)}
                    <p class="score-interpretation">${data.score.interpretation}</p>
                </div>

                ${createFactorBreakdownHTML(data.score.factor_breakdown)}
                ${createComparisonHTML(data.score.composite_score, data.property.municipality)}
            </div>
        </div>
    `;

    modal.innerHTML = content;
    return modal;
}

/**
 * CSS styles for score components
 */
const SCORE_STYLES = `
    /* Score Badge Styles */
    .score-badge {
        padding: 12px;
        border-radius: 8px;
        text-align: center;
        margin: 10px 0;
        min-width: 120px;
    }

    .score-badge-value {
        font-size: 1.8em;
        font-weight: bold;
        line-height: 1;
    }

    .score-badge-label {
        font-size: 0.85em;
        margin-top: 5px;
    }

    .score-overlay {
        position: absolute;
        top: 10px;
        right: 10px;
        z-index: 10;
    }

    .score-badge-overlay {
        padding: 10px 12px;
        border-radius: 6px;
        backdrop-filter: blur(5px);
        min-width: 80px;
        text-align: center;
    }

    /* Persona Selector */
    .persona-selector {
        padding: 15px;
        background: #f9f9f9;
        border-radius: 8px;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        gap: 15px;
        flex-wrap: wrap;
    }

    .persona-selector label {
        font-weight: 600;
        color: #333;
    }

    .persona-selector select {
        padding: 8px 12px;
        border: 2px solid #667eea;
        border-radius: 6px;
        font-size: 1em;
        cursor: pointer;
        background: white;
        color: #333;
    }

    .persona-selector select:focus {
        outline: none;
        border-color: #764ba2;
    }

    .persona-description {
        flex: 1;
        min-width: 200px;
        font-size: 0.9em;
        color: #666;
        display: none;
        padding: 8px 12px;
        background: white;
        border-radius: 6px;
        border-left: 3px solid #667eea;
    }

    /* Factor Breakdown */
    .factor-breakdown {
        margin: 20px 0;
        padding: 15px;
        background: #f9f9f9;
        border-radius: 8px;
    }

    .factor-breakdown h4 {
        margin-bottom: 15px;
        color: #333;
    }

    .factors-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 12px;
    }

    .factor-item {
        padding: 10px;
        background: white;
        border-radius: 6px;
        border: 1px solid #e0e0e0;
    }

    .factor-name {
        font-size: 0.85em;
        font-weight: 600;
        color: #333;
        margin-bottom: 8px;
        text-transform: capitalize;
    }

    .factor-score-bar {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 6px;
    }

    .factor-bar-bg {
        flex: 1;
        height: 6px;
        background: #e0e0e0;
        border-radius: 3px;
        overflow: hidden;
    }

    .factor-bar-fill {
        height: 100%;
        background: linear-gradient(90deg, #667eea, #764ba2);
        transition: width 0.3s;
    }

    .factor-score-value {
        font-size: 0.9em;
        font-weight: bold;
        color: #667eea;
        min-width: 35px;
        text-align: right;
    }

    .factor-weight {
        font-size: 0.75em;
        color: #999;
    }

    /* Comparison Section */
    .comparison-section {
        padding: 15px;
        background: #f9f9f9;
        border-radius: 8px;
        margin-top: 20px;
    }

    .comparison-section h4 {
        margin-bottom: 12px;
        color: #333;
    }

    .comparison-item {
        display: flex;
        justify-content: space-between;
        padding: 8px 0;
        border-bottom: 1px solid #e0e0e0;
    }

    .comparison-item:last-child {
        border-bottom: none;
    }

    .comparison-label {
        font-weight: 600;
        color: #666;
    }

    .comparison-value {
        font-weight: 700;
        color: #667eea;
    }

    .interpretation-box {
        margin-top: 12px;
        padding: 12px;
        border-radius: 6px;
    }

    .interpretation-box p {
        margin: 0;
        font-size: 0.95em;
        line-height: 1.4;
    }

    /* Score Modal */
    .score-modal-overlay {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 1000;
        padding: 20px;
    }

    .score-modal {
        background: white;
        border-radius: 12px;
        max-width: 600px;
        width: 100%;
        max-height: 90vh;
        overflow-y: auto;
        position: relative;
    }

    .modal-close {
        position: absolute;
        top: 15px;
        right: 15px;
        background: none;
        border: none;
        font-size: 1.5em;
        cursor: pointer;
        color: #999;
        transition: color 0.2s;
    }

    .modal-close:hover {
        color: #333;
    }

    .score-modal-header {
        padding: 20px;
        border-bottom: 2px solid #f0f0f0;
    }

    .score-modal-header h2 {
        margin: 0 0 5px 0;
        color: #333;
        font-size: 1.3em;
    }

    .score-modal-header p {
        margin: 0;
        color: #999;
        font-size: 0.9em;
    }

    .score-modal-body {
        padding: 20px;
    }

    .score-display {
        text-align: center;
        margin-bottom: 20px;
    }

    .score-interpretation {
        margin-top: 15px;
        font-size: 1.05em;
        line-height: 1.5;
        color: #555;
    }
`;

// Inject styles when module loads
const styleSheet = document.createElement('style');
styleSheet.textContent = SCORE_STYLES;
document.head.appendChild(styleSheet);
