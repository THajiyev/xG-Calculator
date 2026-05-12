import asyncio
import aiohttp
import os
from dotenv import load_dotenv
from understat import Understat
from supabase import create_client
import warnings
warnings.filterwarnings("ignore")

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
if SUPABASE_KEY is None or SUPABASE_URL is None:
    print("URL or key did not load properly")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

LEAGUES = ["epl", "la_liga", "bundesliga", "serie_a", "ligue_1"]
SEASONS = range(2014, 2026)


async def fetch_with_retry(coro_fn, retries=10, delay=4):
    for attempt in range(retries):
        try:
            return await coro_fn()
        except Exception as e:
            if attempt < retries - 1:
                print(f"  Retrying after error: {e}")
                await asyncio.sleep(delay)
            else:
                raise


async def scrape_shots(understat, league, season):
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
                    "model_xg":        None,
                    "h_a":             s['h_a'],
                    "player_assisted": s.get('player_assisted'),
                    "h_team":          s['h_team'],
                    "a_team":          s['a_team'],
                    "league":          league,
                    "season":          season,
                    "date":            s['date'],
                })
    return shots


async def scrape_matches(understat, league, season):
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


async def scrape_players(understat, league, season):
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


def upsert(table, rows, chunk_size=500):
    for i in range(0, len(rows), chunk_size):
        chunk = rows[i:i + chunk_size]
        supabase.table(table).upsert(chunk).execute()
    print(f"  {table}: {len(rows)} rows inserted")


async def scrape_league_season(league, season):
    async with aiohttp.ClientSession() as session:
        understat = Understat(session)
        print(f"Scraping {league} {season}...")

        shots   = await fetch_with_retry(lambda: scrape_shots(understat, league, season))
        matches = await fetch_with_retry(lambda: scrape_matches(understat, league, season))
        players = await fetch_with_retry(lambda: scrape_players(understat, league, season))

        if shots:   
            upsert("shots",   shots)
        if matches: 
            upsert("matches", matches)
        if players: 
            upsert("players", players)


async def main():
    for league in LEAGUES:
        for season in SEASONS:
            try:
                await scrape_league_season(league, season)
                await asyncio.sleep(1)
            except Exception as e:
                print(f"  FAILED {league} {season}: {e}")
                
# TARGETS = [
#     (league, year)
# ]

# async def main():
#     for league, season in TARGETS:
#         try:
#             await scrape_league_season(league, season)
#             await asyncio.sleep(1)
#         except Exception as e:
#             print(f"  FAILED {league} {season}: {e}")


asyncio.run(main())