# ⚾ MLB 한국어 가이드

메이저리그 선수 기록을 한국어로 볼 수 있는 웹사이트입니다.

## 주요 기능

- 🇰🇷 **한국인 선수 전용 섹션** — 이정후, 김하성, 고우석 실시간 기록
- 📊 **리그 선두 기록** — 홈런, 타율, 타점, 탈삼진, ERA, OPS
- ⭐ **주목 선수** — 오타니, 트라웃 등 스타 선수 프로필
- 📖 **야구 용어 사전** — WAR, FIP, 배럴, Statcast 지표 등 한국어 설명
- 🤖 **AI 분석** — DeepSeek V4 Flash (OpenRouter) 기반 선수 분석 및 용어 설명
- 🔍 **선수 검색** — MLB 전 선수 이름 검색

## 시작하기

### 1. 환경 변수 설정

```bash
cp .env.example .env
```

`.env` 파일을 열고 OpenRouter API 키를 입력하세요:
```
OPENROUTER_API_KEY=sk-or-v1-...
```

> OpenRouter API 키는 https://openrouter.ai/keys 에서 무료로 발급받을 수 있습니다.
> AI 분석 기능 없이 기록 조회만 하려면 키 없이도 사용 가능합니다.

### 2. 실행

```bash
# 가상환경 활성화 및 실행
source venv/bin/activate
python app.py
```

또는 직접:
```bash
venv/bin/python3 app.py
```

### 3. 브라우저에서 열기

```
http://localhost:5000
```

## 기술 스택

- **백엔드**: Python Flask
- **데이터**: MLB Stats API + Baseball Savant
- **AI**: OpenRouter — DeepSeek V4 Flash (무료 최고 성능 모델)
- **프론트엔드**: 순수 HTML/CSS/JS (Noto Sans KR 폰트)

## 데이터 출처

- [MLB Stats API](https://statsapi.mlb.com) — 선수 기록, 리그 순위
- [Baseball Savant](https://baseballsavant.mlb.com) — Statcast 고급 지표 (외부 링크)
