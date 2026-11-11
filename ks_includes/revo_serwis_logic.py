# Revo OS – przypomnienia serwisowe liczone z godzin pracy maszyny (agent /status → hours).
# Ostatnie wykonanie przeglądu: save_variables revo_serwis_<klucz> = godziny maszyny w chwili ZROBIONE.

ITEMS = [  # klucz, nazwa (belt / standard), co ile h, co zrobić
    ("dysza", "Nozzle", "Nozzle", 200,
     "Check the nozzle: wear, leaks, hot tightening. Replace it if the bore is worn out."),
    ("osie", "Belt, belts and axes", "Belts and axes", 500,
     "Check belt tension, guides and axis play. Clean and lubricate the guides."
     " On the Belt also check the conveyor belt and its tracking."),
    ("pelny", "Full service", "Full service", 1000,
     "Full inspection: electronics, wiring, fans, heating, calibration. Best done with Revotech service."),
]
WARN_BEFORE = 0.1   # ostrzeżenie „wkrótce” na ostatnie 10% interwału


def status(hours, variables, is_belt=True):
    if hours is None:
        return []
    out = []
    for key, n_belt, n_std, every, desc in ITEMS:
        last = float((variables or {}).get(f"revo_serwis_{key}", 0) or 0)
        since = max(0.0, float(hours) - last)
        left = every - since
        state = "po terminie" if left <= 0 else ("wkrótce" if left <= every * WARN_BEFORE else "ok")
        out.append({"key": key, "name": n_belt if is_belt else n_std, "every": every, "since": since,
                    "left": left, "state": state, "desc": desc, "fraction": min(1.0, since / every)})
    return out


def due(items):
    return [i for i in items if i["state"] == "po terminie"]


def banner(items):
    d = due(items)
    if not d:
        return ""
    return "SERVICE DUE: " + ", ".join(i["name"] for i in d)


def done_gcode(key, hours):
    return f"SAVE_VARIABLE VARIABLE=revo_serwis_{key} VALUE={round(float(hours), 1)}"
