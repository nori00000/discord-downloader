"""
Discord Downloader — a cross-platform CLI/GUI wrapper around
Tyrrrz's DiscordChatExporter.Cli.

This package exposes four entry points (configured in ``pyproject.toml``):

- ``discord-downloader`` — primary argparse-based CLI
- ``discord-downloader-gui`` — primary tkinter GUI
- ``discord-exporter`` — backward-compatible CLI alias
- ``discord-exporter-gui`` — backward-compatible GUI alias

The core reusable surface lives in ``discord_exporter.exporter.Exporter``
and ``discord_exporter.config.ConfigManager``; ``discord_exporter.utils``
holds pure helpers (URL parsing, sanitization, validation, format enum).

Security model: Discord tokens are stored only on the local filesystem
with owner-only (0600) permissions, never transmitted anywhere except
as an argument to the DCE subprocess. All subprocess output flows through
``utils.sanitize_error_message`` before being logged or raised.
"""

__version__ = "1.1.0"
__author__ = "Discord Downloader"

__all__ = ["__version__", "__author__"]
