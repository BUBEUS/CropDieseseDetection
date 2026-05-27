CREATE TABLE IF NOT EXISTS client (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS hot_drone (
    id INTEGER PRIMARY KEY,
    client_id INTEGER REFERENCES client(id) ON DELETE CASCADE,
    identifier INTEGER NOT NULL,
    photo_number INTEGER NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    altitude REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS hot_iot (
    id INTEGER PRIMARY KEY,
    client_id INTEGER REFERENCES client(id) ON DELETE CASCADE,
    identifier INTEGER NOT NULL,
    temperature REAL NOT NULL,
    humidity REAL NOT NULL,
    pressure REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS client (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
);


CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY,
    client_id INTEGER REFERENCES client(id) ON DELETE CASCADE,
    action TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS archive (
    id INTEGER PRIMARY KEY,
    tu_bedzie TEXT NOT NULL
);




