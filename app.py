from flask import Flask, render_template, jsonify
from datetime import datetime
import os
import math
import requests
from google.transit import gtfs_realtime_pb2

from gtfs_utils import (
    ROUTE_IDS,
    get_route_label,
    get_bus_location_status,
    get_debug_status,
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

# 亀戸七丁目付近だけ監視
ROUTE_STOP_ORDER = {

    # 錦25
    "nishi25": [
        "小松川三丁目",
        "中川新橋",

        "浅間神社",
        "浅間神社(江東区)",

        "亀戸九丁目",
        "亀戸七丁目",
    ],

    # 錦27
    "nishi27": [
        "小松川三丁目",
        "中川新橋",

        "浅間神社",
        "浅間神社(江東区)",

        "亀戸九丁目",
        "亀戸七丁目",
    ],

    # 亀26
    "kame26": [
        "小松川三丁目",
        "中川新橋",

        "浅間神社",
        "浅間神社(江東区)",

        "亀戸九丁目",
        "亀戸七丁目",
    ],
}


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


def is_valid_bus(route_key, current_stop_name):
    order = ROUTE_STOP_ORDER.get(route_key)

    if not order:
        return False

    return current_stop_name in order


def build_progress(route_key, current_stop_name):
    order = ROUTE_STOP_ORDER.get(route_key, [])

    result = []

    for stop in order:
        role = "normal"

        if stop == current_stop_name:
            role = "current"

        if stop == TARGET_LOCATION["name"]:
            role = "target"

        result.append({
            "stop_name": stop,
            "stop_id": "",
            "role": role,
        })

    return result


def make_status_text(route_key, current_stop_name):
    order = ROUTE_STOP_ORDER.get(route_key, [])

    if current_stop_name not in order:
        return "亀戸七丁目へ接近中"

    current_index = order.index(current_stop_name)

    target_candidates = [
        i for i, stop in enumerate(order)
        if stop == TARGET_LOCATION["name"]
    ]

    if not target_candidates:
        return "亀戸七丁目へ接近中"

    target_index = target_candidates[0]

    remaining = target_index - current_index

    if remaining > 1:
        return f"亀戸七丁目まであと{remaining}停留所"

    if remaining == 1:
        return "次は亀戸七丁目"

    if remaining == 0:
        return "亀戸七丁目付近"

    return "亀戸七丁目通過済み"


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

            current_stop_name = location.get(
                "current_stop_name",
                "接近中",
            )

            progress_stops = []
            status_text = "亀戸七丁目へ接近中"

            if route_key:
                progress_stops = build_progress(
                    route_key,
                    current_stop_name,
                )

                status_text = make_status_text(
                    route_key,
                    current_stop_name,
                )

            item = {
                "entity_id": entity.id,
                "vehicle_id": vehicle_id,
                "trip_id": trip_id,
                "route_id": route_id,
                "route_key": route_key,
                "route_label": get_route_label(route_key) if route_key else "",
                "stop_id": stop_id,
                "current_stop_name": current_stop_name,
                "direction": "亀戸七丁目方面",
                "status_text": status_text,
                "remaining_stop_count": None,
                "progress_stops": progress_stops,
                "passed_target": False,
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

        route_key = v.get("route_key")
        current_stop_name = v.get("current_stop_name", "")

        if not route_key:
            continue

        if route_key not in ROUTE_STOP_ORDER:
            continue

        if not is_valid_bus(route_key, current_stop_name):
            continue

        if v.get("distance_km") is None:
            continue

        if v["distance_km"] > SEARCH_RADIUS_KM:
            continue

        buses.append(v)

    buses.sort(
        key=lambda x: (
            x.get("distance_km")
            if x.get("distance_km") is not None
            else 999
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
        "route_stop_order": ROUTE_STOP_ORDER,
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