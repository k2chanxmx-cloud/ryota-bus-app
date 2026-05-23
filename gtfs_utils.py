import csv
import os
import zipfile
import io

GTFS_DIR = "gtfs"

STOPS_FILE = os.path.join(GTFS_DIR, "stops.txt")
TRIPS_FILE = os.path.join(GTFS_DIR, "trips.txt")
ROUTES_FILE = os.path.join(GTFS_DIR, "routes.txt")
STOP_TIMES_ZIP_FILE = os.path.join(GTFS_DIR, "stop_times.txt.zip")

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


def normalize_stop_id(stop_id):
    if not stop_id:
        return ""

    return stop_id.split("-")[0]


def read_csv_rows(path):
    if not os.path.exists(path):
        return

    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield row


def read_zip_csv_rows(zip_path, inner_name):
    if not os.path.exists(zip_path):
        return

    with zipfile.ZipFile(zip_path) as z:
        with z.open(inner_name) as f:
            text = io.TextIOWrapper(f, encoding="utf-8-sig")
            reader = csv.DictReader(text)
            for row in reader:
                yield row


def load_stops():
    stops = {}

    for row in read_csv_rows(STOPS_FILE) or []:
        stop_id = row.get("stop_id", "")
        stop_name = row.get("stop_name", "")

        if not stop_id or not stop_name:
            continue

        stops[stop_id] = stop_name
        stops[normalize_stop_id(stop_id)] = stop_name

    return stops


def load_trips():
    trips = {}
    target_trip_ids = set()

    target_route_ids = set(ROUTE_IDS.values())

    for row in read_csv_rows(TRIPS_FILE) or []:
        trip_id = row.get("trip_id", "")
        route_id = row.get("route_id", "")
        headsign = row.get("trip_headsign", "")
        direction_id = row.get("direction_id", "")

        if not trip_id:
            continue

        trips[trip_id] = {
            "route_id": route_id,
            "trip_headsign": headsign,
            "direction_id": direction_id,
        }

        if route_id in target_route_ids:
            target_trip_ids.add(trip_id)

    return trips, target_trip_ids


def load_routes():
    routes = {}

    for row in read_csv_rows(ROUTES_FILE) or []:
        route_id = row.get("route_id", "")

        if route_id:
            routes[route_id] = {
                "route_short_name": row.get("route_short_name", ""),
                "route_long_name": row.get("route_long_name", ""),
            }

    return routes


STOPS = load_stops()
TRIPS, TARGET_TRIP_IDS = load_trips()
ROUTES = load_routes()


def get_stop_name(stop_id):
    if not stop_id:
        return "接近中"

    if stop_id in STOPS:
        return STOPS[stop_id]

    base_id = normalize_stop_id(stop_id)

    if base_id in STOPS:
        return STOPS[base_id]

    return "接近中"


def load_stop_times():
    stop_times_by_trip = {}

    for row in read_zip_csv_rows(STOP_TIMES_ZIP_FILE, "stop_times.txt") or []:
        trip_id = row.get("trip_id", "")

        if trip_id not in TARGET_TRIP_IDS:
            continue

        stop_id = row.get("stop_id", "")

        if not stop_id:
            continue

        try:
            seq = int(row.get("stop_sequence", "999999"))
        except Exception:
            seq = 999999

        if trip_id not in stop_times_by_trip:
            stop_times_by_trip[trip_id] = []

        stop_times_by_trip[trip_id].append({
            "stop_id": stop_id,
            "base_stop_id": normalize_stop_id(stop_id),
            "stop_name": get_stop_name(stop_id),
            "stop_sequence": seq,
        })

    for trip_id in stop_times_by_trip:
        stop_times_by_trip[trip_id].sort(
            key=lambda x: x.get("stop_sequence", 999999)
        )

    return stop_times_by_trip


STOP_TIMES_BY_TRIP = load_stop_times()


def get_route_label(route_key):
    return ROUTE_LABELS.get(route_key, "不明")


def get_trip_info(trip_id):
    return TRIPS.get(trip_id, {})


def get_trip_stops(trip_id):
    return STOP_TIMES_BY_TRIP.get(trip_id, [])


def is_kameido_direction(trip_id):
    trip = get_trip_info(trip_id)
    headsign = trip.get("trip_headsign", "")

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


def is_valid_bus_for_target_stop(
    trip_id,
    current_stop_id,
    target_stop_name=TARGET_STOP_NAME,
    destination_name=DESTINATION_NAME,
):
    stops = get_trip_stops(trip_id)

    if not stops:
        return False

    current_index = find_stop_index_by_stop_id(stops, current_stop_id)
    target_index = find_stop_index_by_name(stops, target_stop_name)
    destination_index = find_stop_index_by_name(stops, destination_name)

    if target_index is None:
        return False

    if destination_index is None:
        return False

    # 亀戸七丁目 → 亀戸駅前 の順で走る便だけ採用
    if not target_index < destination_index:
        return False

    # 現在停留所が取れない場合は、方向と経路だけで一旦採用
    if current_index is None:
        return True

    # まだ亀戸七丁目に到達していない、または亀戸七丁目停車中の便だけ採用
    if current_index <= target_index:
        return True

    return False


def build_progress_stops(stops, current_index, target_index, window=2):
    if not stops:
        return []

    center = current_index if current_index is not None else target_index

    if center is None:
        return []

    # 現在地から目的停留所までを見せたいので、target_index が先にあるなら含める
    start = max(0, center - window)

    if target_index is not None and target_index > center:
        end = min(len(stops), target_index + 3)
    else:
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
            and current_index < index < target_index
        ):
            role = "between"

        result.append({
            "stop_name": item.get("stop_name", ""),
            "stop_id": item.get("stop_id", ""),
            "role": role,
        })

    return result


def get_bus_location_status(
    trip_id,
    current_stop_id,
    target_stop_name=TARGET_STOP_NAME,
):
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
            "progress_stops": build_progress_stops(
                stops,
                current_index,
                target_index,
            ),
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
        "progress_stops": build_progress_stops(
            stops,
            current_index,
            target_index,
        ),
    }


def find_nearest_scheduled_bus(
    buses,
    route_key,
    now_minutes,
):
    candidates = []

    for bus in buses:
        if bus.get("route_key") != route_key:
            continue

        try:
            h, m = map(int, bus.get("time", "").split(":"))
        except Exception:
            continue

        bus_minutes = h * 60 + m
        diff = bus_minutes - now_minutes

        if -15 <= diff <= 30:
            candidates.append({
                "bus": bus,
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
        "target_trips_loaded": len(TARGET_TRIP_IDS),
        "routes_loaded": len(ROUTES),
        "stop_times_trips_loaded": len(STOP_TIMES_BY_TRIP),
        "stops_file_exists": os.path.exists(STOPS_FILE),
        "trips_file_exists": os.path.exists(TRIPS_FILE),
        "routes_file_exists": os.path.exists(ROUTES_FILE),
        "stop_times_zip_exists": os.path.exists(STOP_TIMES_ZIP_FILE),
    }