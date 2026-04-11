"""
Core exporter functionality for Discord Exporter.

Handles the actual invocation of DiscordChatExporter.Cli.
"""

import subprocess
import sys
import threading
from pathlib import Path
from typing import Optional, List, Callable
from dataclasses import dataclass

from .config import ConfigManager
from .utils import (
    ExportFormat,
    generate_output_filename,
    generate_guild_output_filename,
    sanitize_error_message,
    parse_dce_error,
    get_error_solution,
    convert_json_to_markdown,
    LogEvent,
    LogLevel,
    LogCallback,
    default_log_callback,
)


@dataclass
class ExportOptions:
    """Options for export operations."""
    channel_id: Optional[str] = None
    guild_id: Optional[str] = None
    export_format: ExportFormat = ExportFormat.HTML_DARK
    output_path: Optional[Path] = None
    output_dir: Optional[Path] = None
    after: Optional[str] = None
    before: Optional[str] = None
    media: bool = False
    include_threads: Optional[str] = None  # none, active, all
    safe_mode: bool = False  # Slower but safer (--parallel 1, delays)


class ExportError(Exception):
    """Exception raised when export fails."""
    pass


class DCENotFoundError(Exception):
    """Exception raised when DiscordChatExporter.Cli is not found."""
    pass


class TokenNotConfiguredError(Exception):
    """Exception raised when Discord token is not configured."""
    pass


class Exporter:
    """
    Handles exporting Discord chat logs via DiscordChatExporter.Cli.
    """

    def __init__(self, config: Optional[ConfigManager] = None):
        """
        Initialize the exporter.

        Args:
            config: Optional ConfigManager instance. Creates new one if not provided.
        """
        self.config = config or ConfigManager()
        self._token: Optional[str] = None
        self._dce_path: Optional[str] = None
        self._current_process: Optional[subprocess.Popen] = None
        self._cancelled = False

    def cancel(self):
        """Cancel the current export operation."""
        self._cancelled = True
        if self._current_process:
            try:
                self._current_process.terminate()
                # Give it a moment, then force kill if needed
                try:
                    self._current_process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self._current_process.kill()
            except Exception:
                pass

    def is_cancelled(self) -> bool:
        """Check if export was cancelled."""
        return self._cancelled

    def reset(self):
        """Reset cancel state for new export."""
        self._cancelled = False
        self._current_process = None

    def _get_token(self) -> str:
        """Get the Discord token, raising if not configured."""
        if self._token:
            return self._token

        token = self.config.get_token()
        if not token:
            raise TokenNotConfiguredError(
                "Discord token is not configured. Please run setup first."
            )
        self._token = token
        return token

    def _get_dce_path(self) -> str:
        """Get the DCE executable path, raising if not found."""
        if self._dce_path:
            return self._dce_path

        dce_path = self.config.get_dce_path()
        if not dce_path:
            raise DCENotFoundError(
                "DiscordChatExporter.Cli not found. "
                "Please set DCE_PATH environment variable or configure via setup."
            )
        self._dce_path = dce_path
        return dce_path

    def _build_command(
        self,
        subcommand: str,
        options: ExportOptions
    ) -> List[str]:
        """
        Build the DCE command with arguments.

        Args:
            subcommand: The DCE subcommand (export, exportguild, exportdm).
            options: Export options.

        Returns:
            List of command arguments.
        """
        dce_path = self._get_dce_path()
        token = self._get_token()

        cmd = [dce_path, subcommand]

        # Token
        cmd.extend(['-t', token])

        # Channel or Guild ID
        if options.channel_id:
            cmd.extend(['-c', options.channel_id])
        if options.guild_id:
            cmd.extend(['-g', options.guild_id])

        # Format (use get_dce_format for Markdown -> JSON conversion)
        cmd.extend(['-f', options.export_format.get_dce_format()])

        # Output path
        if options.output_path:
            cmd.extend(['-o', str(options.output_path)])

        # Date range
        if options.after:
            cmd.extend(['--after', options.after])
        if options.before:
            cmd.extend(['--before', options.before])

        # Media download
        if options.media:
            cmd.append('--media')

        # Thread inclusion
        if options.include_threads:
            cmd.extend(['--include-threads', options.include_threads])

        # Safe mode: slower but respects rate limits better
        if options.safe_mode:
            cmd.extend(['--parallel', '1'])  # One channel at a time

        return cmd

    def _build_display_command(self, cmd: List[str]) -> str:
        """
        Build a display-safe command string with masked token.

        Args:
            cmd: The command list.

        Returns:
            Command string with token replaced by ******.
        """
        display_parts = []
        skip_next = False

        for arg in cmd:
            if skip_next:
                display_parts.append("******")
                skip_next = False
            elif arg == '-t':
                display_parts.append(arg)
                skip_next = True
            else:
                display_parts.append(arg)

        return ' '.join(display_parts)

    def _run_command_streaming(
        self,
        cmd: List[str],
        log_callback: LogCallback
    ) -> int:
        """
        Run DCE command with streaming output.

        Uses subprocess.Popen to stream stdout/stderr line by line.
        All output is sanitized before sending to callback.

        Args:
            cmd: The command to run.
            log_callback: Callback function for log events.

        Returns:
            Process return code.

        Raises:
            DCENotFoundError: If DCE executable not found.
            ExportError: If process fails.
        """
        # Get token for sanitization
        try:
            token = self._get_token()
        except TokenNotConfiguredError:
            token = None

        # Log the command (masked)
        display_cmd = self._build_display_command(cmd)
        log_callback(LogEvent(
            level=LogLevel.INFO,
            message=f"실행: {display_cmd}"
        ))

        try:
            # Start process with pipes
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line buffered
                universal_newlines=True
            )

            # Store reference for cancellation
            self._current_process = process

            # Read stdout and stderr in separate threads
            stdout_lines = []
            stderr_lines = []

            def read_stdout():
                for line in process.stdout:
                    if self._cancelled:
                        break
                    line = line.rstrip('\n\r')
                    if line:
                        # Sanitize before logging
                        safe_line = sanitize_error_message(line, token)
                        stdout_lines.append(safe_line)

                        # Check for error patterns in stdout (DCE sometimes outputs errors here)
                        error_type, error_detail = parse_dce_error(safe_line)
                        if error_type != 'unknown':
                            log_callback(LogEvent(
                                level=LogLevel.ERROR,
                                message=safe_line
                            ))
                            log_callback(LogEvent(
                                level=LogLevel.ERROR,
                                message=f"▶ {error_detail}"
                            ))
                        else:
                            log_callback(LogEvent(
                                level=LogLevel.INFO,
                                message=safe_line
                            ))

            def read_stderr():
                for line in process.stderr:
                    if self._cancelled:
                        break
                    line = line.rstrip('\n\r')
                    if line:
                        # Sanitize before logging
                        safe_line = sanitize_error_message(line, token)
                        stderr_lines.append(safe_line)

                        # Check for known error patterns and provide detailed message
                        error_type, error_detail = parse_dce_error(safe_line)
                        if error_type != 'unknown':
                            # Show the original error line first
                            log_callback(LogEvent(
                                level=LogLevel.ERROR,
                                message=safe_line
                            ))
                            # Then show detailed explanation
                            log_callback(LogEvent(
                                level=LogLevel.ERROR,
                                message=f"▶ {error_detail}"
                            ))
                        else:
                            log_callback(LogEvent(
                                level=LogLevel.WARNING,
                                message=safe_line
                            ))

            # Start reader threads
            stdout_thread = threading.Thread(target=read_stdout, daemon=True)
            stderr_thread = threading.Thread(target=read_stderr, daemon=True)
            stdout_thread.start()
            stderr_thread.start()

            # Wait for process to complete
            process.wait()

            # Wait for reader threads
            stdout_thread.join(timeout=5)
            stderr_thread.join(timeout=5)

            # Clear process reference
            self._current_process = None

            # Check if cancelled
            if self._cancelled:
                return -1  # Indicate cancellation

            return process.returncode

        except FileNotFoundError:
            raise DCENotFoundError(
                f"DCE 실행 파일을 찾을 수 없습니다: {cmd[0]}\n"
                "경로가 올바른지 확인하고, 실행 권한이 있는지 확인하세요."
            )
        except Exception as e:
            # Sanitize any exception message
            safe_msg = sanitize_error_message(str(e), token)
            raise ExportError(f"실행 오류: {safe_msg}")

    def _run_command(self, cmd: List[str]) -> subprocess.CompletedProcess:
        """
        Run a DCE command and handle the result.

        Args:
            cmd: The command to run.

        Returns:
            The completed process.

        Raises:
            ExportError: If the command fails.
        """
        # Get token for sanitization
        try:
            token = self._get_token()
        except TokenNotConfiguredError:
            token = None

        # Create a display command with masked token
        display_cmd = []
        skip_next = False
        for i, arg in enumerate(cmd):
            if skip_next:
                display_cmd.append('<TOKEN>')
                skip_next = False
            elif arg == '-t':
                display_cmd.append(arg)
                skip_next = True
            else:
                display_cmd.append(arg)

        print(f"Running: {' '.join(display_cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout for large exports
            )

            if result.returncode != 0:
                stderr = sanitize_error_message(result.stderr, token)
                stdout = sanitize_error_message(result.stdout, token)
                raise ExportError(
                    f"Export failed with code {result.returncode}.\n"
                    f"Output: {stdout}\n"
                    f"Error: {stderr}"
                )

            return result

        except subprocess.TimeoutExpired:
            raise ExportError("Export timed out after 1 hour")
        except FileNotFoundError:
            raise DCENotFoundError(
                f"Could not execute DCE at: {cmd[0]}\n"
                "Please verify the path is correct and the file is executable."
            )
        except Exception as e:
            sanitized_msg = sanitize_error_message(str(e), token)
            raise ExportError(f"Export failed: {sanitized_msg}")

    def export_channel(
        self,
        options: ExportOptions,
        log_callback: Optional[LogCallback] = None
    ) -> Path:
        """
        Export a single Discord channel.

        Args:
            options: Export options including channel_id.
            log_callback: Optional callback for streaming logs.
                         If None, uses default print-based callback.

        Returns:
            Path to the exported file.

        Raises:
            ExportError: If export fails.
            ValueError: If channel_id is not provided.
        """
        if not options.channel_id:
            raise ValueError("channel_id is required for channel export")

        # Use default callback if none provided
        callback = log_callback or default_log_callback

        # Check if Markdown conversion is needed
        is_markdown = options.export_format == ExportFormat.MARKDOWN

        # Use DCE's naming pattern for readable filenames
        # %C = channel name, which includes thread/forum post titles
        if not options.output_path:
            output_dir = options.output_dir or Path.cwd()
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            if is_markdown:
                # For Markdown: DCE exports JSON, then we convert
                options.output_path = output_dir / "%C.json"
            else:
                # Pattern: ChannelName.extension (DCE handles special chars)
                options.output_path = output_dir / f"%C{options.export_format.get_extension()}"

        callback(LogEvent(
            level=LogLevel.INFO,
            message=f"채널 내보내기 시작: {options.channel_id}"
        ))

        if is_markdown:
            callback(LogEvent(
                level=LogLevel.INFO,
                message="Markdown 형식: JSON → MD 변환 예정"
            ))

        cmd = self._build_command('export', options)

        # Use streaming if callback provided, otherwise use blocking
        if log_callback:
            return_code = self._run_command_streaming(cmd, callback)

            # Check if cancelled first (return code -1)
            if self._cancelled:
                callback(LogEvent(
                    level=LogLevel.WARNING,
                    message="내보내기가 중지되었습니다."
                ))
                return options.output_path or Path.cwd()

            if return_code != 0:
                raise ExportError(
                    f"내보내기 실패 (종료 코드: {return_code})"
                )
        else:
            result = self._run_command(cmd)
            # Print output (sanitized)
            token = self._get_token()
            if result.stdout:
                print(sanitize_error_message(result.stdout, token))

        # Convert JSON to Markdown if needed
        final_path = options.output_path
        if is_markdown:
            # Find the actual JSON file created by DCE
            # DCE replaces %C with actual channel name
            json_files = list(output_dir.glob("*.json"))
            if json_files:
                # Get the most recently created JSON file
                json_path = max(json_files, key=lambda p: p.stat().st_mtime)
                md_path = json_path.with_suffix('.md')

                callback(LogEvent(
                    level=LogLevel.INFO,
                    message=f"Markdown 변환 중: {json_path.name} → {md_path.name}"
                ))

                convert_json_to_markdown(json_path, md_path)

                # Optionally remove the JSON file
                json_path.unlink()

                final_path = md_path

        callback(LogEvent(
            level=LogLevel.SUCCESS,
            message=f"완료: {final_path}"
        ))

        return final_path

    def export_guild(
        self,
        options: ExportOptions,
        log_callback: Optional[LogCallback] = None
    ) -> Path:
        """
        Export all channels in a Discord guild.

        Args:
            options: Export options including guild_id.
            log_callback: Optional callback for streaming logs.
                         If None, uses default print-based callback.

        Returns:
            Path to the output directory.

        Raises:
            ExportError: If export fails.
            ValueError: If guild_id is not provided.
        """
        if not options.guild_id:
            raise ValueError("guild_id is required for guild export")

        # Use default callback if none provided
        callback = log_callback or default_log_callback

        # Generate output directory if not specified
        output_dir = generate_guild_output_filename(
            options.guild_id,
            options.export_format,
            options.output_dir
        )

        # For guild export, -o is a directory pattern
        # Use readable naming: ChannelName.extension
        options.output_path = output_dir / f"%C{options.export_format.get_extension()}"

        callback(LogEvent(
            level=LogLevel.INFO,
            message=f"서버 내보내기 시작: {options.guild_id}"
        ))

        if options.include_threads:
            callback(LogEvent(
                level=LogLevel.INFO,
                message=f"스레드 포함 옵션: {options.include_threads}"
            ))

        cmd = self._build_command('exportguild', options)

        # Use streaming if callback provided, otherwise use blocking
        if log_callback:
            return_code = self._run_command_streaming(cmd, callback)

            # Check if cancelled first (return code -1)
            if self._cancelled:
                callback(LogEvent(
                    level=LogLevel.WARNING,
                    message="내보내기가 중지되었습니다."
                ))
                return output_dir

            if return_code != 0:
                raise ExportError(
                    f"내보내기 실패 (종료 코드: {return_code})"
                )
        else:
            result = self._run_command(cmd)
            # Print output (sanitized)
            token = self._get_token()
            if result.stdout:
                print(sanitize_error_message(result.stdout, token))

        callback(LogEvent(
            level=LogLevel.SUCCESS,
            message=f"완료: {output_dir}"
        ))

        return output_dir

    def export_dm(self, options: ExportOptions) -> Path:
        """
        Export all DM channels.

        Args:
            options: Export options.

        Returns:
            Path to the output directory.

        Raises:
            ExportError: If export fails.
        """
        from datetime import datetime

        # Generate output directory
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        if options.output_dir:
            output_dir = Path(options.output_dir) / f"dm-export-{timestamp}"
        else:
            output_dir = Path.cwd() / f"dm-export-{timestamp}"

        output_dir.mkdir(parents=True, exist_ok=True)

        # For DM export, -o is a directory pattern
        options.output_path = output_dir / f"%G - %C{options.export_format.get_extension()}"

        cmd = self._build_command('exportdm', options)
        result = self._run_command(cmd)

        # Print output (sanitized)
        token = self._get_token()
        if result.stdout:
            print(sanitize_error_message(result.stdout, token))

        print(f"\nExported DMs to directory: {output_dir}")
        return output_dir

    def list_guilds(self) -> str:
        """
        List all accessible guilds.

        Returns:
            The command output with guild list.
        """
        dce_path = self._get_dce_path()
        token = self._get_token()

        cmd = [dce_path, 'guilds', '-t', token]
        result = self._run_command(cmd)

        return sanitize_error_message(result.stdout, token)

    def list_channels(self, guild_id: str, include_threads: str = "None",
                      include_vc: bool = True) -> str:
        """
        List all channels in a guild.

        Args:
            guild_id: The guild ID.
            include_threads: Thread inclusion mode ("None", "Active", "All").
            include_vc: Include voice channels. Default True.

        Returns:
            The command output with channel list.
        """
        dce_path = self._get_dce_path()
        token = self._get_token()

        cmd = [dce_path, 'channels', '-t', token, '-g', guild_id,
               '--include-threads', include_threads,
               '--include-vc', str(include_vc)]
        result = self._run_command(cmd)

        return sanitize_error_message(result.stdout, token)

    def list_dm_channels(self) -> str:
        """
        List all DM channels.

        Returns:
            The command output with DM channel list.
        """
        dce_path = self._get_dce_path()
        token = self._get_token()

        cmd = [dce_path, 'dm', '-t', token]
        result = self._run_command(cmd)

        return sanitize_error_message(result.stdout, token)
