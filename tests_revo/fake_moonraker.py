"""Minimalny udawany Moonraker do podglądu KlipperScreena bez drukarki.
Użycie: python fake_moonraker.py [gotowa|drukowanie|drukowanie-<fixed|seq|plates|long|endless>|stol-drukowanie|blad]  (port 7125)"""
import asyncio
import json
import sys
import time

import websockets

MODE = sys.argv[1] if len(sys.argv) > 1 else "drukowanie"
TEST_FAZA = sys.argv[2] if len(sys.argv) > 2 else "idle"
printing = "drukowanie" in MODE
paused = MODE.endswith("-pauza")   # wstrzymany druk (PAUSE): ekran z RESUME
_M = MODE[:-len("-pauza")] if paused else MODE
koniec = MODE in ("koniec", "anulowany")   # wydruk zakończony / anulowany: ekran podsumowania
# Belt: tryb druku z [r]evo Slicer (drukowanie-<tryb>), dane makra FLAT_BELT jak w trakcie prawdziwego druku
BELT = {
    "fixed": ("obudowa-200x150_0.4_PETG.gcode", 6200, 2860, {"mode": "fixed", "unit": "segment", "target": 1, "file_units": 1}),
    "seq": ("PLA_59_kostek_30x30x39.gcode", 1500, 23 * 1500 + 640, {"mode": "sequential", "unit": "piece", "done": 23, "target": 59, "loop": True,
            "file_units": 1, "unit_sum": 23 * 1500, "unit_mark": 23 * 1500, "advance": 80.0}),
    "plates": ("PLA_3_stoly_15_kostek.gcode", 23820, 23820 + 11000, {"mode": "plates", "unit": "plate", "done": 1, "target": 3, "loop": True,
               "file_units": 1, "unit_sum": 23820, "unit_mark": 23820, "advance": 400.0}),
    "long": ("PLA_detal_200x20x600.gcode", 66480, 31000, {"mode": "long", "unit": "segment", "done": 1, "target": 3, "loop": False,
             "file_units": 3, "unit_sum": 22100, "unit_mark": 22100, "advance": 250.0}),
    "endless": ("PLA_tasma_320x2_10m.gcode", 1780, 31 * 1780 + 700, {"mode": "endless", "unit": "segment", "done": 31, "target": 70, "loop": True,
                "file_units": 1, "unit_sum": 31 * 1780, "unit_mark": 31 * 1780, "advance": 140.0, "start_len": 340.0, "min_target": 2, "endless": True}),
}
TRYB = _M.split("drukowanie-")[1] if "drukowanie-" in _M else ("fixed" if _M == "drukowanie" else "")
PLIK, EST, DUR, FB = BELT[TRYB] if TRYB in BELT else ("kostka-20mm_0.4_PETG.gcode", 6200, 2860, {})
PLA = TRYB not in ("", "fixed")

CONFIG = {
    "printer": {"kinematics": "corexy", "max_velocity": "500", "max_accel": "10000", "max_z_velocity": "15"},
    "stepper_x": {"position_max": "351", "position_min": "0"}, "stepper_y": {"position_max": "351", "position_min": "0"}, "stepper_z": {"position_max": "300", "position_min": "-10"},
    "extruder": {"filament_diameter": "1.75", "nozzle_diameter": "0.4"}, "heater_bed": {}, "temperature_sensor komora": {},
    "fan": {}, "heater_fan hotend_fan": {}, "neopixel status": {},
    "virtual_sdcard": {}, "print_stats": {}, "display_status": {}, "output_pin caselight": {}, "save_variables": {}, "gcode_macro _REVO_TEST": {},
}
STATUS = {
    "configfile": {"config": CONFIG, "settings": {"extruder": {"nozzle_diameter": 0.4, "filament_diameter": 1.75}}},
    "webhooks": {"state": "error" if MODE == "blad" else "ready",
                 "state_message": "MCU 'mcu' shutdown: Timer too close" if MODE == "blad" else "Printer is ready"},
    "extruder": {"temperature": (220.2 if PLA else 245.1) if printing else 24.0, "target": (220 if PLA else 245) if printing else 0, "power": 0.4},
    "heater_bed": {"temperature": (55.1 if PLA else 79.8) if printing else 23.0, "target": (55 if PLA else 80) if printing else 0, "power": 0.3},
    "temperature_sensor komora": {"temperature": 47.5 if printing else 22.0},
    "fan": {"speed": 0.6 if printing else 0},
    "print_stats": {"state": ("paused" if paused else "printing") if printing else (("cancelled" if MODE == "anulowany" else "complete") if koniec else "standby"),
                    "filename": PLIK if (printing or koniec) else "",
                    "print_duration": DUR, "total_duration": DUR + 40, "filament_used": 3120,
                    "info": {"current_layer": 84, "total_layer": 180}},
    "virtual_sdcard": {"progress": 0.46 if printing else 0, "is_active": printing, "file_position": 0},
    "display_status": {"progress": 0.46 if printing else 0, "message": None},
    "toolhead": {"homed_axes": "xyz", "position": [300, 300, 16.8, 0], "extruder": "extruder",
                 "max_velocity": 500, "max_accel": 10000},
    "gcode_move": {"gcode_position": [300, 300, 16.8, 0], "speed_factor": 1, "extrude_factor": 1,
                   "homing_origin": [0, 0, 0, 0]},
    "idle_timeout": {"state": "Printing" if printing else "Idle"},
    "pause_resume": {"is_paused": paused},
    "save_variables": {"variables": {"revo_first_run_done": 1, "revo_nozzle_diameter": 0.4, "revo_nozzle": "0.4 mosiadz"}},
    "gcode_macro _REVO_CFG": {"chamber": "temperature_sensor komora", "light_pin": "caselight", "belt_stepper": "" if "stol" in MODE else "belt_drives"},
    "output_pin caselight": {"value": 1.0},
    **({"gcode_macro FLAT_BELT": {"segments": 0, "advanced": 0.0, "finishing": False, "endless": False, "advance": 0.0, "total": 0, "unit": "segment",
                                   "mode": "", "done": 0, "target": 0, "loop": False, "min_target": 1, "file_units": 0, "start_len": 0.0,
                                   "unit_mark": 0.0, "unit_sum": 0.0, "last_unit": 0.0, "cleared": False, **FB}} if FB else {}),
    "gcode_macro _REVO_TEST": {
        "faza": TEST_FAZA, "step": 5, "last": "nie rusza",
        "ask": {"t": "Czy ruszył tylko ten silnik?", "ok": "DZIAŁA", "cmd": "REVO_TEST_ODP WYNIK=ok"},
        "plan": [["Krok %d" % i, "x", "", "", "conn", 60, 0, "opis"] for i in range(5)]
        + [["Silnik stepper_z1", "buzz", "stepper_z1", "", "motor_z1", 20, 1,
            "Silnik Z w narożniku tylny lewy drgnie 10 razy. Tylko ten narożnik bramy powinien się ruszyć."]]
        + [["Krok %d" % i, "x", "", "", "conn", 60, 0, "opis"] for i in range(25)],
        "summary": {"ok": 29, "total": 31, "done": 31, "stopped": "",
                    "results": {"Wentylator hotendu": "problem · hałas / drgania", "Czujnik filamentu": "problem · nie rusza"}},
    },
}

RESULTS = {
    "server.connection.identify": {"connection_id": 1},
    "server.info": {"klippy_connected": True, "klippy_state": STATUS["webhooks"]["state"],
                    "components": ["file_manager", "history", "update_manager"], "failed_components": [],
                    "registered_directories": ["gcodes", "config"], "warnings": [],
                    "missing_klippy_requirements": [], "moonraker_version": "v0.9", "api_version": [1, 5, 0]},
    "printer.info": {"state": STATUS["webhooks"]["state"], "state_message": STATUS["webhooks"]["state_message"],
                     "hostname": "jumpy-jupiter", "software_version": "v0.12.0", "klipper_path": "",
                     "python_path": "", "log_file": "", "config_file": ""},
    "printer.objects.list": {"objects": list(STATUS.keys())},
    "printer.gcode.help": {},
    "machine.system_info": {"system_info": {"cpu_info": {}, "distribution": {}, "network": {}}},
    "server.config": {"config": {"data_store": {"temperature_store_size": 1200}}},
    "server.temperature_store": {},
    "server.files.list": [{"path": PLIK, "modified": time.time(), "size": 1234567,
                           "permissions": "rw"}],
    "server.files.get_directory": {"dirs": [], "files": [], "disk_usage": {"total": 1, "used": 0, "free": 1},
                                   "root_info": {"name": "gcodes", "permissions": "rw"}},
    "server.files.roots": [{"name": "gcodes", "path": "/x", "permissions": "rw"}],
    "server.files.metadata": {"filename": PLIK, "estimated_time": EST,
                              "layer_height": 0.2, "object_height": 20, "thumbnails": []},
    "machine.update.status": {"version_info": {}, "busy": False},
    "server.history.list": {"jobs": [], "count": 0},
    "server.webcams.list": {"webcams": []},
}


def result_for(method, params):
    if method in ("printer.objects.query", "printer.objects.subscribe"):
        return {"eventtime": time.time(), "status": STATUS}
    if method in RESULTS:
        return RESULTS[method]
    return "ok"


async def handler(ws):
    async for msg in ws:
        req = json.loads(msg)
        if "id" not in req:
            continue
        await ws.send(json.dumps({"jsonrpc": "2.0", "id": req["id"],
                                  "result": result_for(req.get("method"), req.get("params"))}))


async def main():
    async with websockets.serve(handler, "127.0.0.1", 7125, process_request=None):
        await asyncio.Future()

asyncio.run(main())
