import asyncio
import aiohttp
from understat import Understat
import pandas as pd
import warnings

#Doesn't print out warnings so it is easier to review the terminal
warnings.filterwarnings("ignore")

#keys for the leagues
leagues = [
    "epl",
    "la_liga",
    "bundesliga",
    "serie_a",
    "ligue_1"
]

database = []

async def get_xg(league, year):
    async with aiohttp.ClientSession() as session:
        understat = Understat(session)
        ids = [item['id'] for item in await understat.get_league_results(league, year)]
        season_data = [
            [
                shot['X'],
                shot['Y'],
                shot['situation'],
                shot['shotType'],
                shot['lastAction'],
                shot['result'],
                id,#for debugging
                shot['xG'],
                league,#for debugging
                year #for debugging
            ]
            for id in ids
            for match_xgs in [await understat.get_match_shots(id)]
            for team in ['a', 'h']
            for shot in match_xgs[team]
        ]

        return season_data

def export_csv(data):
    df = pd.DataFrame(data)
    df.columns = [
        'X',
        'Y',
        'situation',
        'shotType',
        'lastAction',
        'result',
        'id',
        'xG',
        'league',
        'year'
    ]
    df.to_csv('data.csv', index=False)

loop = asyncio.get_event_loop()
for league in leagues:
    for year in range(2014,2023):
        try:
            data=loop.run_until_complete(get_xg(league, year))
            database.extend(data)
            print("COMPLETED", league, year)
        except:
            print("FAILED", league, year)

export_csv(database)