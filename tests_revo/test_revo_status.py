import importlib.util, pathlib
spec = importlib.util.spec_from_file_location("rs", pathlib.Path(__file__).parents[1] / "ks_includes/revo_status.py")
rs = importlib.util.module_from_spec(spec); spec.loader.exec_module(rs)

def test_states():
    assert rs.machine_state("ready", "standby") == "gotowa"
    assert rs.machine_state("printing", "printing") == "drukowanie"
    assert rs.machine_state("printing", "printing", heating=True) == "nagrzewanie"
    assert rs.machine_state("paused", "paused") == "pauza"
    assert rs.machine_state("error", "printing") == "blad"
    assert rs.machine_state("shutdown", "standby") == "blad"
    assert rs.machine_state("ready", "error") == "blad"
    assert rs.machine_state("disconnected", "standby") == "offline"
    assert rs.machine_state("ready", "standby", service=True) == "serwis"
    assert rs.machine_state("error", "standby", service=True) == "blad"  # błąd ważniejszy
    assert rs.machine_state("ready", "standby", busy=True) == "praca"     # kalibracja poza drukiem
    assert rs.machine_state("printing", "printing", busy=True) == "drukowanie"
    assert rs.blink_on("praca", 0.0) != rs.blink_on("praca", 0.5)

def test_segments():
    assert rs.lit_segments("gotowa") == 40
    assert rs.lit_segments("drukowanie", 0.5) == 20
    assert rs.lit_segments("drukowanie", 0.0) == 1
    assert rs.lit_segments("drukowanie", 1.7) == 40

def test_blink():
    assert rs.blink_on("gotowa", 0.6)
    assert rs.blink_on("blad", 0.1) and not rs.blink_on("blad", 0.6)

def test_agent_missing():
    assert rs.agent_service_active("http://127.0.0.1:1/status") is False


def test_kalibracja_z_komunikatow():
    c = rs.calibration_from_response("// Waiting for heater to settle at ambient temperature", False)
    assert c is True
    assert rs.calibration_from_response("// Performing heatup test, target is 200.0 degrees", c) is True
    assert rs.calibration_from_response("ok", c) is True
    assert rs.calibration_from_response("// Finished MPC calibration of heater 'extruder'", c) is False
    assert rs.calibration_from_response("!! Heater extruder not heating", True) is False
