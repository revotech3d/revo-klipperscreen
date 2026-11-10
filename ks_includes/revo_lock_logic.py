# Revo OS – blokada ekranu PIN-em (opcjonalna, włącza ją klient w Menu → Więcej → Blokada ekranu).
# Ustawienia w save_variables: revo_lock = {"on": bool, "min": minuty bezczynności, "pin": sha256}
import hashlib

TIMES = [1, 5, 15, 30, 60]


def hash_pin(pin):
    return hashlib.sha256(("revo-lock:" + str(pin)).encode()).hexdigest()


def settings(variables):
    v = (variables or {}).get("revo_lock") or {}
    on = bool(v.get("on")) and bool(v.get("pin"))
    return {"on": on, "min": int(v.get("min") or 5), "pin": v.get("pin") or ""}


def check(pin, s):
    return bool(s.get("pin")) and hash_pin(pin) == s["pin"]


def save_gcode(on, minutes, pin_hash):
    val = {"on": bool(on), "min": int(minutes), "pin": pin_hash}
    return f'SAVE_VARIABLE VARIABLE=revo_lock VALUE="{val!r}"'
