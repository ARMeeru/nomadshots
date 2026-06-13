"""Adapter isolating all exiftool subprocess interactions."""
import json
import subprocess
import tempfile
from pathlib import Path


class ExiftoolError(Exception):
    """Raised when exiftool invocation fails."""


class ExiftoolNotFoundError(ExiftoolError):
    """Raised when exiftool is not installed."""


def check_exiftool_available() -> None:
    """Verify exiftool is installed. Raises ExiftoolNotFoundError if not found,
    ExiftoolError if installed but failing."""
    try:
        subprocess.run(
            ["exiftool", "-ver"],
            capture_output=True,
            check=True,
        )
    except FileNotFoundError as e:
        raise ExiftoolNotFoundError(
            "exiftool not found — install with: brew install exiftool"
        ) from e
    except subprocess.CalledProcessError as e:
        raise ExiftoolError(
            f"exiftool is installed but failed to run: {e.stderr!r}"
        ) from e


def read_metadata_batch(paths: list[Path]) -> list[dict]:
    """Read metadata from multiple files in a single exiftool invocation.

    Uses -G flag for grouped keys (e.g. EXIF:GPSLatitude, XMP-dc:Creator).
    Uses argfile (-@) for efficient batch processing.
    """
    if not paths:
        return []

    # Validate all paths are resolved and exist
    for p in paths:
        if not p.is_absolute():
            raise ExiftoolError(f"Path must be absolute/resolved: {p}")
        if not p.exists():
            raise ExiftoolError(f"File does not exist: {p}")

    # Write paths to a temporary argfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        argfile_path = f.name
        for p in paths:
            f.write(f"{p}\n")

    try:
        try:
            result = subprocess.run(
                ["exiftool", "-G", "-json", "-n", "-@", argfile_path],
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as e:
            raise ExiftoolNotFoundError(
                "exiftool not found — install with: brew install exiftool"
            ) from e

        if result.returncode != 0 and not result.stdout:
            raise ExiftoolError(
                f"exiftool failed (code {result.returncode}): {result.stderr.strip()}"
            )

        # exiftool may return partial results (some files errored)
        # Parse whatever JSON it produced
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise ExiftoolError(f"Failed to parse exiftool output: {e}")

        return data
    finally:
        Path(argfile_path).unlink(missing_ok=True)


def read_metadata(path: Path) -> dict:
    """Read metadata from a single file. Thin wrapper around batch."""
    results = read_metadata_batch([path])
    if not results:
        raise ExiftoolError(f"No metadata returned for: {path}")
    return results[0]
