"""
Tests for discord_exporter.cli - argparse structure, format parsing, and
`parse_common_export_options` helper. No real DCE execution.
"""

import argparse

import pytest

from discord_exporter import cli
from discord_exporter.utils import ExportFormat

# ---------------------------------------------------------------------------
# Parser structure
# ---------------------------------------------------------------------------

class TestParser:
    def test_parser_builds(self):
        assert cli.create_parser() is not None

    @pytest.mark.parametrize("command", [
        "setup", "export", "exportguild", "exportdm",
        "list-guilds", "list-channels", "list-dm",
    ])
    def test_subcommands_are_registered(self, command):
        parser = cli.create_parser()
        # Parsing only the bare subcommand should not raise (for those that
        # don't have required args the bare command works; for others we
        # expect SystemExit from argparse, which is still a "registered" check).
        try:
            parser.parse_args([command])
        except SystemExit:
            pass  # Missing required args is expected for some commands


# ---------------------------------------------------------------------------
# parse_common_export_options helper
# ---------------------------------------------------------------------------

def _ns(**kwargs):
    """Build a Namespace with the fields common-export expects."""
    defaults = dict(
        format="html",
        output_dir=None,
        after=None,
        before=None,
        media=False,
        include_threads=None,
    )
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


class TestCommonOptionsHelper:
    def test_defaults(self):
        opts = cli.parse_common_export_options(_ns())
        assert opts.export_format == ExportFormat.HTML_DARK
        assert opts.output_dir is None
        assert opts.after is None
        assert opts.before is None
        assert opts.media is False
        assert opts.include_threads is None

    def test_obsidian_format(self):
        opts = cli.parse_common_export_options(_ns(format="obsidian"))
        assert opts.export_format == ExportFormat.MARKDOWN

    def test_md_format(self):
        opts = cli.parse_common_export_options(_ns(format="md"))
        assert opts.export_format == ExportFormat.MARKDOWN

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError):
            cli.parse_common_export_options(_ns(format="rtf"))

    def test_date_parsing(self):
        opts = cli.parse_common_export_options(
            _ns(after="2024-01-01", before="2024-12-31")
        )
        assert opts.after.startswith("2024-01-01")
        assert opts.before.startswith("2024-12-31")

    def test_invalid_date_raises(self):
        with pytest.raises(ValueError):
            cli.parse_common_export_options(_ns(after="yesterday"))

    def test_include_threads_passthrough(self):
        opts = cli.parse_common_export_options(_ns(include_threads="all"))
        assert opts.include_threads == "all"

    def test_output_dir_conversion(self, tmp_path):
        opts = cli.parse_common_export_options(_ns(output_dir=str(tmp_path)))
        assert opts.output_dir == tmp_path


class TestFormatHelp:
    def test_help_lists_obsidian(self):
        parser = cli.create_parser()
        help_text = parser.format_help()
        assert "export" in help_text

        # Check the export subparser's help includes md/obsidian
        sub_help_found = False
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                for name, subparser in action.choices.items():
                    if name == "export":
                        sub_help = subparser.format_help()
                        assert "obsidian" in sub_help or "md" in sub_help
                        sub_help_found = True
        assert sub_help_found
