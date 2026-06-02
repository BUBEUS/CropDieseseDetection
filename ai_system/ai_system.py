"""
AI System – konsument RabbitMQ.

Pobiera zadania z kolejki RabbitMQ (crop_analysis),
analizuje dane IoT lub zdjecia z drona, zapisuje wyniki i audyt do PostgreSQL.
"""

import functools
import json
import os
import random
import time

import pika
import pika.exceptions
import psycopg2
import psycopg2.extras

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://myuser:mypassword@db:5432/mydb")
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@message_broker:5672/")
QUEUE_NAME = "crop_analysis"

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
    disease_detected = random.random() < 0.28
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


def save_audit(conn, client_id: int, action: str, details: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO audit_log (client_id, action, details) VALUES (%s, %s, %s)",
            (client_id, action, details),
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


def wait_for_rabbitmq() -> pika.BlockingConnection:
    while True:
        try:
            params = pika.URLParameters(RABBITMQ_URL)
            params.heartbeat = 60
            params.blocked_connection_timeout = 300
            connection = pika.BlockingConnection(params)
            print("[AI] Polaczono z RabbitMQ.")
            return connection
        except pika.exceptions.AMQPConnectionError:
            print("[AI] Czekam na RabbitMQ...")
            time.sleep(3)


def on_message(ch, method, properties, body, *, conn_holder: list) -> None:
    """Callback wywoływany przez pika dla każdej wiadomości z kolejki."""
    try:
        job = json.loads(body)
        job_type = job.get("job_type")
        client_id = job["device"]["client_id"]
        job_id = job["job_id"]
        conn = conn_holder[0]

        if job_type == "iot_analysis":
            analysis = analyze_iot(job["data"])
            save_iot(conn, job, analysis)
            save_audit(conn, client_id, "iot_saved",
                       f"job_id={job_id} risk={analysis['risk_level']}")
            print(f"[AI] IoT  job={job_id} ryzyko={analysis['risk_level']}  "
                  f"{analysis['analysis_note'][:60]}")

        elif job_type == "drone_analysis":
            analysis = analyze_drone(job["data"])
            save_drone(conn, job, analysis)
            save_audit(conn, client_id, "drone_saved",
                       f"job_id={job_id} disease={analysis['disease_detected']} "
                       f"score={analysis['risk_score']}")
            label = analysis["disease_name"] or "zdrowe"
            print(f"[AI] Drone job={job_id} choroba={'TAK' if analysis['disease_detected'] else 'NIE'}  "
                  f"{label}  score={analysis['risk_score']}")

        else:
            print(f"[AI] Nieznany typ zadania: {job_type}")

        ch.basic_ack(delivery_tag=method.delivery_tag)

    except (psycopg2.OperationalError, psycopg2.InterfaceError) as exc:
        print(f"[AI] Blad bazy danych: {exc}. Ponawiam polaczenie z DB...")
        try:
            conn_holder[0].close()
        except Exception:
            pass
        conn_holder[0] = wait_for_db()
        # Wróć wiadomość do kolejki — zostanie przetworzona po reconnect
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    except Exception as exc:
        print(f"[AI] Blad przetwarzania zadania: {exc}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


# ---------------------------------------------------------------------------
# Glowna petla
# ---------------------------------------------------------------------------

def main() -> None:
    print("[AI] System AI uruchomiony. Lacze z baza i kolejka RabbitMQ...")
    conn_holder = [wait_for_db()]

    while True:
        try:
            rmq_conn = wait_for_rabbitmq()
            channel = rmq_conn.channel()
            channel.queue_declare(queue=QUEUE_NAME, durable=True)
            channel.basic_qos(prefetch_count=1)  # jeden job naraz = fair dispatch

            callback = functools.partial(on_message, conn_holder=conn_holder)
            channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)

            print(f"[AI] Czeka na zadania z kolejki '{QUEUE_NAME}'...")
            channel.start_consuming()

        except (
            pika.exceptions.AMQPConnectionError,
            pika.exceptions.AMQPChannelError,
            pika.exceptions.ConnectionClosedByBroker,
            pika.exceptions.StreamLostError,
        ) as exc:
            print(f"[AI] Utracono polaczenie z RabbitMQ: {exc}. Ponawiam za 5s...")
            time.sleep(5)

        except KeyboardInterrupt:
            print("[AI] Zatrzymywanie...")
            try:
                rmq_conn.close()
            except Exception:
                pass
            break

        except Exception as exc:
            print(f"[AI] Nieoczekiwany blad: {exc}")
            time.sleep(5)


if __name__ == "__main__":
    main()
