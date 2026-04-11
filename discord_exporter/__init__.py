"""
Discord Exporter — a cross-platform CLI/GUI wrapper around
Tyrrrz's DiscordChatExporter.Cli.

This package exposes two entry points (configured in ``pyproject.toml``):

- ``discord-exporter`` — argparse-based CLI (``discord_exporter.cli:main``)
- ``discord-exporter-gui`` — tkinter GUI (``discord_exporter.gui:main``)

The core reusable surface lives in ``discord_exporter.exporter.Exporter``
and ``discord_exporter.config.ConfigManager``; ``discord_exporter.utils``
holds pure helpers (URL parsing, sanitization, validation, format enum).

Security model: Discord tokens are stored only on the local filesystem
with owner-only (0600) permissions, never transmitted anywhere except
as an argument to the DCE subprocess. All subprocess output flows through
``utils.sanitize_error_message`` before being logged or raised.
"""

__version__ = "1.1.0"
__author__ = "Discord Exporter"

__all__ = ["__version__", "__author__"]
