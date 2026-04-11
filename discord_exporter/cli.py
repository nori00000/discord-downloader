#!/usr/bin/env python3
"""
Discord Exporter CLI - A wrapper for DiscordChatExporter.Cli

A cross-platform tool to easily export Discord chat logs.
"""

import argparse
import getpass
import sys
from pathlib import Path
from typing import Optional

from . import __version__
from .config import ConfigManager
from .exporter import (
    DCENotFoundError,
    Exporter,
    ExportError,
    ExportOptions,
    TokenNotConfiguredError,
)
from .utils import (
    ExportFormat,
    parse_date,
    parse_discord_url,
    validate_channel_id,
    validate_guild_id,
)


def print_error(message: str) -> None:
    """Print an error message to stderr."""
    print(f"Error: {message}", file=sys.stderr)


def print_success(message: str) -> None:
    """Print a success message."""
    print(f"✓ {message}")


def prompt_for_token() -> str:
    """Prompt user for Discord token securely."""
    print("\n디스코드 토큰이 설정되어 있지 않습니다.")
    print("토큰을 입력해 주세요 (입력 내용은 표시되지 않습니다):")
    print()

    try:
        token = getpass.getpass("Discord Token: ")
        if not token.strip():
            print_error("토큰이 입력되지 않았습니다.")
            sys.exit(1)
        return token.strip()
    except KeyboardInterrupt:
        print("\n취소되었습니다.")
        sys.exit(1)


def prompt_for_dce_path() -> str:
    """Prompt user for DCE path."""
    print("\nDiscordChatExporter.Cli 경로가 설정되어 있지 않습니다.")
    print("실행 파일의 전체 경로를 입력해 주세요:")
    print()
    print("예시:")
    print("  macOS: ~/Downloads/DiscordChatExporter.Cli.osx-arm64/DiscordChatExporter.Cli")
    print("  Windows: C:\\Tools\\DiscordChatExporter\\DiscordChatExporter.Cli.exe")
    print()

    try:
        path = input("DCE Path: ").strip()
        if not path:
            print_error("경로가 입력되지 않았습니다.")
            sys.exit(1)

        # Expand user path
        expanded = Path(path).expanduser()
        if not expanded.exists():
            print_error(f"파일을 찾을 수 없습니다: {expanded}")
            sys.exit(1)

        return str(expanded)
    except KeyboardInterrupt:
        print("\n취소되었습니다.")
        sys.exit(1)


def ensure_configured(config: ConfigManager) -> None:
    """Ensure token and DCE path are configured."""
    # Check token
    if not config.get_token():
        token = prompt_for_token()
        config.set_token(token)
        print_success("토큰이 저장되었습니다.")

    # Check DCE path
    if not config.get_dce_path():
        dce_path = prompt_for_dce_path()
        config.set_dce_path(dce_path)
        print_success("DCE 경로가 저장되었습니다.")


def cmd_setup(args: argparse.Namespace) -> int:
    """Handle setup command."""
    config = ConfigManager()

    print("Discord Exporter 설정")
    print("=" * 40)

    # Token setup
    if args.token:
        config.set_token(args.token)
        print_success("토큰이 저장되었습니다.")
    else:
        current_token = config.get_token()
        if current_token:
            masked = config.mask_token(current_token)
            print(f"현재 토큰: {masked}")
            change = input("토큰을 변경하시겠습니까? (y/N): ").strip().lower()
            if change == 'y':
                token = prompt_for_token()
                config.set_token(token)
                print_success("토큰이 저장되었습니다.")
        else:
            token = prompt_for_token()
            config.set_token(token)
            print_success("토큰이 저장되었습니다.")

    # DCE path setup
    if args.dce_path:
        expanded = Path(args.dce_path).expanduser()
        if not expanded.exists():
            print_error(f"파일을 찾을 수 없습니다: {expanded}")
            return 1
        config.set_dce_path(str(expanded))
        print_success("DCE 경로가 저장되었습니다.")
    else:
        current_path = config.get_dce_path()
        if current_path:
            print(f"현재 DCE 경로: {current_path}")
            change = input("경로를 변경하시겠습니까? (y/N): ").strip().lower()
            if change == 'y':
                dce_path = prompt_for_dce_path()
                config.set_dce_path(dce_path)
                print_success("DCE 경로가 저장되었습니다.")
        else:
            dce_path = prompt_for_dce_path()
            config.set_dce_path(dce_path)
            print_success("DCE 경로가 저장되었습니다.")

    print()
    print(f"설정 파일 위치: {config.get_config_path()}")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    """Handle export command."""
    config = ConfigManager()
    ensure_configured(config)

    # Determine channel ID
    channel_id: Optional[str] = None
    if args.url:
        try:
            _, channel_id = parse_discord_url(args.url)
        except ValueError as e:
            print_error(str(e))
            return 1
    elif args.channel_id:
        try:
            channel_id = validate_channel_id(args.channel_id)
        except ValueError as e:
            print_error(str(e))
            return 1
    else:
        print_error("--url 또는 --channel-id 중 하나를 지정해야 합니다.")
        return 1

    try:
        options = parse_common_export_options(args)
    except ValueError as e:
        print_error(str(e))
        return 1
    options.channel_id = channel_id

    try:
        exporter = Exporter(config)
        output_path = exporter.export_channel(options)
        print_success(f"내보내기 완료: {output_path}")
        return 0
    except (ExportError, DCENotFoundError, TokenNotConfiguredError) as e:
        print_error(str(e))
        return 1


def cmd_exportguild(args: argparse.Namespace) -> int:
    """Handle exportguild command."""
    config = ConfigManager()
    ensure_configured(config)

    guild_id: Optional[str] = None
    if args.url:
        try:
            guild_id, _ = parse_discord_url(args.url)
            if not guild_id:
                print_error("URL에서 서버 ID를 찾을 수 없습니다.")
                return 1
        except ValueError as e:
            print_error(str(e))
            return 1
    elif args.guild_id:
        try:
            guild_id = validate_guild_id(args.guild_id)
        except ValueError as e:
            print_error(str(e))
            return 1
    else:
        print_error("--url 또는 --guild-id 중 하나를 지정해야 합니다.")
        return 1

    try:
        options = parse_common_export_options(args)
    except ValueError as e:
        print_error(str(e))
        return 1
    options.guild_id = guild_id

    try:
        exporter = Exporter(config)
        output_path = exporter.export_guild(options)
        print_success(f"서버 내보내기 완료: {output_path}")
        return 0
    except (ExportError, DCENotFoundError, TokenNotConfiguredError) as e:
        print_error(str(e))
        return 1


def cmd_exportdm(args: argparse.Namespace) -> int:
    """Handle exportdm command."""
    config = ConfigManager()
    ensure_configured(config)

    try:
        options = parse_common_export_options(args)
    except ValueError as e:
        print_error(str(e))
        return 1
    # DM channels have no threads; drop include_threads even if the user
    # passed it, to match legacy behavior and avoid a DCE error.
    options.include_threads = None

    try:
        exporter = Exporter(config)
        output_path = exporter.export_dm(options)
        print_success(f"DM 내보내기 완료: {output_path}")
        return 0
    except (ExportError, DCENotFoundError, TokenNotConfiguredError) as e:
        print_error(str(e))
        return 1


def cmd_list_guilds(args: argparse.Namespace) -> int:
    """Handle list-guilds command."""
    config = ConfigManager()
    ensure_configured(config)

    try:
        exporter = Exporter(config)
        output = exporter.list_guilds()
        print(output)
        return 0
    except (ExportError, DCENotFoundError, TokenNotConfiguredError) as e:
        print_error(str(e))
        return 1


def cmd_list_channels(args: argparse.Namespace) -> int:
    """Handle list-channels command."""
    config = ConfigManager()
    ensure_configured(config)

    # Determine guild ID
    guild_id: Optional[str] = None

    if args.url:
        try:
            guild_id, _ = parse_discord_url(args.url)
            if not guild_id:
                print_error("URL에서 서버 ID를 찾을 수 없습니다.")
                return 1
        except ValueError as e:
            print_error(str(e))
            return 1
    elif args.guild_id:
        try:
            guild_id = validate_guild_id(args.guild_id)
        except ValueError as e:
            print_error(str(e))
            return 1
    else:
        print_error("--url 또는 --guild-id 중 하나를 지정해야 합니다.")
        return 1

    try:
        exporter = Exporter(config)
        output = exporter.list_channels(guild_id)
        print(output)
        return 0
    except (ExportError, DCENotFoundError, TokenNotConfiguredError) as e:
        print_error(str(e))
        return 1


def cmd_list_dm(args: argparse.Namespace) -> int:
    """Handle list-dm command."""
    config = ConfigManager()
    ensure_configured(config)

    try:
        exporter = Exporter(config)
        output = exporter.list_dm_channels()
        print(output)
        return 0
    except (ExportError, DCENotFoundError, TokenNotConfiguredError) as e:
        print_error(str(e))
        return 1


# Formats accepted by `-f/--format`. These are the user-facing strings;
# ExportFormat.from_string() resolves aliases and case-insensitivity, so we
# keep this list for argparse help/tab completion without restricting it.
CLI_FORMATS = [
    'html', 'html-dark', 'html-light',
    'txt', 'json', 'csv',
    'md', 'obsidian',
]


def add_common_export_args(parser: argparse.ArgumentParser) -> None:
    """Add common export arguments to a parser."""
    parser.add_argument(
        '-f', '--format',
        default='html',
        help=(
            '출력 형식: ' + ', '.join(CLI_FORMATS) +
            ' (기본값: html, md/obsidian은 Obsidian-friendly Markdown)'
        ),
    )
    parser.add_argument(
        '-o', '--output-dir',
        help='출력 디렉터리 경로 (기본값: 현재 디렉터리)'
    )
    parser.add_argument(
        '--after',
        help='이 날짜 이후의 메시지만 내보내기 (형식: YYYY-MM-DD)'
    )
    parser.add_argument(
        '--before',
        help='이 날짜 이전의 메시지만 내보내기 (형식: YYYY-MM-DD)'
    )
    parser.add_argument(
        '--media',
        action='store_true',
        help='첨부파일과 이미지도 함께 다운로드'
    )
    parser.add_argument(
        '--include-threads',
        choices=['none', 'active', 'all'],
        help='스레드 포함 여부: none, active, all'
    )


def parse_common_export_options(args: argparse.Namespace) -> ExportOptions:
    """
    Parse shared export options (format + date range + output_dir + media)
    from argparse into an ExportOptions instance.

    Raises:
        ValueError: If format or date strings are invalid. The caller is
                    responsible for catching and printing the error.
    """
    export_format = ExportFormat.from_string(args.format)

    after = parse_date(args.after) if args.after else None
    before = parse_date(args.before) if args.before else None

    return ExportOptions(
        export_format=export_format,
        output_dir=Path(args.output_dir) if args.output_dir else None,
        after=after,
        before=before,
        media=args.media,
        include_threads=getattr(args, 'include_threads', None),
    )


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog='discord-exporter',
        description='Discord 채팅 로그를 쉽게 내보내기 위한 CLI 도구',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # 초기 설정
  discord-exporter setup

  # 채널 URL로 내보내기
  discord-exporter export --url "https://discord.com/channels/123/456" --format html

  # 채널 ID로 내보내기
  discord-exporter export --channel-id 1234567890123456789 --format txt

  # 날짜 범위 지정
  discord-exporter export --channel-id 123 --after "2024-01-01" --before "2024-12-31"

  # 서버 전체 내보내기
  discord-exporter exportguild --guild-id 1234567890123456789

  # DM 전체 내보내기
  discord-exporter exportdm --format json
        """
    )

    parser.add_argument(
        '-v', '--version',
        action='version',
        version=f'%(prog)s {__version__}'
    )

    subparsers = parser.add_subparsers(
        dest='command',
        title='명령어',
        description='사용 가능한 명령어'
    )

    # Setup command
    setup_parser = subparsers.add_parser(
        'setup',
        help='토큰과 DCE 경로 설정'
    )
    setup_parser.add_argument(
        '--token',
        help='Discord 토큰 (대화형 입력 대신 직접 지정)'
    )
    setup_parser.add_argument(
        '--dce-path',
        help='DiscordChatExporter.Cli 실행 파일 경로'
    )
    setup_parser.set_defaults(func=cmd_setup)

    # Export command
    export_parser = subparsers.add_parser(
        'export',
        help='단일 채널 내보내기'
    )
    export_input = export_parser.add_mutually_exclusive_group(required=True)
    export_input.add_argument(
        '--url',
        help='Discord 채널 URL'
    )
    export_input.add_argument(
        '-c', '--channel-id',
        help='Discord 채널 ID'
    )
    add_common_export_args(export_parser)
    export_parser.set_defaults(func=cmd_export)

    # Export guild command
    exportguild_parser = subparsers.add_parser(
        'exportguild',
        help='서버(길드)의 모든 채널 내보내기'
    )
    guild_input = exportguild_parser.add_mutually_exclusive_group(required=True)
    guild_input.add_argument(
        '--url',
        help='Discord 서버 URL (아무 채널 URL)'
    )
    guild_input.add_argument(
        '-g', '--guild-id',
        help='Discord 서버(길드) ID'
    )
    add_common_export_args(exportguild_parser)
    exportguild_parser.set_defaults(func=cmd_exportguild)

    # Export DM command
    exportdm_parser = subparsers.add_parser(
        'exportdm',
        help='모든 DM 채널 내보내기'
    )
    add_common_export_args(exportdm_parser)
    exportdm_parser.set_defaults(func=cmd_exportdm)

    # List guilds command
    list_guilds_parser = subparsers.add_parser(
        'list-guilds',
        help='접근 가능한 서버 목록 조회'
    )
    list_guilds_parser.set_defaults(func=cmd_list_guilds)

    # List channels command
    list_channels_parser = subparsers.add_parser(
        'list-channels',
        help='서버의 채널 목록 조회'
    )
    channels_input = list_channels_parser.add_mutually_exclusive_group(required=True)
    channels_input.add_argument(
        '--url',
        help='Discord 서버 URL'
    )
    channels_input.add_argument(
        '-g', '--guild-id',
        help='Discord 서버(길드) ID'
    )
    list_channels_parser.set_defaults(func=cmd_list_channels)

    # List DM command
    list_dm_parser = subparsers.add_parser(
        'list-dm',
        help='DM 채널 목록 조회'
    )
    list_dm_parser.set_defaults(func=cmd_list_dm)

    return parser


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
