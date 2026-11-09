from ks_includes import revo_tools_logic as T


def test_catalog_and_filter():
    cat = T.load()
    assert len(cat["kategorie"]) >= 6
    secs = ["stepper_x", "stepper_y", "stepper_z", "stepper_z1", "extruder", "tmc5160 stepper_x", "tmc2209 extruder", "heater_bed"]
    src = T.sources(secs)
    assert src["steppers"] == ["stepper_x", "stepper_y", "stepper_z", "stepper_z1", "extruder"]
    assert src["tmc"] == ["stepper_x", "extruder"]
    avail = ["STEPPER_BUZZ", "DUMP_TMC", "QUERY_ENDSTOPS", "PID_CALIBRATE", "TURN_OFF_HEATERS", "CQGL", "SAVE_CONFIG"]
    vis = T.visible(cat, avail, src)
    names = [c["n"] for k in vis for c in k["komendy"]]
    assert "STEPPER BUZZ" in names and "BAZUJ X Y Z" in names and "WENTYLATOR 100%" in names
    assert "PAS 100 MM" not in names and "INPUT SHAPER" not in names   # brak CLEAR_BELT / SHAPER_CALIBRATE
    assert T.fill("STEPPER_BUZZ STEPPER={silnik}", "silnik", "stepper_z2") == "STEPPER_BUZZ STEPPER=stepper_z2"
    assert not T.needs_confirm("DUMP_TMC STEPPER=x") and T.needs_confirm("SAVE_CONFIG")
