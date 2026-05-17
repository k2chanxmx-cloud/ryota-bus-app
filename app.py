from flask import Flask, render_template, jsonify
from datetime import datetime, timedelta, timezone
import jpholiday

app = Flask(__name__)

JST = timezone(timedelta(hours=9))

STOP_NAME = "亀戸七丁目"
DESTINATION = "亀戸駅前"

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
        "saturday": [],
        "holiday": [],
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
        "saturday": [],
        "holiday": [],
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
        "saturday": [],
        "holiday": [],
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


def get_remaining_buses(route_key):
    now = datetime.now(JST)
    now_minutes = now.hour * 60 + now.minute
    day_type = get_day_type()

    buses = []

    target_routes = BUS_TIMES.keys() if route_key == "all" else [route_key]

    for key in target_routes:
        route = BUS_TIMES[key]
        times = route.get(day_type, [])

        for t in times:
            if time_to_minutes(t) >= now_minutes:
                buses.append({
                    "time": t,
                    "route": route["label"],
                    "route_key": key,
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


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/buses/<route_key>")
def buses(route_key):
    if route_key != "all" and route_key not in BUS_TIMES:
        return jsonify({"error": "invalid route"}), 404

    return jsonify(get_remaining_buses(route_key))


if __name__ == "__main__":
    app.run(debug=True)