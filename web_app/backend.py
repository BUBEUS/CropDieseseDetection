import os
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras
import requests as http_requests
import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="CropDisease Web App")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://myuser:mypassword@db:5432/mydb")
DATA_ACQUISITION_URL = os.getenv("DATA_ACQUISITION_URL", "http://data_acquisition:5000")

app.mount("/photos", StaticFiles(directory="/app/photos"), name="photos")


def query_db(sql: str, params=None) -> list[dict]:
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]


@app.get("/")
def index():
    return FileResponse("index.html")


@app.get("/api/services/status")
def services_status():
    ts = datetime.now(timezone.utc).isoformat()
    result: dict = {
        "web_app": "ok",
        "database": "unknown",
        "data_acquisition": "unknown",
        "data_acquisition_broker": False,
        "timestamp": ts,
    }

    try:
        query_db("SELECT 1")
        result["database"] = "ok"
    except Exception:
        result["database"] = "error"

    try:
        resp = http_requests.get(f"{DATA_ACQUISITION_URL}/health", timeout=2.0)
        if resp.status_code == 200:
            acq = resp.json()
            result["data_acquisition"] = acq.get("status", "unknown")
            result["data_acquisition_broker"] = acq.get("broker_connected", False)
        else:
            result["data_acquisition"] = "degraded"
    except http_requests.exceptions.Timeout:
        result["data_acquisition"] = "timeout"
    except Exception:
        result["data_acquisition"] = "unreachable"

    return result


@app.get("/api/clients")
def clients():
    try:
        return query_db("SELECT id, name, location FROM clients ORDER BY id")
    except Exception as exc:
        return JSONResponse(status_code=503, content={"error": str(exc)})


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
        audit = query_db("SELECT COUNT(*) AS total FROM audit_log")[0]
        return {"iot": iot, "drone": drone, "audit": audit}
    except Exception as exc:
        return JSONResponse(status_code=503, content={"error": str(exc)})


@app.get("/api/iot/latest")
def iot_latest():
    try:
        return query_db(
            """
            SELECT r.id, r.client_id, c.name AS client_name, c.location AS client_location,
                   r.identifier, r.temperature, r.humidity, r.pressure,
                   r.risk_level, r.analysis_note,
                   to_char(r.received_at AT TIME ZONE 'Europe/Warsaw', 'YYYY-MM-DD HH24:MI:SS') AS received_at
            FROM iot_readings r
            LEFT JOIN clients c ON c.id = r.client_id
            ORDER BY r.received_at DESC
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
            SELECT d.id, d.client_id, c.name AS client_name, c.location AS client_location,
                   d.identifier, d.photo_number,
                   d.latitude, d.longitude, d.altitude,
                   d.disease_detected, d.disease_name, d.risk_score, d.recommendation,
                   to_char(d.received_at AT TIME ZONE 'Europe/Warsaw', 'YYYY-MM-DD HH24:MI:SS') AS received_at
            FROM drone_observations d
            LEFT JOIN clients c ON c.id = d.client_id
            ORDER BY d.received_at DESC
            LIMIT 25
            """
        )
    except Exception as exc:
        return JSONResponse(status_code=503, content={"error": str(exc)})


@app.get("/api/audit/latest")
def audit_latest():
    try:
        return query_db(
            """
            SELECT a.id, a.client_id, c.name AS client_name,
                   a.action, a.details,
                   to_char(a.created_at AT TIME ZONE 'Europe/Warsaw', 'YYYY-MM-DD HH24:MI:SS') AS created_at
            FROM audit_log a
            LEFT JOIN clients c ON c.id = a.client_id
            ORDER BY a.created_at DESC
            LIMIT 50
            """
        )
    except Exception as exc:
        return JSONResponse(status_code=503, content={"error": str(exc)})


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)