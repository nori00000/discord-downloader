#!/usr/bin/env python3
"""
Discord Exporter GUI - Tkinter-based graphical interface.

A cross-platform GUI wrapper for DiscordChatExporter.Cli.
"""

import os
import queue
import random
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Optional

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
    LogEvent,
    LogLevel,
    ParsedDiscordUrl,
    cleanup_avatar_emoji_files,
    get_error_solution,
    group_channels_by_type,
    parse_channel_list,
    parse_date,
    parse_dce_error,
    parse_discord_url_extended,
    sanitize_error_message,
    validate_channel_id,
    validate_date_range,
    validate_dce_executable,
    validate_output_directory,
)


class DiscordExporterGUI:
    """Main GUI application for Discord Exporter."""

    # Application constants
    TITLE = "Discord Exporter"
    MIN_WIDTH = 700
    MIN_HEIGHT = 750
    QUEUE_POLL_MS = 100  # Poll queue every 100ms

    # Format options for dropdown
    FORMAT_OPTIONS = [
        ("HTML (Dark)", ExportFormat.HTML_DARK),
        ("HTML (Light)", ExportFormat.HTML_LIGHT),
        ("Markdown (Obsidian)", ExportFormat.MARKDOWN),
        ("Plain Text", ExportFormat.PLAIN_TEXT),
        ("JSON", ExportFormat.JSON),
        ("CSV", ExportFormat.CSV),
    ]

    # Error solutions for user guidance
    ERROR_SOLUTIONS = {
        "token": "상태바의 '토큰 설정' 버튼을 클릭하여 Discord 토큰을 입력하세요.",
        "dce_path": "상태바의 '찾아보기' 버튼을 클릭하여 DCE 실행 파일을 선택하세요.",
        "dce_not_found": "DCE 파일이 삭제되었거나 이동되었습니다. 경로를 다시 설정하세요.",
        "channel": "올바른 Discord 채널 URL 또는 채널 ID를 입력하세요.",
        "permission": "출력 폴더에 쓰기 권한이 있는지 확인하거나, 다른 폴더를 선택하세요.",
        "network": "인터넷 연결을 확인하고, Discord 토큰이 유효한지 확인하세요.",
    }

    def __init__(self):
        """Initialize the GUI application."""
        self.root = tk.Tk()
        self.root.title(self.TITLE)
        self.root.minsize(self.MIN_WIDTH, self.MIN_HEIGHT)

        # Configuration manager
        self.config = ConfigManager()

        # State variables
        self.selected_format = tk.StringVar(value="HTML (Dark)")
        self.media_enabled = tk.BooleanVar(value=False)
        self.exclude_avatars = tk.BooleanVar(value=True)  # Default: exclude avatars
        self.exclude_emojis = tk.BooleanVar(value=True)  # Default: exclude emojis
        self.include_threads = tk.StringVar(value="all")  # "none", "active", "all"
        self.safe_mode = tk.BooleanVar(value=True)  # Default: safe mode ON
        # Delay between exports. Users set a min/max window and press the
        # "랜덤" button to pick a value in [min, max]; the picked value is
        # applied before each DCE invocation.
        self.delay_min = tk.StringVar(value="0")
        self.delay_max = tk.StringVar(value="0")
        self.current_delay = tk.StringVar(value="0.0")
        self.is_running = False

        # Parsed URL state
        self.parsed_url: Optional[ParsedDiscordUrl] = None
        self._channel_list_loading = False

        # Threading
        self.log_queue = queue.Queue()
        self.export_thread: Optional[threading.Thread] = None
        self.exporter: Optional[Exporter] = None  # For cancellation

        # Build UI
        self._create_widgets()
        self._update_status_bar()

        # Load saved settings
        self._load_settings()

        # Start queue polling
        self._poll_log_queue()

        # Save settings on close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_widgets(self):
        """Create all GUI widgets."""
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Create sections
        self._create_status_bar(main_frame)
        self._create_input_area(main_frame)
        self._create_execution_area(main_frame)
        self._create_log_area(main_frame)

    # =========================================================================
    # Status Bar
    # =========================================================================
    def _create_status_bar(self, parent):
        """Create the top status bar."""
        frame = ttk.LabelFrame(parent, text="상태", padding="5")
        frame.pack(fill=tk.X, pady=(0, 10))

        # Token status
        token_frame = ttk.Frame(frame)
        token_frame.pack(fill=tk.X, pady=2)

        ttk.Label(token_frame, text="토큰:").pack(side=tk.LEFT)
        self.lbl_token_status = ttk.Label(token_frame, text="확인 중...")
        self.lbl_token_status.pack(side=tk.LEFT, padx=(5, 20))

        ttk.Button(
            token_frame,
            text="토큰 설정",
            command=self._on_set_token,
            width=12
        ).pack(side=tk.LEFT)

        # DCE path status
        dce_frame = ttk.Frame(frame)
        dce_frame.pack(fill=tk.X, pady=2)

        ttk.Label(dce_frame, text="DCE:").pack(side=tk.LEFT)
        self.lbl_dce_status = ttk.Label(dce_frame, text="확인 중...")
        self.lbl_dce_status.pack(side=tk.LEFT, padx=(5, 20))

        ttk.Button(
            dce_frame,
            text="찾아보기",
            command=self._on_browse_dce,
            width=12
        ).pack(side=tk.LEFT)

    def _update_status_bar(self):
        """Update the status bar with current configuration."""
        # Token status - NEVER show actual token
        token = self.config.get_token()
        if token:
            self.lbl_token_status.config(
                text="✓ 설정됨",
                foreground="green"
            )
        else:
            self.lbl_token_status.config(
                text="✗ 미설정",
                foreground="red"
            )

        # DCE path status
        dce_path = self.config.get_dce_path()
        if dce_path:
            # Show abbreviated path
            display_path = self._abbreviate_path(dce_path)
            self.lbl_dce_status.config(
                text=f"✓ {display_path}",
                foreground="green"
            )
        else:
            self.lbl_dce_status.config(
                text="✗ 미설정",
                foreground="red"
            )

    def _abbreviate_path(self, path: str, max_len: int = 40) -> str:
        """Abbreviate a path for display."""
        if len(path) <= max_len:
            return path
        # Show start and end
        return f"{path[:15]}...{path[-22:]}"

    # =========================================================================
    # Input Area
    # =========================================================================
    def _create_input_area(self, parent):
        """Create the input area with 3-field layout."""
        frame = ttk.LabelFrame(parent, text="내보내기 설정", padding="10")
        frame.pack(fill=tk.X, pady=(0, 10))

        # URL input with parse button
        url_frame = ttk.Frame(frame)
        url_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(url_frame, text="Discord URL:", width=12).pack(side=tk.LEFT)

        self.ent_url = ttk.Entry(url_frame)
        self.ent_url.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 5))
        self._add_context_menu(self.ent_url)

        # Placeholder and auto-parse on paste
        self._set_placeholder(
            self.ent_url,
            "https://discord.com/channels/서버/채널 또는 스레드 URL"
        )
        self.ent_url.bind("<KeyRelease>", self._on_url_change)

        ttk.Button(
            url_frame,
            text="분석",
            command=self._on_parse_url,
            width=8
        ).pack(side=tk.LEFT)

        # ID fields frame (3 fields in a row)
        id_frame = ttk.LabelFrame(frame, text="ID (자동 입력 또는 직접 수정)", padding="5")
        id_frame.pack(fill=tk.X, pady=(0, 10))

        id_inner = ttk.Frame(id_frame)
        id_inner.pack(fill=tk.X)

        # Server ID
        ttk.Label(id_inner, text="서버:", width=6).pack(side=tk.LEFT)
        self.ent_server_id = ttk.Entry(id_inner, width=22)
        self.ent_server_id.pack(side=tk.LEFT, padx=(0, 10))
        self._add_context_menu(self.ent_server_id)

        # Channel ID
        ttk.Label(id_inner, text="채널:", width=6).pack(side=tk.LEFT)
        self.ent_channel_id = ttk.Entry(id_inner, width=22)
        self.ent_channel_id.pack(side=tk.LEFT, padx=(0, 10))
        self._add_context_menu(self.ent_channel_id)

        # Thread ID
        ttk.Label(id_inner, text="스레드:", width=7).pack(side=tk.LEFT)
        self.ent_thread_id = ttk.Entry(id_inner, width=22)
        self.ent_thread_id.pack(side=tk.LEFT)
        self._add_context_menu(self.ent_thread_id)

        # Bind changes to update export target
        self.ent_server_id.bind("<KeyRelease>", self._on_id_change)
        self.ent_channel_id.bind("<KeyRelease>", self._on_id_change)
        self.ent_thread_id.bind("<KeyRelease>", self._on_id_change)

        # Channel list button
        list_btn_frame = ttk.Frame(id_frame)
        list_btn_frame.pack(fill=tk.X, pady=(5, 0))

        ttk.Button(
            list_btn_frame,
            text="채널 목록 조회",
            command=self._on_list_channels,
            width=15
        ).pack(side=tk.LEFT)

        # Filter options
        self.filter_text_only = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            list_btn_frame,
            text="텍스트만",
            variable=self.filter_text_only
        ).pack(side=tk.LEFT, padx=(10, 0))

        self.filter_accessible = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            list_btn_frame,
            text="접근가능만",
            variable=self.filter_accessible
        ).pack(side=tk.LEFT, padx=(5, 0))

        # Channel list Treeview
        channel_frame = ttk.LabelFrame(frame, text="채널 목록 (클릭하여 선택, 더블클릭으로 체크)", padding="5")
        channel_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Treeview with scrollbar
        tree_container = ttk.Frame(channel_frame)
        tree_container.pack(fill=tk.BOTH, expand=True)

        self.channel_tree = ttk.Treeview(
            tree_container,
            columns=("check", "type", "id"),
            show="tree headings",
            height=6,
            selectmode="extended"  # Allow multiple selection
        )
        self.channel_tree.heading("#0", text="채널명", anchor=tk.W)
        self.channel_tree.heading("check", text="✓", anchor=tk.CENTER)
        self.channel_tree.heading("type", text="유형", anchor=tk.W)
        self.channel_tree.heading("id", text="ID", anchor=tk.W)

        self.channel_tree.column("#0", width=180, minwidth=150)
        self.channel_tree.column("check", width=30, minwidth=30, anchor=tk.CENTER)
        self.channel_tree.column("type", width=60, minwidth=50)
        self.channel_tree.column("id", width=160, minwidth=150)

        tree_scroll = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=self.channel_tree.yview)
        self.channel_tree.configure(yscrollcommand=tree_scroll.set)

        self.channel_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Track checked items: {item_id: channel_id}
        self._checked_channels: dict[str, str] = {}

        # Bind events
        self.channel_tree.bind("<Double-1>", self._on_channel_double_click)
        self.channel_tree.bind("<<TreeviewSelect>>", self._on_channel_select)

        # Checkbox control buttons
        check_btn_frame = ttk.Frame(channel_frame)
        check_btn_frame.pack(fill=tk.X, pady=(5, 0))

        ttk.Button(
            check_btn_frame,
            text="선택 항목 체크",
            command=self._check_selected_channels,
            width=15
        ).pack(side=tk.LEFT)

        ttk.Button(
            check_btn_frame,
            text="체크 해제",
            command=self._uncheck_all_channels,
            width=10
        ).pack(side=tk.LEFT, padx=(5, 0))

        ttk.Button(
            check_btn_frame,
            text="전체 체크",
            command=self._check_all_channels,
            width=10
        ).pack(side=tk.LEFT, padx=(5, 0))

        # Export target display
        target_frame = ttk.Frame(frame)
        target_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(target_frame, text="내보내기 대상:").pack(side=tk.LEFT)
        self.lbl_export_target = ttk.Label(
            target_frame,
            text="URL을 입력하세요",
            foreground="gray"
        )
        self.lbl_export_target.pack(side=tk.LEFT, padx=(10, 0))

        # Thread option (for guild export)
        thread_opt_frame = ttk.Frame(frame)
        thread_opt_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(thread_opt_frame, text="스레드 포함:", width=12).pack(side=tk.LEFT)

        self.cmb_threads = ttk.Combobox(
            thread_opt_frame,
            textvariable=self.include_threads,
            values=["none", "active", "all"],
            state="readonly",
            width=15
        )
        self.cmb_threads.pack(side=tk.LEFT, padx=(5, 10))
        self.cmb_threads.current(2)  # Default to "all"

        ttk.Label(
            thread_opt_frame,
            text="(서버 전체 내보내기 시 적용)",
            foreground="gray"
        ).pack(side=tk.LEFT)

        # Format selection
        format_frame = ttk.Frame(frame)
        format_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(format_frame, text="출력 형식:", width=12).pack(side=tk.LEFT)

        format_names = [f[0] for f in self.FORMAT_OPTIONS]
        self.cmb_format = ttk.Combobox(
            format_frame,
            textvariable=self.selected_format,
            values=format_names,
            state="readonly",
            width=20
        )
        self.cmb_format.pack(side=tk.LEFT, padx=(5, 0))
        self.cmb_format.current(0)

        # Output directory
        output_frame = ttk.Frame(frame)
        output_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(output_frame, text="출력 폴더:", width=12).pack(side=tk.LEFT)

        self.ent_output_dir = ttk.Entry(output_frame)
        self.ent_output_dir.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 5))
        self.ent_output_dir.insert(0, str(Path.cwd()))
        self._add_context_menu(self.ent_output_dir)

        ttk.Button(
            output_frame,
            text="찾아보기",
            command=self._on_browse_output,
            width=10
        ).pack(side=tk.LEFT)

        # Date range (optional)
        date_frame = ttk.LabelFrame(frame, text="날짜 범위 (선택)", padding="5")
        date_frame.pack(fill=tk.X, pady=(0, 10))

        date_inner = ttk.Frame(date_frame)
        date_inner.pack(fill=tk.X)

        ttk.Label(date_inner, text="시작일:").pack(side=tk.LEFT)
        self.ent_after = ttk.Entry(date_inner, width=15)
        self.ent_after.pack(side=tk.LEFT, padx=(5, 20))
        self._set_placeholder(self.ent_after, "YYYY-MM-DD")

        ttk.Label(date_inner, text="종료일:").pack(side=tk.LEFT)
        self.ent_before = ttk.Entry(date_inner, width=15)
        self.ent_before.pack(side=tk.LEFT, padx=(5, 0))
        self._set_placeholder(self.ent_before, "YYYY-MM-DD")

        # Options frame
        options_frame = ttk.Frame(frame)
        options_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Checkbutton(
            options_frame,
            text="미디어 다운로드",
            variable=self.media_enabled,
            command=self._on_media_toggle
        ).pack(side=tk.LEFT)

        ttk.Checkbutton(
            options_frame,
            text="안전 모드 (느리지만 안전)",
            variable=self.safe_mode
        ).pack(side=tk.LEFT, padx=(20, 0))

        # Media exclusion options (second row)
        media_options_frame = ttk.Frame(frame)
        media_options_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(
            media_options_frame,
            text="   └ 제외:",
            foreground="gray"
        ).pack(side=tk.LEFT)

        self.chk_exclude_avatars = ttk.Checkbutton(
            media_options_frame,
            text="프로필 이미지",
            variable=self.exclude_avatars
        )
        self.chk_exclude_avatars.pack(side=tk.LEFT)

        self.chk_exclude_emojis = ttk.Checkbutton(
            media_options_frame,
            text="이모지",
            variable=self.exclude_emojis
        )
        self.chk_exclude_emojis.pack(side=tk.LEFT, padx=(10, 0))

        # Initially disable if media not enabled
        self._on_media_toggle()

        # Safe mode info
        ttk.Label(
            frame,
            text="※ 안전 모드: Rate Limit 준수 (기본 ON)",
            foreground="gray",
            font=("TkDefaultFont", 9)
        ).pack(anchor=tk.W)

        # Delay configuration: min/max window + random picker
        delay_frame = ttk.Frame(frame)
        delay_frame.pack(fill=tk.X, pady=(5, 0))

        ttk.Label(delay_frame, text="지연 (초):").pack(side=tk.LEFT)
        ttk.Label(delay_frame, text="최소").pack(side=tk.LEFT, padx=(8, 2))
        self.ent_delay_min = ttk.Entry(
            delay_frame, textvariable=self.delay_min, width=6
        )
        self.ent_delay_min.pack(side=tk.LEFT)
        ttk.Label(delay_frame, text="최대").pack(side=tk.LEFT, padx=(8, 2))
        self.ent_delay_max = ttk.Entry(
            delay_frame, textvariable=self.delay_max, width=6
        )
        self.ent_delay_max.pack(side=tk.LEFT)
        ttk.Button(
            delay_frame,
            text="랜덤",
            command=self._on_randomize_delay,
            width=6,
        ).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Label(delay_frame, text="현재:").pack(side=tk.LEFT, padx=(12, 2))
        ttk.Label(
            delay_frame,
            textvariable=self.current_delay,
            foreground="blue",
        ).pack(side=tk.LEFT)
        ttk.Label(delay_frame, text="초", foreground="gray").pack(side=tk.LEFT)

    def _parse_delay_bounds(self) -> tuple[float, float]:
        """Parse min/max delay fields. Invalid values collapse to 0.

        Returns ``(lo, hi)`` with ``lo <= hi`` and both >= 0. Non-numeric
        input or negatives are silently treated as 0 so the UI never
        raises — the worst case is that no delay is applied.
        """
        def _clean(raw: str) -> float:
            try:
                value = float(raw.strip())
            except (ValueError, AttributeError):
                return 0.0
            return max(0.0, value)

        lo = _clean(self.delay_min.get())
        hi = _clean(self.delay_max.get())
        if hi < lo:
            lo, hi = hi, lo
        return lo, hi

    def _on_randomize_delay(self):
        """Pick a random delay in [min, max] and update the display."""
        lo, hi = self._parse_delay_bounds()
        picked = random.uniform(lo, hi) if hi > 0 else 0.0
        self.current_delay.set(f"{picked:.2f}")
        self._log(f"랜덤 지연 적용: {picked:.2f}초 (범위 {lo:.2f}~{hi:.2f})")

    def _get_current_delay(self) -> float:
        """Return the currently-applied delay in seconds (0 if unset)."""
        try:
            return max(0.0, float(self.current_delay.get()))
        except (ValueError, AttributeError):
            return 0.0

    def _on_media_toggle(self):
        """Enable/disable exclude options based on media checkbox."""
        if self.media_enabled.get():
            self.chk_exclude_avatars.state(['!disabled'])
            self.chk_exclude_emojis.state(['!disabled'])
        else:
            self.chk_exclude_avatars.state(['disabled'])
            self.chk_exclude_emojis.state(['disabled'])

    def _on_url_change(self, event=None):
        """Handle URL field changes - auto-parse after typing stops."""
        # Simple auto-parse when URL looks complete
        url = self.ent_url.get().strip()
        if url.startswith("https://discord.com/channels/") and url.count("/") >= 4:
            self._on_parse_url()

    def _on_parse_url(self):
        """Parse the URL and fill ID fields."""
        url = self.ent_url.get().strip()

        # Skip if placeholder
        if not url or "discord.com/channels" not in url:
            return

        try:
            parsed = parse_discord_url_extended(url)
            self.parsed_url = parsed

            # Fill ID fields
            self.ent_server_id.delete(0, tk.END)
            self.ent_channel_id.delete(0, tk.END)
            self.ent_thread_id.delete(0, tk.END)

            if parsed.guild_id:
                self.ent_server_id.insert(0, parsed.guild_id)
            if parsed.channel_id:
                self.ent_channel_id.insert(0, parsed.channel_id)
            if parsed.thread_id:
                self.ent_thread_id.insert(0, parsed.thread_id)

            # Update export target display
            self._update_export_target()

        except ValueError:
            self.lbl_export_target.config(
                text="URL 오류",
                foreground="red"
            )

    def _on_id_change(self, event=None):
        """Handle ID field changes."""
        self._update_export_target()

    def _update_export_target(self):
        """Update the export target display based on current ID fields or checked channels."""
        # Check for checked channels first
        checked_count = len(self._checked_channels) if hasattr(self, '_checked_channels') else 0

        if checked_count > 0:
            self.lbl_export_target.config(
                text=f"체크된 채널 {checked_count}개",
                foreground="blue"
            )
            return

        server_id = self.ent_server_id.get().strip()
        channel_id = self.ent_channel_id.get().strip()
        thread_id = self.ent_thread_id.get().strip()

        # Store parsed state
        self.parsed_url = ParsedDiscordUrl(
            guild_id=server_id if server_id else None,
            channel_id=channel_id if channel_id else None,
            thread_id=thread_id if thread_id else None
        )

        # Determine target
        if thread_id:
            self.lbl_export_target.config(
                text=f"스레드 ({thread_id})",
                foreground="blue"
            )
        elif channel_id:
            self.lbl_export_target.config(
                text=f"채널 ({channel_id})",
                foreground="green"
            )
        elif server_id:
            self.lbl_export_target.config(
                text=f"서버 전체 ({server_id})",
                foreground="purple"
            )
        else:
            self.lbl_export_target.config(
                text="URL 또는 ID를 입력하세요",
                foreground="gray"
            )

    def _on_list_channels(self):
        """Fetch and display channel list from server."""
        server_id = self.ent_server_id.get().strip()

        if not server_id:
            messagebox.showwarning(
                "서버 ID 필요",
                "채널 목록을 조회하려면 먼저 서버 ID를 입력하세요."
            )
            return

        # Check token and DCE path
        if not self.config.get_token():
            messagebox.showwarning("토큰 필요", "먼저 토큰을 설정하세요.")
            return

        if not self.config.get_dce_path():
            messagebox.showwarning("DCE 필요", "먼저 DCE 경로를 설정하세요.")
            return

        # Clear existing items
        for item in self.channel_tree.get_children():
            self.channel_tree.delete(item)

        self._log(f"채널 목록 조회 중: {server_id}...")
        self._log("(서버 크기에 따라 10초~1분 소요될 수 있음)", "WARNING")

        # Start elapsed time counter
        import time
        start_time = time.time()
        self._channel_list_loading = True

        def update_elapsed():
            if self._channel_list_loading:
                elapsed = int(time.time() - start_time)
                self.lbl_export_target.config(
                    text=f"채널 조회 중... ({elapsed}초)",
                    foreground="orange"
                )
                self.root.after(1000, update_elapsed)

        update_elapsed()

        # Fetch channels in background thread
        filter_text_only = self.filter_text_only.get()
        filter_accessible = self.filter_accessible.get()

        def fetch_channels():
            try:
                exporter = Exporter(self.config)
                # Use --include-vc False to exclude voice channels at DCE level
                output = exporter.list_channels(server_id, include_vc=not filter_text_only)
                channels = parse_channel_list(output)

                if filter_text_only:
                    self.root.after(0, lambda c=len(channels): self._log(
                        f"텍스트 채널: {c}개 (음성 채널 제외됨)", "INFO"
                    ))

                # Step 2: Filter accessible channels if option is enabled (parallel)
                if filter_accessible and channels:
                    total_to_check = len(channels)
                    self.root.after(0, lambda c=total_to_check: self._log(
                        f"접근 권한 확인 중... ({c}개 채널, 10개 병렬 처리)", "WARNING"
                    ))

                    # Use parallel processing for speed
                    from concurrent.futures import ThreadPoolExecutor, as_completed

                    accessible_channels = []
                    inaccessible_count = 0
                    completed = 0

                    with ThreadPoolExecutor(max_workers=10) as executor:
                        future_to_channel = {
                            executor.submit(self._test_channel_access, None, ch.id): ch
                            for ch in channels
                        }

                        for future in as_completed(future_to_channel):
                            channel = future_to_channel[future]
                            completed += 1

                            # Update progress every 5 completions
                            if completed % 5 == 0 or completed == total_to_check:
                                pct = int(completed * 100 / total_to_check)
                                self.root.after(0, lambda p=pct, c=completed, t=total_to_check:
                                    self.lbl_export_target.config(
                                        text=f"권한 확인 {p}% ({c}/{t})",
                                        foreground="orange"
                                    ))

                            try:
                                if future.result():
                                    accessible_channels.append(channel)
                                else:
                                    inaccessible_count += 1
                            except:
                                accessible_channels.append(channel)

                    channels = accessible_channels
                    self.root.after(0, lambda a=len(channels), f=inaccessible_count: self._log(
                        f"접근 가능: {a}개 (권한 없음: {f}개 제외)", "SUCCESS"
                    ))

                # Update UI in main thread
                self.root.after(0, lambda c=channels: self._on_channel_list_complete(c, start_time))

            except Exception as e:
                error_msg = str(e)
                self.root.after(0, lambda msg=error_msg: self._on_channel_list_error(msg))

        threading.Thread(target=fetch_channels, daemon=True).start()

    def _test_channel_access(self, exporter, channel_id: str) -> bool:
        """
        Test if a channel is accessible by attempting a minimal export.

        Args:
            exporter: Exporter instance
            channel_id: Channel ID to test

        Returns:
            True if accessible, False otherwise
        """
        import os
        import subprocess

        try:
            dce_path = self.config.get_dce_path()
            token = self.config.get_token()

            if not dce_path or not token:
                return True  # Can't test, assume accessible

            # Use DCE to try to get channel info (minimal request)
            cmd = [
                dce_path, 'export',
                '-t', token,
                '-c', channel_id,
                '-f', 'Json',
                '-o', os.devnull,  # Discard output
                '--after', '2099-01-01',  # Far future date = no messages
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=2  # Fast timeout
            )

            # Sanitize before any string handling — even though we only
            # branch on keywords, future changes could log this output.
            token = self.config.get_token()
            safe_stdout = sanitize_error_message(result.stdout or "", token)
            safe_stderr = sanitize_error_message(result.stderr or "", token)
            output = (safe_stdout + safe_stderr).lower()
            if 'forbidden' in output or 'unauthorized' in output or 'missing access' in output:
                return False

            return True

        except subprocess.TimeoutExpired:
            return True  # Timeout doesn't mean inaccessible
        except Exception:
            return True  # Assume accessible on error

    def _test_channels_parallel(self, channels: list, max_workers: int = 5) -> list:
        """
        Test multiple channels in parallel for faster checking.

        Args:
            channels: List of ChannelInfo objects
            max_workers: Number of parallel workers

        Returns:
            List of accessible channels
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        accessible = []
        total = len(channels)

        # Skip non-text channel types
        text_types = {'TextChannel', 'Forum', 'Thread', 'PrivateThread', 'PublicThread', 'News', 'Announcement'}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_channel = {}

            for channel in channels:
                # Skip voice/stage/category channels
                if channel.type not in text_types:
                    accessible.append(channel)
                    continue

                future = executor.submit(self._test_channel_access, None, channel.id)
                future_to_channel[future] = channel

            completed = 0
            for future in as_completed(future_to_channel):
                channel = future_to_channel[future]
                completed += 1

                # Update progress every 10 channels
                if completed % 10 == 0:
                    self.root.after(0, lambda c=completed, t=total: self.lbl_export_target.config(
                        text=f"채널 확인 중... ({c}/{t})",
                        foreground="orange"
                    ))

                try:
                    if future.result():
                        accessible.append(channel)
                except Exception:
                    accessible.append(channel)  # On error, assume accessible

        return accessible

    def _on_channel_list_complete(self, channels, start_time):
        """Handle channel list fetch completion."""
        import time
        self._channel_list_loading = False
        elapsed = int(time.time() - start_time)

        self._populate_channel_tree(channels)
        self._log(f"채널 조회 완료 ({elapsed}초 소요)", "SUCCESS")
        self._update_export_target()

    def _on_channel_list_error(self, error):
        """Handle channel list fetch error."""
        self._channel_list_loading = False
        self._log(f"채널 목록 조회 실패: {error}", "ERROR")
        self._update_export_target()

    def _populate_channel_tree(self, channels: list):
        """Populate the channel tree with channel data."""
        # Clear existing items and checked state
        for item in self.channel_tree.get_children():
            self.channel_tree.delete(item)
        self._checked_channels.clear()

        if not channels:
            self._log("채널이 없거나 조회할 수 없습니다.", "WARNING")
            return

        # Group channels by type
        groups = group_channels_by_type(channels)

        # Add to treeview
        for type_name, channel_list in groups.items():
            # Create parent node for type
            parent = self.channel_tree.insert(
                "",
                tk.END,
                text=f"{type_name} ({len(channel_list)})",
                values=("", "", ""),  # check, type, id
                open=True
            )

            # Add channels under this type
            for channel in channel_list:
                self.channel_tree.insert(
                    parent,
                    tk.END,
                    text=channel.name,
                    values=("☐", channel.get_type_display(), channel.id),
                    tags=(channel.type.lower(),)
                )

        self._log(f"채널 {len(channels)}개 조회됨", "SUCCESS")

    def _on_channel_select(self, event):
        """Handle channel selection in treeview."""
        # Update export target to show selection count
        self._update_export_target()

    def _on_channel_double_click(self, event):
        """Toggle checkbox on double-click."""
        item = self.channel_tree.identify_row(event.y)
        if not item:
            return

        values = self.channel_tree.item(item, "values")
        # Skip if it's a parent node (no ID)
        if not values or len(values) < 3 or not values[2]:
            return

        self._toggle_channel_check(item)

    def _toggle_channel_check(self, item):
        """Toggle the check state of a channel item."""
        values = list(self.channel_tree.item(item, "values"))
        if len(values) < 3:
            return

        channel_id = values[2]
        if item in self._checked_channels:
            # Uncheck
            del self._checked_channels[item]
            values[0] = "☐"
        else:
            # Check
            self._checked_channels[item] = channel_id
            values[0] = "☑"

        self.channel_tree.item(item, values=values)
        self._update_export_target()

    def _check_selected_channels(self):
        """Check all currently selected channels."""
        for item in self.channel_tree.selection():
            values = self.channel_tree.item(item, "values")
            if values and len(values) >= 3 and values[2]:
                if item not in self._checked_channels:
                    self._toggle_channel_check(item)
        self._update_export_target()

    def _uncheck_all_channels(self):
        """Uncheck all channels."""
        for item in list(self._checked_channels.keys()):
            values = list(self.channel_tree.item(item, "values"))
            values[0] = "☐"
            self.channel_tree.item(item, values=values)
        self._checked_channels.clear()
        self._update_export_target()

    def _check_all_channels(self):
        """Check all channels in the tree."""
        def check_children(parent):
            for item in self.channel_tree.get_children(parent):
                values = self.channel_tree.item(item, "values")
                if values and len(values) >= 3 and values[2]:
                    if item not in self._checked_channels:
                        self._checked_channels[item] = values[2]
                        new_values = list(values)
                        new_values[0] = "☑"
                        self.channel_tree.item(item, values=new_values)
                # Recurse into children
                check_children(item)

        check_children("")
        self._update_export_target()

    def _set_placeholder(self, entry: ttk.Entry, placeholder: str):
        """Set placeholder text for an entry widget."""
        entry.insert(0, placeholder)
        entry.config(foreground="gray")

        def on_focus_in(event):
            if entry.get() == placeholder:
                entry.delete(0, tk.END)
                entry.config(foreground="black")

        def on_focus_out(event):
            if not entry.get():
                entry.insert(0, placeholder)
                entry.config(foreground="gray")

        entry.bind("<FocusIn>", on_focus_in)
        entry.bind("<FocusOut>", on_focus_out)

        # Add right-click context menu
        self._add_context_menu(entry)

    def _add_context_menu(self, widget):
        """Add right-click context menu to a widget (Entry/Text)."""
        menu = tk.Menu(widget, tearoff=0)
        menu.add_command(label="잘라내기", accelerator="Cmd+X",
                        command=lambda: self._context_cut(widget))
        menu.add_command(label="복사", accelerator="Cmd+C",
                        command=lambda: self._context_copy(widget))
        menu.add_command(label="붙여넣기", accelerator="Cmd+V",
                        command=lambda: self._context_paste(widget))
        menu.add_separator()
        menu.add_command(label="전체 선택", accelerator="Cmd+A",
                        command=lambda: self._context_select_all(widget))

        def show_menu(event):
            widget.focus_set()
            menu.tk_popup(event.x_root, event.y_root)

        # Bind right-click (Button-2 on macOS, Button-3 on Windows/Linux)
        widget.bind("<Button-2>", show_menu)  # macOS
        widget.bind("<Button-3>", show_menu)  # Windows/Linux
        widget.bind("<Control-Button-1>", show_menu)  # macOS Ctrl+Click

    def _context_cut(self, widget):
        """Cut selected text."""
        try:
            widget.event_generate("<<Cut>>")
        except tk.TclError:
            pass

    def _context_copy(self, widget):
        """Copy selected text."""
        try:
            widget.event_generate("<<Copy>>")
        except tk.TclError:
            pass

    def _context_paste(self, widget):
        """Paste from clipboard."""
        try:
            widget.event_generate("<<Paste>>")
        except tk.TclError:
            # Fallback: manual paste
            try:
                text = widget.clipboard_get()
                try:
                    widget.delete("sel.first", "sel.last")
                except tk.TclError:
                    pass
                widget.insert("insert", text)
            except tk.TclError:
                pass

    def _context_select_all(self, widget):
        """Select all text."""
        widget.select_range(0, tk.END)
        widget.icursor(tk.END)

    # =========================================================================
    # Execution Area
    # =========================================================================
    def _create_execution_area(self, parent):
        """Create the execution area."""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=(0, 10))

        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X)

        self.btn_export = ttk.Button(
            btn_frame,
            text="내보내기 실행",
            command=self._on_export,
            width=15
        )
        self.btn_export.pack(side=tk.LEFT, padx=(0, 10))

        self.btn_stop = ttk.Button(
            btn_frame,
            text="중지",
            command=self._on_stop,
            width=10,
            state=tk.DISABLED
        )
        self.btn_stop.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(
            btn_frame,
            text="폴더 열기",
            command=self._on_open_folder,
            width=12
        ).pack(side=tk.LEFT)

        # Status label
        self.lbl_status = ttk.Label(
            frame,
            text="대기 중",
            foreground="gray"
        )
        self.lbl_status.pack(fill=tk.X, pady=(10, 0))

    def _set_running_state(self, running: bool):
        """Set the UI state for running/idle."""
        self.is_running = running

        if running:
            self.btn_export.config(state=tk.DISABLED)
            self.btn_stop.config(state=tk.NORMAL)
            self.lbl_status.config(text="실행 중...", foreground="blue")
        else:
            self.btn_export.config(state=tk.NORMAL)
            self.btn_stop.config(state=tk.DISABLED)

    def _on_stop(self):
        """Handle stop button click."""
        if not self.is_running or not self.exporter:
            return

        self._log("중지 요청...", "WARNING")
        self.lbl_status.config(text="중지 중...", foreground="orange")
        self.btn_stop.config(state=tk.DISABLED)

        # Cancel the export
        self.exporter.cancel()

    # =========================================================================
    # Log Area
    # =========================================================================
    def _create_log_area(self, parent):
        """Create the log area."""
        frame = ttk.LabelFrame(parent, text="로그 (우클릭으로 복사)", padding="5")
        frame.pack(fill=tk.BOTH, expand=True)

        # Text widget with scrollbar
        log_frame = ttk.Frame(frame)
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.txt_log = tk.Text(
            log_frame,
            height=10,
            wrap=tk.WORD,
            font=("Consolas", 10) if os.name == 'nt' else ("Monaco", 10)
        )
        self.txt_log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(log_frame, command=self.txt_log.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt_log.config(yscrollcommand=scrollbar.set)

        # Configure tags for colors
        self.txt_log.tag_config("error", foreground="red")
        self.txt_log.tag_config("success", foreground="green")
        self.txt_log.tag_config("warning", foreground="orange")

        # Make read-only but allow selection/copy
        self.txt_log.bind("<Key>", self._block_log_edit)

        # Add context menu for copy
        self._add_log_context_menu(self.txt_log)

        # Clear button
        ttk.Button(
            frame,
            text="로그 지우기",
            command=self._on_clear_log,
            width=12
        ).pack(anchor=tk.E, pady=(5, 0))

    def _block_log_edit(self, event):
        """Block editing in log but allow copy shortcuts."""
        # Allow Cmd+C (copy), Cmd+A (select all)
        if event.state & 0x8 or event.state & 0x4:  # Cmd or Ctrl
            if event.keysym.lower() == 'c':
                # Manually handle copy
                self._log_copy(self.txt_log)
                return "break"
            if event.keysym.lower() == 'a':
                self._log_select_all(self.txt_log)
                return "break"
        return "break"  # Block all other keys

    def _add_log_context_menu(self, widget):
        """Add right-click context menu to log widget."""
        menu = tk.Menu(widget, tearoff=0)
        menu.add_command(label="복사", accelerator="Cmd+C",
                        command=lambda: self._log_copy(widget))
        menu.add_command(label="전체 선택", accelerator="Cmd+A",
                        command=lambda: self._log_select_all(widget))

        def show_menu(event):
            menu.tk_popup(event.x_root, event.y_root)

        widget.bind("<Button-2>", show_menu)  # macOS
        widget.bind("<Button-3>", show_menu)  # Windows/Linux

    def _log_copy(self, widget):
        """Copy selected text from log."""
        try:
            # Try to get selected text
            try:
                text = widget.selection_get()
            except tk.TclError:
                # No selection - copy all text
                text = widget.get("1.0", tk.END).strip()

            if text:
                self.root.clipboard_clear()
                self.root.clipboard_append(text)
                self.root.update_idletasks()
                self.root.update()
                # Force clipboard to persist on macOS
                self.root.after(10, lambda: None)
        except Exception:
            pass

    def _log_select_all(self, widget):
        """Select all text in log."""
        widget.tag_add("sel", "1.0", tk.END)

    def _log(self, message: str, level: str = "INFO"):
        """
        Add a message to the log.

        Args:
            message: The message to log (must be token-free).
            level: Log level (INFO, ERROR, SUCCESS, WARNING).
        """
        timestamp = datetime.now().strftime("%H:%M:%S")

        self.txt_log.insert(tk.END, f"[{timestamp}] ")

        # Apply color based on level
        tag = level.lower() if level.lower() in ("error", "success", "warning") else None
        self.txt_log.insert(tk.END, message + "\n", tag)

        self.txt_log.see(tk.END)

    def _log_event(self, event: LogEvent):
        """Log a LogEvent from the exporter."""
        level_map = {
            LogLevel.DEBUG: "INFO",
            LogLevel.INFO: "INFO",
            LogLevel.WARNING: "WARNING",
            LogLevel.ERROR: "ERROR",
            LogLevel.SUCCESS: "SUCCESS",
        }
        self._log(event.message, level_map.get(event.level, "INFO"))

    def _on_clear_log(self):
        """Clear the log area."""
        self.txt_log.delete("1.0", tk.END)

    def _poll_log_queue(self):
        """Poll the log queue and update the log display."""
        try:
            while True:
                item = self.log_queue.get_nowait()

                if isinstance(item, LogEvent):
                    self._log_event(item)
                elif isinstance(item, dict):
                    # Handle completion/error/cancelled signals
                    if item.get("type") == "complete":
                        self._on_export_complete(item.get("path"))
                    elif item.get("type") == "batch_complete":
                        self._on_batch_export_complete(
                            item.get("paths", []),
                            item.get("total", 0)
                        )
                    elif item.get("type") == "cancelled":
                        self._on_export_cancelled()
                    elif item.get("type") == "error":
                        self._on_export_error(
                            item.get("error"),
                            item.get("solution")
                        )

        except queue.Empty:
            pass

        # Schedule next poll
        self.root.after(self.QUEUE_POLL_MS, self._poll_log_queue)

    # =========================================================================
    # Button Handlers
    # =========================================================================
    def _on_set_token(self):
        """Handle token setup button."""
        self._prompt_for_token()
        self._update_status_bar()

    def _prompt_for_token(self) -> bool:
        """
        Show token input dialog.

        Returns:
            True if token was set, False if cancelled.
        """
        dialog = TokenDialog(self.root, self.config)
        self.root.wait_window(dialog.top)
        return dialog.was_saved

    def _prompt_for_dce(self) -> bool:
        """
        Show DCE file selection dialog.

        Returns:
            True if DCE was set, False if cancelled.
        """
        filetypes = [("All files", "*.*")]
        if os.name == 'nt':
            filetypes = [("Executable", "*.exe"), ("All files", "*.*")]

        path = filedialog.askopenfilename(
            title="DiscordChatExporter.Cli 실행 파일을 선택하세요",
            filetypes=filetypes
        )

        if path:
            self.config.set_dce_path(path)
            self._log(f"DCE 경로 설정됨: {self._abbreviate_path(path)}")
            return True
        return False

    def _on_browse_dce(self):
        """Handle DCE browse button."""
        filetypes = [("All files", "*.*")]
        if os.name == 'nt':
            filetypes = [("Executable", "*.exe"), ("All files", "*.*")]

        path = filedialog.askopenfilename(
            title="DiscordChatExporter.Cli 선택",
            filetypes=filetypes
        )

        if path:
            self.config.set_dce_path(path)
            self._update_status_bar()
            self._log(f"DCE 경로 설정: {path}")

    def _on_browse_output(self):
        """Handle output directory browse button."""
        path = filedialog.askdirectory(
            parent=self.root,
            title="출력 폴더 선택",
            initialdir=self.ent_output_dir.get() or str(Path.cwd()),
            mustexist=False
        )

        if path:
            self.ent_output_dir.delete(0, tk.END)
            self.ent_output_dir.insert(0, path)

    def _on_open_folder(self):
        """Open the output folder in file explorer."""
        path = self.ent_output_dir.get()
        if not path or not Path(path).exists():
            path = str(Path.cwd())

        if os.name == 'nt':
            os.startfile(path)
        elif os.name == 'posix':
            import subprocess
            subprocess.run(['open', path] if os.uname().sysname == 'Darwin'
                          else ['xdg-open', path])

    def _on_export(self):
        """Handle export button click."""
        if self.is_running:
            return

        # Step 1: Check token - prompt if missing
        if not self.config.get_token():
            self._log("토큰이 설정되지 않았습니다. 설정 창을 엽니다...")
            if not self._prompt_for_token():
                self._log("토큰 설정이 취소되었습니다.", "WARNING")
                return
            self._update_status_bar()

        # Step 2: Check DCE path - prompt if missing
        if not self.config.get_dce_path():
            self._log("DCE 경로가 설정되지 않았습니다. 파일 선택 창을 엽니다...")
            if not self._prompt_for_dce():
                self._log("DCE 경로 설정이 취소되었습니다.", "WARNING")
                return
            self._update_status_bar()

        self._log("검증 시작...")

        # Run validation
        is_valid, errors = self._validate_inputs()

        if not is_valid:
            self._log("검증 실패!", "ERROR")
            for error in errors:
                self._log(f"  - {error}", "ERROR")
            self.lbl_status.config(text="검증 실패", foreground="red")

            # Show error dialog with solution
            self._show_error_dialog(errors)
            return

        self._log("검증 통과!", "SUCCESS")

        # Check if we have checked channels for batch export
        checked_count = len(self._checked_channels) if hasattr(self, '_checked_channels') else 0

        if checked_count > 0:
            # Batch export: export each checked channel separately
            self._start_batch_export()
        else:
            # Single export
            options = self._build_export_options()
            if not options:
                return

            # Start export in background thread
            self._set_running_state(True)
            self._log("내보내기 시작...")

            # Store media settings for post-export cleanup
            self._export_media_settings = (
                self.media_enabled.get(),
                self.exclude_avatars.get(),
                self.exclude_emojis.get()
            )

            self.export_thread = threading.Thread(
                target=self._run_export,
                args=(options,),
                daemon=True
            )
            self.export_thread.start()

    def _start_batch_export(self):
        """Start batch export for multiple checked channels."""
        channel_ids = list(self._checked_channels.values())
        total = len(channel_ids)

        self._set_running_state(True)
        self._log(f"배치 내보내기 시작: {total}개 채널")

        # Store media settings for post-export cleanup
        self._export_media_settings = (
            self.media_enabled.get(),
            self.exclude_avatars.get(),
            self.exclude_emojis.get()
        )

        # Store batch info
        self._batch_channel_ids = channel_ids
        self._batch_current = 0
        self._batch_total = total
        self._batch_completed_paths = []

        self.export_thread = threading.Thread(
            target=self._run_batch_export,
            daemon=True
        )
        self.export_thread.start()

    def _run_batch_export(self):
        """Run batch export in background thread."""
        for i, channel_id in enumerate(self._batch_channel_ids):
            if not self.is_running:
                self.log_queue.put({"type": "cancelled"})
                return

            self._batch_current = i + 1
            self.log_queue.put(LogEvent(
                level=LogLevel.INFO,
                message=f"[{self._batch_current}/{self._batch_total}] 채널 {channel_id} 내보내기 중..."
            ))

            try:
                # Build options for this channel
                options = self._build_export_options_for_channel(channel_id)
                if not options:
                    continue

                # Create exporter and run
                exporter = Exporter(self.config)
                exporter.reset()
                self.exporter = exporter

                # Log callback for this export
                def log_callback(event: LogEvent):
                    self.log_queue.put(event)

                output_path = exporter.export_channel(options, log_callback)

                self.log_queue.put(LogEvent(
                    level=LogLevel.SUCCESS,
                    message=f"[{self._batch_current}/{self._batch_total}] 완료: {Path(output_path).name}"
                ))
                self._batch_completed_paths.append(output_path)

            except Exception as e:
                error_msg = sanitize_error_message(str(e))
                error_type, error_detail = parse_dce_error(error_msg)

                self.log_queue.put(LogEvent(
                    level=LogLevel.ERROR,
                    message=f"[{self._batch_current}/{self._batch_total}] 실패: {error_msg}"
                ))

                # Show detailed error explanation if available
                if error_type != 'unknown':
                    self.log_queue.put(LogEvent(
                        level=LogLevel.ERROR,
                        message=f"    ▶ {error_detail}"
                    ))

        # All done
        self.log_queue.put({
            "type": "batch_complete",
            "paths": self._batch_completed_paths,
            "total": self._batch_total
        })

    def _build_export_options_for_channel(self, channel_id: str) -> Optional[ExportOptions]:
        """Build ExportOptions for a specific channel ID."""
        # Get common options
        format_name = self.selected_format.get()
        format_map = {
            "HTML (Dark)": ExportFormat.HTML_DARK,
            "HTML (Light)": ExportFormat.HTML_LIGHT,
            "Text": ExportFormat.PLAIN_TEXT,
            "JSON": ExportFormat.JSON,
            "CSV": ExportFormat.CSV,
            "Markdown": ExportFormat.MARKDOWN,
        }
        export_format = format_map.get(format_name, ExportFormat.HTML_DARK)

        output_dir = self.ent_output_dir.get().strip() or None
        after = self._get_entry_value(self.ent_after)
        before = self._get_entry_value(self.ent_before)

        return ExportOptions(
            channel_id=channel_id,
            guild_id=None,
            export_format=export_format,
            output_dir=output_dir,
            after=after,
            before=before,
            media=self.media_enabled.get(),
            include_threads=None,
            safe_mode=self.safe_mode.get(),
            delay_seconds=self._get_current_delay(),
        )

    def _run_export(self, options: ExportOptions):
        """
        Run export in background thread.

        All output is sent to log_queue, never directly to UI.
        Token is never included in any output.
        """
        def log_callback(event: LogEvent):
            """Send log events to queue (thread-safe)."""
            self.log_queue.put(event)

        try:
            exporter = Exporter(self.config)
            exporter.reset()  # Clear any previous cancel state
            self.exporter = exporter  # Store for cancellation

            # Choose export method based on options
            if options.guild_id:
                output_path = exporter.export_guild(options, log_callback)
            else:
                output_path = exporter.export_channel(options, log_callback)

            # Check if cancelled
            if exporter.is_cancelled():
                self.log_queue.put({
                    "type": "cancelled"
                })
                return

            # Signal completion
            self.log_queue.put({
                "type": "complete",
                "path": str(output_path)
            })

        except TokenNotConfiguredError:
            self.log_queue.put({
                "type": "error",
                "error": "Discord 토큰이 설정되지 않았습니다.",
                "solution": self.ERROR_SOLUTIONS["token"]
            })

        except DCENotFoundError as e:
            # Sanitize error message (should not contain token, but be safe)
            safe_msg = sanitize_error_message(str(e), self.config.get_token())
            self.log_queue.put({
                "type": "error",
                "error": safe_msg,
                "solution": self.ERROR_SOLUTIONS["dce_not_found"]
            })

        except ExportError as e:
            # Error message is already sanitized in exporter
            safe_msg = sanitize_error_message(str(e), self.config.get_token())
            error_type, error_detail = parse_dce_error(safe_msg)
            solution = get_error_solution(error_type) if error_type != 'unknown' else self.ERROR_SOLUTIONS["network"]

            self.log_queue.put({
                "type": "error",
                "error": f"{safe_msg}\n\n{error_detail}" if error_type != 'unknown' else safe_msg,
                "solution": solution
            })

        except Exception as e:
            # Catch-all: always sanitize
            safe_msg = sanitize_error_message(str(e), self.config.get_token())
            error_type, error_detail = parse_dce_error(safe_msg)

            if error_type != 'unknown':
                self.log_queue.put({
                    "type": "error",
                    "error": f"{safe_msg}\n\n{error_detail}",
                    "solution": get_error_solution(error_type)
                })
            else:
                self.log_queue.put({
                    "type": "error",
                    "error": f"예상치 못한 오류: {safe_msg}",
                    "solution": "로그를 확인하고 설정을 다시 확인해주세요."
                })

    def _on_export_cancelled(self):
        """Handle export cancellation."""
        self._set_running_state(False)
        self.exporter = None
        self._log("내보내기가 중지되었습니다.", "WARNING")
        self.lbl_status.config(text="중지됨", foreground="orange")

    def _on_export_complete(self, path: str):
        """Handle export completion."""
        self._set_running_state(False)
        self.exporter = None
        self._log(f"내보내기 완료: {path}", "SUCCESS")

        # Clean up avatar/emoji files if media was enabled with exclusions
        if hasattr(self, '_export_media_settings'):
            media_enabled, exclude_avatars, exclude_emojis = self._export_media_settings
            if media_enabled and (exclude_avatars or exclude_emojis):
                self._cleanup_media_files(path, exclude_avatars, exclude_emojis)
            delattr(self, '_export_media_settings')

        # Show path in status (abbreviated if too long)
        display_path = self._abbreviate_path(path, max_len=50)
        self.lbl_status.config(text=f"완료: {display_path}", foreground="green")

        # Store path for folder opening
        self._last_export_path = path

        # Show completion dialog with "Open Folder" option
        self._show_completion_dialog(path)

    def _on_batch_export_complete(self, paths: list[str], total: int):
        """Handle batch export completion."""
        self._set_running_state(False)
        self.exporter = None

        completed = len(paths)
        failed = total - completed

        self._log(f"배치 내보내기 완료: {completed}/{total}개 성공", "SUCCESS")
        if failed > 0:
            self._log(f"  ({failed}개 실패)", "WARNING")

        # Clean up avatar/emoji files for each exported file
        if hasattr(self, '_export_media_settings'):
            media_enabled, exclude_avatars, exclude_emojis = self._export_media_settings
            if media_enabled and (exclude_avatars or exclude_emojis):
                for path in paths:
                    self._cleanup_media_files(path, exclude_avatars, exclude_emojis)
            delattr(self, '_export_media_settings')

        # Clear checked channels after successful export
        self._uncheck_all_channels()

        # Show status
        self.lbl_status.config(
            text=f"배치 완료: {completed}/{total}개",
            foreground="green" if failed == 0 else "orange"
        )

        # Store first path for folder opening
        if paths:
            self._last_export_path = paths[0]

            # Show completion dialog
            output_dir = str(Path(paths[0]).parent)
            self._show_batch_completion_dialog(output_dir, completed, total)

    def _show_batch_completion_dialog(self, output_dir: str, completed: int, total: int):
        """Show batch completion dialog."""
        dialog = tk.Toplevel(self.root)
        dialog.title("배치 내보내기 완료")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.geometry("400x130")
        dialog.resizable(False, False)

        # Center on parent
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 400) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 130) // 2
        dialog.geometry(f"+{x}+{y}")

        # Content
        ttk.Label(
            dialog,
            text=f"✅ {completed}/{total}개 채널 내보내기 완료!",
            font=("TkDefaultFont", 12, "bold")
        ).pack(pady=(15, 5))

        ttk.Label(dialog, text=f"저장 위치: {output_dir}").pack(pady=5)

        # Buttons
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=15)

        ttk.Button(
            btn_frame,
            text="폴더 열기",
            command=lambda: [self._open_folder(output_dir), dialog.destroy()]
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            btn_frame,
            text="닫기",
            command=dialog.destroy
        ).pack(side=tk.LEFT, padx=5)

    def _open_folder(self, path: str):
        """Open a folder in file explorer."""
        if os.name == 'nt':
            os.startfile(path)
        elif os.name == 'posix':
            import subprocess
            subprocess.run(['open', path] if os.uname().sysname == 'Darwin'
                          else ['xdg-open', path])

    def _cleanup_media_files(self, path: str, exclude_avatars: bool, exclude_emojis: bool):
        """Clean up avatar and emoji files after export."""
        try:
            export_path = Path(path)

            # Find all exported files (could be multiple for guild export)
            if export_path.is_dir():
                # Guild export - find all HTML/JSON files
                files = list(export_path.glob("*.html")) + list(export_path.glob("*.json"))
            else:
                files = [export_path]

            total_avatars = 0
            total_emojis = 0

            for file in files:
                avatars, emojis = cleanup_avatar_emoji_files(
                    file,
                    log_callback=lambda e: self._log(e.message, e.level.name),
                    delete_avatars=exclude_avatars,
                    delete_emojis=exclude_emojis
                )
                total_avatars += avatars
                total_emojis += emojis

            if total_avatars > 0 or total_emojis > 0:
                self._log(f"미디어 정리: 아바타 {total_avatars}개, 이모지 {total_emojis}개 삭제", "SUCCESS")
        except Exception as e:
            self._log(f"미디어 정리 실패: {e}", "WARNING")

    def _show_completion_dialog(self, path: str):
        """Show completion dialog with Open Folder button."""
        dialog = tk.Toplevel(self.root)
        dialog.title("내보내기 완료")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.geometry("450x150")
        dialog.resizable(False, False)

        # Center on parent
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 450) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 150) // 2
        dialog.geometry(f"+{x}+{y}")

        frame = ttk.Frame(dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        # Success icon and message
        ttk.Label(
            frame,
            text="내보내기가 완료되었습니다!",
            font=("TkDefaultFont", 12, "bold")
        ).pack(anchor=tk.W)

        # File path (abbreviated)
        display_path = self._abbreviate_path(path, max_len=55)
        ttk.Label(
            frame,
            text=f"파일: {display_path}",
            foreground="gray"
        ).pack(anchor=tk.W, pady=(5, 0))

        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=(20, 0))

        def open_folder_and_close():
            self._open_folder_for_path(path)
            dialog.destroy()

        ttk.Button(
            btn_frame,
            text="폴더 열기",
            command=open_folder_and_close,
            width=12
        ).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(
            btn_frame,
            text="확인",
            command=dialog.destroy,
            width=12
        ).pack(side=tk.LEFT)

        # Bind Enter to close
        dialog.bind("<Return>", lambda e: dialog.destroy())
        dialog.focus_set()

    def _open_folder_for_path(self, file_path: str):
        """
        Open the folder containing the file in system file explorer.

        Handles Windows/macOS/Linux differences.
        """
        import subprocess
        from pathlib import Path

        folder = str(Path(file_path).parent)

        try:
            if os.name == 'nt':
                # Windows: use explorer with /select to highlight file
                subprocess.run(['explorer', '/select,', file_path], check=False)
            elif os.uname().sysname == 'Darwin':
                # macOS: use 'open' command, -R reveals file in Finder
                subprocess.run(['open', '-R', file_path], check=False)
            else:
                # Linux: use xdg-open on folder
                subprocess.run(['xdg-open', folder], check=False)
        except Exception as e:
            self._log(f"폴더 열기 실패: {e}", "WARNING")

    def _on_export_error(self, error: str, solution: str):
        """Handle export error."""
        self._set_running_state(False)
        self.exporter = None
        self._log(f"오류: {error}", "ERROR")
        self.lbl_status.config(text="실패", foreground="red")

        messagebox.showerror(
            "내보내기 실패",
            f"{error}\n\n해결 방법:\n{solution}"
        )

    def _show_error_dialog(self, errors: list):
        """Show validation error dialog with solutions."""
        solutions = []

        for error in errors:
            if "토큰" in error:
                solutions.append(self.ERROR_SOLUTIONS["token"])
            elif "DCE" in error:
                solutions.append(self.ERROR_SOLUTIONS["dce_path"])
            elif "채널" in error or "URL" in error:
                solutions.append(self.ERROR_SOLUTIONS["channel"])
            elif "폴더" in error or "권한" in error:
                solutions.append(self.ERROR_SOLUTIONS["permission"])

        # Remove duplicates
        solutions = list(dict.fromkeys(solutions))

        message = "입력값 검증에 실패했습니다.\n\n"
        message += "오류:\n"
        for error in errors:
            message += f"• {error}\n"

        if solutions:
            message += "\n해결 방법:\n"
            for solution in solutions:
                message += f"• {solution}\n"

        messagebox.showwarning("검증 실패", message)

    # =========================================================================
    # Validation & Options Building
    # =========================================================================
    def _get_entry_value(self, entry: ttk.Entry) -> Optional[str]:
        """Get entry value, returning None for placeholder or empty."""
        value = entry.get().strip()
        # Check if it's a placeholder
        placeholders = [
            "https://discord.com/channels/서버/채널 또는 스레드 URL",
            "YYYY-MM-DD"
        ]
        if not value or value in placeholders:
            return None
        return value

    def _get_export_format(self) -> ExportFormat:
        """Get selected export format."""
        selected = self.selected_format.get()
        for name, fmt in self.FORMAT_OPTIONS:
            if name == selected:
                return fmt
        return ExportFormat.HTML_DARK

    def _validate_inputs(self) -> tuple[bool, list[str]]:
        """
        Validate all inputs.

        Returns:
            Tuple of (is_valid, list of error messages).
            Error messages never contain token.
        """
        errors = []

        # 1. Check token configuration (don't show token value!)
        if not self.config.get_token():
            errors.append("Discord 토큰이 설정되지 않았습니다")

        # 2. Check DCE path with detailed validation
        dce_path = self.config.get_dce_path()
        is_valid, dce_error = validate_dce_executable(dce_path)
        if not is_valid:
            errors.append(dce_error)

        # 3. Validate ID fields - at least one must be provided (or checked channels)
        server_id = self.ent_server_id.get().strip()
        channel_id = self.ent_channel_id.get().strip()
        thread_id = self.ent_thread_id.get().strip()
        checked_count = len(self._checked_channels) if hasattr(self, '_checked_channels') else 0

        if not server_id and not channel_id and not thread_id and checked_count == 0:
            errors.append(
                "내보내기 대상이 없습니다.\n"
                "Discord URL을 입력하거나 채널을 체크해주세요."
            )
        elif checked_count > 0:
            # Checked channels are valid - no further ID validation needed
            pass
        else:
            # Validate IDs if provided
            if thread_id:
                try:
                    validate_channel_id(thread_id)
                except ValueError as e:
                    errors.append(f"스레드 ID 오류: {e}")
            elif channel_id:
                try:
                    validate_channel_id(channel_id)
                except ValueError as e:
                    errors.append(f"채널 ID 오류: {e}")
            elif server_id:
                try:
                    validate_channel_id(server_id)  # Same validation logic
                except ValueError as e:
                    errors.append(f"서버 ID 오류: {e}")

        # 4. Validate output directory with permission check
        output_dir = self.ent_output_dir.get().strip()
        is_valid, dir_error = validate_output_directory(output_dir)
        if not is_valid:
            errors.append(dir_error)

        # 5. Validate dates with range check
        after = self._get_entry_value(self.ent_after)
        before = self._get_entry_value(self.ent_before)

        try:
            validate_date_range(after, before)
        except ValueError as e:
            errors.append(str(e))

        return (len(errors) == 0, errors)

    def _build_export_options(self) -> Optional[ExportOptions]:
        """Build ExportOptions from current inputs."""
        server_id = self.ent_server_id.get().strip() or None
        channel_id = self.ent_channel_id.get().strip() or None
        thread_id = self.ent_thread_id.get().strip() or None

        # Determine export target
        # Priority: thread > channel > guild
        export_channel_id = None
        export_guild_id = None
        include_threads = None

        if thread_id:
            # Thread export: use thread ID as channel ID
            export_channel_id = thread_id
        elif channel_id:
            # Channel export
            export_channel_id = channel_id
        elif server_id:
            # Guild export
            export_guild_id = server_id
            include_threads = self.include_threads.get()

        output_dir = self.ent_output_dir.get().strip() or None

        after = self._get_entry_value(self.ent_after)
        before = self._get_entry_value(self.ent_before)

        # Parse dates if provided
        if after:
            after = parse_date(after)
        if before:
            before = parse_date(before)

        return ExportOptions(
            channel_id=export_channel_id,
            guild_id=export_guild_id,
            export_format=self._get_export_format(),
            output_dir=Path(output_dir) if output_dir else None,
            after=after,
            before=before,
            media=self.media_enabled.get(),
            include_threads=include_threads,
            safe_mode=self.safe_mode.get(),
            delay_seconds=self._get_current_delay(),
        )

    # =========================================================================
    # Settings Persistence
    # =========================================================================
    def _load_settings(self):
        """Load saved settings from config."""
        settings = self.config.get_gui_settings()

        # Output directory
        output_dir = settings.get('output_dir')
        if output_dir:
            self.ent_output_dir.delete(0, tk.END)
            self.ent_output_dir.insert(0, output_dir)

        # Export format
        export_format = settings.get('export_format')
        if export_format and export_format in [f[0] for f in self.FORMAT_OPTIONS]:
            self.selected_format.set(export_format)
            self.cmb_format.set(export_format)

        # Media options
        if 'media_enabled' in settings:
            self.media_enabled.set(settings['media_enabled'])
        if 'exclude_avatars' in settings:
            self.exclude_avatars.set(settings['exclude_avatars'])
        if 'exclude_emojis' in settings:
            self.exclude_emojis.set(settings['exclude_emojis'])

        # Thread option
        include_threads = settings.get('include_threads')
        if include_threads and include_threads in ['none', 'active', 'all']:
            self.include_threads.set(include_threads)
            self.cmb_threads.set(include_threads)

        # Safe mode
        if 'safe_mode' in settings:
            self.safe_mode.set(settings['safe_mode'])

        # Delay bounds
        if 'delay_min' in settings:
            self.delay_min.set(str(settings['delay_min']))
        if 'delay_max' in settings:
            self.delay_max.set(str(settings['delay_max']))

        # Filter text channels only
        if 'filter_text_only' in settings:
            self.filter_text_only.set(settings['filter_text_only'])

        # Filter accessible channels
        if 'filter_accessible' in settings:
            self.filter_accessible.set(settings['filter_accessible'])

        # Update media toggle state
        self._on_media_toggle()

    def _save_settings(self):
        """Save current settings to config."""
        settings = {
            'output_dir': self.ent_output_dir.get().strip(),
            'export_format': self.selected_format.get(),
            'media_enabled': self.media_enabled.get(),
            'exclude_avatars': self.exclude_avatars.get(),
            'exclude_emojis': self.exclude_emojis.get(),
            'include_threads': self.include_threads.get(),
            'safe_mode': self.safe_mode.get(),
            'delay_min': self.delay_min.get(),
            'delay_max': self.delay_max.get(),
            'filter_text_only': self.filter_text_only.get(),
            'filter_accessible': self.filter_accessible.get(),
        }
        self.config.set_gui_settings(settings)

    def _on_close(self):
        """Handle window close event."""
        # Save settings before closing
        self._save_settings()
        self.root.destroy()

    # =========================================================================
    # Main
    # =========================================================================
    def run(self):
        """Start the GUI main loop."""
        self.root.mainloop()


class TokenDialog:
    """Dialog for setting Discord token."""

    def __init__(self, parent, config: ConfigManager):
        self.config = config
        self.was_saved = False  # Track if token was saved

        self.top = tk.Toplevel(parent)
        self.top.title("토큰 설정")
        self.top.transient(parent)
        self.top.grab_set()

        # Center on parent
        self.top.geometry("450x180")

        self._create_widgets()

    def _create_widgets(self):
        frame = ttk.Frame(self.top, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        # Current status (masked!)
        current_token = self.config.get_token()
        if current_token:
            status_text = f"현재 토큰: {self.config.mask_token(current_token)}"
        else:
            status_text = "현재 토큰: 미설정"

        ttk.Label(frame, text=status_text).pack(anchor=tk.W)

        # Help text for first-time users
        help_text = "Discord 개발자 도구(F12) → Network → authorization 헤더에서 토큰을 복사하세요."
        help_label = ttk.Label(frame, text=help_text, foreground="gray")
        help_label.pack(anchor=tk.W, pady=(5, 0))

        # New token entry (masked!)
        ttk.Label(frame, text="새 토큰:").pack(anchor=tk.W, pady=(10, 0))
        self.ent_token = ttk.Entry(frame, show="*", width=50)
        self.ent_token.pack(fill=tk.X, pady=(5, 0))
        self.ent_token.focus_set()

        # Enable Cmd+V paste on macOS
        self.ent_token.bind("<Command-v>", self._on_paste)
        self.ent_token.bind("<Control-v>", self._on_paste)

        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=(15, 0))

        ttk.Button(
            btn_frame,
            text="저장",
            command=self._on_save
        ).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(
            btn_frame,
            text="취소",
            command=self.top.destroy
        ).pack(side=tk.LEFT)

        # Bind Enter key to save
        self.ent_token.bind("<Return>", lambda e: self._on_save())

    def _on_paste(self, event):
        """Handle paste event for token entry."""
        try:
            clipboard = self.top.clipboard_get()
            # Clear selection if any, then insert
            try:
                self.ent_token.delete("sel.first", "sel.last")
            except tk.TclError:
                pass  # No selection
            self.ent_token.insert("insert", clipboard)
        except tk.TclError:
            pass  # Clipboard empty or unavailable
        return "break"  # Prevent default handling

    def _on_save(self):
        token = self.ent_token.get().strip()
        if token:
            self.config.set_token(token)
            self.was_saved = True
            messagebox.showinfo("완료", "토큰이 저장되었습니다.")
            self.top.destroy()
        else:
            messagebox.showwarning("경고", "토큰을 입력해주세요.")


def main():
    """Main entry point for GUI."""
    app = DiscordExporterGUI()
    app.run()


if __name__ == "__main__":
    main()
