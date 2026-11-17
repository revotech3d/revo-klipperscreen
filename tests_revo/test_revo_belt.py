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


def test_file_info_from_the_gcode_line():
    i = bl.parse_info("FLAT_BELT_INFO MODE=sequential TARGET=59 LOOP=1 FILE_UNITS=1 ADVANCE=80.000 UNIT=piece ENDLESS=0 SEGMENTS=59")
    assert i["mode"] == "sequential" and i["target"] == 59 and i["loop"]
    assert bl.file_badge(i) == "SEQUENTIAL · 59 PIECES"
    assert bl.series_time(i, 1500, 59) == 59 * 1500
    e = bl.parse_info("FLAT_BELT_INFO MODE=endless TARGET=70 LOOP=1 FILE_UNITS=2 ADVANCE=140.000 START=340.0 UNIT=segment")
    assert bl.file_badge(e) == "ENDLESS · 10.00 M" and bl.per_unit(e, 18652) == 9326
    f = bl.parse_info("FLAT_BELT_INFO MODE=fixed TARGET=0 LOOP=0 FILE_UNITS=0 UNIT=piece EJECT=time")
    assert bl.file_badge(f) == "FIXED BED · EJECT" and not f["loop"]
    # an older file without MODE is not a belt file for the list
    assert bl.parse_info("FLAT_BELT_INFO ENDLESS=1 ADVANCE=140.000 SEGMENTS=0 UNIT=segment") is None


def test_read_info_from_a_file(tmp_path):
    g = tmp_path / "a.gcode"
    g.write_text("; HEADER\n" + "; thumbnail data\n" * 1000 + "PRINT_START\nFLAT_BELT_INFO MODE=plates TARGET=3 LOOP=1 FILE_UNITS=1 ADVANCE=175.6 UNIT=plate\nG1 X1\n")
    assert bl.file_badge(bl.read_info(str(g))) == "PLATES · 3 PLATES"
    assert bl.read_info(str(tmp_path / "missing.gcode")) is None


def test_view_spool():
    fb = dict(SEQ, target=0, unit_mark=8300.0)          # bieżąca sztuka dopiero się zaczęła
    v = bl.view(fb, 8300.0, now=0, spool=(500.0, 1000.0), unit_g=10.0)
    assert v["spool_units"] == 50 and abs(v["progress"] - 0.5) < 1e-9
    assert v["stats"][1] == ("SPOOL FOR", "50 PIECES") and v["spool_line"] == "FILAMENT 50% · ENOUGH FOR 50 PIECES"
    # seria 59 szt., zrobione 12: brakuje filamentu
    v = bl.view(dict(SEQ, unit_mark=8300.0), 8300.0, now=0, spool=(200.0, 1000.0), unit_g=10.0)
    assert v["spool_warn"] and "ENOUGH FOR 20 OF 47 PIECES · CHANGE SPOOL" in v["spool_line"]
    v = bl.view(dict(SEQ, unit_mark=8300.0), 8300.0, now=0, spool=(900.0, 1000.0), unit_g=10.0)
    assert not v["spool_warn"] and v["spool_line"].endswith("ENOUGH FOR THE REST (47 PIECES)")
    # endless: metry
    e = {"mode": "endless", "unit": "segment", "done": 3, "target": 0, "loop": True, "advance": 100.0, "start_len": 100.0}
    v = bl.view(e, 100.0, now=0, spool=(100.0, None), unit_g=5.0)
    assert v["spool_line"] == "FILAMENT 100 g · ENOUGH FOR 2.00 M"
    # bez danych szpuli – jak dawniej
    v = bl.view(dict(SEQ, target=0), 8300.0, now=0)
    assert v["spool_line"] == "" and v["stats"][1][0] == "ENDS IN"
