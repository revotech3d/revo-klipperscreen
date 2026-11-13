# Revo OS – materiały filamentu (temperatura wymiany) i opis stanu szpuli. Te same wartości w Revo Panel (www).
MATERIALS = [("PLA", 215), ("PETG", 240), ("ABS", 255), ("ASA", 260), ("TPU", 230),
             ("PA", 270), ("PC", 280), ("PETG-CF", 250), ("PA-CF", 280), ("INNY", 240)]
TEMP = dict(MATERIALS)
SPOOLS = [1000, 750, 500, 250, 2000, 3000]


def swap_temp(old, new):
    """Wymiana: gorętsza z temperatur starego i nowego materiału (stary musi się stopić, nowy przepłynąć)."""
    return max(TEMP.get(old or "", 0), TEMP.get(new or "", 240), 200)


def label(sz):
    sz = sz or {}
    mat, left = sz.get("mat") or "", sz.get("zostalo_g")
    if left is None:
        return f"{mat} · spool level unknown".strip(" ·")
    return f"{mat} · {left:.0f} g".strip(" ·")


def fraction(sz):
    sz = sz or {}
    if sz.get("zostalo_g") is None or not sz.get("pelna_g"):
        return None
    return max(0.0, min(1.0, sz["zostalo_g"] / sz["pelna_g"]))
