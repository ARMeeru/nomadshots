# NomadShots

NomadShots is a local-first photo metadata audit tool for travel photos.
Version 0.1 ships the audit command: it scans a folder, reports privacy-sensitive metadata, and writes a Markdown report.

## Install

NomadShots requires Python 3.11+ and a local `exiftool` binary.

```bash
brew install exiftool
python -m pip install -e ".[dev]"
```

For a runtime-only install from a checkout:

```bash
python -m pip install -e .
```

## Audit Photos

```bash
nomadshots audit /path/to/photos
```

By default this writes `audit-report.md` in the current directory.
If the current directory is also the audited folder, pass `--out` with a path outside that folder.

Useful options:

```bash
nomadshots audit /path/to/photos --out /tmp/nomadshots-audit.md
nomadshots audit /path/to/photos --recursive --out /tmp/nomadshots-audit.md
```

The terminal output includes the headline count:

```text
X of Y photos contain GPS coordinates.
```

The Markdown report includes one row per image with GPS presence, nearest offline location, device make/model, capture timestamp, sensitive fields, and any per-file error.

Exit codes:

- `0`: audit completed without per-file errors.
- `1`: setup or input error, such as missing `exiftool` or invalid folder.
- `2`: audit completed, but one or more files had read/format errors.

## Privacy Guarantees

- Originals are read-only. The audit command never modifies, moves, renames, or deletes source images.
- Report output paths inside the audited folder are rejected to avoid overwriting source files.
- No network calls are used in the default code path.
- Reverse geocoding uses the bundled GeoNames `cities15000` dataset.
- GPS coordinates are not printed to terminal logs. They are only included in the user-requested audit report.
- `exiftool` is isolated behind the adapter module and is invoked with argument lists, not a shell command string.

## v0.1 Limits

This release is audit-only. It does not implement `scrub`, `export`, `scan`, metadata stripping, resize/format conversion, independent scrub verification, sidecar auditing, or Photos library integration.

## Release Checks

Run these before cutting a v0.1 release:

```bash
python -m pytest -q
nomadshots audit tests/fixtures --out /tmp/nomadshots-audit.md
rg -n "requests|urllib|httpx|socket|curl|wget" src
rg -n "shell=True" src
python -m pytest -q tests/test_package_data.py tests/test_immutability.py
```

Expected results:

- The full test suite passes.
- The fixture audit exits `2` because `tests/fixtures/corrupt.jpg` is intentionally corrupt.
- The network-import grep returns no production matches.
- The production `shell=True` grep returns no matches. Test files may mention `shell=True` in assertions.
- Package-data and library/CLI immutability tests pass.

If packaging changes, also build and install a local artifact in a clean environment, then rerun the package-data and CLI smoke checks.
