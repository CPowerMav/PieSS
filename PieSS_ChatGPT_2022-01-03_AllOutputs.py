# ChatGPT_Trial_01:


import requests
import json
import time
import math
import RPi.GPIO as GPIO

# Set the GPIO pin numbers for the LEDs and the servo motor
LED_10_MINUTES = 18
LED_5_MINUTES = 23
LED_1_MINUTE = 24
SERVO_MOTOR = 25

# Set the GPIO pin mode
GPIO.setmode(GPIO.BCM)

# Set the pin numbers for the LEDs as outputs
GPIO.setup(LED_10_MINUTES, GPIO.OUT)
GPIO.setup(LED_5_MINUTES, GPIO.OUT)
GPIO.setup(LED_1_MINUTE, GPIO.OUT)

# Set the pin number for the servo motor as an output
GPIO.setup(SERVO_MOTOR, GPIO.OUT)

# Set the longitude and latitude of your location
latitude = 37.7749
longitude = -122.4194

# Set the URL for the OpenNotify ISS Location API
url = "http://api.open-notify.org/iss-now.json"

# Set the frequency of the servo motor (in Hz)
frequency = 50

# Set the minimum and maximum pulse widths for the servo motor
min_pulse_width = 0.0005
max_pulse_width = 0.0024

# Set the pulse width range and center
pulse_range = max_pulse_width - min_pulse_width
pulse_center = min_pulse_width + pulse_range / 2

# Set the maximum angle of the servo motor
max_angle = 180

# Set the minimum and maximum elevations (in degrees) for the ISS to be visible from your location
min_elevation = 0
max_elevation = 10

# Set the radius of the Earth (in meters)
earth_radius = 6371e3

# Create a PWM instance for the servo motor
pwm = GPIO.PWM(SERVO_MOTOR, frequency)

# Start the PWM with a 0% duty cycle (0 degrees)
pwm.start(0)

def get_iss_location():
  """Get the current location of the ISS."""
  try:
    # Send a GET request to the OpenNotify ISS Location API
    response = requests.get(url)

    # If the request is successful
    if response.status_code == 200:
      # Parse the response as JSON
      data = json.loads(response.content.decode())

      # Get the ISS location from the response
      iss_location = data['iss_position']

      # Get the latitude and longitude of the ISS
      iss_latitude = float(iss_location['latitude'])
      iss_longitude = float(iss_location['longitude'])

      # Return the ISS latitude and longitude
      return (iss_latitude, iss_longitude)
    else:
      # If the request is unsuccessful, print an error message
      print(f"Error: {response.status_code}")
  except:
    # If there is an error, print an error message
    print("Error: Could not get ISS location")






# ChatGPT_Trial_02:

import requests
import json
import time
import math
import pigpio

# Set the GPIO pin number for the servo motor
SERVO_MOTOR_GPIO = 25

# Set the minimum and maximum pulse widths for the servo motor
min_pulse_width = 500
max_pulse_width = 2500

# Set the pulse width range and center
pulse_range = max_pulse_width - min_pulse_width
pulse_center = min_pulse_width + pulse_range / 2

# Set the maximum angle of the servo motor
max_angle = 180

# Set the minimum and maximum elevations (in degrees) for the ISS to be visible from your location
min_elevation = 0
max_elevation = 10

# Set the radius of the Earth (in meters)
earth_radius = 6371e3

# Connect to the pigpiod daemon
pi = pigpio.pi()

def set_servo_angle(angle):
  """Set the angle of the servo motor."""
  # Calculate the pulse width for the desired angle
  pulse_width = min_pulse_width + (angle / max_angle) * pulse_range

  # Set the servo pulse width
  pi.set_servo_pulsewidth(SERVO_MOTOR_GPIO, pulse_width)

def get_iss_elevation(latitude, longitude):
  """Get the elevation of the ISS above the horizon (in degrees) at the given latitude and longitude."""
  try:
    # Send a GET request to the OpenNotify ISS Pass API
    response = requests.get(f"http://api.open-notify.org/iss-pass.json?lat={latitude}&lon={longitude}")

    # If the request is successful
    if response.status_code == 200:
      # Parse the response as JSON
      data = json.loads(response.content.decode())

      # Get the response data
      response_data = data['response'][0]

      # Get the duration of the pass (in seconds)
      duration = response_data['duration']

      # Calculate the elevation of the ISS (in degrees)
      elevation = 90 - math.degrees(math.acos(earth_radius / (earth_radius + response_data['risetime'])))

      # Return the elevation and duration of the pass
      return (elevation, duration)
    else:
      # If the request is unsuccessful, print an error message
      print(f"Error: {response.status_code}")
  except:
    # If there is an error, print an error message
    print("Error: Could not get ISS elevation")

def get_iss_azimuth(latitude, longitude):
  """Get the azimuth of the ISS (in degrees) at the given latitude and longitude."""
  # Get the current location of the ISS
  iss_location = get_iss_location()

  # If the ISS location was successfully retrieved
  if iss_location:
    # Unpack the ISS latitude and longitude
    iss_latitude, iss_longitude = iss_location

    # Convert the ISS latitude and longitude to radians
    iss_latitude_rad = math.radians(iss_latitude)
    iss_longitude_rad = math.radians(iss_longitude)
    latitude_rad = math.radians(latitude)
    longitude_rad = math.radians(longitude)

    # Calculate the azimuth of the ISS (in radians)
    azimuth = math.atan2(
      math.sin(iss_longitude_rad - longitude_rad) * math.cos(iss_latitude_rad),
      math.cos(latitude_rad) * math.sin(iss_latitude_rad) - math.sin(latitude_rad) * math.cos(iss_latitude_rad) * math.cos(iss_longitude_rad - longitude_rad)
    )

    # Convert the azimuth to degrees
    azimuth = math.degrees(azimuth)

    # Normalize the azimuth to a value between 0 and 360 degrees
    if azimuth < 0:
      azimuth += 360

    # Return the azimuth
    return azimuth

def get_iss_direction(azimuth):
  """Get the direction (north, east, south, or west) that the ISS is located based on the given azimuth."""
  if azimuth >= 337.5 or azimuth < 22.5:
    return "north"
  elif azimuth >= 22.5 and azimuth < 67.5:
    return "east"
  elif azimuth >= 67.5 and azimuth < 112.5:
    return "south"
  elif azimuth >= 112.5 and azimuth < 157.5:
    return "west"
  elif azimuth >= 157.5 and azimuth < 202.5:
    return "north"
  elif azimuth >= 202.5 and azimuth < 247.5:
    return "east"
  elif azimuth >= 247.5 and azimuth < 292.5:
    return "south"
  elif azimuth >= 292.5 and azimuth < 337.5:
    return "west"

def is_iss_visible(latitude, longitude):
  """Check if the ISS is currently visible at the given latitude and longitude."""
  # Get the elevation of the ISS at the given latitude and longitude
  elevation = get_iss_elevation(latitude, longitude)

  # If the elevation was successfully retrieved
  if elevation:
    # Unpack the elevation and duration of the pass
    elevation, duration = elevation

    # If the ISS is above the minimum elevation and below the maximum elevation
    if elevation > min_elevation and elevation < max_elevation:
      return True
    else:
      return False
  else:
    return False

def notify(minutes):
  """Notify the user that the ISS will be visible in the given number of minutes."""
  # Turn on the appropriate LED
  if minutes == 10:
    GPIO.output(LED_10_MINUTES, True)
  elif minutes == 5:
    GPIO.output(LED_5_MINUTES, True)
  elif minutes == 1:
    GPIO.output(LED_1_MINUTE, True)

def main():
  # Set the initial state of the LEDs to off
  GPIO.output(LED_10_MINUTES, False)
  GPIO.output(LED_5_MINUTES, False)
  GPIO.output(LED_1_MINUTE, False)

  # Set the initial angle of the servo motor to 0 degrees
  set_servo_angle(0)

  while True:
    # Get the current location of the ISS
    iss_location = get_iss_location()

    # If the ISS location was successfully retrieved
    if iss_location:
      # Unpack the ISS latitude and longitude
      iss_latitude, iss_longitude = iss_location

      # Get the azimuth of the ISS at the user's location
      azimuth = get_iss_azimuth(latitude, long
     
      # Get the direction that the ISS is located
      direction = get_iss_direction(azimuth)

      # Print the direction that the ISS is located
      print(f"ISS Direction: {direction}")

      # Check if the ISS is currently visible at the user's location
      iss_visible = is_iss_visible(latitude, longitude)

      # If the ISS is visible
      if iss_visible:
        # Turn on the servo motor
        set_servo_angle(max_angle)

        # Turn off the LEDs
        GPIO.output(LED_10_MINUTES, False)
        GPIO.output(LED_5_MINUTES, False)
        GPIO.output(LED_1_MINUTE, False)
      else:
        # Get the elevation and duration of the next pass of the ISS at the user's location
        next_pass = get_iss_elevation(latitude, longitude)

        # If the next pass was successfully retrieved
        if next_pass:
          # Unpack the elevation and duration of the pass
          elevation, duration = next_pass

          # Calculate the time until the next pass (in minutes)
          time_until_next_pass = duration / 60

          # If the time until the next pass is greater than or equal to 10 minutes
          if time_until_next_pass >= 10:
            # Notify the user that the ISS will be visible in 10 minutes
            notify(10)
          # If the time until the next pass is greater than or equal to 5 minutes
          elif time_until_next_pass >= 5:
            # Notify the user that the ISS will be visible in 5 minutes
            notify(5)
          # If the time until the next pass is greater than or equal to 1 minute
          elif time_until_next_pass >= 1:
            # Notify the user that the ISS will be visible in 1 minute
            notify(1)

        # If the next pass was not successfully retrieved
        else:
          # Turn off the LEDs
          GPIO.output(LED_10_MINUTES, False)
          GPIO.output(LED_5_MINUTES, False)
          GPIO.output(LED_1_MINUTE, False)

        # Turn off the servo motor
        set_servo_angle(0)

    # Sleep for 1 second
    time.sleep(1)

# If the script is run directly
if __name__ == "__main__":
  try:
    # Run the main function
    main()
  except KeyboardInterrupt:
    # When the user presses Ctrl+C, clean up the GPIO pins and exit
    GPIO.cleanup()
    exit()




# ChatGPT_Trial_03:

      # Get the direction that the ISS is located
      direction = get_iss_direction(azimuth)

      # Print the direction that the ISS is located
      print(f"ISS Direction: {direction}")

      # Check if the ISS is currently visible at the user's location
      iss_visible = is_iss_visible(latitude, longitude)

      # If the ISS is visible
      if iss_visible:
        # Turn on the servo motor
        set_servo_angle(max_angle)

        # Turn off the LEDs
        GPIO.output(LED_10_MINUTES, False)
        GPIO.output(LED_5_MINUTES, False)
        GPIO.output(LED_1_MINUTE, False)
      else:
        # Get the elevation and duration of the next pass of the ISS at the user's location
        next_pass = get_iss_elevation(latitude, longitude)

        # If the next pass was successfully retrieved
        if next_pass:
          # Unpack the elevation and duration of the pass
          elevation, duration = next_pass

          # Calculate the time until the next pass (in minutes)
          time_until_next_pass = duration / 60

          # If the time until the next pass is greater than or equal to 10 minutes
          if time_until_next_pass >= 10:
            # Notify the user that the ISS will be visible in 10 minutes
            notify(10)
          # If the time until the next pass is greater than or equal to 5 minutes
          elif time_until_next_pass >= 5:
            # Notify the user that the ISS will be visible in 5 minutes
            notify(5)
          # If the time until the next pass is greater than or equal to 1 minute
          elif time_until_next_pass >= 1:
            # Notify the user that the ISS will be visible in 1 minute
            notify(1)

        # If the next pass was not successfully retrieved
        else:
          # Turn off the LEDs
          GPIO.output(LED_10_MINUTES, False)
          GPIO.output(LED_5_MINUTES, False)
          GPIO.output(LED_1_MINUTE, False)

        # Turn off the servo motor
        set_servo_angle(0)

    # Sleep for 1 second
    time.sleep(1)

# If the script is run directly
if __name__ == "__main__":
  try:
    # Run the main function
    main()
  except KeyboardInterrupt:
    # When the user presses Ctrl+C, clean up the GPIO pins and exit
    GPIO.cleanup()
    exit()




# ChatGPT_Trial_04:

import math
import time
import requests
import json
import RPi.GPIO as GPIO
import pigpio

# Set the OpenNotify ISS Location API URL
url = "http://api.open-notify.org/iss-now.json"

# Set the GPIO pin numbers for the LEDs
LED_10_MINUTES = 17
LED_5_MINUTES = 27
LED_1_MINUTE = 22

# Set the GPIO pin number for the servo motor
SERVO_MOTOR_GPIO = 25

# Set the minimum and maximum pulse widths for the servo motor
min_pulse_width = 500
max_pulse_width = 2500

# Set the pulse width range and center
pulse_range = max_pulse_width - min_pulse_width
pulse_center = min_pulse_width + pulse_range / 2

# Set the maximum angle of the servo motor
max_angle = 180

# Set the minimum and maximum elevations (in degrees) for the ISS to be visible from your location
min_elevation = 0
max_elevation = 10

# Set the latitude and longitude of your location
latitude = 37.4848
longitude = -122.148

# Set the radius of the Earth (in meters)
earth_radius = 6371e3

# Use the BCM pin numbering scheme
GPIO.setmode(GPIO.BCM)

# Set the GPIO pins for the LEDs to output mode
GPIO.setup(LED_10_MINUTES, GPIO.OUT)
GPIO.setup(LED_5_MINUTES, GPIO.OUT)
GPIO.setup(LED_1_MINUTE, GPIO.OUT)

# Connect to the pigpiod daemon
pi = pigpio.pi()

def set_servo_angle(angle):
  """Set the angle of the servo motor."""
  # Calculate the pulse width for the desired angle
  pulse_width = min_pulse_width + (angle / max_angle) * pulse_range

  # Set the servo pulse width
  pi.set_servo_pulsewidth(SERVO_MOTOR_GPIO, pulse_width)

def get_iss_location():
  """Get the current location of the ISS."""
  try:
    # Send a GET request to the OpenNotify ISS Location API
    response = requests.get(url)

    # If the request is successful
    if response.status_code == 200:
      # Parse the response as JSON
      data = json.loads(response.content.decode())

      # Get the ISS location from the response
      iss_location = data['iss_position']

      # Get the latitude and longitude of the ISS
      iss_latitude = float(iss_location['latitude'])
      iss_longitude = float(iss_location['longitude'])

      # Return the ISS latitude and longitude
      return (iss_latitude, iss_longitude)
    else:
      # If the request is unsuccessful, print an error message
      print(f"Error: {response.status_code}")
  except:
    # If there is an error, print an error






# ChatGPT_Trial_05:

import pigpio
import time

from iss import ISS
from geolocation import get_location

# Constants for servo duty times
SERVO_MIN = 1530
SERVO_MAX = 530

# Constants for LED pin numbers
LED_N = 26
LED_E = 19
LED_S = 13
LED_W = 6

# Constants for notification LED pin numbers
LED_10_MIN = 21
LED_5_MIN = 20
LED_1_MIN = 16

# Initialize the pigpio library and set up the servo
pi = pigpio.pi()
servo = pigpio.Servo(pi)

# Initialize the ISS object with the latitude and longitude of the current location
lat, lon = get_location()
iss = ISS(lat, lon)

while True:
    # Check the next pass of the ISS
    next_pass = iss.next_pass()

    # Calculate the time until the next pass in seconds
    time_until = (next_pass['risetime'] - time.time())

    # If the ISS is 10 minutes or less from being visible, turn on the 10 minute LED
    if time_until <= 600:
        pi.write(LED_10_MIN, pigpio.HIGH)
    else:
        pi.write(LED_10_MIN, pigpio.LOW)

    # If the ISS is 5 minutes or less from being visible, turn on the 5 minute LED
    if time_until <= 300:
        pi.write(LED_5_MIN, pigpio.HIGH)
    else:
        pi.write(LED_5_MIN, pigpio.LOW)

    # If the ISS is 1 minute or less from being visible, turn on the 1 minute LED
    if time_until <= 60:
        pi.write(LED_1_MIN, pigpio.HIGH)
    else:
        pi.write(LED_1_MIN, pigpio.LOW)

    # If the ISS is visible, move the servo and turn on the appropriate LED
    if time_until <= 5:
        # Move the servo to 90 degrees
        servo.set_servo_pulsewidth(SERVO_MIN)

        # Turn on the LED for the direction the ISS will be visible
        if next_pass['azimuth'] >= 0 and next_pass['azimuth'] < 90:
            pi.write(LED_N, pigpio.HIGH)
        elif next_pass['azimuth'] >= 90 and next_pass['azimuth'] < 180:
            pi.write(LED_E, pigpio.HIGH)
        elif next_pass['azimuth'] >= 180 and next_pass['azimuth'] < 270:
            pi.write(LED_S, pigpio.HIGH)
        elif next_pass['azimuth'] >= 270 and next_pass['azimuth'] <= 360:
            pi.write(LED_W, pigpio.HIGH)
    else:
        # Move the servo back to 0 degrees
        servo.set_servo_pulsewidth(SERVO_MAX)

        # Turn off all direction LEDs
        pi.write(LED_N, pigpio.LOW)
        pi.write(LED_E, pigpio.LOW)
        pi.write(LED_S, pigpio.LOW)
        pi.write(LED_W, pigpio.LOW)
# Sleep for 5 seconds before checking again
time.sleep(5)

# Clean up pigpio and servo resources
servo.stop()
pi.stop()

