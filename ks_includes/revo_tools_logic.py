# Revo OS – katalog komend serwisowych (wspólny z Revo Panel: revo-config/web/komendy.json). Bez GTK.
import json
import os
import re

PATHS = [os.path.expanduser("~/revo-config/web/komendy.json"),
         os.path.join(os.path.dirname(__file__), "..", "styles", "revo", "komendy.json")]
QUIET = ("GET_POSITION", "QUERY_ENDSTOPS", "QUERY_FILAMENT_SENSOR", "DUMP_TMC", "STATUS", "MEASURE_AXES_NOISE")


def load():
    for p in PATHS:
        if os.path.isfile(p):
            return json.load(open(p, encoding="utf-8"))
    return {"kategorie": []}


def sources(config_sections):
    """Listy do wyboru parametrów z sekcji konfiguracji Klippera."""
    secs = list(config_sections)
    steppers = [s for s in secs if re.match(r"^stepper_\w+$", s)] + (["extruder"] if "extruder" in secs else [])
    tmc = [s.split(" ", 1)[1] for s in secs if re.match(r"^tmc\d+ \S+$", s)]
    return {"steppers": steppers, "tmc": tmc}


def commands_ok(gcode, available):
    """Czy każda linia zaczyna się od komendy, którą maszyna zna (G/M-kody są zawsze)."""
    if available is None:
        return True
    avail = {a.upper() for a in available}
    for line in gcode.split("\n"):
        w = line.strip().split(" ")[0].upper()
        if not w or re.match(r"^[GM]\d+$", w):
            continue
        if w not in avail:
            return False
    return True


def visible(catalog, available, srcs):
    """Kategorie z komendami dostępnymi na tej maszynie (bez parametrów, dla których nie ma wyboru)."""
    out = []
    for k in catalog.get("kategorie", []):
        cmds = []
        for c in k.get("komendy", []):
            if not commands_ok(c["g"], available):
                continue
            p = c.get("p") or {}
            if any(isinstance(v, str) and not srcs.get(v) for v in p.values()):
                continue
            cmds.append(c)
        if cmds:
            out.append({"nazwa": k["nazwa"], "komendy": cmds})
    return out


def fill(gcode, name, value):
    return gcode.replace("{" + name + "}", str(value))


def needs_confirm(gcode):
    return gcode.split(" ")[0].split("\n")[0].upper() not in QUIET
