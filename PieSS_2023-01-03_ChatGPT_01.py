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

        # Turn off all direction
