# Revo OS – przypomnienia serwisowe liczone z godzin pracy maszyny (agent /status → hours).
# Ostatnie wykonanie przeglądu: save_variables revo_serwis_<klucz> = godziny maszyny w chwili ZROBIONE.

ITEMS = [  # klucz, nazwa (belt / standard), co ile h, co zrobić
    ("dysza", "Dysza", "Dysza", 200,
     "Sprawdź dyszę: zużycie, wycieki, dokręcenie na gorąco. Wymień, jeśli otwór jest rozbity."),
    ("osie", "Taśma, pasy i osie", "Pasy i osie", 500,
     "Sprawdź naciąg pasów, prowadnice i luzy osi. Wyczyść i nasmaruj prowadnice."
     " Na Belcie sprawdź też taśmę i jej prowadzenie."),
    ("pelny", "Pełny serwis", "Pełny serwis", 1000,
     "Pełny przegląd: elektronika, przewody, wentylatory, grzanie, kalibracja. Najlepiej z serwisem Revotech."),
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
    return "PRZEGLĄD: " + ", ".join(i["name"] for i in d)


def done_gcode(key, hours):
    return f"SAVE_VARIABLE VARIABLE=revo_serwis_{key} VALUE={round(float(hours), 1)}"
