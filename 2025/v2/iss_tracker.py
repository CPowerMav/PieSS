#!/usr/bin/env python3
"""
iss_tracker.py
Main program for tracking the ISS and raising a flag with LEDs and a servo.
Features:
- Automatic IP-based location detection
- Night-time only alerts
- Direction LEDs
- LED alerts for 10, 5, 1 minute warnings
- Servo movement with torque hold
- Automatic TLE caching
"""

import time
import os
import requests
from datetime import datetime, timedelta
import pigpio
from gpiozero import LED
from skyfield.api import Topos, load, EarthSatellite

# ----------------------------
# CONFIGURATION
# ----------------------------

# File and TLE configuration
CACHE_FILE = 'stations.tle'  # Local cached TLE file
TLE_URL = 'https://celestrak.org/NORAD/elements/gp.php?CATNR=25544&FORMAT=tle'
TLE_REFRESH_HOURS = 12  # Refresh TLE data every 12 hours

# Visibility filters
MIN_ELEVATION = 15.0  # Minimum degrees above horizon
MAX_SUN_ELEVATION = -6.0  # Sun must be below -6° (Civil Twilight)

# Alert timings (seconds)
ALERT_1_SEC = 600  # 10 minutes
ALERT_2_SEC = 300  # 5 minutes
ALERT_3_SEC = 60   # 1 minute

# Servo GPIO configuration
SERVO_PIN = 16
SERVO_UP = 530
SERVO_DOWN = 1530

# ----------------------------
# HARDWARE SETUP
# ----------------------------

# Initialize pigpio for servo control
pi = pigpio.pi()
if not pi.connected:
    raise RuntimeError("Could not connect to pigpio. Run 'sudo pigpiod'.")

# Initialize LEDs
led_10m = LED(22)   # Red: 10-minute alert
led_5m = LED(27)    # Yellow: 5-minute alert
led_1m = LED(17)    # Green: 1-minute alert

led_n = LED(5)      # North direction
led_e = LED(6)      # East direction
led_s = LED(13)     # South direction
led_w = LED(12)     # West direction

# Optional running LED (status indicator)
led_running = LED(5)

# ----------------------------
# HELPER FUNCTIONS
# ----------------------------

def set_servo(position, hold_torque=True):
    """
    Move servo to a given position.
    hold_torque: keep pulse to hold position if True; detach to reduce power/heat if False.
    """
    pi.set_servo_pulsewidth(SERVO_PIN, position)
    if not hold_torque:
        time.sleep(1)
        pi.set_servo_pulsewidth(SERVO_PIN, 0)

def reset_leds():
    """Turn off all LEDs."""
    led_10m.off()
    led_5m.off()
    led_1m.off()
    led_n.off()
    led_e.off()
    led_s.off()
    led_w.off()

def update_direction_leds(azimuth):
    """
    Update directional LEDs based on azimuth degrees.
    North = 0/360°, East = 90°, South = 180°, West = 270°
    """
    led_n.off(); led_e.off(); led_s.off(); led_w.off()
    if azimuth >= 315 or azimuth < 45: led_n.on()
    elif 45 <= azimuth < 135: led_e.on()
    elif 135 <= azimuth < 225: led_s.on()
    elif 225 <= azimuth < 315: led_w.on()

def get_location():
    """
    Attempt to detect geographical location via IP geolocation.
    Returns (latitude, longitude, altitude) or defaults if detection fails.
    """
    try:
        r = requests.get("https://ipapi.co/json/")
        data = r.json()
        return float(data["latitude"]), float(data["longitude"]), float(data.get("altitude", 0))
    except:
        print("Location detection failed, using default coordinates.")
        return 43.577090, -79.727520, 128

def get_satellite_data():
    """
    Load TLE data for ISS, using local cache when available.
    """
    ts = load.timescale()
    should_download = True
    if os.path.exists(CACHE_FILE):
        age = time.time() - os.path.getmtime(CACHE_FILE)
        if age < (TLE_REFRESH_HOURS * 3600):
            should_download = False
    satellites = load.tle_file(TLE_URL, filename=CACHE_FILE, reload=should_download)
    by_name = {sat.name: sat for sat in satellites}
    return by_name['ISS (ZARYA)'], ts

def is_location_dark(observer, time_t, ephemeris):
    """
    Check if it is night-time at the observer's location.
    Returns True if the sun is below MAX_SUN_ELEVATION.
    """
    sun = ephemeris['sun']
    alt, _, _ = observer.at(time_t).observe(sun).apparent().altaz()
    return alt.degrees < MAX_SUN_ELEVATION

# ----------------------------
# MAIN LOOP
# ----------------------------

def main():
    print("--- Starting ISS Tracker ---")

    # Load ephemeris for sun calculations
    eph = load('de421.bsp')

    # Detect location automatically
    latitude, longitude, elevation = get_location()
    observer_location = Topos(latitude, longitude, elevation_m=elevation)

    # Reset LEDs and servo
    reset_leds()
    set_servo(SERVO_DOWN, hold_torque=False)

    while True:
        try:
            # Load ISS TLE data
            iss, ts = get_satellite_data()

            # Calculate passes for next 24 hours
            t0 = ts.now()
            t1 = ts.from_datetime(t0.utc_datetime() + timedelta(days=1))
            times, events = iss.find_events(observer_location, t0, t1, altitude_degrees=MIN_ELEVATION)

            next_pass_found = False

            # Iterate to find first visible pass
            for i in range(len(times)):
                if events[i] != 0: continue  # Skip if not rise
                if i + 2 >= len(times): break  # Ensure rise-peak-set exists

                rise_t, peak_t, set_t = times[i], times[i+1], times[i+2]

                # Skip if peak occurs during daylight
                if not is_location_dark(observer_location, peak_t, eph):
                    print(f"Skipping pass at {rise_t.utc_iso()} (Daylight)")
                    continue

                next_pass_found = True

                # Calculate duration and time to rise
                now = ts.now()
                rise_dt = rise_t.utc_datetime()
                set_dt = set_t.utc_datetime()
                duration_sec = (set_dt - rise_dt).total_seconds()
                seconds_to_rise = (rise_dt - now.utc_datetime()).total_seconds()

                # Sleep until 12 minutes before rise
                time_to_wait = seconds_to_rise - 720
                if time_to_wait > 0: time.sleep(time_to_wait)

                # Track alerts
                alert1_fired = alert2_fired = alert3_fired = flag_is_up = False
                while True:
                    now = ts.now().utc_datetime()
                    remaining = (rise_dt - now).total_seconds()
                    if now > set_dt: break

                    # Alerts
                    if ALERT_1_SEC >= remaining > ALERT_2_SEC and not alert1_fired:
                        led_10m.on(); alert1_fired = True
                    elif ALERT_2_SEC >= remaining > ALERT_3_SEC and not alert2_fired:
                        led_10m.off(); led_5m.on(); alert2_fired = True
                    elif ALERT_3_SEC >= remaining > 0 and not alert3_fired:
                        led_5m.off(); led_1m.on()
                        set_servo(SERVO_UP, hold_torque=True)
                        flag_is_up = True; alert3_fired = True

                    # Direction LEDs
                    if remaining < 60:
                        difference = iss - observer_location
                        alt, az, distance = difference.at(ts.now()).altaz()
                        if alt.degrees > 0: update_direction_leds(az.degrees)

                    time.sleep(0.5)

                # Reset hardware after pass
                reset_leds()
                set_servo(SERVO_DOWN, hold_torque=False)
                break

            # Sleep if no visible pass
            if not next_pass_found: time.sleep(3600)

        except Exception as e:
            print(f"Error: {e}")
            reset_leds()
            set_servo(SERVO_DOWN, hold_torque=False)
            time.sleep(60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        reset_leds()
        set_servo(SERVO_DOWN, hold_torque=False)
        pi.stop()
