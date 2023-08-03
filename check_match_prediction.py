import joblib
import pandas as pd
from helper_methods import *
import math
import asyncio
import aiohttp
import warnings
from understat import Understat

#Doesn't print out warnings so it is easier to review the terminal
warnings.filterwarnings("ignore")

class Predictions:

    def __init__(self):
        self.model = joblib.load('model.pkl')
        self.scaler = load_scaler_from_json('scaler.json')

    def get_shot_xg(self, data):
        x = (1-float(data['X']))*get_dimension_constant()
        y = abs(.5-float(data['Y']))
        dataframe = pd.DataFrame({
            'foot': [1 if data['shotType'] in ['RightFoot', 'LeftFoot'] else 0],
            'X': [x],
            'Y': [y],
            'angle': [get_angle(data, scaleX=True)],
            'distance': [math.hypot(x,y)],
            "Throughball":[1 if data['lastAction']=="Throughball" else 0],
            'Standard': [1 if data['lastAction']=='Standard' else 0],
            "Rebound": [1 if data['lastAction']=="Rebound" else 0],
            "Cross": [1 if data['lastAction']=="Cross" else 0],
            "Penalty":[1 if data['situation']=="Penalty" else 0]
        }, index=[0])
        all_cols = dataframe[['X','Y', 'angle', 'distance', 'foot', "Throughball", "Standard", "Rebound", "Cross", "Penalty"]]
        all_cols = self.scaler.transform(all_cols)
        return self.model.predict_proba(all_cols).tolist()[0][1]
    
    def analyze_match(self, id):
        async def analyze(id):
            #Expected results are the outputs from our model
            #Actual is the real scoreline 
            #Official are the xGs from Understat
            result = {
                "expected":{
                    "h":0,
                    "a":0
                },
                "actual":{
                    "h":0,
                    "a":0
                },
                "official":{
                    "h":0,
                    "a":0
                }
            }
            async with aiohttp.ClientSession() as session:
                understat = Understat(session)
                for match_xgs in [await understat.get_match_shots(id)]:
                    for team in ['a', 'h']:
                        for shot in match_xgs[team]:
                            my_xG = self.get_shot_xg(shot)
                            official_xg = float(shot['xG'])
                            result['expected'][team]=result['expected'][team]+my_xG
                            result["official"][team]=result["official"][team]+official_xg
                            if shot['result']=='Goal':
                                result['actual'][team]=result['actual'][team]+1
            return result
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(analyze(id))

    def get_formatted_result(self, id):
        result = self.analyze_match(id)
        expected_h = round(result["expected"]["h"], 3)
        expected_a = round(result["expected"]["a"], 3)
        actual_h = round(result["actual"]["h"], 3)
        actual_a = round(result["actual"]["a"], 3)
        official_h = round(result["official"]["h"], 3)
        official_a = round(result["official"]["a"], 3)
        score = f"ID: {id}, E: {expected_h:.3f}:{expected_a:.3f}, A:{actual_h}:{actual_a}, xG:{official_h}:{official_a}"
        match_result = 2 if actual_h == actual_a else (1 if actual_h > actual_a else 0)
        my_prediction = int(expected_h>expected_a)==match_result
        understat_prediction = int(official_h>official_a)==match_result
        return my_prediction, understat_prediction, score
    
    def get_ids(self, league, year):
        async def pull_ids(league, year):
            async with aiohttp.ClientSession() as session:
                understat = Understat(session)
                ids = [item['id'] for item in await understat.get_league_results(league, year)]
                return ids
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(pull_ids(league, year))

    def test_league(self, league, year, save_txt=False):
        ids = self.get_ids(league, year)
        understat_predictions = []
        my_predictions = []
        scores = ""
        filename = league+str(year)+".txt"
        for id in ids:
            my_prediction, understat_prediction, score = self.get_formatted_result(id)
            understat_predictions.append(understat_prediction)
            my_predictions.append(my_prediction)
            scores+=score+"\n"
        print(league, year)
        print("MY MODEL")
        print(my_predictions.count(1), "out of", len(my_predictions))
        print("UNDERSTAT MODEL")
        print(understat_predictions.count(1), "out of", len(understat_predictions))
        if save_txt:
            with open(filename, 'w') as file:
                file.write(scores)

predictor = Predictions()

leagues = [
    "epl",
    "la_liga",
    "bundesliga",
    "serie_a",
    "ligue_1"
]

for year in range(2014,2023):
    for league in leagues:
        predictor.test_league(league, year, save_txt=True)