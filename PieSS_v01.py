#  Overhead is defined as 10 degrees in elevation for the observer.
#  The times are computed in UTC and the length of time that the ISS is above 10 degrees is in seconds.
#  Epoch time: https://www.epochconverter.com

import json, urllib.request, time, pigpio
from gpiozero import LED
from os import system
from time import sleep

#Define variable names for pinouts

# LED
LED_north = LED(5)
LED_east = LED(6)
LED_south = LED(13)
LED_west = LED(12)
LED_oneMin = LED(17)
LED_fiveMin = LED(27)
LED_tenMin = LED(22)

# Servo
pi = pigpio.pi()

myServo = 16
myServoUp = 2000 # Servo duty time for flag raised
myServoDown = 1000 # Servo duty time for flag raised
flagUp = False

# API
momLatitude = 43.577090
momLongitude = -79.727520
altitude = 128
url = "http://api.open-notify.org/iss-pass.json?lat={lat}&lon={long}&alt={a}".format(lat=momLatitude, long=momLongitude, a=altitude)
refreshTime = 10 # How often we check API

#Alerts
# Compare minutes against time remaining for alerts
alertOne = 10
alertTwo = 5
alertThree = 1

# Triggers so we dont have the alert go over multiple times
alertOneTriggered = False
alertTwoTriggered = False
alertThreeTriggered = False

alerts = ""

# activate piGpio daemon
# system("sudo pigpiod")

#Alerts - put logic here
def AlertOne():
  print("Alert 1 triggered!")
  LED_tenMin.on()
  print("Ten minute light is on")
  
def AlertTwo():
  print("Alert 2 triggered!")
  LED_tenMin.off()
  print("Ten minute light is off")
  LED_fiveMin.on()
  print("Five minute light is on")
    
def AlertThree():
  print("Alert 3 triggered!")
  LED_fiveMin.off()
  LED_oneMin.on()
  print("One minute light is on")
  pi.set_servo_pulsewidth(myServo, myServoUp) # flag raised
  sleep(1)
  pi.set_servo_pulsewidth(myServo, 0) # flag motor off
  sleep(1)
  flagUp = True
  print("flag is up")

#reset everything back to default!
def Reset():
  print("resetting")
  LED_tenMin.off()
  LED_fiveMin.off()
  LED_oneMin.off()
  LED_north.off()
  LED_east.off()
  LED_south.off()
  LED_west.off()
  pi.set_servo_pulsewidth(myServo, myServoDown) # flag raised
  sleep(1)
  pi.set_servo_pulsewidth(myServo, 0) # flag motor off
  sleep(1)
  flagUp = False
    
# Check if an alert has been triggered against the remaining time in minutes
def CheckalertTimes(seconds):
  minutes = seconds/60
  minutes = int(minutes)
  # minutes -= 652 # This is an offest for testing
  print("debug minutes: " + str(minutes))
  global alertOneTriggered
  global alertTwoTriggered
  global alertThreeTriggered
  global alerts

  if minutes <= alertOne and minutes > alertTwo:
      if alertOneTriggered is False:
        alertOneTriggered = True
        alerts = "Alerts:  {one}m [X]  {two}m [ ]  {three}m [ ]".format(one=alertOne, two=alertTwo, three=alertThree)
        AlertOne()
  elif minutes <= alertTwo and minutes > alertThree:
      if alertTwoTriggered is False:
        alertTwoTriggered = True
        alerts = "Alerts:  {one}m [X]  {two}m [X]  {three}m [ ]".format(one=alertOne, two=alertTwo, three=alertThree)
        AlertTwo()
  elif minutes <= alertThree and minutes >= 0:
      if alertThreeTriggered is False:
        alertThreeTriggered = True
        alerts = "Alerts:  {one}m [X]  {two}m [X]  {three}m [X] \nIIS Overhead is coming in ".format(one=alertOne, two=alertTwo, three=alertThree) + str(minutes*60) + " seconds"
        AlertThree()
  else:
     alertOneTriggered = False
     alertTwoTriggered = False
     alertThreeTriggered = False
     alerts = "Alerts:  {one}m [ ]  {two}m [ ]  {three}m [ ]".format(one=alertOne, two=alertTwo, three=alertThree)
     # print("IIS is " + str(int(minutes)) + " minutes away")
     
"""

# Display progress on LCD(16) - Future feature
def ShowLCD(tLeft, dur):
  value = int(tLeft / 60) # convert time to minutes
  value -= 159 # Use this to create an offset in minutes to test the data (if 20 mins are left, value -= 4 = 16 mins left)
  if 16 >= value: # if each chararacter on the LCD is 1, if there is less than 16 minutes left, show updates
    LCDDisplay = "================" # number of characters match LCD
    invertValue = 16 - value
    LCDDisplay = LCDDisplay[:invertValue] + "0" + LCDDisplay[invertValue+1:]
    print (str(LCDDisplay))

  if value == 0: # if it's less than 1 minute, display message
    LCDDisplay = "Overhead {secs} Sec".format(secs=dur)
    print (str(LCDDisplay))

"""

while True:
  #Get JSON data
  req = urllib.request.urlopen(url)
  resp = json.loads(req.read())
  # print("\nResponse: " + str(resp))

  # Matches the 'iss-pass.json' json structure
  request = resp["request"] # why is this one resp?
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
  print("")
  print("=========[ Overhead ISS Pass ]==========")
  print(time.strftime("Next: %Y-%m-%d %I:%M:%S %p", time.localtime(risetime)))
  print("Duration: " + str(duration) + " seconds")
  print("Time Left: " + str(int(timeLeft/60)) + " minutes")
  print(alerts)
  print("========================================")
  # ShowLCD(timeLeft, duration)

  checktime = int(timeLeft/60)
  # print (checktime)
  if checktime == 0:
    print ("is flag up?" + flagUp)
    if flagUp is True:
      Reset()

  time.sleep(refreshTime)   

"""
GPIO.cleanup() # need this somewhere?
"""
