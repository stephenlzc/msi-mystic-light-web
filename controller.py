#!/usr/bin/env python3
"""
MSI Mystic Light HID Controller
Handles direct communication with the MSI Mystic Light USB device.
"""

import hid
import time
import threading
from typing import Optional, Tuple, List, Dict

# MSI Mystic Light USB IDs
MSI_VID = 0x1462
MSI_PID = 0x7D99
REPORT_ID = 0x52
PACKET_SIZE = 185

# Mode IDs (internal English keys)
MODES: Dict[str, int] = {
    "Direct": 0x25,
    "Static": 1,
    "Breathing": 2,
    "Flashing": 3,
    "Double flashing": 4,
    "Lightning": 6,
    "Meteor": 8,
    "Color ring": 11,
    "Planetary": 12,
    "Double meteor": 13,
    "Energy": 14,
    "Blink": 16,
    "Clock": 17,
    "Color pulse": 18,
    "Color shift": 19,
    "Color wave": 20,
    "Marquee": 21,
    "Rainbow wave": 26,
    "Visor": 27,
    "Rainbow flashing": 29,
    "Color ring double flashing": 30,
    "Stack": 31,
    "Fire": 32,
}

# Chinese display names
MODE_NAMES_CN: Dict[str, str] = {
    "Direct": "直接控制",
    "Static": "静态",
    "Breathing": "呼吸",
    "Flashing": "闪烁",
    "Double flashing": "双闪",
    "Lightning": "闪电",
    "Meteor": "流星",
    "Color ring": "彩色环",
    "Planetary": "行星",
    "Double meteor": "双流星",
    "Energy": "能量",
    "Blink": "眨眼",
    "Clock": "时钟",
    "Color pulse": "彩色脉冲",
    "Color shift": "颜色变换",
    "Color wave": "彩色波浪",
    "Marquee": "跑马灯",
    "Rainbow wave": "彩虹波浪",
    "Visor": "面罩",
    "Rainbow flashing": "彩虹闪烁",
    "Color ring double flashing": "彩色环双闪",
    "Stack": "堆叠",
    "Fire": "火焰",
}

# Zone definitions: (offset, size, name, has_extra_byte)
ZONES = [
    (1, 10, "JRGB1", False),
    (11, 10, "JPIPE1", False),
    (21, 10, "JPIPE2", False),
    (31, 11, "JRAINBOW1", True),
    (42, 11, "JRAINBOW2", True),
    (53, 11, "JCORSAIR", True),
    (64, 10, "JCOROUT", False),
    (74, 10, "ONBOARD", False),
    (84, 10, "ONBRD1", False),
    (94, 10, "ONBRD2", False),
    (104, 10, "ONBRD3", False),
    (114, 10, "ONBRD4", False),
    (124, 10, "ONBRD5", False),
    (134, 10, "ONBRD6", False),
    (144, 10, "ONBRD7", False),
    (154, 10, "ONBRD8", False),
    (164, 10, "ONBRD9", False),
    (174, 10, "JRGB2", False),
]

ZONE_MAP = {name: (off, size, has_extra) for off, size, name, has_extra in ZONES}

# Zones that should be disabled by default (matching Windows behavior)
DISABLED_ZONES = {"JCORSAIR", "ONBRD5"}

# Known working modes (based on user feedback, will expand as validated)
# All modes are kept available but we log which ones are used.


class MysticLightController:
    """Thread-safe controller for MSI Mystic Light RGB."""

    def __init__(self):
        self._lock = threading.RLock()
        self._dev: Optional[hid.device] = None
        self._last_state: Optional[bytearray] = None
        self._master_on: bool = True
        self._connect()

    def _connect(self) -> bool:
        """Try to open the HID device."""
        try:
            self._dev = hid.device()
            self._dev.open(MSI_VID, MSI_PID)
            print("[Controller] HID device opened")
            return True
        except Exception as e:
            print(f"[Controller] Failed to open device: {e}")
            self._dev = None
            return False

    def _disconnect(self) -> None:
        """Close device handle."""
        if self._dev:
            try:
                self._dev.close()
            except Exception:
                pass
            self._dev = None

    def _reconnect(self) -> bool:
        """Force reconnect."""
        self._disconnect()
        time.sleep(0.1)
        return self._connect()

    def _ensure_connected(self) -> bool:
        """Ensure device is open and valid."""
        if self._dev is None:
            return self._connect()
        try:
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                future = ex.submit(self._dev.get_feature_report, REPORT_ID, PACKET_SIZE)
                future.result(timeout=2.0)
            return True
        except Exception:
            print("[Controller] Device handle stale, reconnecting...")
            return self._reconnect()

    def _read_state(self) -> bytearray:
        """Read current controller state with timeout/reconnect."""
        if not self._ensure_connected():
            raise RuntimeError("Device not available")
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            future = ex.submit(self._dev.get_feature_report, REPORT_ID, PACKET_SIZE)
            try:
                raw = future.result(timeout=3.0)
            except concurrent.futures.TimeoutError:
                print("[Controller] HID read timeout, reconnecting...")
                self._reconnect()
                if not self._ensure_connected():
                    raise RuntimeError("Device not available after reconnect")
                future2 = ex.submit(self._dev.get_feature_report, REPORT_ID, PACKET_SIZE)
                raw = future2.result(timeout=3.0)

        buf = bytearray(raw)
        # Some backends prepend report_id, some don't. Normalize.
        if len(buf) == PACKET_SIZE - 1:
            buf = bytearray([REPORT_ID]) + buf
        elif len(buf) != PACKET_SIZE:
            print(f"[Controller] WARNING: Unexpected report size {len(buf)}, expected {PACKET_SIZE}")
            if len(buf) < PACKET_SIZE:
                buf = buf + bytearray(PACKET_SIZE - len(buf))
            else:
                buf = buf[:PACKET_SIZE]

        if buf[0] != REPORT_ID:
            print(f"[Controller] WARNING: Unexpected report ID {buf[0]:02x}, expected {REPORT_ID:02x}")

        return buf

    def _write_state(self, buf: bytearray) -> None:
        """Write state to controller using double-packet protocol with timeout."""
        if not self._ensure_connected():
            raise RuntimeError("Device not available")

        import concurrent.futures

        def _send(data):
            self._dev.send_feature_report(bytes(data))

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            # First packet: save_data = 0
            buf[184] = 0
            future = ex.submit(_send, bytes(buf))
            try:
                future.result(timeout=3.0)
            except concurrent.futures.TimeoutError:
                print("[Controller] HID write timeout (pkt1), reconnecting...")
                self._reconnect()
                if not self._ensure_connected():
                    raise RuntimeError("Device not available after reconnect")
                future2 = ex.submit(_send, bytes(buf))
                future2.result(timeout=3.0)

            time.sleep(0.05)

            # Second packet: save_data = 1
            buf[184] = 1
            future = ex.submit(_send, bytes(buf))
            try:
                future.result(timeout=3.0)
            except concurrent.futures.TimeoutError:
                print("[Controller] HID write timeout (pkt2), reconnecting...")
                self._reconnect()
                if not self._ensure_connected():
                    raise RuntimeError("Device not available after reconnect")
                future2 = ex.submit(_send, bytes(buf))
                future2.result(timeout=3.0)

            time.sleep(0.05)

    def _hex_to_rgb(self, hexcolor: str) -> Tuple[int, int, int]:
        hexcolor = hexcolor.lstrip("#")
        if len(hexcolor) != 6:
            raise ValueError("Color must be 6-digit hex")
        return (
            int(hexcolor[0:2], 16),
            int(hexcolor[2:4], 16),
            int(hexcolor[4:6], 16),
        )

    def _apply_zone(
        self,
        buf: bytearray,
        offset: int,
        has_extra: bool,
        mode: int,
        r: int,
        g: int,
        b: int,
        is_rainbow: bool,
        disabled: bool = False,
        r2: int = None,
        g2: int = None,
        b2: int = None,
    ) -> None:
        """Apply settings to a single zone in the buffer."""
        if disabled:
            buf[offset] = 0  # MSI_MODE_DISABLE
            buf[offset + 1] = 0
            buf[offset + 2] = 0
            buf[offset + 3] = 0
            buf[offset + 4] = 0x28
            buf[offset + 5] = 0
            buf[offset + 6] = 0
            buf[offset + 7] = 0
            buf[offset + 8] = 0x80
            buf[offset + 9] = 0
            if has_extra:
                buf[offset + 10] = 0
            return

        # Use color2 if provided, otherwise fallback to color1
        if r2 is None:
            r2, g2, b2 = r, g, b

        buf[offset] = mode
        buf[offset + 1] = r
        buf[offset + 2] = g
        buf[offset + 3] = b
        # CRITICAL: use fixed 0xa8 (tested working value) with bit 7 enabled
        buf[offset + 4] = 0xa8
        buf[offset + 5] = r2
        buf[offset + 6] = g2
        buf[offset + 7] = b2
        # For rainbow modes, bit 7 = 0 means random/rainbow color
        # For static modes, bit 7 = 1 means fixed color
        if is_rainbow:
            buf[offset + 8] = 0x00
        else:
            buf[offset + 8] = 0x80
        buf[offset + 9] = 0
        if has_extra:
            buf[offset + 10] = 100

    def set_all(
        self,
        mode: str = "Static",
        color: str = "FFFFFF",
        brightness: int = 100,
        speed: str = "medium",
        color2: str = None,
    ) -> None:
        """Set all zones to the same mode and color."""
        with self._lock:
            if not self._master_on and mode != "Static":
                return

            mode_id = MODES.get(mode, 1)
            r, g, b = self._hex_to_rgb(color)
            r2, g2, b2 = r, g, b
            if color2:
                r2, g2, b2 = self._hex_to_rgb(color2)
            is_rainbow = mode in [
                "Rainbow wave", "Color ring", "Planetary", "Double meteor",
                "Energy", "Color shift", "Rainbow flashing", "Fire",
                "Color ring double flashing", "Marquee",
            ]

            buf = self._read_state()

            for offset, size, name, has_extra in ZONES:
                disabled = name in DISABLED_ZONES
                self._apply_zone(
                    buf, offset, has_extra, mode_id, r, g, b,
                    is_rainbow, disabled, r2, g2, b2
                )

            # ONBOARD special handling (observed from Windows)
            buf[74] = mode_id
            buf[75] = r
            buf[76] = g
            buf[77] = b
            buf[78] = 0xa8
            buf[79] = r2
            buf[80] = g2
            buf[81] = b2
            buf[82] = 0x01  # SYNC_SETTING_ONBOARD
            buf[83] = 4     # padding = 4 (observed from Windows)

            self._write_state(buf)
            self._last_state = bytearray(buf)
            self._master_on = True
            print(f"[Controller] set_all: mode={mode} color={color} color2={color2}")

    def set_zone(
        self,
        zone: str,
        mode: str = "Static",
        color: str = "FFFFFF",
        brightness: int = 100,
        speed: str = "medium",
        color2: str = None,
    ) -> None:
        """Set a specific zone."""
        with self._lock:
            if zone not in ZONE_MAP:
                raise ValueError(f"Unknown zone: {zone}. Available: {list(ZONE_MAP.keys())}")

            mode_id = MODES.get(mode, 1)
            r, g, b = self._hex_to_rgb(color)
            r2, g2, b2 = r, g, b
            if color2:
                r2, g2, b2 = self._hex_to_rgb(color2)
            is_rainbow = mode in [
                "Rainbow wave", "Color ring", "Planetary", "Double meteor",
                "Energy", "Color shift", "Rainbow flashing", "Fire",
                "Color ring double flashing", "Marquee",
            ]

            # Use last known state as base to avoid reading potentially stale/corrupt hardware state
            if self._last_state is not None:
                buf = bytearray(self._last_state)
                print(f"[Controller] set_zone({zone}): using cached _last_state")
            else:
                buf = self._read_state()
                print(f"[Controller] set_zone({zone}): using fresh _read_state")

            offset, size, has_extra = ZONE_MAP[zone]
            disabled = zone in DISABLED_ZONES

            old_effect = buf[offset]
            old_color = f"{buf[offset+1]:02X}{buf[offset+2]:02X}{buf[offset+3]:02X}"

            self._apply_zone(
                buf, offset, has_extra, mode_id, r, g, b,
                is_rainbow, disabled, r2, g2, b2
            )

            # If setting ONBOARD, apply special params
            if zone == "ONBOARD":
                buf[82] = 0x01
                buf[83] = 4

            self._write_state(buf)
            self._last_state = bytearray(buf)
            self._master_on = True
            print(f"[Controller] set_zone({zone}): mode={mode} color={color} color2={color2} "
                  f"(old effect={old_effect} color={old_color})")

    def master_switch(self, state: bool) -> None:
        """Turn all lights on or off."""
        with self._lock:
            self._master_on = state
            if state:
                # Restore last state or default white
                if self._last_state is not None:
                    print(f"[Controller] master_switch(ON): restoring _last_state")
                    self._write_state(self._last_state)
                else:
                    print(f"[Controller] master_switch(ON): no _last_state, setting default white")
                    buf = self._read_state()
                    for offset, size, name, has_extra in ZONES:
                        disabled = name in DISABLED_ZONES
                        self._apply_zone(
                            buf, offset, has_extra, 1, 255, 255, 255,
                            False, disabled
                        )
                    buf[82] = 0x01
                    buf[83] = 4
                    self._write_state(buf)
                    self._last_state = bytearray(buf)
            else:
                # Save current state before turning off
                try:
                    self._last_state = self._read_state()
                    print(f"[Controller] master_switch(OFF): saved _last_state")
                except Exception as e:
                    print(f"[Controller] master_switch(OFF): failed to save state: {e}")
                # Turn off by setting all to black static
                buf = self._read_state()
                for offset, size, name, has_extra in ZONES:
                    buf[offset] = 1
                    buf[offset + 1] = 0
                    buf[offset + 2] = 0
                    buf[offset + 3] = 0
                    buf[offset + 4] = 0x28
                    buf[offset + 5] = 0
                    buf[offset + 6] = 0
                    buf[offset + 7] = 0
                    buf[offset + 8] = 0x80
                    buf[offset + 9] = 0
                    if has_extra:
                        buf[offset + 10] = 0
                self._write_state(buf)
                print(f"[Controller] master_switch(OFF): all zones black")

    def get_status(self) -> Dict:
        """Get current controller status."""
        with self._lock:
            try:
                buf = self._read_state()
                zones_status = {}
                for offset, size, name, has_extra in ZONES:
                    zones_status[name] = {
                        "effect": buf[offset],
                        "color": f"{buf[offset+1]:02X}{buf[offset+2]:02X}{buf[offset+3]:02X}",
                        "speed": f"0x{buf[offset+4]:02X}",
                        "flags": f"0x{buf[offset+8]:02X}",
                    }
                return {
                    "connected": True,
                    "master_on": self._master_on,
                    "zones": zones_status,
                }
            except Exception as e:
                return {
                    "connected": False,
                    "error": str(e),
                    "master_on": self._master_on,
                }

    def get_modes(self) -> List[str]:
        """Return list of available modes (Chinese names)."""
        return list(MODE_NAMES_CN.keys())

    def close(self) -> None:
        """Close the HID device."""
        with self._lock:
            self._disconnect()


# Singleton instance
_controller: Optional[MysticLightController] = None


def get_controller() -> MysticLightController:
    global _controller
    if _controller is None:
        _controller = MysticLightController()
    return _controller
