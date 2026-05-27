
'''
Odbiór: Przyjęcie połączenia HTTP/HTTPS.

Normalizacja: Przekształcenie danych do standardu, który rozumie Twoja kolejka.

Publikacja: Wysłanie wiadomości do brokera (np. RabbitMQ/Kafka).

Potwierdzenie: Zwrócenie szybkiej odpowiedzi do nadawcy, by mógł wysłać kolejną paczkę.
'''

from collections import deque
from datetime import datetime, timezone
from threading import Lock
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException


app = FastAPI(title="Data Acquisition System")

# FIFO w pamieci pelni tutaj role uproszczonego brokera danych.
# Dzieki temu Data Service dostaje szybkie potwierdzenie, a AI moze pobrac
# zadanie w osobnym kroku bez blokowania odbioru kolejnych pomiarow.
message_queue: deque[dict[str, Any]] = deque()
queue_lock = Lock()
job_sequence = 0


def _utc_timestamp() -> str:
    """Zwraca znacznik czasu w ISO 8601, aby wszystkie uslugi mialy ten sam format."""
    return datetime.now(timezone.utc).isoformat()


def _next_job_id() -> int:
    """Nadaje kolejne id zadania, zeby mozna bylo sledzic przeplyw danych."""
    global job_sequence
    with queue_lock:
        job_sequence += 1
        return job_sequence


def _require_fields(payload: dict[str, Any], required_fields: list[str]) -> None:
    """Sprawdza, czy nadawca przeslal wszystkie pola wymagane dla danego typu danych."""
    missing_fields = [field for field in required_fields if field not in payload]
    if missing_fields:
        raise HTTPException(
            status_code=400,
            detail=f"Brakuje wymaganych pol: {', '.join(missing_fields)}",
        )


def _normalize_iot_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Zamienia surowy pomiar IoT na wspolny format zadania dla kolejki."""
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
    """Buduje ustandaryzowany opis obserwacji z drona, gotowy do analizy obrazu."""
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
    """
    Tworzy wspolny model wiadomosci.
    Data Service moze wysylac rozne typy danych, ale kolejka i AI powinny
    dostac jeden przewidywalny format.
    """
    payload_type = payload.get("type")

    if payload_type == "iot":
        return _normalize_iot_payload(payload)
    if payload_type == "drone":
        return _normalize_drone_payload(payload)

    raise HTTPException(
        status_code=400,
        detail="Nieznany typ danych. Oczekiwano 'iot' albo 'drone'.",
    )


def enqueue_message(message: dict[str, Any]) -> int:
    """Dodaje zadanie do kolejki i zwraca aktualny rozmiar bufora."""
    with queue_lock:
        message_queue.append(message)
        return len(message_queue)


def dequeue_message() -> dict[str, Any] | None:
    """Pobiera najstarsze zadanie z kolejki zgodnie z zasada FIFO."""
    with queue_lock:
        if not message_queue:
            return None
        return message_queue.popleft()


@app.get("/health")
def healthcheck() -> dict[str, Any]:
    """Prosty endpoint do sprawdzenia, czy serwis dziala."""
    with queue_lock:
        queue_size = len(message_queue)

    return {
        "status": "ok",
        "service": "data_acquisition",
        "queue_size": queue_size,
        "timestamp": _utc_timestamp(),
    }


@app.get("/queue/status")
def queue_status() -> dict[str, Any]:
    """Zwraca rozmiar kolejki, aby latwiej obserwowac przeplyw danych."""
    with queue_lock:
        queue_size = len(message_queue)
        next_job = message_queue[0]["job_id"] if message_queue else None

    return {
        "queue_size": queue_size,
        "next_job_id": next_job,
        "timestamp": _utc_timestamp(),
    }


@app.post("/data")
def receive_data(payload: dict[str, Any]) -> dict[str, Any]:
    """
    1. Odbiera dane HTTP z Data Service.
    2. Waliduje i normalizuje payload.
    3. Odkalda wiadomosc do kolejki.
    4. Szybko odpowiada nadawcy, zeby mogl wysylac kolejne pakiety.
    """
    normalized_message = normalize_payload(payload)
    queue_size = enqueue_message(normalized_message)

    return {
        "status": "queued",
        "job_id": normalized_message["job_id"],
        "job_type": normalized_message["job_type"],
        "queue_size": queue_size,
        "received_at": normalized_message["received_at"],
    }


@app.get("/broker/next")
def get_next_message() -> dict[str, Any]:
    """
    Uproszczony interfejs brokera.
    AI System moze pobierac kolejne zadania z kolejki do dalszej analizy.
    """
    message = dequeue_message()
    if message is None:
        raise HTTPException(status_code=404, detail="Kolejka jest pusta.")

    return {
        "status": "dispatched",
        "message": message,
        "dispatched_at": _utc_timestamp(),
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)
