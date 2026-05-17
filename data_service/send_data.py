import requests


class DataSender:
    def __init__(self, target_url):
        self.target_url = target_url


    def send_data(self, payload):
        try:
            headers = {'Content-Type': 'application/json'}

            response = requests.post(self.target_url, json=payload, timeout=5)
            response.raise_for_status()  # Sprawdza, czy odpowiedź jest sukcesem (2xx)

            print(f"[SUKCES] Dane zostały wysłane do {self.target_url}. Odpowiedź serwera: {response.status_code}")
            return True

        except requests.exceptions.Timeout:
            print("[BŁĄD] Przekroczono czas oczekiwania (Timeout). Serwer Data Acquisition nie odpowiada.")
            return False
        except requests.exceptions.ConnectionError:
            print("[BŁĄD] Brak połączenia. Czy kontener Data Acquisition jest włączony?")
            return False
        except requests.exceptions.HTTPError as err:
            print(f"[BŁĄD] Serwer zwrócił błąd: {err}")
            return False