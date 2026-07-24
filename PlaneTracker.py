import requests
import json
import time
import threading
from datetime import datetime
from math import atan2, degrees
from pyproj import Geod
import sys


class PlaneTracker:
    def __init__(
        self,
        icao_code,
        tracker_lat_long,
        tracker_baro_alt_m
    ):
        self.icao_code = icao_code

        # Tuple formatted as: (latitude, longitude)
        self.tracker_lat_long = tracker_lat_long

        # Tracker altitude above mean sea level, in meters
        self.tracker_baro_alt_m = tracker_baro_alt_m

        self.latest_time = datetime.fromtimestamp(0)
        self.latest_data = {}

        self.master_heading_target = -1
        self.master_inclination_target = -1

        self.serial1 = serial.Serial('/dev/serial0', baudrate=115200, timeout=.5)


    def start(self):
        fetch_data_loop_t = threading.Thread(
            target=self.fetch_data_loop,
            daemon=True
        )
        fetch_data_loop_t.start()

        time.sleep(2)

        while True:
            self.update_targets()
            #print(self.master_heading_target)
            #print(self.master_inclination_target)
            print()
            self.write_angles_to_serial()
            time.sleep(0.01)

    def update_targets(self):
        geod = Geod(ellps="WGS84")
        plane = self.latest_data["ac"][0]

        plane_lat = float(plane["lat"])
        plane_lon = float(plane["lon"])
        heading_deg = float(plane["track"])
        speed_knots = float(plane["gs"])

        data_timestamp = float(self.latest_data["now"])

        if data_timestamp > 10_000_000_000:
            data_timestamp /= 1000

        elapsed_seconds = max(0, time.time() - data_timestamp)

        speed_mps = speed_knots * 0.514444
        traveled_m = speed_mps * elapsed_seconds

        predicted_lon, predicted_lat, _ = geod.fwd(
            plane_lon,
            plane_lat,
            heading_deg,
            traveled_m
        )

        azimuth, _, distance_m = geod.inv(
            self.tracker_lat_long[1],
            self.tracker_lat_long[0],
            predicted_lon,
            predicted_lat
        )

        azimuth %= 360

        # Prefer geometric altitude when available.
        plane_altitude = plane.get("alt_geom")

        if plane_altitude is None:
            plane_altitude = plane.get("alt_baro")

        if plane_altitude is None or plane_altitude == "ground":
            raise ValueError("Aircraft altitude is unavailable")

        # ADS-B altitude values are normally feet.
        plane_altitude_m = float(plane_altitude) * 0.3048

        altitude_difference_m = (
            plane_altitude_m - self.tracker_baro_alt_m
        )

        inclination_deg = degrees(
            atan2(
                altitude_difference_m,
                distance_m
            )
        )

        self.master_heading_target = azimuth
        self.master_inclination_target = inclination_deg

        return distance_m

    def fetch_data_loop(self):
        while True:
            url = f"https://api.adsb.lol/v2/icao/{self.icao_code}"
            print(f"requesting: '{url}'")

            try:
                req = requests.get(
                    url=url,
                    timeout=10
                )
                req.raise_for_status()

                data = req.json()

                timestamp = int(data["now"]) // 1000
                utc_time = datetime.fromtimestamp(timestamp)

                if utc_time > self.latest_time:
                    self.latest_time = utc_time
                    self.latest_data = data
                    print("update")

            except Exception as error:
                print(f"fetch failed: {error}")
                time.sleep(10)

            time.sleep(8)

    def write_angles_to_serial(self):
        payload = str(self.master_heading_target) + "," + str(self.master_inclination_target) + "\r"
        self.serial1.write(payload.encode('utf-8'))
        print(f"Response: {self.serial1.read(20).decode()}")