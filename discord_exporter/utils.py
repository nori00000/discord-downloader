"""
Utility functions for Discord Exporter.

Includes URL parsing, filename generation, and validation helpers.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Callable
from enum import Enum
from dataclasses import dataclass


# =============================================================================
# Log Event Types (for GUI/CLI streaming)
# =============================================================================

class LogLevel(Enum):
    """Log level for streaming output."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"


@dataclass
class LogEvent:
    """
    Log event for streaming to GUI/CLI.

    All messages must be token-free (sanitized before creating LogEvent).
    """
    level: LogLevel
    message: str  # Must be sanitized - never contains token
    timestamp: str = ""  # HH:MM:SS format

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().strftime("%H:%M:%S")


# Type alias for log callback function
LogCallback = Callable[[LogEvent], None]


def default_log_callback(event: LogEvent) -> None:
    """Default callback that prints to stdout (for CLI)."""
    prefix = ""
    if event.level == LogLevel.ERROR:
        prefix = "[ERROR] "
    elif event.level == LogLevel.WARNING:
        prefix = "[WARN] "
    elif event.level == LogLevel.SUCCESS:
        prefix = "[OK] "
    print(f"[{event.timestamp}] {prefix}{event.message}")


class ExportFormat(Enum):
    """Supported export formats for DiscordChatExporter."""
    HTML_DARK = "HtmlDark"
    HTML_LIGHT = "HtmlLight"
    PLAIN_TEXT = "PlainText"
    JSON = "Json"
    CSV = "Csv"
    MARKDOWN = "Markdown"  # Custom: JSON -> Markdown conversion

    @classmethod
    def from_string(cls, value: str) -> 'ExportFormat':
        """
        Parse format from user-friendly string.

        Args:
            value: User input like 'html', 'txt', 'json', etc.

        Returns:
            The corresponding ExportFormat enum.

        Raises:
            ValueError: If format is not recognized.
        """
        value_lower = value.lower().strip()

        format_map = {
            'html': cls.HTML_DARK,
            'htmldark': cls.HTML_DARK,
            'html-dark': cls.HTML_DARK,
            'html_dark': cls.HTML_DARK,
            'htmllight': cls.HTML_LIGHT,
            'html-light': cls.HTML_LIGHT,
            'html_light': cls.HTML_LIGHT,
            'txt': cls.PLAIN_TEXT,
            'text': cls.PLAIN_TEXT,
            'plaintext': cls.PLAIN_TEXT,
            'plain': cls.PLAIN_TEXT,
            'json': cls.JSON,
            'csv': cls.CSV,
            'md': cls.MARKDOWN,
            'markdown': cls.MARKDOWN,
            'obsidian': cls.MARKDOWN,
        }

        if value_lower in format_map:
            return format_map[value_lower]

        valid_formats = ['html', 'html-dark', 'html-light', 'txt', 'json', 'csv', 'md']
        raise ValueError(
            f"Unknown format '{value}'. Valid formats: {', '.join(valid_formats)}"
        )

    def get_extension(self) -> str:
        """Get the file extension for this format."""
        extension_map = {
            ExportFormat.HTML_DARK: '.html',
            ExportFormat.HTML_LIGHT: '.html',
            ExportFormat.PLAIN_TEXT: '.txt',
            ExportFormat.JSON: '.json',
            ExportFormat.CSV: '.csv',
            ExportFormat.MARKDOWN: '.md',
        }
        return extension_map[self]

    def get_dce_format(self) -> str:
        """Get the DCE format value (for Markdown, use Json internally)."""
        if self == ExportFormat.MARKDOWN:
            return "Json"  # Export as JSON first, then convert
        return self.value


@dataclass
class ParsedDiscordUrl:
    """Parsed Discord URL with server, channel, and thread IDs."""
    guild_id: Optional[str] = None
    channel_id: Optional[str] = None
    thread_id: Optional[str] = None

    def get_export_target(self) -> Tuple[str, str]:
        """
        Determine export target type and ID.

        Returns:
            Tuple of (target_type, target_id) where target_type is
            'thread', 'channel', or 'guild'.
        """
        if self.thread_id:
            return ("thread", self.thread_id)
        elif self.channel_id:
            return ("channel", self.channel_id)
        elif self.guild_id:
            return ("guild", self.guild_id)
        else:
            return ("none", "")

    def get_description(self) -> str:
        """Get human-readable description of what will be exported."""
        target_type, target_id = self.get_export_target()
        if target_type == "thread":
            return f"스레드 ({target_id})"
        elif target_type == "channel":
            return f"채널 ({target_id})"
        elif target_type == "guild":
            return f"서버 전체 ({target_id})"
        else:
            return "대상 없음"


def parse_discord_url_extended(url: str) -> ParsedDiscordUrl:
    """
    Parse a Discord URL to extract guild ID, channel ID, and thread ID.

    Supports formats:
    - https://discord.com/channels/GUILD_ID/CHANNEL_ID
    - https://discord.com/channels/GUILD_ID/CHANNEL_ID/MESSAGE_ID
    - https://discord.com/channels/GUILD_ID/CHANNEL_ID/threads/THREAD_ID
    - https://discord.com/channels/@me/CHANNEL_ID (DM)

    Args:
        url: The Discord URL to parse.

    Returns:
        ParsedDiscordUrl with guild_id, channel_id, and thread_id.

    Raises:
        ValueError: If the URL format is not recognized.
    """
    url = url.strip()

    # Check for common issues
    if not url:
        raise ValueError(
            "URL이 비어있습니다.\n"
            "올바른 예시: https://discord.com/channels/123456789/987654321"
        )

    if not url.startswith(('http://', 'https://')):
        raise ValueError(
            "URL이 http:// 또는 https://로 시작해야 합니다.\n"
            f"입력값: {url[:50]}...\n"
            "올바른 예시: https://discord.com/channels/123456789/987654321"
        )

    if 'discord.com' not in url and 'discordapp.com' not in url:
        raise ValueError(
            "Discord URL이 아닙니다.\n"
            f"입력값: {url[:50]}...\n"
            "올바른 예시: https://discord.com/channels/123456789/987654321"
        )

    if '/channels/' not in url:
        raise ValueError(
            "채널 URL이 아닙니다. '/channels/'가 포함되어야 합니다.\n"
            f"입력값: {url[:50]}...\n"
            "Discord에서 채널을 열고 브라우저 주소창의 URL을 복사하세요.\n"
            "올바른 예시: https://discord.com/channels/123456789/987654321"
        )

    # Pattern for thread URLs: /channels/GUILD/CHANNEL/threads/THREAD
    thread_pattern = r'https?://(?:www\.)?(?:discord\.com|discordapp\.com)/channels/(@me|\d+)/(\d+)/threads/(\d+)'
    thread_match = re.match(thread_pattern, url)

    if thread_match:
        guild_id = thread_match.group(1)
        channel_id = thread_match.group(2)
        thread_id = thread_match.group(3)

        if guild_id == '@me':
            guild_id = None

        return ParsedDiscordUrl(
            guild_id=guild_id,
            channel_id=channel_id,
            thread_id=thread_id
        )

    # Pattern for regular channel URLs: /channels/GUILD/CHANNEL[/MESSAGE]
    channel_pattern = r'https?://(?:www\.)?(?:discord\.com|discordapp\.com)/channels/(@me|\d+)/(\d+)(?:/\d+)?'
    channel_match = re.match(channel_pattern, url)

    if channel_match:
        guild_id = channel_match.group(1)
        channel_id = channel_match.group(2)

        if guild_id == '@me':
            guild_id = None

        return ParsedDiscordUrl(
            guild_id=guild_id,
            channel_id=channel_id,
            thread_id=None
        )

    # Try to identify specific issues for better error messages
    parts = url.split('/channels/')
    if len(parts) == 2:
        path_parts = parts[1].split('/')
        if len(path_parts) < 2:
            raise ValueError(
                "채널 ID가 누락되었습니다.\n"
                f"입력값: {url}\n"
                "URL 형식: https://discord.com/channels/서버ID/채널ID"
            )
        if not path_parts[0].isdigit() and path_parts[0] != '@me':
            raise ValueError(
                f"서버 ID가 올바르지 않습니다: '{path_parts[0]}'\n"
                "서버 ID는 숫자여야 합니다."
            )
        if not path_parts[1].isdigit():
            raise ValueError(
                f"채널 ID가 올바르지 않습니다: '{path_parts[1]}'\n"
                "채널 ID는 숫자여야 합니다."
            )

    raise ValueError(
        "URL 형식을 인식할 수 없습니다.\n"
        f"입력값: {url[:50]}...\n"
        "올바른 예시: https://discord.com/channels/123456789/987654321"
    )


def parse_discord_url(url: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse a Discord channel URL to extract guild ID and channel ID.

    Supports formats:
    - https://discord.com/channels/GUILD_ID/CHANNEL_ID
    - https://discord.com/channels/@me/CHANNEL_ID (DM)
    - https://discordapp.com/channels/GUILD_ID/CHANNEL_ID

    Args:
        url: The Discord URL to parse.

    Returns:
        A tuple of (guild_id, channel_id). Guild ID may be None for DMs.

    Raises:
        ValueError: If the URL format is not recognized.
    """
    # Use extended parser and convert to legacy format
    parsed = parse_discord_url_extended(url)
    return parsed.guild_id, parsed.channel_id


def validate_channel_id(channel_id: str) -> str:
    """
    Validate that a channel ID is a valid Discord snowflake.

    Args:
        channel_id: The channel ID to validate.

    Returns:
        The validated channel ID.

    Raises:
        ValueError: If the channel ID is not valid.
    """
    # Discord snowflakes are 17-20 digit numbers
    if not channel_id:
        raise ValueError("Channel ID cannot be empty")

    if not channel_id.isdigit():
        raise ValueError(f"Channel ID must be a number, got: {channel_id}")

    if len(channel_id) < 17 or len(channel_id) > 20:
        raise ValueError(
            f"Channel ID should be 17-20 digits, got {len(channel_id)} digits"
        )

    return channel_id


def validate_guild_id(guild_id: str) -> str:
    """
    Validate that a guild ID is a valid Discord snowflake.

    Args:
        guild_id: The guild ID to validate.

    Returns:
        The validated guild ID.

    Raises:
        ValueError: If the guild ID is not valid.
    """
    if not guild_id:
        raise ValueError("Guild ID cannot be empty")

    if not guild_id.isdigit():
        raise ValueError(f"Guild ID must be a number, got: {guild_id}")

    if len(guild_id) < 17 or len(guild_id) > 20:
        raise ValueError(
            f"Guild ID should be 17-20 digits, got {len(guild_id)} digits"
        )

    return guild_id


def generate_output_filename(
    channel_id: str,
    export_format: ExportFormat,
    output_dir: Optional[Path] = None
) -> Path:
    """
    Generate an output filename for the export.

    Format: channel-<CHANNEL_ID>-<YYYYMMDD-HHMMSS>.<ext>

    Args:
        channel_id: The Discord channel ID.
        export_format: The export format.
        output_dir: Optional output directory. Defaults to current directory.

    Returns:
        The full path for the output file.
    """
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    extension = export_format.get_extension()
    filename = f"channel-{channel_id}-{timestamp}{extension}"

    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir / filename

    return Path.cwd() / filename


def generate_guild_output_filename(
    guild_id: str,
    export_format: ExportFormat,
    output_dir: Optional[Path] = None
) -> Path:
    """
    Generate an output filename pattern for guild export.

    Args:
        guild_id: The Discord guild ID.
        export_format: The export format.
        output_dir: Optional output directory.

    Returns:
        The output directory path (files will be named by DCE).
    """
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    extension = export_format.get_extension()

    if output_dir:
        output_dir = Path(output_dir)
    else:
        output_dir = Path.cwd()

    # Create a subdirectory for guild exports
    guild_dir = output_dir / f"guild-{guild_id}-{timestamp}"
    guild_dir.mkdir(parents=True, exist_ok=True)

    return guild_dir


def parse_date(date_str: str) -> str:
    """
    Parse and validate a date string.

    Accepts formats:
    - YYYY-MM-DD
    - YYYY-MM-DD HH:MM
    - YYYY-MM-DD HH:MM:SS

    Args:
        date_str: The date string to parse.

    Returns:
        The date string in a format accepted by DCE.

    Raises:
        ValueError: If the date format is not valid.
    """
    date_str = date_str.strip()

    if not date_str:
        raise ValueError("날짜가 비어있습니다.")

    formats = [
        '%Y-%m-%d',
        '%Y-%m-%d %H:%M',
        '%Y-%m-%d %H:%M:%S',
        '%Y/%m/%d',
        '%Y/%m/%d %H:%M',
        '%Y/%m/%d %H:%M:%S',
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            # Return in ISO format that DCE accepts
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            continue

    # Provide specific error guidance
    raise ValueError(
        f"날짜 형식이 올바르지 않습니다: '{date_str}'\n"
        f"올바른 형식: YYYY-MM-DD (예: 2024-01-15)"
    )


def validate_date_range(after: Optional[str], before: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Validate and parse a date range.

    Args:
        after: Start date string (optional).
        before: End date string (optional).

    Returns:
        Tuple of (parsed_after, parsed_before).

    Raises:
        ValueError: If dates are invalid or after > before.
    """
    parsed_after = None
    parsed_before = None

    if after:
        parsed_after = parse_date(after)

    if before:
        parsed_before = parse_date(before)

    # Check logical order
    if parsed_after and parsed_before:
        after_dt = datetime.strptime(parsed_after, '%Y-%m-%d %H:%M:%S')
        before_dt = datetime.strptime(parsed_before, '%Y-%m-%d %H:%M:%S')

        if after_dt >= before_dt:
            raise ValueError(
                f"시작일이 종료일보다 늦거나 같습니다.\n"
                f"시작일: {after}\n"
                f"종료일: {before}\n"
                f"시작일은 종료일보다 이전이어야 합니다."
            )

    return parsed_after, parsed_before


def validate_output_directory(path: str) -> Tuple[bool, str]:
    """
    Validate output directory, creating if necessary.

    Args:
        path: The directory path.

    Returns:
        Tuple of (is_valid, error_message).
        error_message is empty if valid.
    """
    import os

    if not path or not path.strip():
        return True, ""  # Empty means use CWD

    path = path.strip()
    dir_path = Path(path)

    try:
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            return True, ""

        if not dir_path.is_dir():
            return False, (
                f"경로가 폴더가 아닙니다: {path}\n"
                f"파일이 아닌 폴더 경로를 선택해주세요."
            )

        # Check write permission
        test_file = dir_path / ".write_test"
        try:
            test_file.touch()
            test_file.unlink()
        except PermissionError:
            return False, (
                f"폴더에 쓰기 권한이 없습니다: {path}\n"
                f"해결 방법:\n"
                f"• 다른 폴더를 선택하세요\n"
                f"• 또는 터미널에서 chmod 명령으로 권한을 변경하세요:\n"
                f"  chmod 755 \"{path}\""
            )

        return True, ""

    except PermissionError:
        return False, (
            f"폴더를 생성할 권한이 없습니다: {path}\n"
            f"해결 방법:\n"
            f"• 다른 위치를 선택하세요\n"
            f"• 또는 상위 폴더의 권한을 확인하세요"
        )
    except Exception as e:
        return False, f"폴더 접근 오류: {e}"


def validate_dce_executable(path: str) -> Tuple[bool, str]:
    """
    Validate DCE executable path and permissions.

    Args:
        path: The DCE executable path.

    Returns:
        Tuple of (is_valid, error_message).
        error_message is empty if valid.
    """
    import os
    import platform

    if not path or not path.strip():
        return False, "DCE 경로가 설정되지 않았습니다."

    path = path.strip()
    exe_path = Path(path)

    if not exe_path.exists():
        return False, (
            f"DCE 파일을 찾을 수 없습니다: {path}\n"
            f"해결 방법:\n"
            f"• 파일이 이동되었거나 삭제되었는지 확인하세요\n"
            f"• '찾아보기' 버튼으로 올바른 경로를 선택하세요"
        )

    if not exe_path.is_file():
        return False, (
            f"DCE 경로가 파일이 아닙니다: {path}\n"
            f"DiscordChatExporter.Cli 실행 파일을 선택해주세요."
        )

    # Check execution permission (macOS/Linux)
    if platform.system() != 'Windows':
        if not os.access(path, os.X_OK):
            return False, (
                f"DCE 파일에 실행 권한이 없습니다.\n"
                f"파일: {path}\n"
                f"\n"
                f"해결 방법 - 터미널에서 다음 명령을 실행하세요:\n"
                f"chmod +x \"{path}\""
            )

    return True, ""


def sanitize_error_message(message: str, token: Optional[str] = None) -> str:
    """
    Sanitize error messages to remove sensitive information.

    Args:
        message: The error message to sanitize.
        token: Optional token to specifically remove.

    Returns:
        The sanitized message.
    """
    if not message:
        return message

    sanitized = message

    # Remove any potential token patterns (Discord tokens have specific formats)
    # User tokens: start with alphanumeric, contain dots
    # Bot tokens: similar pattern

    # Generic token pattern
    token_pattern = r'[A-Za-z0-9_-]{24,}\.[A-Za-z0-9_-]{6}\.[A-Za-z0-9_-]{27,}'
    sanitized = re.sub(token_pattern, '<TOKEN>', sanitized)

    # If we have a specific token, replace it
    if token:
        sanitized = sanitized.replace(token, '<TOKEN>')

    return sanitized


def parse_dce_error(message: str) -> Tuple[str, str]:
    """
    Parse DCE error message and return user-friendly description.

    Args:
        message: The error message from DCE.

    Returns:
        Tuple of (error_type, user_friendly_message in Korean).
    """
    message_lower = message.lower()

    # Error patterns and their translations
    error_patterns = {
        # Permission/Auth errors
        'forbidden': (
            'forbidden',
            '접근 권한 없음: 이 채널에 접근할 권한이 없습니다.\n'
            '  - 채널이 비공개이거나 역할 제한이 있을 수 있습니다.\n'
            '  - 서버에서 해당 채널을 볼 수 있는지 확인하세요.'
        ),
        'unauthorized': (
            'unauthorized',
            '인증 실패: Discord 토큰이 유효하지 않습니다.\n'
            '  - 토큰이 만료되었거나 잘못되었을 수 있습니다.\n'
            '  - 새 토큰을 발급받아 다시 설정하세요.'
        ),
        'authentication': (
            'authentication',
            '인증 오류: Discord 토큰을 확인하세요.\n'
            '  - 토큰이 올바르게 입력되었는지 확인하세요.'
        ),

        # Not found errors
        'not found': (
            'not_found',
            '찾을 수 없음: 채널 또는 서버가 존재하지 않습니다.\n'
            '  - ID가 올바른지 확인하세요.\n'
            '  - 채널/서버가 삭제되었을 수 있습니다.'
        ),
        'unknown channel': (
            'unknown_channel',
            '알 수 없는 채널: 해당 채널 ID를 찾을 수 없습니다.\n'
            '  - 채널이 삭제되었거나 ID가 잘못되었습니다.'
        ),
        'unknown guild': (
            'unknown_guild',
            '알 수 없는 서버: 해당 서버 ID를 찾을 수 없습니다.\n'
            '  - 서버에서 퇴장했거나 서버가 삭제되었을 수 있습니다.'
        ),

        # Rate limit errors
        'rate limit': (
            'rate_limit',
            '요청 제한: Discord API 호출 제한에 걸렸습니다.\n'
            '  - 잠시 후 다시 시도하세요.\n'
            '  - "안전 모드"를 활성화하면 이 문제를 줄일 수 있습니다.'
        ),
        'too many requests': (
            'rate_limit',
            '너무 많은 요청: API 호출이 제한되었습니다.\n'
            '  - 1-2분 후 다시 시도하세요.'
        ),

        # Network errors
        'connection': (
            'connection',
            '연결 오류: Discord 서버에 연결할 수 없습니다.\n'
            '  - 인터넷 연결을 확인하세요.\n'
            '  - VPN을 사용 중이라면 끄고 시도해보세요.'
        ),
        'timeout': (
            'timeout',
            '시간 초과: 응답을 받지 못했습니다.\n'
            '  - 네트워크 상태를 확인하세요.\n'
            '  - 대용량 채널의 경우 시간이 오래 걸릴 수 있습니다.'
        ),
        'network': (
            'network',
            '네트워크 오류: 연결에 문제가 있습니다.\n'
            '  - 인터넷 연결을 확인하세요.'
        ),

        # Discord API errors
        'missing access': (
            'missing_access',
            '접근 권한 부족: 이 리소스에 접근할 수 없습니다.\n'
            '  - 서버 멤버인지 확인하세요.\n'
            '  - 채널 접근 권한을 확인하세요.'
        ),
        'missing permissions': (
            'missing_permissions',
            '권한 부족: 필요한 권한이 없습니다.\n'
            '  - 메시지 읽기 권한이 있는지 확인하세요.'
        ),

        # Server errors
        'internal server error': (
            'server_error',
            'Discord 서버 오류: Discord 측 문제입니다.\n'
            '  - 잠시 후 다시 시도하세요.'
        ),
        '500': (
            'server_error',
            'Discord 서버 오류 (500): 잠시 후 다시 시도하세요.'
        ),
        '502': (
            'server_error',
            'Discord 게이트웨이 오류 (502): 잠시 후 다시 시도하세요.'
        ),
        '503': (
            'server_error',
            'Discord 서비스 일시 중단 (503): 잠시 후 다시 시도하세요.'
        ),
    }

    # Check each pattern
    for pattern, (error_type, description) in error_patterns.items():
        if pattern in message_lower:
            return (error_type, description)

    # Default: return original message
    return ('unknown', f'오류 발생: {message}')


def get_error_solution(error_type: str) -> str:
    """
    Get solution suggestion for error type.

    Args:
        error_type: The error type from parse_dce_error.

    Returns:
        Solution suggestion in Korean.
    """
    solutions = {
        'forbidden': '채널 권한을 확인하거나 다른 채널을 선택하세요.',
        'unauthorized': '토큰 설정 버튼을 클릭하여 새 토큰을 입력하세요.',
        'authentication': '토큰 설정을 다시 확인하세요.',
        'not_found': 'ID가 올바른지 확인하세요.',
        'unknown_channel': '다른 채널을 선택하세요.',
        'unknown_guild': '서버 ID를 다시 확인하세요.',
        'rate_limit': '1-2분 기다린 후 다시 시도하세요.',
        'connection': '인터넷 연결을 확인하세요.',
        'timeout': '다시 시도하거나 더 작은 날짜 범위를 설정하세요.',
        'network': '인터넷 연결을 확인하세요.',
        'missing_access': '서버 멤버 여부와 채널 권한을 확인하세요.',
        'missing_permissions': '메시지 읽기 권한을 확인하세요.',
        'server_error': 'Discord 상태 페이지를 확인하고 잠시 후 다시 시도하세요.',
    }
    return solutions.get(error_type, '설정을 확인하고 다시 시도하세요.')


def convert_json_to_markdown(json_path: Path, md_path: Path) -> None:
    """
    Convert DCE JSON export to Obsidian-compatible Markdown.

    Args:
        json_path: Path to the JSON file from DCE export.
        md_path: Path for the output Markdown file.
    """
    import json

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    lines = []

    # Header with channel info
    guild_name = data.get('guild', {}).get('name', 'DM')
    channel_name = data.get('channel', {}).get('name', 'Unknown')
    channel_topic = data.get('channel', {}).get('topic', '')

    lines.append(f"# {channel_name}")
    lines.append(f"**서버**: {guild_name}")
    if channel_topic:
        lines.append(f"**주제**: {channel_topic}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Messages
    messages = data.get('messages', [])
    current_date = None

    for msg in messages:
        # Date header
        timestamp = msg.get('timestamp', '')
        if timestamp:
            date_part = timestamp[:10]  # YYYY-MM-DD
            if date_part != current_date:
                current_date = date_part
                lines.append(f"## {current_date}")
                lines.append("")

        # Author and time
        author = msg.get('author', {})
        author_name = author.get('name', 'Unknown')
        author_nickname = author.get('nickname', '')
        display_name = author_nickname or author_name

        time_part = timestamp[11:16] if len(timestamp) > 16 else ''  # HH:MM

        # Message content
        content = msg.get('content', '')

        lines.append(f"### {display_name} ({time_part})")
        if content:
            lines.append(content)

        # Attachments (Obsidian format)
        attachments = msg.get('attachments', [])
        for att in attachments:
            att_url = att.get('url', '')
            att_name = att.get('fileName', 'attachment')
            if att_url:
                # Obsidian image/file embed format
                if any(att_name.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
                    lines.append(f"![]({att_url})")
                else:
                    lines.append(f"[{att_name}]({att_url})")

        # Embeds
        embeds = msg.get('embeds', [])
        for embed in embeds:
            embed_title = embed.get('title', '')
            embed_desc = embed.get('description', '')
            embed_url = embed.get('url', '')

            if embed_title:
                if embed_url:
                    lines.append(f"> **[{embed_title}]({embed_url})**")
                else:
                    lines.append(f"> **{embed_title}**")
            if embed_desc:
                # Quote embed description
                for line in embed_desc.split('\n'):
                    lines.append(f"> {line}")

        # Reactions
        reactions = msg.get('reactions', [])
        if reactions:
            reaction_str = " ".join([
                f"{r.get('emoji', {}).get('name', '?')}({r.get('count', 0)})"
                for r in reactions
            ])
            lines.append(f"*반응: {reaction_str}*")

        lines.append("")

    # Write markdown file
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


@dataclass
class ChannelInfo:
    """Information about a Discord channel."""
    id: str
    type: str
    name: str
    category: Optional[str] = None

    def is_thread(self) -> bool:
        """Check if this is a thread."""
        return self.type.lower() in ('thread', 'publicthread', 'privatethread')

    def is_forum(self) -> bool:
        """Check if this is a forum channel."""
        return self.type.lower() in ('forum', 'forumchannel')

    def get_type_display(self) -> str:
        """Get display name for channel type."""
        type_map = {
            'textchannel': '텍스트',
            'voicechannel': '음성',
            'category': '카테고리',
            'forum': '포럼',
            'forumchannel': '포럼',
            'thread': '스레드',
            'publicthread': '스레드',
            'privatethread': '비공개 스레드',
            'announcement': '공지',
            'announcementchannel': '공지',
            'stage': '스테이지',
            'stagechannel': '스테이지',
        }
        return type_map.get(self.type.lower(), self.type)


def parse_channel_list(output: str) -> list[ChannelInfo]:
    """
    Parse DCE channel list output.

    DCE output format:
    CHANNEL_ID | [Category /] ChannelName

    Args:
        output: Raw output from DCE channels command.

    Returns:
        List of ChannelInfo objects.
    """
    channels = []

    for line in output.strip().split('\n'):
        line = line.strip()
        if not line:
            continue

        # Split by pipe separator
        parts = [p.strip() for p in line.split('|')]

        if len(parts) >= 2:
            channel_id = parts[0].strip()
            name_part = parts[1].strip()

            # Skip if ID doesn't look valid
            if not channel_id.isdigit():
                continue

            # Check for category in name (format: "Category / Name")
            category = None
            channel_name = name_part
            if ' / ' in name_part:
                cat_parts = name_part.split(' / ', 1)
                category = cat_parts[0].strip()
                channel_name = cat_parts[1].strip()

            # Type is not provided by DCE, use "채널" as default
            channel_type = "TextChannel"

            channels.append(ChannelInfo(
                id=channel_id,
                type=channel_type,
                name=channel_name,
                category=category
            ))

    return channels


def group_channels_by_category(channels: list[ChannelInfo]) -> dict[str, list[ChannelInfo]]:
    """
    Group channels by their category for display.

    Args:
        channels: List of ChannelInfo objects.

    Returns:
        Dictionary mapping category names to lists of channels.
    """
    groups: dict[str, list[ChannelInfo]] = {}

    for channel in channels:
        category = channel.category or "기타"
        if category not in groups:
            groups[category] = []
        groups[category].append(channel)

    return groups


# Keep old function name for backwards compatibility
group_channels_by_type = group_channels_by_category


def cleanup_avatar_emoji_files(
    export_path: Path,
    media_dir: Optional[Path] = None,
    log_callback: Optional[LogCallback] = None,
    delete_avatars: bool = True,
    delete_emojis: bool = True
) -> Tuple[int, int]:
    """
    Delete avatar and emoji files from media directory after export.

    DCE downloads all media to a single folder. This function parses the
    exported JSON/HTML to find avatar and emoji URLs, then deletes the
    corresponding downloaded files.

    Args:
        export_path: Path to the exported file (JSON or HTML).
        media_dir: Optional media directory. If not specified, looks for
                   {export_name}_Files folder next to the export.
        log_callback: Optional callback for logging.
        delete_avatars: Whether to delete avatar files (default True).
        delete_emojis: Whether to delete emoji files (default True).

    Returns:
        Tuple of (avatars_deleted, emojis_deleted).
    """
    import json
    import hashlib
    import os

    def log(msg: str, level: str = "INFO"):
        if log_callback:
            log_callback(LogEvent(
                level=LogLevel[level.upper()],
                message=msg
            ))

    export_path = Path(export_path)

    # Find media directory
    if media_dir is None:
        # DCE creates a folder named {export_name}_Files
        media_dir = export_path.parent / f"{export_path.stem}_Files"

    if not media_dir.exists():
        log(f"미디어 폴더 없음: {media_dir}", "WARNING")
        return (0, 0)

    # Collect URLs to delete based on patterns
    avatar_patterns = ['cdn.discordapp.com/avatars/', 'cdn.discord.com/avatars/']
    emoji_patterns = ['cdn.discordapp.com/emojis/', 'cdn.discord.com/emojis/']

    def get_dce_filename(url: str) -> Optional[str]:
        """Calculate the filename DCE would use for a given URL."""
        try:
            from urllib.parse import urlparse, parse_qs, urlencode

            parsed = urlparse(url)
            path = parsed.path

            # Get original filename from path
            original_name = path.split('/')[-1]
            if not original_name:
                return None

            # Split name and extension
            if '.' in original_name:
                name_part, ext = original_name.rsplit('.', 1)
                ext = '.' + ext
            else:
                name_part = original_name
                ext = ''

            # Truncate name to 42 chars
            name_part = name_part[:42]

            # Normalize URL by removing Discord CDN signature params
            query_params = parse_qs(parsed.query)
            # Remove ex, is, hm params
            for param in ['ex', 'is', 'hm']:
                query_params.pop(param, None)
            normalized_query = urlencode(query_params, doseq=True)
            normalized_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if normalized_query:
                normalized_url += f"?{normalized_query}"

            # Calculate hash (DCE uses first 5 chars of SHA256)
            url_hash = hashlib.sha256(normalized_url.encode()).hexdigest()[:5]

            return f"{name_part}-{url_hash}{ext}"
        except Exception:
            return None

    def find_urls_in_file(filepath: Path) -> list[str]:
        """Extract all URLs from export file."""
        urls = []
        content = filepath.read_text(encoding='utf-8', errors='ignore')

        # Find all URLs matching Discord CDN patterns
        import re
        url_pattern = r'https?://cdn\.discord(?:app)?\.com/[^\s"\'<>)}\]]*'
        urls = re.findall(url_pattern, content)

        return urls

    # Find URLs in export file
    log("미디어 파일 분석 중...")
    all_urls = find_urls_in_file(export_path)

    avatar_urls = [u for u in all_urls if any(p in u for p in avatar_patterns)] if delete_avatars else []
    emoji_urls = [u for u in all_urls if any(p in u for p in emoji_patterns)] if delete_emojis else []

    if delete_avatars or delete_emojis:
        log(f"발견: 아바타 {len(set(avatar_urls))}개, 이모지 {len(set(emoji_urls))}개")

    # Calculate filenames and delete
    avatars_deleted = 0
    emojis_deleted = 0

    if delete_avatars:
        for url in set(avatar_urls):
            filename = get_dce_filename(url)
            if filename:
                filepath = media_dir / filename
                if filepath.exists():
                    try:
                        filepath.unlink()
                        avatars_deleted += 1
                    except Exception as e:
                        log(f"삭제 실패: {filename} - {e}", "WARNING")

    if delete_emojis:
        for url in set(emoji_urls):
            filename = get_dce_filename(url)
            if filename:
                filepath = media_dir / filename
                if filepath.exists():
                    try:
                        filepath.unlink()
                        emojis_deleted += 1
                    except Exception as e:
                        log(f"삭제 실패: {filename} - {e}", "WARNING")

    if avatars_deleted > 0 or emojis_deleted > 0:
        log(f"정리 완료: 아바타 {avatars_deleted}개, 이모지 {emojis_deleted}개 삭제", "SUCCESS")

    return (avatars_deleted, emojis_deleted)
