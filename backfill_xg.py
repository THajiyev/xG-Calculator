import pandas as pd
import numpy as np
import joblib
import os
import warnings
from dotenv import load_dotenv
from supabase import create_client

warnings.filterwarnings('ignore')
load_dotenv()

supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))


def fetch_null_shots(limit=50000):
    all_shots = []
    offset = 0
    chunk = 1000
    while len(all_shots) < limit:
        result = supabase.table('shots').select('*').is_('model_xg', 'null').range(offset, offset + chunk - 1).execute()
        all_shots.extend(result.data)
        if len(result.data) < chunk:
            break
        offset += chunk
    print(f'Fetched {len(all_shots)} null shots')
    return pd.DataFrame(all_shots)


def predict_and_write(shots):
    own_goals  = shots[shots['result'] == 'OwnGoal']
    penalties  = shots[shots['situation'] == 'Penalty']
    to_predict = shots[
        (shots['result'] != 'OwnGoal') &
        (shots['situation'] != 'Penalty')
    ].copy()

    to_predict['x']      = to_predict['x'].astype(float)
    to_predict['y']      = to_predict['y'].astype(float)
    to_predict['minute'] = to_predict['minute'].astype(int).clip(1, 119)
    to_predict['season'] = to_predict['season'].astype(int)

    to_predict['player_assisted'] = to_predict['player_assisted'].str.replace('&#039;', "'", regex=False)
    to_predict['is_assisted'] = to_predict['player_assisted'].notnull().astype(int)

    drop_cols = ['model_xg', 'player', 'player_id', 'h_team', 'a_team',
                 'date', 'match_id', 'player_assisted', 'result',
                 'understat_xg', 'season']
    to_predict = to_predict.drop(columns=[c for c in drop_cols if c in to_predict.columns])

    noise_actions = ['SubstitutionOn', 'SubstitutionOff', 'FormationChange', 'Start', 'End']
    to_predict['last_action'] = to_predict['last_action'].replace(noise_actions, 'Other')

    to_predict['game_phase'] = pd.cut(
        to_predict['minute'],
        bins=[0, 15, 30, 45, 60, 75, 90, 120],
        labels=['0-15', '15-30', '30-45', '45-60', '60-75', '75-90', '90+']
    )

    to_predict = pd.get_dummies(to_predict, columns=['last_action', 'situation', 'shot_type', 'league', 'h_a', 'game_phase'])

    GOAL_X, GOAL_Y = 1.0, 0.5
    to_predict['distance']         = np.sqrt((to_predict['x'] - GOAL_X)**2 + (to_predict['y'] - GOAL_Y)**2)
    to_predict['distance_squared'] = to_predict['distance'] ** 2
    to_predict['off_central']      = abs(to_predict['y'] - 0.5).astype(float)

    def goal_angle(x, y):
        left   = np.array([1.0, 0.458])
        right  = np.array([1.0, 0.542])
        a      = np.array([x, y])
        ba     = a - left
        ca     = a - right
        cosine = np.dot(ba, ca) / (np.linalg.norm(ba) * np.linalg.norm(ca) + 1e-6)
        return np.arccos(np.clip(cosine, -1, 1))

    to_predict['goal_angle']       = to_predict.apply(lambda r: goal_angle(r['x'], r['y']), axis=1)
    to_predict['distance_x_angle'] = to_predict['distance'] * to_predict['goal_angle']
    to_predict['in_six_yard_box']  = ((to_predict['x'] > 0.88) & (to_predict['y'].between(0.35, 0.65))).astype(int)
    to_predict['in_penalty_box']   = ((to_predict['x'] > 0.70) & (to_predict['y'].between(0.2,  0.8))).astype(int)

    shot_ids = to_predict['id'].tolist()

    model_features = model.calibrated_classifiers_[0].base_estimator.get_booster().feature_names
    df_aligned = to_predict.drop(columns=['id'], errors='ignore').reindex(columns=model_features, fill_value=0)

    preds = model.predict_proba(df_aligned)[:, 1]

    updates_dict = {}
    for sid, pred in zip(shot_ids, preds):
        updates_dict[sid] = {'id': sid, 'model_xg': float(pred)}
    for _, row in penalties.iterrows():
        updates_dict[row['id']] = {'id': row['id'], 'model_xg': 0.76}
    for _, row in own_goals.iterrows():
        updates_dict[row['id']] = {'id': row['id'], 'model_xg': 0.0}

    updates = list(updates_dict.values())
    for i in range(0, len(updates), 500):
        supabase.table('shots').upsert(updates[i:i+500]).execute()

    print(f'Wrote {len(updates)} predictions')
    return len(updates)


if __name__ == '__main__':
    print('Loading model...')
    model = joblib.load('xg_model.pkl')

    iteration = 1
    while iteration<=25:
        print(f'\nIteration {iteration}...')
        shots = fetch_null_shots(limit=50000)
        if len(shots) == 0:
            print('No more null shots. Done!')
            break
        predict_and_write(shots)
        iteration += 1