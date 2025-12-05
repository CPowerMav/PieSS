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
myServoUp = 530 # Servo duty time for flag raised
myServoDown = 1530 # Servo duty time for flag raised
flagUp = False

# API Configuration
currentLatitude = 43.577090
currentLongitude = -79.727520
currentAltitude = 128  # meters

# Timing configurations
API_CHECK_INTERVAL = 1800  # Check API every 30 minutes (in seconds)
ALERT_CHECK_INTERVAL = 5   # Check for alerts every 5 seconds
last_api_check = 0
cached_next_pass = None

def get_api_url():
    return (f"https://spotthestation.nasa.gov/trajectory_data.cfm?"
            f"latitude={currentLatitude}&longitude={currentLongitude}&"
            f"elevation={currentAltitude}&type=text&apikey={NASA_API_KEY}")

def parse_nasa_data(data):
    """Parse NASA's SpotTheStation data to find next pass"""
    try:
        lines = data.decode('utf-8').split('\n')
        current_time = time.time()
        
        for i in range(len(lines)):
            if "Maximum Elevation:" in lines[i]:
                date_str = lines[i-2].strip()
                pass_time = datetime.strptime(date_str, "%A %b %d, %Y %I:%M %p").replace(tzinfo=timezone.utc).timestamp()
                
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

def fetch_next_pass():
    """Fetch new prediction from NASA API"""
    try:
        req = urllib.request.urlopen(get_api_url())
        return parse_nasa_data(req.read())
    except Exception as ex:
        print(f"Error fetching NASA data: {str(ex)}")
        return None

def is_prediction_still_valid(pass_data):
    """Check if the cached prediction is still valid"""
    if not pass_data:
        return False
    
    current_time = time.time()
    
    # If the predicted pass time is in the past, it's invalid
    if pass_data["risetime"] < current_time:
        return False
        
    return True

# Alert functions remain the same
def AlertOne():
    print("Alert 1 triggered!")
    LED_tenMin.on()
    print("Ten minute light is on")

def AlertTwo():
    print("Alert 2 triggered!")
    LED_tenMin.off()
    LED_fiveMin.on()
    print("Five minute light is on")

def AlertThree(duration):
    print("Alert 3 triggered!")
    LED_fiveMin.off()
    LED_oneMin.on()
    print("One minute light is on")
    pi.set_servo_pulsewidth(myServo, myServoUp)
    sleep(1)
    pi.set_servo_pulsewidth(myServo, 0)
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
    pi.set_servo_pulsewidth(myServo, myServoDown)
    sleep(1)
    pi.set_servo_pulsewidth(myServo, 0)
    sleep(1)
    global flagUp
    flagUp = False

def CheckalertTimes(seconds, duration):
    minutes = seconds/60
    minutes = int(minutes)
    print("debug minutes: " + str(minutes))
    global alertOneTriggered, alertTwoTriggered, alertThreeTriggered, alerts

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

# turn on North LED to indicate the script is running
LED_north.on()

print(f"Starting ISS Tracker. Checking NASA API every {API_CHECK_INTERVAL/60} minutes.")

while True:
    current_time = time.time()
    
    # Check if we need to fetch new prediction data
    if (current_time - last_api_check >= API_CHECK_INTERVAL) or \
       (not is_prediction_still_valid(cached_next_pass)):
        print("\nFetching new prediction from NASA API...")
        cached_next_pass = fetch_next_pass()
        last_api_check = current_time
        
        if cached_next_pass:
            print(f"New prediction received for {time.strftime('%Y-%m-%d %I:%M:%S %p', time.localtime(cached_next_pass['risetime']))}")
    
    # Process current prediction and handle alerts
    if cached_next_pass:
        timeLeft = cached_next_pass["risetime"] - current_time
        
        # Check the remaining minutes against the alert times
        CheckalertTimes(timeLeft, cached_next_pass["duration"])
        
        # Display status
        print("\n=========[ Overhead ISS Pass ]==========")
        print(time.strftime("Next: %Y-%m-%d %I:%M:%S %p", time.localtime(cached_next_pass["risetime"])))
        print("Duration: " + str(cached_next_pass["duration"]) + " seconds")
        print("Time Left: " + str(int(timeLeft/60)) + " minutes")
        print(alerts)
        print("========================================")
    else:
        print("No upcoming passes found. Will check again soon.")
    
    sleep(ALERT_CHECK_INTERVAL)