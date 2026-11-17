"""Symulator ekranu Revo OS na revo3d.pl – zrzuty 1:1 z prawdziwego KlipperScreena i mapa przycisków.

Uruchamia ten ekran (ten sam kod, który działa na maszynie) na wirtualnym wyświetlaczu 480×800 z fałszywym
Moonrakerem (tests_revo/fake_moonraker.py) i fałszywym agentem, klika po kolei każdy przycisk i zapisuje:
zrzut każdego ekranu (WebP) + gdzie są przyciski i dokąd prowadzą (manifest.json). Wynik trafia do
revotech-sites/content/revo3d-pl/media/symulator/<wariant>/ i jest pokazywany na revo3d.pl/symulator-revo-os/.

Uruchamia go tools/symulator/generuj.sh (wszystkie warianty) – po każdym wydaniu ekranu.
"""
import hashlib
import json
import os
import re
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
CONF, LOG, OUT, VARIANT = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
sys.argv = ["screen.py", "-c", CONF, "-l", LOG]

import gi  # noqa: E402

gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, GLib, Gtk  # noqa: E402

import screen  # noqa: E402
from ks_includes import revo_net  # noqa: E402
from ks_includes.widgets.revo_estop import HOLD_S  # noqa: E402

# Wygląd jak na maszynie w sieci firmy (w generatorze nie ma prawdziwej sieci)
revo_net.describe = lambda *a, **k: "Wi-Fi 72% 192.168.1.50"
revo_net.local_ip = lambda: "192.168.1.50"
try:
    from panels import revo_system
    revo_system.ip = lambda: "192.168.1.50"
except Exception:
    pass

MAX_STATES = int(os.environ.get("SYM_MAX", "70"))
MAX_DEPTH = int(os.environ.get("SYM_DEPTH", "4"))
# przyciski, których symulator nie klika (wyłączają system, zmieniają tryb ekranu albo kończą sesję)
SKIP = re.compile(r"SHUT ?DOWN|REBOOT|RESTART|POWER OFF|SWITCH TO KLIPPERSCREEN|END SERVICE|LOG ?OUT|SIGN OUT|"
                  r"FIRMWARE|UPDATE|WYŁĄCZ|ZAMKNIJ SYSTEM|FACTORY", re.I)
CLOCK = re.compile(r"^\d{1,2}:\d{2}$")
NOOP = re.compile(r"^[0-9⌫]$|^[−+-]\d+$")   # klawiatura liczb: zmienia tylko liczbę na ekranie

os.makedirs(OUT, exist_ok=True)


def pump(sec):
    end = time.monotonic() + sec
    while time.monotonic() < end:
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)
        time.sleep(0.01)


def top_window(win):
    dl = [d for d in win.dialogs if d.get_mapped()]
    return dl[-1] if dl else win


def top_layer(win):
    """Okno dialogowe albo najwyższa nakładka (PIN, blokada ekranu) – przyciski pod nią są niedostępne."""
    top = top_window(win)
    if top is not win:
        return top, top
    kids = [c for c in win.overlay.get_children() if c.get_visible() and c.get_mapped()]
    return top, (kids[-1] if len(kids) > 1 else top)


def walk(w, fn):
    if not w.get_visible() or not w.get_mapped():
        return
    fn(w)
    if isinstance(w, Gtk.Container):
        for c in w.get_children():
            walk(c, fn)


def label_of(b):
    txt = []
    walk(b, lambda w: txt.append(w.get_text()) if isinstance(w, Gtk.Label) and w.get_text().strip() else None)
    return " ".join(t.replace("\n", " ") for t in txt).strip()


def visible_rect(w, top):
    a = w.get_allocation()
    r = w.translate_coordinates(top, 0, 0)
    if not r or a.width < 4 or a.height < 4:
        return None
    x, y = r
    # przycięcie do okien przewijanych
    p = w.get_parent()
    while p is not None and p is not top:
        if isinstance(p, Gtk.ScrolledWindow):
            pa = p.get_allocation()
            pr = p.translate_coordinates(top, 0, 0)
            if pr:
                x0, y0 = max(x, pr[0]), max(y, pr[1])
                x1, y1 = min(x + a.width, pr[0] + pa.width), min(y + a.height, pr[1] + pa.height)
                if x1 - x0 < 8 or y1 - y0 < 8:
                    return None
                return [x0, y0, x1 - x0, y1 - y0]
        p = p.get_parent()
    if x >= 480 or y >= 800 or x + a.width <= 0 or y + a.height <= 0:
        return None
    return [max(0, x), max(0, y), min(480, x + a.width) - max(0, x), min(800, y + a.height) - max(0, y)]


def buttons(win):
    top, layer = top_layer(win)
    out = []

    def f(w):
        if isinstance(w, Gtk.Button) and w.get_sensitive():
            r = visible_rect(w, top)
            if r:
                out.append((w, r, label_of(w) or w.get_tooltip_text() or w.get_name() or ""))
    walk(layer, f)
    out.sort(key=lambda t: (t[1][1], t[1][0]))
    return out


def signature(win):
    """Ekran = rodzaj + panel + tytuł okna + napisy na przyciskach. Wartości (temperatury, wybrany krok)
    nie tworzą nowych ekranów – zmieniają się tylko napisy na etykietach."""
    top, layer = top_layer(win)
    labels = sorted({re.sub(r"\d+", "#", lab) for w, r, lab in buttons(win)})
    heads = []
    walk(layer, lambda w: heads.append(w.get_text()) if isinstance(w, Gtk.Label) and
         w.get_style_context().has_class("revo_win_title") else None)
    labels += sorted(set(heads))
    panel = win._cur_panels[-1] if win._cur_panels else ""
    kind = "dialog" if top is not win or layer is not top else "panel"
    dtitle = top.get_title() if top is not win else ""
    return hashlib.sha1(json.dumps([kind, panel, dtitle, labels]).encode()).hexdigest()[:12], panel, kind


def title(win):
    top = top_window(win)
    if top is not win:
        return top.get_title() or "Dialog"
    p = win._cur_panels[-1] if win._cur_panels else ""
    names = {"main_menu": "Home", "job_status": "Print", "splash_screen": "Machine stopped"}
    if p in names:
        return names[p]
    try:
        t = win.base_panel.titlelbl.get_text()
        return re.sub(r"^\S+\s+", "", t) if t else p
    except Exception:
        return p


def shoot(name):
    pb = Gdk.pixbuf_get_from_window(Gdk.get_default_root_window(), 0, 0, 480, 800)
    png = os.path.join(OUT, name + ".png")
    pb.savev(png, "png", [], [])
    return name + ".png"


def reset(win):
    for d in list(win.dialogs):
        try:
            win.gtk.remove_dialog(d)
        except Exception:
            d.destroy()
    kids = win.overlay.get_children()
    for c in kids[1:]:   # nakładki (PIN, blokada) z poprzedniego kroku
        win.overlay.remove(c)
    if kids:
        kids[0].show()
    win._menu_go_back(home=True)
    pump(0.5)


def find_button(win, center):
    for w, r, lab in buttons(win):
        if r[0] <= center[0] <= r[0] + r[2] and r[1] <= center[1] <= r[1] + r[3]:
            return w
    return None


def replay(win, path, wait=0.4):
    reset(win)
    for c in path:
        b = find_button(win, c)
        if b is None:
            return False
        b.clicked()
        pump(wait)
    return True


def explore(win):
    states, order = {}, []
    sig, panel, kind = signature(win)
    queue = [(sig, [])]
    states[sig] = {"id": "s0", "path": [], "panel": panel, "kind": kind}
    order.append(sig)
    while queue:
        sig, path = queue.pop(0)
        st = states[sig]
        if not replay(win, path):
            pump(1.5)   # second try: some screens (guides, dialogs) need longer to build
            if not replay(win, path, 1.2):
                print(f"replay failed: {st['id']}", flush=True)
                continue
        st["title"] = title(win).strip()
        if st["kind"] == "dialog" and path:
            st["parent"] = next((v["id"] for v in states.values() if v["path"] == path[:-1]), None)
        st["img"] = shoot(st["id"])
        st["buttons"] = []
        dirty = False
        for w, r, lab in buttons(win):
            cx, cy = r[0] + r[2] // 2, r[1] + r[3] // 2
            btn = {"r": r, "label": lab[:60], "to": None}
            st["buttons"].append(btn)
            if w.__class__.__name__ == "EStopHold" or lab.strip() == "emergency":   # action-bar E-STOP is held too
                btn["to"] = "estop"
                btn["hold"] = HOLD_S
                continue
            if lab.strip() == "main" and order:
                btn["to"] = states[order[0]]["id"]
                continue
            if SKIP.search(lab) or lab.strip() == "shutdown" or NOOP.match(lab.strip()) or len(path) >= MAX_DEPTH:
                continue
            try:
                if dirty and not replay(win, path):
                    break
            except Exception as e:
                print("replay error", e, flush=True)
                dirty = True
                continue
            b = find_button(win, (cx, cy))
            if b is None:
                continue
            try:
                b.clicked()
                pump(0.5)
                nsig, npanel, nkind = signature(win)
            except Exception as e:
                print("click error", lab, e, flush=True)
                dirty = True
                continue
            dirty = nsig != sig
            if nsig == sig:
                continue
            if nsig not in states:
                if len(states) >= MAX_STATES:
                    continue
                states[nsig] = {"id": f"s{len(states)}", "path": path + [(cx, cy)], "panel": npanel, "kind": nkind}
                order.append(nsig)
                queue.append((nsig, path + [(cx, cy)]))
            btn["to"] = states[nsig]["id"]
        print(f"[{len(order)}] {st['id']} {st['title']} buttons={len(st['buttons'])}", flush=True)
    out = [states[s] for s in order if "img" in states[s]]
    ok = {s["id"] for s in out} | {"estop"}
    for s in out:   # no dead links: a screen that could not be replayed is not in the simulator
        for b in s["buttons"]:
            if b.get("to") and b["to"] not in ok:
                b["to"] = None
    return out


def stop_screen(win, home_id):
    # E-STOP przytrzymany (HOLD_S): ten sam ekran zatrzymania co na maszynie (Klipper shutdown z webhooks)
    reset(win)
    win.printer.data.setdefault("webhooks", {})["state_message"] = "Shutdown due to webhooks request"
    win.printer.data["webhooks"]["state"] = "shutdown"
    win.state_shutdown()
    pump(1.5)
    st = {"id": "estop", "title": "Emergency stop", "panel": "splash_screen", "kind": "panel"}
    st["img"] = shoot("estop")
    st["buttons"] = [{"r": r, "label": lab[:60], "to": home_id if "FULL RESTART" in lab.upper() else None}
                     for w, r, lab in buttons(win)]
    return st


def prompt_screen(win):
    """REVO-0101 question as the machine shows it (action:prompt from REVO_CHECK_NOZZLE)."""
    reset(win)
    for line in ("prompt_begin REVO-0101 · File prepared for nozzle 0.4", "prompt_text Installed nozzle is 0.6. Print anyway?",
                 "prompt_footer_button Cancel|_REVO_NOZZLE_CANCEL|error", "prompt_footer_button Print|_REVO_NOZZLE_OK|primary",
                 "prompt_show"):
        win.process_action(line)
    pump(1.5)
    return shoot("prompt")


def run(win):
    try:
        pump(2)
        if os.environ.get("SYM_PROMPT_ONLY"):
            print("PROMPT", prompt_screen(win), flush=True)
            reset(win)
            win._revo_alert_q = []
            win.show_popup_message("REVO-0501 · Chamber door is open: Close the door and start the print again.", 3)
            pump(1.2)
            print("ALERT", shoot("alert"), flush=True)
            reset(win)
            win._revo_alert_q = []
            win.show_popup_message("Must home axis first: 120.000 0.000 5.000 [0.000]", 3)
            pump(1.2)
            print("ALERT2", shoot("alert2"), flush=True)
            reset(win)
            win._revo_alert_q = []
            win.show_popup_message("REVO-0203 · Filament ran out or is stuck: The filament sensor stopped the print.", 3)
            win.show_popup_message("REVO-0501 · Chamber door is open: Close the door and start the print again.", 3)
            pump(1.2)
            print("ALERT3", shoot("alert3"), flush=True)
            return
        states = explore(win)
        states.append(stop_screen(win, states[0]["id"]))
        for s in states:
            s.pop("path", None)
        ver = ("v" + os.environ["SYM_SCREEN"]) if os.environ.get("SYM_SCREEN") else \
            os.popen("git -C %s describe --tags --abbrev=0" % ROOT).read().strip()
        man = {"variant": VARIANT, "version": ver, "generated": time.strftime("%Y-%m-%d"), "start": states[0]["id"],
               "size": [480, 800], "screens": {s["id"]: s for s in states}}
        with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(man, f, ensure_ascii=False, indent=1)
        print("DONE", len(states), flush=True)
    except Exception:
        import traceback
        traceback.print_exc()
        sys.stdout.flush()
    finally:
        os._exit(0)


# Panele, które bez prawdziwego sprzętu się nie ładują (LED, sieć, system) – bez okna błędu, ekran zostaje
screen.KlipperScreen.show_error_modal = lambda self, *a, **k: print("panel error", a[0] if a else "", flush=True)
orig = screen.KlipperScreen.__init__


def init(self, *a, **k):
    orig(self, *a, **k)
    GLib.timeout_add(12000, lambda: run(self) and False)


screen.KlipperScreen.__init__ = init
screen.main()
