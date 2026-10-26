document.addEventListener("DOMContentLoaded", () => {
  const mapEl = document.getElementById("adminMap");
  if (!mapEl || !window.L) return;
  // Coordinates are displayed as links in the table below. No fake marker is added.
  const map = L.map(mapEl).setView([12.8797, 121.7740], 5);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19, attribution: "&copy; OpenStreetMap contributors"
  }).addTo(map);
  const rows = [...document.querySelectorAll("a[href*='openstreetmap.org/?mlat=']")];
  const points = [];
  rows.forEach(link => {
    try {
      const url = new URL(link.href);
      const lat = Number(url.searchParams.get("mlat"));
      const lon = Number(url.searchParams.get("mlon"));
      if (Number.isFinite(lat) && Number.isFinite(lon)) points.push([lat,lon,link.textContent.trim()]);
    } catch (_) {}
  });
  points.forEach(([lat,lon,label]) => L.marker([lat,lon]).addTo(map).bindPopup(label));
  if (points.length) {
    const group = L.featureGroup(points.map(p => L.marker([p[0],p[1]])));
    map.fitBounds(group.getBounds().pad(0.15));
  }
});
