# Build NomadShots v0.1 — Audit Command

## Context

NomadShots is a privacy-first photo metadata tool. v0.1 ships the `audit` command which scans a photo folder and reports what sensitive metadata exists — giving users visibility before they share. This is standalone value before scrub/export are built.

## Project Structure

```
nomadshots/
├── pyproject.toml              # Project config, dependencies (pinned)
├── src/
│   └── nomadshots/
│       ├── __init__.py
│       ├── cli.py              # Typer CLI entry point
│       ├── audit.py            # Audit logic (orchestrates scanning)
│       ├── exiftool_adapter.py # Single adapter isolating exiftool subprocess calls
│       ├── geocoder.py         # Offline reverse geocoder (bundled dataset)
│       ├── models.py           # Data classes for audit results
│       └── report.py           # Markdown report generator
├── data/
│   └── cities15000.txt         # GeoNames cities dataset (bundled, offline)
├── tests/
│   ├── conftest.py             # Shared fixtures
│   ├── fixtures/               # Test images with known metadata
│   │   ├── gps_heic.heic      # HEIC with GPS + device info
│   │   ├── gps_jpeg.jpg       # JPEG with GPS + device info
│   │   ├── no_gps.jpg         # JPEG with no GPS
│   │   └── minimal.jpg        # Minimal JPEG (no EXIF at all)
│   ├── test_audit_e2e.py      # End-to-end CLI tests
│   ├── test_exiftool_adapter.py
│   ├── test_geocoder.py
│   └── test_immutability.py   # Assert fixture checksums unchanged after run
└── README.md                   # (not created — backlog)
```

## Task 1: Project Scaffolding + Dependencies

- Create `pyproject.toml` with pinned deps: `typer[all]`, `pytest`, `pytest-subprocess` (for mocking exiftool)
- Set up `src/nomadshots/__init__.py`, entry point `[project.scripts] nomadshots = "nomadshots.cli:app"`
- Python 3.11+ required

## Task 2: Exiftool Adapter Module

**File:** `src/nomadshots/exiftool_adapter.py`

- Single function: `read_metadata(file_path: Path) -> dict` — calls exiftool via `subprocess.run` with argument list (never shell=True)
- Validates file_path is resolved and within allowed directory (path traversal protection)
- Parses JSON output from `exiftool -json -n <file>`
- Raises clear errors on failure (fail loud)
- Type hints on all public functions

## Task 3: Offline Reverse Geocoder

**File:** `src/nomadshots/geocoder.py`

- Bundled dataset: GeoNames `cities15000.txt` (public domain, ~24k cities, ~2MB)
- Loads city data into a simple KD-tree or brute-force nearest-neighbor (use scipy.spatial.cKDTree or a pure-python approach to avoid heavy deps — decision: use a minimal pure-python haversine nearest-neighbor with numpy for the small dataset)
- Function: `reverse_geocode(lat: float, lon: float) -> str` returns nearest city + country
- No network calls — dataset shipped in `data/`
- Lazy-loads on first call

## Task 4: Data Models

**File:** `src/nomadshots/models.py`

- `@dataclass FileAuditResult`: filepath, has_gps, gps_coords (optional tuple), nearest_location (optional str), device_make, device_model, capture_time, sensitive_fields (list of field names found)
- `@dataclass AuditSummary`: total_files, files_with_gps, files_with_device_info, results list

## Task 5: Audit Logic

**File:** `src/nomadshots/audit.py`

- `audit_folder(folder: Path) -> AuditSummary`
- Scans for image files (`.heic`, `.jpeg`, `.jpg`, `.png`, `.tiff`)
- Validates folder path (resolved, exists, is directory)
- Calls exiftool adapter per file, builds FileAuditResult
- Performs reverse geocoding for files with GPS
- Never opens source files for writing
- GPS coordinates only appear in the audit report (per privacy rules), never in logs

## Task 6: Report Generator

**File:** `src/nomadshots/report.py`

- `generate_report(summary: AuditSummary, output_path: Path) -> None`
- Writes `audit-report.md` with: headline stat, per-file table (filename, GPS?, location, device, timestamp, sensitive fields)
- Terminal summary via typer echo (headline + counts)

## Task 7: CLI Entry Point

**File:** `src/nomadshots/cli.py`

- Typer app with `audit` command: `nomadshots audit <folder>`
- Validates folder exists
- Calls audit logic, generates report, prints summary
- Exit code 0 on success

## Task 8: Test Fixtures

**Directory:** `tests/fixtures/`

- Generate synthetic test images with known EXIF metadata using Pillow + piexif (in a fixture-generation script, not shipped)
- HEIC fixture: create a minimal HEIC with GPS and device tags (using pillow-heif for creation)
- JPEG fixtures: GPS+device, no-GPS, minimal
- Record SHA256 checksums of all fixtures in `tests/conftest.py`

## Task 9: Test Suite

- **`test_audit_e2e.py`**: Full CLI invocation via `typer.testing.CliRunner` against fixture folder; assert report content matches expected metadata; assert headline counts correct
- **`test_exiftool_adapter.py`**: Unit tests with mocked subprocess; assert argument list format (no shell); assert path validation rejects traversal
- **`test_geocoder.py`**: Known lat/lon → expected city name
- **`test_immutability.py`**: Run audit on fixtures folder, then assert all fixture SHA256 checksums unchanged (original-immutability requirement)

## Key Design Decisions

1. **Reverse geocoding**: Use GeoNames cities15000 dataset (public domain, ~24k entries). Pure-python nearest-neighbor with haversine distance — no scipy needed, keeps deps minimal.
2. **No Pillow in main code path**: exiftool handles all metadata reading (HEIC + JPEG). Pillow only used in test fixture generation.
3. **Subprocess safety**: All exiftool calls use `subprocess.run([...], shell=False)` with resolved Path objects.
4. **Privacy**: GPS coords printed only in the audit report output. Logs show filenames/counts only.

## Dependencies (pinned in pyproject.toml)

- `typer[all]` — CLI framework
- `exiftool` (system dependency, not pip) — metadata backend
- Dev deps: `pytest`, `pillow`, `piexif` (fixture generation only)

## Verification

1. `pip install -e .` in a venv
2. `pytest tests/ -v` — all tests pass
3. `nomadshots audit tests/fixtures/` — produces correct terminal output and `audit-report.md`
4. Confirm: no network calls (grep for requests/urllib/httpx in src/)
5. Confirm: no file writes to input directory (only output is the report in CWD or specified path)
6. Confirm: exiftool calls use argument lists (grep for shell=True — must find zero)
