"""
Odbiór: Przyjęcie połączenia HTTP.
Normalizacja: Przekształcenie danych do standardu kolejki.
Publikacja: Wydanie wiadomości do RabbitMQ (aio-pika, persistent).
Potwierdzenie: Szybka odpowiedź do nadawcy.
"""

import asyncio
import json
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

import aio_pika
import uvicorn
from fastapi import FastAPI, HTTPException

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@message_broker:5672/")
QUEUE_NAME = "crop_analysis"

rmq_connection: aio_pika.abc.AbstractRobustConnection | None = None
rmq_channel: aio_pika.abc.AbstractRobustChannel | None = None
job_sequence: int = 0
published_count: int = 0


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _next_job_id() -> int:
    global job_sequence
    job_sequence += 1
    return job_sequence


def _require_fields(payload: dict[str, Any], required_fields: list[str]) -> None:
    missing_fields = [f for f in required_fields if f not in payload]
    if missing_fields:
        raise HTTPException(
            status_code=400,
            detail=f"Brakuje wymaganych pol: {', '.join(missing_fields)}",
        )


def _normalize_iot_payload(payload: dict[str, Any]) -> dict[str, Any]:
    _require_fields(
        payload,
        ["identifier", "client_id", "temperature", "humidity", "pressure"],
    )
    return {
        "job_id": _next_job_id(),
        "job_type": "iot_analysis",
        "source_type": "iot",
        "received_at": _utc_timestamp(),
        "device": {
            "identifier": payload["identifier"],
            "client_id": payload["client_id"],
        },
        "data": {
            "temperature": payload["temperature"],
            "humidity": payload["humidity"],
            "pressure": payload["pressure"],
        },
    }


def _normalize_drone_payload(payload: dict[str, Any]) -> dict[str, Any]:
    _require_fields(
        payload,
        ["identifier", "client_id", "photo_number", "latitude", "longitude", "altitude"],
    )
    photo_number = payload["photo_number"]
    return {
        "job_id": _next_job_id(),
        "job_type": "drone_analysis",
        "source_type": "drone",
        "received_at": _utc_timestamp(),
        "device": {
            "identifier": payload["identifier"],
            "client_id": payload["client_id"],
        },
        "data": {
            "photo_number": photo_number,
            "photo_path": f"photos/photo_{photo_number}.jpg",
            "photo_url": f"http://web_app:8000/photos/photo_{photo_number}.jpg",
            "latitude": payload["latitude"],
            "longitude": payload["longitude"],
            "altitude": payload["altitude"],
        },
    }


def normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    payload_type = payload.get("type")
    if payload_type == "iot":
        return _normalize_iot_payload(payload)
    if payload_type == "drone":
        return _normalize_drone_payload(payload)
    raise HTTPException(
        status_code=400,
        detail="Nieznany typ danych. Oczekiwano 'iot' albo 'drone'.",
    )


# ---------------------------------------------------------------------------
# Cykl życia aplikacji – połączenie z RabbitMQ
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    global rmq_connection, rmq_channel

    while True:
        try:
            rmq_connection = await aio_pika.connect_robust(RABBITMQ_URL)
            rmq_channel = await rmq_connection.channel()
            await rmq_channel.declare_queue(QUEUE_NAME, durable=True)
            print(f"[DataAcq] Polaczono z RabbitMQ, kolejka '{QUEUE_NAME}'.")
            break
        except Exception as exc:
            print(f"[DataAcq] Czekam na RabbitMQ: {exc}")
            await asyncio.sleep(3)

    yield

    if rmq_connection and not rmq_connection.is_closed:
        await rmq_connection.close()
        print("[DataAcq] Polaczenie z RabbitMQ zamkniete.")


app = FastAPI(title="Data Acquisition System", lifespan=lifespan)


# ---------------------------------------------------------------------------
# Endpointy
# ---------------------------------------------------------------------------

@app.get("/health")
async def healthcheck() -> dict[str, Any]:
    broker_ok = rmq_channel is not None and not rmq_channel.is_closed
    return {
        "status": "ok" if broker_ok else "degraded",
        "service": "data_acquisition",
        "broker": "rabbitmq",
        "broker_connected": broker_ok,
        "timestamp": _utc_timestamp(),
    }


@app.get("/queue/status")
async def queue_status() -> dict[str, Any]:
    return {
        "broker": "rabbitmq",
        "queue_name": QUEUE_NAME,
        "published_since_start": published_count,
        "management_ui": "http://localhost:15672",
        "timestamp": _utc_timestamp(),
    }


@app.post("/data")
async def receive_data(payload: dict[str, Any]) -> dict[str, Any]:
    """
    1. Odbiera dane HTTP z Data Service.
    2. Waliduje i normalizuje payload.
    3. Publikuje wiadomość do RabbitMQ (persistent – przeżyje restart brokera).
    4. Szybko odpowiada nadawcy.
    """
    global published_count

    if rmq_channel is None or rmq_channel.is_closed:
        raise HTTPException(status_code=503, detail="Broker niedostepny. Sprobuj pozniej.")

    normalized_message = normalize_payload(payload)

    await rmq_channel.default_exchange.publish(
        aio_pika.Message(
            body=json.dumps(normalized_message).encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        ),
        routing_key=QUEUE_NAME,
    )
    published_count += 1

    return {
        "status": "queued",
        "job_id": normalized_message["job_id"],
        "job_type": normalized_message["job_type"],
        "received_at": normalized_message["received_at"],
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)
