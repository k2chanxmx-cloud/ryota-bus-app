import csv
import os


GTFS_DIR = "gtfs"

STOPS_FILE = os.path.join(GTFS_DIR, "stops.txt")
TRIPS_FILE = os.path.join(GTFS_DIR, "trips.txt")
ROUTES_FILE = os.path.join(GTFS_DIR, "routes.txt")


ROUTE_IDS = {
    "kame26": "058",
    "nishi25": "075",
    "nishi27": "092",
}


def read_csv_dict(path):
    if not os.path.exists(path):
        return []

    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_stops():
    rows = read_csv_dict(STOPS_FILE)
    stops = {}

    for row in rows:
        stop_id = row.get("stop_id", "")
        stop_name = row.get("stop_name", "")

        if stop_id and stop_name:
            stops[stop_id] = stop_name

    return stops


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


STOPS = load_stops()
TRIPS = load_trips()
ROUTES = load_routes()


def get_stop_name(stop_id):
    if not stop_id:
        return "接近中"

    if stop_id in STOPS:
        return STOPS[stop_id]

    base_stop_id = stop_id.split("-")[0]

    if base_stop_id in STOPS:
        return STOPS[base_stop_id]

    return "接近中"


def get_route_key_by_route_id(route_id):
    for key, value in ROUTE_IDS.items():
        if value == route_id:
            return key

    return None


def get_route_label(route_key):
    labels = {
        "kame26": "亀26",
        "nishi25": "錦25",
        "nishi27": "錦27",
    }

    return labels.get(route_key, "不明")


def get_trip_info(trip_id):
    return TRIPS.get(trip_id, {})


def is_kameido_direction(trip_id):
    trip = get_trip_info(trip_id)

    headsign = trip.get("trip_headsign", "")
    direction_id = trip.get("direction_id", "")

    if "亀戸" in headsign:
        return True

    # fallback：route_id特定時のtrip_idを見る限り、まずは -1- を亀戸方面扱い
    if "-1-" in trip_id:
        return True

    return False


def get_direction_label(trip_id):
    if is_kameido_direction(trip_id):
        return "亀戸駅前方面"

    return "反対方面"


def is_target_direction(trip_id):
    return is_kameido_direction(trip_id)


def get_debug_status():
    return {
        "stops_loaded": len(STOPS),
        "trips_loaded": len(TRIPS),
        "routes_loaded": len(ROUTES),
        "stops_file_exists": os.path.exists(STOPS_FILE),
        "trips_file_exists": os.path.exists(TRIPS_FILE),
        "routes_file_exists": os.path.exists(ROUTES_FILE),
    }