# Revo OS: druk na płaskim pasie – co pokazuje ekran drukowania.
# Dane z makra FLAT_BELT (revo.cfg), które [r]evo Slicer wypełnia przez FLAT_BELT_INFO i FLAT_BELT_UNIT_DONE.
import math
import time

MODES = {
    "fixed": ("FIXED BED", "BELT STANDS STILL"),
    "sequential": ("SEQUENTIAL", "ONE PIECE AT A TIME"),
    "plates": ("PLATES", "THE WHOLE PLATE, AGAIN AND AGAIN"),
    "long": ("LONG PARTS", "ONE PART IN SEGMENTS"),
    "endless": ("ENDLESS", "ONE SEGMENT AFTER ANOTHER"),
}
UNITS = {"piece": ("PIECE", "PIECES"), "plate": ("PLATE", "PLATES"), "segment": ("SEGMENT", "SEGMENTS")}


def fmt_time(s):
    if s is None:
        return "–"
    s = int(max(0, s))
    h, m = divmod(s // 60, 60)
    if h >= 24:
        return f"{h // 24}d {h % 24}h"
    return f"{h}h {m:02d}m" if h else f"{m}m {s % 60:02d}s"


def length_m(fb, units):
    """Endless: the part's length after `units` segments, m."""
    if units <= 0:
        return 0.0
    return (float(fb.get("start_len", 0)) + (units - 1) * float(fb.get("advance", 0))) / 1000


def unit_time(fb, est_time=0.0):
    """Measured average time per unit, or the file's estimate split over the units it covers."""
    done = int(fb.get("done", 0))
    if done > 0 and float(fb.get("unit_sum", 0)) > 0:
        return float(fb["unit_sum"]) / done
    units = int(fb.get("file_units", 0))
    if est_time and units > 0:
        return float(est_time) / units
    return None


def min_target(fb):
    return max(int(fb.get("done", 0)) + 1, int(fb.get("min_target", 1)))


def step_target(fb, target, delta):
    """+/- on the screen. 0 = until stopped: − starts from the smallest target, + keeps it."""
    lo = min_target(fb)
    if target == 0:
        return lo if delta < 0 else 0
    return max(lo, target + delta)


def target_text(fb, target):
    if target == 0:
        return "∞"
    if fb.get("mode") == "endless":
        return f"{length_m(fb, target):.2f} m"
    return str(target)


def view(fb, print_duration, est_time=0.0, now=None, spool=None, unit_g=None):
    """Texts for the belt window. None when the print is not a belt print from [r]evo Slicer.
    spool: (grams left, full spool grams or None); unit_g: filament per unit from the file –
    with no quantity limit the belt prints until the spool ends, so that is what we count down."""
    mode = fb.get("mode") or ""
    if mode not in MODES:
        return None
    now = time.time() if now is None else now
    name, sub = MODES[mode]
    one, many = UNITS.get(fb.get("unit"), UNITS["segment"])
    done, target = int(fb.get("done", 0)), int(fb.get("target", 0))
    loop = bool(fb.get("loop"))
    per = unit_time(fb, est_time)
    current = max(0.0, float(print_duration) - float(fb.get("unit_mark", 0)))
    # The file's estimate can be short (a lower speed or acceleration limit on the printer): once the
    # unit runs past it, the estimate grows with it, so the bar never shows a unit done before the
    # printer reports it and the times ahead follow the real pace.
    if per and current > 0.97 * per:
        per = current / 0.97
    v = {"mode": name, "sub": sub, "loop": loop, "counter": "", "counter_unit": "", "bar_unit": 0.0, "bar_all": 0.0,
         "stats": [], "target": target_text(fb, target), "target_title": "QUANTITY", "finishing": bool(fb.get("finishing")),
         "progress": None, "left": None, "spool_units": None, "spool_time": None, "spool_left": None, "spool_line": "", "spool_warn": False}
    if mode == "fixed":
        return v
    if mode == "endless":
        v["sub"] = "UNTIL STOPPED" if target == 0 else "TO " + target_text(fb, target)
        v["counter"] = f"{length_m(fb, done):.2f}"
        v["counter_unit"] = "M PRINTED"
        v["target_title"] = "LENGTH"
    else:
        v["counter"] = f"{done} / {target}" if target > 0 else str(done)
        v["counter_unit"] = (many if target != 1 else one) + ("" if target > 0 else " · UNTIL STOPPED")
        v["target_title"] = many
    if per:
        v["bar_unit"] = min(1.0, current / per)
    left = None
    if target > 0:
        v["bar_all"] = min(1.0, (done + v["bar_unit"]) / target)
        v["progress"] = v["bar_all"]
        if per:
            left = max(0.0, (target - done) * per - current)
    v["left"] = left
    sp = spool_view(fb, spool, unit_g, done, target, per, current, now) if loop else None
    if sp:
        v.update(sp)
        if target == 0:
            if v["spool_left"] is not None:
                v["progress"] = v["spool_left"]
            st = v["spool_time"]
            v["stats"] = [
                ("PER " + one, fmt_time(per) if per else "–"),
                ("SPOOL FOR", sp["spool_for"]),
                ("SPOOL EMPTY", time.strftime("%H:%M", time.localtime(now + st)) if st is not None else "–"),
            ]
            return v
    v["stats"] = [
        ("PER " + one, fmt_time(per) if per else "–"),
        ("ENDS IN", fmt_time(left) if left is not None else "∞" if target == 0 else "–"),
        ("READY AT", time.strftime("%H:%M", time.localtime(now + left)) if left is not None else "–"),
    ]
    return v


def spool_view(fb, spool, unit_g, done, target, per, current, now):
    """Filament on the spool against the series: % left, whether it lasts to the end of the series,
    and with no limit how many pieces / plates / metres it is enough for. None without spool data."""
    if not spool or spool[0] is None or not unit_g:
        return None
    g_left, g_full = float(spool[0]), spool[1]
    one, many = UNITS.get(fb.get("unit"), UNITS["segment"])
    endless = fb.get("mode") == "endless"
    frac = min(1.0, current / per) if per else 0.0
    n = g_left / float(unit_g) + frac            # units the spool covers, counted from the start of the current one
    left = max(0.0, min(1.0, g_left / float(g_full))) if g_full else None
    pct = f"FILAMENT {left * 100:.0f}% · " if left is not None else f"FILAMENT {g_left:.0f} g · "

    def amount(u):
        if endless:
            return f"{u * float(fb.get('advance', 0)) / 1000:.2f} M"
        u = int(u)
        return f"{u} {one if u == 1 else many}"
    r = {"spool_left": left, "spool_units": int(n), "spool_time": max(0.0, n * per - current) if per else None,
         "spool_for": amount(n), "spool_warn": False}
    if target > 0:
        need = max(0, target - done)
        if n + 1e-9 >= need:
            r["spool_line"] = pct + "ENOUGH FOR THE REST (" + amount(need) + ")"
        else:
            r["spool_warn"] = True
            when = f" ≈ {time.strftime('%H:%M', time.localtime(now + r['spool_time']))}" if r["spool_time"] is not None else ""
            first = f"{n * float(fb.get('advance', 0)) / 1000:.2f}" if endless else str(int(n))
            r["spool_line"] = pct + f"ENOUGH FOR {first} OF {amount(need)} · CHANGE SPOOL{when}"
    else:
        r["spool_line"] = pct + "ENOUGH FOR " + amount(n)
    return r


# ---------- plik przed startem: tryb i ilość z linii FLAT_BELT_INFO ([r]evo Slicer) ----------
FILE_UNITS = {"sequential": ("PIECE", "PIECES"), "plates": ("PLATE", "PLATES"), "long": ("SEGMENT", "SEGMENTS"),
              "endless": ("SEGMENT", "SEGMENTS")}


def parse_info(line):
    """FLAT_BELT_INFO MODE=… TARGET=… → dict, or None for a line that is not one or an older file."""
    if not line.startswith("FLAT_BELT_INFO"):
        return None
    p = {}
    for kv in line.split()[1:]:
        k, _, v = kv.partition("=")
        p[k.upper()] = v
    mode = p.get("MODE", "").lower()
    if mode not in MODES:
        return None
    num = lambda k, d=0.0: float(p.get(k) or d)
    return {"mode": mode, "target": int(num("TARGET")), "loop": p.get("LOOP") == "1", "advance": num("ADVANCE"),
            "start_len": num("START"), "file_units": int(num("FILE_UNITS")), "eject": p.get("EJECT", "off").lower()}


def read_info(path, limit=1 << 20):
    """Reads the start of a G-code file until its FLAT_BELT_INFO line (after the header and the start G-code)."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            read = 0
            for line in f:
                read += len(line)
                if line.startswith("FLAT_BELT_INFO"):
                    return parse_info(line.strip())
                if read > limit:
                    break
    except OSError:
        pass
    return None


def file_badge(info):
    """Short text for the file list: 'SEQUENTIAL · 59 PCS', 'ENDLESS · 10.00 M', 'FIXED BED · EJECT'."""
    if not info:
        return ""
    name = MODES[info["mode"]][0]
    t = info["target"]
    if info["mode"] == "fixed":
        return name + (" · EJECT" if info["eject"] not in ("", "off") else "")
    if info["mode"] == "endless":
        return f"{name} · " + (f"{length_m(info_fb(info), t):.2f} M" if t else "∞")
    one, many = FILE_UNITS[info["mode"]]
    return f"{name} · " + (f"{t} {many if t != 1 else one}" if t else "∞")


def info_fb(info):
    """The file's values in the shape of the FLAT_BELT macro, for length_m()."""
    return {"start_len": info["start_len"], "advance": info["advance"], "mode": info["mode"]}


def per_unit(info, est_time):
    if info and info["file_units"] > 0 and est_time:
        return float(est_time) / info["file_units"]
    return None


def series_time(info, est_time, target):
    per = per_unit(info, est_time)
    return per * target if per and target > 0 else None
