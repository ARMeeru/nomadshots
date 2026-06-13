"""Tests for the exiftool_adapter module."""
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from nomadshots.exiftool_adapter import (
    ExiftoolError,
    ExiftoolNotFoundError,
    check_exiftool_available,
    read_metadata,
    read_metadata_batch,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestReadMetadataBatch:
    """Tests for read_metadata_batch()."""

    def test_uses_argument_list_not_shell(self):
        """Subprocess must be called with argument list, never shell=True."""
        fixture = FIXTURES_DIR / "minimal.jpg"
        with patch("nomadshots.exiftool_adapter.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout='[{"SourceFile": "' + str(fixture) + '"}]',
                stderr="",
            )
            read_metadata_batch([fixture])

            mock_run.assert_called_once()
            call_args = mock_run.call_args
            # First positional arg is the command list
            cmd = call_args[0][0]
            assert isinstance(cmd, list), "Command must be a list, not a string"
            assert cmd[0] == "exiftool"

    def test_no_shell_true(self):
        """shell=True must never be passed."""
        fixture = FIXTURES_DIR / "minimal.jpg"
        with patch("nomadshots.exiftool_adapter.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout='[{"SourceFile": "' + str(fixture) + '"}]',
                stderr="",
            )
            read_metadata_batch([fixture])

            call_kwargs = mock_run.call_args[1]
            assert call_kwargs.get("shell") is not True, "shell=True must never be used"

    def test_uses_G_json_n_flags(self):
        """Command must include -G, -json, -n flags and argfile via -@."""
        fixture = FIXTURES_DIR / "minimal.jpg"
        with patch("nomadshots.exiftool_adapter.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout='[{"SourceFile": "' + str(fixture) + '"}]',
                stderr="",
            )
            read_metadata_batch([fixture])

            cmd = mock_run.call_args[0][0]
            assert "exiftool" in cmd
            assert "-G" in cmd
            assert "-json" in cmd
            assert "-n" in cmd
            assert "-@" in cmd

    def test_relative_path_raises_exiftool_error(self):
        """Relative paths must raise ExiftoolError."""
        relative = Path("tests/fixtures/minimal.jpg")
        with pytest.raises(ExiftoolError, match="absolute"):
            read_metadata_batch([relative])

    def test_nonexistent_path_raises_exiftool_error(self):
        """Non-existent files must raise ExiftoolError."""
        nonexistent = Path("/tmp/does_not_exist_nomadshots_12345.jpg")
        with pytest.raises(ExiftoolError):
            read_metadata_batch([nonexistent])

    def test_empty_list_returns_empty(self):
        """Empty input returns empty list without calling exiftool."""
        with patch("nomadshots.exiftool_adapter.subprocess.run") as mock_run:
            result = read_metadata_batch([])
            assert result == []
            mock_run.assert_not_called()

    def test_real_batch_read(self):
        """Integration: actually reads metadata from a real fixture."""
        fixture = (FIXTURES_DIR / "gps_jpeg.jpg").resolve()
        result = read_metadata_batch([fixture])
        assert len(result) == 1
        data = result[0]
        assert "EXIF:Make" in data
        assert data["EXIF:Make"] == "Apple"


class TestCheckExiftoolAvailable:
    """Tests for check_exiftool_available()."""

    def test_raises_when_exiftool_missing(self):
        """ExiftoolNotFoundError raised when exiftool binary not found."""
        with patch(
            "nomadshots.exiftool_adapter.subprocess.run",
            side_effect=FileNotFoundError("No such file or directory: 'exiftool'"),
        ):
            with pytest.raises(ExiftoolNotFoundError):
                check_exiftool_available()

    def test_succeeds_with_real_exiftool(self):
        """Real exiftool installation — should not raise."""
        # This test requires exiftool to be installed on the system
        check_exiftool_available()  # Should not raise
