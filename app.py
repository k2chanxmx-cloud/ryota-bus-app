from flask import Flask, render_template, jsonify
from datetime import datetime, timedelta, timezone
import os
import math
import requests
import jpholiday
from google.transit import gtfs_realtime_pb2

from gtfs_utils import (
    ROUTE_IDS,
    get_stop_name,
    get_route_label,
    get_direction_label,
    is_target_direction,
    is_valid_bus_for_target_stop,
    get_bus_location_status,
    find_nearest_scheduled_bus,
    get_debug_status,
)

app = Flask(__name__)

JST = timezone(timedelta(hours=9))

ODPT_API_KEY = os.environ.get("ODPT_API_KEY")
ODPT_REALTIME_URL = "https://api.odpt.org/api/v4/gtfs/realtime/ToeiBus"

STOP_NAME = "亀戸七丁目"
DESTINATION = "亀戸駅前"

TARGET_LAT = 35.6990
TARGET_LON = 139.8400
SEARCH_RADIUS_KM = 3.5

DISPLAY_GRACE_MINUTES = 15

ROUTES = {
    "all": "すべて",
    "kame26": "亀26",
    "nishi25": "錦25",
    "nishi27": "錦27",
}

BUS_TIMES = {
    "kame26": {
        "label": "亀26",
        "weekday": [
            "06:01", "06:26", "06:53",
            "07:13", "07:31", "07:46",
            "08:04", "08:19", "08:36", "08:55",
            "09:10", "09:30", "09:53",
            "10:20", "10:45",
            "11:25",
            "12:04", "12:44",
            "13:24",
            "14:04", "14:44",
            "15:15", "15:43",
            "16:04", "16:23", "16:39", "16:55",
            "17:12", "17:31", "17:51",
            "18:14", "18:37",
            "19:03", "19:40",
            "20:18", "20:52",
            "21:28",
            "22:01", "22:41",
        ],
        "saturday": [
            "06:01", "06:26", "06:51",
            "07:17", "07:42",
            "08:09", "08:34",
            "09:00", "09:29", "09:55",
            "10:20", "10:43",
            "11:06", "11:29", "11:52",
            "12:15", "12:37",
            "13:00", "13:27", "13:55",
            "14:23", "14:51",
            "15:19", "15:48",
            "16:18", "16:44",
            "17:09", "17:32", "17:54",
            "18:19", "18:52",
            "19:22", "19:53",
            "20:27",
            "21:02", "21:35",
            "22:09", "22:40",
        ],
        "holiday": [
            "06:01", "06:36",
            "07:07", "07:38",
            "08:11", "08:44",
            "09:18", "09:54",
            "10:33",
            "11:08", "11:29", "11:49",
            "12:08", "12:28", "12:48",
            "13:05", "13:27", "13:47",
            "14:13", "14:40",
            "15:05", "15:28", "15:48",
            "16:08", "16:28", "16:48",
            "17:08", "17:28", "17:56",
            "18:24", "18:54",
            "19:29",
            "20:02", "20:34",
            "21:06", "21:39",
            "22:11", "22:41",
        ],
    },

    "nishi25": {
        "label": "錦25",
        "weekday": [
            "06:18", "06:30", "06:42", "06:51",
            "07:00", "07:08", "07:15", "07:21", "07:27", "07:33", "07:38", "07:44", "07:49", "07:55",
            "08:00", "08:05", "08:10", "08:15", "08:21", "08:26", "08:31", "08:35", "08:40", "08:46", "08:51", "08:57",
            "09:03", "09:10", "09:17", "09:24", "09:31", "09:38", "09:45", "09:53",
            "10:01", "10:08", "10:16", "10:24", "10:32", "10:40", "10:48", "10:56",
            "11:04", "11:11", "11:19", "11:27", "11:35", "11:43", "11:51", "11:59",
            "12:07", "12:15", "12:23", "12:31", "12:39", "12:47", "12:55",
            "13:03", "13:11", "13:19", "13:27", "13:35", "13:43", "13:50", "13:58",
            "14:06", "14:14", "14:22", "14:30", "14:38", "14:46", "14:53",
            "15:01", "15:09", "15:17", "15:25", "15:33", "15:41", "15:48", "15:56",
            "16:04", "16:12", "16:20", "16:28", "16:35", "16:42", "16:48", "16:54",
            "17:00", "17:06", "17:12", "17:18", "17:24", "17:30", "17:36", "17:42", "17:48", "17:54",
            "18:00", "18:06", "18:13", "18:21", "18:29", "18:38", "18:47", "18:56",
            "19:04", "19:13", "19:22", "19:32", "19:41", "19:51",
            "20:01", "20:10", "20:20", "20:30", "20:41", "20:52",
            "21:03", "21:14", "21:25", "21:37", "21:49", "21:59",
            "22:11",
        ],
        "saturday": [
            "06:22", "06:32", "06:43", "06:54",
            "07:04", "07:13", "07:20", "07:30", "07:40", "07:49", "07:58",
            "08:07", "08:15", "08:22", "08:29", "08:37", "08:44", "08:51", "08:58",
            "09:06", "09:13", "09:20", "09:28", "09:35", "09:42", "09:50", "09:57",
            "10:04", "10:11", "10:18", "10:25", "10:32", "10:38", "10:45", "10:52", "10:59",
            "11:06", "11:13", "11:20", "11:27", "11:33", "11:39", "11:45", "11:51", "11:57",
            "12:03", "12:10", "12:17", "12:24", "12:31", "12:38", "12:45", "12:52", "12:59",
            "13:06", "13:13", "13:20", "13:27", "13:34", "13:41", "13:48", "13:55",
            "14:02", "14:09", "14:16", "14:23", "14:30", "14:36", "14:43", "14:50", "14:57",
            "15:04", "15:10", "15:17", "15:24", "15:31", "15:38", "15:45", "15:52", "15:59",
            "16:06", "16:13", "16:20", "16:27", "16:34", "16:40", "16:46", "16:52", "16:58",
            "17:04", "17:10", "17:16", "17:22", "17:28", "17:34", "17:41", "17:48", "17:55",
            "18:02", "18:10", "18:18", "18:26", "18:34", "18:42", "18:50", "18:59",
            "19:07", "19:15", "19:24", "19:33", "19:42", "19:51",
            "20:00", "20:08", "20:18", "20:29", "20:41", "20:54",
            "21:07", "21:20", "21:34", "21:49",
            "22:06",
        ],
        "holiday": [
            "06:22", "06:40",
            "07:00", "07:15", "07:29", "07:43", "07:55",
            "08:08", "08:20", "08:34", "08:45", "08:55",
            "09:06", "09:15", "09:24", "09:32", "09:39", "09:45", "09:51", "09:57",
            "10:03", "10:09", "10:15", "10:21", "10:27", "10:33", "10:39", "10:45", "10:51", "10:57",
            "11:04", "11:11", "11:18", "11:25", "11:32", "11:39", "11:46", "11:53",
            "12:00", "12:07", "12:14", "12:21", "12:28", "12:35", "12:42", "12:49", "12:56",
            "13:03", "13:10", "13:17", "13:23", "13:30", "13:37", "13:44", "13:51", "13:58",
            "14:05", "14:12", "14:19", "14:26", "14:33", "14:40", "14:47", "14:54",
            "15:00", "15:07", "15:13", "15:20", "15:26", "15:32", "15:38", "15:44", "15:49", "15:55",
            "16:01", "16:07", "16:13", "16:19", "16:25", "16:31", "16:37", "16:43", "16:49", "16:55",
            "17:01", "17:07", "17:13", "17:20", "17:27", "17:34", "17:42", "17:50", "17:58",
            "18:06", "18:13", "18:22", "18:30", "18:38", "18:46", "18:55",
            "19:03", "19:12", "19:22", "19:32", "19:42", "19:52",
            "20:03", "20:15", "20:27", "20:38", "20:51",
            "21:05", "21:19", "21:34", "21:49",
            "22:05",
        ],
    },

    "nishi27": {
        "label": "錦27",
        "weekday": [
            "07:07", "07:34", "07:55",
            "08:16", "08:33", "08:52",
            "09:13", "09:39",
            "10:05", "10:32",
            "11:00", "11:30",
            "12:02", "12:31", "12:59",
            "13:25", "13:54",
            "14:26", "14:59",
            "15:30", "15:58",
            "16:34",
            "17:07", "17:34",
            "18:05", "18:40",
            "19:20", "19:59",
            "20:39",
            "21:10",
        ],
        "saturday": [
            "07:03", "07:29", "07:56",
            "08:25", "08:55",
            "09:27",
            "10:01", "10:32",
            "11:08", "11:38",
            "12:15", "12:46",
            "13:18", "13:50",
            "14:26", "14:59",
            "15:32",
            "16:02", "16:36",
            "17:12", "17:54",
            "18:34",
            "19:17", "19:55",
            "20:37",
            "21:09",
        ],
        "holiday": [
            "07:04", "07:42",
            "08:14", "08:45",
            "09:17", "09:50",
            "10:14", "10:44",
            "11:07", "11:29", "11:52",
            "12:16", "12:48",
            "13:20", "13:48",
            "14:16", "14:50",
            "15:22", "15:52",
            "16:22", "16:59",
            "17:38",
            "18:22",
            "19:10", "19:53",
            "20:36",
            "21:06",
        ],
    },
}


def get_day_type():
    now = datetime.now(JST)

    if jpholiday.is_holiday(now.date()) or now.weekday() == 6:
        return "holiday"

    if now.weekday() == 5:
        return "saturday"

    return "weekday"


def time_to_minutes(t):
    h, m = map(int, t.split(":"))
    return h * 60 + m


def distance_km(lat1, lon1, lat2, lon2):
    r = 6371.0

    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_rad)
        * math.cos(lat2_rad)
        * math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return r * c


def get_remaining_buses(route_key):
    now = datetime.now(JST)
    now_minutes = now.hour * 60 + now.minute
    day_type = get_day_type()

    buses = []

    if route_key == "all":
        target_routes = BUS_TIMES.keys()
    else:
        target_routes = [route_key]

    for key in target_routes:
        route = BUS_TIMES[key]
        times = route.get(day_type, [])

        for t in times:
            bus_minutes = time_to_minutes(t)

            if bus_minutes + DISPLAY_GRACE_MINUTES >= now_minutes:
                buses.append({
                    "time": t,
                    "route": route["label"],
                    "route_key": key,
                    "status": "scheduled",
                    "realtime": None,
                })

    buses.sort(key=lambda x: time_to_minutes(x["time"]))

    return {
        "stop": STOP_NAME,
        "destination": DESTINATION,
        "route": ROUTES.get(route_key, "すべて"),
        "day_type": day_type,
        "now": now.strftime("%H:%M"),
        "buses": buses,
    }


def fetch_toei_realtime():
    if not ODPT_API_KEY:
        return {
            "ok": False,
            "reason": "ODPT_API_KEY が未設定です",
            "vehicles": [],
        }

    try:
        res = requests.get(
            ODPT_REALTIME_URL,
            params={"acl:consumerKey": ODPT_API_KEY},
            timeout=10,
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
            vehicle_id = vehicle.vehicle.id if vehicle.vehicle.id else ""
            stop_id = vehicle.stop_id if vehicle.stop_id else ""

            lat = None
            lon = None

            if vehicle.HasField("position"):
                lat = vehicle.position.latitude
                lon = vehicle.position.longitude

            route_key = None
            route_label = ""

            for key, target_route_id in ROUTE_IDS.items():
                if route_id == target_route_id:
                    route_key = key
                    route_label = get_route_label(key)
                    break

            location = get_bus_location_status(
                trip_id=trip_id,
                current_stop_id=stop_id,
                target_stop_name=STOP_NAME,
            )

            item = {
                "entity_id": entity.id,
                "trip_id": trip_id,
                "route_id": route_id,
                "route_key": route_key,
                "route_label": route_label,
                "direction": get_direction_label(trip_id),
                "vehicle_id": vehicle_id,
                "stop_id": stop_id,
                "stop_name": get_stop_name(stop_id),
                "current_stop_name": location["current_stop_name"],
                "remaining_stop_count": location["remaining_stop_count"],
                "status_text": location["status_text"],
                "progress_stops": location["progress_stops"],
                "latitude": lat,
                "longitude": lon,
                "distance_km": None,
            }

            if lat is not None and lon is not None:
                item["distance_km"] = round(
                    distance_km(TARGET_LAT, TARGET_LON, lat, lon),
                    3,
                )

            vehicles.append(item)

        return {
            "ok": True,
            "reason": "",
            "vehicles": vehicles,
        }

    except Exception as e:
        return {
            "ok": False,
            "reason": str(e),
            "vehicles": [],
        }


def get_realtime_buses(route_key):
    realtime = fetch_toei_realtime()

    if not realtime["ok"]:
        return {
            "ok": False,
            "reason": realtime["reason"],
            "vehicles": [],
        }

    vehicles = []

    for v in realtime["vehicles"]:
        if v.get("route_key") is None:
            continue

        if route_key != "all" and v.get("route_key") != route_key:
            continue

        trip_id = v.get("trip_id", "")
        current_stop_id = v.get("stop_id", "")

        if not is_target_direction(trip_id):
            continue

        if not is_valid_bus_for_target_stop(
            trip_id=trip_id,
            current_stop_id=current_stop_id,
        ):
            continue

        if v.get("distance_km") is None:
            continue

        if v["distance_km"] > SEARCH_RADIUS_KM:
            continue

        vehicles.append(v)

    vehicles.sort(
        key=lambda x: (
            x["remaining_stop_count"]
            if x.get("remaining_stop_count") is not None
            else 9999,
            x["distance_km"]
            if x.get("distance_km") is not None
            else 9999,
        )
    )

    return {
        "ok": True,
        "reason": "",
        "vehicles": vehicles,
    }


def get_fused_buses(route_key):
    scheduled = get_remaining_buses(route_key)
    realtime = get_realtime_buses(route_key)

    buses = scheduled["buses"]

    if not realtime["ok"]:
        scheduled["realtime_ok"] = False
        scheduled["realtime_reason"] = realtime["reason"]
        scheduled["realtime_vehicles"] = []
        return scheduled

    now = datetime.now(JST)
    now_minutes = now.hour * 60 + now.minute

    vehicles = realtime["vehicles"]
    used_vehicle_ids = set()

    for bus in buses:
        for vehicle in vehicles:
            if vehicle.get("vehicle_id") in used_vehicle_ids:
                continue

            if vehicle.get("route_key") != bus["route_key"]:
                continue

            matched_for_vehicle = find_nearest_scheduled_bus(
                buses=buses,
                route_key=vehicle["route_key"],
                now_minutes=now_minutes,
            )

            if matched_for_vehicle and matched_for_vehicle.get("time") == bus.get("time"):
                bus["status"] = "realtime"
                bus["realtime"] = vehicle
                used_vehicle_ids.add(vehicle.get("vehicle_id"))
                break

    scheduled["realtime_ok"] = True
    scheduled["realtime_reason"] = ""
    scheduled["realtime_vehicles"] = vehicles

    return scheduled


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/buses/<route_key>")
def buses(route_key):
    if route_key != "all" and route_key not in BUS_TIMES:
        return jsonify({"error": "invalid route"}), 404

    return jsonify(get_fused_buses(route_key))


@app.route("/api/realtime/<route_key>")
def realtime(route_key):
    if route_key != "all" and route_key not in BUS_TIMES:
        return jsonify({"error": "invalid route"}), 404

    result = get_realtime_buses(route_key)

    return jsonify({
        "stop": STOP_NAME,
        "destination": DESTINATION,
        "route": ROUTES.get(route_key, "すべて"),
        "now": datetime.now(JST).strftime("%H:%M"),
        "ok": result["ok"],
        "reason": result["reason"],
        "vehicles": result["vehicles"],
    })


@app.route("/api/realtime-debug")
def realtime_debug():
    realtime = fetch_toei_realtime()
    vehicles = realtime.get("vehicles", [])

    nearby = [
        v for v in vehicles
        if v.get("distance_km") is not None
        and v["distance_km"] <= SEARCH_RADIUS_KM
    ]

    nearby.sort(
        key=lambda x: x["distance_km"]
        if x.get("distance_km") is not None
        else 9999
    )

    route_summary = {}

    for v in nearby:
        route_id = v.get("route_id") or "unknown"

        if route_id not in route_summary:
            route_summary[route_id] = {
                "route_id": route_id,
                "count": 0,
                "vehicles": [],
            }

        route_summary[route_id]["count"] += 1
        route_summary[route_id]["vehicles"].append(v)

    return jsonify({
        "ok": realtime["ok"],
        "reason": realtime["reason"],
        "gtfs": get_debug_status(),
        "target": {
            "name": STOP_NAME,
            "latitude": TARGET_LAT,
            "longitude": TARGET_LON,
            "search_radius_km": SEARCH_RADIUS_KM,
        },
        "all_count": len(vehicles),
        "nearby_count": len(nearby),
        "nearby_sample": nearby[:40],
        "route_summary": list(route_summary.values()),
    })


if __name__ == "__main__":
    app.run(debug=True)