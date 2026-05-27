FROM python:3.13-slim

WORKDIR /app

# Instalujemy tylko to, czego potrzebuje serwis Data Acquisition.
RUN pip install --no-cache-dir fastapi "uvicorn[standard]"

# Kopiujemy plik aplikacji do kontenera.
COPY . .

EXPOSE 5000

# Start serwera HTTP odbierajacego dane od Data Service.
CMD ["uvicorn", "acquire_data:app", "--host", "0.0.0.0", "--port", "5000"]
