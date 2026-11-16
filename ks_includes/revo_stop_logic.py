# Revo OS – ekran zatrzymania: komunikat Klippera (shutdown / error) → zrozumiały tytuł, powód, co zrobić i kod REVO.
# Kody i treści zgodne z revo-config web/kody.json (Revo Panel → Kody błędów).
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
)
HEATERS = {"extruder": "Nozzle", "heater_bed": "Belt / bed"}
AFTER = "Tap FULL RESTART. Home the axes before the next print."


def klipper_lines(msg):
    """The informative lines of a Klipper message, without the standard restart instructions."""
    out = []
    for line in (msg or "").replace("\r", "").split("\n"):
        s = line.strip()
        if s and not any(b in s.lower() for b in BOILERPLATE) and s.lower() not in ("the",):
            out.append(s)
    return out


def describe(msg, belt=True):
    """{'code', 'title', 'reason', 'detail', 'klipper'} for the stop screen."""
    m = msg or ""
    low = m.lower()
    k = " · ".join(klipper_lines(m)[:2])
    if "webhooks request" in low or "emergency stop" in low or "m112" in low:
        return dict(code="REVO-0801", title="EMERGENCY STOP",
                    reason="E-STOP was pressed. Motors, belt and heaters are off; the hotend fan keeps cooling. The print cannot be resumed.",
                    detail="Check the machine and clear the cause. " + AFTER, klipper=k)
    h = re.search(r"heater (\S+) not heating at expected rate", m, re.I)
    if h:
        name = HEATERS.get(h.group(1), h.group(1))
        if h.group(1) == "heater_bed" and not belt:
            name = "Bed"
        return dict(code="REVO-0403", title="HEATING ERROR",
                    reason=f"{name} is not heating at the expected rate.",
                    detail="Check the heater and thermistor cables, then tap FULL RESTART. If it happens again, call service.",
                    klipper=k)
    if "adc out of range" in low:
        return dict(code="REVO-0802", title="THERMISTOR ERROR",
                    reason="A temperature sensor reads out of range (cable loose or broken).",
                    detail="Check the thermistor plug on the toolhead and the bed, then tap FULL RESTART. If it happens again, call service.",
                    klipper=k)
    if "lost communication with mcu" in low or "unable to connect" in low or "mcu" in low and "shutdown" in low:
        return dict(code="REVO-0803", title="BOARD CONNECTION LOST",
                    reason="The screen lost the connection to a control board (main board or toolhead).",
                    detail="Tap FULL RESTART. If the message comes back, check the toolhead cable (CAN) and call service.",
                    klipper=k)
    if "timer too close" in low:
        return dict(code="REVO-0804", title="CONTROL BOARD OVERLOAD",
                    reason="A control board could not keep up with the moves.",
                    detail="Tap FULL RESTART. If it happens often, call service.", klipper=k)
    if "tmc" in low and ("error" in low or "fault" in low or "reports" in low):
        return dict(code="REVO-0805", title="MOTOR DRIVER ERROR",
                    reason="A motor driver reported a fault (overheating or a cable problem).",
                    detail="Let the machine cool down for a few minutes, then tap FULL RESTART. If it happens again, call service.",
                    klipper=k)
    if "move out of range" in low:
        return dict(code="REVO-0806", title="MOVE OUT OF RANGE",
                    reason="A move went outside the working area.",
                    detail="Check the file and the machine profile in the slicer. " + AFTER, klipper=k)
    return dict(code="REVO-0809", title="MACHINE STOPPED",
                reason="Klipper stopped the machine. Motors and heaters are off.",
                detail="Tap FULL RESTART. If the message comes back, call service.", klipper=k)
