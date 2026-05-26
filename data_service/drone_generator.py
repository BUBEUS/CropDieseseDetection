import random

PHOTO_FOLDER = "photos" #konwencja nazewnictwa photo_{number}.jpg

class DroneGenerator:
    def __init__(self):
        self.client_id = 0

        self.photo_number = 0
        self.latitude = 0.0
        self.longitude = 0.0
        self.altitude = 0.0

    def generate_photo(self, max_number=1):
        self.photo_number = random.randint(1, max_number)
        self.latitude = round(random.uniform(-90.0, 90.0), 6)
        self.longitude = round(random.uniform(-180.0, 180.0), 6)
        self.altitude = round(random.uniform(0.0, 10000.0), 2)


    def get_drone_payload(self):
        return {
            "client_id": self.client_id,
            "photo_number": self.photo_number,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "altitude": self.altitude
        }

