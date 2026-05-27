from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import psycopg2
from psycopg2.extras import RealDictCursor

app = FastAPI()

app.mount("/photos", StaticFiles(directory="/app/photos"), name="photos")

def get_db_connection():
    return psycopg2.connect(
        host="db", # Zmień na "db", jeśli uruchamiasz backend również jako kontener w docker-compose
        database="mydb",
        user="myuser",
        password="mypassword",
        cursor_factory=RealDictCursor
    )

@app.get("/")
def read_root():
    return FileResponse("index.html")

@app.get("/api/clients")
def get_clients():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, name FROM client')
    clients = cur.fetchall()
    conn.close()
    return clients

@app.get("/api/drone/{client_id}")
def get_drone_data(client_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM hot_drone WHERE client_id = %s', (client_id,))
    data = cur.fetchall()
    conn.close()
    return data

@app.get("/api/iot/{client_id}")
def get_iot_data(client_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM hot_iot WHERE client_id = %s', (client_id,))
    data = cur.fetchall()
    conn.close()
    return data

@app.get("/api/audit/{client_id}")
def get_audit_data(client_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM audit_log WHERE client_id = %s', (client_id,))
    data = cur.fetchall()
    conn.close()
    return data

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)