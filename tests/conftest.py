"""Shared pytest fixtures for discord-downloader tests."""

import os
import sys
from pathlib import Path

import pytest

# Make the package importable without needing editable install
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture
def isolated_home(tmp_path, monkeypatch):
    """
    Redirect Path.home() to a tmp directory so ConfigManager writes into
    an isolated location instead of the user's real ~/.discord-downloader.

    Also clears DISCORD_TOKEN / DCE_PATH env vars so tests see a clean slate.
    """
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    monkeypatch.delenv("DCE_PATH", raising=False)
    return fake_home


@pytest.fixture
def fake_dce(tmp_path):
    """
    Create a fake DCE executable (empty script) that is marked as executable.
    Tests that only validate path/permissions can point at this.
    """
    dce = tmp_path / "fake-dce"
    dce.write_text("#!/bin/sh\necho 'fake dce'\n")
    os.chmod(dce, 0o755)
    return dce
