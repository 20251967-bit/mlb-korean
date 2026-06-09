import os
import re
import requests
from datetime import datetime, timezone
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY', '')
# 무료 모델 우선순위 (앞의 모델이 rate-limit되면 다음 모델로 자동 전환)
OPENROUTER_MODELS = [
    "openai/gpt-oss-120b:free",
    "openai/gpt-oss-20b:free",
    "deepseek/deepseek-v4-flash:free",
]
MLB_API_BASE = "https://statsapi.mlb.com/api/v1"

def get_current_season():
    """MLB 시즌은 보통 3월 말~10월. 1~2월은 전년도 시즌으로 간주."""
    now = datetime.now(timezone.utc)
    return now.year if now.month >= 3 else now.year - 1

# CURRENT_SEASON은 요청마다 get_current_season()으로 동적 계산

KOREAN_PLAYERS = [
    {
        "id": 808982,
        "name_kr": "이정후",
        "name_en": "Jung Hoo Lee",
        "team_kr": "샌프란시스코 자이언츠",
        "team_en": "San Francisco Giants",
        "position_kr": "외야수",
        "position_type": "batter",
        "number": "51",
        "team_color": "#FD5A1E",
        "team_abbr": "SF",
        "bio_kr": "KBO 역대 최고의 타자 중 한 명으로 평가받으며 2024년 샌프란시스코 자이언츠와 6년 1억 1,300만 달러 계약을 맺고 MLB에 진출했습니다. '타격 머신'이라 불릴 만큼 뛰어난 컨택 능력을 보유하고 있습니다.",
    },
    {
        "id": 673490,
        "name_kr": "김하성",
        "name_en": "Ha-Seong Kim",
        "team_kr": "애틀랜타 브레이브스",
        "team_en": "Atlanta Braves",
        "position_kr": "유격수/2루수",
        "position_type": "batter",
        "number": "7",
        "team_color": "#CE1141",
        "team_abbr": "ATL",
        "bio_kr": "KBO에서 최고의 유격수로 활약했던 김하성은 수준급 수비와 안정적인 타격으로 MLB 무대에 자리잡았습니다. 뛰어난 선구안과 출루율, 다재다능한 수비 능력이 강점입니다.",
    },
    {
        "id": 808975,
        "name_kr": "김혜성",
        "name_en": "Hyeseong Kim",
        "team_kr": "로스앤젤레스 다저스",
        "team_en": "Los Angeles Dodgers",
        "position_kr": "유격수/2루수",
        "position_type": "batter",
        "number": "3",
        "team_color": "#005A9C",
        "team_abbr": "LAD",
        "bio_kr": "KBO 최고의 리드오프 타자로 꼽히던 김혜성은 2025년 LA 다저스와 계약하며 MLB에 입성했습니다. 빠른 발과 뛰어난 선구안, 안정적인 수비가 강점인 테이블세터입니다.",
    },
    {
        "id": 823550,
        "name_kr": "송성문",
        "name_en": "Sung-Mun Song",
        "team_kr": "샌디에이고 파드레스",
        "team_en": "San Diego Padres",
        "position_kr": "2루수/3루수",
        "position_type": "batter",
        "number": "38",
        "team_color": "#2F241D",
        "team_abbr": "SD",
        "bio_kr": "KBO에서 꾸준한 타격과 수비로 주목받은 송성문은 샌디에이고 파드레스 유니폼을 입고 MLB 무대에 도전하고 있습니다. 좌타자로서 컨택 능력이 뛰어납니다.",
    },
    {
        "id": 808970,
        "name_kr": "고우석",
        "name_en": "Woo-Suk Go",
        "team_kr": "톨레도 머드헨스 (AAA)",
        "team_en": "Toledo Mud Hens (DET affiliate)",
        "position_kr": "구원투수",
        "position_type": "pitcher",
        "number": "40",
        "team_color": "#0C2340",
        "team_abbr": "DET",
        "status": "minor",
        "bio_kr": "KBO 최정상급 마무리 투수 출신인 고우석은 현재 디트로이트 산하 AAA 팀(톨레도 머드헨스)에서 MLB 콜업을 준비하고 있습니다.",
    },
    {
        "id": 678225,
        "name_kr": "배지환",
        "name_en": "Ji Hwan Bae",
        "team_kr": "시러큐스 메츠 (AAA)",
        "team_en": "Syracuse Mets (NYM affiliate)",
        "position_kr": "2루수/외야수",
        "position_type": "batter",
        "number": "9",
        "team_color": "#002D72",
        "team_abbr": "NYM",
        "status": "minor",
        "bio_kr": "탁월한 스피드와 출루 능력을 갖춘 배지환은 현재 뉴욕 메츠 산하 AAA 팀(시러큐스 메츠)에서 MLB 복귀를 위해 준비 중입니다.",
    },
]

FEATURED_PLAYERS = [
    {"id": 660271, "name_kr": "쇼헤이 오타니", "name_en": "Shohei Ohtani", "team_kr": "LA 다저스", "position_kr": "지명타자/투수"},
    {"id": 545361, "name_kr": "마이크 트라웃", "name_en": "Mike Trout", "team_kr": "LA 에인절스", "position_kr": "외야수"},
    {"id": 605141, "name_kr": "무키 베츠", "name_en": "Mookie Betts", "team_kr": "LA 다저스", "position_kr": "외야수"},
    {"id": 665742, "name_kr": "후안 소토", "name_en": "Juan Soto", "team_kr": "뉴욕 메츠", "position_kr": "외야수"},
    {"id": 660670, "name_kr": "로널드 아쿠냐 주니어", "name_en": "Ronald Acuña Jr.", "team_kr": "애틀랜타 브레이브스", "position_kr": "외야수"},
    {"id": 683002, "name_kr": "거나 헨더슨", "name_en": "Gunnar Henderson", "team_kr": "볼티모어 오리올스", "position_kr": "유격수"},
]

# 주요 선수 한국어 소개글
PLAYER_BIOS = {
    808975: "KBO 최고의 리드오프 타자 출신으로 LA 다저스에서 활약 중입니다. 빠른 발과 좋은 선구안을 바탕으로 상위 타선에서 출루를 책임집니다.",
    823550: "KBO에서 꾸준한 활약을 보여준 내야수로 샌디에이고 파드레스에서 MLB 커리어를 쌓아가고 있습니다. 좌타 컨택 능력과 다재다능한 수비 포지션이 강점입니다.",
    660271: "투타 겸업으로 야구 역사를 새로 쓴 이도류 스타. 2023년 만장일치 MVP를 수상했으며 10년 7억 달러라는 역대 최고액 계약으로 다저스에 입단했습니다. 한국 팬들에게도 손흥민에 버금가는 인지도를 자랑합니다.",
    545361: "MLB 역사상 최고의 외야수로 평가받는 트라웃은 세 차례 MVP를 수상했습니다. 부상으로 많은 시즌을 잃었지만 건강할 때의 퍼포먼스는 역대급입니다.",
    605141: "수비와 공격 모두 최정상급인 베츠는 2020년 다저스 월드시리즈 우승을 이끌었습니다. 볼링 실력도 프로급이라는 독특한 취미를 가진 올라운더 플레이어입니다.",
    665742: "뛰어난 선구안과 출루 능력으로 '가장 안정적인 타자' 중 한 명으로 꼽힙니다. 2024년 뉴욕 메츠와 15년 7억 6,500만 달러 계약으로 MLB 최고 계약 기록을 경신했습니다.",
    660670: "2023년 만장일치 NL MVP. 40홈런-70도루를 동시에 달성한 유일한 선수로, 폭발적인 스피드와 파워를 겸비한 현 시대 최고의 외야수 중 한 명입니다.",
    683002: "볼티모어의 새로운 간판스타. 2024년 시즌 35홈런을 때려내며 AL 유격수 중 최고의 타격 능력을 선보이고 있습니다. '미래의 MVP 후보'로 일컬어지는 차세대 스타입니다.",
}

KOREAN_PLAYER_IDS = {p["id"] for p in KOREAN_PLAYERS}

GLOSSARY = {
    "타격 기본 용어": [
        {"term": "타율 (AVG, Batting Average)", "short": "안타를 칠 확률", "detail": "안타 수 ÷ 타수. 0.300 이상이면 우수한 타자로 평가합니다."},
        {"term": "출루율 (OBP, On-Base Percentage)", "short": "베이스에 나갈 확률", "detail": "안타·볼넷·몸에 맞는 공 등을 모두 포함해 출루한 비율. 타율보다 타자의 실제 가치를 잘 반영합니다."},
        {"term": "장타율 (SLG, Slugging Percentage)", "short": "타격 파워 지표", "detail": "타수당 평균 획득 루수. 홈런=4루, 3루타=3루, 2루타=2루, 1루타=1루로 계산합니다."},
        {"term": "OPS (출루율+장타율)", "short": "타자 종합 공격력", "detail": "출루율과 장타율을 더한 값. 0.900 이상은 최상급, 0.800 이상은 우수, 0.700 이상은 평균 이상입니다."},
        {"term": "wRC+ (가중 득점 창출)", "short": "리그 보정 타격 지표", "detail": "리그 평균과 구장 특성을 보정한 득점 창출 능력. 100이 평균이며, 150이면 평균보다 50% 뛰어난 타자입니다."},
        {"term": "wOBA (가중 출루율)", "short": "정교한 타자 가치 지표", "detail": "출루 방법(단타·2루타·홈런 등)에 실제 득점 가치를 반영해 계산하는 지표. OPS보다 더 정확합니다."},
        {"term": "BABIP (인플레이 타율)", "short": "운·불운을 보여주는 지표", "detail": "홈런을 제외하고 인플레이된 타구의 안타 비율. 평균은 약 .300이며, 크게 벗어나면 운이 작용한 것으로 봅니다."},
        {"term": "ISO (순수 장타율)", "short": "순수 파워 지표", "detail": "장타율에서 타율을 뺀 값. 2루타 이상만 측정하므로 순수 장타 능력을 보여줍니다."},
        {"term": "BB% (볼넷 비율)", "short": "선구안 지표", "detail": "타석 대비 볼넷 비율. 10% 이상이면 뛰어난 선구안을 가진 타자입니다."},
        {"term": "K% (삼진 비율)", "short": "삼진 당하는 비율", "detail": "타석 대비 삼진 비율. 낮을수록 삼진이 적은 컨택 능력이 좋은 타자입니다."},
    ],
    "투구 기본 용어": [
        {"term": "평균자책점 (ERA, Earned Run Average)", "short": "투수의 가장 기본 지표", "detail": "9이닝당 허용 자책점. 3.00 이하는 우수, 4.00 이하는 평균 이상으로 봅니다."},
        {"term": "FIP (수비 무관 평균자책점)", "short": "투수 자체 능력만 측정", "detail": "삼진·볼넷·홈런만으로 계산해 수비의 영향을 제거한 투수 능력 지표. ERA보다 미래 성적 예측에 정확합니다."},
        {"term": "WHIP (이닝당 출루 허용)", "short": "이닝당 얼마나 내보냈나", "detail": "이닝당 허용 볼넷+피안타 수. 1.00 이하는 최상급, 1.30 이하는 평균 이상입니다."},
        {"term": "K/9 (9이닝당 삼진)", "short": "탈삼진 능력", "detail": "9이닝당 잡아낸 삼진 수. 10 이상이면 탈삼진 능력이 뛰어난 투수입니다."},
        {"term": "BB/9 (9이닝당 볼넷)", "short": "제구력 지표", "detail": "9이닝당 허용 볼넷 수. 낮을수록 제구력이 좋습니다. 3.0 이하는 우수한 수준입니다."},
        {"term": "K/BB (삼진/볼넷 비율)", "short": "종합 투구 능력", "detail": "삼진을 볼넷으로 나눈 값. 높을수록 삼진은 잘 잡고 볼넷은 적게 내주는 완성도 높은 투수입니다."},
        {"term": "WAR (대체 선수 대비 승리 기여)", "short": "선수의 종합 가치", "detail": "평균 대체 선수(마이너리거)와 비교해 몇 승의 가치를 만들어냈는지 나타냅니다. 2.0 이상 평균 주전, 5.0 이상 올스타급, 8.0 이상 MVP급입니다."},
        {"term": "QS (퀄리티 스타트)", "short": "좋은 선발 등판 기준", "detail": "6이닝 이상 투구하며 3자책점 이하를 허용했을 때 기록됩니다. 선발투수의 안정성을 나타냅니다."},
    ],
    "Statcast 첨단 지표": [
        {"term": "엑시트 벨로시티 (Exit Velocity)", "short": "타구 속도", "detail": "타격 직후 공이 배트에서 떠나는 속도(mph). 높을수록 강한 타구. 95mph 이상은 강한 타구(하드힛)입니다."},
        {"term": "발사각도 (Launch Angle)", "short": "타구가 날아가는 각도", "detail": "타구가 지면과 이루는 각도. 10~25도가 라인드라이브/뜬공으로 안타 확률이 높습니다. 25~50도는 홈런 구간입니다."},
        {"term": "배럴 (Barrel)", "short": "최고급 타구", "detail": "엑시트 벨로시티와 발사각도가 모두 최적인 타구. 배럴 타구의 타율은 .700 이상, 장타율은 1.500을 넘습니다."},
        {"term": "배럴% (Barrel Rate)", "short": "배럴 타구 비율", "detail": "전체 타구 중 배럴 타구의 비율. 10% 이상이면 강타자, 15% 이상이면 최상급 파워 타자입니다."},
        {"term": "하드힛% (Hard Hit Rate)", "short": "강한 타구 비율", "detail": "95mph 이상 타구의 비율. 40% 이상이면 타구 질이 우수한 타자입니다."},
        {"term": "xBA (예상 타율)", "short": "운 없애고 계산한 타율", "detail": "타구의 엑시트 벨로시티와 발사각도를 기반으로 계산한 예상 타율. 실제 타율보다 진짜 실력을 반영합니다."},
        {"term": "xSLG (예상 장타율)", "short": "운 없애고 계산한 장타율", "detail": "타구 데이터로 계산한 예상 장타율. 실제와 차이가 크면 운이 개입한 것입니다."},
        {"term": "xERA (예상 평균자책점)", "short": "투수의 진짜 실력", "detail": "타구 질, 삼진, 볼넷을 기반으로 계산한 예상 ERA. FIP보다 더 많은 요소를 반영합니다."},
        {"term": "스프린트 스피드 (Sprint Speed)", "short": "주루 속도", "detail": "최대 주루 속도(피트/초). 27ft/s 이상은 최상급, 23ft/s 이하는 느린 편입니다. 1mph ≈ 1.47ft/s입니다."},
        {"term": "회전수 (Spin Rate, RPM)", "short": "공의 회전 속도", "detail": "투구 시 공이 1분당 회전하는 횟수. 직구는 회전수가 높을수록 뜨는 느낌이 강해 타자를 헛치게 합니다."},
        {"term": "수직 무브먼트 (Vertical Break)", "short": "공의 위아래 움직임", "detail": "중력 대비 공이 얼마나 위아래로 움직이는지. 포심 직구는 양수(뜨는 효과), 싱커는 음수(가라앉는 효과)입니다."},
        {"term": "수평 무브먼트 (Horizontal Break)", "short": "공의 좌우 움직임", "detail": "공이 좌우로 얼마나 움직이는지 나타냅니다. 투심, 커터, 체인지업 등의 구종이 큰 수평 무브먼트를 보입니다."},
    ],
    "야구 상황/전술 용어": [
        {"term": "득점권 (RISP, Runners in Scoring Position)", "short": "2루 또는 3루에 주자가 있는 상황", "detail": "2루 또는 3루에 주자가 있을 때. 이 상황에서의 타율을 RISP 타율이라 합니다."},
        {"term": "클러치 (Clutch)", "short": "중요한 순간의 성적", "detail": "접전 상황이나 득점권에서의 성적. 클러치 능력이 뛰어난 선수는 중요한 순간에 더 잘 합니다."},
        {"term": "플래툰 (Platoon)", "short": "투수 유형에 따른 선수 기용", "detail": "우투수/좌투수 상대에 따라 선수를 바꾸는 전략. 보통 우타자는 좌투수에 강하고 좌타자는 우투수에 강합니다."},
        {"term": "세이브 (SV, Save)", "short": "팀 승리를 지킨 기록", "detail": "3점 이하 리드 상황에서 마지막 이닝을 마무리한 투수에게 주어지는 기록입니다."},
        {"term": "홀드 (HLD, Hold)", "short": "중간계투 성공 기록", "detail": "팀이 리드 중인 상황에서 1이닝 이상을 세이브 조건 충족 없이 마무리한 투수의 기록입니다."},
        {"term": "오프닝 (Opener)", "short": "전략적 1선발 투수", "detail": "본 선발 투수 전에 1~2이닝만 던지는 전략적 투수. 상대 타선의 분석 결과로 활용합니다."},
        {"term": "인플레이 (In Play)", "short": "수비에서 처리해야 하는 타구", "detail": "홈런·삼진·볼넷이 아닌, 수비수가 처리해야 하는 타구입니다."},
        {"term": "웨이버 (Waiver)", "short": "다른 팀 영입 가능 선수 공시", "detail": "팀이 선수를 방출하기 전 다른 30개 팀에게 영입 기회를 주는 절차입니다."},
        {"term": "DH (지명타자, Designated Hitter)", "short": "투수 대신 타격만 하는 선수", "detail": "투수 대신 타격 순서에 들어가는 선수. 수비는 하지 않습니다. 현재 양 리그 모두 DH 제도를 운용합니다."},
    ],
}


def get_savant_url(player_id, name_en):
    slug = name_en.lower()
    slug = re.sub(r"[^a-z0-9 ]", "", slug).replace(" ", "-")
    return f"https://baseballsavant.mlb.com/savant-player/{slug}-{player_id}"


def call_openrouter(system_prompt, user_prompt, max_tokens=600):
    if not OPENROUTER_API_KEY:
        return None, "API 키가 설정되지 않았습니다. .env 파일에 OPENROUTER_API_KEY를 설정해주세요."

    last_error = "알 수 없는 오류"
    for model in OPENROUTER_MODELS:
        try:
            resp = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": os.environ.get("APP_URL", "http://localhost:5001"),
                    "X-Title": "MLB Korean Guide",
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "max_tokens": max_tokens,
                },
                timeout=30,
            )
            if resp.ok:
                content = resp.json()["choices"][0]["message"]["content"]
                if content and content.strip():
                    return content, None
                last_error = f"{model}: 빈 응답"
            else:
                last_error = f"{model}: HTTP {resp.status_code}"
        except Exception as e:
            last_error = str(e)

    return None, f"모든 모델 응답 실패: {last_error}"


@app.route("/")
def index():
    season = get_current_season()
    return render_template("index.html", korean_players=KOREAN_PLAYERS, featured_players=FEATURED_PLAYERS, season=season)


@app.route("/player/<int:player_id>")
def player(player_id):
    korean_info = next((p for p in KOREAN_PLAYERS if p["id"] == player_id), None)
    season = get_current_season()
    return render_template("player.html", player_id=player_id, korean_info=korean_info, season=season)


@app.route("/glossary")
def glossary():
    return render_template("glossary.html", glossary=GLOSSARY)


@app.route("/search")
def search():
    query = request.args.get("q", "")
    return render_template("search.html", query=query)


# --- API 엔드포인트 ---

@app.route("/api/player/<int:player_id>")
def api_player(player_id):
    try:
        info = requests.get(f"{MLB_API_BASE}/people/{player_id}", params={"hydrate": "currentTeam"}, timeout=10)
        hitting = requests.get(
            f"{MLB_API_BASE}/people/{player_id}/stats",
            params={"stats": "season", "season": get_current_season(), "group": "hitting", "sportId": 1},
            timeout=10,
        )
        pitching = requests.get(
            f"{MLB_API_BASE}/people/{player_id}/stats",
            params={"stats": "season", "season": get_current_season(), "group": "pitching", "sportId": 1},
            timeout=10,
        )

        person = info.json().get("people", [{}])[0] if info.ok else {}
        name_en = person.get("fullName", "")

        result = {
            "info": person,
            "hitting": hitting.json().get("stats", []) if hitting.ok else [],
            "pitching": pitching.json().get("stats", []) if pitching.ok else [],
            "korean_info": next((p for p in KOREAN_PLAYERS if p["id"] == player_id), None),
            "bio_kr": PLAYER_BIOS.get(player_id),
            "savant_url": get_savant_url(player_id, name_en) if name_en else None,
        }
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# 한국어 이름 → MLB player ID 매핑
# (한국어 이름, 영문 이름, player_id, 팀, 포지션)
KOREAN_NAME_DB = [
    # ── 한국인 선수 ──
    ("이정후",        "Jung Hoo Lee",           808982, "San Francisco Giants",      "CF"),
    ("김하성",        "Ha-Seong Kim",           673490, "Atlanta Braves",            "SS"),
    ("김혜성",        "Hyeseong Kim",           808975, "Los Angeles Dodgers",       "SS"),
    ("혜성",          "Hyeseong Kim",           808975, "Los Angeles Dodgers",       "SS"),
    ("송성문",        "Sung-Mun Song",          823550, "San Diego Padres",          "2B"),
    ("고우석",        "Woo-Suk Go",             808970, "Toledo Mud Hens",           "RP"),
    ("배지환",        "Ji Hwan Bae",            678225, "Syracuse Mets",             "2B"),
    ("류현진",        "Hyun Jin Ryu",           547943, "",                          "SP"),

    # ── 일본 선수 ──
    ("쇼헤이 오타니", "Shohei Ohtani",          660271, "Los Angeles Dodgers",       "DH"),
    ("오타니",        "Shohei Ohtani",          660271, "Los Angeles Dodgers",       "DH"),
    ("요시다",        "Masataka Yoshida",        680776, "Boston Red Sox",            "LF"),
    ("마사타카 요시다","Masataka Yoshida",       680776, "Boston Red Sox",            "LF"),
    ("무라카미",      "Munetaka Murakami",       807799, "Chicago White Sox",         "1B"),
    ("무네타카 무라카미","Munetaka Murakami",    807799, "Chicago White Sox",         "1B"),
    ("세가",          "Kodai Senga",            673540, "New York Mets",             "SP"),
    ("코다이 세가",   "Kodai Senga",            673540, "New York Mets",             "SP"),
    ("야마모토",      "Yoshinobu Yamamoto",      808967, "Los Angeles Dodgers",       "SP"),
    ("요시노부 야마모토","Yoshinobu Yamamoto",   808967, "Los Angeles Dodgers",       "SP"),
    ("사사키",        "Roki Sasaki",            808963, "Los Angeles Dodgers",       "SP"),
    ("로키 사사키",   "Roki Sasaki",            808963, "Los Angeles Dodgers",       "SP"),

    # ── 외야수 ──
    ("마이크 트라웃", "Mike Trout",             545361, "Los Angeles Angels",        "CF"),
    ("트라웃",        "Mike Trout",             545361, "Los Angeles Angels",        "CF"),
    ("무키 베츠",     "Mookie Betts",           605141, "Los Angeles Dodgers",       "RF"),
    ("베츠",          "Mookie Betts",           605141, "Los Angeles Dodgers",       "RF"),
    ("후안 소토",     "Juan Soto",              665742, "New York Mets",             "RF"),
    ("소토",          "Juan Soto",              665742, "New York Mets",             "RF"),
    ("아론 저지",     "Aaron Judge",            592450, "New York Yankees",          "RF"),
    ("저지",          "Aaron Judge",            592450, "New York Yankees",          "RF"),
    ("로널드 아쿠냐","Ronald Acuña Jr.",        660670, "Atlanta Braves",            "RF"),
    ("아쿠냐",        "Ronald Acuña Jr.",        660670, "Atlanta Braves",            "RF"),
    ("훌리오 로드리게스","Julio Rodríguez",      677594, "Seattle Mariners",          "CF"),
    ("로드리게스",    "Julio Rodríguez",         677594, "Seattle Mariners",          "CF"),
    ("코빈 캐럴",     "Corbin Carroll",         682998, "Arizona Diamondbacks",      "CF"),
    ("캐럴",          "Corbin Carroll",         682998, "Arizona Diamondbacks",      "CF"),
    ("재즈 치솜",   "Jazz Chisholm Jr.",       665862, "New York Yankees",          "CF"),
    ("치솜",        "Jazz Chisholm Jr.",       665862, "New York Yankees",          "CF"),
    ("세드릭 멀린스", "Cedric Mullins",          656775, "Baltimore Orioles",         "CF"),
    ("멀린스",        "Cedric Mullins",          656775, "Baltimore Orioles",         "CF"),
    ("조지 스프링어", "George Springer",         543807, "Toronto Blue Jays",         "CF"),
    ("스프링어",      "George Springer",         543807, "Toronto Blue Jays",         "CF"),
    ("마르셀 오수나", "Marcell Ozuna",           542303, "Atlanta Braves",            "DH"),
    ("오수나",        "Marcell Ozuna",           542303, "Atlanta Braves",            "DH"),
    ("크리스천 옐리치","Christian Yelich",       592885, "Milwaukee Brewers",         "LF"),
    ("옐리치",        "Christian Yelich",        592885, "Milwaukee Brewers",         "LF"),
    ("지안카를로 스탠튼","Giancarlo Stanton",    519317, "New York Yankees",          "DH"),
    ("스탠튼",        "Giancarlo Stanton",       519317, "New York Yankees",          "DH"),
    ("마이클 해리스", "Michael Harris II",       671739, "Atlanta Braves",            "CF"),
    ("해리스",        "Michael Harris II",       671739, "Atlanta Braves",            "CF"),
    ("카일 터커",     "Kyle Tucker",            663527, "Chicago Cubs",              "RF"),
    ("터커",          "Kyle Tucker",            663527, "Chicago Cubs",              "RF"),

    # ── 내야수 ──
    ("거나 헨더슨", "Gunnar Henderson",        683002, "Baltimore Orioles",         "SS"),
    ("헨더슨",        "Gunnar Henderson",        683002, "Baltimore Orioles",         "SS"),
    ("프레디 프리먼", "Freddie Freeman",         518692, "Los Angeles Dodgers",       "1B"),
    ("프리먼",        "Freddie Freeman",         518692, "Los Angeles Dodgers",       "1B"),
    ("블라디미르 게레로","Vladimir Guerrero Jr.", 665489, "Toronto Blue Jays",         "1B"),
    ("게레로",        "Vladimir Guerrero Jr.",   665489, "Toronto Blue Jays",         "1B"),
    ("브라이스 하퍼", "Bryce Harper",            547180, "Philadelphia Phillies",     "1B"),
    ("하퍼",          "Bryce Harper",            547180, "Philadelphia Phillies",     "1B"),
    ("카일 슈워버",   "Kyle Schwarber",          656941, "Philadelphia Phillies",     "LF"),
    ("슈워버",        "Kyle Schwarber",          656941, "Philadelphia Phillies",     "LF"),
    ("트레이 터너",   "Trea Turner",             607208, "Philadelphia Phillies",     "SS"),
    ("요르단 알바레스","Yordan Alvarez",          670541, "Houston Astros",            "DH"),
    ("알바레스",      "Yordan Alvarez",           670541, "Houston Astros",            "DH"),
    ("페르난도 타티스","Fernando Tatis Jr.",      665487, "San Diego Padres",          "SS"),
    ("타티스",        "Fernando Tatis Jr.",       665487, "San Diego Padres",          "SS"),
    ("호세 라미레스", "José Ramírez",             608070, "Cleveland Guardians",       "3B"),
    ("라미레스",      "José Ramírez",             608070, "Cleveland Guardians",       "3B"),
    ("라파엘 데버스", "Rafael Devers",            646240, "Boston Red Sox",            "3B"),
    ("데버스",        "Rafael Devers",            646240, "Boston Red Sox",            "3B"),
    ("바비 위트",     "Bobby Witt Jr.",           677951, "Kansas City Royals",        "SS"),
    ("위트",          "Bobby Witt Jr.",           677951, "Kansas City Royals",        "SS"),
    ("엘리 드 라 크루스","Elly De La Cruz",         682829, "Cincinnati Reds",           "SS"),
    ("드라크루스",    "Elly De La Cruz",          682829, "Cincinnati Reds",           "SS"),
    ("잭슨 홀리데이","Jackson Holliday",          702616, "Baltimore Orioles",         "2B"),
    ("홀리데이",      "Jackson Holliday",         702616, "Baltimore Orioles",         "2B"),
    ("코리 시거",     "Corey Seager",             608369, "Texas Rangers",             "SS"),
    ("시거",          "Corey Seager",             608369, "Texas Rangers",             "SS"),
    ("마커스 세미언", "Marcus Semien",            543760, "Texas Rangers",             "2B"),
    ("세미언",        "Marcus Semien",            543760, "Texas Rangers",             "2B"),
    ("놀란 아레나도", "Nolan Arenado",            571448, "St. Louis Cardinals",       "3B"),
    ("아레나도",      "Nolan Arenado",            571448, "St. Louis Cardinals",       "3B"),
    ("폴 골드슈미트", "Paul Goldschmidt",         502671, "St. Louis Cardinals",       "1B"),
    ("골드슈미트",    "Paul Goldschmidt",         502671, "St. Louis Cardinals",       "1B"),
    ("맷 올슨",       "Matt Olson",               621566, "Atlanta Braves",            "1B"),
    ("올슨",          "Matt Olson",               621566, "Atlanta Braves",            "1B"),
    ("오스틴 라일리", "Austin Riley",             663586, "Atlanta Braves",            "3B"),
    ("오지 알비스",   "Ozzie Albies",             645277, "Atlanta Braves",            "2B"),
    ("알비스",        "Ozzie Albies",             645277, "Atlanta Braves",            "2B"),
    ("댄스비 스완슨", "Dansby Swanson",           621020, "Chicago Cubs",              "SS"),
    ("스완슨",        "Dansby Swanson",           621020, "Chicago Cubs",              "SS"),
    ("피트 알론소",   "Pete Alonso",              624413, "New York Mets",             "1B"),
    ("알론소",        "Pete Alonso",              624413, "New York Mets",             "1B"),
    ("코디 벨린저",   "Cody Bellinger",           641355, "New York Yankees",          "1B"),
    ("벨린저",        "Cody Bellinger",           641355, "New York Yankees",          "1B"),
    ("맥스 먼시",     "Max Muncy",                571970, "Los Angeles Dodgers",       "2B"),
    ("먼시",          "Max Muncy",                571970, "Los Angeles Dodgers",       "2B"),
    ("잔더 보가츠",   "Xander Bogaerts",          593428, "San Diego Padres",          "SS"),
    ("보가츠",        "Xander Bogaerts",          593428, "San Diego Padres",          "SS"),
    ("윌리 아다메스","Willy Adames",              642715, "San Francisco Giants",      "SS"),
    ("아다메스",      "Willy Adames",             642715, "San Francisco Giants",      "SS"),
    ("앤서니 리조",   "Anthony Rizzo",            519203, "New York Yankees",          "1B"),
    ("리조",          "Anthony Rizzo",            519203, "New York Yankees",          "1B"),
    ("DJ 르마이유",   "DJ LeMahieu",              518934, "New York Yankees",          "2B"),
    ("르마이유",      "DJ LeMahieu",              518934, "New York Yankees",          "2B"),
    ("알레한드로 커크","Alejandro Kirk",           672386, "Toronto Blue Jays",         "C"),
    ("커크",          "Alejandro Kirk",           672386, "Toronto Blue Jays",         "C"),
    ("애들리 루치먼", "Adley Rutschman",          668939, "Baltimore Orioles",         "C"),
    ("루치먼",        "Adley Rutschman",          668939, "Baltimore Orioles",         "C"),
    ("가브리엘 모레노","Gabriel Moreno",           672515, "Arizona Diamondbacks",      "C"),
    ("살바도르 페레스","Salvador Perez",           521692, "Kansas City Royals",        "C"),
    ("페레스",        "Salvador Perez",           521692, "Kansas City Royals",        "C"),
    ("윌슨 콘트레라스","Willson Contreras",       575929, "St. Louis Cardinals",       "C"),
    ("션 머피",       "Sean Murphy",              669221, "Atlanta Braves",            "C"),
    ("윌 스미스",     "Will Smith",               669257, "Los Angeles Dodgers",       "C"),

    # ── 투수 ──
    ("스펜서 스트라이더","Spencer Strider",       675911, "Atlanta Braves",            "SP"),
    ("스트라이더",    "Spencer Strider",          675911, "Atlanta Braves",            "SP"),
    ("잭 휠러",       "Zack Wheeler",             554430, "Philadelphia Phillies",     "SP"),
    ("휠러",          "Zack Wheeler",             554430, "Philadelphia Phillies",     "SP"),
    ("게릿 콜",       "Gerrit Cole",              543037, "New York Yankees",          "SP"),
    ("콜",            "Gerrit Cole",              543037, "New York Yankees",          "SP"),
    ("코빈 번스",     "Corbin Burnes",            669203, "Baltimore Orioles",         "SP"),
    ("번스",          "Corbin Burnes",            669203, "Baltimore Orioles",         "SP"),
    ("로건 웹",       "Logan Webb",               657277, "San Francisco Giants",      "SP"),
    ("웹",            "Logan Webb",               657277, "San Francisco Giants",      "SP"),
    ("루이스 카스티요","Luis Castillo",           622491, "Seattle Mariners",          "SP"),
    ("카스티요",      "Luis Castillo",            622491, "Seattle Mariners",          "SP"),
    ("딜런 시즈",     "Dylan Cease",              656302, "San Diego Padres",          "SP"),
    ("시즈",          "Dylan Cease",              656302, "San Diego Padres",          "SP"),
    ("프램버 발데스", "Framber Valdez",           664285, "Houston Astros",            "SP"),
    ("발데스",        "Framber Valdez",           664285, "Houston Astros",            "SP"),
    ("파블로 로페스", "Pablo López",              641154, "Minnesota Twins",           "SP"),
    ("로페스",        "Pablo López",              641154, "Minnesota Twins",           "SP"),
    ("샌디 알칸타라","Sandy Alcantara",           645261, "Miami Marlins",             "SP"),
    ("알칸타라",      "Sandy Alcantara",          645261, "Miami Marlins",             "SP"),
    ("크리스 세일",   "Chris Sale",               519242, "Atlanta Braves",            "SP"),
    ("세일",          "Chris Sale",               519242, "Atlanta Braves",            "SP"),
    ("블레이크 스넬", "Blake Snell",              605483, "San Francisco Giants",      "SP"),
    ("스넬",          "Blake Snell",              605483, "San Francisco Giants",      "SP"),
    ("폴 스키니스",   "Paul Skenes",              694973, "Pittsburgh Pirates",        "SP"),
    ("스키니스",      "Paul Skenes",              694973, "Pittsburgh Pirates",        "SP"),
    ("클레이튼 커쇼", "Clayton Kershaw",          477132, "Los Angeles Dodgers",       "SP"),
    ("커쇼",          "Clayton Kershaw",          477132, "Los Angeles Dodgers",       "SP"),
    ("맥스 슈어저",   "Max Scherzer",             453286, "Texas Rangers",             "SP"),
    ("슈어저",        "Max Scherzer",             453286, "Texas Rangers",             "SP"),
    ("칼 라일리",     "Cal Raleigh",              663728, "Seattle Mariners",          "C"),
    ("라일리",        "Cal Raleigh",              663728, "Seattle Mariners",          "C"),
]

def is_korean(text):
    return any('가' <= c <= '힣' or 'ㄱ' <= c <= 'ㅎ' for c in text)

def search_korean_db(query):
    """한국어 이름으로 로컬 DB 검색 (부분 일치)"""
    results = []
    seen_ids = set()
    for name_kr, name_en, pid, team, pos in KOREAN_NAME_DB:
        if query in name_kr and pid not in seen_ids:
            seen_ids.add(pid)
            results.append({
                "id": pid,
                "fullName": name_en,
                "fullNameKr": name_kr,
                "currentTeam": {"name": team},
                "primaryPosition": {"name": pos, "abbreviation": pos},
            })
    return results

def fetch_player_info(player_id):
    """MLB API에서 선수 상세 정보 조회"""
    try:
        resp = requests.get(
            f"{MLB_API_BASE}/people/{player_id}",
            params={"hydrate": "currentTeam"},
            timeout=8,
        )
        if resp.ok:
            people = resp.json().get("people", [])
            return people[0] if people else None
    except Exception:
        pass
    return None

@app.route("/api/search")
def api_search():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"people": []})

    # 한국어 입력 감지
    if is_korean(query):
        local = search_korean_db(query)
        if not local:
            return jsonify({"people": []})
        # MLB API로 실시간 팀·포지션 보완, 한국어 이름 보존 (최대 6명)
        enriched = []
        for p in local[:6]:
            info = fetch_player_info(p["id"])
            if info:
                info["fullNameKr"] = p["fullNameKr"]   # 한국어 이름 유지
                enriched.append(info)
            else:
                enriched.append(p)
        return jsonify({"people": enriched})

    # 영문 검색 — 기존 MLB Stats API 사용
    try:
        resp = requests.get(
            f"{MLB_API_BASE}/people/search",
            params={"names": query, "sportIds": 1},
            timeout=10,
        )
        return jsonify(resp.json() if resp.ok else {"people": []})
    except Exception:
        return jsonify({"people": []})


# 타격 통계는 hitting group, 투구 통계는 pitching group으로 분기
HITTING_CATS = {
    "battingAverage": "avg",
    "homeRuns": "homeRuns",
    "rbi": "rbi",
    "onBasePlusSlugging": "ops",
    "hits": "hits",
    "stolenBases": "stolenBases",
}
PITCHING_CATS = {
    "strikeOuts": "strikeOuts",
    "era": "era",
    "wins": "wins",
    "whip": "whip",
    "saves": "saves",
}

@app.route("/api/leaders")
def api_leaders():
    category = request.args.get("category", "homeRuns")
    limit = int(request.args.get("limit", 10))
    season = get_current_season()

    try:
        if category in HITTING_CATS:
            sort_stat = HITTING_CATS[category]
            resp = requests.get(
                f"{MLB_API_BASE}/stats",
                params={
                    "stats": "season",
                    "season": season,
                    "group": "hitting",
                    "sortStat": sort_stat,
                    "order": "desc",
                    "limit": limit,
                    "sportId": 1,
                    "playerPool": "Qualified",
                    "hydrate": "person,currentTeam",
                },
                timeout=10,
            )
            if resp.ok:
                splits = resp.json().get("stats", [{}])[0].get("splits", [])
                leaders = [
                    {
                        "rank": i + 1,
                        "person": s.get("player", {}),
                        "team": s.get("team", {}),
                        "value": s["stat"].get(sort_stat, "-"),
                    }
                    for i, s in enumerate(splits)
                ]
                return jsonify({"leagueLeaders": [{"leaders": leaders}]})

        else:
            # 투구 통계 — 기존 leaders 엔드포인트 사용
            resp = requests.get(
                f"{MLB_API_BASE}/stats/leaders",
                params={
                    "leaderCategories": category,
                    "season": season,
                    "sportId": 1,
                    "limit": limit,
                    "hydrate": "person,team",
                },
                timeout=10,
            )
            if resp.ok:
                return jsonify(resp.json())

        return jsonify({})
    except Exception:
        return jsonify({})


# 주요 수상 ID → (한국어 이름, 이모지, 중요도)
AWARD_MAP = {
    # MVP / 최우수
    "ALMVP":      ("AL MVP",              "🏆", 1),
    "NLMVP":      ("NL MVP",              "🏆", 1),
    # 사이영
    "ALCY":       ("AL 사이영상",          "🏆", 1),
    "NLCY":       ("NL 사이영상",          "🏆", 1),
    # 신인왕
    "ALROY":      ("AL 신인왕",            "🌟", 1),
    "NLROY":      ("NL 신인왕",            "🌟", 1),
    # 골드글러브
    "ALGG":       ("AL 골드글러브",        "🥇", 2),
    "NLGG":       ("NL 골드글러브",        "🥇", 2),
    # 실버슬러거
    "ALSS":       ("AL 실버슬러거",        "🥈", 2),
    "NLSS":       ("NL 실버슬러거",        "🥈", 2),
    # 포스트시즌 MVP
    "WSMVP":      ("월드시리즈 MVP",       "🏆", 1),
    "NLCSMVP":    ("NLCS MVP",            "🌟", 2),
    "ALCSMVP":    ("ALCS MVP",            "🌟", 2),
    "WSBATTER":   ("WS 최우수 타자",       "⭐", 2),
    "WSPITCHER":  ("WS 최우수 투수",       "⭐", 2),
    # 행크 애런상 (리그 최고 타자)
    "ALHAA":      ("AL 행크 애런상",       "⭐", 2),
    "NLHAA":      ("NL 행크 애런상",       "⭐", 2),
    # 월드시리즈 우승
    "WSCHAMP":    ("월드시리즈 우승",      "💍", 1),
    # 올스타
    "ALAS":       ("AL 올스타",            "⭐", 3),
    "NLAS":       ("NL 올스타",            "⭐", 3),
    # All-MLB
    "MLBAFIRST":  ("All-MLB 1팀",          "🌟", 2),
    "MLBSECOND":  ("All-MLB 2팀",          "⭐", 3),
    # 컴백
    "ALCOM":      ("AL 컴백 플레이어상",   "💪", 2),
    "NLCOM":      ("NL 컴백 플레이어상",   "💪", 2),
    # DH상
    "DHOY":       ("에드가 마르티네스상",  "🏅", 3),
    # 로베르토 클레멘테
    "MLBRC":      ("로베르토 클레멘테상",  "❤️", 2),
    # 수비상
    "WDPOY":      ("윌슨 수비상",          "🧤", 2),
    "WMLBDPOY":   ("윌슨 MLB 수비왕",     "🧤", 2),
    # WBC
    "WBCMVP":     ("WBC MVP",             "🌏", 2),
    # 선수 투표
    "MLBPCALOP":  ("선수 투표 AL 최우수",  "👥", 3),
    "MLBPCNLOP":  ("선수 투표 NL 최우수",  "👥", 3),
    "MLBPCPOY":   ("선수 투표 올해의 선수","👥", 2),
}

@app.route("/api/player/<int:player_id>/awards")
def api_player_awards(player_id):
    try:
        resp = requests.get(f"{MLB_API_BASE}/people/{player_id}/awards", timeout=10)
        if not resp.ok:
            return jsonify({"awards": []})

        raw = resp.json().get("awards", [])
        result = []
        seen = set()

        for a in raw:
            aid = a.get("id", "")
            season = a.get("season", "")
            if aid not in AWARD_MAP:
                continue
            key = (aid, season)
            if key in seen:
                continue
            seen.add(key)

            kr_name, emoji, tier = AWARD_MAP[aid]
            result.append({
                "id": aid,
                "season": season,
                "name_kr": kr_name,
                "name_en": a.get("name", ""),
                "emoji": emoji,
                "tier": tier,
            })

        # 중요도순 → 연도 내림차순 정렬
        result.sort(key=lambda x: (x["tier"], -int(x["season"] or 0)))
        return jsonify({"awards": result})
    except Exception as e:
        return jsonify({"awards": [], "error": str(e)})


@app.route("/api/standings")
def api_standings():
    season = get_current_season()
    try:
        resp = requests.get(
            f"{MLB_API_BASE}/standings",
            params={
                "leagueId": "103,104",
                "season": season,
                "standingsTypes": "regularSeason",
                "hydrate": "team,division,league,record",
            },
            timeout=10,
        )
        return jsonify(resp.json() if resp.ok else {})
    except Exception:
        return jsonify({})


@app.route("/api/explain", methods=["POST"])
def api_explain():
    data = request.json or {}
    term = data.get("term", "").strip()
    if not term:
        return jsonify({"error": "용어를 입력해주세요"}), 400

    system = "당신은 MLB 야구 전문 해설가입니다. 야구를 처음 접하는 한국인도 쉽게 이해할 수 있도록 친절하고 간결하게 설명합니다."
    prompt = f"""야구 용어 "{term}"을 한국어로 쉽게 설명해주세요.

다음 구조로 답해주세요:
📌 **기본 설명** (2~3문장으로 쉽게)
📊 **왜 중요한가?** (팬 입장에서 이 수치를 어떻게 해석하면 되는지)
⭐ **실제 예시** (유명 선수나 구체적인 상황을 들어서)

단, 전문 용어는 최대한 피하고 일상적인 한국어로 설명해주세요."""

    content, error = call_openrouter(system, prompt, max_tokens=500)
    if error:
        return jsonify({"error": error}), 500
    return jsonify({"explanation": content})


@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    data = request.json or {}
    name = data.get("name", "")
    stats = data.get("stats", {})

    system = "당신은 MLB 야구 분석 전문가입니다. 한국 팬들에게 쉽고 흥미롭게 선수 분석을 제공합니다."
    prompt = f"""{name} 선수의 {get_current_season()}시즌 기록을 분석해주세요.

기록 데이터:
{stats}

다음을 포함해서 한국어로 200자 내외로 분석해주세요:
- 이번 시즌 전반적인 평가 (좋은지/아쉬운지)
- 가장 두드러지는 강점 또는 약점
- 한국 팬들에게 전하는 한마디

쉽고 흥미롭게 작성해주세요."""

    content, error = call_openrouter(system, prompt, max_tokens=300)
    if error:
        return jsonify({"error": error}), 500
    return jsonify({"analysis": content})


@app.route("/api/bio", methods=["POST"])
def api_bio():
    """선수 소개글 AI 자동 생성"""
    data = request.json or {}
    name_en = data.get("name_en", "")
    name_kr = data.get("name_kr", "")
    team = data.get("team", "")
    position = data.get("position", "")
    stats = data.get("stats", {})

    display_name = name_kr or name_en
    system = "당신은 MLB 야구 전문 해설가입니다. 한국 팬들을 위해 선수를 간결하고 흥미롭게 소개합니다."
    prompt = f"""MLB 선수 {display_name}({name_en})을 한국 팬들에게 소개하는 글을 2~3문장으로 써주세요.
팀: {team}, 포지션: {position}
{f'2026시즌 주요 기록: {stats}' if stats else ''}

조건:
- 이 선수의 대표적인 특징이나 강점 위주로 작성
- 야구를 잘 모르는 한국인도 이해할 수 있는 표현 사용
- 존댓말 사용
- 2~3문장으로 짧고 임팩트 있게"""

    content, error = call_openrouter(system, prompt, max_tokens=200)
    if error:
        return jsonify({"error": error}), 500
    return jsonify({"bio": content})


TEAM_KR = {
    "Angels": "에인절스", "Astros": "애스트로스", "Athletics": "애슬레틱스",
    "Blue Jays": "블루제이스", "Braves": "브레이브스", "Brewers": "브루어스",
    "Cardinals": "카디널스", "Cubs": "컵스", "Diamondbacks": "다이아몬드백스",
    "Dodgers": "다저스", "Giants": "자이언츠", "Guardians": "가디언스",
    "Mariners": "매리너스", "Marlins": "말린스", "Mets": "메츠",
    "Nationals": "내셔널스", "Orioles": "오리올스", "Padres": "파드레스",
    "Phillies": "필리스", "Pirates": "파이리츠", "Rangers": "레인저스",
    "Rays": "레이스", "Red Sox": "레드삭스", "Reds": "레즈",
    "Rockies": "로키스", "Royals": "로열스", "Tigers": "타이거스",
    "Twins": "트윈스", "White Sox": "화이트삭스", "Yankees": "양키스",
}

CITY_KR = {
    "Arizona": "애리조나", "Atlanta": "애틀랜타", "Baltimore": "볼티모어",
    "Boston": "보스턴", "Chicago": "시카고", "Cincinnati": "신시내티",
    "Cleveland": "클리블랜드", "Colorado": "콜로라도", "Detroit": "디트로이트",
    "Houston": "휴스턴", "Kansas City": "캔자스시티", "Los Angeles": "로스앤젤레스",
    "Miami": "마이애미", "Milwaukee": "밀워키", "Minnesota": "미네소타",
    "New York": "뉴욕", "Oakland": "오클랜드", "Philadelphia": "필라델피아",
    "Pittsburgh": "피츠버그", "San Diego": "샌디에이고", "San Francisco": "샌프란시스코",
    "Seattle": "시애틀", "St. Louis": "세인트루이스", "Tampa Bay": "탬파베이",
    "Texas": "텍사스", "Toronto": "토론토", "Washington": "워싱턴",
    "Sacramento": "새크라멘토", "Las Vegas": "라스베이거스",
}

STATUS_KR = {
    "Final": "종료", "Final: Tied": "종료(연장)", "Game Over": "종료",
    "Scheduled": "예정", "Pre-Game": "경기 전", "Warmup": "워밍업",
    "In Progress": "진행 중", "Delayed": "지연", "Suspended": "중단",
    "Postponed": "연기", "Cancelled": "취소",
}

def team_name_kr(full_name):
    for en, kr in TEAM_KR.items():
        if en in full_name:
            for city_en, city_kr in CITY_KR.items():
                if full_name.startswith(city_en):
                    return f"{city_kr} {kr}"
            return kr
    return full_name

@app.route("/api/schedule")
def api_schedule():
    date_str = request.args.get("date", "")
    if not date_str:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        resp = requests.get(
            f"{MLB_API_BASE}/schedule",
            params={
                "sportId": 1,
                "date": date_str,
                "hydrate": "teams,linescore,decisions,probablePitcher",
            },
            timeout=10,
        )
        if not resp.ok:
            return jsonify({"games": []})

        raw_games = resp.json().get("dates", [{}])[0].get("games", []) if resp.json().get("dates") else []
        games = []
        for g in raw_games:
            home = g["teams"]["home"]
            away = g["teams"]["away"]
            status_raw = g["status"]["detailedState"]
            status_code = g["status"]["codedGameState"]  # S=예정, I=진행중, F=종료

            # 이닝별 점수
            innings = []
            ls = g.get("linescore", {})
            for inn in ls.get("innings", []):
                innings.append({
                    "num": inn.get("num"),
                    "away": inn.get("away", {}).get("runs", "-"),
                    "home": inn.get("home", {}).get("runs", "-"),
                })

            # 투수 결정
            decisions = g.get("decisions", {})

            # 한국 선수 출전 여부 체크
            kr_ids = {p["id"] for p in KOREAN_PLAYERS}
            home_team_id = home["team"]["id"]
            away_team_id = away["team"]["id"]

            home_name = home["team"]["name"]
            away_name = away["team"]["name"]

            games.append({
                "gamePk": g["gamePk"],
                "gameDate": g.get("gameDate", ""),
                "status": STATUS_KR.get(status_raw, status_raw),
                "statusCode": status_code,
                "away": {
                    "id": away_team_id,
                    "name": away_name,
                    "nameKr": team_name_kr(away_name),
                    "score": away.get("score"),
                    "isWinner": away.get("isWinner", False),
                    "probablePitcher": away.get("probablePitcher", {}).get("fullName", ""),
                },
                "home": {
                    "id": home_team_id,
                    "name": home_name,
                    "nameKr": team_name_kr(home_name),
                    "score": home.get("score"),
                    "isWinner": home.get("isWinner", False),
                    "probablePitcher": home.get("probablePitcher", {}).get("fullName", ""),
                },
                "innings": innings,
                "linescore": {
                    "inning": ls.get("currentInning"),
                    "inningHalf": ls.get("inningHalf", ""),
                    "away": {"hits": ls.get("teams", {}).get("away", {}).get("hits", "-"),
                             "errors": ls.get("teams", {}).get("away", {}).get("errors", "-")},
                    "home": {"hits": ls.get("teams", {}).get("home", {}).get("hits", "-"),
                             "errors": ls.get("teams", {}).get("home", {}).get("errors", "-")},
                },
                "decisions": {
                    "winner": decisions.get("winner", {}).get("fullName", ""),
                    "loser": decisions.get("loser", {}).get("fullName", ""),
                    "save": decisions.get("save", {}).get("fullName", ""),
                },
            })

        return jsonify({"games": games, "date": date_str})
    except Exception as e:
        return jsonify({"games": [], "error": str(e)})


@app.route("/games")
def games_page():
    return render_template("games.html", season=get_current_season())


if __name__ == "__main__":
    app.run(debug=True, port=5001)
