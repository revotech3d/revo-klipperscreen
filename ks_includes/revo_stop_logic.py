# Revo OS – ekran zatrzymania: komunikat Klippera (shutdown / error) → zrozumiały tytuł, co się stało,
# dlaczego, co zrobić i kod REVO. Kody i treści zgodne z revo-config web/kody.json (Revo Panel → Kody błędów).
import re

BOILERPLATE = (
    "once the underlying issue is corrected",
    '"firmware_restart" command',
    "config, and restart the host software",
    "printer is shutdown",
    "see the 'verify_heater' section",
    "for the parameters that control this check",
    "klipper has shutdown",
    "klipper has encountered an error",
    "a firmware_restart may fix the issue",
    "this generally occurs",
    "this often indicates",
    "for other processes consuming",
)
HEATERS = {"extruder": "Nozzle", "heater_bed": "Belt"}
HOME = " Home the axes before the next print."
SERVICE = " If it comes back, call Revotech service."

# (code, title, Klipper patterns, what happened and why, what to do) – the first matching rule wins,
# so specific messages come before the generic board ones.
RULES = (
    ("REVO-0801", "EMERGENCY STOP", r"webhooks request|emergency stop",
     "Someone stopped the machine on purpose: E-STOP held on this screen, or the emergency stop in Revo Panel "
     "or Mainsail. This is not a fault. Motors, belt and heaters are off; the hotend fan keeps cooling. "
     "The print cannot be resumed.",
     "Check the machine and clear what made you stop it, then tap FULL RESTART." + HOME),
    ("REVO-0801", "EMERGENCY STOP", r"\bm112\b",
     "An M112 emergency stop command arrived from the print file, a macro or the console. "
     "Motors, belt and heaters are off; the hotend fan keeps cooling. The print cannot be resumed.",
     "If you did not send it, check the file's custom G-code in the slicer. Tap FULL RESTART." + HOME),
    ("REVO-0403", "HEATING ERROR", r"heater (\S+) not heating at expected rate",
     "{heater} did not reach or hold its temperature, so the machine switched everything off to protect it. "
     "Usual causes: a loose heater or thermistor plug, a draught or fan blowing on the nozzle, "
     "or a failing heater cartridge.",
     "Check the heater and thermistor cables, keep the nozzle out of strong airflow, then tap FULL RESTART." + SERVICE),
    ("REVO-0802", "TEMPERATURE SENSOR ERROR", r"adc out of range|thermocouple|max31865|temperature.*(out of range|fault)",
     "A temperature sensor shows an impossible value (too hot or too cold), so the machine stopped heating for safety. "
     "Usually the thermistor plug is loose or the cable is broken; rarely a real overheat.",
     "Check the thermistor plugs on the toolhead and the belt, then tap FULL RESTART." + SERVICE),
    ("REVO-0804", "CONTROL BOARD OVERLOAD", r"timer too close|missed scheduling|rescheduled timer|stepper too far in past|move queue overflow",
     "A control board fell behind with the moves and stopped to avoid a wrong move. "
     "Usually a very dense file, many programs at once on the screen computer, or a weak toolhead cable connection.",
     "Tap FULL RESTART and start the print again." + SERVICE),
    ("REVO-0805", "MOTOR DRIVER ERROR", r"\btmc\b.*(error|fault|reports|unable to read|register)|unable to (read|write) tmc",
     "A motor driver reported a fault: overheating, a short or no answer. Usually a driver that got too hot "
     "or a loose motor cable.",
     "Let the machine cool down for a few minutes, check the motor plugs, then tap FULL RESTART." + SERVICE),
    ("REVO-0806", "MOVE OUT OF RANGE", r"move out of range|move exceeds maximum",
     "A move in the file goes outside the working area of the machine. "
     "Usually the file was sliced for another printer or another bed size.",
     "Slice the file with the Revon Belt profile in [r]evo Slicer, then tap FULL RESTART." + HOME),
    ("REVO-0807", "CONFIGURATION ERROR", r"unable to parse|config file|option '.*' in section|section '.*' |error in config|must be specified|is not a valid",
     "The machine configuration has an error, so the machine cannot start. "
     "Usually after a manual change in printer.cfg or an interrupted update.",
     "Undo the last configuration change or install the latest Revo OS, then tap FULL RESTART. Call Revotech service if unsure."),
    ("REVO-0808", "FIRMWARE MISMATCH", r"protocol error|mcu protocol|version mismatch|command format mismatch",
     "A control board runs a different firmware version than the machine software. Usually after an update "
     "when a board was not flashed.",
     "Call Revotech service: the board firmware needs to be updated."),
    ("REVO-0803", "BOARD CONNECTION LOST", r"lost communication with mcu|unable to connect|unable to open serial|timeout on connect|mcu '.*' shutdown|can bus",
     "The screen computer lost the connection to a control board (main board or toolhead), so the machine "
     "stopped. Usually a loose toolhead cable (CAN), an electrical interference or a power dip.",
     "Tap FULL RESTART. If the message comes back, check the toolhead cable and call Revotech service."),
)
FALLBACK = ("REVO-0809", "MACHINE STOPPED",
            "The machine software stopped the machine for a reason not listed here. Motors and heaters are off; "
            "the hotend fan keeps cooling. The Klipper line below says what it reported.",
            "Tap FULL RESTART." + SERVICE + " Tell them the code and the Klipper line.")


def klipper_lines(msg):
    """The informative lines of a Klipper message, without the standard restart instructions."""
    out = []
    for line in (msg or "").replace("\r", "").split("\n"):
        s = line.strip()
        if s and not any(b in s.lower() for b in BOILERPLATE):
            out.append(s)
    return out


def describe(msg, belt=True):
    """{'code', 'title', 'reason', 'detail', 'klipper'} for the stop screen.
    reason = what happened, in plain words, and the usual causes; detail = what to do."""
    lines = klipper_lines(msg)
    text = "\n".join(lines) or (msg or "")
    k = " · ".join(lines[:2])
    for code, title, pat, reason, todo in RULES:
        m = re.search(pat, text, re.I)
        if m:
            if "{heater}" in reason:
                h = m.group(1)
                name = HEATERS.get(h, h) if belt or h != "heater_bed" else "Bed"
                reason = reason.replace("{heater}", f"The {name} heater" if name in ("Belt", "Bed") else name)
            return dict(code=code, title=title, reason=reason, detail=todo, klipper=k)
    code, title, reason, todo = FALLBACK
    return dict(code=code, title=title, reason=reason, detail=todo, klipper=k)
