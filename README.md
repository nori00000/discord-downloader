# Discord Downloader

![CI](https://github.com/nori00000/discord-downloader/actions/workflows/test.yml/badge.svg)

[DiscordChatExporter.Cli](https://github.com/Tyrrrz/DiscordChatExporter)를 쉽게 사용하기 위한 크로스 플랫폼 CLI/GUI 래퍼 도구입니다.

이제 기본 명령어는 `discord-downloader`이며, 기존 `discord-exporter` 명령도 하위 호환용으로 계속 동작합니다.

## 주요 기능

- Discord 채널 URL 또는 채널 ID로 채팅 로그 내보내기
- 다양한 출력 형식: HTML, TXT, JSON, CSV, **Markdown (Obsidian 호환)**
- 날짜 범위 지정 내보내기 (단일 채널/서버/DM)
- 서버 전체(guild) / DM 전체 일괄 내보내기
- 토큰 안전 저장 (로컬 파일, `chmod 600`, 외부 전송 없음)
- GUI (tkinter) / CLI 두 가지 인터페이스
- macOS (Apple Silicon) 및 Windows 지원

## 사전 요구사항

1. **Python 3.8 이상**
2. **DiscordChatExporter.Cli** - [릴리즈 페이지](https://github.com/Tyrrrz/DiscordChatExporter/releases)에서 다운로드

### DiscordChatExporter.Cli 다운로드

| OS | 다운로드 파일 |
|----|-------------|
| macOS (M1/M2/M3) | `DiscordChatExporter.Cli.osx-arm64.zip` |
| macOS (Intel) | `DiscordChatExporter.Cli.osx-x64.zip` |
| Windows (64-bit) | `DiscordChatExporter.Cli.win-x64.zip` |
| Windows (ARM) | `DiscordChatExporter.Cli.win-arm64.zip` |

## 설치

### macOS

```bash
# 1. 저장소 클론 또는 소스 다운로드
cd ~/Documents/dev/discord-downloader

# 2. 패키지 설치 (editable 모드)
pip3 install -e .

# 3. DiscordChatExporter.Cli 다운로드 및 압축 해제
# ~/Downloads/DiscordChatExporter.Cli.osx-arm64/ 에 위치한다고 가정

# 4. 실행 권한 부여 (macOS에서 필요)
chmod +x ~/Downloads/DiscordChatExporter.Cli.osx-arm64/DiscordChatExporter.Cli
```

### Windows (PowerShell)

```powershell
# 1. 저장소 클론 또는 소스 다운로드
cd C:\Users\YourName\Documents\discord-downloader

# 2. 패키지 설치
pip install -e .

# 3. DiscordChatExporter.Cli 다운로드 및 압축 해제
# C:\Tools\DiscordChatExporter\ 에 위치한다고 가정
```

### pip를 통한 직접 설치

```bash
# macOS
pip3 install .

# Windows
pip install .
```

## 초기 설정

처음 사용 시 Discord 토큰과 DCE 경로를 설정해야 합니다.

```bash
discord-downloader setup
```

또는 명령줄로 직접 설정:

```bash
# macOS
discord-downloader setup --dce-path ~/Downloads/DiscordChatExporter.Cli.osx-arm64/DiscordChatExporter.Cli

# Windows
discord-downloader setup --dce-path "C:\Tools\DiscordChatExporter\DiscordChatExporter.Cli.exe"
```

### 환경 변수로 설정 (선택사항)

```bash
# macOS/Linux (.zshrc 또는 .bashrc에 추가)
export DISCORD_TOKEN="your-token-here"
export DCE_PATH="$HOME/Downloads/DiscordChatExporter.Cli.osx-arm64/DiscordChatExporter.Cli"

# Windows (PowerShell 프로필에 추가)
$env:DISCORD_TOKEN = "your-token-here"
$env:DCE_PATH = "C:\Tools\DiscordChatExporter\DiscordChatExporter.Cli.exe"
```

## Discord 토큰 얻기

1. Discord 웹/앱에서 개발자 도구 열기 (F12 또는 Cmd+Option+I)
2. Network 탭 선택
3. 아무 채널 클릭
4. `messages` 요청 찾기
5. Headers에서 `authorization` 값 복사

> **주의**: 토큰은 절대 타인과 공유하지 마세요. 이 도구는 토큰을 로컬에만 저장하며 외부로 전송하지 않습니다.

## GUI 사용법

GUI를 사용하면 명령어 없이 시각적으로 Discord 채팅을 내보낼 수 있습니다.

### GUI 실행

```bash
# 방법 1: 모듈로 실행
python -m discord_exporter.gui

# 방법 2: 엔트리포인트로 실행 (pip install 후)
discord-downloader-gui
```

### GUI 사용 절차

1. **초기 설정** (최초 1회)
   - 상태바에서 "토큰 설정" 클릭 → Discord 토큰 입력
   - "찾아보기" 클릭 → DiscordChatExporter.Cli 파일 선택

2. **내보내기 실행**
   - 입력 방식 선택: "채널 URL" 또는 "채널 ID"
   - Discord에서 채널 URL 복사하여 붙여넣기
   - 출력 형식 선택 (HTML Dark 권장)
   - "내보내기 실행" 클릭

3. **완료**
   - 완료 다이얼로그에서 "폴더 열기" 클릭
   - 또는 상태바에 표시된 경로 확인

### GUI 자주 겪는 오류

| 오류 | 원인 | 해결 방법 |
|------|------|----------|
| "토큰이 설정되지 않았습니다" | 토큰 미입력 | 상태바 "토큰 설정" 클릭 → 토큰 입력 |
| "DCE 파일을 찾을 수 없습니다" | DCE 경로 잘못됨 | "찾아보기"로 DCE 파일 다시 선택 |
| "DCE 파일에 실행 권한이 없습니다" | macOS 권한 문제 | 터미널에서 `chmod +x /path/to/DCE` 실행 |
| "URL 형식을 인식할 수 없습니다" | 잘못된 URL | Discord에서 채널 URL 다시 복사 |
| "시작일이 종료일보다 늦습니다" | 날짜 순서 오류 | 시작일을 종료일보다 이전으로 수정 |
| "폴더에 쓰기 권한이 없습니다" | 출력 폴더 권한 | 다른 폴더 선택 또는 권한 변경 |

### Discord 채널 URL 복사 방법

1. Discord 웹 또는 앱에서 원하는 채널 열기
2. 브라우저 주소창의 URL 복사 (웹)
3. 또는 채널 우클릭 → "링크 복사" (앱)

URL 형식: `https://discord.com/channels/서버ID/채널ID`

---

## CLI 사용법

### 단일 채널 내보내기

```bash
# URL로 내보내기
discord-downloader export --url "https://discord.com/channels/123456789/987654321" --format html

# 채널 ID로 내보내기
discord-downloader export --channel-id 987654321 --format txt

# 출력 디렉터리 지정
discord-downloader export --channel-id 987654321 --format html --output-dir ./exports

# 날짜 범위 지정
discord-downloader export --channel-id 987654321 --after "2024-01-01" --before "2024-12-31"

# 미디어(이미지, 첨부파일) 포함
discord-downloader export --channel-id 987654321 --format html --media
```

### 서버 전체 내보내기

```bash
# 서버 ID로 내보내기
discord-downloader exportguild --guild-id 123456789 --format html

# URL로 내보내기 (아무 채널 URL)
discord-downloader exportguild --url "https://discord.com/channels/123456789/987654321"
```

### DM 전체 내보내기

```bash
discord-downloader exportdm --format json
```

### 목록 조회

```bash
# 접근 가능한 서버 목록
discord-downloader list-guilds

# 서버의 채널 목록
discord-downloader list-channels --guild-id 123456789

# DM 채널 목록
discord-downloader list-dm
```

## 출력 형식

| 형식 | 설명 | 파일 확장자 |
|-----|------|-----------|
| `html` | HTML Dark 테마 (기본값) | `.html` |
| `html-dark` | HTML Dark 테마 | `.html` |
| `html-light` | HTML Light 테마 | `.html` |
| `txt` | 일반 텍스트 | `.txt` |
| `json` | JSON 형식 | `.json` |
| `csv` | CSV 형식 | `.csv` |
| `md` / `markdown` | Markdown (Obsidian 호환) | `.md` |
| `obsidian` | `md`의 별칭 — Obsidian Vault에 바로 드롭 | `.md` |

Markdown 내보내기는 내부적으로 DCE의 JSON 익스포트를 돌린 뒤 이미지 임베드,
서버/채널 헤더, 날짜별 섹션, 반응(reaction) 각주를 포함한 Obsidian-friendly
구조로 변환합니다.

## 명령어 옵션

### export

| 옵션 | 설명 |
|-----|------|
| `--url` | Discord 채널 URL |
| `-c, --channel-id` | Discord 채널 ID |
| `-f, --format` | 출력 형식 (기본값: html) |
| `-o, --output-dir` | 출력 디렉터리 |
| `--after` | 이 날짜 이후 메시지만 (YYYY-MM-DD) |
| `--before` | 이 날짜 이전 메시지만 (YYYY-MM-DD) |
| `--media` | 미디어 파일 다운로드 |
| `--include-threads` | 스레드 포함 (none/active/all) |

### exportguild

| 옵션 | 설명 |
|-----|------|
| `--url` | Discord 서버 URL (아무 채널 URL) |
| `-g, --guild-id` | Discord 서버 ID |
| (export와 동일한 옵션들) | |

### exportdm

| 옵션 | 설명 |
|-----|------|
| (export와 동일한 옵션들, URL/ID 제외) | |

## 설정 파일 위치

- **macOS/Linux**: `~/.discord-downloader/`
- **Windows**: `C:\Users\YourName\.discord-downloader\`

설정 파일:
- `config.json` - JSON 형식 설정
- `.env` - 환경 변수 형식 설정

## 출력 파일명

기본 파일명 형식: `channel-<채널ID>-<YYYYMMDD-HHMMSS>.<확장자>`

예: `channel-987654321-20240115-143022.html`

## 문제 해결

### macOS에서 "개발자를 확인할 수 없음" 오류

```bash
# DiscordChatExporter.Cli가 있는 디렉터리에서
xattr -d com.apple.quarantine DiscordChatExporter.Cli
```

### DCE를 찾을 수 없음

```bash
# DCE 경로 재설정
discord-downloader setup --dce-path /path/to/DiscordChatExporter.Cli
```

### 토큰 재설정

```bash
discord-downloader setup
# "토큰을 변경하시겠습니까?" 에서 y 입력
```

## 보안

토큰 처리는 가능한 한 보수적으로 설계되어 있습니다:

- **로컬 저장 전용.** 토큰은 `~/.discord-downloader/{config.json, .env}`에만
  기록되며, 외부 서비스로 전송되는 일은 없습니다. 네트워크 호출은 전부 DCE
  서브프로세스를 통해서만 발생합니다.
- **`chmod 0600` 자동 적용.** 설정 파일은 저장 즉시 소유자만 읽고 쓸 수 있게
  권한이 조여지며, 이전 버전에서 만들어진 world-readable 파일은 `ConfigManager`
  생성 시점에 자동으로 마이그레이션됩니다. (Windows에서는 POSIX 퍼미션 대신
  사용자 프로필 디렉토리의 ACL에 의존합니다.)
- **에러/로그 마스킹.** 모든 서브프로세스 출력은 `utils.sanitize_error_message`를
  통과해 Discord 토큰 패턴(`<TOKEN>`)으로 치환된 뒤에만 로그/예외에 기록됩니다.
  GUI의 상태바는 토큰 실값 대신 `✓ 설정됨` 상태 표시만 보여줍니다.
- **토큰 표시 규칙.** 대화형 입력은 `getpass` 사용, 설정 요약에는 `mask_token()`이
  적용한 `xxxx...xxxx` 형식만 노출됩니다.

의심스러운 노출이 있었다면 Discord 비밀번호를 변경해 기존 토큰을 무효화한 뒤
`discord-downloader setup`으로 새 토큰을 등록하는 것을 권장합니다.

## 개발 / 테스트

```bash
# dev 의존성과 함께 editable 설치
pip install -e ".[dev]"

# 린트
ruff check discord_exporter/ tests/

# 테스트
pytest
```

CI는 Linux + macOS 매트릭스(Py 3.9 – 3.13)와 Windows smoke 잡으로 구성되어
있습니다 — `.github/workflows/test.yml` 참고.

## 라이선스

MIT License

## 참고

- [DiscordChatExporter](https://github.com/Tyrrrz/DiscordChatExporter) - 실제 내보내기를 수행하는 도구
