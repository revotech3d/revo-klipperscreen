"""Minimalny udawany Moonraker do podglądu KlipperScreena bez drukarki.
Użycie: python fake_moonraker.py [gotowa|drukowanie|blad]  (port 7125)"""
import asyncio
import json
import sys
import time

import websockets

MODE = sys.argv[1] if len(sys.argv) > 1 else "drukowanie"
printing = MODE == "drukowanie"

CONFIG = {
    "extruder": {"filament_diameter": "1.75", "nozzle_diameter": "0.4"}, "heater_bed": {}, "temperature_sensor komora": {},
    "fan": {}, "heater_fan hotend_fan": {}, "neopixel status": {},
    "virtual_sdcard": {}, "print_stats": {}, "display_status": {}, "output_pin caselight": {}, "save_variables": {},
}
STATUS = {
    "configfile": {"config": CONFIG, "settings": {"extruder": {"nozzle_diameter": 0.4, "filament_diameter": 1.75}}},
    "webhooks": {"state": "error" if MODE == "blad" else "ready",
                 "state_message": "MCU 'mcu' shutdown: Timer too close" if MODE == "blad" else "Printer is ready"},
    "extruder": {"temperature": 245.1 if printing else 24.0, "target": 245 if printing else 0, "power": 0.4},
    "heater_bed": {"temperature": 79.8 if printing else 23.0, "target": 80 if printing else 0, "power": 0.3},
    "temperature_sensor komora": {"temperature": 47.5 if printing else 22.0},
    "fan": {"speed": 0.6 if printing else 0},
    "print_stats": {"state": "printing" if printing else "standby",
                    "filename": "kostka-20mm_0.4_PETG.gcode" if printing else "",
                    "print_duration": 2860, "total_duration": 2900, "filament_used": 3120,
                    "info": {"current_layer": 84, "total_layer": 180}},
    "virtual_sdcard": {"progress": 0.46 if printing else 0, "is_active": printing, "file_position": 0},
    "display_status": {"progress": 0.46 if printing else 0, "message": None},
    "toolhead": {"homed_axes": "xyz", "position": [300, 300, 16.8, 0], "extruder": "extruder",
                 "max_velocity": 500, "max_accel": 10000},
    "gcode_move": {"gcode_position": [300, 300, 16.8, 0], "speed_factor": 1, "extrude_factor": 1,
                   "homing_origin": [0, 0, 0, 0]},
    "idle_timeout": {"state": "Printing" if printing else "Idle"},
    "pause_resume": {"is_paused": False},
    "save_variables": {"variables": {"revo_nozzle_diameter": 0.4, "revo_nozzle": "0.4 mosiadz"}},
    "gcode_macro _REVO_CFG": {"chamber": "temperature_sensor komora", "light_pin": "caselight"},
    "output_pin caselight": {"value": 1.0},
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
    "server.files.list": [{"path": "kostka-20mm_0.4_PETG.gcode", "modified": time.time(), "size": 1234567,
                           "permissions": "rw"}],
    "server.files.get_directory": {"dirs": [], "files": [], "disk_usage": {"total": 1, "used": 0, "free": 1},
                                   "root_info": {"name": "gcodes", "permissions": "rw"}},
    "server.files.roots": [{"name": "gcodes", "path": "/x", "permissions": "rw"}],
    "server.files.metadata": {"filename": "kostka-20mm_0.4_PETG.gcode", "estimated_time": 6200,
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
