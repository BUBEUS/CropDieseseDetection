from .send_data import DataSender
from .iot_generator import DataGenerator
from .drone_generator import DroneGenerator
import time
import random



'''Pomysł jest taki, żeby uruchomić np 5 kontenerów Data Service, każdy losowe dane IOT i z drona np do 10 różnych klientów'''

print("Uruchomiono Data Service...")

iot_generator = DataGenerator()
drone_generator = DroneGenerator()
data_sender = DataSender(target_url="http://data_acquisition:5000/data")

#takich pętli powiedzmy będzie działało z 5 próbując dać dane do kolejki imitując wysyłanie od różnych klientów
while True:
    attempts = 0
    max_attempts = 5
    wait_time = 2

    if random.random() < 0.7:
        # Generowanie danych IOT
        iot_generator.generate_measurement()
        iot_payload = iot_generator.get_iot_payload()

        while attempts < max_attempts:
            if data_sender.send_data(iot_payload):
                print("Wysyłanie danych IOT...")
                break
            attempts += 1
            print(f"Ponawianie próby {attempts}/{max_attempts} za {wait_time}s...")
            time.sleep(wait_time)
            wait_time*= 2

    else:
        # Generowanie danych z drona
        drone_generator.generate_photo(max_number=5)
        drone_payload = drone_generator.get_drone_payload()

        while attempts < max_attempts:
            if data_sender.send_data(drone_payload):
                print("Wysyłanie danych z drona...")
                break
            attempts += 1
            print(f"Ponawianie próby {attempts}/{max_attempts} za {wait_time}s...")
            time.sleep(wait_time)
            wait_time*= 2


    # Czekaj 5 sekund przed kolejnym cyklem
    time.sleep(5)


