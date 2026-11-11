from ks_includes import revo_serwis_logic as s


def test_states():
    it = {i["key"]: i for i in s.status(450, {"revo_serwis_dysza": 200})}
    assert it["dysza"]["state"] == "po terminie"        # 250 h od wymiany > 200
    assert it["osie"]["state"] == "wkrótce"             # 450 z 500
    assert it["pelny"]["state"] == "ok"
    assert s.banner(s.status(450, {"revo_serwis_dysza": 200})) == "SERVICE DUE: Nozzle"


def test_names_and_gcode():
    assert s.status(0, {}, is_belt=False)[1]["name"] == "Belts and axes"
    assert s.status(None, {}) == []
    assert s.done_gcode("dysza", 412.345) == "SAVE_VARIABLE VARIABLE=revo_serwis_dysza VALUE=412.3"
