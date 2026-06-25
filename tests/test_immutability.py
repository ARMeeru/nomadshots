"""Critical immutability test: original fixture files must never be modified.

This is the 'originals are read-only' test required by the AGENTS.md spec.
"""
import hashlib
from pathlib import Path

import pytest
from typer.testing import CliRunner

from nomadshots.audit import audit_folder
from nomadshots.cli import app

FIXTURES_DIR = Path(__file__).parent / "fixtures"
runner = CliRunner()


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _snapshot(directory: Path) -> dict[str, str]:
    """Record SHA256 of every file in directory."""
    return {
        f.name: _sha256(f)
        for f in sorted(directory.iterdir())
        if f.is_file()
    }


class TestFixtureImmutability:
    """Verify that running audit_folder never modifies any input file."""

    def test_audit_does_not_modify_fixtures(self):
        """All fixture checksums must be unchanged after an audit run."""
        checksums_before = _snapshot(FIXTURES_DIR)
        assert checksums_before, "Fixture directory must not be empty"

        # Run the full audit pipeline (errors are expected for corrupt.jpg)
        try:
            audit_folder(FIXTURES_DIR, recursive=False)
        except Exception:
            # Even if the audit raises, we still check immutability
            pass

        checksums_after = _snapshot(FIXTURES_DIR)

        # Assert every file present before is still present and unchanged
        for name, digest_before in checksums_before.items():
            assert name in checksums_after, (
                f"Fixture file was deleted or renamed: {name}"
            )
            assert checksums_after[name] == digest_before, (
                f"Fixture file was MODIFIED by audit pipeline: {name}\n"
                f"  Before: {digest_before}\n"
                f"  After:  {checksums_after[name]}"
            )

    def test_audit_recursive_does_not_modify_fixtures(self):
        """Recursive audit also must not modify any input file."""
        checksums_before = _snapshot(FIXTURES_DIR)

        try:
            audit_folder(FIXTURES_DIR, recursive=True)
        except Exception:
            pass

        checksums_after = _snapshot(FIXTURES_DIR)

        for name, digest_before in checksums_before.items():
            assert name in checksums_after, f"File deleted: {name}"
            assert checksums_after[name] == digest_before, (
                f"File modified: {name}"
            )

    def test_no_new_files_created_in_fixtures(self):
        """Audit must not create any new files inside the fixtures directory."""
        files_before = {f.name for f in FIXTURES_DIR.iterdir() if f.is_file()}

        try:
            audit_folder(FIXTURES_DIR, recursive=False)
        except Exception:
            pass

        files_after = {f.name for f in FIXTURES_DIR.iterdir() if f.is_file()}
        new_files = files_after - files_before
        assert not new_files, (
            f"Audit created unexpected files in fixtures dir: {new_files}"
        )


class TestCliImmutability:
    """Verify that CLI output handling cannot modify input files."""

    def test_cli_rejects_report_path_inside_input_folder(self, tmp_path):
        """The report path must not be allowed inside the audited input tree."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        source = input_dir / "minimal.jpg"
        source.write_bytes((FIXTURES_DIR / "minimal.jpg").read_bytes())
        digest_before = _sha256(source)

        result = runner.invoke(
            app,
            ["audit", str(input_dir), "--out", str(source)],
            catch_exceptions=False,
        )

        assert result.exit_code == 1
        assert "report output must be outside the audited folder" in result.output
        assert source.exists()
        assert _sha256(source) == digest_before

    def test_cli_does_not_create_report_inside_input_folder(self, tmp_path):
        """Rejecting an in-tree report path must not create a new input file."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        source = input_dir / "minimal.jpg"
        source.write_bytes((FIXTURES_DIR / "minimal.jpg").read_bytes())
        report = input_dir / "audit-report.md"

        result = runner.invoke(
            app,
            ["audit", str(input_dir), "--out", str(report)],
            catch_exceptions=False,
        )

        assert result.exit_code == 1
        assert not report.exists()
