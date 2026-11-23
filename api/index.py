"""Vercel Python serverless entry point."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from flask import Flask, render_template, request
from dotenv import load_dotenv

from services.sports_api import (
    get_activities, get_f1_schedule, get_f1_drivers, get_nba_players,
    get_nba_teams, get_sports, get_next_race, SPORTS_TRANSLATIONS,
)

load_dotenv(ROOT / ".env")
app = Flask(__name__, template_folder=str(ROOT / "templates"), static_folder=str(ROOT / "static"))
app.config["JSON_AS_ASCII"] = False


@app.context_processor
def common_context():
    return {"sports_translations": SPORTS_TRANSLATIONS}


@app.get("/")
def home():
    activities = get_activities()[:3]
    return render_template("index.html", activities=activities, next_race=get_next_race(), sports=get_sports()[:6])


@app.get("/sports")
def sports_page():
    sports, notice = get_sports(with_notice=True)
    return render_template("sports.html", sports=sports, notice=notice)


@app.get("/schedule")
def schedule_page():
    sport = request.args.get("sport", "all").lower()
    races, notice = get_f1_schedule(with_notice=True)
    # The supplied live source is F1. Curated sample rows keep the all-sports view useful.
    sample = [
        {"round": "焦點賽事", "name": "MLB 焦點戰：洋基 vs. 紅襪", "circuit": "美國紐約（賽事日期以官方公告為準）", "time_tw": "賽程依官方公告更新"},
        {"round": "焦點賽事", "name": "NBA 焦點戰：勇士 vs. 湖人", "circuit": "美國加州（賽事日期以官方公告為準）", "time_tw": "賽程依官方公告更新"},
    ]
    rows = races if sport == "f1" else races + sample
    return render_template("schedule.html", races=rows, sport=sport, notice=notice)


@app.get("/players")
def players_page():
    category = request.args.get("type", "nba").lower()
    query = request.args.get("q", "").strip()
    if category == "f1":
        players, notice = get_f1_drivers(with_notice=True)
    else:
        category = "nba"
        players, notice = get_nba_players(query=query, with_notice=True)
    return render_template("players.html", players=players, category=category, query=query, notice=notice, teams=get_nba_teams())


@app.get("/activities")
def activities_page():
    items = get_activities()
    sport = request.args.get("sport", "")
    city = request.args.get("city", "")
    if sport:
        items = [item for item in items if item["sport_type"] == sport]
    if city:
        items = [item for item in items if item["city"] == city]
    return render_template("activities.html", activities=items, selected_sport=sport, selected_city=city,
                           sports=sorted({x["sport_type"] for x in get_activities()}), cities=sorted({x["city"] for x in get_activities()}))


@app.errorhandler(404)
def not_found(_error):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=True)
