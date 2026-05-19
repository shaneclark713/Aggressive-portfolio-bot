CREATE TABLE IF NOT EXISTS ecosystem_state (
    state_id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'spy_0dte',
    ecosystem_score REAL,
    deployment_mode TEXT,
    risk_regime TEXT,
    runtime_health TEXT,
    feedback TEXT,
    environment_state TEXT,
    reinforcement_bias TEXT,
    adaptation_state TEXT,
    state_persistence TEXT,
    payload TEXT NOT NULL
);