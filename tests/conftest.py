"""Shared pytest fixtures and baseline checksums for NomadShots tests."""
import hashlib
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _sha256(path: Path) -> str:
    """Return hex SHA256 digest of file contents."""
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def compute_fixture_checksums() -> dict[str, str]:
    """Compute SHA256 checksums for all fixture files dynamically."""
    checksums = {}
    for f in sorted(FIXTURES_DIR.iterdir()):
        if f.is_file():
            checksums[f.name] = _sha256(f)
    return checksums


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    """Return the path to the test fixtures directory."""
    assert FIXTURES_DIR.exists(), f"Fixtures directory missing: {FIXTURES_DIR}"
    return FIXTURES_DIR


@pytest.fixture(scope="session")
def fixture_checksums() -> dict[str, str]:
    """SHA256 checksums of all fixture files computed at session start."""
    return compute_fixture_checksums()
