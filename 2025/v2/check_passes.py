cd /home/piess/PieSS/2025/v2
source venv/bin/activate

# Create a quick debug script
cat > check_passes.py << 'EOF'
from skyfield.api import Topos, load
from datetime import datetime, timedelta

ts = load.timescale()
satellites = load.tle_file('stations.tle')
iss = satellites[0]

# Your location
observer = Topos(43.2596, -79.7925, elevation_m=0)

# Next 48 hours
t0 = ts.now()
t1 = ts.from_datetime(t0.utc_datetime() + timedelta(hours=48))

times, events = iss.find_events(observer, t0, t1, altitude_degrees=15.0)

print("All ISS passes in next 48 hours (min 15° elevation):")
for i in range(0, len(times), 3):
    if i+2 < len(times):
        rise = times[i]
        peak = times[i+1]
        setting = times[i+2]
        
        # Get max elevation
        difference = iss - observer
        alt, az, dist = difference.at(peak).altaz()
        
        print(f"Rise: {rise.utc_datetime()} UTC | Peak: {peak.utc_datetime()} UTC (alt: {alt.degrees:.1f}°) | Set: {setting.utc_datetime()} UTC")
EOF

python3 check_passes.py