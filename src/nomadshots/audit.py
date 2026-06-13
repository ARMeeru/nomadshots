"""Audit orchestration — scans folders for image metadata."""
import logging
from pathlib import Path

from .exiftool_adapter import ExiftoolError, read_metadata_batch
from .geocoder import reverse_geocode
from .models import AuditSummary, FileAuditResult, is_sensitive_tag

logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = frozenset({".heic", ".jpg", ".jpeg", ".png", ".tiff", ".tif"})


def _discover_images(folder: Path, recursive: bool = False) -> list[Path]:
    """Find image files by extension (case-insensitive)."""
    images = []
    iterator = folder.rglob("*") if recursive else folder.iterdir()
    for item in iterator:
        if item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS:
            images.append(item.resolve())
    return sorted(images)


def _build_result(filepath: Path, metadata: dict) -> FileAuditResult:
    """Build a FileAuditResult from exiftool metadata dict."""
    # Check for GPS
    gps_lat = metadata.get("EXIF:GPSLatitude") or metadata.get("Composite:GPSLatitude")
    gps_lon = metadata.get("EXIF:GPSLongitude") or metadata.get("Composite:GPSLongitude")
    has_gps = gps_lat is not None and gps_lon is not None
    gps_coords = (float(gps_lat), float(gps_lon)) if has_gps else None

    # Reverse geocode if GPS present
    nearest_location = None
    if has_gps and gps_coords:
        try:
            nearest_location = reverse_geocode(gps_coords[0], gps_coords[1])
        except Exception:
            nearest_location = "Unknown"

    # Device info
    device_make = metadata.get("EXIF:Make")
    device_model = metadata.get("EXIF:Model")

    # Capture time
    capture_time = metadata.get("EXIF:DateTimeOriginal") or metadata.get("EXIF:CreateDate")
    if capture_time is not None:
        capture_time = str(capture_time)

    # Find all sensitive fields present
    sensitive_fields = [key for key in metadata.keys() if is_sensitive_tag(key)]

    return FileAuditResult(
        filepath=filepath,
        has_gps=has_gps,
        gps_coords=gps_coords,
        nearest_location=nearest_location,
        device_make=device_make,
        device_model=device_model,
        capture_time=capture_time,
        sensitive_fields=sensitive_fields,
        error=None,
    )


def audit_folder(folder: Path, recursive: bool = False) -> AuditSummary:
    """Audit all image files in a folder for sensitive metadata.

    Args:
        folder: Directory to scan (must exist, must be a directory).
        recursive: If True, scan subdirectories.

    Returns:
        AuditSummary with per-file results.
    """
    folder = folder.resolve()
    if not folder.exists():
        raise FileNotFoundError(f"Folder does not exist: {folder}")
    if not folder.is_dir():
        raise NotADirectoryError(f"Not a directory: {folder}")

    images = _discover_images(folder, recursive)
    # Log only filename counts, never GPS or metadata content
    logger.info("Found %d image files in %s", len(images), folder)

    results: list[FileAuditResult] = []

    if not images:
        return AuditSummary(
            total_files=0,
            files_with_gps=0,
            files_with_device_info=0,
            file_errors=0,
            results=[],
        )

    # Batch read metadata
    try:
        metadata_list = read_metadata_batch(images)
    except ExiftoolError:
        # If the entire batch fails, try one by one
        metadata_list = None

    if metadata_list is not None and len(metadata_list) == len(images):
        # Successful batch — process each
        for filepath, metadata in zip(images, metadata_list):
            try:
                # Detect exiftool-level file format errors
                exiftool_err = metadata.get("ExifTool:Error")
                if exiftool_err:
                    raise ExiftoolError(f"exiftool: {exiftool_err}")
                result = _build_result(filepath, metadata)
            except Exception as e:
                result = FileAuditResult(
                    filepath=filepath,
                    has_gps=False,
                    gps_coords=None,
                    nearest_location=None,
                    device_make=None,
                    device_model=None,
                    capture_time=None,
                    sensitive_fields=[],
                    error=str(e),
                )
            results.append(result)
    else:
        # Batch failed or returned wrong count — try individually
        from .exiftool_adapter import read_metadata
        for filepath in images:
            try:
                metadata = read_metadata(filepath)
                exiftool_err = metadata.get("ExifTool:Error")
                if exiftool_err:
                    raise ExiftoolError(f"exiftool: {exiftool_err}")
                result = _build_result(filepath, metadata)
            except Exception as e:
                result = FileAuditResult(
                    filepath=filepath,
                    has_gps=False,
                    gps_coords=None,
                    nearest_location=None,
                    device_make=None,
                    device_model=None,
                    capture_time=None,
                    sensitive_fields=[],
                    error=str(e),
                )
            results.append(result)

    files_with_gps = sum(1 for r in results if r.has_gps)
    files_with_device_info = sum(1 for r in results if r.device_make or r.device_model)
    file_errors = sum(1 for r in results if r.error is not None)

    return AuditSummary(
        total_files=len(results),
        files_with_gps=files_with_gps,
        files_with_device_info=files_with_device_info,
        file_errors=file_errors,
        results=results,
    )
