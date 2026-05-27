import random

'''Generuje losowe dane IOT'''

class DataGenerator:
    def __init__(self):
        self.client_id = 0
        self.identifier = 0

        self.temperature = 0.0
        self.humidity = 0
        self.pressure = 0

    def generate_measurement(self):
        self.identifier = random.randint(1, 20)
        self.client_id = random.randint(1, 20)
        self.temperature = round(random.uniform(-20.0, 40.0), 2)
        self.humidity = random.randint(0, 100)
        self.pressure = random.randint(950, 1050)

    def get_iot_payload(self):
        return {
            "type": "iot",
            "identifier": self.identifier,
            "client_id": self.client_id,
            "temperature": self.temperature,
            "humidity": self.humidity,
            "pressure": self.pressure
        }


