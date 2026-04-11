"""
Tests for discord_exporter.exporter - command building, token masking in
logs, output dir validation, and error paths.

We DO NOT invoke real DCE. Instead we stub ConfigManager to return a token
and a path to a fake DCE script created by the `fake_dce` fixture.
"""

from pathlib import Path

import pytest

from discord_exporter.config import ConfigManager
from discord_exporter.exporter import (
    DCENotFoundError,
    Exporter,
    ExportError,
    ExportOptions,
    TokenNotConfiguredError,
)
from discord_exporter.utils import ExportFormat

pytestmark = pytest.mark.usefixtures("isolated_home")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_exporter(fake_dce: Path, token: str = "t.E.st") -> Exporter:
    cm = ConfigManager()
    cm.set_token(token)
    cm.set_dce_path(str(fake_dce))
    return Exporter(cm)


# ---------------------------------------------------------------------------
# Command building
# ---------------------------------------------------------------------------

class TestBuildCommand:
    def test_channel_export_includes_required_flags(self, fake_dce):
        ex = _make_exporter(fake_dce)
        opts = ExportOptions(
            channel_id="123456789012345678",
            export_format=ExportFormat.HTML_DARK,
        )
        cmd = ex._build_command("export", opts)
        assert cmd[0] == str(fake_dce)
        assert cmd[1] == "export"
        assert "-t" in cmd
        assert "-c" in cmd
        assert "123456789012345678" in cmd
        assert "-f" in cmd
        assert "HtmlDark" in cmd

    def test_markdown_format_uses_json_backend(self, fake_dce):
        ex = _make_exporter(fake_dce)
        opts = ExportOptions(
            channel_id="100",
            export_format=ExportFormat.MARKDOWN,
        )
        cmd = ex._build_command("export", opts)
        # Markdown is synthesized from a JSON export
        assert "Json" in cmd
        assert "Markdown" not in cmd

    def test_date_range_and_media_flags(self, fake_dce):
        ex = _make_exporter(fake_dce)
        opts = ExportOptions(
            channel_id="100",
            after="2024-01-01 00:00:00",
            before="2024-12-31 00:00:00",
            media=True,
            include_threads="all",
        )
        cmd = ex._build_command("export", opts)
        assert "--after" in cmd and "2024-01-01 00:00:00" in cmd
        assert "--before" in cmd and "2024-12-31 00:00:00" in cmd
        assert "--media" in cmd
        assert "--include-threads" in cmd and "all" in cmd

    def test_safe_mode_sets_parallel_one(self, fake_dce):
        ex = _make_exporter(fake_dce)
        opts = ExportOptions(channel_id="100", safe_mode=True)
        cmd = ex._build_command("export", opts)
        assert "--parallel" in cmd
        idx = cmd.index("--parallel")
        assert cmd[idx + 1] == "1"


# ---------------------------------------------------------------------------
# Token masking in display command
# ---------------------------------------------------------------------------

class TestDisplayCommand:
    def test_build_display_command_masks_token(self, fake_dce):
        token = "Njk4OTIyMDU1MzQ5MDQzMzEx.fake.value_under_test"
        ex = _make_exporter(fake_dce, token=token)
        cmd = ex._build_command(
            "export",
            ExportOptions(channel_id="100", export_format=ExportFormat.JSON),
        )
        display = ex._build_display_command(cmd)
        assert token not in display
        assert "******" in display
        # Other args still visible
        assert "100" in display
        assert "Json" in display


# ---------------------------------------------------------------------------
# _prepare_output_dir
# ---------------------------------------------------------------------------

class TestPrepareOutputDir:
    def test_none_returns_cwd(self, fake_dce):
        ex = _make_exporter(fake_dce)
        result = ex._prepare_output_dir(None)
        assert result == Path.cwd()

    def test_creates_missing_dir(self, fake_dce, tmp_path):
        ex = _make_exporter(fake_dce)
        target = tmp_path / "new_output"
        ex._prepare_output_dir(target)
        assert target.exists()

    def test_existing_dir(self, fake_dce, tmp_path):
        ex = _make_exporter(fake_dce)
        result = ex._prepare_output_dir(tmp_path)
        assert result == tmp_path.expanduser()

    def test_file_as_dir_raises(self, fake_dce, tmp_path):
        ex = _make_exporter(fake_dce)
        f = tmp_path / "file.txt"
        f.write_text("hi")
        with pytest.raises(ExportError):
            ex._prepare_output_dir(f)


# ---------------------------------------------------------------------------
# Configuration guards
# ---------------------------------------------------------------------------

class TestConfigurationGuards:
    def test_missing_token_raises(self, isolated_home, fake_dce):
        cm = ConfigManager()
        cm.set_dce_path(str(fake_dce))
        ex = Exporter(cm)
        with pytest.raises(TokenNotConfiguredError):
            ex._get_token()

    def test_missing_dce_raises(self, isolated_home):
        cm = ConfigManager()
        cm.set_token("t.E.st")
        ex = Exporter(cm)
        with pytest.raises(DCENotFoundError):
            ex._get_dce_path()

    def test_non_executable_dce_raises(self, isolated_home, tmp_path):
        dce = tmp_path / "not_executable"
        dce.write_text("x")
        # No chmod +x
        cm = ConfigManager()
        cm.set_token("t.E.st")
        cm.set_dce_path(str(dce))
        ex = Exporter(cm)
        with pytest.raises(DCENotFoundError) as exc_info:
            ex._get_dce_path()
        assert "실행 권한" in str(exc_info.value)


# ---------------------------------------------------------------------------
# export_channel signature — no real subprocess, just exercise argument paths
# ---------------------------------------------------------------------------

class TestExportChannelRequiresChannelId:
    def test_missing_channel_id_raises(self, fake_dce):
        ex = _make_exporter(fake_dce)
        with pytest.raises(ValueError):
            ex.export_channel(ExportOptions())


class TestExportGuildRequiresGuildId:
    def test_missing_guild_id_raises(self, fake_dce):
        ex = _make_exporter(fake_dce)
        with pytest.raises(ValueError):
            ex.export_guild(ExportOptions())
