"""Tests for the offline reverse geocoder."""
import pytest

from nomadshots.geocoder import reverse_geocode


class TestReverseGeocode:
    """Test cases for reverse_geocode() using the bundled cities dataset."""

    def test_ho_chi_minh_city(self):
        """Coordinates in Ho Chi Minh City should return nearby city name."""
        result = reverse_geocode(10.7626, 106.6602)
        assert isinstance(result, str)
        assert len(result) > 0
        # Ho Chi Minh City or close alias — just check it's a non-empty string
        # with a country code appended
        assert "," in result  # "CityName, CountryCode" format

    def test_ho_chi_minh_contains_city_name(self):
        """Ho Chi Minh City coordinates — should return matching city."""
        result = reverse_geocode(10.7626, 106.6602)
        # The GeoNames dataset may have "Ho Chi Minh City" or "Thu Duc" nearby
        # Accept anything near HCMC; verify it's in Vietnam (VN) at minimum
        assert "VN" in result or "Ho Chi Minh" in result or "Thanh" in result, (
            f"Expected a Vietnamese city near HCMC, got: {result!r}"
        )

    def test_new_york(self):
        """New York City coordinates should return a city near NYC."""
        result = reverse_geocode(40.7128, -74.0060)
        assert isinstance(result, str)
        # Accept NYC or nearby NJ/NY city — should contain US country code
        assert "US" in result or "New York" in result, (
            f"Expected a US city near NYC, got: {result!r}"
        )

    def test_paris(self):
        """Paris coordinates should return a French city."""
        result = reverse_geocode(48.8566, 2.3522)
        assert isinstance(result, str)
        assert "FR" in result or "Paris" in result, (
            f"Expected a French city near Paris, got: {result!r}"
        )

    def test_returns_string_format(self):
        """Return format is 'CityName, CountryCode'."""
        result = reverse_geocode(10.7626, 106.6602)
        parts = result.split(", ")
        assert len(parts) == 2, f"Expected 'City, CC' format, got: {result!r}"
        assert len(parts[1]) == 2, f"Country code should be 2 chars: {parts[1]!r}"

    def test_poles_and_extremes(self):
        """Edge case: extreme coordinates should not crash."""
        result_north = reverse_geocode(90.0, 0.0)
        result_south = reverse_geocode(-90.0, 0.0)
        assert isinstance(result_north, str)
        assert isinstance(result_south, str)
