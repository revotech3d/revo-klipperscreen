from ks_includes import revo_stop_logic as s

ESTOP = ("Shutdown due to webhooks request\nOnce the underlying issue is corrected, use the\n"
         "\"FIRMWARE_RESTART\" command to reset the firmware, reload the\nconfig, and restart the host software.\nPrinter is shutdown\n")
HEAT = ("Heater extruder not heating at expected rate\nSee the 'verify_heater' section in docs/Config_Reference.md\n"
        "for the parameters that control this check.\nOnce the underlying issue is corrected, use the\n"
        "\"FIRMWARE_RESTART\" command to reset the firmware, reload the\nconfig, and restart the host software.\nPrinter is shutdown\n")


def test_estop_is_named_and_the_klipper_boilerplate_goes():
    d = s.describe(ESTOP)
    assert d["title"] == "EMERGENCY STOP" and d["code"] == "REVO-0801"
    assert "on purpose" in d["reason"] and "not a fault" in d["reason"] and "hotend fan keeps cooling" in d["reason"]
    assert d["klipper"] == "Shutdown due to webhooks request"


def test_heating_error_names_the_heater():
    d = s.describe(HEAT)
    assert d["code"] == "REVO-0403" and d["reason"].startswith("Nozzle did not reach")
    assert s.describe(HEAT.replace("extruder", "heater_bed"), belt=False)["reason"].startswith("The Bed heater")
    assert d["klipper"] == "Heater extruder not heating at expected rate"


def test_other_messages():
    assert s.describe("Lost communication with MCU 'EBBCan'")["code"] == "REVO-0803"
    assert s.describe("ADC out of range")["code"] == "REVO-0802"
    assert s.describe("Something new")["title"] == "MACHINE STOPPED"


MCU = ("MCU 'mcu' shutdown: {}\nThis often indicates the host computer is overloaded. Check\n"
       "for other processes consuming excessive CPU time.\nOnce the underlying issue is corrected, use the\n"
       "\"FIRMWARE_RESTART\" command to reset the firmware, reload the\nconfig, and restart the host software.\nPrinter is shutdown\n")


def test_mcu_shutdowns_are_told_apart():
    assert s.describe(MCU.format("Timer too close"))["code"] == "REVO-0804"
    assert s.describe(MCU.format("ADC out of range"))["code"] == "REVO-0802"
    assert s.describe(MCU.format("Missed scheduling of next digital out event"))["code"] == "REVO-0804"
    assert s.describe(MCU.format("Something else"))["code"] == "REVO-0803"
    assert s.describe(MCU.format("Timer too close"))["klipper"] == "MCU 'mcu' shutdown: Timer too close"


def test_more_messages():
    assert s.describe("Shutdown due to M112 command")["code"] == "REVO-0801"
    assert "M112" in s.describe("Shutdown due to M112 command")["reason"]
    assert s.describe("TMC 'stepper_x' reports error: GSTAT: 00000001 reset=1")["code"] == "REVO-0805"
    assert s.describe("Unable to read tmc uart 'stepper_y' register IFCNT")["code"] == "REVO-0805"
    assert s.describe("Option 'step_pin' in section 'stepper_x' must be specified")["code"] == "REVO-0807"
    assert s.describe("MCU Protocol error")["code"] == "REVO-0808"
    assert s.describe("Heater heater_bed not heating at expected rate")["reason"].startswith("The Belt heater")


def test_every_description_says_what_happened_and_what_to_do():
    for _, title, _, reason, todo in s.RULES:
        assert title.isupper() and len(reason) > 60 and todo.endswith(".")
