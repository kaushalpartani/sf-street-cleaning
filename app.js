let map;
let currentGeoJSONLayer = null;
let allNeighborhoodsLayer = null;
let selectedNeighborhood = null;
let userLocationMarker = null;
let userLocation = null;


function initializeMap() {
    if (map) {
        map.remove(); // Remove the existing map completely
    }

    map = L.map('map').setView([37.7749, -122.4194], 12);

    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 20
    }).addTo(map);

    // Re-add all neighborhoods layer
    if (allNeighborhoodsLayer) {
        allNeighborhoodsLayer.addTo(map);
    }

    // Re-add user location marker if it exists
    if (userLocationMarker) {
        userLocationMarker.addTo(map);
    }
}

function loadNeighborhoodData(neighborhood) {
    // Check if the clicked neighborhood is already selected
    if (selectedNeighborhood && selectedNeighborhood.feature.properties.NeighborhoodName === neighborhood.properties.NeighborhoodName) {
        console.log('Neighborhood already selected:', neighborhood.properties.NeighborhoodName);
        return; // Exit the function if the neighborhood is already selected
    }

    initializeMap(); // Reinitialize the map

    const fileName = neighborhood.properties.FileName;

    if (!fileName) {
        console.error('FileName is missing for neighborhood:', neighborhood.properties.NeighborhoodName);
        alert('Error: Missing file name for this neighborhood');
        return;
    }

    const filePath = `https://raw.githubusercontent.com/kaushalpartani/sf-street-cleaning/refs/heads/main/data/neighborhoods/${fileName}.geojson`;

    loadGeoJSONFromFile(filePath);

    // Save selected neighborhood
    localStorage.setItem('lastNeighborhood', neighborhood.properties.NeighborhoodName);

    // Highlight selected neighborhood and hide its tooltip
    allNeighborhoodsLayer.eachLayer(layer => {
        if (layer.feature.properties.NeighborhoodName === neighborhood.properties.NeighborhoodName) {
            layer.setStyle({
                fillOpacity: 0.3,
                weight: 3
            });
            layer.unbindTooltip();
            selectedNeighborhood = layer;
        } else {
            layer.setStyle({
                fillOpacity: 0.1,
                weight: 2
            });
            if (!layer.getTooltip()) {
                layer.bindTooltip(layer.feature.properties.NeighborhoodName, {
                    permanent: false,
                    direction: 'center',
                    className: 'neighborhood-tooltip'
                });
            }
        }
    });

    // Fit map to neighborhood boundary
    map.fitBounds(L.geoJSON(neighborhood).getBounds());

    // Update search bar with selected neighborhood
    document.getElementById("neighborhood-search").value = neighborhood.properties.NeighborhoodName;
}

function loadGeoJSONFromFile(filePath) {
    fetch(filePath)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (!data) {
                throw new Error('GeoJSON data is null or undefined');
            }
            if (!data.features || !Array.isArray(data.features)) {
                throw new Error('GeoJSON data is missing features array');
            }
            if (data.features.length === 0) {
                throw new Error('GeoJSON features array is empty');
            }
            currentGeoJSONLayer = L.geoJSON(data, {
                style: function(feature) {
                    return {
                        color: "#1a237e",
                        weight: 5,
                        opacity: 0.65
                    };
                },
                onEachFeature: onEachFeature
            }).addTo(map);
        })
        .catch(error => {
            console.error('Error loading GeoJSON data:', error, 'for file:', filePath);
            alert(`Error loading neighborhood data: ${error.message}`);
        });
}

function loadAllNeighborhoods(data) {
    allNeighborhoodsLayer = L.geoJSON(data, {
        style: {
            color: "#ff7800",
            weight: 2,
            opacity: 0.65,
            fillOpacity: 0.1
        },
        onEachFeature: (feature, layer) => {
            layer.on('click', () => {
                loadNeighborhoodData(feature);
            });
            layer.bindTooltip(feature.properties.NeighborhoodName, {
                permanent: false,
                direction: 'center',
                className: 'neighborhood-tooltip'
            });
        }
    }).addTo(map);

    map.fitBounds(allNeighborhoodsLayer.getBounds());
}

function formatDateString(dateString) {
    if (!dateString || dateString === 'N/A') return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: 'numeric'
    });
}

function getRelevantCleaning(side) {
    const now = new Date();
    const nextCleaning = new Date(side.NextCleaning);
    const nextNextCleaning = new Date(side.NextNextCleaning);

    if (now < nextCleaning) {
        return {
            cleaning: side.NextCleaning || 'N/A',
            cleaningEnd: side.NextCleaningEnd || 'N/A',
            calendarLink: side.NextCleaningCalendarLink || '#'
        };
    } else {
        return {
            cleaning: side.NextNextCleaning || 'N/A',
            cleaningEnd: side.NextNextCleaningEnd || 'N/A',
            calendarLink: side.NextNextCleaningCalendarLink || '#'
        };
    }
}

function createSideInfo(sideName, sideData) {
    if (!sideData) return '';

    const relevantCleaning = getRelevantCleaning(sideData);
    const nextCleaning = formatDateString(relevantCleaning.cleaning);
    const nextCleaningEnd = formatDateString(relevantCleaning.cleaningEnd);

    return `
        <div class="side-info">
            <div class="side-title">${sideName || 'Street'} Side</div>
            <div class="cleaning-info"><strong>Next:</strong> ${nextCleaning}</div>
            <div class="cleaning-info"><strong>Until:</strong> ${nextCleaningEnd}</div>
            <a href="${relevantCleaning.calendarLink}" target="_blank" class="calendar-button">Add to Calendar</a>
        </div>
    `;
}

function onEachFeature(feature, layer) {
    if (feature.properties) {
        let popupContent = `
            <div class="popup-title">${feature.properties.StreetIdentifier || 'Street Information'}</div>
        `;

        if (feature.properties.Sides && typeof feature.properties.Sides === 'object') {
            for (const [sideName, sideData] of Object.entries(feature.properties.Sides)) {
                popupContent += createSideInfo(sideName, sideData);
            }
        } else {
            // Handle case where Sides is not an object or is missing
            popupContent += createSideInfo('', feature.properties);
        }

        layer.bindPopup(popupContent, {
            maxWidth: 250
        });

        // Add a wider invisible line for easier interaction
        const invisibleLine = L.polyline(layer.getLatLngs(), {
            color: 'transparent',
            weight: 20,
            opacity: 0
        }).addTo(map);

        invisibleLine.bindPopup(popupContent, {
            maxWidth: 250
        });
    }
}

function showUserLocation() {
    if (userLocation) {
        // If we already have the user's location, just refocus the map
        focusUserLocation();
    } else if ("geolocation" in navigator) {
        navigator.geolocation.getCurrentPosition(function(position) {
            userLocation = {
                lat: position.coords.latitude,
                lng: position.coords.longitude
            };
            addUserLocationMarker();
            focusUserLocation();
        }, function(error) {
            console.log("User denied geolocation");
        }, {
            enableHighAccuracy: true,
            timeout: 5000,
            maximumAge: 0
        });
    } else {
        console.log("Geolocation is not supported by this browser");
    }
}

function addUserLocationMarker() {
    // Remove existing marker if any
    if (userLocationMarker) {
        map.removeLayer(userLocationMarker);
    }

    // Create a custom icon for the user's location
    const userIcon = L.divIcon({
        className: 'user-location-icon',
        html: `<div class="user-location-dot"></div>`,
        iconSize: [20, 20],
        iconAnchor: [10, 10]
    });

    // Add marker to the map
    userLocationMarker = L.marker([userLocation.lat, userLocation.lng], {icon: userIcon}).addTo(map);
}

function focusUserLocation() {
    if (userLocation) {
        map.setView([userLocation.lat, userLocation.lng], 15);
    }
}

// Initial map setup
initializeMap();

// Load neighborhood data
fetch('https://raw.githubusercontent.com/kaushalpartani/sf-street-cleaning/refs/heads/main/data/neighborhoods.geojson')
    .then(response => response.json())
    .then(data => {
        const neighborhoods = data.features.map(feature => feature.properties.NeighborhoodName);
        new Awesomplete(document.getElementById("neighborhood-search"), {
            list: neighborhoods,
            minChars: 1,
            autoFirst: true
        });

        document.getElementById("neighborhood-search").addEventListener("awesomplete-selectcomplete", function(e) {
            const selectedNeighborhoodName = e.text.value;
            const neighborhood = data.features.find(feature => feature.properties.NeighborhoodName === selectedNeighborhoodName);
            if (neighborhood) {
                loadNeighborhoodData(neighborhood);
            }
        });

        loadAllNeighborhoods(data);

        // Load last selected neighborhood if exists
        const lastNeighborhood = localStorage.getItem('lastNeighborhood');
        if (lastNeighborhood) {
            const neighborhood = data.features.find(feature => feature.properties.NeighborhoodName === lastNeighborhood);
            if (neighborhood) {
                loadNeighborhoodData(neighborhood);
            }
        }
    })
    .catch(error => console.error('Error loading neighborhood data:', error));

// Menu functionality
const menuToggle = document.getElementById('menu-toggle');
const sidebar = document.getElementById('sidebar');
const mapContainer = document.getElementById('map-container');

menuToggle.addEventListener('click', function(e) {
    e.stopPropagation();
    sidebar.classList.toggle('open');
});

// Close sidebar when clicking outside
document.addEventListener('click', function(e) {
    if (!sidebar.contains(e.target) && !menuToggle.contains(e.target)) {
        sidebar.classList.remove('open');
    }
});

document.getElementById('about-option').addEventListener('click', function(e) {
    e.preventDefault();
    document.getElementById('about-modal').style.display = 'block';
    sidebar.classList.remove('open');
});

document.getElementById('disclaimer-option').addEventListener('click', function(e) {
    e.preventDefault();
    document.getElementById('disclaimer-modal').style.display = 'block';
    sidebar.classList.remove('open');
});

// Close modal functionality
var closeButtons = document.getElementsByClassName('close-button');
for (var i = 0; i < closeButtons.length; i++) {
    closeButtons[i].onclick = function() {
        this.parentElement.parentElement.style.display = 'none';
    }
}

// Close modal when clicking outside of it
window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.style.display = 'none';
    }
}

// Location button functionality
document.getElementById('location-button').addEventListener('click', showUserLocation);