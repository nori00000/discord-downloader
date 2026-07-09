# Discord Exporter 프로젝트 규칙

이 문서는 프로젝트 개발 시 반드시 준수해야 하는 상시 규칙입니다.

---

## 1. 보안 규칙 (토큰 처리)

### 절대 금지 사항
- **토큰을 절대 평문으로 출력하지 않는다**
  - UI 화면 (Entry, Label, Text 등)
  - 로그/콘솔 출력 (print, logging)
  - 에러 메시지 (Exception, traceback)
  - README/문서
  - 소스코드 상수/주석

### 토큰 표시 규칙
- 사용자에게 토큰 표시 시: `xxxx...xxxx` (앞 4자리...뒤 4자리)
- 실행 커맨드 로그 시: `******` 또는 `<TOKEN>`
- 에러 메시지: `sanitize_error_message()` 함수로 필터링

### 토큰 노출 위험 지점 체크리스트
- [ ] `cli.py`: 사용자 입력 토큰이 로그/화면에 직접 출력되지 않는가 (`getpass` 사용, `print`/`logging` 직접 호출 금지)
- [ ] `exporter.py`: `_run_command()` 에서 display_cmd 생성 시 마스킹
- [ ] `exporter.py`: subprocess 결과 출력 시 `sanitize_error_message()` 적용
- [ ] `config.py`: `mask_token()` 함수 사용
- [ ] GUI: 토큰 입력 필드는 `show="*"` 속성 사용
- [ ] GUI: 상태 표시에 토큰 포함 금지
- [ ] GUI: 실행 로그에 마스킹된 커맨드만 표시

---

## 2. 의존성 규칙

### 허용된 의존성
- **Python 표준 라이브러리만 사용**
  - `tkinter` - GUI (표준 라이브러리)
  - `argparse` - CLI 파싱
  - `subprocess` - 외부 프로세스 실행
  - `json` - 설정 파일
  - `pathlib`, `os` - 경로 처리
  - `datetime` - 시간 처리
  - `re` - 정규식
  - `getpass` - 보안 입력
  - `threading` - 비동기 작업 (GUI용)
  - `queue` - GUI 로그 큐 (스레드 간 통신)
  - `concurrent.futures` - 채널 접근성 병렬 테스트 (GUI용)
  - `hashlib` - 미디어 파일명 해시 계산 (avatar/emoji 정리)
  - `platform` - OS 감지 (DCE 경로 자동탐지, 권한 처리)
  - `urllib.parse` - URL 파싱 (미디어 파일명 계산)
  - `time` - 채널 목록 조회 경과 시간 표시 (GUI용)

### 금지된 의존성
- `python-dotenv` → 직접 파싱 구현 완료
- `requests`, `httpx` → 불필요 (DCE가 처리)
- `PyQt`, `wxPython` → Tkinter만 사용
- 기타 외부 패키지 → 추가 전 반드시 논의

---

## 3. 아키텍처 규칙

### 코어 로직 재사용
```
discord_exporter/
├── config.py      # 설정 관리 (공용)
├── utils.py       # 유틸리티 (공용)
├── exporter.py    # DCE 호출 로직 (공용)
├── cli.py         # CLI 프론트엔드
└── gui.py         # GUI 프론트엔드
```

- `exporter.py`는 CLI/GUI 모두에서 재사용
- GUI는 프론트엔드로만 구현 (비즈니스 로직 중복 금지)
- 새 프론트엔드 추가 시 `exporter.py` 수정 최소화

### DCE 경로 처리 우선순위
1. 환경 변수 `DCE_PATH`
2. 설정 파일 `~/.discord-exporter/config.json`
3. 자동 탐지 (일반적인 설치 경로)

**하드코딩 절대 금지**

---

## 4. 개발 프로세스 규칙

### 변경 순서
1. **작은 변경** - 한 번에 하나의 기능/수정만
2. **검증** - 변경 후 즉시 테스트
3. **다음 단계** - 검증 완료 후에만 진행

### 커밋 전 체크리스트
- [ ] 토큰이 코드/로그에 노출되지 않는가?
- [ ] 외부 의존성을 추가하지 않았는가?
- [ ] 기존 CLI 기능이 정상 동작하는가?
- [ ] 에러 메시지에 민감 정보가 없는가?

---

## 5. GUI 구현 규칙 (Tkinter)

### 필수 사항
- `tkinter` 표준 라이브러리만 사용
- 토큰 입력 필드: `Entry(show="*")`
- 실행 중 UI 블로킹 방지: `threading` 사용
- 크로스 플랫폼 호환성 유지 (macOS/Windows)

### UI 표시 규칙
- 실행 커맨드 로그: 토큰은 `******`로 치환
- 상태 메시지: 토큰 미포함
- 에러 표시: `sanitize_error_message()` 적용

---

## 6. 파일별 책임

| 파일 | 책임 | 토큰 접근 |
|------|------|----------|
| `config.py` | 설정 저장/로드, 토큰 마스킹 | 저장/로드만 |
| `utils.py` | URL 파싱, 포맷 변환, 에러 필터링 | 필터링만 |
| `exporter.py` | DCE 호출, 커맨드 빌드 | 커맨드 빌드 시 |
| `cli.py` | CLI 인터페이스 | 사용자 입력 시 |
| `gui.py` | GUI 인터페이스 | 사용자 입력 시 |

---

## 변경 이력

| 날짜 | 변경 내용 |
|------|----------|
| 2025-01-13 | 초기 규칙 문서 작성 |
| 2026-06-08 | Doc-Sync 검증 완료 — 코드베이스(v1.1.0) 대비 정합성 확인. 주요 사항: `safe_mode` 필드(ExportOptions, GUI 전용), Markdown export(`md`/`obsidian` 포맷), 스트리밍 실행(`_run_command_streaming`) 모두 §1-§6 규칙 준수 확인됨 |
| 2026-06-09 | Doc-Sync 재검증 — MISMATCH 4건 수정: ①GUI_TEST_CHECKLIST 시나리오 10 예상 메시지(실제 코드 기준으로 교정), ②시나리오 4 예상 메시지(영문 ValueError 래핑 명시), ③README GUI 주요 기능에 채널 목록 조회·배치 내보내기·미디어 정리 항목 추가, ④exportdm `--include-threads` 무시 동작 명시 |
| 2026-06-10 | Doc-Sync 3차 검증 — MISMATCH 3건 수정: ①GUI_SPEC §3 상태 전이 다이어그램 "3초 후 자동" → "즉시 자동"으로 교정(코드에 after(3000) 없음) + 설명 주석 추가, ②GUI_SPEC §2 위젯 목록 누락 4개 추가(exclude_avatars, exclude_emojis, filter_text_only, filter_accessible), ③CORE_API_PLAN §3.3 default_log_callback 예시 코드 실제 구현(레벨별 prefix) 반영 |
| 2026-06-11 | Doc-Sync 4차 검증 — MISMATCH 2건 수정: ①GUI_SPEC §5 E4 오류 메시지 "채널 URL 또는 ID를 입력해주세요" → "내보내기 대상이 없습니다.\nDiscord URL을 입력하거나 채널을 체크해주세요."로 교정(gui.py `_validate_inputs` 실제 메시지), ②GUI_SPEC §5 E2 오류 메시지 "DCE 실행 파일 경로가 설정되지 않았습니다" → "DCE 경로가 설정되지 않았습니다."로 교정(utils.py `validate_dce_executable` 반환값) |
| 2026-06-12 | Doc-Sync 5차 검증 — MISMATCH 3건 수정: ①README GUI 오류표 "시작일이 종료일보다 늦습니다" → "늦거나 같습니다"로 교정(utils.py `validate_date_range` 실제 메시지), ②GUI_SPEC §4 시나리오 1 스텝 3-6 교정(비존재 `btn_settings`/설정 다이얼로그/[저장] → 상태바 "토큰 설정"+"찾아보기" 버튼 흐름으로), ③GUI_SPEC §4 시나리오 3 스텝 1 교정(비존재 `[URL/ID 전환]` 버튼 → `ent_channel_id` 직접 입력으로) |
| 2026-06-13 | Doc-Sync 6차 검증 — MISMATCH 4건 수정: ①GUI_SPEC §5 E5 메시지 교정(다이얼로그 없음 → `lbl_export_target` "URL 오류" 인라인 + E4 fallback), ②E6 메시지 교정("채널 ID 오류: Channel ID should be 17-20 digits, got N digits"로), ③E7 메시지 교정("날짜 형식이 올바르지 않습니다: '{date_str}'"로), ④E8 메시지 교정("폴더에 쓰기 권한이 없습니다: {path}"로). UNDOCUMENTED 2건 추가: ⑤GUI_SPEC §2 위젯 목록에 `lbl_export_target`·`cmb_threads` 추가. STALE 1건 수정: ⑥CORE_API_PLAN §3.1 ExportOptions 예시에 `safe_mode` 필드 추가 |
| 2026-06-17 | Doc-Sync 7차 검증 — MISMATCH 2건 수정: ①GUI_SPEC §2 `lbl_export_target` 기본값 교정(`"URL 또는 ID를 입력하세요"` → `"URL을 입력하세요"` — 위젯 생성 시 초기값 기준, `_update_export_target()` 첫 호출 후 변경됨을 명시), ②GUI_TEST_CHECKLIST 시나리오 3 예상 결과 교정(다이얼로그+로그 → `lbl_export_target` `"URL 오류"` 인라인 + 내보내기 실행 시 E4 다이얼로그로) |
| 2026-06-19 | Doc-Sync 8차 검증 — MISMATCH 2건 수정: ①README GUI 오류표 URL 에러 메시지 교정(`"URL 형식을 인식할 수 없습니다"` → `"URL 오류"` 인라인 — utils.py Python 예외 메시지가 GUI에 직접 노출되지 않음을 반영), ②GUI_TEST_CHECKLIST 시나리오 3 예상 결과에 `https://google.com/channels/...` 케이스 조기 반환 동작 주의사항 추가(`_on_parse_url`의 `"discord.com/channels" not in url` 조건으로 인해 "URL 오류" 미표시) |
| 2026-06-20 | Doc-Sync 9차 검증 — STALE_DOC 1건 수정: §2 허용된 의존성 목록에 실제 사용 중인 표준 라이브러리 6개 추가(`queue`, `concurrent.futures`, `hashlib`, `platform`, `urllib.parse`, `time`) — 규칙 위반 아님, 목록 불완전 보완 |
| 2026-06-22 | Doc-Sync 10차 검증 — MISMATCH 1건 수정: README §주요 기능 "macOS (Apple Silicon) 및 Windows 지원" → "macOS (Apple Silicon) / Windows / Linux 지원"으로 교정 (config.py `_auto_detect_dce()` Linux 분기, CI ubuntu-latest 매트릭스, pyproject.toml `OS Independent` 분류자 근거) |
| 2026-06-24 | Doc-Sync 11차 검증 — MISMATCH 2건 수정: ①README §다운로드 표 Linux 행 추가(`DiscordChatExporter.Cli.linux-x64.zip` — config.py Linux 자동탐지 경로·CI ubuntu-latest 근거), ②README §환경 변수 `macOS/Linux` 통합 예시 → macOS / Linux 개별 예시로 분리(Linux DCE 경로 `linux-x64` 반영) |
| 2026-06-28 | Doc-Sync 12차 검증 — MISMATCH 0건, 전체 84개 클레임 MATCH. 코드 버그 관찰: `gui.py` `_build_export_options_for_channel()` format_map 키 불일치(`"Text"` vs `"Plain Text"`, `"Markdown"` vs `"Markdown (Obsidian)"`) → 배치 내보내기에서 해당 포맷 선택 시 HTML_DARK로 silent fallback 발생. 문서 수정 불필요, 코드 수정 권고. |
| 2026-06-30 | Doc-Sync 13차 검증 — MISMATCH 0건, 전체 130개 클레임 MATCH. 코드 버그 수정: `gui.py` `_build_export_options_for_channel()` 내 별도 format_map 제거 → `self._get_export_format()` 재사용으로 교체. FORMAT_OPTIONS 표시명과 자동 동기화되어 배치 내보내기에서 "Plain Text"/"Markdown (Obsidian)" silent fallback 버그 해결. |
| 2026-07-01 | Doc-Sync 14차 검증 — MISMATCH 0건, 전체 142개 클레임 MATCH. 전 회차 대비 신규 코드 커밋 없음 확인. 이번 회차 추가 검증: GUI 위젯 이름 전체 교차 확인(lbl_token_status~txt_log 25개), `filter_accessible` ThreadPoolExecutor(max_workers=10) 동작, `safe_mode` 기본값 True, `exclude_avatars/emojis` 기본값 True, `ent_token show="*"`. |
| 2026-07-02 | Doc-Sync 15차 검증 — MISMATCH 0건, 전체 157개 클레임 MATCH (+15 신규). 신규 검증: `_run_command()` `<TOKEN>` 마스킹(CLAUDE.md §1 `<TOKEN>`/`******` 모두 허용 확인), `mask_token()` 앞4자리...뒤4자리 포맷, config.json+.env 이중 저장, `group_channels_by_type` backward-compat alias, Linux DCE 자동탐지 경로(`linux-x64`), `convert_json_to_markdown()` Obsidian 구조, `cleanup_avatar_emoji_files()` ↔ GUI exclude_avatars/emojis 연결, ExportOptions.safe_mode 이중 기본값(dataclass=False/GUI=True 의도적 차이). 관찰: git 워킹트리 7개 uncommitted 파일(마지막 커밋 2026-06-05) — 코드-문서 정합성에는 영향 없음. |
| 2026-07-03 | Doc-Sync 16차 검증 — MISMATCH 0건, 전체 172개 클레임 MATCH (+15 신규). 신규 검증: §2 허용 라이브러리 15개 실제 import 교차 확인(`queue`/`concurrent.futures`/`hashlib`/`platform`/`urllib.parse`/`time` 모두 실재), `_build_export_options_for_channel()` `_get_export_format()` 재사용 확인(2026-06-30 버그수정 반영), E1~E8 에러 메시지 8개 전수 재확인, `_test_channels_parallel()` dead code 관찰(gui.py:758 정의, 미호출 — 코드 정리 권고, 문서 수정 불필요), 전체 위젯 25개 재확인, CI 매트릭스(ubuntu+macos py3.9~3.13 + windows smoke) 재확인. |
| 2026-07-04 | Doc-Sync 17차 검증 — UNDOCUMENTED 1건 수정: `.env.example`의 `DCE_PATH` 안내 주석에 Linux 경로 예시(`linux-x64`)가 누락되어 있어 macOS/Windows 예시와 나란히 추가(README §환경 변수·config.py `_auto_detect_dce()` Linux 분기와 정합). 나머지 전체 클레임(코드 import 15개 전량, GUI_SPEC/GUI_TEST_CHECKLIST/CORE_API_PLAN 위젯·에러메시지·상태전이, README 기능표/다운로드표/CLI 옵션, pyproject.toml/CI 매트릭스, git 워킹트리 uncommitted 상태) MATCH — 전 회차(16차) 대비 신규 코드 커밋 없음. |
| 2026-07-07 | Doc-Sync 18차 검증 — MISMATCH 0건. 전 회차(17차, 2026-07-04) 대비 소스 커밋 없음(마지막 커밋 여전히 `24ded85`, 2026-06-05; 8개 파일 uncommitted 상태 그대로 유지: `.env.example`/`CLAUDE.md`/`PUBLICATION_REVIEW.md`/`README.md`/`gui.py`/`docs/CORE_API_PLAN.md`/`docs/GUI_SPEC.md`/`docs/GUI_TEST_CHECKLIST.md`). 이번 회차 재확인 범위: `gui.py`(2160줄) 위젯 25개·`FORMAT_OPTIONS` 6종·`_get_export_format()` 재사용(2026-06-30 수정 반영)·`_test_channels_parallel()` dead code 잔존(gui.py:758, 미호출, 코드 정리 권고 재확인)·`_validate_inputs()`/`_run_export()` 에러 문자열 전수, `utils.py`(URL 파싱 6종 에러메시지·`validate_channel_id`/`validate_date_range`/`validate_output_directory`/`validate_dce_executable`·`sanitize_error_message`·`convert_json_to_markdown`·`cleanup_avatar_emoji_files`), `exporter.py`(`_build_command`·`safe_mode`→`--parallel 1`·스트리밍/블로킹 이중 경로), `config.py`(`_auto_detect_dce` 3-OS 분기·0600 권한·env>config 우선순위), `cli.py`(서브커맨드 6종·`CLI_FORMATS`·`--include-threads` choices), `pyproject.toml`/`.github/workflows/test.yml`(CI 매트릭스: ubuntu+macos py3.9-3.13 + windows-latest py3.12 smoke), `PROJECT.md`/`NOTICE.md`/`PUBLICATION_REVIEW.md`(공개 준비 상태 문구 일치) — 전체 MATCH. |
| 2026-07-08 | Doc-Sync 19차 검증 — MISMATCH 0건. 전 회차(18차, 2026-07-07) 대비 소스 커밋 없음(마지막 커밋 여전히 `24ded85`, 2026-06-05; 동일 8개 파일 uncommitted 상태 유지, `gui.py` mtime 2026-06-30 이후 변경 없음). 이번 회차 재확인 범위: `cli.py`/`config.py`/`utils.py`/`exporter.py`/`__init__.py`/`pyproject.toml` 전량 재독, `gui.py` 2160줄 전량 재독(위젯 25개·`FORMAT_OPTIONS` 6종·`_get_export_format()` 재사용·`_test_channels_parallel()` dead code 잔존(gui.py:758, 미호출) 재확인), `setup.py`, `tests/`(5개 파일 704줄), `.github/workflows/test.yml`(CI 매트릭스 재확인), `PROJECT.md`/`NOTICE.md`/`PUBLICATION_REVIEW.md` 공개 준비 문구 재확인. 교차 검증: README "토큰이 설정되지 않았습니다"(gui.py:1328 `_on_export` 초기 자동 프롬프트 로그)와 GUI_SPEC E1 "Discord 토큰이 설정되지 않았습니다"(gui.py:1883/1535 `_validate_inputs`/`_run_export` 검증 실패 경로)가 서로 다른 코드 경로의 문자열을 각각 정확히 인용하고 있음을 확인 — 오탐 아님, 수정 불필요. `ruff check discord_exporter/ tests/` 재실행 clean, `pytest` 로컬 미설치 재확인(PUBLICATION_REVIEW.md 기재와 일치) — 전체 MATCH, 신규 UNDOCUMENTED/STALE 없음. |
| 2026-07-09 | Doc-Sync 20차 검증 — MISMATCH 1건 수정: GUI_SPEC §2 위젯 목록의 `btn_browse_output`/`btn_open_folder`/`btn_clear_log`가 `gui.py`에서 `self.` 인스턴스 속성으로 저장되지 않는 익명 `ttk.Button`으로 구현되어 있음(실제 명명된 버튼 속성은 `self.btn_export`/`self.btn_stop` 2개뿐, `grep -c "self\.btn_" gui.py` = 9건 전부 이 2개에서만 발생)을 확인하고 표에 `†` 각주로 명시(라벨·동작 자체는 일치, 속성명만 실재하지 않음 — 기능적 MATCH이나 "위젯 ID" 표기가 오도 가능하여 저심각 MISMATCH로 분류). 전 회차(19차, 2026-07-08) 대비 소스 커밋 없음(마지막 커밋 `24ded85` 유지, 8개 파일 uncommitted 그대로). 재확인 범위: CLI 서브커맨드 6종·`CLI_FORMATS`/`ExportFormat.from_string`(`md`/`markdown`/`obsidian` 별칭 일치)·`validate_channel_id`/`validate_date_range`/`validate_output_directory`/`validate_dce_executable`/`parse_date` 에러 문자열 전수 재대조(README §GUI 오류표, GUI_SPEC §5 E1-E10, GUI_TEST_CHECKLIST 시나리오 1-10과 문자 단위 일치)·`FORMAT_OPTIONS` 6종·`_test_channels_parallel` dead code 잔존 재확인(호출부 0건)·`.env.example` Linux 경로 예시·`NOTICE.md`/CI 매트릭스(ubuntu+macos py3.9-3.13+windows smoke). `ruff check discord_exporter/ tests/` clean, `pytest` 로컬 미설치 재확인. 나머지 전체 MATCH. |
