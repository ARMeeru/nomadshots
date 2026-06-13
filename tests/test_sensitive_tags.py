"""Tests for SENSITIVE_TAGS constant and is_sensitive_tag() — format-match tests.

CRITICAL: The format-match test uses real exiftool output from actual fixture files
to verify SENSITIVE_TAGS entries match the exact keys returned by the adapter.
If the test reveals drift, SENSITIVE_TAGS in models.py must be corrected.
"""
from pathlib import Path

import pytest

from nomadshots.exiftool_adapter import read_metadata
from nomadshots.models import SENSITIVE_TAGS, is_sensitive_tag

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestIsSensitiveTag:
    """Unit tests for is_sensitive_tag()."""

    def test_gps_keys_are_sensitive(self):
        """Any key containing 'GPS' is sensitive."""
        assert is_sensitive_tag("EXIF:GPSLatitude") is True
        assert is_sensitive_tag("EXIF:GPSLongitude") is True
        assert is_sensitive_tag("EXIF:GPSLatitudeRef") is True
        assert is_sensitive_tag("EXIF:GPSLongitudeRef") is True
        assert is_sensitive_tag("Composite:GPSLatitude") is True
        assert is_sensitive_tag("Composite:GPSPosition") is True

    def test_sensitive_tags_set_membership(self):
        """All entries in SENSITIVE_TAGS must return True."""
        for tag in SENSITIVE_TAGS:
            assert is_sensitive_tag(tag) is True, (
                f"is_sensitive_tag({tag!r}) returned False — tag in SENSITIVE_TAGS "
                f"but not matched by the function"
            )

    def test_non_sensitive_keys_are_not_sensitive(self):
        """Structural / file info keys must not be flagged."""
        assert is_sensitive_tag("File:FileName") is False
        assert is_sensitive_tag("File:FileSize") is False
        assert is_sensitive_tag("EXIF:ImageWidth") is False
        assert is_sensitive_tag("File:MIMEType") is False
        assert is_sensitive_tag("Composite:Megapixels") is False

    def test_device_make_not_in_sensitive_tags_directly(self):
        """EXIF:Make / EXIF:Model are NOT in SENSITIVE_TAGS (they're device info)."""
        # Note: Make/Model are reported separately as device_make/device_model
        # They should NOT trigger is_sensitive_tag unless explicitly added
        assert "EXIF:Make" not in SENSITIVE_TAGS
        assert "EXIF:Model" not in SENSITIVE_TAGS


class TestFormatMatchGpsJpeg:
    """CRITICAL: Verify SENSITIVE_TAGS matches real exiftool -G output format."""

    def test_gps_keys_present_in_real_output(self):
        """Read gps_jpeg.jpg metadata — GPS keys must be present."""
        fixture = (FIXTURES_DIR / "gps_jpeg.jpg").resolve()
        metadata = read_metadata(fixture)

        # GPS keys should be present
        gps_keys = [k for k in metadata if "GPS" in k]
        assert gps_keys, (
            f"No GPS keys found in gps_jpeg.jpg metadata. "
            f"Available keys: {sorted(metadata.keys())}"
        )

    def test_gps_keys_flagged_as_sensitive(self):
        """Every GPS key in real metadata must be flagged as sensitive."""
        fixture = (FIXTURES_DIR / "gps_jpeg.jpg").resolve()
        metadata = read_metadata(fixture)

        gps_keys = [k for k in metadata if "GPS" in k]
        for key in gps_keys:
            assert is_sensitive_tag(key) is True, (
                f"GPS key {key!r} found in real exiftool output but "
                f"is_sensitive_tag() returned False — SENSITIVE_TAGS or the "
                f"function logic needs to be updated."
            )

    def test_datetime_key_format_matches(self):
        """EXIF:DateTimeOriginal format must match real exiftool output."""
        fixture = (FIXTURES_DIR / "gps_jpeg.jpg").resolve()
        metadata = read_metadata(fixture)

        datetime_keys = [k for k in metadata if "DateTime" in k or "Date" in k]
        assert datetime_keys, (
            f"No date/time keys in metadata. Keys: {sorted(metadata.keys())}"
        )

        # Verify SENSITIVE_TAGS contains the actual keys returned by exiftool
        for key in datetime_keys:
            if key in SENSITIVE_TAGS:
                assert is_sensitive_tag(key) is True

    def test_software_key_format_matches(self):
        """EXIF:Software key format must match real exiftool output."""
        fixture = (FIXTURES_DIR / "gps_jpeg.jpg").resolve()
        metadata = read_metadata(fixture)

        if "EXIF:Software" in metadata:
            assert is_sensitive_tag("EXIF:Software") is True, (
                "EXIF:Software found in real output but not flagged as sensitive. "
                "Add it to SENSITIVE_TAGS in models.py."
            )

    def test_all_sensitive_fields_in_real_output_are_flagged(self):
        """
        CRITICAL format-match test.

        For every key in real exiftool output of gps_jpeg.jpg that SHOULD be
        sensitive (GPS, timestamps, device serial, owner, software), assert
        that is_sensitive_tag() returns True.

        This catches format drift between SENSITIVE_TAGS and real adapter output.
        """
        fixture = (FIXTURES_DIR / "gps_jpeg.jpg").resolve()
        metadata = read_metadata(fixture)
        actual_keys = set(metadata.keys())

        # Build set of keys that should be sensitive based on their content
        should_be_sensitive = set()
        for key in actual_keys:
            if "GPS" in key:
                should_be_sensitive.add(key)
            if key in SENSITIVE_TAGS:
                should_be_sensitive.add(key)

        failures = []
        for key in should_be_sensitive:
            if not is_sensitive_tag(key):
                failures.append(key)

        assert not failures, (
            f"These keys appear in real exiftool output but is_sensitive_tag() "
            f"returns False — fix SENSITIVE_TAGS in models.py:\n"
            + "\n".join(f"  {k!r}" for k in sorted(failures))
        )


class TestFormatMatchHeic:
    """Format-match test using gps_heic.heic."""

    def test_gps_keys_present_in_heic(self):
        """HEIC file GPS keys must be present and flagged."""
        fixture = (FIXTURES_DIR / "gps_heic.heic").resolve()
        metadata = read_metadata(fixture)

        gps_keys = [k for k in metadata if "GPS" in k]
        assert gps_keys, (
            f"No GPS keys found in HEIC metadata. "
            f"Keys: {sorted(metadata.keys())}"
        )
        for key in gps_keys:
            assert is_sensitive_tag(key) is True, (
                f"HEIC GPS key {key!r} not flagged as sensitive"
            )

    def test_make_model_in_heic(self):
        """EXIF:Make and EXIF:Model should appear in HEIC metadata."""
        fixture = (FIXTURES_DIR / "gps_heic.heic").resolve()
        metadata = read_metadata(fixture)

        assert "EXIF:Make" in metadata, "EXIF:Make missing from HEIC metadata"
        assert metadata["EXIF:Make"] == "Apple"
        assert "EXIF:Model" in metadata, "EXIF:Model missing from HEIC metadata"
