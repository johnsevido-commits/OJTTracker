import math

def haversine_meters(lat1, lon1, lat2, lon2):
    """Great-circle distance between two latitude/longitude pairs in meters."""
    radius = 6371000
    p1, p2 = math.radians(float(lat1)), math.radians(float(lat2))
    dp = math.radians(float(lat2) - float(lat1))
    dl = math.radians(float(lon2) - float(lon1))
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def validate_coordinates(payload, max_accuracy=100):
    try:
        lat = float(payload["latitude"])
        lon = float(payload["longitude"])
        accuracy = float(payload["accuracy"])
    except (KeyError, TypeError, ValueError):
        return None, "Location data is missing or invalid."
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None, "GPS coordinates are outside the valid range."
    if accuracy < 0:
        return None, "GPS accuracy cannot be negative."
    if accuracy > float(max_accuracy):
        return None, f"GPS accuracy is {accuracy:.0f} m. Please retry in a place with a better signal."
    return {"latitude": lat, "longitude": lon, "accuracy": accuracy}, None
