#!/usr/bin/env python3
"""
Scheduler for automatic light changes based on time of day.
"""

import json
import os
import threading
import time
from datetime import datetime
from typing import Dict, Any, Optional


DEFAULT_SCHEDULE = {
    "enabled": False,
    "slots": [
        {
            "start": "06:00",
            "end": "18:00",
            "color": "E8F4FF",
            "mode": "Static",
            "brightness": 100,
        },
        {
            "start": "18:00",
            "end": "22:00",
            "color": "FFCC80",
            "mode": "Breathing",
            "brightness": 80,
        },
        {
            "start": "22:00",
            "end": "06:00",
            "color": "4A0000",
            "mode": "Static",
            "brightness": 30,
        },
    ]
}

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schedule.json")


class ScheduleManager:
    """Background thread that checks time and auto-adjusts lights."""

    def __init__(self, controller):
        self.controller = controller
        self.config: Dict[str, Any] = self._load_config()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._last_slot: Optional[int] = None

    def _load_config(self) -> Dict[str, Any]:
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return dict(DEFAULT_SCHEDULE)

    def _save_config(self) -> None:
        with open(CONFIG_PATH, "w") as f:
            json.dump(self.config, f, indent=2)

    def get_config(self) -> Dict[str, Any]:
        return self.config

    def update_config(self, data: Dict[str, Any]) -> None:
        self.config = data
        self._save_config()

    def _time_to_minutes(self, t: str) -> int:
        """Convert 'HH:MM' to minutes since midnight."""
        h, m = map(int, t.split(":"))
        return h * 60 + m

    def _get_current_slot(self) -> Optional[int]:
        """Determine which time slot we are currently in."""
        now = datetime.now()
        current_minutes = now.hour * 60 + now.minute

        for i, slot in enumerate(self.config.get("slots", [])):
            start = self._time_to_minutes(slot["start"])
            end = self._time_to_minutes(slot["end"])

            if start <= end:
                # Normal range (e.g., 06:00 - 18:00)
                if start <= current_minutes < end:
                    return i
            else:
                # Overnight range (e.g., 22:00 - 06:00)
                if current_minutes >= start or current_minutes < end:
                    return i
        return None

    def _apply_slot(self, slot_index: int) -> None:
        """Apply the settings for a given time slot."""
        slots = self.config.get("slots", [])
        if slot_index < 0 or slot_index >= len(slots):
            return

        slot = slots[slot_index]
        color = slot.get("color", "FFFFFF")
        mode = slot.get("mode", "Static")
        brightness = slot.get("brightness", 100)

        try:
            self.controller.set_all(mode, color, brightness)
        except Exception as e:
            print(f"[Scheduler] Failed to apply slot {slot_index}: {e}")

    def _run(self) -> None:
        """Main scheduler loop."""
        while not self._stop_event.is_set():
            if self.config.get("enabled", False):
                slot = self._get_current_slot()
                if slot is not None and slot != self._last_slot:
                    self._apply_slot(slot)
                    self._last_slot = slot
            else:
                self._last_slot = None

            # Check every 60 seconds
            self._stop_event.wait(60)

    def start(self) -> None:
        """Start the scheduler background thread."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the scheduler."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)
