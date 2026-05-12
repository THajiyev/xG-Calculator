CREATE TABLE shots (
    id               TEXT PRIMARY KEY,
    match_id         TEXT,
    player           TEXT,
    player_id        TEXT,
    minute           INTEGER,
    x                FLOAT,        
    y                FLOAT,        
    situation        TEXT,         
    shot_type        TEXT,         
    last_action      TEXT,         
    result           TEXT,         
    understat_xg     FLOAT,        
    model_xg         FLOAT,        
    h_a              TEXT,         
    player_assisted  TEXT,         
    h_team           TEXT,
    a_team           TEXT,
    league           TEXT,
    season           INTEGER,
    date             TIMESTAMP
);

CREATE TABLE matches (
    id               TEXT PRIMARY KEY,
    home_team        TEXT,
    away_team        TEXT,
    home_goals       INTEGER,
    away_goals       INTEGER,
    home_xg          FLOAT,
    away_xg          FLOAT,
    home_forecast    FLOAT,       
    draw_forecast    FLOAT,
    away_forecast    FLOAT,
    date             TIMESTAMP,
    season           INTEGER,
    league           TEXT
);

CREATE TABLE players (
    id               TEXT,
    season           INTEGER,
    league           TEXT,
    player_name      TEXT,
    team             TEXT,
    games            INTEGER,
    goals            INTEGER,
    xg               FLOAT,
    assists          INTEGER,
    xa               FLOAT,
    shots            INTEGER,
    key_passes       INTEGER,
    npg              INTEGER,      
    npxg             FLOAT,       
    PRIMARY KEY (id, season, league)
);


CREATE INDEX idx_shots_league_season ON shots (league, season);
CREATE INDEX idx_shots_match ON shots (match_id);
CREATE INDEX idx_shots_player ON shots (player_id);
CREATE INDEX idx_matches_league_season ON matches (league, season);
CREATE INDEX idx_matches_home_team ON matches (home_team);
CREATE INDEX idx_matches_away_team ON matches (away_team);
CREATE INDEX idx_players_team_season ON players (team, season);