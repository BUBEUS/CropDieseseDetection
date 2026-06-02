"""
AI System – petla przetwarzania zadan.

Pobiera zadania z kolejki Data Acquisition (GET /broker/next),
analizuje dane IoT lub zdjecia z drona, zapisuje wyniki do PostgreSQL.
"""

import os
import random
import time

import psycopg2
import psycopg2.extras
import requests

DATA_ACQUISITION_URL = os.getenv("DATA_ACQUISITION_URL", "http://data_acquisition:5000")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://myuser:mypassword@db:5432/mydb")

# Realistyczne nazwy chorob upraw
CROP_DISEASES = [
    "Zaraza ziemniaka (Phytophthora infestans)",
    "Mączniak prawdziwy zbóż",
    "Septorioza liści pszenicy",
    "Rdza liściowa (Puccinia triticina)",
    "Botrytis cinerea (szara pleśń)",
    "Alternarioza (Alternaria spp.)",
    "Fuzarioza kłosów pszenicy",
]


# ---------------------------------------------------------------------------
# Logika analizy
# ---------------------------------------------------------------------------

def analyze_iot(data: dict) -> dict:
    temp = data["temperature"]
    humidity = data["humidity"]

    if humidity > 75 and 15 <= temp <= 30:
        return {
            "risk_level": "high",
            "analysis_note": (
                f"ALERT: Warunki sprzyjają chorobom grzybicznym! "
                f"Wilgotność {humidity}%, temp {temp:.1f}°C. "
                f"Zalecane opryski profilaktyczne."
            ),
        }
    if temp < 2:
        return {
            "risk_level": "medium",
            "analysis_note": (
                f"Ryzyko przymrozku: {temp:.1f}°C. "
                f"Rozważ okrycie wrażliwych upraw."
            ),
        }
    if humidity > 65 and temp > 20:
        return {
            "risk_level": "medium",
            "analysis_note": (
                f"Umiarkowane ryzyko chorób. "
                f"Wilgotność {humidity}%, temp {temp:.1f}°C – monitoruj uprawy."
            ),
        }
    return {
        "risk_level": "low",
        "analysis_note": (
            f"Warunki normalne. Temp {temp:.1f}°C, wilg {humidity}%. Brak ryzyka."
        ),
    }


def analyze_drone(data: dict) -> dict:
    disease_detected = random.random() < 0.28  # ~28% szans na chorobę
    if disease_detected:
        name = random.choice(CROP_DISEASES)
        score = round(random.uniform(0.58, 0.96), 2)
        return {
            "disease_detected": True,
            "disease_name": name,
            "risk_score": score,
            "recommendation": (
                f"Wykryto objawy: {name} (pewność {score:.0%}). "
                f"Zalecany oprysk na obszarze ok. ({data['latitude']:.4f}, "
                f"{data['longitude']:.4f}). Pomiń zdrowe strefy."
            ),
        }
    score = round(random.uniform(0.0, 0.22), 2)
    return {
        "disease_detected": False,
        "disease_name": None,
        "risk_score": score,
        "recommendation": "Rośliny zdrowe. Brak interwencji wymagany.",
    }


# ---------------------------------------------------------------------------
# Zapis do bazy
# ---------------------------------------------------------------------------

def save_iot(conn, job: dict, analysis: dict) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO iot_readings
                (client_id, identifier, temperature, humidity, pressure,
                 risk_level, analysis_note)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                job["device"]["client_id"],
                job["device"]["identifier"],
                job["data"]["temperature"],
                job["data"]["humidity"],
                job["data"]["pressure"],
                analysis["risk_level"],
                analysis["analysis_note"],
            ),
        )
    conn.commit()


def save_drone(conn, job: dict, analysis: dict) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO drone_observations
                (client_id, identifier, photo_number, photo_path,
                 latitude, longitude, altitude,
                 disease_detected, disease_name, risk_score, recommendation)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                job["device"]["client_id"],
                job["device"]["identifier"],
                job["data"]["photo_number"],
                job["data"]["photo_path"],
                job["data"]["latitude"],
                job["data"]["longitude"],
                job["data"]["altitude"],
                analysis["disease_detected"],
                analysis["disease_name"],
                analysis["risk_score"],
                analysis["recommendation"],
            ),
        )
    conn.commit()


# ---------------------------------------------------------------------------
# Infrastruktura
# ---------------------------------------------------------------------------

def wait_for_db() -> psycopg2.extensions.connection:
    while True:
        try:
            conn = psycopg2.connect(DATABASE_URL)
            print("[AI] Polaczono z baza danych.")
            return conn
        except psycopg2.OperationalError:
            print("[AI] Czekam na baze danych...")
            time.sleep(3)


def process_next_job(conn) -> bool:
    """Pobiera jedno zadanie z kolejki i je przetwarza. Zwraca False gdy kolejka pusta."""
    try:
        resp = requests.get(f"{DATA_ACQUISITION_URL}/broker/next", timeout=5)
    except requests.exceptions.Timeout:
        print("[AI] Timeout – Data Acquisition nie odpowiada.")
        return False
    except requests.exceptions.ConnectionError:
        print("[AI] Brak polaczenia z Data Acquisition.")
        return False

    if resp.status_code == 404:
        return False  # kolejka pusta

    resp.raise_for_status()
    job = resp.json()["message"]
    job_type = job.get("job_type")
    print(f"[AI] Zadanie {job['job_id']} ({job_type})")

    if job_type == "iot_analysis":
        analysis = analyze_iot(job["data"])
        save_iot(conn, job, analysis)
        print(f"     ryzyko={analysis['risk_level']}  {analysis['analysis_note'][:70]}")

    elif job_type == "drone_analysis":
        analysis = analyze_drone(job["data"])
        save_drone(conn, job, analysis)
        label = analysis["disease_name"] or "zdrowe"
        print(f"     choroba={'TAK' if analysis['disease_detected'] else 'NIE'}  {label}  score={analysis['risk_score']}")

    return True


# ---------------------------------------------------------------------------
# Glowna petla
# ---------------------------------------------------------------------------

def main() -> None:
    print("[AI] System AI uruchomiony. Lacze z baza i kolejka...")
    conn = wait_for_db()

    while True:
        try:
            processed = process_next_job(conn)
            # Gdy kolejka pusta – odczekaj chwile, by nie hammeric serwisu
            if not processed:
                time.sleep(2)
        except Exception as exc:
            print(f"[AI] Blad: {exc}. Ponawiam polaczenie...")
            try:
                conn.close()
            except Exception:
                pass
            time.sleep(5)
            conn = wait_for_db()


if __name__ == "__main__":
    main()
