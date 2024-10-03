import math , random
from math import radians, sin, cos, sqrt, atan2 
import requests
from fcm_django.models import FCMDevice
from firebase_admin.messaging import Message, WebpushConfig, WebpushNotification



def send_notification_fb(user_id, title, message, data):
    try:
        device = FCMDevice.objects.filter(user=user_id).last()
        result = device.send_message(title=title, body=message, data=data, sound=True)
        return result
    except Exception as e:
        print('exception in utils',str(e))
        pass


def generateOTP() :
 
    # Declare a digits variable 
    # which stores all digits
    digits = "0123456789"
    OTP = ""
 
   # length of password can be changed
   # by changing value in range
    for i in range(8) :
        OTP += digits[math.floor(random.random() * 10)]
 
    return OTP


def calculate_distance(lat1, lon1, lat2, lon2):
    # OpenStreetMap API URL
    url = f"https://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"

    # Send HTTP request to the OpenStreetMap API
    response = requests.get(url)
    data = response.json()

    # Extract the distance from the API response
    if "routes" in data and len(data["routes"]) > 0:
        distance = data["routes"][0]["distance"] / 1000  # Convert meters to kilometers
        return int(distance)

    return None



def haversine_distance(lat1, lon1, lat2, lon2):
    # Convert latitude and longitude from degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    # Radius of the Earth in kilometers (mean value)
    radius = 6371.0

    # Calculate the distance
    distance = radius * c

    return distance


