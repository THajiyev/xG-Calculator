import asyncio
import aiohttp
import os
from datetime import datetime
from understat import Understat
from supabase import create_client
import warnings
warnings.filterwarnings("ignore")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

LEAGUES = ["epl", "la_liga", "bundesliga", "serie_a", "ligue_1"]


def get_current_season():
    now = datetime.now()
    return now.year if now.month >= 8 else now.year - 1


def upsert(table, rows, chunk_size=500):
    for i in range(0, len(rows), chunk_size):
        chunk = rows[i:i + chunk_size]
        supabase.table(table).upsert(chunk).execute()
    print(f"  {table}: {len(rows)} rows upserted")


async def update_shots(understat, league, season):
    match_ids = [
        item['id']
        for item in await understat.get_league_results(league, season)
    ]
    shots = []
    for match_id in match_ids:
        match_shots = await understat.get_match_shots(match_id)
        for side in ['h', 'a']:
            for s in match_shots[side]:
                shots.append({
                    "id":              s['id'],
                    "match_id":        s['match_id'],
                    "player":          s['player'],
                    "player_id":       s['player_id'],
                    "minute":          int(s['minute']),
                    "x":               float(s['X']),
                    "y":               float(s['Y']),
                    "situation":       s['situation'],
                    "shot_type":       s['shotType'],
                    "last_action":     s['lastAction'],
                    "result":          s['result'],
                    "understat_xg":    float(s['xG']),
                    "h_a":             s['h_a'],
                    "player_assisted": s.get('player_assisted'),
                    "h_team":          s['h_team'],
                    "a_team":          s['a_team'],
                    "league":          league,
                    "season":          season,
                    "date":            s['date'],
                })
    return shots


async def update_matches(understat, league, season):
    results = await understat.get_league_results(league, season)
    matches = []
    for r in results:
        forecast = r.get('forecast', {})
        matches.append({
            "id":            r['id'],
            "home_team":     r['h']['title'],
            "away_team":     r['a']['title'],
            "home_goals":    int(r['goals']['h']) if r['goals']['h'] is not None else None,
            "away_goals":    int(r['goals']['a']) if r['goals']['a'] is not None else None,
            "home_xg":       float(r['xG']['h']) if r['xG']['h'] else None,
            "away_xg":       float(r['xG']['a']) if r['xG']['a'] else None,
            "home_forecast": float(forecast['w']) if forecast.get('w') else None,
            "draw_forecast": float(forecast['d']) if forecast.get('d') else None,
            "away_forecast": float(forecast['l']) if forecast.get('l') else None,
            "date":          r['datetime'],
            "season":        season,
            "league":        league,
        })
    return matches


async def update_players(understat, league, season):
    raw = await understat.get_league_players(league, season)
    players = []
    for p in raw:
        players.append({
            "id":          p['id'],
            "season":      season,
            "league":      league,
            "player_name": p['player_name'],
            "team":        p['team_title'],
            "games":       int(p['games']),
            "goals":       int(p['goals']),
            "xg":          float(p['xG']),
            "assists":     int(p['assists']),
            "xa":          float(p['xA']),
            "shots":       int(p['shots']),
            "key_passes":  int(p['key_passes']),
            "npg":         int(p['npg']),
            "npxg":        float(p['npxG']),
        })
    return players


async def run_incremental_update():
    current_season = get_current_season()
    seasons_to_update = [current_season - 1, current_season]
    print(f"Updating seasons: {seasons_to_update}")

    for league in LEAGUES:
        for season in seasons_to_update:
            try:
                async with aiohttp.ClientSession() as session:
                    understat = Understat(session)
                    print(f"Updating {league} {season}...")

                    shots   = await update_shots(understat, league, season)
                    matches = await update_matches(understat, league, season)
                    players = await update_players(understat, league, season)

                    if shots:   upsert("shots",   shots)
                    if matches: upsert("matches", matches)
                    if players: upsert("players", players)

            except Exception as e:
                print(f"  FAILED {league} {season}: {e}")


def backfill_model_xg(model, X, shot_ids):
    predictions = model.predict_proba(X)[:, 1]
    updates = [
        {"id": shot_id, "model_xg": float(pred)}
        for shot_id, pred in zip(shot_ids, predictions)
    ]
    upsert("shots", updates)
    print(f"Backfilled model_xg for {len(updates)} shots")


if __name__ == "__main__":
    import sys

    mode = sys.argv[1] if len(sys.argv) > 1 else "update"

    if mode == "update":
        asyncio.run(run_incremental_update())

    elif mode == "backfill_model":
        print("Load your model and call backfill_model_xg(model, X, shot_ids) directly.")

    else:
        print(f"Unknown mode: {mode}. Use 'update' or 'backfill_model'.")