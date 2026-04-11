"""
Tests for discord_exporter.utils - URL parsing, date parsing, sanitization,
format resolution, and directory validation.
"""

import os

import pytest

from discord_exporter.utils import (
    ExportFormat,
    parse_date,
    parse_discord_url,
    parse_discord_url_extended,
    sanitize_error_message,
    validate_channel_id,
    validate_date_range,
    validate_dce_executable,
    validate_guild_id,
    validate_output_directory,
)

# ---------------------------------------------------------------------------
# URL parsing
# ---------------------------------------------------------------------------

class TestParseDiscordUrl:
    def test_channel_url(self):
        guild, channel = parse_discord_url(
            "https://discord.com/channels/411001645158105102/767174379955027988"
        )
        assert guild == "411001645158105102"
        assert channel == "767174379955027988"

    def test_dm_url_has_no_guild(self):
        guild, channel = parse_discord_url(
            "https://discord.com/channels/@me/767174379955027988"
        )
        assert guild is None
        assert channel == "767174379955027988"

    def test_message_id_suffix_is_ignored(self):
        guild, channel = parse_discord_url(
            "https://discord.com/channels/100/200/9999999999999"
        )
        assert guild == "100"
        assert channel == "200"

    def test_thread_url_extended(self):
        parsed = parse_discord_url_extended(
            "https://discord.com/channels/100/200/threads/300"
        )
        assert parsed.guild_id == "100"
        assert parsed.channel_id == "200"
        assert parsed.thread_id == "300"

    def test_rejects_non_url(self):
        with pytest.raises(ValueError):
            parse_discord_url("not a url")

    def test_rejects_non_discord_domain(self):
        with pytest.raises(ValueError):
            parse_discord_url("https://example.com/channels/1/2")

    def test_rejects_empty(self):
        with pytest.raises(ValueError):
            parse_discord_url("")


# ---------------------------------------------------------------------------
# Snowflake validation
# ---------------------------------------------------------------------------

class TestSnowflakeValidation:
    def test_valid_channel_id(self):
        assert validate_channel_id("12345678901234567") == "12345678901234567"

    def test_valid_guild_id(self):
        assert validate_guild_id("98765432109876543") == "98765432109876543"

    def test_rejects_letters(self):
        with pytest.raises(ValueError):
            validate_channel_id("abc123def456ghi78")

    def test_rejects_too_short(self):
        with pytest.raises(ValueError):
            validate_channel_id("123")

    def test_rejects_too_long(self):
        with pytest.raises(ValueError):
            validate_channel_id("1" * 25)

    def test_rejects_empty(self):
        with pytest.raises(ValueError):
            validate_channel_id("")


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------

class TestParseDate:
    def test_iso_date(self):
        assert parse_date("2024-01-15") == "2024-01-15 00:00:00"

    def test_datetime_with_time(self):
        assert parse_date("2024-01-15 14:30") == "2024-01-15 14:30:00"

    def test_slash_date(self):
        assert parse_date("2024/01/15") == "2024-01-15 00:00:00"

    def test_rejects_invalid(self):
        with pytest.raises(ValueError):
            parse_date("not a date")

    def test_rejects_empty(self):
        with pytest.raises(ValueError):
            parse_date("")


class TestValidateDateRange:
    def test_both_none(self):
        assert validate_date_range(None, None) == (None, None)

    def test_after_before(self):
        a, b = validate_date_range("2024-01-01", "2024-12-31")
        assert a == "2024-01-01 00:00:00"
        assert b == "2024-12-31 00:00:00"

    def test_rejects_reverse_order(self):
        with pytest.raises(ValueError):
            validate_date_range("2024-12-31", "2024-01-01")

    def test_rejects_equal(self):
        with pytest.raises(ValueError):
            validate_date_range("2024-01-01", "2024-01-01")


# ---------------------------------------------------------------------------
# ExportFormat
# ---------------------------------------------------------------------------

class TestExportFormat:
    @pytest.mark.parametrize("user_input,expected", [
        ("html", ExportFormat.HTML_DARK),
        ("html-dark", ExportFormat.HTML_DARK),
        ("html-light", ExportFormat.HTML_LIGHT),
        ("txt", ExportFormat.PLAIN_TEXT),
        ("plaintext", ExportFormat.PLAIN_TEXT),
        ("json", ExportFormat.JSON),
        ("csv", ExportFormat.CSV),
        ("md", ExportFormat.MARKDOWN),
        ("markdown", ExportFormat.MARKDOWN),
        ("obsidian", ExportFormat.MARKDOWN),
    ])
    def test_from_string(self, user_input, expected):
        assert ExportFormat.from_string(user_input) == expected

    def test_case_insensitive(self):
        assert ExportFormat.from_string("HTML") == ExportFormat.HTML_DARK
        assert ExportFormat.from_string("Obsidian") == ExportFormat.MARKDOWN

    def test_markdown_uses_json_backend(self):
        assert ExportFormat.MARKDOWN.get_dce_format() == "Json"
        assert ExportFormat.MARKDOWN.get_extension() == ".md"

    def test_unknown_format_raises(self):
        with pytest.raises(ValueError):
            ExportFormat.from_string("rtf")


# ---------------------------------------------------------------------------
# Sanitization
# ---------------------------------------------------------------------------

class TestSanitizeErrorMessage:
    def test_removes_discord_token_pattern(self):
        # Matches Discord's "base64.base64.base64" token format
        msg = "Failed: token MTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY.ABCDEF.xyz123ABC456DEF789GHI012JKL3"
        out = sanitize_error_message(msg)
        assert "MTIzNDU2" not in out
        assert "<TOKEN>" in out

    def test_removes_explicit_token(self):
        token = "XXX1XXX2XXX3XXX4XXX5XXX6.FAKE.yyyyyyYYYYYYzzzzzzZZZZ"
        msg = f"Error running export with {token} failed"
        out = sanitize_error_message(msg, token)
        assert token not in out
        assert "<TOKEN>" in out

    def test_empty_string(self):
        assert sanitize_error_message("") == ""

    def test_no_token_preserved(self):
        msg = "Connection refused on port 443"
        assert sanitize_error_message(msg) == msg


# ---------------------------------------------------------------------------
# Output directory validation
# ---------------------------------------------------------------------------

class TestValidateOutputDirectory:
    def test_empty_path_is_valid(self):
        ok, _ = validate_output_directory("")
        assert ok

    def test_existing_writable_dir(self, tmp_path):
        ok, err = validate_output_directory(str(tmp_path))
        assert ok, f"error: {err}"

    def test_creates_missing_dir(self, tmp_path):
        target = tmp_path / "new_sub" / "nested"
        ok, _ = validate_output_directory(str(target))
        assert ok
        assert target.exists()

    def test_rejects_file_as_dir(self, tmp_path):
        f = tmp_path / "a.txt"
        f.write_text("hi")
        ok, err = validate_output_directory(str(f))
        assert not ok
        assert "폴더" in err

    @pytest.mark.skipif(os.name == "nt" or os.geteuid() == 0,
                        reason="root bypasses read-only perms; skip on Windows")
    def test_rejects_unwritable_dir(self, tmp_path):
        locked = tmp_path / "locked"
        locked.mkdir()
        os.chmod(locked, 0o500)  # read + execute, no write
        try:
            ok, err = validate_output_directory(str(locked))
            assert not ok
            assert "쓰기" in err or "권한" in err
        finally:
            os.chmod(locked, 0o700)  # restore for cleanup


class TestValidateDceExecutable:
    def test_empty_path(self):
        ok, err = validate_dce_executable("")
        assert not ok

    def test_missing_file(self, tmp_path):
        ok, err = validate_dce_executable(str(tmp_path / "nope"))
        assert not ok
        assert "찾을 수 없" in err

    def test_directory_not_file(self, tmp_path):
        ok, err = validate_dce_executable(str(tmp_path))
        assert not ok
        assert "파일이 아닙" in err

    @pytest.mark.skipif(os.name == "nt", reason="POSIX x bit on macOS/Linux only")
    def test_rejects_non_executable(self, tmp_path):
        f = tmp_path / "dce"
        f.write_text("binary-ish")
        os.chmod(f, 0o644)
        ok, err = validate_dce_executable(str(f))
        assert not ok
        assert "실행 권한" in err

    def test_accepts_fake_dce(self, fake_dce):
        ok, err = validate_dce_executable(str(fake_dce))
        assert ok, f"error: {err}"
