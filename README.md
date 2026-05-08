# MSI Mystic Light RGB Web Control Panel

> A web-based RGB lighting controller for MSI PRO B760M-A DDR4 II (MS-7D99) motherboards on Linux.

![Platform](https://img.shields.io/badge/platform-Linux-blue)
![Python](https://img.shields.io/badge/python-3.8+-blue)
![License](https://img.shields.io/badge/license-MIT-green)

[中文文档](README_zh-cn.md)

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Motivation](#2-motivation)
3. [Problems Encountered](#3-problems-encountered)
4. [Implementation](#4-implementation)
5. [Features](#5-features)
6. [Installation & Usage](#6-installation--usage)
7. [File Structure](#7-file-structure)
8. [Known Limitations](#8-known-limitations)
9. [Acknowledgments](#9-acknowledgments)

---

## 1. Project Overview

This project is a **browser-based RGB control panel** for MSI Mystic Light motherboards that runs natively on Linux, listens on port `17700`, and requires **zero Windows dependencies**.

After discovering that no existing Linux tool could properly control the RGB lighting on my MSI PRO B760M-A DDR4 II motherboard, I reverse-engineered the USB HID protocol and built this panel from scratch. It provides independent zone control, 23 animation modes, color presets, scheduling, and a master on/off switch — all accessible from any browser on your network.

## 2. Motivation

**Hardware:** MSI PRO B760M-A DDR4 II (MS-7D99) + Intel i7-12700K + NVIDIA RTX 4060 Ti  
**OS:** Ubuntu 22.04.5 LTS (Jammy)

I wanted to control my motherboard's RGB lighting from Linux. The official **MSI Center** has no Linux version. I tried three common approaches and they all failed:

1. **OpenRGB PPA (v0.81)** — Device list empty. MS-7D99 is not supported.
2. **OpenRGB Git build (v0.9+)** — The device appears, but **lights do not turn on**.
3. **Windows VM + MSI Center** — USB passthrough works, but MSI Center detects the VM's non-MSI DMI and **refuses to load the Mystic Light module**.

The only remaining path was to talk to the hardware directly from Linux.

## 3. Problems Encountered

### 3.1 OpenRGB: Recognized but Lights Stay Off

OpenRGB's `MSIMysticLight185Controller::SetMode()` calculates `speedAndBrightnessFlags = (brightness << 2) | (speed & 0x03)`, but **never sets bit 7**.

By sniffing the USB Feature Reports written by MSI Center on Windows, I discovered the critical difference:

| Zone | OpenRGB writes | MSI Center writes | Difference |
|:---|:---|:---|:---|
| ONBOARD | `0x28` | `0xa8` | **Bit 7: 0 → 1** |
| JRAINBOW1 | `0x29` | `0x28` | Close |

`0xa8 = 0x28 | 0x80`. That single bit is the **hardware enable flag**. Without it, the controller receives the packet but keeps the physical output disabled.

**Verification:** Manually flipping that bit in a Python script made the lights turn on immediately.

### 3.2 Windows VM Route is a Dead End

Passing the USB device into a Windows 11 VM works at the USB level, but MSI Center performs a DMI/board vendor check. It sees a QEMU/virtual board, concludes "this is not an MSI motherboard," and **silently hides the Mystic Light control panel**. No workaround exists.

### 3.3 USB Device Conflicts with VM

When the Windows VM is running, it grabs the Mystic Light USB device via `usbfs`, making `/dev/hidraw2` disappear from the host. To reclaim it:

```bash
# Unbind from the VM / usbfs
echo '1-9' > /sys/bus/usb/drivers/usb/unbind
sleep 2
echo '1-9' > /sys/bus/usb/drivers/usb/bind
sleep 2
```

## 4. Implementation

### 4.1 Hardware Protocol Reverse Engineering

- **Device:** USB HID, `VID=0x1462`, `PID=0x7D99`
- **Node:** `/dev/hidraw2`
- **Packet:** 185-byte Feature Report, Report ID `0x52`

**Zone offset table:**

| Zone | Offset | Size | Notes |
|:---|:---|:---|:---|
| JRGB1 | 1 | 10 | |
| JPIPE1 | 11 | 10 | |
| JPIPE2 | 21 | 10 | |
| JRAINBOW1 | 31 | 11 | Extra byte at +10 |
| JRAINBOW2 | 42 | 11 | Extra byte at +10 |
| JCORSAIR | 53 | 11 | Disabled by default |
| JCOROUT | 64 | 10 | |
| ONBOARD | 74 | 10 | Special handling |
| ONBRD1–9 | 84–164 | 10 each | |
| JRGB2 | 174 | 10 | |
| save_data | 184 | 1 | 0 = preview, 1 = commit |

**Critical protocol rules discovered:**
1. **Enable bit:** `speedAndBrightnessFlags |= 0x80` (bit 7 must be set or the zone stays dark)
2. **Double-packet send:** First `save_data=0`, then `save_data=1`, with ≥50 ms delay
3. **ONBOARD special:** `colorFlags = 0x01` (not `0x80`), `padding = 4`
4. **JRAINBOW extra byte:** offset +10 = `100` (cycle/led count)

### 4.2 Software Stack

| Layer | Tech |
|:---|:---|
| Backend | Flask (Python 3), `hidapi` via system `python3-hid` |
| Frontend | Vanilla HTML/CSS/JS, Apple Design Language dark theme |
| API | RESTful JSON over HTTP, port `17700` |
| Deployment | systemd service, auto-start on boot, auto-restart on crash |

### 4.3 Core Logic

- **`controller.py`** — Thread-safe HID wrapper with timeout/reconnect. Handles the double-packet protocol, stale device detection, and state caching.
- **`server.py`** — Flask routes for `/api/set`, `/api/set_zone`, `/api/master`, `/api/status`, `/api/schedule`.
- **`scheduler.py`** — Optional time-based auto-switching (disabled by default).

## 5. Features

- **4 independent zones:** JRGB1, JRAINBOW1, JRAINBOW2, ONBOARD
- **23 animation modes** with Chinese localization: Static, Breathing, Flashing, Double Flashing, Lightning, Meteor, Color Ring, Planetary, Double Meteor, Energy, Blink, Clock, Color Pulse, Color Shift, Color Wave, Marquee, Rainbow Wave, Visor, Rainbow Flashing, Color Ring Double Flashing, Stack, Fire, Direct
- **32 color presets** in 3 groups (Common, Cyberpunk, Ambient)
- **Master on/off switch** with state save/restore
- **Second color support** — 15 dual-color modes automatically reveal a second color picker
- **Rainbow mode hints** — 4 built-in rainbow/preset modes show a warning that user-selected colors have no effect
- **Optional scheduling** — Auto-change by time of day

## 6. Installation & Usage

### Dependencies

```bash
sudo apt update
sudo apt install python3-flask python3-hid
```

### Install systemd service

```bash
sudo cp msi-rgb.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable msi-rgb.service
sudo systemctl start msi-rgb.service
```

### Access

Open `http://<your-server-ip>:17700` in any browser.

## 7. File Structure

```
msi_rgb/
├── controller.py          # HID hardware abstraction layer
├── server.py              # Flask web server & API
├── scheduler.py           # Time-based auto-switching
├── presets.json           # Color preset definitions
├── msi-rgb.service        # systemd unit file
├── templates/
│   └── index.html         # Web UI
├── static/
│   ├── css/style.css      # Apple-style dark theme
│   └── js/app.js          # Frontend logic
├── logs/                  # Runtime logs
├── REQUIREMENTS.md        # Full protocol reverse-engineering docs
└── AGENTS.md              # Context for AI assistants
```

## 8. Known Limitations

- **JRAINBOW2 / ONBOARD global sync:** The controller firmware treats these zones as "master" channels; changing them may propagate to other zones. This is hardware behavior, not a software bug.
- **Brightness/speed sliders are UI placeholders:** The controller's `speedAndBrightnessFlags` uses a fixed tested-working value (`0xa8`). The sliders send values but do not alter the hardware flag.
- **Root required:** Access to `/dev/hidraw2` requires root or custom udev rules.

## 9. Acknowledgments

- **OpenRGB** — Provided the initial reference for MSI Mystic Light controller structure (even though it didn't work for this board).
- **MSI Center (Windows)** — The source of truth for the correct USB packet values.

## License

MIT
