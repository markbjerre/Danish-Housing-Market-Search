// Initialize state
let properties = [];
let filters = {
    minPrice: 0,
    maxPrice: 10000000,
    propertyType: '',
    minSize: 0,
    municipality: ''
};

// Initialize price range slider
const priceRange = document.getElementById('price-range');
noUiSlider.create(priceRange, {
    start: [0, 10000000],
    connect: true,
    range: {
        'min': 0,
        'max': 10000000
    },
    format: {
        to: value => Math.round(value),
        from: value => Math.round(value)
    }
});

// Update price display
priceRange.noUiSlider.on('update', (values) => {
    document.getElementById('price-min').textContent = `${values[0].toLocaleString()} kr`;
    document.getElementById('price-max').textContent = `${values[1].toLocaleString()} kr`;
    filters.minPrice = values[0];
    filters.maxPrice = values[1];
    loadProperties();
});

// Event listeners for filters
document.getElementById('min-size').addEventListener('change', (e) => {
    filters.minSize = e.target.value;
    loadProperties();
});

document.getElementById('property-type').addEventListener('change', (e) => {
    filters.propertyType = e.target.value;
    loadProperties();
});

document.getElementById('municipality').addEventListener('change', (e) => {
    filters.municipality = e.target.value;
    loadProperties();
});

// Load properties from API
async function loadProperties() {
    const container = document.getElementById('properties-container');
    container.classList.add('loading');
    
    try {
        const params = new URLSearchParams({
            min_price: filters.minPrice,
            max_price: filters.maxPrice,
            property_type: filters.propertyType,
            min_size: filters.minSize,
            municipality: filters.municipality
        });
        
        const response = await fetch(`/api/properties?${params}`);
        properties = await response.json();
        renderProperties();
    } catch (error) {
        console.error('Error loading properties:', error);
    } finally {
        container.classList.remove('loading');
    }
}

// Render properties grid
function renderProperties() {
    const container = document.getElementById('properties-container');
    
    // Update count badge
    document.getElementById('property-count').textContent = properties.length;
    
    if (properties.length === 0) {
        container.innerHTML = '<div class="col-12"><div class="alert alert-info">No properties found matching your filters.</div></div>';
        return;
    }
    
    container.innerHTML = properties.map(property => `
        <div class="col-md-6 col-lg-4">
            <div class="card property-card">
                <div class="card-body">
                    <h5 class="card-title">
                        ${property.address || 'No address'}
                        <a href="https://www.boligsiden.dk/addresses/${property.id}" target="_blank" class="ms-2" title="View on Boligsiden.dk">
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-box-arrow-up-right" viewBox="0 0 16 16">
                                <path fill-rule="evenodd" d="M8.636 3.5a.5.5 0 0 0-.5-.5H1.5A1.5 1.5 0 0 0 0 4.5v10A1.5 1.5 0 0 0 1.5 16h10a1.5 1.5 0 0 0 1.5-1.5V7.864a.5.5 0 0 0-1 0V14.5a.5.5 0 0 1-.5.5h-10a.5.5 0 0 1-.5-.5v-10a.5.5 0 0 1 .5-.5h6.636a.5.5 0 0 0 .5-.5z"/>
                                <path fill-rule="evenodd" d="M16 .5a.5.5 0 0 0-.5-.5h-5a.5.5 0 0 0 0 1h3.793L6.146 9.146a.5.5 0 1 0 .708.708L15 1.707V5.5a.5.5 0 0 0 1 0v-5z"/>
                            </svg>
                        </a>
                    </h5>
                    <p class="card-text">
                        <strong>Price:</strong> ${property.price ? property.price.toLocaleString() + ' kr' : 'N/A'}<br>
                        <strong>Size:</strong> ${property.square_meters ? property.square_meters + ' m²' : 'N/A'}<br>
                        <strong>Type:</strong> ${property.property_type || 'N/A'}<br>
                        <strong>Municipality:</strong> ${property.municipality || 'N/A'}<br>
                        ${property.rooms ? `<strong>Rooms:</strong> ${property.rooms}<br>` : ''}
                        ${property.year_built ? `<strong>Built:</strong> ${property.year_built}` : ''}
                    </p>
                    ${property.total_score > 0 ? `
                    <div class="scores">
                        <div class="d-flex justify-content-between">
                            <span>Total Score</span>
                            <span>${Math.round(property.total_score)}</span>
                        </div>
                        <div class="score-bar">
                            <div class="score-fill ${getScoreClass(property.total_score)}" 
                                 style="width: ${property.total_score}%"></div>
                        </div>
                        
                        <div class="mt-2 small">
                            <div>Price Score: ${Math.round(property.price_score)}</div>
                            <div>Size Score: ${Math.round(property.size_score)}</div>
                            <div>Location Score: ${Math.round(property.location_score)}</div>
                            <div>Age Score: ${Math.round(property.age_score)}</div>
                        </div>
                    </div>
                    ` : '<div class="text-muted small"><em>Score not yet calculated</em></div>'}
                </div>
            </div>
        </div>
    `).join('');
}

// Helper function for score colors
function getScoreClass(score) {
    if (score >= 80) return 'score-high';
    if (score >= 50) return 'score-medium';
    return 'score-low';
}

// Load initial data
async function initialize() {
    // Load municipalities
    const municipalitySelect = document.getElementById('municipality');
    const municipalities = await fetch('/api/municipalities').then(r => r.json());
    municipalities.forEach(municipality => {
        const option = document.createElement('option');
        option.value = municipality;
        option.textContent = municipality;
        municipalitySelect.appendChild(option);
    });
    
    // Load property types
    const propertyTypeSelect = document.getElementById('property-type');
    const propertyTypes = await fetch('/api/property-types').then(r => r.json());
    propertyTypes.forEach(type => {
        const option = document.createElement('option');
        option.value = type;
        option.textContent = type;
        propertyTypeSelect.appendChild(option);
    });
    
    // Load scoring weights
    const weights = await fetch('/api/scoring-weights').then(r => r.json());
    Object.entries(weights).forEach(([key, value]) => {
        const element = document.getElementById(`${key}-weight`);
        if (element) {
            element.value = value * 100;
        }
    });
    
    // Load initial properties
    await loadProperties();
}

// Update scoring weights
document.getElementById('update-weights').addEventListener('click', async () => {
    const weights = {};
    ['price', 'size', 'location', 'age'].forEach(key => {
        weights[`${key}_weight`] = document.getElementById(`${key}-weight`).value / 100;
    });
    
    try {
        await fetch('/api/scoring-weights', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(weights)
        });
        
        // Reload properties to get updated scores
        await loadProperties();
    } catch (error) {
        console.error('Error updating weights:', error);
    }
});

// Initialize the application
initialize();
