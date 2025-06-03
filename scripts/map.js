var map = L.map('map').setView([45.05232742060916, 7.681427509114751], 20);

L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
}).addTo(map);

var redMarker = L.AwesomeMarkers.icon({
    icon: 'envelope',
    prefix: 'fa',
    iconColor: 'white',
    markerColor: 'darkpurple'
});

var marker = L.marker([45.05232742060916, 7.681427509114751], { icon: redMarker }).addTo(map);

var popup = L.popup()
    .setLatLng([45.0524072060916, 7.681427509114751])
    .setContent("Via Pietro Giuria 1, Torino, Italy")
    .openOn(map);
