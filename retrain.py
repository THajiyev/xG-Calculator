import pandas as pd
import numpy as np
import joblib
import warnings
import os
from dotenv import load_dotenv
from supabase import create_client
from xgboost import XGBClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import log_loss, brier_score_loss

warnings.filterwarnings('ignore')
load_dotenv()

supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

BEST_PARAMS = {
    'n_estimators': 600,
    'max_depth': 4,
    'learning_rate': 0.17,
    'subsample': 0.9,
}

TEST_SEASONS = [2024, 2025]
DROP_COLS = ['id', 'result', 'understat_xg', 'is_goal', 'season']


def fetch_all(table):
    rows = []
    chunk = 1000
    offset = 0
    while True:
        result = supabase.table(table).select('*').range(offset, offset + chunk - 1).execute()
        rows.extend(result.data)
        if len(result.data) < chunk:
            break
        offset += chunk
    return pd.DataFrame(rows)


def clean_and_engineer(df):
    df = df[df['result'] != 'OwnGoal'].copy()
    df = df[df['situation'] != 'Penalty'].copy()
    df['is_goal'] = (df['result'] == 'Goal').astype(int)
    df['understat_xg'] = df['understat_xg'].astype(float)
    df['x'] = df['x'].astype(float)
    df['y'] = df['y'].astype(float)
    df['minute'] = df['minute'].astype(int)
    df['season'] = df['season'].astype(int)

    df['player_assisted'] = df['player_assisted'].str.replace('&#039;', "'", regex=False)
    df['is_assisted'] = df['player_assisted'].notnull().astype(int)

    df = df.drop(columns=['model_xg', 'player', 'player_id', 'h_team', 'a_team',
                           'date', 'match_id', 'player_assisted'])

    noise_actions = ['SubstitutionOn', 'SubstitutionOff', 'FormationChange', 'Start', 'End']
    df['last_action'] = df['last_action'].replace(noise_actions, 'Other')

    df['game_phase'] = pd.cut(
        df['minute'],
        bins=[0, 15, 30, 45, 60, 75, 90, 120],
        labels=['0-15', '15-30', '30-45', '45-60', '60-75', '75-90', '90+']
    )

    df = pd.get_dummies(df, columns=['last_action', 'situation', 'shot_type', 'league', 'h_a', 'game_phase'])

    GOAL_X, GOAL_Y = 1.0, 0.5
    df['distance'] = np.sqrt((df['x'] - GOAL_X)**2 + (df['y'] - GOAL_Y)**2)
    df['distance_squared'] = df['distance'] ** 2
    df['off_central'] = abs(df['y'] - 0.5).astype(float)

    def goal_angle(x, y):
        left  = np.array([1.0, 0.458])
        right = np.array([1.0, 0.542])
        a = np.array([x, y])
        ba = a - left
        ca = a - right
        cosine = np.dot(ba, ca) / (np.linalg.norm(ba) * np.linalg.norm(ca) + 1e-6)
        return np.arccos(np.clip(cosine, -1, 1))

    df['goal_angle'] = df.apply(lambda r: goal_angle(r['x'], r['y']), axis=1)
    df['distance_x_angle'] = df['distance'] * df['goal_angle']

    df['in_six_yard_box'] = ((df['x'] > 0.88) & (df['y'].between(0.35, 0.65))).astype(int)
    df['in_penalty_box']  = ((df['x'] > 0.70) & (df['y'].between(0.2,  0.8))).astype(int)

    return df


def train(df):
    train_df = df[~df['season'].isin(TEST_SEASONS)].copy()
    test_df  = df[df['season'].isin(TEST_SEASONS)].copy()

    max_season = train_df['season'].max()
    sample_weights = train_df['season'].apply(
        lambda s: 1 + (s - 2014) / (max_season - 2014)
    ).values

    X_train = train_df.drop(columns=DROP_COLS)
    y_train = train_df['is_goal']
    X_test  = test_df.drop(columns=DROP_COLS)
    y_test  = test_df['is_goal']

    model = CalibratedClassifierCV(
        XGBClassifier(
            **BEST_PARAMS,
            colsample_bytree=0.8,
            use_label_encoder=False,
            eval_metric='logloss',
            random_state=42
        ), cv=3, method='isotonic'
    )
    model.fit(X_train, y_train, sample_weight=sample_weights)

    preds        = model.predict_proba(X_test)[:, 1]
    ll           = log_loss(y_test, preds)
    bs           = brier_score_loss(y_test, preds)
    understat_ll = log_loss(y_test, test_df['understat_xg'])

    print(f'Log-loss:  {ll:.4f}')
    print(f'Brier:     {bs:.4f}')
    print(f'Understat: {understat_ll:.4f}')
    print(f'Gap:       {(ll - understat_ll) / understat_ll * 100:.1f}%')

    return model


if __name__ == '__main__':
    print('Fetching data...')
    df = fetch_all('shots')
    print(f'Fetched {len(df)} shots')

    print('Cleaning and engineering features...')
    df = clean_and_engineer(df)

    print('Training model...')
    model = train(df)

    joblib.dump(model, 'xg_model.pkl')
    print('Saved xg_model.pkl')
