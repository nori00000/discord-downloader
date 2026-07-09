# Discord Exporter GUI 설계 문서

> **버전**: 1.0
> **작성일**: 2025-01-13
> **상태**: 구현 완료 (초기 설계 문서 — 실제 구현과 일부 차이 있음, 아래 참고)
>
> **설계 대비 실제 구현 차이**:
> - `ent_channel` (단일 입력) → `ent_url` + `ent_server_id` + `ent_channel_id` + `ent_thread_id` (4개 독립 필드)
> - `btn_toggle_mode` (URL↔ID 전환 버튼) → 없음; URL 자동 분석 후 ID 필드에 자동 입력
> - `radio_format` (Radiobutton, 4개) → `cmb_format` (Combobox, 6개 — Markdown/CSV 추가됨)
> - `btn_settings` (설정 버튼) → 없음; 상태바의 "토큰 설정" + "찾아보기" 버튼으로 분리
> - `progress` (Progressbar) → 없음; `lbl_status` (Label) 로 상태 표시
> - RUNNING 상태: `btn_export` → "취소" 표시 아님; `btn_export` 비활성화 + `btn_stop` 별도 활성화
> - 채널 목록 조회(Treeview) + 배치 내보내기 기능 추가됨 (설계에 없던 기능)

---

## 1. 화면 레이아웃

```
┌─────────────────────────────────────────────────────────────┐
│ [상단 상태바]                                                │
│  토큰: ✓ 설정됨 | DCE: ✓ 설정됨 | 상태: 대기 중              │
├─────────────────────────────────────────────────────────────┤
│ [입력 영역]                                                  │
│                                                             │
│  채널 URL 또는 ID: [________________________] [URL/ID 전환]  │
│                                                             │
│  출력 형식:  ○ HTML(Dark)  ○ HTML(Light)  ○ TXT  ○ JSON    │
│                                                             │
│  출력 폴더:  [____________________] [찾아보기...]            │
│                                                             │
│  ┌─ 날짜 범위 (선택) ─────────────────────────────────────┐ │
│  │  시작일: [YYYY-MM-DD]    종료일: [YYYY-MM-DD]          │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  ☐ 미디어 다운로드 (이미지/첨부파일)                         │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ [실행 영역]                                                  │
│                                                             │
│  [ 내보내기 실행 ]    [ 설정 ]    [ 폴더 열기 ]              │
│                                                             │
│  [■■■■■■■■■■░░░░░░░░░░] 45% - 메시지 수집 중...             │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ [로그 영역]                                                  │
│                                                             │
│  [14:30:22] 내보내기 시작: 채널 1459814338754773161         │
│  [14:30:22] 실행: DCE export -t ****** -c 145981... -f Html │
│  [14:30:25] 메시지 수집 중...                                │
│  [14:30:45] 완료: channel-1459814338754773161-20250113.html │
│                                                             │
│                                                  [ 로그 지우기 ] │
└─────────────────────────────────────────────────────────────┘
```

**영역 크기 비율**: 상태바 5% / 입력 40% / 실행 15% / 로그 40%

---

## 2. 위젯 목록

| 위젯 ID | 타입 | 라벨 | 기본값 | 필수 | 비고 |
|---------|------|------|--------|------|------|
| `lbl_token_status` | Label | 토큰 상태 | "미설정" | - | ✓/✗ + "설정됨"/"미설정" |
| `lbl_dce_status` | Label | DCE 상태 | "미설정" | - | ✓/✗ + 경로 또는 "미설정" |
| `lbl_status` | Label | 현재 상태 | "대기 중" | - | 실행 영역 하단, 상태 머신 반영 |
| `ent_url` | Entry | Discord URL | placeholder | - | URL 자동 분석 → ID 필드 채움 |
| `ent_server_id` | Entry | 서버 ID | "" | 선택 | URL 분석 자동 입력 또는 직접 입력 |
| `ent_channel_id` | Entry | 채널 ID | "" | 선택 | URL 분석 자동 입력 또는 직접 입력 |
| `ent_thread_id` | Entry | 스레드 ID | "" | 선택 | URL 분석 자동 입력 또는 직접 입력 |
| `cmb_format` | Combobox | 출력 형식 | "HTML (Dark)" | **필수** | 6개 옵션 (HTML Dark/Light, Markdown, Plain Text, JSON, CSV) |
| `ent_output_dir` | Entry | 출력 폴더 | 현재 디렉터리 | 선택 | 비어있으면 CWD |
| `btn_browse_output`<sup>†</sup> | Button | 찾아보기 | - | - | 출력 폴더 선택 다이얼로그 |
| `ent_after` | Entry | 시작일 | "" | 선택 | YYYY-MM-DD 형식 |
| `ent_before` | Entry | 종료일 | "" | 선택 | YYYY-MM-DD 형식 |
| `media_enabled` | Checkbutton | 미디어 다운로드 | False | 선택 | --media 옵션 |
| `safe_mode` | Checkbutton | 안전 모드 | True | 선택 | --parallel 1 옵션 |
| `chk_exclude_avatars` / `exclude_avatars` | Checkbutton | 프로필 이미지 제외 | True | 선택 | 미디어 다운로드 시 아바타 파일 자동 삭제; media_enabled=False이면 비활성화 |
| `chk_exclude_emojis` / `exclude_emojis` | Checkbutton | 이모지 제외 | True | 선택 | 미디어 다운로드 시 이모지 파일 자동 삭제; media_enabled=False이면 비활성화 |
| `filter_text_only` | Checkbutton | 텍스트만 | True | 선택 | 채널 목록 조회 시 음성 채널 제외 (--include-vc False 전달) |
| `filter_accessible` | Checkbutton | 접근가능만 | False | 선택 | 채널 목록 조회 후 접근 권한 확인 (ThreadPoolExecutor 10개 병렬 테스트) |
| `lbl_export_target` | Label | 내보내기 대상 | `"URL을 입력하세요"` (gray) — 첫 `_update_export_target()` 호출 후 `"URL 또는 ID를 입력하세요"`로 변경 | - | URL 파싱 또는 ID 직접 입력에 따라 대상 표시; URL 오류 시 `"URL 오류"` (red); 체크된 채널 수 표시 가능 |
| `cmb_threads` | Combobox | 스레드 포함 | `"all"` | 선택 | `"none"` / `"active"` / `"all"`; 서버 전체 내보내기(`exportguild`) 시에만 적용; `include_threads` StringVar 연동 |
| `btn_export` | Button | 내보내기 실행 | - | - | 메인 액션; 실행 중 비활성화 |
| `btn_stop` | Button | 중지 | - | - | 실행 중에만 활성화; 취소 신호 전송 |
| `btn_open_folder`<sup>†</sup> | Button | 폴더 열기 | - | - | 출력 폴더 열기 |
| `channel_tree` | Treeview | 채널 목록 | - | - | 채널 조회 + 배치 선택 체크박스 |
| `txt_log` | Text | 로그 | "" | - | 읽기 전용, 스크롤 |
| `btn_clear_log`<sup>†</sup> | Button | 로그 지우기 | - | - | 로그 초기화 |

> **설계 원본과의 차이**: `btn_toggle_mode`, `btn_settings`, `progress`(Progressbar)는 구현에서 제거됨.
> `ent_channel` 단일 필드 → `ent_url` + `ent_server_id/channel_id/thread_id` 3개 독립 필드로 분리.
> `radio_format` → `cmb_format` (Combobox, 옵션 수 4→6)으로 변경.
>
> <sup>†</sup> **구현 참고 (2026-07-09 Doc-Sync 재확인)**: `btn_browse_output`/`btn_open_folder`/`btn_clear_log`는
> `gui.py`에서 라벨·동작은 표와 일치하나 `self.` 인스턴스 속성으로 저장되지 않는 익명 `ttk.Button`으로 구현되어
> 있습니다(`self.btn_export`/`self.btn_stop`만 실제 명명된 속성으로 존재). 표의 "위젯 ID"는 기능 식별용 명칭이며
> 코드에서 해당 이름으로 직접 접근 가능한 속성이 아님에 주의하세요.

---

## 3. 상태 전이 (State Machine)

```
                    ┌──────────────┐
                    │              │
        ┌───────────│    IDLE      │◄──────────────┐
        │           │   (대기 중)   │               │
        │           └──────┬───────┘               │
        │                  │                       │
        │         [내보내기 클릭]                   │
        │                  │                       │
        │                  ▼                       │
        │           ┌──────────────┐               │
        │           │              │               │
        │           │  VALIDATING  │───[검증 실패]──┘
        │           │   (검증 중)   │
        │           └──────┬───────┘
        │                  │
        │            [검증 성공]
        │                  │
        │                  ▼
        │           ┌──────────────┐
        │           │              │
   [취소 클릭]◄─────│   RUNNING    │
        │           │   (실행 중)   │
        │           └──────┬───────┘
        │                  │
        │         ┌────────┴────────┐
        │         │                 │
        │         ▼                 ▼
        │   ┌──────────┐     ┌──────────┐
        │   │          │     │          │
        └──►│   DONE   │     │  FAILED  │
            │  (완료)   │     │  (실패)   │
            └──────────┘     └──────────┘
                 │                 │
                 └────────┬────────┘
                          │
                    [즉시 자동]
                          │
                          ▼
                    ┌──────────────┐
                    │     IDLE     │
                    └──────────────┘
```

### 상태별 UI 동작

| 상태 | btn_export | btn_stop | 입력 필드 | lbl_status | 로그 |
|------|------------|----------|----------|------------|------|
| IDLE | 활성화 "내보내기 실행" | 비활성화 | 편집 가능 | "대기 중" (gray) | 유지 |
| VALIDATING | 비활성화 | 비활성화 | 편집 가능 | — | "검증 시작..." |
| RUNNING | 비활성화 | **활성화 "중지"** | 편집 가능 | "실행 중..." (blue) | 실시간 업데이트 |
| DONE | 활성화 | 비활성화 | 편집 가능 | "완료: [경로]" (green) | "완료" 메시지 |
| FAILED | 활성화 | 비활성화 | 편집 가능 | "실패" (red) | 에러 메시지 |

> **설계 원본과의 차이**: RUNNING 상태에서 `btn_export`가 "취소"로 변경되는 방식 대신,
> `btn_export` 비활성화 + 별도 `btn_stop` 활성화 방식으로 구현됨.
> `progress` Progressbar 없음; `lbl_status` Label로 상태 표시.
> DONE/FAILED → IDLE 전환은 설계 원본의 "3초 후 자동"과 달리 **즉시** 전환됨
> (`_set_running_state(False)` 즉시 호출; `after(3000)` 미구현).

---

## 4. 사용자 시나리오 (정상 흐름) - 6개

### 시나리오 1: 최초 실행 → 설정 완료
1. 사용자가 앱 실행
2. 상태바에 "토큰: ✗ 미설정" 표시
3. 상태바의 "토큰 설정" 버튼 클릭 → 팝업에서 토큰 입력 (마스킹 표시) → 확인
4. 상태바의 "찾아보기" 버튼 클릭 → 파일 다이얼로그에서 DCE 실행 파일 선택
5. 상태바 갱신 "토큰: ✓ 설정됨" / "DCE: ✓ 설정됨"

> **구현 참고**: `btn_settings`·설정 다이얼로그·[저장] 버튼은 존재하지 않음. 상태바의 "토큰 설정" + "찾아보기" 버튼으로 분리 구현됨 (헤더 주석 참조).

### 시나리오 2: URL로 채널 내보내기
1. 채널 URL 붙여넣기: `https://discord.com/channels/123/456`
2. 출력 형식 선택: HTML(Dark)
3. [내보내기 실행] 클릭
4. 진행률 표시, 로그에 진행 상황
5. 완료 메시지 + 파일 경로 표시
6. [폴더 열기] 클릭하여 결과 확인

### 시나리오 3: 채널 ID로 내보내기
1. "채널 ID" 입력란에 채널 ID를 직접 입력: `1459814338754773161` (`ent_channel_id` 필드)
2. 출력 형식: TXT 선택
3. [내보내기 실행] → 완료

> **구현 참고**: `btn_toggle_mode`(URL↔ID 전환 버튼)은 존재하지 않음. URL 입력 시 ID 필드가 자동 채워지고, 채널 ID 필드에 직접 입력도 가능함.

### 시나리오 4: 날짜 범위 지정 내보내기
1. 채널 URL 입력
2. 시작일: `2024-01-01`, 종료일: `2024-12-31`
3. [내보내기 실행]
4. 해당 기간 메시지만 내보내기 완료

### 시나리오 5: 미디어 포함 내보내기
1. 채널 URL 입력
2. "미디어 다운로드" 체크
3. [내보내기 실행]
4. 이미지/첨부파일 포함하여 내보내기 완료

### 시나리오 6: 출력 폴더 변경
1. [찾아보기...] 클릭
2. 폴더 선택 다이얼로그에서 원하는 폴더 선택
3. 경로가 입력 필드에 표시
4. 내보내기 실행 → 선택한 폴더에 저장

---

## 5. 에러 시나리오 - 10개

| # | 에러 상황 | 표시 메시지 | 사용자 조치 |
|---|----------|------------|------------|
| E1 | 토큰 미설정 | "Discord 토큰이 설정되지 않았습니다" | [설정] 버튼 클릭 → 토큰 입력 |
| E2 | DCE 경로 미설정 | "DCE 경로가 설정되지 않았습니다." (`validate_dce_executable()` 반환값) | [설정] 버튼 클릭 → 경로 지정 |
| E3 | DCE 파일 없음 | "DCE 파일을 찾을 수 없습니다: [경로]" | [설정]에서 올바른 경로로 수정 |
| E4 | 채널 ID 비어있음 | "내보내기 대상이 없습니다.\nDiscord URL을 입력하거나 채널을 체크해주세요." (`gui.py:_validate_inputs`) | 채널 URL/ID 입력 또는 채널 목록에서 체크 |
| E5 | 잘못된 URL 형식 | 다이얼로그 없음; `lbl_export_target`에 `"URL 오류"` 인라인 표시 (`gui.py:_on_parse_url` ValueError 처리). 이후 내보내기 클릭 시 ID 필드가 비어있으면 E4 메시지 발생 | URL 재입력 또는 채널 ID 직접 입력 |
| E6 | 잘못된 채널 ID | `"채널 ID 오류: Channel ID should be 17-20 digits, got N digits"` (`validate_channel_id()` 영문 ValueError, `_validate_inputs`에서 `"채널 ID 오류: "` 접두어 래핑) | 올바른 채널 ID 입력 |
| E7 | 잘못된 날짜 형식 | `"날짜 형식이 올바르지 않습니다: '{date_str}'\n올바른 형식: YYYY-MM-DD (예: 2024-01-15)"` (`utils.py:parse_date()`) | 날짜 형식 수정 |
| E8 | 출력 폴더 접근 불가 | `"폴더에 쓰기 권한이 없습니다: {path}"` (`utils.py:validate_output_directory()`) | 다른 폴더 선택 또는 권한 수정 |
| E9 | DCE 실행 실패 | "내보내기 실패: [마스킹된 에러]" | 로그 확인 후 설정/입력 수정 |
| E10 | 네트워크/인증 오류 | "Discord 접근 실패. 토큰을 확인하세요" | [설정]에서 토큰 재입력 |

### 에러 표시 방식
- 입력 검증 에러: 해당 필드 아래에 빨간색 텍스트
- 실행 에러: 로그 영역에 `[ERROR]` 태그로 표시
- 모든 에러 메시지는 `sanitize_error_message()` 적용

---

## 6. 보안 규칙

### 토큰 표시 금지
```
✓ 올바른 표시: "토큰: ✓ 설정됨"
✓ 올바른 표시: "토큰: ✗ 미설정"
✗ 금지: "토큰: MTIzNDU2Nzg5MDEyMzQ1Njc4.xxxxx"
✗ 금지: "토큰: MTIz...xxx (일부 표시)"
```

### 설정 다이얼로그
```python
# 토큰 입력 필드
Entry(show="*")  # 입력 시 **** 표시

# 현재 토큰 상태
if token_exists:
    label.config(text="현재 토큰: ****...****")  # mask_token() 사용
```

### 로그 마스킹
```
✓ 올바름: [14:30:22] 실행: DCE export -t ****** -c 1459... -f HtmlDark
✗ 금지:   [14:30:22] 실행: DCE export -t MTIzNDU2... -c 1459... -f HtmlDark
```

### 에러 메시지 마스킹
- 모든 에러는 `utils.sanitize_error_message(error, token)` 처리
- Exception traceback에도 토큰 포함 가능성 → 필터링 필수

---

## 7. 구현 파일 목록

| 파일 | 상태 | 변경 내용 |
|------|------|----------|
| `discord_exporter/gui.py` | **완료** | 메인 GUI 애플리케이션 (설정 다이얼로그 포함) |
| `pyproject.toml` | **완료** | GUI 엔트리포인트 추가됨 |
| `discord_exporter/config.py` | 유지 | 재사용 (수정 없음) |
| `discord_exporter/utils.py` | 유지 | 재사용 (수정 없음) |
| `discord_exporter/exporter.py` | 유지 | 재사용 (수정 없음) |
| `discord_exporter/cli.py` | 유지 | 재사용 (수정 없음) |

> **참고**: 당초 설계에서 별도 파일로 계획했던 `gui_dialogs.py`(설정 다이얼로그)는
> `gui.py` 내부 클래스로 통합되어 별도 파일로 생성되지 않았습니다.

### 엔트리포인트 (적용 완료)

```toml
# pyproject.toml
[project.scripts]
discord-exporter = "discord_exporter.cli:main"

[project.gui-scripts]
discord-exporter-gui = "discord_exporter.gui:main"
```

---

## 8. 검증 체크리스트

구현 완료 후 확인할 항목:

- [ ] 토큰이 UI 어디에도 평문 표시되지 않음
- [ ] 로그에 토큰이 마스킹되어 표시됨
- [ ] 에러 메시지에 토큰이 포함되지 않음
- [ ] macOS에서 정상 동작
- [ ] Windows에서 정상 동작
- [ ] CLI 기능이 영향받지 않음
- [ ] 상태 전이가 설계대로 동작함
- [ ] 모든 에러 시나리오가 처리됨
