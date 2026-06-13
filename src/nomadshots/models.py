"""Data models and constants for NomadShots metadata audit."""
from dataclasses import dataclass, field
from pathlib import Path

# Sensitive tags in grouped form (matching exiftool -G output)
SENSITIVE_TAGS: frozenset[str] = frozenset({
    "EXIF:SerialNumber",        # device serial
    "EXIF:LensSerialNumber",    # lens serial
    "EXIF:OwnerName",           # camera owner
    "EXIF:Software",            # software/OS version
    "EXIF:DateTimeOriginal",    # capture timestamp
    "EXIF:CreateDate",          # creation timestamp
    "EXIF:ModifyDate",          # modification timestamp
    "EXIF:SubSecDateTimeOriginal",  # sub-second timestamp
    "XMP:Creator",              # XMP creator tag
    "XMP-dc:Creator",           # Dublin Core creator
})


def is_sensitive_tag(key: str) -> bool:
    """Return True if key is in SENSITIVE_TAGS or if GPS appears in the key.

    GPS tags are matched by substring (case-sensitive) to catch all
    exiftool -G grouped GPS keys like EXIF:GPSLatitude, GPS:GPSLongitude, etc.
    """
    return key in SENSITIVE_TAGS or "GPS" in key


@dataclass
class FileAuditResult:
    """Audit result for a single image file."""
    filepath: Path
    has_gps: bool
    gps_coords: tuple[float, float] | None
    nearest_location: str | None
    device_make: str | None
    device_model: str | None
    capture_time: str | None
    sensitive_fields: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass
class AuditSummary:
    """Summary of an audit run over a folder."""
    total_files: int
    files_with_gps: int
    files_with_device_info: int
    file_errors: int
    results: list[FileAuditResult] = field(default_factory=list)


def format_headline(summary: "AuditSummary") -> str:
    """Format the audit headline string."""
    return f"{summary.files_with_gps} of {summary.total_files} photos contain GPS coordinates."
