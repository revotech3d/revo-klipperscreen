# Revo OS – Temperatury (OrionUI): heksagony dyszy, pasa/stołu i komory, presety materiałów,
# temperatura docelowa każdej grzałki wpisywana z klawiatury (okno grzałki) i wyłączenie wszystkich grzałek.
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

from ks_includes import revo_home_logic as logic
from ks_includes.screen_panel import ScreenPanel
from ks_includes.widgets.revo_home import PRESETS, HexGauge, RevoActions, _lbl, window

LIMIT = {"extruder": 300, "heater_bed": 120}


def _pad(w, m=6):
    w.set_margin_start(m)
    w.set_margin_end(m)
    w.set_margin_top(m)
    w.set_margin_bottom(m)
    return w


class Panel(RevoActions, ScreenPanel):
    def __init__(self, screen, title, **kwargs):
        super().__init__(screen, title or "Temperature")
        self.p, self.printer, self.screen = self, self._printer, self._screen
        self._timer = None
        belt = logic.is_belt(self._printer)
        self.bed_name = "BELT" if belt else "BED"
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.get_style_context().add_class("revo_home")

        hexes = Gtk.Box(spacing=4, homogeneous=True)
        self.hx = {
            "extruder": HexGauge("NOZZLE", 300, lambda: self.pick("extruder")),
            "heater_bed": HexGauge(self.bed_name, 120, lambda: self.pick("heater_bed")),
            "chamber": HexGauge("CHAMBER", 60),
        }
        for h in self.hx.values():
            h.set_size_request(130, 100)
            hexes.pack_start(h, True, True, 0)
        box.pack_start(window("THERMAL CONTROL", _pad(hexes), "TAP TO SET"), False, False, 0)

        pg = Gtk.Grid(column_homogeneous=True, column_spacing=6, row_spacing=6)
        for i, (name, e, b) in enumerate(PRESETS + [("ALL OFF", 0, 0)]):
            bt = Gtk.Button(label=f"{name}\n{e}° / {b}°" if e else "HEATERS OFF")
            bt.get_child().set_justify(Gtk.Justification.CENTER)
            bt.get_style_context().add_class("revo_preset")
            bt.set_size_request(-1, 50)
            bt.connect("clicked", lambda w, e=e, b=b: self.gcode(
                f"SET_HEATER_TEMPERATURE HEATER=extruder TARGET={e}\nSET_HEATER_TEMPERATURE HEATER=heater_bed TARGET={b}"))
            pg.attach(bt, i % 2, i // 2, 1, 1)
        box.pack_start(window("PRESETS", _pad(pg), f"NOZZLE / {self.bed_name}"), False, False, 0)

        # set target: one row per heater, a tap opens the keypad (type the temperature, presets, ±5)
        sg = Gtk.Grid(column_homogeneous=True, column_spacing=6, row_spacing=6)
        self.setbtn = {}
        for row, dev in enumerate(("extruder", "heater_bed")):
            name = "NOZZLE" if dev == "extruder" else self.bed_name
            b = Gtk.Button()
            b.get_style_context().add_class("revo_preset")
            b.set_size_request(-1, 64)
            b.connect("clicked", lambda w, d=dev: self.pick(d))
            self.setbtn[dev] = (b, name)
            sg.attach(b, 0, row, 1, 1)
        self.setwin = window("SET TEMPERATURE", _pad(sg), "TAP TO TYPE")
        box.pack_start(self.setwin, False, False, 0)
        self.content.add(box)

    def pick(self, dev):
        presets = [0, 200, 210, 220, 240, 250, 260] if dev == "extruder" else [0, 60, 70, 80, 90, 100, 110]
        self.heater_dialog(dev, "NOZZLE" if dev == "extruder" else self.bed_name, presets, LIMIT[dev])

    def activate(self):
        self._tick()
        self._timer = GLib.timeout_add_seconds(1, self._tick)

    def deactivate(self):
        if self._timer:
            GLib.source_remove(self._timer)
            self._timer = None

    def _tick(self):
        for dev, h in self.hx.items():
            src = logic.cfg(self._printer, "chamber", "temperature_sensor chamber") if dev == "chamber" else dev
            st = self._printer.get_stat(src) or {}
            t, tg = st.get("temperature"), st.get("target")
            h.set(float(t) if isinstance(t, (int, float)) else None, float(tg) if isinstance(tg, (int, float)) and dev != "chamber" else None)
        for dev, (b, name) in self.setbtn.items():
            st = self._printer.get_stat(dev) or {}
            t, tg = st.get("temperature"), st.get("target") or 0
            now = f"{t:.0f}°" if isinstance(t, (int, float)) else "–"
            b.set_label(f"{name}   {now}  →  {tg:.0f}°" if tg else f"{name}   {now}  ·  OFF")
        return self._timer is not None
