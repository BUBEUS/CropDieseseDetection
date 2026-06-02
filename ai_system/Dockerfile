FROM python:3.13-slim

WORKDIR /app

RUN pip install --no-cache-dir requests psycopg2-binary pika

COPY . .

CMD ["python", "-u", "ai_system.py"]
