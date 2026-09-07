-- Схема бази даних для проєкту Steam Analytics

-- Основна таблиця ігор (статичні дані: жанр, дата виходу, видавець)
CREATE TABLE IF NOT EXISTS games (
    app_id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    release_date TEXT,          -- YYYY-MM-DD, якщо відомо; інакше YYYY
    release_year INTEGER,
    genres TEXT,                -- через кому: "Action,RPG"
    developer TEXT,
    publisher TEXT,
    price_usd REAL,
    is_free INTEGER DEFAULT 0,
    source TEXT,                 -- 'store_search' | 'steamspy'
    first_seen_at TEXT DEFAULT (datetime('now')),
    last_updated_at TEXT DEFAULT (datetime('now'))
);

-- Часові зрізи: скільки людей грає онлайн зараз (накопичується з кожним запуском пайплайну)
CREATE TABLE IF NOT EXISTS player_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    app_id INTEGER NOT NULL,
    players_online INTEGER,
    collected_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (app_id) REFERENCES games(app_id)
);

-- Агреговані лічильники релізів за рік+жанр (перераховується щоразу з таблиці games)
CREATE TABLE IF NOT EXISTS releases_by_genre_year (
    release_year INTEGER,
    genre TEXT,
    game_count INTEGER,
    updated_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (release_year, genre)
);

-- Лог запусків пайплайну (для діагностики автоматизації)
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_started_at TEXT DEFAULT (datetime('now')),
    run_finished_at TEXT,
    games_upserted INTEGER,
    snapshots_added INTEGER,
    status TEXT,                 -- 'success' | 'partial' | 'failed'
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_games_release_year ON games(release_year);
CREATE INDEX IF NOT EXISTS idx_snapshots_app_id ON player_snapshots(app_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_collected_at ON player_snapshots(collected_at);
