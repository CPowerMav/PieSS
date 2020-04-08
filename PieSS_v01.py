#Real time ISS tracker - www.101computing.net/real-time-ISS-tracker/

import json, urllib.request, time
from gpiozero import LED

#Define names for pinouts

LED_north = LED(17)
LED_east = LED(27)
LED_south = LED(22)
LED_west = LED(23)
LED_oneMin = LED(5)
LED_fiveMin = LED(6)
LED_tenMin = LED(13)

#Define variable names

momLatitude = 43.577090
momLongitude = -79.727520

"""
#For use later
#A first JSON request to retrieve the name of all the astronauts currently in space.
url = "http://api.open-notify.org/astros.json"
response = urllib.request.urlopen(url)
result = json.loads(response.read())
print("There are currently " + str(result["number"]) + " astronauts in space:")
print("")

people = result["people"]

for p in people:
  print(p["name"] + " on board of " + p["craft"])
"""

"""
this may be useful instead:
http://open-notify.org/Open-Notify-API/ISS-Pass-Times/
or
https://gist.github.com/rochacbruno/2883505
"""

while True:
  #A JSON request to retrieve the current longitude and latitude of the IIS space station (real time)  
  url = "http://api.open-notify.org/iss-now.json"
  response = urllib.request.urlopen(url)
  result = json.loads(response.read())
    
  #Let's extract the required information
  location = result["iss_position"]
  lat = location["latitude"]
  lon = location["longitude"]
    
  #Output information on screen
  print("\nLatitude: " + str(lat))
  print("Longitude: " + str(lon))
  
  #refresh position every 5 seconds
  time.sleep(5)


"""
#Adding a servo that raises a flag when it's time to go out and look at the sky
import RPi.GPIO as GPIO
from time import sleep

GPIO.setmode(GPIO.BOARD)
GPIO.setup(03, GPIO.OUT)
pwm=GPIO.PWM(03, 50)
pwm.start(0)

def SetAngle(angle):
	duty = angle / 18 + 2
	GPIO.output(03, True)
	pwm.ChangeDutyCycle(duty)
	sleep(1)
	GPIO.output(03, False)
	pwm.ChangeDutyCycle(0)


SetAngle(90) 
pwm.stop()
GPIO.cleanup()
"""
