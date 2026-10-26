(() => {
  let currentLocation = null;
  let map = null;
  let marker = null;
  const $ = id => document.getElementById(id);
  function setStatus(message, kind="neutral") {
    const el = $("gpsStatus");
    if (el) { el.textContent = message; el.className = `gps-status ${kind}`; }
  }
  function drawMap(lat, lon, accuracy) {
    const target = $("studentMap");
    if (!target || !window.L) return;
    if (!map) {
      target.innerHTML = "";
      map = L.map(target).setView([lat, lon], 17);
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19, attribution: "&copy; OpenStreetMap contributors"
      }).addTo(map);
    } else map.setView([lat, lon], 17);
    if (marker) marker.remove();
    marker = L.marker([lat, lon]).addTo(map).bindPopup(`Reported accuracy: ${Math.round(accuracy)} m`).openPopup();
    L.circle([lat, lon], {radius: accuracy, color: "#8b5cf6", fillOpacity: 0.08}).addTo(map);
    setTimeout(() => map.invalidateSize(), 100);
  }
  function getLocation() {
    if (!navigator.geolocation) {
      setStatus("This browser does not support location services.", "error");
      return;
    }
    setStatus("Requesting current location… keep the page open.", "neutral");
    const btn = $("getLocation");
    if (btn) { btn.disabled = true; btn.textContent = "Getting location…"; }
    navigator.geolocation.getCurrentPosition(position => {
      currentLocation = {
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
        accuracy: position.coords.accuracy
      };
      $("gpsLat").textContent = currentLocation.latitude.toFixed(6);
      $("gpsLon").textContent = currentLocation.longitude.toFixed(6);
      $("gpsAccuracy").textContent = `${Math.round(currentLocation.accuracy)} m`;
      setStatus("Location retrieved. Check the coordinates before recording attendance.", "success");
      drawMap(currentLocation.latitude, currentLocation.longitude, currentLocation.accuracy);
      document.dispatchEvent(new CustomEvent("ojttrack:location", {detail: currentLocation}));
      if (btn) { btn.disabled = false; btn.textContent = "↻ Refresh location"; }
    }, error => {
      const messages = {
        1: "Location permission was denied. Allow location access in your browser settings and retry.",
        2: "Your location is currently unavailable. Try moving near a window or enabling device location.",
        3: "Location request timed out. Please retry."
      };
      currentLocation = null;
      setStatus(messages[error.code] || "Could not retrieve your location.", "error");
      if (btn) { btn.disabled = false; btn.textContent = "↻ Retry location"; }
    }, {enableHighAccuracy:true, timeout:20000, maximumAge:0});
  }
  document.addEventListener("DOMContentLoaded", () => {
    const btn = $("getLocation");
    if (btn) btn.addEventListener("click", getLocation);
    document.addEventListener("ojttrack:request-location", () => {
      if (!currentLocation) {
        setStatus("First retrieve your current location, then submit attendance.", "error");
      } else {
        document.dispatchEvent(new CustomEvent("ojttrack:submit-attendance", {detail: currentLocation}));
      }
    });
    document.addEventListener("ojttrack:get-current-location", () => {
      if (currentLocation) document.dispatchEvent(new CustomEvent("ojttrack:submit-attendance", {detail: currentLocation}));
    });
  });
  window.OJTTrackGPS = {getCurrent: () => currentLocation};
})();
