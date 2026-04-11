"""
Configuration management for Discord Exporter.

Handles token storage, DCE path configuration, and environment variables.
Tokens are stored locally and never transmitted externally.
"""

import json
import os
from pathlib import Path
from typing import Any, Optional


class ConfigManager:
    """Manages configuration including Discord token and DCE path."""

    # Configuration file locations
    CONFIG_DIR_NAME = ".discord-exporter"
    CONFIG_FILE_NAME = "config.json"
    ENV_FILE_NAME = ".env"

    # Environment variable names
    ENV_TOKEN = "DISCORD_TOKEN"
    ENV_DCE_PATH = "DCE_PATH"

    def __init__(self):
        self._config_dir = self._get_config_dir()
        self._config_file = self._config_dir / self.CONFIG_FILE_NAME
        self._env_file = self._config_dir / self.ENV_FILE_NAME
        self._config: dict[str, Any] = {}
        self._load_config()

    def _get_config_dir(self) -> Path:
        """Get the configuration directory path."""
        # Use user's home directory
        home = Path.home()
        config_dir = home / self.CONFIG_DIR_NAME
        return config_dir

    def _ensure_config_dir(self) -> None:
        """Ensure the configuration directory exists."""
        self._config_dir.mkdir(parents=True, exist_ok=True)

    def _load_config(self) -> None:
        """Load configuration from file.

        Also migrates existing files that were created before the 0600
        permission policy to restrict access to the owner only.
        """
        if self._config_file.exists():
            try:
                with open(self._config_file, encoding='utf-8') as f:
                    self._config = json.load(f)
            except (OSError, json.JSONDecodeError):
                self._config = {}
            # Tighten permissions on legacy world-readable config files
            self._restrict_permissions(self._config_file)

        # Also load from .env file if exists
        self._load_env_file()
        if self._env_file.exists():
            self._restrict_permissions(self._env_file)

    def _load_env_file(self) -> None:
        """Load environment variables from .env file."""
        if self._env_file.exists():
            try:
                with open(self._env_file, encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, _, value = line.partition('=')
                            key = key.strip()
                            value = value.strip()
                            # Remove quotes if present
                            if (value.startswith('"') and value.endswith('"')) or \
                               (value.startswith("'") and value.endswith("'")):
                                value = value[1:-1]
                            # Store in config
                            if key == self.ENV_TOKEN:
                                self._config['token'] = value
                            elif key == self.ENV_DCE_PATH:
                                self._config['dce_path'] = value
            except OSError:
                pass

    def _save_config(self) -> None:
        """Save configuration to file with owner-only permissions (0600)."""
        self._ensure_config_dir()
        with open(self._config_file, 'w', encoding='utf-8') as f:
            json.dump(self._config, f, indent=2)
        self._restrict_permissions(self._config_file)

    def _save_env_file(self) -> None:
        """Save configuration to .env file format with owner-only permissions (0600)."""
        self._ensure_config_dir()
        lines = []

        if 'token' in self._config:
            lines.append(f'{self.ENV_TOKEN}="{self._config["token"]}"')
        if 'dce_path' in self._config:
            lines.append(f'{self.ENV_DCE_PATH}="{self._config["dce_path"]}"')

        with open(self._env_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')
        self._restrict_permissions(self._env_file)

    @staticmethod
    def _restrict_permissions(path: Path) -> None:
        """
        Restrict file permissions to owner-only (0600).

        No-op on Windows where POSIX permission bits don't apply; Windows
        users should rely on filesystem ACLs on their user profile directory.
        """
        if os.name == 'nt':
            return
        try:
            os.chmod(path, 0o600)
        except OSError:
            # Best effort; don't crash config save if chmod fails
            # (e.g., network filesystem, readonly mount)
            pass

    def get_token(self) -> Optional[str]:
        """
        Get the Discord token.

        Priority:
        1. Environment variable DISCORD_TOKEN
        2. Config file

        Returns:
            The token or None if not configured.
        """
        # Check environment variable first
        env_token = os.environ.get(self.ENV_TOKEN)
        if env_token:
            return env_token

        return self._config.get('token')

    def set_token(self, token: str) -> None:
        """
        Save the Discord token to configuration.

        Args:
            token: The Discord token to save.
        """
        self._config['token'] = token
        self._save_config()
        self._save_env_file()

    def get_dce_path(self) -> Optional[str]:
        """
        Get the DiscordChatExporter.Cli executable path.

        Priority:
        1. Environment variable DCE_PATH
        2. Config file
        3. Auto-detect common locations

        Returns:
            The path or None if not found.
        """
        # Check environment variable first
        env_path = os.environ.get(self.ENV_DCE_PATH)
        if env_path:
            expanded = os.path.expanduser(env_path)
            if os.path.isfile(expanded):
                return expanded

        # Check config file
        config_path = self._config.get('dce_path')
        if config_path:
            expanded = os.path.expanduser(config_path)
            if os.path.isfile(expanded):
                return expanded

        # Auto-detect common locations
        return self._auto_detect_dce()

    def _auto_detect_dce(self) -> Optional[str]:
        """Auto-detect DiscordChatExporter.Cli in common locations."""
        import platform

        home = Path.home()
        system = platform.system()

        if system == 'Darwin':  # macOS
            # Common macOS locations
            candidates = [
                home / "Downloads" / "DiscordChatExporter.Cli.osx-arm64" / "DiscordChatExporter.Cli",
                home / "Downloads" / "DiscordChatExporter.Cli.osx-x64" / "DiscordChatExporter.Cli",
                home / "Applications" / "DiscordChatExporter.Cli",
                Path("/usr/local/bin/DiscordChatExporter.Cli"),
            ]
        elif system == 'Windows':
            # Common Windows locations
            candidates = [
                Path("C:/Tools/DiscordChatExporter/DiscordChatExporter.Cli.exe"),
                Path("C:/Program Files/DiscordChatExporter/DiscordChatExporter.Cli.exe"),
                home / "Downloads" / "DiscordChatExporter.Cli.win-x64" / "DiscordChatExporter.Cli.exe",
                home / "Downloads" / "DiscordChatExporter.Cli.win-arm64" / "DiscordChatExporter.Cli.exe",
            ]
        else:  # Linux
            candidates = [
                home / "Downloads" / "DiscordChatExporter.Cli.linux-x64" / "DiscordChatExporter.Cli",
                Path("/usr/local/bin/DiscordChatExporter.Cli"),
            ]

        for candidate in candidates:
            if candidate.exists():
                return str(candidate)

        return None

    def set_dce_path(self, path: str) -> None:
        """
        Save the DCE executable path to configuration.

        Args:
            path: The path to DiscordChatExporter.Cli.
        """
        self._config['dce_path'] = path
        self._save_config()
        self._save_env_file()

    def is_configured(self) -> bool:
        """Check if both token and DCE path are configured."""
        return bool(self.get_token() and self.get_dce_path())

    def get_config_path(self) -> Path:
        """Get the path to the configuration directory."""
        return self._config_dir

    def mask_token(self, token: str) -> str:
        """
        Mask a token for safe display in logs.

        Args:
            token: The token to mask.

        Returns:
            A masked version showing only first and last 4 characters.
        """
        if not token or len(token) < 12:
            return "****"
        return f"{token[:4]}...{token[-4:]}"

    def get_gui_settings(self) -> dict[str, Any]:
        """
        Get GUI settings.

        Returns:
            Dictionary of GUI settings.
        """
        return self._config.get('gui_settings', {})

    def set_gui_settings(self, settings: dict[str, Any]) -> None:
        """
        Save GUI settings.

        Args:
            settings: Dictionary of GUI settings to save.
        """
        self._config['gui_settings'] = settings
        self._save_config()

    def get_gui_setting(self, key: str, default: Any = None) -> Any:
        """
        Get a single GUI setting.

        Args:
            key: The setting key.
            default: Default value if not found.

        Returns:
            The setting value or default.
        """
        return self._config.get('gui_settings', {}).get(key, default)

    def set_gui_setting(self, key: str, value: Any) -> None:
        """
        Set a single GUI setting.

        Args:
            key: The setting key.
            value: The value to set.
        """
        if 'gui_settings' not in self._config:
            self._config['gui_settings'] = {}
        self._config['gui_settings'][key] = value
        self._save_config()
