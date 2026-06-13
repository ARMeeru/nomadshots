"""Smoke test: verify bundled data is discoverable via importlib.resources."""
from importlib import resources


def test_cities_dataset_is_bundled():
    """The cities dataset must be findable after pip install."""
    data_ref = resources.files("nomadshots.data").joinpath("cities15000.txt.gz")
    with resources.as_file(data_ref) as data_path:
        assert data_path.is_file(), f"cities15000.txt.gz not found at {data_path}"
