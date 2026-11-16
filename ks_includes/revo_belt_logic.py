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


def view(fb, print_duration, est_time=0.0, now=None):
    """Texts for the belt window. None when the print is not a belt print from [r]evo Slicer."""
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
    v = {"mode": name, "sub": sub, "loop": loop, "counter": "", "counter_unit": "", "bar_unit": 0.0, "bar_all": 0.0,
         "stats": [], "target": target_text(fb, target), "target_title": "QUANTITY", "finishing": bool(fb.get("finishing")),
         "progress": None, "left": None}
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
    v["stats"] = [
        ("PER " + one, fmt_time(per) if per else "–"),
        ("ENDS IN", fmt_time(left) if left is not None else "∞" if target == 0 else "–"),
        ("READY AT", time.strftime("%H:%M", time.localtime(now + left)) if left is not None else "–"),
    ]
    return v


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
