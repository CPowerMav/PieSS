import json, urllib.request, time, pigpio
from gpiozero import LED
from os import system
from time import sleep


myServoUp = 600 # Servo duty time for flag raised
myServoDown = 2400 # Servo duty time for flag raised

# Servo
pi = pigpio.pi()


pi.set_servo_pulsewidth(myServo, myServoUp) # flag up
pi.set_servo_pulsewidth(myServo, 0) # flag motor off
sleep(3)
pi.set_servo_pulsewidth(myServo, myServoDown) # flag down
sleep(1)
pi.set_servo_pulsewidth(myServo, 0) # flag motor off
sleep(3)
