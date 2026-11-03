var map = L.map('map').setView([45.05, 7.68], 12);

L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 20,
    attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
}).addTo(map);

// Glyph comes from Ionicons, which about.html loads
var officeIcon = L.AwesomeMarkers.icon({
    icon: 'email',
    prefix: 'ion',
    iconColor: 'white',
    markerColor: 'darkpurple'
});

L.marker([45.0524, 7.6814], { icon: officeIcon })
    .addTo(map)
    .bindPopup("Via Pietro Giuria 1, Torino, Italy")
    .openPopup();
