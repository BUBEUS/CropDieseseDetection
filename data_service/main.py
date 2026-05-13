from .send_data import DataSender
from .iot_generator import DataGenerator
from .drone_generator import DroneGenerator
import time



'''Pomysł jest taki, żeby uruchomić np 5 kontenerów'''


print("Uruchomiono Data Service...")

iot_generator = DataGenerator()
drone_generator = DroneGenerator()
data_sender = DataSender(target_url="http://data_acquisition:5000/data")

while True:
    # Generowanie danych IOT
    iot_generator.generate_measurement()
    iot_payload = iot_generator.get_iot_payload()

    # Generowanie danych z drona
    drone_generator.generate_photo(max_number=5)
    drone_payload = drone_generator.get_drone_payload()

    # Wysyłanie danych do Data Acquisition
    print("Wysyłanie danych IOT...")
    data_sender.send_data(iot_payload)

    print("Wysyłanie danych z drona...")
    data_sender.send_data(drone_payload)

    # Czekaj 5 sekund przed kolejnym cyklem
    time.sleep(5)