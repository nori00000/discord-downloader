# Discord Downloader

![CI](https://github.com/nori00000/discord-downloader/actions/workflows/test.yml/badge.svg)

[DiscordChatExporter.Cli](https://github.com/Tyrrrz/DiscordChatExporter)를 좀 더 쉽게 쓰기 위한 도구입니다.
터미널로 써도 되고, 버튼이 있는 화면(GUI)으로 써도 됩니다.

이제 기본 명령어는 `discord-downloader`입니다.
예전에 쓰던 `discord-exporter` 명령도 당분간은 그대로 쓸 수 있습니다.

## 주요 기능

- Discord 채널 링크나 채널 번호로 대화 내용 저장하기
- 여러 형식으로 저장하기: HTML, TXT, JSON, CSV, **Markdown (Obsidian 호환)**
- 날짜를 정해서 원하는 기간만 저장하기
- 서버 전체 / DM 전체 한 번에 저장하기
- 토큰을 내 컴퓨터에만 안전하게 저장하기
- 화면으로 쓰는 GUI와 명령어로 쓰는 CLI 둘 다 지원
- macOS (Apple Silicon) 및 Windows 지원

## 먼저 준비할 것

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

## 처음 한 번만 설정하면 돼요

처음 쓸 때는 Discord 토큰과 DCE 파일 위치를 알려줘야 합니다.

```bash
discord-downloader setup
```

아래처럼 한 번에 넣어도 됩니다:

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

## Discord 토큰 찾는 방법

1. Discord 웹이나 앱에서 개발자 도구를 엽니다. `F12` 또는 `Cmd+Option+I`
2. `Network` 탭을 누릅니다.
3. 아무 채널이나 한 번 클릭합니다.
4. `messages` 요청을 찾습니다.
5. `Headers` 안의 `authorization` 값을 복사합니다.

> **주의**: 토큰은 비밀번호처럼 생각하면 됩니다. 다른 사람에게 보내지 마세요.

## 화면으로 쓰는 방법

GUI를 쓰면 명령어를 몰라도 버튼만 눌러서 저장할 수 있습니다.

### 화면 열기

```bash
# 방법 1: 모듈로 실행
python -m discord_exporter.gui

# 방법 2: 엔트리포인트로 실행 (pip install 후)
discord-downloader-gui
```

### 이렇게 쓰면 됩니다

1. **처음 한 번**
   - 위쪽에서 `토큰 넣기`를 누르고 Discord 토큰을 넣습니다.
   - `찾아보기`를 눌러 `DiscordChatExporter.Cli` 파일을 고릅니다.

2. **저장하기**
   - 디스코드 채널 링크를 붙여넣거나 채널 번호를 넣습니다.
   - 원하는 저장 형식을 고릅니다.
   - `저장 시작`을 누릅니다.

3. **끝나면**
   - `폴더 열기`를 눌러 바로 결과를 볼 수 있습니다.
   - 또는 화면 아래에 나온 저장 위치를 확인하면 됩니다.

### 자주 생기는 문제

| 오류 | 원인 | 해결 방법 |
|------|------|----------|
| "토큰이 설정되지 않았습니다" | 토큰을 안 넣음 | 위쪽 `토큰 넣기`를 눌러 토큰 입력 |
| "DCE 파일을 찾을 수 없습니다" | DCE 파일 위치가 틀림 | `찾아보기`로 DCE 파일 다시 선택 |
| "DCE 파일에 실행 권한이 없습니다" | macOS 권한 문제 | 터미널에서 `chmod +x /path/to/DCE` 실행 |
| "URL 형식을 인식할 수 없습니다" | 링크가 잘못됨 | Discord에서 채널 링크 다시 복사 |
| "시작일이 종료일보다 늦습니다" | 날짜 순서 오류 | 시작일을 종료일보다 이전으로 수정 |
| "폴더에 쓰기 권한이 없습니다" | 출력 폴더 권한 | 다른 폴더 선택 또는 권한 변경 |

### Discord 채널 링크 복사 방법

1. Discord 웹 또는 앱에서 원하는 채널을 엽니다.
2. 웹이면 브라우저 주소창 링크를 복사합니다.
3. 앱이면 채널을 오른쪽 클릭한 뒤 `링크 복사`를 누릅니다.

URL 형식: `https://discord.com/channels/서버ID/채널ID`

---

## 명령어로 쓰는 방법

### 채널 하나 저장하기

```bash
# 링크로 저장
discord-downloader export --url "https://discord.com/channels/123456789/987654321" --format html

# 채널 번호로 저장
discord-downloader export --channel-id 987654321 --format txt

# 저장 폴더 정하기
discord-downloader export --channel-id 987654321 --format html --output-dir ./exports

# 날짜 범위 정하기
discord-downloader export --channel-id 987654321 --after "2024-01-01" --before "2024-12-31"

# 사진이나 첨부파일도 함께 받기
discord-downloader export --channel-id 987654321 --format html --media
```

### 서버 전체 저장하기

```bash
# 서버 번호로 저장
discord-downloader exportguild --guild-id 123456789 --format html

# 링크로 저장 (아무 채널 링크면 됨)
discord-downloader exportguild --url "https://discord.com/channels/123456789/987654321"
```

### DM 전체 저장하기

```bash
discord-downloader exportdm --format json
```

### 목록 보기

```bash
# 내가 볼 수 있는 서버 목록
discord-downloader list-guilds

# 서버 안의 채널 목록
discord-downloader list-channels --guild-id 123456789

# DM 채널 목록
discord-downloader list-dm
```

## 저장 형식

| 형식 | 설명 | 파일 확장자 |
|-----|------|-----------|
| `html` | 어두운 화면용 웹페이지 (기본값) | `.html` |
| `html-dark` | 어두운 화면용 웹페이지 | `.html` |
| `html-light` | 밝은 화면용 웹페이지 | `.html` |
| `txt` | 글자만 저장 | `.txt` |
| `json` | JSON 파일 | `.json` |
| `csv` | CSV 형식 | `.csv` |
| `md` / `markdown` | Markdown (Obsidian 호환) | `.md` |
| `obsidian` | `md`와 같음. 옵시디언에 바로 넣기 좋음 | `.md` |

Markdown으로 저장할 때는 내부적으로 JSON으로 한 번 내보낸 뒤,
이미지, 서버/채널 제목, 날짜별 구분, 반응 정보까지 붙여서
옵시디언에서 보기 편한 형태로 바꿔줍니다.

## 명령어 옵션

### export

| 옵션 | 설명 |
|-----|------|
| `--url` | Discord 채널 링크 |
| `-c, --channel-id` | Discord 채널 번호 |
| `-f, --format` | 저장 형식 (기본값: html) |
| `-o, --output-dir` | 저장 폴더 |
| `--after` | 이 날짜 이후만 저장 (YYYY-MM-DD) |
| `--before` | 이 날짜 이전만 저장 (YYYY-MM-DD) |
| `--media` | 사진이나 파일도 함께 받기 |
| `--include-threads` | 스레드 포함 여부 (none/active/all) |

### exportguild

| 옵션 | 설명 |
|-----|------|
| `--url` | Discord 서버 링크 (아무 채널 링크) |
| `-g, --guild-id` | Discord 서버 번호 |
| (export와 같은 옵션) | |

### exportdm

| 옵션 | 설명 |
|-----|------|
| (export와 같은 옵션, 링크/번호 제외) | |

## 설정 파일 위치

- **macOS/Linux**: `~/.discord-downloader/`
- **Windows**: `C:\Users\YourName\.discord-downloader\`

설정 파일:
- `config.json` - JSON 형식 설정
- `.env` - 환경 변수 형식 설정

## 저장되는 파일 이름

기본 파일명 형식: `channel-<채널ID>-<YYYYMMDD-HHMMSS>.<확장자>`

예: `channel-987654321-20240115-143022.html`

## 문제 해결

### macOS에서 "개발자를 확인할 수 없음" 오류

```bash
# DiscordChatExporter.Cli가 있는 디렉터리에서
xattr -d com.apple.quarantine DiscordChatExporter.Cli
```

### DCE 파일을 찾을 수 없을 때

```bash
# DCE 위치 다시 설정
discord-downloader setup --dce-path /path/to/DiscordChatExporter.Cli
```

### 토큰 다시 넣기

```bash
discord-downloader setup
# "토큰을 바꿀까요?" 에서 y 입력
```

## 보안

토큰은 최대한 조심해서 다루도록 만들었습니다:

- **내 컴퓨터에만 저장합니다.** 토큰은 `~/.discord-downloader/{config.json, .env}`에만
  저장되며, 다른 서비스로 따로 보내지지 않습니다.
- **파일 권한도 자동으로 조입니다.** 설정 파일은 저장하자마자
  소유자만 읽고 쓸 수 있게 맞춥니다.
- **오류 기록에도 토큰을 숨깁니다.** 로그나 에러 메시지에 토큰이 그대로 보이지 않게 처리합니다.
- **화면에도 토큰을 다 보여주지 않습니다.** 요약 화면에는 일부만 가려서 보여줍니다.

혹시 토큰이 노출된 것 같다면 Discord 비밀번호를 바꿔 기존 토큰을 막고,
`discord-downloader setup`으로 새 토큰을 넣는 걸 권장합니다.

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
