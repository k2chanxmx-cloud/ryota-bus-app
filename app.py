from flask import Flask, render_template, jsonify
from datetime import datetime
import os
import math
import requests
from google.transit import gtfs_realtime_pb2

from gtfs_utils import (
    ROUTE_IDS,
    get_route_label,
    get_direction_label,
    get_bus_location_status,
    get_debug_status,
    is_before_or_at_target_stop,
)

app = Flask(__name__)

ODPT_API_KEY = os.environ.get("ODPT_API_KEY")
ODPT_REALTIME_URL = "https://api.odpt.org/api/v4/gtfs/realtime/ToeiBus"

TARGET_LOCATION = {
    "name": "亀戸七丁目",
    "latitude": 35.6990,
    "longitude": 139.8400,
}

SEARCH_RADIUS_KM = 3.5


def distance_km(lat1, lon1, lat2, lon2):
    r = 6371.0

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return r * c


def get_route_key(route_id):
    for key, value in ROUTE_IDS.items():
        if value == route_id:
            return key

    return None


def fetch_toei_realtime():
    if not ODPT_API_KEY:
        return {
            "ok": False,
            "reason": "ODPT_API_KEY が未設定です",
            "vehicles": [],
            "all_count": 0,
        }

    try:
        res = requests.get(
            ODPT_REALTIME_URL,
            params={"acl:consumerKey": ODPT_API_KEY},
            timeout=15,
        )

        res.raise_for_status()

        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(res.content)

        vehicles = []

        for entity in feed.entity:
            if not entity.HasField("vehicle"):
                continue

            vehicle = entity.vehicle

            trip_id = vehicle.trip.trip_id if vehicle.trip.trip_id else ""
            route_id = vehicle.trip.route_id if vehicle.trip.route_id else ""
            stop_id = vehicle.stop_id if vehicle.stop_id else ""
            vehicle_id = vehicle.vehicle.id if vehicle.vehicle.id else entity.id

            lat = None
            lon = None

            if vehicle.HasField("position"):
                lat = vehicle.position.latitude
                lon = vehicle.position.longitude

            route_key = get_route_key(route_id)

            location = get_bus_location_status(
                trip_id=trip_id,
                current_stop_id=stop_id,
                target_stop_name=TARGET_LOCATION["name"],
            )

            item = {
                "entity_id": entity.id,
                "vehicle_id": vehicle_id,
                "trip_id": trip_id,
                "route_id": route_id,
                "route_key": route_key,
                "route_label": get_route_label(route_key) if route_key else "",
                "stop_id": stop_id,
                "current_stop_name": location.get("current_stop_name", "接近中"),
                "direction": get_direction_label(trip_id),
                "status_text": location.get("status_text", "接近中"),
                "remaining_stop_count": location.get("remaining_stop_count"),
                "progress_stops": location.get("progress_stops", []),
                "passed_target": location.get("passed_target", False),
                "latitude": lat,
                "longitude": lon,
                "distance_km": None,
            }

            if lat is not None and lon is not None:
                item["distance_km"] = round(
                    distance_km(
                        TARGET_LOCATION["latitude"],
                        TARGET_LOCATION["longitude"],
                        lat,
                        lon,
                    ),
                    3,
                )

            vehicles.append(item)

        return {
            "ok": True,
            "reason": "",
            "vehicles": vehicles,
            "all_count": len(vehicles),
        }

    except Exception as e:
        print("REALTIME FETCH ERROR =", str(e))

        return {
            "ok": False,
            "reason": str(e),
            "vehicles": [],
            "all_count": 0,
        }


def get_realtime_buses():
    realtime = fetch_toei_realtime()

    if not realtime["ok"]:
        return {
            "ok": False,
            "reason": realtime["reason"],
            "buses": [],
            "all_count": realtime["all_count"],
        }

    buses = []

    for v in realtime["vehicles"]:

        if not v.get("route_key"):
            continue

        if v.get("distance_km") is None:
            continue

        if v["distance_km"] > SEARCH_RADIUS_KM:
            continue

        # 亀戸七丁目をこれから通る便だけ
        if not is_before_or_at_target_stop(
            trip_id=v.get("trip_id", ""),
            current_stop_id=v.get("stop_id", ""),
            target_stop_name=TARGET_LOCATION["name"],
        ):
            continue

        # 亀戸七丁目を通過済みなら除外
        if v.get("passed_target"):
            continue

        buses.append(v)

    buses.sort(
        key=lambda x: (
            x.get("remaining_stop_count")
            if x.get("remaining_stop_count") is not None
            else 999,
            x.get("distance_km")
            if x.get("distance_km") is not None
            else 999,
        )
    )

    return {
        "ok": True,
        "reason": "",
        "buses": buses,
        "all_count": realtime["all_count"],
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/realtime")
def realtime_api():
    result = get_realtime_buses()

    return jsonify({
        "ok": result["ok"],
        "reason": result["reason"],
        "count": len(result["buses"]),
        "buses": result["buses"],
    })


@app.route("/api/realtime-debug")
def realtime_debug():
    realtime = fetch_toei_realtime()
    result = get_realtime_buses()

    return jsonify({
        "ok": realtime["ok"],
        "reason": realtime["reason"],
        "all_count": realtime["all_count"],
        "nearby_count": len(result["buses"]),
        "nearby_sample": result["buses"][:40],
        "gtfs": get_debug_status(),
        "target": {
            "name": TARGET_LOCATION["name"],
            "latitude": TARGET_LOCATION["latitude"],
            "longitude": TARGET_LOCATION["longitude"],
            "search_radius_km": SEARCH_RADIUS_KM,
        },
    })


@app.route("/health")
def health():
    return jsonify({
        "ok": True,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=10000,
        debug=True,
    )