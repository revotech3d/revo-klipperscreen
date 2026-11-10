import ast

from ks_includes import revo_lock_logic as l


def test_lock_settings_roundtrip():
    g = l.save_gcode(True, 15, l.hash_pin("2468"))
    val = ast.literal_eval(ast.literal_eval(g.split("VALUE=", 1)[1]))
    s = l.settings({"revo_lock": val})
    assert s["on"] and s["min"] == 15 and l.check("2468", s) and not l.check("1111", s)
    assert not l.settings({})["on"] and not l.settings({"revo_lock": {"on": True, "pin": ""}})["on"]
