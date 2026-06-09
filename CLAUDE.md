# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# 가상환경 활성화 및 실행
source venv/bin/activate && python app.py

# 의존성 설치
pip install -r requirements.txt
```

앱은 **포트 5001**에서 실행됩니다 (macOS Control Center가 5000번 점유). 접속: http://localhost:5001

환경 변수 설정:
```bash
cp .env.example .env
# .env에 OPENROUTER_API_KEY 입력 (없어도 AI 기능 제외 정상 동작)
```

### macOS 자동 시작 (launchd)

`~/Library/LaunchAgents/com.mlb-korean.plist`로 등록되어 있어 로그인 시 자동 실행됨. 로그: `server.log`

```bash
# 서비스 중지
launchctl unload ~/Library/LaunchAgents/com.mlb-korean.plist
# 서비스 재시작
launchctl unload ~/Library/LaunchAgents/com.mlb-korean.plist && launchctl load ~/Library/LaunchAgents/com.mlb-korean.plist
```

## Architecture

단일 파일 Flask 앱 (`app.py`) + Jinja2 템플릿 구조. 별도 DB 없음.

### 데이터 흐름

- **한국인 선수 목록**: `KOREAN_PLAYERS` 리스트 (app.py 하드코딩) → `/` 홈, `/player/<id>` 상세
- **MLB 실시간 데이터**: `MLB_API_BASE = "https://statsapi.mlb.com/api/v1"` 호출 → 타격/투구 스탯, 리그 순위, 경기 일정
- **선수 검색**: 한국어 입력 시 `KOREAN_NAME_DB` 로컬 DB 부분 일치 → MLB API로 팀/포지션 보완. 영문 입력 시 MLB Stats API `/people/search` 직접 호출
- **AI 분석**: OpenRouter API (`call_openrouter()`) — 모델 rate-limit 시 `OPENROUTER_MODELS` 리스트 순서대로 자동 폴백

### API 엔드포인트

| 엔드포인트 | 설명 |
|---|---|
| `GET /api/player/<id>` | 선수 정보 + 시즌 타격/투구 스탯 |
| `GET /api/player/<id>/awards` | 수상 이력 (AWARD_MAP으로 한국어 변환) |
| `GET /api/leaders?category=homeRuns` | 리그 순위 (타격: stats API, 투구: leaders API) |
| `GET /api/search?q=이정후` | 선수 검색 |
| `GET /api/schedule?date=2026-05-25` | 경기 일정/결과 |
| `GET /api/standings` | 팀 순위 |
| `POST /api/explain` | 용어 AI 설명 |
| `POST /api/analyze` | 선수 스탯 AI 분석 |
| `POST /api/bio` | 선수 소개글 AI 생성 |

### 페이지 라우팅

| URL | 템플릿 | 설명 |
|---|---|---|
| `/` | `index.html` | 홈 — 한국인 선수 카드 + 주목 선수 |
| `/player/<id>` | `player.html` | 선수 상세 (스탯·수상·AI 분석) |
| `/glossary` | `glossary.html` | 야구 용어 사전 |
| `/search` | `search.html` | 선수 검색 결과 |
| `/games` | `games.html` | 경기 일정/결과 |

### 프론트엔드

- 순수 HTML/CSS/JS (프레임워크 없음)
- `templates/base.html`이 공통 레이아웃 (네비, 푸터, `static/js/main.js` 로드)
- `static/js/main.js`에 공통 검색 드롭다운 로직, 각 페이지별 JS는 해당 템플릿 내 `<script>` 블록에 인라인
- `KOREAN_PLAYERS`(한국인)와 `FEATURED_PLAYERS`(오타니 등 비한국인 스타)는 별도 리스트로 홈에서 각각 렌더링

### 주요 데이터 구조 (app.py)

- `KOREAN_PLAYERS`: 한국인 선수 메타 (id, 한국어 이름/팀/포지션, 팀 색상, `status: "minor"` 여부)
- `KOREAN_NAME_DB`: 검색용 (한국어 이름, 영문 이름, player_id, 팀, 포지션) 튜플 리스트 — 동의어/단축명 포함
- `GLOSSARY`: 카테고리별 야구 용어 사전 (한국어 설명 포함)
- `AWARD_MAP`: MLB 수상 ID → (한국어 이름, 이모지, 중요도 tier)
- `TEAM_KR` / `CITY_KR`: 팀/도시 영문→한국어 변환 매핑
- `get_current_season()`: 1~2월은 전년도 시즌으로 간주

### 한국인 선수 추가 방법

1. `KOREAN_PLAYERS`에 선수 딕셔너리 추가 (MLB player ID 필수)
2. `KOREAN_NAME_DB`에 한국어 이름·동의어 튜플 추가
3. 필요시 `PLAYER_BIOS`에 한국어 소개글 추가
