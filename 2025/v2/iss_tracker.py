#!/usr/bin/env python3
"""iss_tracker.py
Main program for tracking the ISS and raising a flag with LEDs and a servo.

Features:
- Automatic IP-based location detection
- Night-time only alerts (based on sunrise/sunset)
- Direction LEDs
- Progressive LED alerts with accelerating blink patterns
- Servo movement with torque hold
- Automatic TLE caching
"""

import os
import time
from datetime import datetime, timedelta

import requests
import pigpio
from gpiozero import LED
from skyfield.api import Topos, load
from skyfield import almanac

# ----------------------------
# CONFIGURATION
# ----------------------------

# File and TLE configuration
CACHE_FILE = 'stations.tle'  # Local cached TLE file
TLE_URL = 'https://celestrak.org/NORAD/elements/gp.php?CATNR=25544&FORMAT=tle'
TLE_REFRESH_HOURS = 12  # Refresh TLE data every 12 hours

# Visibility filters
MIN_ELEVATION = 10.0     # Minimum degrees above horizon

# Alert timings (seconds before rise)
ALERT_30M = 1800  # 30 minutes
ALERT_10M = 600   # 10 minutes
ALERT_5M = 300    # 5 minutes

# Servo GPIO configuration
SERVO_PIN = 16
SERVO_UP = 530
SERVO_DOWN = 1530

# LED GPIO pins
LED_30M_PIN = 22  # Red: 30-minute alert
LED_10M_PIN = 27  # Yellow: 10-minute alert
LED_5M_PIN = 17   # Green: 5-minute alert

LED_N_PIN = 5     # North direction
LED_E_PIN = 6     # East direction
LED_S_PIN = 13    # South direction
LED_W_PIN = 12    # West direction

# ----------------------------
# HARDWARE SETUP
# ----------------------------

# Initialize pigpio for servo control
pi = pigpio.pi()
if not pi.connected:
    raise RuntimeError("Could not connect to pigpio. Run 'sudo pigpiod'.")

# Initialize LEDs
led_30m = LED(LED_30M_PIN)
led_10m = LED(LED_10M_PIN)
led_5m = LED(LED_5M_PIN)

led_n = LED(LED_N_PIN)
led_e = LED(LED_E_PIN)
led_s = LED(LED_S_PIN)
led_w = LED(LED_W_PIN)


# ----------------------------
# HELPER FUNCTIONS
# ----------------------------

def set_servo(position: int, hold_torque: bool = True) -> None:
    """Move servo to a given pulse-width position.

    If hold_torque is False, the pulse is released after 1s so the servo
    is not powered continuously (less heat / noise).
    """
    pi.set_servo_pulsewidth(SERVO_PIN, position)
    if not hold_torque:
        time.sleep(1)
        pi.set_servo_pulsewidth(SERVO_PIN, 0)


def reset_leds() -> None:
    """Turn off all LEDs."""
    led_30m.off()
    led_10m.off()
    led_5m.off()
    led_n.off()
    led_e.off()
    led_s.off()
    led_w.off()


def update_direction_leds(azimuth: float) -> None:
    """Update directional LEDs based on azimuth in degrees.

    North = 0/360°, East = 90°, South = 180°, West = 270°
    """
    led_n.off()
    led_e.off()
    led_s.off()
    led_w.off()

    if azimuth >= 315 or azimuth < 45:
        led_n.on()
    elif 45 <= azimuth < 135:
        led_e.on()
    elif 135 <= azimuth < 225:
        led_s.on()
    elif 225 <= azimuth < 315:
        led_w.on()


def test_hardware():
    """Run a quick hardware test on startup to verify all components"""
    print("Running hardware self-test...")
    
    # Test sequence
    test_items = [
        ("North", led_n),
        ("West", led_w),
        ("South", led_s),
        ("East", led_e),
        ("30-min", led_30m),
        ("10-min", led_10m),
        ("5-min", led_5m),
    ]
    
    # Test LEDs
    for name, led in test_items:
        print(f"  Testing {name} LED... ", end="", flush=True)
        led.on()
        time.sleep(0.5)
        led.off()
        print("OK")
        time.sleep(0.2)
    
    # Test servo
    print("  Testing servo UP... ", end="", flush=True)
    set_servo(SERVO_UP, hold_torque=False)
    time.sleep(1)
    print("OK")
    
    print("  Testing servo DOWN... ", end="", flush=True)
    set_servo(SERVO_DOWN, hold_torque=False)
    time.sleep(1)
    print("OK")
    
    print("Hardware self-test complete!\n")


def blink_led(led, duration: float, blink_rate: float, check_interval: float = 0.1):
    """
    Blink an LED for a specified duration at a given rate.
    
    Args:
        led: LED object to blink
        duration: How long to blink (seconds)
        blink_rate: Time for one complete on/off cycle (seconds)
        check_interval: How often to check timing (seconds)
    """
    start_time = time.time()
    on_time = blink_rate / 2
    off_time = blink_rate / 2
    
    led_state = False
    last_toggle = start_time
    
    while (time.time() - start_time) < duration:
        current_time = time.time()
        elapsed_since_toggle = current_time - last_toggle
        
        if led_state and elapsed_since_toggle >= on_time:
            led.off()
            led_state = False
            last_toggle = current_time
        elif not led_state and elapsed_since_toggle >= off_time:
            led.on()
            led_state = True
            last_toggle = current_time
        
        time.sleep(check_interval)
    
    led.off()


def get_location():
    """Detect geographical location via IP geolocation.

    Tries multiple providers in order.
    Returns (latitude, longitude, altitude_meters).
    Altitude defaults to 0.0 (not critical for ISS tracking).
    """

    providers = [
        {
            "name": "ipapi",
            "url": "https://ipapi.co/json/",
            "lat": lambda d: d.get("latitude"),
            "lon": lambda d: d.get("longitude"),
        },
        {
            "name": "ipinfo",
            "url": "https://ipinfo.io/json",
            "lat": lambda d: float(d["loc"].split(",")[0]) if "loc" in d else None,
            "lon": lambda d: float(d["loc"].split(",")[1]) if "loc" in d else None,
        },
        {
            "name": "ifconfig",
            "url": "https://ifconfig.co/json",
            "lat": lambda d: d.get("latitude"),
            "lon": lambda d: d.get("longitude"),
        },
    ]

    headers = {
        "User-Agent": "ISS-Tracker/1.0 (Raspberry Pi)"
    }

    for provider in providers:
        try:
            resp = requests.get(provider["url"], headers=headers, timeout=5)
            resp.raise_for_status()
            data = resp.json()

            lat = provider["lat"](data)
            lon = provider["lon"](data)

            if lat is None or lon is None:
                raise ValueError("Latitude/longitude missing")

            lat = float(lat)
            lon = float(lon)

            print(
                f"Detected location via {provider['name']}: "
                f"{lat:.4f}, {lon:.4f}, alt 0m"
            )

            return lat, lon, 0.0

        except Exception as exc:
            print(f"Location provider {provider['name']} failed ({exc})")

    # Final fallback (only if all providers fail)
    print("All location providers failed, using default coordinates.")
    return 43.577090, -79.727520, 128.0


def get_satellite_data():
    """Load TLE data for ISS, using local cache when available."""
    ts = load.timescale()
    should_download = True

    if os.path.exists(CACHE_FILE):
        age = time.time() - os.path.getmtime(CACHE_FILE)
        if age < (TLE_REFRESH_HOURS * 3600):
            should_download = False

    try:
        satellites = load.tle_file(
            TLE_URL,
            filename=CACHE_FILE,
            reload=should_download,
        )
    except Exception as exc:
        # If download failed but cache exists, try using the cached file only.
        print(f"TLE download failed ({exc}).")
        if os.path.exists(CACHE_FILE):
            print("Using cached TLE file.")
            satellites = load.tle_file(CACHE_FILE)
        else:
            raise

    by_name = {sat.name: sat for sat in satellites}
    return by_name['ISS (ZARYA)'], ts


def get_sunrise_sunset(observer_topos: Topos, date_t, ts, ephemeris):
    """
    Calculate sunrise and sunset times for a given date.
    Returns (sunrise_time, sunset_time) as Skyfield Time objects.
    
    Args:
        observer_topos: Observer's location
        date_t: Skyfield Time object for the date
        ts: Skyfield timescale
        ephemeris: Ephemeris data
    """
    earth = ephemeris['earth']
    observer = earth + observer_topos
    
    # Start at midnight of the given date
    dt = date_t.utc_datetime().replace(hour=0, minute=0, second=0, microsecond=0)
    t0 = ts.from_datetime(dt)
    t1 = ts.from_datetime(dt + timedelta(days=1))
    
    # Find sunrise/sunset events
    times, events = almanac.find_discrete(t0, t1, almanac.sunrise_sunset(ephemeris, observer_topos))
    
    sunrise = None
    sunset = None
    
    for t, is_sunrise in zip(times, events):
        if is_sunrise:
            sunrise = t
        else:
            sunset = t
    
    return sunrise, sunset


def is_visible_at_night(observer_topos: Topos, pass_time_t, ts, ephemeris) -> bool:
    """
    Check if a pass occurs during night time (sun below horizon).
    
    Args:
        observer_topos: Observer's location
        pass_time_t: Skyfield Time object for the pass
        ts: Skyfield timescale
        ephemeris: Ephemeris data
    """
    # Check sun elevation - simpler and more reliable than sunrise/sunset bracketing
    sun = ephemeris['sun']
    earth = ephemeris['earth']
    observer = earth + observer_topos
    alt, _, _ = observer.at(pass_time_t).observe(sun).apparent().altaz()
    
    # Sun must be at least 6 degrees below horizon (civil twilight)
    return alt.degrees < -6.0


# ----------------------------
# MAIN LOOP
# ----------------------------

def main() -> None:
    print("--- Starting ISS Tracker ---")

    # Load ephemeris for sun calculations
    eph = load('de421.bsp')

    # Detect location automatically
    latitude, longitude, elevation = get_location()
    observer_location = Topos(latitude, longitude, elevation_m=elevation)

    # Reset LEDs and servo
    reset_leds()
    set_servo(SERVO_DOWN, hold_torque=False)
    
    # Run hardware test
    test_hardware()

    while True:
        try:
            # Load ISS TLE data
            iss, ts = get_satellite_data()

            # Calculate passes for next 24 hours
            t0 = ts.now()
            t1 = ts.from_datetime(t0.utc_datetime() + timedelta(days=1))
            times, events = iss.find_events(
                observer_location, t0, t1, altitude_degrees=MIN_ELEVATION
            )

            next_pass_found = False

            # Iterate to find first visible pass
            for i in range(len(times)):
                if events[i] != 0:
                    # 0 = rise, 1 = peak, 2 = set
                    continue

                if i + 2 >= len(times):
                    # Ensure we have rise-peak-set trio
                    break

                rise_t, peak_t, set_t = times[i], times[i + 1], times[i + 2]

                # Skip if peak occurs during daylight
                if not is_visible_at_night(observer_location, peak_t, ts, eph):
                    print(f"Skipping pass at {rise_t.utc_iso()} (daylight)")
                    continue

                next_pass_found = True

                # Calculate duration and time to rise
                now_ts = ts.now()
                rise_dt = rise_t.utc_datetime()
                set_dt = set_t.utc_datetime()
                duration_sec = (set_dt - rise_dt).total_seconds()
                seconds_to_rise = (rise_dt - now_ts.utc_datetime()).total_seconds()

                print(
                    f"Next visible pass: rise {rise_dt} UTC, duration {duration_sec:.0f}s, "
                    f"starts in {seconds_to_rise/60:.1f} minutes"
                )

                # Sleep until 32 minutes before rise (gives time for LEDs to start)
                time_to_wait = seconds_to_rise - 1920  # 32 minutes
                if time_to_wait > 0:
                    time.sleep(time_to_wait)

                # Progressive countdown with accelerating blink patterns
                while True:
                    now = ts.now().utc_datetime()
                    remaining = (rise_dt - now).total_seconds()

                    if now > set_dt:
                        # Pass is over
                        break

                    # 30-10 minute countdown (Red LED with progressive blinking)
                    if remaining > ALERT_10M:
                        if remaining > 1500:  # 25-30 min
                            print("30-minute alert (very slow blink)")
                            blink_led(led_30m, min(300, remaining - 1500), 4.0)
                        elif remaining > 1200:  # 20-25 min
                            print("25-minute alert (slow blink)")
                            blink_led(led_30m, min(300, remaining - 1200), 3.0)
                        elif remaining > 900:  # 15-20 min
                            print("20-minute alert (medium blink)")
                            blink_led(led_30m, min(300, remaining - 900), 2.0)
                        elif remaining > ALERT_10M:  # 10-15 min
                            print("15-minute alert (fast blink)")
                            blink_led(led_30m, min(300, remaining - ALERT_10M), 1.0)

                    # 10-5 minute countdown (Yellow LED with progressive blinking)
                    elif remaining > ALERT_5M:
                        led_30m.off()
                        if remaining > 480:  # 8-10 min
                            print("10-minute alert (slow blink)")
                            blink_led(led_10m, min(120, remaining - 480), 3.0)
                        elif remaining > 360:  # 6-8 min
                            print("8-minute alert (medium blink)")
                            blink_led(led_10m, min(120, remaining - 360), 2.0)
                        elif remaining > ALERT_5M:  # 5-6 min
                            print("6-minute alert (fast blink)")
                            blink_led(led_10m, min(60, remaining - ALERT_5M), 1.0)

                    # 5-0 minute countdown (Green LED with progressive blinking)
                    elif remaining > 0:
                        led_10m.off()
                        if remaining > 180:  # 3-5 min
                            print("5-minute alert (medium blink)")
                            blink_led(led_5m, min(120, remaining - 180), 2.0)
                        elif remaining > 60:  # 1-3 min
                            print("3-minute alert (fast blink)")
                            blink_led(led_5m, min(120, remaining - 60), 1.0)
                        elif remaining > 0:  # 0-1 min
                            print("1-minute alert (rapid blink, raising flag)")
                            set_servo(SERVO_UP, hold_torque=True)
                            blink_led(led_5m, remaining, 0.5)
                            break

                    time.sleep(0.5)

                # During the pass - only show directional LEDs
                led_5m.off()
                print("Pass in progress - showing direction")
                
                while True:
                    now = ts.now().utc_datetime()
                    if now > set_dt:
                        break
                    
                    difference = iss - observer_location
                    alt, az, _ = difference.at(ts.now()).altaz()
                    
                    if alt.degrees > 0:
                        update_direction_leds(az.degrees)
                    
                    time.sleep(0.5)

                # Reset hardware after pass
                print("Pass complete, lowering flag.")
                reset_leds()
                set_servo(SERVO_DOWN, hold_torque=False)
                break  # Break out of event loop, re-calc passes

            # If we didn't find any visible pass, wait an hour and try again
            if not next_pass_found:
                print("No visible pass in next 24h, sleeping 1 hour.")
                time.sleep(3600)

        except Exception as e:
            print(f"Error: {e}")
            reset_leds()
            set_servo(SERVO_DOWN, hold_torque=False)
            time.sleep(60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Exiting on Ctrl+C, cleaning up GPIO.")
        reset_leds()
        set_servo(SERVO_DOWN, hold_torque=False)
        pi.stop()
