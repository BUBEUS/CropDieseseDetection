import os

import psycopg2
import psycopg2.extras
import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="CropDisease Web App")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://myuser:mypassword@db:5432/mydb")

app.mount("/photos", StaticFiles(directory="/app/photos"), name="photos")


def query_db(sql: str, params=None) -> list[dict]:
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]


@app.get("/")
def index():
    return FileResponse("index.html")


@app.get("/api/dashboard")
def dashboard():
    try:
        iot = query_db(
            "SELECT COUNT(*) AS total, "
            "COUNT(CASE WHEN risk_level='high' THEN 1 END) AS high_risk "
            "FROM iot_readings"
        )[0]
        drone = query_db(
            "SELECT COUNT(*) AS total, "
            "COUNT(CASE WHEN disease_detected THEN 1 END) AS diseases "
            "FROM drone_observations"
        )[0]
        return {"iot": iot, "drone": drone}
    except Exception as exc:
        return JSONResponse(status_code=503, content={"error": str(exc)})


@app.get("/api/iot/latest")
def iot_latest():
    try:
        return query_db(
            """
            SELECT id, client_id, identifier,
                   temperature, humidity, pressure,
                   risk_level, analysis_note,
                   to_char(received_at AT TIME ZONE 'Europe/Warsaw', 'YYYY-MM-DD HH24:MI:SS') AS received_at
            FROM iot_readings
            ORDER BY received_at DESC
            LIMIT 25
            """
        )
    except Exception as exc:
        return JSONResponse(status_code=503, content={"error": str(exc)})


@app.get("/api/drone/latest")
def drone_latest():
    try:
        return query_db(
            """
            SELECT id, client_id, identifier, photo_number,
                   latitude, longitude, altitude,
                   disease_detected, disease_name, risk_score, recommendation,
                   to_char(received_at AT TIME ZONE 'Europe/Warsaw', 'YYYY-MM-DD HH24:MI:SS') AS received_at
            FROM drone_observations
            ORDER BY received_at DESC
            LIMIT 25
            """
        )
    except Exception as exc:
        return JSONResponse(status_code=503, content={"error": str(exc)})


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
