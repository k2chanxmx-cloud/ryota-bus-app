import os
import csv
import zipfile

# =========================
# パス設定
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

GTFS_DIR = os.path.join(BASE_DIR, "gtfs")

ROUTES_FILE = os.path.join(GTFS_DIR, "routes.txt")
TRIPS_FILE = os.path.join(GTFS_DIR, "trips.txt")
STOPS_FILE = os.path.join(GTFS_DIR, "stops.txt")
STOP_TIMES_ZIP = os.path.join(GTFS_DIR, "stop_times.txt.zip")

# =========================
# デバッグ表示
# =========================
print("=== GTFS DEBUG START ===")
print("BASE_DIR =", BASE_DIR)
print("GTFS_DIR =", GTFS_DIR)

print("ROUTES_FILE EXISTS =", os.path.exists(ROUTES_FILE))
print("TRIPS_FILE EXISTS =", os.path.exists(TRIPS_FILE))
print("STOPS_FILE EXISTS =", os.path.exists(STOPS_FILE))
print("STOP_TIMES_ZIP EXISTS =", os.path.exists(STOP_TIMES_ZIP))

# =========================
# データ格納
# =========================
ROUTES = {}
TRIPS = {}
STOPS = {}
STOP_TIMES = {}

# =========================
# routes.txt 読み込み
# =========================
if os.path.exists(ROUTES_FILE):

    with open(ROUTES_FILE, encoding="utf-8-sig") as f:

        reader = csv.DictReader(f)

        for row in reader:

            route_id = row.get("route_id", "")

            ROUTES[route_id] = {
                "route_short_name": row.get("route_short_name", ""),
                "route_long_name": row.get("route_long_name", "")
            }

print("ROUTES LOADED =", len(ROUTES))

# =========================
# trips.txt 読み込み
# =========================
if os.path.exists(TRIPS_FILE):

    with open(TRIPS_FILE, encoding="utf-8-sig") as f:

        reader = csv.DictReader(f)

        for row in reader:

            trip_id = row.get("trip_id", "")

            TRIPS[trip_id] = {
                "route_id": row.get("route_id", ""),
                "trip_headsign": row.get("trip_headsign", "")
            }

print("TRIPS LOADED =", len(TRIPS))

# =========================
# stops.txt 読み込み
# =========================
if os.path.exists(STOPS_FILE):

    with open(STOPS_FILE, encoding="utf-8-sig") as f:

        reader = csv.DictReader(f)

        for row in reader:

            stop_id = row.get("stop_id", "")

            STOPS[stop_id] = {
                "stop_name": row.get("stop_name", ""),
                "stop_lat": row.get("stop_lat", ""),
                "stop_lon": row.get("stop_lon", "")
            }

print("STOPS LOADED =", len(STOPS))

# =========================
# stop_times.txt.zip 読み込み
# =========================
if os.path.exists(STOP_TIMES_ZIP):

    try:

        with zipfile.ZipFile(STOP_TIMES_ZIP) as z:

            print("ZIP CONTENTS =", z.namelist())

            txt_name = None

            for name in z.namelist():

                if name.endswith("stop_times.txt"):
                    txt_name = name
                    break

            print("FOUND stop_times.txt =", txt_name)

            if txt_name:

                with z.open(txt_name) as f:

                    reader = csv.DictReader(
                        (line.decode("utf-8-sig") for line in f)
                    )

                    row_count = 0

                    for row in reader:

                        trip_id = row.get("trip_id", "")
                        stop_id = row.get("stop_id", "")
                        stop_sequence = row.get("stop_sequence", "0")

                        if trip_id not in STOP_TIMES:
                            STOP_TIMES[trip_id] = []

                        STOP_TIMES[trip_id].append({
                            "stop_id": stop_id,
                            "stop_sequence": int(stop_sequence)
                        })

                        row_count += 1

                    print("STOP_TIMES ROWS =", row_count)

    except Exception as e:

        print("ZIP READ ERROR =", str(e))

else:

    print("STOP_TIMES_ZIP NOT FOUND")

print("STOP_TIMES TRIPS =", len(STOP_TIMES))

print("=== GTFS DEBUG END ===")


# =========================
# ユーティリティ
# =========================
def get_route_label(route_id):

    route_map = {
        "058": "亀26",
        "075": "錦25",
        "092": "錦27",
    }

    return route_map.get(route_id, "")


def get_trip_route_id(trip_id):

    trip = TRIPS.get(trip_id)

    if not trip:
        return None

    return trip.get("route_id")


def get_trip_headsign(trip_id):

    trip = TRIPS.get(trip_id)

    if not trip:
        return ""

    return trip.get("trip_headsign", "")


def get_stop_name(stop_id):

    stop = STOPS.get(stop_id)

    if not stop:
        return ""

    return stop.get("stop_name", "")


def get_progress_stops(trip_id):

    if trip_id not in STOP_TIMES:
        return []

    stop_list = STOP_TIMES[trip_id]

    sorted_list = sorted(
        stop_list,
        key=lambda x: x["stop_sequence"]
    )

    result = []

    for item in sorted_list:

        stop_name = get_stop_name(item["stop_id"])

        if stop_name:

            result.append(stop_name)

    return result


def is_before_or_at_target_stop(
    trip_id,
    current_stop_id,
    target_stop_name="亀戸七丁目"
):

    if trip_id not in STOP_TIMES:
        return False

    stop_list = sorted(
        STOP_TIMES[trip_id],
        key=lambda x: x["stop_sequence"]
    )

    current_seq = None
    target_seq = None

    for item in stop_list:

        stop_name = get_stop_name(item["stop_id"])

        if item["stop_id"] == current_stop_id:
            current_seq = item["stop_sequence"]

        if stop_name == target_stop_name:
            target_seq = item["stop_sequence"]

    if current_seq is None:
        return False

    if target_seq is None:
        return False

    return current_seq <= target_seq