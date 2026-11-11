"""Validate installed distribution and checker rejection, without importing fixtures."""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts/check_import_boundaries.py"


def test_installed_distribution(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            "import danus_ai; from importlib.metadata import version; "
            "assert version('danus-ai') == '0.1.0'; "
            "assert 'site-packages' in danus_ai.__file__",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    ("name", "code", "marker"),
    [
        ("legal", 0, "PASS"),
        ("illegal", 1, "B01"),
    ],
)
def test_fixture_cli(name: str, code: int, marker: str) -> None:
    result = subprocess.run(
        [sys.executable, str(CHECKER), str(ROOT / "fixtures/import_boundaries" / name)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == code, result.stderr
    assert marker in result.stdout


@pytest.mark.parametrize(
    ("source", "rule"),
    [
        ("from ..ideation import service", "B01"),
        ("from danus_ai import ideation", "B01"),
        ("import danus_ai.memory.store", "B01"),
        ("import httpx", "B02"),
        ("import sqlite3", "B02"),
        ("import os", "B02"),
        ("__import__('httpx')", "B03"),
    ],
)
def test_rejection_forms(tmp_path: Path, source: str, rule: str) -> None:
    component = "contracts" if rule != "B01" else "orchestration"
    target = tmp_path / component / "probe.py"
    target.parent.mkdir()
    target.write_text(source, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(CHECKER), str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1, result.stderr
    assert rule in result.stdout


def test_missing_root_fails(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(CHECKER), str(tmp_path / "missing")],
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
