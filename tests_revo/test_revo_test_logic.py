from ks_includes import revo_test_logic as L

PLAN = [["Termistory", "temps", "", "", "temps", 5, 1, "opis A"],
        ["Silnik stepper_z1", "buzz", "stepper_z1", "", "motor_z1", 20, 1, "opis B"],
        ["Wentylator nadmuchu", "fan", "", "", "fan_part", 20, 0, "opis C"],
        ["Grzanie pasa", "heat", "heater_bed", 60, "heat_bed", 600, 1, "opis D"]]


def test_idle():
    v = L.view({})
    assert v["faza"] == "idle" and v["buttons"][0][1] == "REVO_SELFTEST"


def test_eta_and_counts():
    v = L.view({"faza": "ask", "plan": PLAN, "step": 1, "ask": {"t": "Czy ruszył?", "ok": "DZIAŁA", "cmd": "X"}}, elapsed=10)
    assert v["num"] == 2 and v["total"] == 4 and v["left"] == "Remaining: 2 steps"
    assert L.eta(PLAN, 1, 10) == 10 + 620 and v["eta"] == "~ 10 min"
    assert v["img"] == "motor_z1" and v["title"] == "Czy ruszył?"
    assert [b[0] for b in v["buttons"]] == ["PRZERWIJ", "PROBLEM", "DZIAŁA"] and v["buttons"][2][1] == "X"


def test_reason_and_repeat():
    v = L.view({"faza": "reason", "plan": PLAN, "step": 2})
    assert v["buttons"][0][1] == 'REVO_TEST_PRZYCZYNA P="nie rusza"' and len(v["buttons"]) == 4
    v = L.view({"faza": "repeat", "plan": PLAN, "step": 2, "last": "hałas / drgania"})
    assert v["title"] == "Problem: hałas / drgania" and [b[0] for b in v["buttons"]] == ["POWTÓRZ", "DALEJ"]
    v = L.view({"faza": "repeat", "plan": PLAN, "step": 1, "last": "nie rusza"})
    assert v["buttons"][1][0] == "ZAKOŃCZ TEST" and "krytyczny" in v["note"]


def test_summary():
    sm = {"ok": 3, "total": 4, "done": 4, "stopped": "", "results": {"A": "ok", "Wentylator nadmuchu": "problem · hałas"}}
    v = L.view({"faza": "done", "plan": PLAN, "summary": sm})
    assert v["title"] == "Wynik: 3/4 OK" and v["problems"] == ["Wentylator nadmuchu: hałas"]
    assert L.view({"faza": "stop", "plan": PLAN, "summary": dict(sm, stopped="przerwany", done=2)})["name"] == "TEST PRZERWANY"
