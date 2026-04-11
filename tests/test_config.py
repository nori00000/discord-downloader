"""
Tests for discord_exporter.config.ConfigManager.

Focus: permission hardening (chmod 600), env var precedence, round-trip
persistence, and the auto-migration of legacy world-readable config files.
"""

import json
import os
import stat

import pytest

from discord_exporter.config import ConfigManager

pytestmark = pytest.mark.usefixtures("isolated_home")


# ---------------------------------------------------------------------------
# Permission hardening
# ---------------------------------------------------------------------------

@pytest.mark.skipif(os.name == "nt", reason="POSIX permissions don't apply on Windows")
def test_save_token_sets_mode_0600(isolated_home):
    cm = ConfigManager()
    cm.set_token("Njk4OTIyMDU1MzQ5MDQzMzEx.fake.token_value_for_test_only")

    cfg_path = isolated_home / ".discord-exporter" / "config.json"
    env_path = isolated_home / ".discord-exporter" / ".env"

    for path in (cfg_path, env_path):
        assert path.exists(), f"{path} not created"
        mode = stat.S_IMODE(path.stat().st_mode)
        assert mode == 0o600, f"{path} has mode {oct(mode)}, expected 0o600"


@pytest.mark.skipif(os.name == "nt", reason="POSIX permissions don't apply on Windows")
def test_load_migrates_legacy_0644_config(isolated_home):
    """Legacy config files written with world-readable perms must be
    re-chmod'd to 0600 at load time so users don't stay exposed."""
    cfg_dir = isolated_home / ".discord-exporter"
    cfg_dir.mkdir()
    cfg_path = cfg_dir / "config.json"
    cfg_path.write_text(json.dumps({"token": "fake_legacy_token"}))
    os.chmod(cfg_path, 0o644)

    # Instantiating ConfigManager loads + migrates
    ConfigManager()

    mode = stat.S_IMODE(cfg_path.stat().st_mode)
    assert mode == 0o600, f"legacy config still {oct(mode)}"


# ---------------------------------------------------------------------------
# Round-trip persistence
# ---------------------------------------------------------------------------

def test_set_and_get_token_roundtrip():
    cm = ConfigManager()
    assert cm.get_token() is None

    cm.set_token("abc123")

    # New instance should read the value back from disk
    cm2 = ConfigManager()
    assert cm2.get_token() == "abc123"


def test_env_var_overrides_config(monkeypatch):
    cm = ConfigManager()
    cm.set_token("from_config")

    monkeypatch.setenv("DISCORD_TOKEN", "from_env")
    cm2 = ConfigManager()
    assert cm2.get_token() == "from_env", "env var must take precedence"


# ---------------------------------------------------------------------------
# Token masking
# ---------------------------------------------------------------------------

def test_mask_token_short_input():
    cm = ConfigManager()
    assert cm.mask_token("") == "****"
    assert cm.mask_token("short") == "****"


def test_mask_token_shows_only_edges():
    cm = ConfigManager()
    token = "XXX1XXX2XXX3XXX4XXX5XXX6.FAKE.abcdefGHIJK"
    masked = cm.mask_token(token)
    assert masked == "XXX1...HIJK"
    # Middle section must never leak
    assert "FAKE" not in masked
    assert token not in masked
