#!/usr/bin/env python3
"""
PieSS Hardware Test Script
Tests all LEDs and servo in sequence to verify connections
"""

import time
import pigpio
from gpiozero import LED

# GPIO Pin Configuration (matching iss_tracker.py)
SERVO_PIN = 16
SERVO_UP = 530
SERVO_DOWN = 1530

LED_10M_PIN = 22  # Red: 10-minute alert
LED_5M_PIN = 27   # Yellow: 5-minute alert
LED_1M_PIN = 17   # Green: 1-minute alert

LED_N_PIN = 5     # North direction
LED_E_PIN = 6     # East direction
LED_S_PIN = 13    # South direction
LED_W_PIN = 12    # West direction

# Test timing
LED_DURATION = 1.5  # seconds each LED stays on
SERVO_DURATION = 2.0  # seconds servo holds position

def main():
    print("=== PieSS Hardware Test ===")
    print("Testing all LEDs and servo in sequence...")
    print("Press Ctrl+C to exit\n")
    
    # Initialize pigpio for servo
    pi = pigpio.pi()
    if not pi.connected:
        print("ERROR: Could not connect to pigpiod")
        print("Make sure pigpiod is running: sudo systemctl start pigpiod")
        return
    
    # Initialize LEDs
    led_n = LED(LED_N_PIN)
    led_w = LED(LED_W_PIN)
    led_s = LED(LED_S_PIN)
    led_e = LED(LED_E_PIN)
    led_10m = LED(LED_10M_PIN)
    led_5m = LED(LED_5M_PIN)
    led_1m = LED(LED_1M_PIN)
    
    # Test sequence
    test_items = [
        ("North LED (GPIO 5)", led_n, None),
        ("West LED (GPIO 12)", led_w, None),
        ("South LED (GPIO 13)", led_s, None),
        ("East LED (GPIO 6)", led_e, None),
        ("10-minute LED - Red (GPIO 22)", led_10m, None),
        ("5-minute LED - Yellow (GPIO 27)", led_5m, None),
        ("1-minute LED - Green (GPIO 17)", led_1m, None),
        ("Servo - Flag UP (GPIO 16)", None, SERVO_UP),
        ("Servo - Flag DOWN (GPIO 16)", None, SERVO_DOWN),
    ]
    
    try:
        cycle = 1
        while True:
            print(f"\n--- Test Cycle {cycle} ---")
            
            for name, led, servo_pos in test_items:
                print(f"Testing: {name}... ", end="", flush=True)
                
                if led is not None:
                    # Test LED
                    led.on()
                    time.sleep(LED_DURATION)
                    led.off()
                    print("✓")
                    
                elif servo_pos is not None:
                    # Test servo
                    pi.set_servo_pulsewidth(SERVO_PIN, servo_pos)
                    time.sleep(SERVO_DURATION)
                    pi.set_servo_pulsewidth(SERVO_PIN, 0)  # Release torque
                    print("✓")
                
                time.sleep(0.3)  # Small gap between tests
            
            cycle += 1
            print("\nWaiting 2 seconds before next cycle...")
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\n\n=== Test stopped by user ===")
        print("Cleaning up...")
        
        # Turn off all LEDs
        led_n.off()
        led_w.off()
        led_s.off()
        led_e.off()
        led_10m.off()
        led_5m.off()
        led_1m.off()
        
        # Release servo
        pi.set_servo_pulsewidth(SERVO_PIN, 0)
        pi.stop()
        
        print("Hardware test complete!")

if __name__ == "__main__":
    main()
