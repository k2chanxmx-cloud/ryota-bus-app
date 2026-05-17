import csv
import os


GTFS_DIR = "gtfs"

STOPS_FILE = os.path.join(GTFS_DIR, "stops.txt")
TRIPS_FILE = os.path.join(GTFS_DIR, "trips.txt")
ROUTES_FILE = os.path.join(GTFS_DIR, "routes.txt")
STOP_TIMES_FILE = os.path.join(GTFS_DIR, "stop_times.txt")


ROUTE_IDS = {
    "kame26": "058",
    "nishi25": "075",
    "nishi27": "092",
}


ROUTE_LABELS = {
    "kame26": "亀26",
    "nishi25": "錦25",
    "nishi27": "錦27",
}


TARGET_STOP_NAME = "亀戸七丁目"
DESTINATION_NAME = "亀戸駅前"


def read_csv_dict(path):
    if not os.path.exists(path):
        return []

    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def normalize_stop_id(stop_id):
    if not stop_id:
        return ""

    return stop_id.split("-")[0]


def load_stops():
    rows = read_csv_dict(STOPS_FILE)
    stops = {}
    stop_name_to_ids = {}

    for row in rows:
        stop_id = row.get("stop_id", "")
        stop_name = row.get("stop_name", "")

        if stop_id and stop_name:
            stops[stop_id] = stop_name

            base_id = normalize_stop_id(stop_id)
            if base_id:
                stops[base_id] = stop_name

            if stop_name not in stop_name_to_ids:
                stop_name_to_ids[stop_name] = []

            stop_name_to_ids[stop_name].append(stop_id)

            if base_id and base_id not in stop_name_to_ids[stop_name]:
                stop_name_to_ids[stop_name].append(base_id)

    return stops, stop_name_to_ids


def load_trips():
    rows = read_csv_dict(TRIPS_FILE)
    trips = {}

    for row in rows:
        trip_id = row.get("trip_id", "")
        route_id = row.get("route_id", "")
        trip_headsign = row.get("trip_headsign", "")
        direction_id = row.get("direction_id", "")

        if trip_id:
            trips[trip_id] = {
                "route_id": route_id,
                "trip_headsign": trip_headsign,
                "direction_id": direction_id,
            }

    return trips


def load_routes():
    rows = read_csv_dict(ROUTES_FILE)
    routes = {}

    for row in rows:
        route_id = row.get("route_id", "")
        route_short_name = row.get("route_short_name", "")
        route_long_name = row.get("route_long_name", "")

        if route_id:
            routes[route_id] = {
                "route_short_name": route_short_name,
                "route_long_name": route_long_name,
            }

    return routes


def load_stop_times():
    rows = read_csv_dict(STOP_TIMES_FILE)
    stop_times_by_trip = {}

    for row in rows:
        trip_id = row.get("trip_id", "")
        stop_id = row.get("stop_id", "")
        stop_sequence = row.get("stop_sequence", "")

        if not trip_id or not stop_id:
            continue

        try:
            seq = int(stop_sequence)
        except Exception:
            seq = 999999

        if trip_id not in stop_times_by_trip:
            stop_times_by_trip[trip_id] = []

        stop_times_by_trip[trip_id].append({
            "stop_id": stop_id,
            "base_stop_id": normalize_stop_id(stop_id),
            "stop_name": "",
            "stop_sequence": seq,
            "arrival_time": row.get("arrival_time", ""),
            "departure_time": row.get("departure_time", ""),
        })

    return stop_times_by_trip


STOPS, STOP_NAME_TO_IDS = load_stops()
TRIPS = load_trips()
ROUTES = load_routes()
STOP_TIMES_BY_TRIP = load_stop_times()


def attach_stop_names():
    for trip_id, stop_times in STOP_TIMES_BY_TRIP.items():
        for item in stop_times:
            item["stop_name"] = get_stop_name(item.get("stop_id", ""))

        stop_times.sort(key=lambda x: x.get("stop_sequence", 999999))


def get_stop_name(stop_id):
    if not stop_id:
        return "接近中"

    if stop_id in STOPS:
        return STOPS[stop_id]

    base_stop_id = normalize_stop_id(stop_id)

    if base_stop_id in STOPS:
        return STOPS[base_stop_id]

    return "接近中"


attach_stop_names()


def get_route_key_by_route_id(route_id):
    for key, value in ROUTE_IDS.items():
        if value == route_id:
            return key

    return None


def get_route_label(route_key):
    return ROUTE_LABELS.get(route_key, "不明")


def get_trip_info(trip_id):
    return TRIPS.get(trip_id, {})


def get_trip_stops(trip_id):
    return STOP_TIMES_BY_TRIP.get(trip_id, [])


def is_kameido_direction(trip_id):
    trip = get_trip_info(trip_id)

    headsign = trip.get("trip_headsign", "")
    direction_id = trip.get("direction_id", "")

    if "亀戸" in headsign:
        return True

    if DESTINATION_NAME in headsign:
        return True

    if "-1-" in trip_id:
        return True

    return False


def get_direction_label(trip_id):
    if is_kameido_direction(trip_id):
        return "亀戸駅前方面"

    return "反対方面"


def is_target_direction(trip_id):
    return is_kameido_direction(trip_id)


def find_stop_index_by_stop_id(stops, stop_id):
    if not stop_id:
        return None

    base_stop_id = normalize_stop_id(stop_id)

    for index, item in enumerate(stops):
        if item.get("stop_id") == stop_id:
            return index

        if item.get("base_stop_id") == base_stop_id:
            return index

    return None


def find_stop_index_by_name(stops, stop_name):
    for index, item in enumerate(stops):
        if item.get("stop_name") == stop_name:
            return index

    return None


def get_remaining_stop_count(trip_id, current_stop_id, target_stop_name=TARGET_STOP_NAME):
    stops = get_trip_stops(trip_id)

    if not stops:
        return None

    current_index = find_stop_index_by_stop_id(stops, current_stop_id)
    target_index = find_stop_index_by_name(stops, target_stop_name)

    if current_index is None or target_index is None:
        return None

    remaining = target_index - current_index

    return remaining


def get_bus_location_status(trip_id, current_stop_id, target_stop_name=TARGET_STOP_NAME):
    stops = get_trip_stops(trip_id)
    current_stop_name = get_stop_name(current_stop_id)

    if not stops:
        return {
            "current_stop_name": current_stop_name,
            "remaining_stop_count": None,
            "status_text": "接近中",
            "progress_stops": [],
        }

    current_index = find_stop_index_by_stop_id(stops, current_stop_id)
    target_index = find_stop_index_by_name(stops, target_stop_name)

    if current_index is None or target_index is None:
        return {
            "current_stop_name": current_stop_name,
            "remaining_stop_count": None,
            "status_text": "接近中",
            "progress_stops": build_progress_stops(stops, current_index, target_index),
        }

    remaining = target_index - current_index

    if remaining > 1:
        status_text = f"あと{remaining}停留所"
    elif remaining == 1:
        status_text = "次の停留所"
    elif remaining == 0:
        status_text = "まもなく到着"
    else:
        status_text = "通過済み"

    return {
        "current_stop_name": current_stop_name,
        "remaining_stop_count": remaining,
        "status_text": status_text,
        "progress_stops": build_progress_stops(stops, current_index, target_index),
    }


def build_progress_stops(stops, current_index, target_index, window=2):
    if not stops:
        return []

    if current_index is None and target_index is None:
        return []

    if current_index is None:
        center = target_index
    else:
        center = current_index

    if center is None:
        return []

    start = max(0, center - window)
    end = min(len(stops), center + window + 3)

    result = []

    for index in range(start, end):
        item = stops[index]
        role = "normal"

        if current_index is not None and index == current_index:
            role = "current"

        if target_index is not None and index == target_index:
            role = "target"

        if (
            current_index is not None
            and target_index is not None
            and index > current_index
            and index < target_index
        ):
            role = "between"

        result.append({
            "stop_name": item.get("stop_name", ""),
            "stop_id": item.get("stop_id", ""),
            "role": role,
        })

    return result


def find_nearest_scheduled_bus(buses, route_key, now_minutes):
    candidates = []

    for bus in buses:
        if bus.get("route_key") != route_key:
            continue

        time_text = bus.get("time", "")

        try:
            h, m = map(int, time_text.split(":"))
        except Exception:
            continue

        bus_minutes = h * 60 + m
        diff = bus_minutes - now_minutes

        if -15 <= diff <= 30:
            candidates.append({
                "bus": bus,
                "diff": diff,
                "abs_diff": abs(diff),
            })

    if not candidates:
        return None

    candidates.sort(key=lambda x: x["abs_diff"])

    return candidates[0]["bus"]


def get_debug_status():
    return {
        "stops_loaded": len(STOPS),
        "trips_loaded": len(TRIPS),
        "routes_loaded": len(ROUTES),
        "stop_times_trips_loaded": len(STOP_TIMES_BY_TRIP),
        "stops_file_exists": os.path.exists(STOPS_FILE),
        "trips_file_exists": os.path.exists(TRIPS_FILE),
        "routes_file_exists": os.path.exists(ROUTES_FILE),
        "stop_times_file_exists": os.path.exists(STOP_TIMES_FILE),
    }