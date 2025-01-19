import json
import urllib.request
import time
from datetime import datetime, timezone
import pigpio
from gpiozero import LED
from os import system, getenv
from time import sleep
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API key from environment variable
NASA_API_KEY = getenv('NASA_API_KEY', 'DEMO_KEY')  # Falls back to DEMO_KEY if not found

# Rest of your code remains the same
LED_north = LED(5)
# ... (rest of your LED and servo configurations)

# Updated API Configuration
momLatitude = 43.577090
momLongitude = -79.727520
altitude = 128  # meters

# NASA Spot The Station API endpoint
def get_api_url():
    return (f"https://spotthestation.nasa.gov/trajectory_data.cfm?"
            f"latitude={momLatitude}&longitude={momLongitude}&"
            f"elevation={altitude}&type=text")

refreshTime = 5  # How often we check API in seconds

# Alerts
alertOne = 10  # minutes
alertTwo = 5
alertThree = 1

alertOneTriggered = False
alertTwoTriggered = False
alertThreeTriggered = False

alerts = ""

def parse_nasa_data(data):
    """Parse NASA's SpotTheStation data to find next pass"""
    try:
        # Split into lines and find next valid sighting
        lines = data.decode('utf-8').split('\n')
        current_time = time.time()
        
        for i in range(len(lines)):
            if "Maximum Elevation:" in lines[i]:
                # Extract date from 2 lines before
                date_str = lines[i-2].strip()
                # Convert date string to epoch time
                pass_time = datetime.strptime(date_str, "%A %b %d, %Y %I:%M %p").replace(tzinfo=timezone.utc).timestamp()
                
                # Extract duration from next line (usually contains "Duration: xx minutes")
                duration_line = lines[i+1]
                duration_mins = int(''.join(filter(str.isdigit, duration_line)))
                duration_secs = duration_mins * 60
                
                if pass_time > current_time:
                    return {
                        "duration": duration_secs,
                        "risetime": int(pass_time)
                    }
    except Exception as e:
        print(f"Error parsing NASA data: {str(e)}")
        return None
    
    return None

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

def AlertThree(duration):
    print("Alert 3 triggered!")
    LED_fiveMin.off()
    LED_oneMin.on()
    print("One minute light is on")
    pi.set_servo_pulsewidth(myServo, myServoUp)  # flag raised
    sleep(1)
    pi.set_servo_pulsewidth(myServo, 0)  # flag motor off
    sleep(1)
    global flagUp
    flagUp = True
    print("flag is up")
    sleep(duration)
    Reset()

def Reset():
    print("resetting")
    LED_tenMin.off()
    LED_fiveMin.off()
    LED_oneMin.off()
    LED_east.off()
    LED_south.off()
    LED_west.off()
    pi.set_servo_pulsewidth(myServo, myServoDown)  # flag down
    sleep(1)
    pi.set_servo_pulsewidth(myServo, 0)  # flag motor off
    sleep(1)
    global flagUp
    flagUp = False

def CheckalertTimes(seconds, duration):
    minutes = seconds/60
    minutes = int(minutes)
    print("debug minutes: " + str(minutes))
    global alertOneTriggered
    global alertTwoTriggered
    global alertThreeTriggered
    global alerts

    if minutes <= alertOne and minutes > alertTwo:
        if not alertOneTriggered:
            alertOneTriggered = True
            alerts = f"Alerts:  {alertOne}m [X]  {alertTwo}m [ ]  {alertThree}m [ ]"
            AlertOne()
    elif minutes <= alertTwo and minutes > alertThree:
        if not alertTwoTriggered:
            alertTwoTriggered = True
            alerts = f"Alerts:  {alertOne}m [X]  {alertTwo}m [X]  {alertThree}m [ ]"
            AlertTwo()
    elif minutes <= alertThree and minutes >= 0:
        if not alertThreeTriggered:
            alertThreeTriggered = True
            alerts = f"Alerts:  {alertOne}m [X]  {alertTwo}m [X]  {alertThree}m [X] \nISS Overhead is coming in {minutes*60} seconds"
            AlertThree(duration)
    else:
        alertOneTriggered = False
        alertTwoTriggered = False
        alertThreeTriggered = False
        alerts = f"Alerts:  {alertOne}m [ ]  {alertTwo}m [ ]  {alertThree}m [ ]"

def Error(e):
    print("ERROR: " + e)

# turn on North LED to indicate the script is running
LED_north.on()

while True:
    try:
        # Get data from NASA API
        req = urllib.request.urlopen(get_api_url())
        next_pass = parse_nasa_data(req.read())
        
        if next_pass:
            duration = next_pass["duration"]
            risetime = next_pass["risetime"]
            
            # Get current time (epoch time)
            currentTime = int(time.time())
            timeLeft = risetime - currentTime
            
            # Check the remaining minutes against the alert times
            CheckalertTimes(timeLeft, duration)
            
            # Formatted output to view
            print("")
            print("=========[ Overhead ISS Pass ]==========")
            print(time.strftime("Next: %Y-%m-%d %I:%M:%S %p", time.localtime(risetime)))
            print("Duration: " + str(duration) + " seconds")
            print("Time Left: " + str(int(timeLeft/60)) + " minutes")
            print(alerts)
            print("========================================")
        else:
            print("No upcoming passes found in the next few days")
            
    except Exception as ex:
        Error(str(ex))
        pass
    
    time.sleep(refreshTime)

