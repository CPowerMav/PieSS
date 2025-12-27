#!/usr/bin/env python3
"""iss_tracker.py
Main program for tracking the ISS and raising a flag with LEDs and a servo.

Features:
- Automatic IP-based location detection
- Night-time only alerts
- Direction LEDs
- LED alerts for 10, 5, 1 minute warnings
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
MIN_ELEVATION = 15.0     # Minimum degrees above horizon
MAX_SUN_ELEVATION = -6.0 # Sun must be below -6° (civil twilight)

# Alert timings (seconds)
ALERT_1_SEC = 600  # 10 minutes
ALERT_2_SEC = 300  # 5 minutes
ALERT_3_SEC = 60   # 1 minute

# Servo GPIO configuration
SERVO_PIN = 16
SERVO_UP = 530
SERVO_DOWN = 1530

# LED GPIO pins
LED_10M_PIN = 22  # Red: 10-minute alert
LED_5M_PIN = 27   # Yellow: 5-minute alert
LED_1M_PIN = 17   # Green: 1-minute alert

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
led_10m = LED(LED_10M_PIN)
led_5m = LED(LED_5M_PIN)
led_1m = LED(LED_1M_PIN)

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
    led_10m.off()
    led_5m.off()
    led_1m.off()
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
    
    # Test sequence - same order as hardware_test.py
    test_items = [
        ("North", led_n),
        ("West", led_w),
        ("South", led_s),
        ("East", led_e),
        ("10-min", led_10m),
        ("5-min", led_5m),
        ("1-min", led_1m),
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
    
    print("  Testing servo UP... ", end="", flush=True)
    set_servo(SERVO_UP, hold_torque=False)
    time.sleep(1)
    print("OK")
    
    print("  Testing servo DOWN... ", end="", flush=True)
    set_servo(SERVO_DOWN, hold_torque=False)
    time.sleep(1)
    print("OK")
    
    print("Hardware self-test complete!\n")

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


def get_sunrise_sunset(observer_topos: Topos, date_t, ephemeris):
    """
    Calculate sunrise and sunset times for a given date.
    Returns (sunrise_time, sunset_time) as Skyfield Time objects.
    """
    ts = ephemeris.timescale
    earth = ephemeris['earth']
    sun = ephemeris['sun']
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


def is_visible_at_night(observer_topos: Topos, pass_time_t, ephemeris) -> bool:
    """
    Check if a pass occurs during night time (between sunset and sunrise).
    Also checks that the ISS is illuminated by the sun (for visibility).
    """
    # Get sunrise and sunset for the pass date
    sunrise, sunset = get_sunrise_sunset(observer_topos, pass_time_t, ephemeris)
    
    if sunrise is None or sunset is None:
        # Fallback to old method if we can't calculate sunrise/sunset
        sun = ephemeris['sun']
        earth = ephemeris['earth']
        observer = earth + observer_topos
        alt, _, _ = observer.at(pass_time_t).observe(sun).apparent().altaz()
        return alt.degrees < MAX_SUN_ELEVATION
    
    pass_datetime = pass_time_t.utc_datetime()
    
    # Handle case where sunset is before sunrise (normal night)
    if sunset.utc_datetime() < sunrise.utc_datetime():
        is_night = pass_datetime >= sunset.utc_datetime() or pass_datetime <= sunrise.utc_datetime()
    else:
        # Handle case crossing midnight
        is_night = pass_datetime >= sunset.utc_datetime() and pass_datetime <= sunrise.utc_datetime()
    
    return is_night


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

    # Run through hardware test once
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
                if not is_visible_at_night(observer_location, peak_t, eph):
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

                # Sleep until 12 minutes before rise (gives time for LEDs to step up)
                time_to_wait = seconds_to_rise - 720
                if time_to_wait > 0:
                    time.sleep(time_to_wait)

                # Track alerts
                alert1_fired = False
                alert2_fired = False
                alert3_fired = False

                while True:
                    now = ts.now().utc_datetime()
                    remaining = (rise_dt - now).total_seconds()

                    if now > set_dt:
                        # Pass is over
                        break

                    # Alerts
                    if ALERT_1_SEC >= remaining > ALERT_2_SEC and not alert1_fired:
                        print("10-minute alert")
                        led_10m.on()
                        alert1_fired = True

                    elif ALERT_2_SEC >= remaining > ALERT_3_SEC and not alert2_fired:
                        print("5-minute alert")
                        led_10m.off()
                        led_5m.on()
                        alert2_fired = True

                    elif ALERT_3_SEC >= remaining > 0 and not alert3_fired:
                        print("1-minute alert (raising flag)")
                        led_5m.off()
                        led_1m.on()
                        set_servo(SERVO_UP, hold_torque=True)
                        alert3_fired = True

                    # Direction LEDs in the last minute before rise
                    if remaining < 60:
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
