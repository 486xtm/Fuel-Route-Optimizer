// Theme Management
const themeToggle = document.getElementById('themeToggle');
const themeIcon = document.getElementById('themeIcon');
const html = document.documentElement;

// Check for saved theme preference or default to light mode
const currentTheme = localStorage.getItem('theme') || 'light';
if (currentTheme === 'dark') {
    html.classList.add('dark');
    themeIcon.textContent = '🌙';
} else {
    html.classList.remove('dark');
    themeIcon.textContent = '☀️';
}

// Theme toggle handler
themeToggle.addEventListener('click', () => {
    html.classList.toggle('dark');

    if (html.classList.contains('dark')) {
        localStorage.setItem('theme', 'dark');
        themeIcon.textContent = '🌙';
        // Update map tiles for dark mode
        updateMapTiles('dark');
    } else {
        localStorage.setItem('theme', 'light');
        themeIcon.textContent = '☀️';
        // Update map tiles for light mode
        updateMapTiles('light');
    }
});

// Initialize map
let map = L.map('map').setView([39.8283, -98.5795], 4); // Center of USA

// Store tile layer reference
let tileLayer = null;

// Function to update map tiles based on theme
function updateMapTiles(theme) {
    if (tileLayer) {
        map.removeLayer(tileLayer);
    }

    if (theme === 'dark') {
        tileLayer = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
            attribution: '© OpenStreetMap contributors © CARTO',
            maxZoom: 19
        }).addTo(map);
    } else {
        tileLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 19
        }).addTo(map);
    }
}

// Initialize map tiles based on current theme
updateMapTiles(currentTheme);

// Store map layers
let routeLayer = null;
let markersLayer = L.layerGroup().addTo(map);

// Form submission
document.getElementById('routeForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const startLocation = document.getElementById('startLocation').value;
    const endLocation = document.getElementById('endLocation').value;
    const initialFuel = parseInt(document.getElementById('initialFuel').value);

    // Show loading
    document.getElementById('loading').classList.remove('hidden');
    document.getElementById('optimizeBtn').disabled = true;
    document.getElementById('error').classList.add('hidden');
    document.getElementById('results').classList.add('hidden');

    try {
        const response = await fetch('/api/optimize-route/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                start_location: startLocation,
                end_location: endLocation,
                initial_fuel_miles: initialFuel
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Failed to optimize route');
        }

        // Display results
        displayResults(data);

    } catch (error) {
        document.getElementById('error').textContent = error.message;
        document.getElementById('error').classList.remove('hidden');
    } finally {
        document.getElementById('loading').classList.add('hidden');
        document.getElementById('optimizeBtn').disabled = false;
    }
});

function displayResults(data) {
    // Update summary
    document.getElementById('totalDistance').textContent = `${data.total_distance_miles.toFixed(2)} mi`;
    document.getElementById('totalDuration').textContent = `${data.total_duration_hours.toFixed(1)} hrs`;
    document.getElementById('fuelStopsCount').textContent = data.fuel_stops.length;
    document.getElementById('totalCost').textContent = `$${data.total_fuel_cost.toFixed(2)}`;

    // Show results
    document.getElementById('results').classList.remove('hidden');

    // Clear existing layers
    if (routeLayer) {
        map.removeLayer(routeLayer);
    }
    markersLayer.clearLayers();

    // Draw route on map
    const routeCoords = data.route_geometry.map(coord => [coord[1], coord[0]]); // [lon, lat] to [lat, lon]
    routeLayer = L.polyline(routeCoords, {
        color: '#667eea',
        weight: 5,
        opacity: 0.8
    }).addTo(map);

    // Add start marker
    const startMarker = L.marker([data.start_coords.lat, data.start_coords.lon], {
        icon: L.divIcon({
            className: 'custom-marker',
            html: `<div style="background: linear-gradient(135deg, #10b981, #059669); color: white; padding: 10px 16px; border-radius: 24px; font-weight: 700; box-shadow: 0 4px 12px rgba(16, 185, 129, 0.4); border: 3px solid white;">🏁 Start</div>`,
            iconSize: [90, 45],
            iconAnchor: [45, 22]
        })
    }).addTo(markersLayer);

    startMarker.bindPopup(`
        <div class="font-bold text-lg text-green-600 mb-1">🏁 Starting Point</div>
        <div class="text-gray-700">${data.start_location}</div>
    `);

    // Add fuel stop markers
    data.fuel_stops.forEach((stop, index) => {
        const marker = L.marker([stop.coordinates.lat, stop.coordinates.lon], {
            icon: L.divIcon({
                className: 'custom-marker',
                html: `<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; width: 42px; height: 42px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 18px; box-shadow: 0 4px 12px rgba(102, 126, 234, 0.5); border: 4px solid white;">${index + 1}</div>`,
                iconSize: [42, 42],
                iconAnchor: [21, 21]
            })
        }).addTo(markersLayer);

        marker.bindPopup(`
            <div class="font-bold text-lg text-purple-600 mb-2">⛽ Stop ${stop.sequence}: ${stop.station_name}</div>
            <div class="space-y-1 text-sm">
                <div>📍 <span class="font-semibold">${stop.city}, ${stop.state}</span></div>
                <div>💰 <span class="font-semibold text-green-600">$${stop.price_per_gallon.toFixed(3)}/gal</span></div>
                <div>⛽ <span class="font-semibold">${stop.gallons.toFixed(1)} gallons</span></div>
                <div>💵 <span class="font-semibold">Cost: $${stop.cost.toFixed(2)}</span></div>
                <div>📏 <span class="font-semibold">${stop.distance_from_start.toFixed(1)} mi from start</span></div>
            </div>
        `);
    });

    // Add end marker
    const endMarker = L.marker([data.end_coords.lat, data.end_coords.lon], {
        icon: L.divIcon({
            className: 'custom-marker',
            html: `<div style="background: linear-gradient(135deg, #ef4444, #dc2626); color: white; padding: 10px 16px; border-radius: 24px; font-weight: 700; box-shadow: 0 4px 12px rgba(239, 68, 68, 0.4); border: 3px solid white;">🎯 End</div>`,
            iconSize: [90, 45],
            iconAnchor: [45, 22]
        })
    }).addTo(markersLayer);

    endMarker.bindPopup(`
        <div class="font-bold text-lg text-red-600 mb-1">🎯 Destination</div>
        <div class="text-gray-700">${data.end_location}</div>
    `);

    // Fit map to show entire route
    map.fitBounds(routeLayer.getBounds(), { padding: [50, 50] });

    // Display fuel stops list in sidebar
    displayFuelStops(data.fuel_stops);
}

function displayFuelStops(fuelStops) {
    const fuelStopsList = document.getElementById('fuelStopsList');
    fuelStopsList.innerHTML = '';

    if (fuelStops.length === 0) {
        fuelStopsList.classList.add('hidden');
        return;
    }

    // Show the fuel stops list
    fuelStopsList.classList.remove('hidden');

    // Add fuel stop cards
    fuelStops.forEach(stop => {
        const card = document.createElement('div');
        card.className = 'glass-effect rounded-xl shadow-lg p-5 hover:shadow-2xl hover:scale-105 transform transition-all duration-200 cursor-pointer';
        card.innerHTML = `
            <div class="flex items-start justify-between mb-3">
                <div class="flex items-center flex-1">
                    <div class="bg-gradient-to-br from-primary to-secondary text-white w-12 h-12 rounded-full flex items-center justify-center font-bold text-xl shadow-lg flex-shrink-0">
                        ${stop.sequence}
                    </div>
                    <div class="ml-3 flex-1 min-w-0">
                        <h4 class="font-bold text-gray-800 dark:text-gray-100 text-sm leading-tight truncate">${stop.station_name}</h4>
                        <p class="text-xs text-gray-600 dark:text-gray-400 mt-1">📍 ${stop.city}, ${stop.state}</p>
                    </div>
                </div>
            </div>
            <div class="space-y-2">
                <div class="flex justify-between items-center bg-gradient-to-r from-green-50 to-green-100 dark:from-green-900 dark:to-green-800 rounded-lg p-3 border-l-4 border-green-500">
                    <span class="text-xs text-green-700 dark:text-green-300 font-semibold">Price/Gallon</span>
                    <span class="text-lg font-bold text-green-900 dark:text-green-100">$${stop.price_per_gallon.toFixed(3)}</span>
                </div>
                <div class="grid grid-cols-2 gap-2">
                    <div class="bg-blue-50 dark:bg-blue-900 rounded-lg p-2 text-center">
                        <p class="text-xs text-blue-600 dark:text-blue-300 font-semibold">Distance</p>
                        <p class="text-sm font-bold text-blue-900 dark:text-blue-100">${stop.distance_from_start.toFixed(1)} mi</p>
                    </div>
                    <div class="bg-purple-50 dark:bg-purple-900 rounded-lg p-2 text-center">
                        <p class="text-xs text-purple-600 dark:text-purple-300 font-semibold">Gallons</p>
                        <p class="text-sm font-bold text-purple-900 dark:text-purple-100">${stop.gallons.toFixed(1)} gal</p>
                    </div>
                </div>
                <div class="bg-gradient-to-r from-yellow-50 to-yellow-100 dark:from-yellow-900 dark:to-yellow-800 rounded-lg p-3 border-l-4 border-yellow-500">
                    <div class="flex justify-between items-center">
                        <span class="text-xs text-yellow-700 dark:text-yellow-300 font-semibold">Total Cost</span>
                        <span class="text-xl font-bold text-yellow-900 dark:text-yellow-100">$${stop.cost.toFixed(2)}</span>
                    </div>
                </div>
            </div>
        `;
        fuelStopsList.appendChild(card);
    });
}
