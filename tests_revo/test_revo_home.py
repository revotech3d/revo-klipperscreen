import importlib.util, pathlib
spec = importlib.util.spec_from_file_location("lg", pathlib.Path(__file__).parents[1] / "ks_includes/revo_home_logic.py")
lg = importlib.util.module_from_spec(spec); spec.loader.exec_module(lg)

class P:
    def __init__(s, state, data): s.state, s.d = state, data
    def get_stat(s, o, k=None):
        v = s.d.get(o, {}); return v.get(k) if k else v

D = {"print_stats": {"state": "standby"}, "extruder": {"temperature": 21.4, "target": 0},
     "heater_bed": {"temperature": 20.1, "target": 0}, "save_variables": {"variables": {"revo_nozzle_diameter": 0.4}},
     "gcode_macro _REVO_CFG": {"chamber": "temperature_sensor enclosure_temp", "light_pin": "caselight"},
     "temperature_sensor enclosure_temp": {"temperature": 20.9}, "output_pin caselight": {"value": 1.0}}

def test_ready():
    v = lg.view(P("ready", D), 12.4)
    assert v["state"] == "GOTOWA" and v["nozzle_size"] == "Ø0.4" and v["chamber_temp"] == "21°"
    assert v["light"] == "Wł." and v["info"] == "System OK · 12 h pracy"

def test_heating_and_error():
    d = dict(D, extruder={"temperature": 100, "target": 210})
    v = lg.view(P("ready", d)); assert v["state"] == "NAGRZEWA" and "→ 210°" in v["nozzle_temp"]
    assert lg.view(P("error", D))["state"] == "BŁĄD"

def test_missing():
    v = lg.view(P("ready", {"print_stats": {}}))
    assert v["nozzle_size"] == "Ø?" and v["light"] == "brak" and v["chamber_temp"] == "–"
