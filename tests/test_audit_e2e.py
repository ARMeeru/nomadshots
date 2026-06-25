"""End-to-end CLI tests for NomadShots audit command.

The Typer app exposes `audit` as a named subcommand,
so CliRunner must include "audit" as the first argument.
"""
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from nomadshots.cli import app

runner = CliRunner()

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _run_audit(folder: Path, out: Path, extra_flags: list[str] | None = None):
    """Helper: invoke the CLI audit command and return the result."""
    args = ["audit", str(folder)] + (extra_flags or []) + ["--out", str(out)]
    return runner.invoke(app, args, catch_exceptions=False)


class TestAuditGPSCount:
    """Audit fixtures/ should detect exactly 3 files with GPS."""

    def test_gps_headline_count(self, tmp_path):
        report = tmp_path / "report.md"
        result = _run_audit(FIXTURES_DIR, report)
        # 3 files have GPS: gps_jpeg.jpg, gps_heic.heic, GPS_UPPER.HEIC
        assert "3 of" in result.output, (
            f"Expected '3 of' in output. Got:\n{result.output}"
        )

    def test_uppercase_heic_counted(self, tmp_path):
        report = tmp_path / "report.md"
        result = _run_audit(FIXTURES_DIR, report)
        # GPS_UPPER.HEIC should be included in GPS count
        assert "3 of" in result.output


class TestReportFile:
    """Report output file tests."""

    def test_report_written_to_custom_path(self, tmp_path):
        report = tmp_path / "custom-report.md"
        _run_audit(FIXTURES_DIR, report)
        assert report.exists(), "Report file should be written"
        content = report.read_text()
        assert "NomadShots Audit Report" in content

    def test_report_contains_per_file_results(self, tmp_path):
        report = tmp_path / "report.md"
        _run_audit(FIXTURES_DIR, report)
        content = report.read_text()
        # The per-file table should include gps_jpeg.jpg
        assert "gps_jpeg.jpg" in content

    def test_out_flag_works(self, tmp_path):
        report = tmp_path / "test-report.md"
        result = _run_audit(FIXTURES_DIR, report)
        assert report.exists()
        assert str(report) in result.output


class TestRecursiveFlag:
    """--recursive flag tests."""

    def test_recursive_no_crash(self, tmp_path):
        """Recursive scan of fixtures dir should complete (exit 0 or 2)."""
        report = tmp_path / "report.md"
        result = runner.invoke(
            app,
            ["audit", "--recursive", str(FIXTURES_DIR), "--out", str(report)],
            catch_exceptions=False,
        )
        # Should complete (exit 0 or 2 — but not 1 which means exiftool missing)
        assert result.exit_code in (0, 2), (
            f"Expected exit 0 or 2, got {result.exit_code}. Output:\n{result.output}"
        )

    def test_recursive_with_subdir(self, tmp_path):
        """Recursive scan discovers files in subdirectories."""
        subdir = tmp_path / "nested"
        subdir.mkdir()
        shutil.copy(FIXTURES_DIR / "minimal.jpg", subdir / "minimal.jpg")

        report = tmp_path.parent / f"{tmp_path.name}-report.md"
        result = runner.invoke(
            app,
            ["audit", "--recursive", str(tmp_path), "--out", str(report)],
            catch_exceptions=False,
        )
        assert result.exit_code == 0, (
            f"Expected exit 0 for folder with only minimal.jpg. "
            f"Got {result.exit_code}. Output:\n{result.output}"
        )
        content = report.read_text()
        assert "minimal.jpg" in content


class TestCorruptFile:
    """Corrupt JPEG handling."""

    def test_corrupt_jpg_appears_in_report(self, tmp_path):
        """Corrupt file must appear in the report (with or without error)."""
        report = tmp_path / "report.md"
        _run_audit(FIXTURES_DIR, report)
        content = report.read_text()
        assert "corrupt.jpg" in content

    def test_exit_code_2_when_corrupt_present(self, tmp_path):
        """Exit code 2 when there are file errors."""
        # Create a folder with ONLY the corrupt file
        corrupt_dir = tmp_path / "only_corrupt"
        corrupt_dir.mkdir()
        shutil.copy(FIXTURES_DIR / "corrupt.jpg", corrupt_dir / "corrupt.jpg")

        report = tmp_path / "report.md"
        result = runner.invoke(
            app,
            ["audit", str(corrupt_dir), "--out", str(report)],
            catch_exceptions=False,
        )
        assert result.exit_code == 2, (
            f"Expected exit code 2 for corrupt-only folder. Got {result.exit_code}.\n"
            f"Output:\n{result.output}"
        )

    def test_corrupt_jpg_produces_error_in_report(self, tmp_path):
        """Corrupt-only folder: report must mention the error."""
        corrupt_dir = tmp_path / "only_corrupt"
        corrupt_dir.mkdir()
        shutil.copy(FIXTURES_DIR / "corrupt.jpg", corrupt_dir / "corrupt.jpg")

        report = tmp_path / "report.md"
        runner.invoke(
            app,
            ["audit", str(corrupt_dir), "--out", str(report)],
            catch_exceptions=False,
        )
        content = report.read_text()
        assert "corrupt.jpg" in content
        # The error column should not be "—" for a corrupt file
        assert "File format error" in content or "error" in content.lower()


class TestFullReportRow:
    """Assert that gps_jpeg.jpg produces a complete, correct report row."""

    def test_gps_jpeg_report_row(self, tmp_path):
        """gps_jpeg.jpg row must include device make/model, timestamp, location, sensitive tag."""
        report_path = tmp_path / "report.md"
        result = runner.invoke(
            app,
            ["audit", str(FIXTURES_DIR), "--out", str(report_path)],
            catch_exceptions=False,
        )
        assert result.exit_code in (0, 2), (
            f"Unexpected exit code {result.exit_code}.\nOutput:\n{result.output}"
        )
        assert report_path.exists(), "Report file was not created"
        content = report_path.read_text()

        # Find the row for gps_jpeg.jpg
        row = None
        for line in content.splitlines():
            if "gps_jpeg.jpg" in line:
                row = line
                break
        assert row is not None, "gps_jpeg.jpg row not found in report"

        # Device make/model (Apple and iPhone)
        assert "Apple" in row, f"Expected 'Apple' in row: {row}"
        assert "iPhone" in row, f"Expected 'iPhone' in row: {row}"

        # A timestamp (any digit sequence that looks like a date/time)
        import re
        assert re.search(r"\d{4}", row), f"Expected a year/timestamp in row: {row}"

        # A nearest location string (non-empty, non-dash location column)
        # The location column is the 3rd pipe-delimited field
        columns = [c.strip() for c in row.split("|")]
        # columns[0] = '', columns[1] = filename, columns[2] = GPS Yes/No,
        # columns[3] = location, columns[4] = device, ...
        assert len(columns) > 4, f"Row has unexpected format: {row}"
        location_col = columns[3]
        assert location_col != "—" and location_col != "", (
            f"Expected a city location, got: {location_col!r}"
        )

        # At least one sensitive tag name (GPS-related or timestamp)
        assert ("GPS" in row or "DateTimeOriginal" in row or "EXIF:" in row), (
            f"Expected at least one sensitive tag name in row: {row}"
        )


class TestCleanFolder:
    """Exit code 0 when no errors."""

    def test_exit_code_0_clean_folder(self, tmp_path):
        """Auditing only valid files gives exit code 0."""
        clean_dir = tmp_path / "clean"
        clean_dir.mkdir()
        for name in ("gps_jpeg.jpg", "no_gps.jpg", "minimal.jpg"):
            shutil.copy(FIXTURES_DIR / name, clean_dir / name)

        report = tmp_path / "report.md"
        result = runner.invoke(
            app,
            ["audit", str(clean_dir), "--out", str(report)],
            catch_exceptions=False,
        )
        assert result.exit_code == 0, (
            f"Expected exit code 0 for clean folder. Got {result.exit_code}.\n"
            f"Output:\n{result.output}"
        )

    def test_full_fixtures_exits_with_2(self, tmp_path):
        """Full fixtures folder has corrupt.jpg so should exit with 2."""
        report = tmp_path / "report.md"
        result = _run_audit(FIXTURES_DIR, report)
        assert result.exit_code == 2, (
            f"Expected exit 2 (corrupt.jpg). Got {result.exit_code}.\n"
            f"Output:\n{result.output}"
        )
