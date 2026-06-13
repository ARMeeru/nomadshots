"""Offline reverse geocoder using GeoNames cities15000 dataset.

Pure-Python haversine brute-force. No numpy, no scipy.
Lazy-loads on first call.
"""
import gzip
import math
from importlib import resources
from typing import NamedTuple


class City(NamedTuple):
    name: str
    country: str
    lat: float
    lon: float


_cities: tuple[City, ...] | None = None


def _load_cities() -> tuple[City, ...]:
    """Load cities from bundled gzipped GeoNames dataset."""
    global _cities
    if _cities is not None:
        return _cities

    cities = []
    # Use importlib.resources to find the data file inside the package
    data_ref = resources.files("nomadshots.data").joinpath("cities15000.txt.gz")
    with resources.as_file(data_ref) as data_path:
        with gzip.open(data_path, 'rt', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) < 9:
                    continue
                name = parts[2]  # asciiname
                lat = float(parts[4])
                lon = float(parts[5])
                country = parts[8]  # country code
                cities.append(City(name=name, country=country, lat=lat, lon=lon))

    _cities = tuple(cities)
    return _cities


def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate haversine distance in km between two points."""
    R = 6371.0  # Earth radius in km

    lat1_r = math.radians(lat1)
    lat2_r = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def reverse_geocode(lat: float, lon: float) -> str:
    """Find nearest city to given coordinates.

    Returns "CityName, CountryCode" string.
    Pure-Python brute-force search — no network calls.
    """
    cities = _load_cities()

    best_city: City | None = None
    best_distance = float('inf')

    for city in cities:
        dist = _haversine_distance(lat, lon, city.lat, city.lon)
        if dist < best_distance:
            best_distance = dist
            best_city = city

    if best_city is None:
        return "Unknown"

    return f"{best_city.name}, {best_city.country}"
