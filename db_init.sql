-- Pomiary z czujnikow IoT z wynikiem analizy ryzyka
CREATE TABLE IF NOT EXISTS iot_readings (
    id          SERIAL PRIMARY KEY,
    client_id   INTEGER NOT NULL,
    identifier  INTEGER NOT NULL,
    temperature REAL    NOT NULL,
    humidity    REAL    NOT NULL,
    pressure    REAL    NOT NULL,
    risk_level     TEXT,
    analysis_note  TEXT,
    received_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Obserwacje z dronow z wynikiem detekcji chorob
CREATE TABLE IF NOT EXISTS drone_observations (
    id               SERIAL PRIMARY KEY,
    client_id        INTEGER NOT NULL,
    identifier       INTEGER NOT NULL,
    photo_number     INTEGER NOT NULL,
    photo_path       TEXT,
    latitude         REAL    NOT NULL,
    longitude        REAL    NOT NULL,
    altitude         REAL    NOT NULL,
    disease_detected BOOLEAN DEFAULT FALSE,
    disease_name     TEXT,
    risk_score       REAL,
    recommendation   TEXT,
    received_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Log zdarzen systemowych
CREATE TABLE IF NOT EXISTS audit_log (
    id         SERIAL PRIMARY KEY,
    client_id  INTEGER,
    action     TEXT        NOT NULL,
    details    TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
