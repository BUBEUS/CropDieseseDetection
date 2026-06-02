-- Klienci systemu (farmerzy, agrogospodarstwa)
CREATE TABLE IF NOT EXISTS clients (
    id         SERIAL PRIMARY KEY,
    name       TEXT NOT NULL,
    location   TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO clients (id, name, location) VALUES
(1,  'Agrogospodarstwo Kowalski',       'Mazowieckie'),
(2,  'Ferma Nowak sp. z o.o.',           'Małopolskie'),
(3,  'Sad Wiśniewskich',                 'Lubelskie'),
(4,  'Rolnictwo Wójcik',                 'Podkarpackie'),
(5,  'Ekologiczne Pola Kamińska',        'Wielkopolskie'),
(6,  'Agroturystyka Lewandowski',        'Pomorskie'),
(7,  'Pola Zielińskich',                 'Łódzkie'),
(8,  'Uprawy Woźniak',                   'Kujawsko-Pomorskie'),
(9,  'Szklarnie Dąbrowski',              'Śląskie'),
(10, 'Sady Kozłowski',                   'Dolnośląskie'),
(11, 'Farma Kaczmarek',                  'Opolskie'),
(12, 'Plantacja Mazur',                  'Warmińsko-Mazurskie'),
(13, 'Agro Piotrowski',                  'Podlaskie'),
(14, 'Uprawy Grabowski',                 'Zachodniopomorskie'),
(15, 'Sadownictwo Pawlak',               'Świętokrzyskie'),
(16, 'Rolnik Michalski',                 'Lubuskie'),
(17, 'Hodowla Nowicki',                  'Mazowieckie'),
(18, 'Ekofarm Adamczyk',                 'Małopolskie'),
(19, 'Pola Jabłońska',                   'Lubelskie'),
(20, 'Agrogospodarstwo Szymański',       'Wielkopolskie')
ON CONFLICT (id) DO NOTHING;

-- Pomiary z czujnikow IoT z wynikiem analizy ryzyka
CREATE TABLE IF NOT EXISTS iot_readings (
    id          SERIAL PRIMARY KEY,
    client_id   INTEGER NOT NULL REFERENCES clients(id),
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
    client_id        INTEGER NOT NULL REFERENCES clients(id),
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
    client_id  INTEGER REFERENCES clients(id),
    action     TEXT        NOT NULL,
    details    TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
