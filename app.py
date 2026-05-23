from flask import Flask, render_template, jsonify
from datetime import datetime
import requests
import math

from gtfs_utils import (
    ROUTE_IDS,
    get_route_key_by_route_id,
    get_route_label,
    get_direction_label,
    is_target_direction,
    is_before_or_at_target_stop,
    get_bus_location_status,
    get_debug_status,
)

app = Flask(__name__)

TARGET_LOCATION = {
    "name": "亀戸七丁目",
    "latitude": 35.6990,
    "longitude": 139.8400,
}

GTFS_RT_URL = "https://tokyo-bus-gfsrt.odpt.org/api/v1/gtfsrt"

SEARCH_RADIUS_KM = 3.5


def haversine(lat1, lon1, lat2, lon2):
    r = 6371

    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return r * c


def fetch_gtfs_rt():
    try:
        res = requests.get(GTFS_RT_URL, timeout=15)

        if res.status_code != 200:
            print("GTFS ERROR STATUS =", res.status_code)
            return []

        data = res.json()

        return data.get("entity", [])

    except Exception as e:
        print("GTFS FETCH ERROR =", str(e))
        return []


def parse_vehicle(entity):
    try:
        vehicle = entity.get("vehicle", {})

        trip = vehicle.get("trip", {})
        position = vehicle.get("position", {})
        vehicle_info = vehicle.get("vehicle", {})

        trip_id = trip.get("tripId", "")
        route_id = trip.get("routeId", "")
        stop_id = vehicle.get("stopId", "")

        lat = position.get("latitude")
        lon = position.get("longitude")

        if lat is None or lon is None:
            return None

        distance = haversine(
            TARGET_LOCATION["latitude"],
            TARGET_LOCATION["longitude"],
            lat,
            lon,
        )

        if distance > SEARCH_RADIUS_KM:
            return None

        route_key = get_route_key_by_route_id(route_id)

        if not route_key:
            return None

        if not is_target_direction(trip_id):
            return None

        if not is_before_or_at_target_stop(trip_id, stop_id):
            return None

        status = get_bus_location_status(
            trip_id,
            stop_id,
        )

        return {
            "vehicle_id": vehicle_info.get("id", "不明"),
            "trip_id": trip_id,
            "route_id": route_id,
            "route_key": route_key,
            "route_label": get_route_label(route_key),
            "latitude": lat,
            "longitude": lon,
            "distance_km": round(distance, 3),
            "direction": get_direction_label(trip_id),
            "current_stop_name": status.get(
                "current_stop_name",
                "接近中",
            ),
            "remaining_stop_count": status.get(
                "remaining_stop_count"
            ),
            "status_text": status.get(
                "status_text",
                "接近中",
            ),
            "progress_stops": status.get(
                "progress_stops",
                [],
            ),
            "passed_target": status.get(
                "passed_target",
                False,
            ),
        }

    except Exception as e:
        print("PARSE VEHICLE ERROR =", str(e))
        return None


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/realtime")
def realtime_api():
    try:
        entities = fetch_gtfs_rt()

        buses = []

        for entity in entities:
            parsed = parse_vehicle(entity)

            if parsed:
                buses.append(parsed)

        buses.sort(
            key=lambda x: x.get("distance_km", 999)
        )

        print("REALTIME BUSES =", buses[:3])

        return jsonify({
            "ok": True,
            "count": len(buses),
            "buses": buses,
        })

    except Exception as e:
        print("REALTIME API ERROR =", str(e))

        return jsonify({
            "ok": False,
            "error": str(e),
            "buses": [],
        })


@app.route("/api/realtime-debug")
def realtime_debug():
    try:
        entities = fetch_gtfs_rt()

        nearby = []

        for entity in entities:
            parsed = parse_vehicle(entity)

            if parsed:
                nearby.append(parsed)

        route_summary = {}

        for bus in nearby:
            rid = bus["route_id"]

            if rid not in route_summary:
                route_summary[rid] = {
                    "count": 0,
                    "vehicles": [],
                }

            route_summary[rid]["count"] += 1
            route_summary[rid]["vehicles"].append(bus)

        return jsonify({
            "ok": True,
            "all_count": len(entities),
            "nearby_count": len(nearby),
            "nearby_sample": nearby[:40],
            "route_summary": route_summary,
            "target": {
                "name": TARGET_LOCATION["name"],
                "latitude": TARGET_LOCATION["latitude"],
                "longitude": TARGET_LOCATION["longitude"],
                "search_radius_km": SEARCH_RADIUS_KM,
            },
            "gtfs": get_debug_status(),
        })

    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e),
        })


@app.route("/health")
def health():
    return jsonify({
        "ok": True,
        "time": datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
    })


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=10000,
        debug=True,
    )