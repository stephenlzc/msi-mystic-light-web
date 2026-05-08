#!/usr/bin/env python3
"""
MSI Mystic Light RGB Web Control Panel
Flask backend serving the web UI and API.
"""

import json
import os
import sys
import threading
import time
from datetime import datetime
from typing import Dict, Any

from flask import Flask, render_template, request, jsonify, send_from_directory

from controller import get_controller, MODES, MODE_NAMES_CN
from scheduler import ScheduleManager

# Configuration
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(APP_ROOT, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["JSON_SORT_KEYS"] = False

# Load presets
PRESETS_PATH = os.path.join(APP_ROOT, "presets.json")
try:
    with open(PRESETS_PATH, "r") as f:
        PRESETS_DATA = json.load(f)
except Exception:
    PRESETS_DATA = {"groups": []}

# Schedule manager
schedule_manager: ScheduleManager = None


def log_event(message: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}\n"
    print(line.strip())
    with open(os.path.join(LOG_DIR, "server.log"), "a") as f:
        f.write(line)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/modes")
def api_modes():
    # Return both English internal keys and Chinese display names
    modes_list = []
    for key in MODES.keys():
        modes_list.append({
            "key": key,
            "name": MODE_NAMES_CN.get(key, key)
        })
    return jsonify({"modes": modes_list})


@app.route("/api/presets")
def api_presets():
    return jsonify(PRESETS_DATA)


@app.route("/api/status")
def api_status():
    ctrl = get_controller()
    return jsonify(ctrl.get_status())


@app.route("/api/set", methods=["POST"])
def api_set():
    try:
        data = request.get_json() or {}
        mode = data.get("mode", "Static")
        color = data.get("color", "FFFFFF").lstrip("#")
        brightness = int(data.get("brightness", 100))
        speed = data.get("speed", "medium")
        color2 = data.get("color2", "").lstrip("#") or None

        ctrl = get_controller()
        ctrl.set_all(mode, color, brightness, speed, color2)

        log_event(f"SET mode={mode} color={color} color2={color2} brightness={brightness} speed={speed}")
        return jsonify({"success": True, "mode": mode, "color": color, "color2": color2})
    except Exception as e:
        log_event(f"SET ERROR: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/set_zone", methods=["POST"])
def api_set_zone():
    try:
        data = request.get_json() or {}
        zone = data.get("zone", "JRGB1")
        mode = data.get("mode", "Static")
        color = data.get("color", "FFFFFF").lstrip("#")
        brightness = int(data.get("brightness", 100))
        speed = data.get("speed", "medium")
        color2 = data.get("color2", "").lstrip("#") or None

        ctrl = get_controller()
        ctrl.set_zone(zone, mode, color, brightness, speed, color2)

        log_event(f"SET_ZONE zone={zone} mode={mode} color={color} color2={color2}")
        return jsonify({"success": True, "zone": zone, "mode": mode, "color": color, "color2": color2})
    except Exception as e:
        log_event(f"SET_ZONE ERROR: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/master", methods=["POST"])
def api_master():
    try:
        data = request.get_json() or {}
        state = data.get("state", "on")
        on = state.lower() in ("on", "true", "1")

        ctrl = get_controller()
        ctrl.master_switch(on)

        log_event(f"MASTER state={'ON' if on else 'OFF'}")
        return jsonify({"success": True, "state": "on" if on else "off"})
    except Exception as e:
        log_event(f"MASTER ERROR: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/schedule", methods=["GET", "POST"])
def api_schedule():
    global schedule_manager
    if request.method == "GET":
        return jsonify(schedule_manager.get_config() if schedule_manager else {})

    try:
        data = request.get_json() or {}
        if schedule_manager:
            schedule_manager.update_config(data)
            log_event("SCHEDULE updated")
        return jsonify({"success": True})
    except Exception as e:
        log_event(f"SCHEDULE ERROR: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


def init_scheduler():
    global schedule_manager
    schedule_manager = ScheduleManager(get_controller())
    schedule_manager.start()
    log_event("Scheduler started")


if __name__ == "__main__":
    log_event("=== MSI RGB Control Panel starting ===")
    try:
        # Quick hardware check
        ctrl = get_controller()
        status = ctrl.get_status()
        if status.get("connected"):
            log_event("Hardware connected successfully")
        else:
            log_event("WARNING: Hardware not connected")
    except Exception as e:
        log_event(f"WARNING: Hardware init error: {e}")

    init_scheduler()

    # Run Flask
    app.run(host="0.0.0.0", port=17700, debug=False, threaded=True)
