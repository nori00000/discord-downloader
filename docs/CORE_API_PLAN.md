# 코어 API 설계 문서

> **버전**: 1.0
> **작성일**: 2025-01-13
> **목적**: GUI/CLI 공용 API 설계
> **상태**: 구현 완료 (이 문서는 설계 당시의 의도를 기록한 역사 문서입니다)
>
> **설계 대비 실제 구현 차이**:
> - `LogEvent.raw_line` 필드: 설계에 포함됐으나 최종 구현에서 제거됨
> - `ExportOptions.safe_mode` 필드: 설계 이후 추가됨 (`--parallel 1` 옵션 제어)
> - `gui_dialogs.py`: 별도 파일 대신 `gui.py` 내부 클래스로 통합 구현됨

---

## 1. 현재 구조 분석

### 현재 문제점

| 파일 | 문제점 | 영향 |
|------|--------|------|
| `exporter.py` | `subprocess.run()` 사용 → 블로킹 | GUI 멈춤 |
| `exporter.py` | `print()` 직접 호출 | GUI 로그 연동 불가 |
| `exporter.py` | 스트리밍 출력 없음 | 실시간 진행 표시 불가 |

### 현재 데이터 흐름

```
CLI/GUI → Exporter.export_channel() → _run_command() → subprocess.run()
                                            │
                                            ├── print() ← 문제: GUI에서 캡처 불가
                                            └── return result ← 완료 후에만 반환
```

---

## 2. 목표 API 설계

### 설계 원칙
1. **CLI 하위 호환성**: 기존 CLI 동작 변경 없음
2. **최소 변경**: `exporter.py`만 수정, 다른 파일 유지
3. **콜백 기반**: 로그 이벤트를 콜백으로 전달
4. **토큰 마스킹**: 모든 출력 지점에서 마스킹 보장

### 목표 데이터 흐름

```
GUI ─────────────────────────────────────────────────────────────┐
  │                                                              │
  │  log_callback(LogEvent)  ◄───────────────────────────┐       │
  │                                                      │       │
  └──► Exporter.export_channel(options, log_callback) ───┘       │
                      │                                          │
                      ▼                                          │
              _run_command_streaming()                           │
                      │                                          │
                      ├── line by line ──► LogEvent 생성         │
                      │                         │                │
                      │                         ▼                │
                      │                   마스킹 처리 ────────────┘
                      │
                      └── subprocess.Popen (스트리밍)
```

---

## 3. API 인터페이스 정의

### 3.1 입력 파라미터 (ExportOptions 확장 없음)

현재 `ExportOptions` 그대로 사용:

```python
@dataclass
class ExportOptions:
    channel_id: Optional[str] = None      # 필수 (export 시)
    guild_id: Optional[str] = None        # 필수 (exportguild 시)
    export_format: ExportFormat = HTML_DARK
    output_path: Optional[Path] = None    # 자동 생성 가능
    output_dir: Optional[Path] = None     # 출력 디렉터리
    after: Optional[str] = None           # YYYY-MM-DD
    before: Optional[str] = None          # YYYY-MM-DD
    media: bool = False                   # --media 옵션
    include_threads: Optional[str] = None # none/active/all
```

### 3.2 로그 이벤트 모델 (신규)

```python
from enum import Enum
from dataclasses import dataclass
from typing import Optional

class LogLevel(Enum):
    """로그 레벨"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"

@dataclass
class LogEvent:
    """GUI/CLI로 전달되는 로그 이벤트"""
    level: LogLevel
    message: str                    # 마스킹 적용된 메시지
    timestamp: str                  # HH:MM:SS 형식
    raw_line: Optional[str] = None  # DCE 원본 출력 (마스킹됨)
```

### 3.3 콜백 타입 정의

```python
from typing import Callable, Optional

# 로그 콜백: GUI에서 로그 표시에 사용
LogCallback = Callable[[LogEvent], None]

# 기본 콜백 (CLI용): print로 출력
def default_log_callback(event: LogEvent) -> None:
    print(f"[{event.timestamp}] {event.message}")
```

### 3.4 Exporter 메서드 시그니처 변경

```python
class Exporter:
    def export_channel(
        self,
        options: ExportOptions,
        log_callback: Optional[LogCallback] = None  # 추가
    ) -> Path:
        """
        단일 채널 내보내기

        Args:
            options: 내보내기 옵션
            log_callback: 로그 이벤트 콜백 (None이면 print 사용)

        Returns:
            출력 파일 경로
        """
        ...

    def export_guild(
        self,
        options: ExportOptions,
        log_callback: Optional[LogCallback] = None
    ) -> Path:
        ...

    def export_dm(
        self,
        options: ExportOptions,
        log_callback: Optional[LogCallback] = None
    ) -> Path:
        ...
```

---

## 4. 토큰 마스킹 지점

### 마스킹 적용 위치 (총 5개 지점)

| # | 위치 | 파일:함수 | 마스킹 방법 |
|---|------|----------|------------|
| M1 | 실행 커맨드 표시 | `exporter.py:_build_display_command()` | `-t` 다음 값 → `******` |
| M2 | DCE stdout 라인 | `exporter.py:_run_command_streaming()` | `sanitize_error_message()` |
| M3 | DCE stderr 라인 | `exporter.py:_run_command_streaming()` | `sanitize_error_message()` |
| M4 | Exception 메시지 | `exporter.py:_run_command_streaming()` | `sanitize_error_message()` |
| M5 | 설정 표시 | `config.py:mask_token()` | `xxxx...xxxx` |

### 마스킹 흐름도

```
DCE subprocess
     │
     ├── stdout ──► sanitize_error_message() ──► LogEvent.message
     │
     ├── stderr ──► sanitize_error_message() ──► LogEvent.message
     │
     └── exception ──► sanitize_error_message() ──► raise ExportError
                                                        │
                                                        ▼
                                              (토큰 없는 에러 메시지)
```

---

## 5. 내부 구현 변경 사항

### 5.1 스트리밍 실행 메서드 (신규)

```python
def _run_command_streaming(
    self,
    cmd: List[str],
    log_callback: LogCallback
) -> int:
    """
    DCE 명령을 스트리밍 모드로 실행

    - subprocess.Popen 사용
    - stdout/stderr 라인 단위 읽기
    - 각 라인을 LogEvent로 변환하여 콜백 호출
    - 토큰 마스킹 적용

    Returns:
        프로세스 종료 코드
    """
```

### 5.2 표시용 커맨드 생성 (분리)

```python
def _build_display_command(self, cmd: List[str]) -> str:
    """
    로그 표시용 마스킹된 커맨드 문자열 생성

    -t <TOKEN> → -t ******
    """
```

### 5.3 기존 _run_command 유지

```python
def _run_command(self, cmd: List[str]) -> subprocess.CompletedProcess:
    """
    기존 블로킹 실행 (CLI 하위 호환용)

    내부적으로 _run_command_streaming 호출하도록 변경 가능
    또는 그대로 유지하고 export 메서드에서 분기
    """
```

---

## 6. GUI 호출 패턴

### 6.1 스레드에서 실행

```python
import threading
import queue

class ExportWorker:
    def __init__(self, exporter: Exporter, log_queue: queue.Queue):
        self.exporter = exporter
        self.log_queue = log_queue

    def run(self, options: ExportOptions):
        """백그라운드 스레드에서 실행"""
        def log_callback(event: LogEvent):
            self.log_queue.put(event)

        try:
            result = self.exporter.export_channel(options, log_callback)
            self.log_queue.put(LogEvent(
                level=LogLevel.SUCCESS,
                message=f"완료: {result}",
                timestamp=get_timestamp()
            ))
        except ExportError as e:
            self.log_queue.put(LogEvent(
                level=LogLevel.ERROR,
                message=str(e),  # 이미 마스킹됨
                timestamp=get_timestamp()
            ))
```

### 6.2 GUI 메인 루프에서 큐 소비

```python
def poll_log_queue(self):
    """Tkinter after()로 주기적 호출"""
    while not self.log_queue.empty():
        event = self.log_queue.get_nowait()
        self.append_log(event)

    self.root.after(100, self.poll_log_queue)
```

---

## 7. 변경 파일 목록

| 파일 | 상태 | 변경 내용 | 변경 이유 |
|------|------|----------|----------|
| `exporter.py` | **수정** | LogEvent/LogCallback 추가, _run_command_streaming() 추가 | 스트리밍 출력 지원 |
| `utils.py` | **수정** | LogEvent, LogLevel, LogCallback 타입 추가 | 공용 타입 정의 |
| `config.py` | 유지 | 변경 없음 | - |
| `cli.py` | 유지 | 변경 없음 (기존 동작 유지) | 하위 호환성 |
| `gui.py` | **신규** | GUI 구현 | 1단계에서 설계 |

### 변경 최소화 원칙 적용

```
변경 파일: 2개 (exporter.py, utils.py)
신규 파일: 1개 (gui.py) - 별도 단계에서 생성
유지 파일: 2개 (config.py, cli.py)
```

---

## 8. 하위 호환성 보장

### CLI 기존 동작

```python
# 변경 전
exporter.export_channel(options)  # print()로 출력

# 변경 후 - 동일하게 동작
exporter.export_channel(options)  # log_callback=None → 기본 print 콜백 사용
```

### 내부 분기 로직

```python
def export_channel(self, options, log_callback=None):
    if log_callback is None:
        log_callback = default_log_callback  # print 사용

    # 이하 동일한 로직
```

---

## 9. 검증 체크리스트

구현 후 확인 항목:

- [ ] 기존 CLI 명령이 동일하게 동작하는가?
- [ ] log_callback=None 시 print로 출력되는가?
- [ ] LogEvent.message에 토큰이 포함되지 않는가?
- [ ] DCE stdout/stderr가 실시간으로 콜백에 전달되는가?
- [ ] Exception 발생 시에도 토큰이 마스킹되는가?
- [ ] GUI 스레드에서 호출 시 메인 스레드가 블로킹되지 않는가?

---

## 10. 다음 단계

1. **3단계**: `utils.py`에 LogEvent, LogLevel 추가
2. **4단계**: `exporter.py`에 스트리밍 메서드 추가
3. **5단계**: GUI 구현 (`gui.py`)
