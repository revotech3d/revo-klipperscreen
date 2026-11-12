# Revo OS – logika paska statusu (bez GTK, testowalna)
import json
import time
import urllib.request

# stan -> (kolor RGB 0..1, miganie)
COLORS = {
    "gotowa": ((0.243, 0.839, 0.388), False),      # #3ED663 (czystsza zieleń na ekranie DSI)
    "drukowanie": ((0.949, 0.953, 0.961), False),  # #F2F3F5
    "nagrzewanie": ((0.941, 0.627, 0.294), False),  # #F0A04B
    "pauza": ((0.941, 0.627, 0.294), True),
    "praca": ((0.941, 0.627, 0.294), True),        # kalibracja, test, bazowanie poza wydrukiem – nie dotykać

    "blad": ((1.0, 0.302, 0.322), True),            # #FF4D52
    "serwis": ((0.357, 0.659, 1.0), False),         # #5BA8FF
    "offline": ((0.604, 0.627, 0.659), False),      # #9AA0A8
}

SEGMENTS = 40


def machine_state(printer_state, print_state, heating=False, service=False, busy=False):
    """printer_state: stan Klippera (ready/error/shutdown/startup/disconnected),
    print_state: print_stats.state (standby/printing/paused/complete/cancelled/error)."""
    if printer_state in ("error", "shutdown"):
        return "blad"
    if printer_state not in ("ready", "printing", "paused"):
        return "offline"
    if print_state == "error":
        return "blad"
    if service:
        return "serwis"
    if print_state == "paused":
        return "pauza"
    if print_state == "printing":
        return "nagrzewanie" if heating else "drukowanie"
    if busy:   # idle_timeout = Printing bez wydruku: kalibracja (MPC, mapa stołu, input shaper), test, bazowanie
        return "praca"
    return "gotowa"


# Kalibracje, które stoją w miejscu (idle_timeout zostaje „Ready”) – rozpoznawane po komunikatach Klippera
_CAL_START = ("Waiting for heater to settle", "Performing heatup test", "Performing ambient transfer",
              "Waiting for temperature to stabilize", "PID parameters", "Starting PID calibration")
_CAL_END = ("Finished MPC", "Finished PID", "The SAVE_CONFIG command will update")


def calibration_from_response(line, current):
    """Na podstawie linii odpowiedzi G-code: czy trwa kalibracja grzałki (True/False)."""
    if line.startswith("!! ") or any(k in line for k in _CAL_END):
        return False
    if any(k in line for k in _CAL_START):
        return True
    return current


def lit_segments(state, progress=0.0, segments=SEGMENTS):
    """Ile segmentów świeci: w druku – postęp, w innych stanach – cały pasek."""
    if state in ("drukowanie", "nagrzewanie", "pauza"):
        p = max(0.0, min(1.0, progress or 0.0))
        return max(1, round(p * segments))
    return segments


def blink_on(state, t=None):
    """Miganie 1 Hz dla stanów alarmowych."""
    if not COLORS[state][1]:
        return True
    t = time.monotonic() if t is None else t
    return int(t * 2) % 2 == 0


def agent_service_active(url="http://127.0.0.1:7130/status", timeout=0.3):
    """Pyta lokalnego agenta Revo, czy trwa tryb serwisowy. Brak agenta = False."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return bool(json.loads(r.read().decode()).get("service"))
    except Exception:
        return False
