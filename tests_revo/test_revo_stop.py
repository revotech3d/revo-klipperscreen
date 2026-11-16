from ks_includes import revo_stop_logic as s

ESTOP = ("Shutdown due to webhooks request\nOnce the underlying issue is corrected, use the\n"
         "\"FIRMWARE_RESTART\" command to reset the firmware, reload the\nconfig, and restart the host software.\nPrinter is shutdown\n")
HEAT = ("Heater extruder not heating at expected rate\nSee the 'verify_heater' section in docs/Config_Reference.md\n"
        "for the parameters that control this check.\nOnce the underlying issue is corrected, use the\n"
        "\"FIRMWARE_RESTART\" command to reset the firmware, reload the\nconfig, and restart the host software.\nPrinter is shutdown\n")


def test_estop_is_named_and_the_klipper_boilerplate_goes():
    d = s.describe(ESTOP)
    assert d["title"] == "EMERGENCY STOP" and d["code"] == "REVO-0801"
    assert "hotend fan keeps cooling" in d["reason"] and d["klipper"] == "Shutdown due to webhooks request"


def test_heating_error_names_the_heater():
    d = s.describe(HEAT)
    assert d["code"] == "REVO-0403" and d["reason"].startswith("Nozzle is not heating")
    assert s.describe(HEAT.replace("extruder", "heater_bed"), belt=False)["reason"].startswith("Bed ")
    assert d["klipper"] == "Heater extruder not heating at expected rate"


def test_other_messages():
    assert s.describe("Lost communication with MCU 'EBBCan'")["code"] == "REVO-0803"
    assert s.describe("ADC out of range")["code"] == "REVO-0802"
    assert s.describe("Something new")["title"] == "MACHINE STOPPED"
