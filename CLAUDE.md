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
- [ ] `cli.py`: 커맨드 빌드 시 `-t` 인자 다음 값 마스킹
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
└── gui.py         # GUI 프론트엔드 (예정)
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
