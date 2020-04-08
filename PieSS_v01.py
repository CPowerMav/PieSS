
#  Overhead is defined as 10 degrees in elevation for the observer.
#  The times are computed in UTC and the length of time that the ISS is above 10 degrees is in seconds.
#  Epoch time: https://www.epochconverter.com

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
altitude = 128

url = "http://api.open-notify.org/iss-pass.json?lat={lat}&lon={long}&alt={a}".format(lat=momLatitude, long=momLongitude, a=altitude)

# Compare minutes against time remaining for alerts
alertOne = 10
alertTwo = 5
alertThree = 1

# Triggers so we dont have the alert go over multiple times
alertOneTriggered = False
alertTwoTriggered = False
alertThreeTriggered = False

alerts = ""

# How often we check API
refreshTime = 5


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

# Check if an alert has been triggered against the remaining time in minutes
def CheckalertTimes(seconds):
  minutes = seconds/60
  minutes = int(minutes)
  
  global alertOneTriggered
  global alertTwoTriggered
  global alertThreeTriggered
  global alerts

  if minutes <= alertOne and minutes > alertTwo:
      if alertOneTriggered is False:
        alertOneTriggered = True
        alerts = "Alerts:  {one}m [X]  {two}m [ ]  {three}m [ ]".format(one=alertOne, two=alertTwo, three=alertThree)
  elif minutes <= alertTwo and minutes > alertThree:
      if alertTwoTriggered is False:
        alertTwoTriggered = True
        alerts = "Alerts:  {one}m [X]  {two}m [X]  {three}m [ ]".format(one=alertOne, two=alertTwo, three=alertThree)
  elif minutes <= alertThree:
      if alertThreeTriggered is False:
        alertThreeTriggered = True
        alerts = "Alerts:  {one}m [X]  {two}m [X]  {three}m [X] \nIIS Overhead is coming in " + str(minutes*60) + " seconds, hold your butts!".format(one=alertOne, two=alertTwo, three=alertThree)
  else:
     alertOneTriggered = False
     alertTwoTriggered = False
     alertThreeTriggered = False
     # print("IIS is " + str(int(minutes)) + " minutes away")
     alerts = "Alerts:  {one}m [ ]  {two}m [ ]  {three}m [ ]".format(one=alertOne, two=alertTwo, three=alertThree)

# Display progress on LCD(16)
def ShowLCD(tLeft, dur):
  value = int(tLeft / 60) # convert time to minutes
  #value -= 183 # Use this to create an offset in minutes to test the data (if 20 mins are left, value -= 4 = 16 mins left)
  if 16 >= value: # if each chararacter on the LCD is 1, if there is less than 16 minutes left, show updates
    print(str(value))
    LCDDisplay = "================" # number of characters match LCD
    invertValue = 16 - value
    LCDDisplay = LCDDisplay[:invertValue] + "0" + LCDDisplay[invertValue+1:]
    print (str(LCDDisplay))

  if value == 0: # if it's less than 1 minute, display message
    LCDDisplay = "ISS IS OVERHEAD!"
    print (str(LCDDisplay))


while True:
  #Get JSON data
  req = urllib.request.urlopen(url)
  resp = json.loads(req.read())
  # print("\nResponse: " + str(resp))

  # Matches the 'iss-pass.json' json structure
  request = resp["request"]
  latitude = request["latitude"]
  longitude = request["longitude"]
  altitude = request["altitude"]
  datetime = request["datetime"] # generated time, not current - helps if we can't get current time on a device
  
  # Get first overhead response
  response = resp["response"]
  # we're only grabbing the first index ('0') because we only need to see the next upcoming pass
  duration = response[0]["duration"] 
  risetime = response[0]["risetime"]

  # This will list all your response/passes if you have a need later
  # but will have to store them in objects
  # for r in response:
  #   print ("response: "+str(r))

  # values sent, we can use to confirm they come back correctly
  # print("\nLat: " + str(latitude))
  # print("\nLong: " + str(longitude))
  # print("\nAlt: " + str(altitude))

  # Get current time (epoch time)
  currentTime = int(time.time())
  timeLeft = risetime - currentTime

  # Check the remaining minutes against the alert times
  CheckalertTimes(timeLeft)

  # Formatted output to view
  print ("")
  print ("=========[ Overhead ISS Pass ]==========")
  print(time.strftime("Next: %Y-%m-%d %I:%M:%S %p", time.localtime(risetime)))
  print ("Duration: " + str(duration) + " seconds")
  print("Time Left: " + str(int(timeLeft/60)) + " minutes")
  print(alerts)
  print ("=========================================")

  ShowLCD(timeLeft, duration)
      

  time.sleep(refreshTime)   

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
