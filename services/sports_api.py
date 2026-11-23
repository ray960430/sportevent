"""Sports data clients with process-local TTL caching and friendly fallbacks."""
from datetime import datetime, timezone, timedelta
from functools import wraps
import json
import os
from pathlib import Path
import time
from typing import Any

import requests

ROOT = Path(__file__).resolve().parent.parent
TTL_SECONDS = 900
_CACHE: dict[str, tuple[float, Any]] = {}
_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": "TaiwanSportsHub/1.0", "Accept": "application/json"})

SPORTS_TRANSLATIONS = {
    "Basketball": "籃球", "Soccer": "足球", "Baseball": "棒球", "Tennis": "網球",
    "Motorsport": "賽車", "American Football": "美式足球", "Ice Hockey": "冰上曲棍球",
    "Cricket": "板球", "Golf": "高爾夫球", "Rugby": "橄欖球", "Volleyball": "排球",
    "Badminton": "羽球", "Boxing": "拳擊", "Cycling": "自由車", "Swimming": "游泳",
    "Formula 1": "一級方程式賽車", "Wrestling": "角力", "MMA": "綜合格鬥",
}

FALLBACK_SPORTS = [
    {"strSport": "Basketball", "strSportThumb": "https://www.thesportsdb.com/images/sports/basketball.jpg", "strSportIcon": "🏀", "strFormat": "室內球類", "strDescription": "兩隊在球場上以傳球、運球與投籃得分，講求團隊合作與攻守轉換。"},
    {"strSport": "Soccer", "strSportThumb": "https://www.thesportsdb.com/images/sports/soccer.jpg", "strSportIcon": "⚽", "strFormat": "戶外球類", "strDescription": "兩隊以腳控球並嘗試將球送入對方球門，是全球熱門的團隊運動。"},
    {"strSport": "Baseball", "strSportThumb": "https://www.thesportsdb.com/images/sports/baseball.jpg", "strSportIcon": "⚾", "strFormat": "棒球", "strDescription": "攻守輪替的球類運動，投打對決與守備策略是比賽看點。"},
    {"strSport": "Tennis", "strSportThumb": "https://www.thesportsdb.com/images/sports/tennis.jpg", "strSportIcon": "🎾", "strFormat": "拍類運動", "strDescription": "選手以球拍隔網擊球，透過落點、旋轉與耐力爭取分數。"},
    {"strSport": "Motorsport", "strSportThumb": "https://www.thesportsdb.com/images/sports/motorsport.jpg", "strSportIcon": "🏎️", "strFormat": "賽車", "strDescription": "車手在封閉賽道競速，策略、輪胎管理與進站都會左右名次。"},
    {"strSport": "Badminton", "strSportThumb": "https://www.thesportsdb.com/images/sports/badminton.jpg", "strSportIcon": "🏸", "strFormat": "拍類運動", "strDescription": "以球拍擊打羽球越網，反應、步法與變化球是比賽關鍵。"},
]

FALLBACK_TEAMS = [
    {"full_name": "Boston Celtics", "city": "Boston", "name": "Celtics", "conference": "East", "division": "Atlantic"},
    {"full_name": "Los Angeles Lakers", "city": "Los Angeles", "name": "Lakers", "conference": "West", "division": "Pacific"},
    {"full_name": "Golden State Warriors", "city": "San Francisco", "name": "Warriors", "conference": "West", "division": "Pacific"},
    {"full_name": "Chicago Bulls", "city": "Chicago", "name": "Bulls", "conference": "East", "division": "Central"},
]
FALLBACK_PLAYERS = [
    {"first_name": "Stephen", "last_name": "Curry", "position": "後衛", "height_feet": 6, "height_inches": 2, "weight_pounds": "185", "team": {"full_name": "Golden State Warriors", "conference": "West"}},
    {"first_name": "LeBron", "last_name": "James", "position": "前鋒", "height_feet": 6, "height_inches": 9, "weight_pounds": "250", "team": {"full_name": "Los Angeles Lakers", "conference": "West"}},
    {"first_name": "Jayson", "last_name": "Tatum", "position": "前鋒", "height_feet": 6, "height_inches": 8, "weight_pounds": "210", "team": {"full_name": "Boston Celtics", "conference": "East"}},
    {"first_name": "Luka", "last_name": "Doncic", "position": "後衛", "height_feet": 6, "height_inches": 7, "weight_pounds": "230", "team": {"full_name": "Los Angeles Lakers", "conference": "West"}},
]


def _get_json(url: str, *, params: dict | None = None, headers: dict | None = None) -> dict:
    response = _SESSION.get(url, params=params, headers=headers, timeout=8)
    response.raise_for_status()
    return response.json()


def _cached(key: str, loader):
    now = time.monotonic()
    entry = _CACHE.get(key)
    if entry and entry[0] > now:
        return entry[1], True
    value = loader()
    _CACHE[key] = (now + TTL_SECONDS, value)
    return value, False


def _local_fallback(loader, fallback):
    try:
        return _cached(loader.__name__, loader)[0], False
    except (requests.RequestException, ValueError, KeyError, TypeError):
        return fallback, True


def format_taiwan_time(value: str | None) -> str:
    if not value:
        return "時間待公布"
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        tw = parsed.astimezone(timezone(timedelta(hours=8)))
        return tw.strftime("%Y/%m/%d %H:%M (台灣時間)")
    except (ValueError, TypeError):
        return "時間待公布"


def _load_f1_schedule():
    data = _get_json("https://api.jolpi.ca/ergast/f1/current.json")
    races = data["MRData"]["RaceTable"]["Races"]
    result = []
    for race in races:
        date, clock = race.get("date", ""), race.get("time", "00:00:00Z")
        result.append({"round": race.get("round", "—"), "name": race.get("raceName", "賽事名稱待公布"),
                       "circuit": race.get("Circuit", {}).get("circuitName", "賽道待公布"),
                       "location": ", ".join(filter(None, [race.get("Circuit", {}).get("Location", {}).get("locality"), race.get("Circuit", {}).get("Location", {}).get("country")])),
                       "time_tw": format_taiwan_time(f"{date}T{clock}"), "url": race.get("url", "")})
    return result


def get_f1_schedule(with_notice=False):
    try:
        rows, cached = _cached("f1_schedule", _load_f1_schedule)
        notice = "賽程資料來自 Jolpica F1，顯示台灣時間。" + ("（使用 15 分鐘快取）" if cached else "")
    except (requests.RequestException, ValueError, KeyError, TypeError):
        rows, notice = [], "目前無法連線取得 F1 最新賽程，請稍後再試。"
    return (rows, notice) if with_notice else rows


def _load_f1_drivers():
    data = _get_json("https://api.jolpi.ca/ergast/f1/current/drivers.json")
    return [{"name": f"{d.get('givenName','')} {d.get('familyName','')}".strip(), "nationality": d.get("nationality", "—"),
             "number": d.get("permanentNumber", "—"), "code": d.get("code", "—"), "team": "F1 車手", "url": d.get("url", "")} for d in data["MRData"]["DriverTable"]["Drivers"]]


def get_f1_drivers(with_notice=False):
    try:
        rows, cached = _cached("f1_drivers", _load_f1_drivers)
        notice = "車手名單來自 Jolpica F1。" + ("（使用 15 分鐘快取）" if cached else "")
    except (requests.RequestException, ValueError, KeyError, TypeError):
        rows, notice = [], "目前無法連線取得 F1 車手名單，請稍後再試。"
    return (rows, notice) if with_notice else rows


def _load_sports():
    data = _get_json("https://www.thesportsdb.com/api/v1/json/123/all_sports.php")
    return data.get("sports") or FALLBACK_SPORTS


def get_sports(with_notice=False):
    try:
        rows, cached = _cached("sports", _load_sports)
        notice = "運動百科資料來自 TheSportsDB。" + ("（使用 15 分鐘快取）" if cached else "")
    except (requests.RequestException, ValueError, KeyError, TypeError):
        rows, notice = FALLBACK_SPORTS, "目前顯示精選運動百科範例，外部資料服務暫時無法連線。"
    normalized = []
    for item in rows:
        row = dict(item)
        row["name_zh"] = SPORTS_TRANSLATIONS.get(row.get("strSport", ""), row.get("strSport", "其他運動"))
        row["image"] = (row.get("strSportThumb") or row.get("strSportIcon") or "")
        if row["image"] and not row["image"].startswith("data:"):
            row["image"] = row["image"].rstrip("/") + "/medium"
        row["summary"] = row.get("strDescription") or f"認識{row['name_zh']}的賽事規則、訓練方式與精彩看點。"
        row["icon"] = row.get("strSportIcon") or "🏅"
        normalized.append(row)
    return (normalized, notice) if with_notice else normalized


def _nba_request(path, params=None):
    key = os.environ.get("BALLDONTLIE_API_KEY", "").strip()
    if not key:
        raise RuntimeError("未設定 API 金鑰")
    data = _get_json(f"https://api.balldontlie.io/v1/{path}", params=params, headers={"Authorization": key})
    return data.get("data", [])


def get_nba_teams():
    if not os.environ.get("BALLDONTLIE_API_KEY", "").strip():
        rows = FALLBACK_TEAMS
    else:
        try:
            rows, _ = _cached("nba_teams", lambda: _nba_request("teams"))
        except (requests.RequestException, ValueError, KeyError, TypeError, RuntimeError):
            rows = FALLBACK_TEAMS
            _CACHE["nba_teams"] = (time.monotonic() + TTL_SECONDS, rows)
    return [{**team, "conference_zh": {"East": "東區", "West": "西區"}.get(team.get("conference"), team.get("conference", "—"))} for team in rows]


def _load_nba_players(query):
    params = {"per_page": 100}
    if query:
        params["search"] = query
    return _nba_request("players", params)


def get_nba_players(query="", with_notice=False):
    key = os.environ.get("BALLDONTLIE_API_KEY", "").strip()
    fallback = [dict(p) for p in FALLBACK_PLAYERS if not query or query.casefold() in f"{p['first_name']} {p['last_name']}".casefold()]
    if not key:
        rows, notice = fallback, "尚未設定 NBA API 金鑰，目前顯示精選球星範例資料。"
    else:
        try:
            rows, cached = _cached(f"nba_players:{query.casefold()}", lambda: _load_nba_players(query))
            notice = "球員資料來自 BALLDONTLIE NBA API。" + ("（使用 15 分鐘快取）" if cached else "")
        except (requests.RequestException, ValueError, KeyError, TypeError, RuntimeError) as exc:
            rows = fallback
            # Cache the fallback too, so repeated page views do not hammer a rate-limited API.
            _CACHE[f"nba_players:{query.casefold()}"] = (time.monotonic() + TTL_SECONDS, rows)
            msg = "API 請求頻率已達上限" if isinstance(exc, requests.HTTPError) and exc.response is not None and exc.response.status_code == 429 else "NBA 資料服務暫時無法使用"
            notice = f"{msg}，目前顯示精選球星範例資料。"
    normalized = []
    for p in rows:
        feet, inches = p.get("height_feet"), p.get("height_inches")
        height_cm = round((int(feet) * 12 + int(inches)) * 2.54) if feet is not None and inches is not None else None
        pounds = p.get("weight_pounds")
        weight_kg = round(float(pounds) * 0.45359237, 1) if pounds not in (None, "") else None
        team = p.get("team") or {}
        conference = team.get("conference")
        normalized.append({"name": f"{p.get('first_name','')} {p.get('last_name','')}".strip(), "position": p.get("position") or "—",
                           "height_raw": f"{feet}-{inches}" if feet is not None and inches is not None else "—",
                           "weight_raw": f"{pounds} lbs" if pounds else "—", "height_cm": height_cm, "weight_kg": weight_kg,
                           "team": team.get("full_name", "自由球員"), "conference_zh": {"East": "東區", "West": "西區"}.get(conference, conference or "—")})
    return (normalized, notice) if with_notice else normalized


def get_activities():
    with (ROOT / "data" / "tw_activities.json").open(encoding="utf-8") as f:
        return json.load(f)


def get_next_race():
    races = get_f1_schedule()
    now = datetime.now(timezone(timedelta(hours=8)))
    for race in races:
        try:
            date = datetime.strptime(race["time_tw"][:16], "%Y/%m/%d %H:%M").replace(tzinfo=timezone(timedelta(hours=8)))
            if date >= now:
                return race
        except (ValueError, KeyError):
            continue
    return races[0] if races else None
