import importlib.util, pathlib
spec = importlib.util.spec_from_file_location("bl", pathlib.Path(__file__).parents[1] / "ks_includes/revo_belt_logic.py")
bl = importlib.util.module_from_spec(spec); spec.loader.exec_module(bl)

SEQ = {"mode": "sequential", "unit": "piece", "done": 12, "target": 59, "loop": True, "unit_sum": 12 * 600.0,
       "unit_mark": 8000.0, "file_units": 1, "min_target": 1}


def test_older_file_or_no_belt():
    assert bl.view({"mode": ""}, 0) is None
    assert bl.view({}, 0) is None


def test_sequential_counts_pieces_and_time_left():
    v = bl.view(SEQ, 8300.0, now=0)
    assert v["mode"] == "SEQUENTIAL" and v["counter"] == "12 / 59" and v["counter_unit"] == "PIECES"
    assert v["bar_unit"] == 0.5
    # 47 pieces left at 10 min, half of the current one done
    assert v["left"] == 47 * 600 - 300
    assert v["stats"][0] == ("PER PIECE", "10m 00s") and v["stats"][1][1] == "7h 45m"


def test_first_piece_uses_the_file_estimate():
    fb = dict(SEQ, done=0, unit_sum=0.0, unit_mark=100.0)
    v = bl.view(fb, 400.0, est_time=1200.0, now=0)
    assert v["stats"][0][1] == "20m 00s" and v["left"] == 59 * 1200 - 300


def test_until_stopped():
    v = bl.view(dict(SEQ, mode="plates", unit="plate", target=0), 8300.0, now=0)
    assert v["counter"] == "12" and "UNTIL STOPPED" in v["counter_unit"]
    assert v["left"] is None and v["stats"][1][1] == "∞" and v["target"] == "∞"


def test_endless_shows_metres():
    fb = {"mode": "endless", "unit": "segment", "done": 23, "target": 70, "loop": True, "advance": 140.0,
          "start_len": 340.0, "unit_sum": 23 * 900.0, "unit_mark": 0.0, "min_target": 2}
    v = bl.view(fb, 450.0, now=0)
    assert v["counter"] == "3.42" and v["counter_unit"] == "M PRINTED"
    assert v["target"] == "10.00 m" and v["sub"] == "TO 10.00 m" and v["target_title"] == "LENGTH"


def test_fixed_names_the_mode_only():
    v = bl.view({"mode": "fixed"}, 10.0)
    assert v["mode"] == "FIXED BED" and v["counter"] == "" and not v["loop"]


def test_stepper_never_goes_below_the_current_unit():
    assert bl.step_target(SEQ, 59, -1) == 58
    assert bl.step_target(SEQ, 13, -1) == 13
    assert bl.step_target(SEQ, 0, -1) == 13 and bl.step_target(SEQ, 0, +1) == 0
    assert bl.step_target(dict(SEQ, done=0, min_target=2), 0, -1) == 2
