# Revo OS – dane ekranu głównego (bez GTK, testowalne)


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _deg(v):
    v = _num(v)
    return "–" if v is None else f"{v:.0f}°"


def cfg(printer, key, default=None):
    v = printer.get_stat("gcode_macro _REVO_CFG", key)
    return default if v in (None, {}, "") else v


def light_pin(printer):
    return cfg(printer, "light_pin", "")


def kalibracja(printer):
    """Napis „KALIBRACJA PASA/STOŁU/DYSZY”, gdy trwa MPC_CALIBRATE lub PID_CALIBRATE (makro _REVO_KALIB), inaczej ''."""
    co = printer.get_stat("gcode_macro _REVO_KALIB", "co") or ""
    if not co or not (_num(printer.get_stat(co, "target")) or 0) > 0:
        return ""
    return "KALIBRACJA DYSZY" if co == "extruder" else f"KALIBRACJA {'PASA' if is_belt(printer) else 'STOŁU'}"


def view(printer, hours=None):
    ps = printer.get_stat("print_stats", "state") or "standby"
    klipper = printer.state
    if klipper in ("error", "shutdown"):
        state, cls = "BŁĄD", "revo_err"
    elif ps == "printing" or klipper == "printing":
        state, cls = "DRUKUJE", "revo_warn"
    elif ps == "paused" or klipper == "paused":
        state, cls = "PAUZA", "revo_warn"
    else:
        ext_t = _num(printer.get_stat("extruder", "target")) or 0
        bed_t = _num(printer.get_stat("heater_bed", "target")) or 0
        state, cls = ("NAGRZEWA", "revo_warn") if (ext_t or bed_t) else ("GOTOWA", "revo_ok")
        kal = kalibracja(printer)
        if kal:
            state, cls = kal, "revo_warn"

    vars_ = printer.get_stat("save_variables", "variables") or {}
    d = _num(vars_.get("revo_nozzle_diameter"))
    nozzle_size = f"Ø{d:g}" if d else "Ø?"

    ext = printer.get_stat("extruder") or {}
    nozzle_temp = _deg(ext.get("temperature"))
    if (_num(ext.get("target")) or 0) > 0:
        nozzle_temp += f" → {_num(ext.get('target')):.0f}°"
    bed = printer.get_stat("heater_bed") or {}
    bed_temp = _deg(bed.get("temperature"))
    if (_num(bed.get("target")) or 0) > 0:
        bed_temp += f"→{_num(bed.get('target')):.0f}"

    chamber = cfg(printer, "chamber", "temperature_sensor chamber")
    chamber_temp = _deg((printer.get_stat(chamber) or {}).get("temperature"))

    pin = light_pin(printer)
    light_on = bool(pin) and (_num(printer.get_stat(f"output_pin {pin}", "value")) or 0) > 0
    light = ("Włączone" if light_on else "Wyłączone") if pin else "brak"

    info = "System OK" if cls != "revo_err" else "Sprawdź komunikat"
    if hours is not None:
        info += f" · {hours:.0f} h pracy"
    return {"state": state, "state_class": cls, "info": info, "nozzle_size": nozzle_size,
            "nozzle_temp": nozzle_temp, "bed_temp": bed_temp, "chamber_temp": chamber_temp,
            "light": light, "light_on": light_on}


def machine_type(printer):
    """'belt' (stół-taśma z silnikiem) albo 'stol' (sztywny stół). Z _REVO_CFG, a gdy brak – po belt_stepper."""
    t = str(cfg(printer, "machine_type", "") or "").lower()
    if t in ("belt", "stol"):
        return t
    return "belt" if cfg(printer, "belt_stepper", "") else "stol"


def is_belt(printer):
    return machine_type(printer) == "belt"


def bed_label(printer, upper=True):
    s = "PAS" if is_belt(printer) else "STÓŁ"
    return s if upper else s.capitalize().replace("Stół", "Stół")
