# Revo OS – Temperatury (OrionUI): heksagony dyszy, pasa/stołu i komory, presety materiałów,
# ustawianie celu krokami i wyłączenie wszystkich grzałek.
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

from ks_includes import revo_home_logic as logic
from ks_includes.screen_panel import ScreenPanel
from ks_includes.widgets.revo_home import PRESETS, HexGauge, RevoActions, _lbl, window

LIMIT = {"extruder": 300, "heater_bed": 120}
STEPS = [-10, -5, -1, 1, 5, 10]


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
        self.dev = "extruder"
        self.want = None
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
        box.pack_start(window("THERMAL CONTROL", _pad(hexes), "TAP TO SELECT"), False, False, 0)

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

        st = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.tlbl = _lbl("", "revo_big", 0.5)
        st.pack_start(self.tlbl, False, False, 0)
        sg = Gtk.Grid(column_homogeneous=True, column_spacing=6, row_spacing=6)
        for i, d in enumerate(STEPS):
            b = Gtk.Button(label=f"{d:+d}".replace("-", "−"))
            b.get_style_context().add_class("revo_preset")
            b.set_size_request(-1, 42)
            b.connect("clicked", lambda w, d=d: self.step(d))
            sg.attach(b, i % 3, i // 3, 1, 1)
        st.pack_start(sg, False, False, 0)
        row = Gtk.Grid(column_homogeneous=True, column_spacing=6)
        off = Gtk.Button(label="OFF")
        off.get_style_context().add_class("revo_preset")
        off.set_size_request(-1, 48)
        off.connect("clicked", lambda w: self.apply(0))
        setb = Gtk.Button(label="SET")
        setb.get_style_context().add_class("revo_print")
        setb.set_size_request(-1, 48)
        setb.connect("clicked", lambda w: self.apply(self.want))
        row.attach(off, 0, 0, 1, 1)
        row.attach(setb, 1, 0, 2, 1)
        st.pack_start(row, False, False, 0)
        self.setwin = window("SET TARGET · NOZZLE", _pad(st), "MAX 300°C")
        box.pack_start(self.setwin, False, False, 0)
        self.content.add(box)

    def _title(self):
        bar = self.setwin.get_children()[0]
        labels = [c for c in bar.get_children() if isinstance(c, Gtk.Label)]
        name = "NOZZLE" if self.dev == "extruder" else self.bed_name
        labels[1].set_label(f"SET TARGET · {name}")
        labels[-1].set_label(f"MAX {LIMIT[self.dev]}°C")

    def pick(self, dev):
        self.dev, self.want = dev, None
        self._title()
        self._tick()

    def _target(self):
        return float((self._printer.get_stat(self.dev) or {}).get("target") or 0)

    def step(self, d):
        base = self.want if self.want is not None else (self._target() or (210 if self.dev == "extruder" else 60))
        self.want = max(0, min(LIMIT[self.dev], round(base + d)))
        self._tick()

    def apply(self, v):
        if v is None:
            return
        self.gcode(f"SET_HEATER_TEMPERATURE HEATER={self.dev} TARGET={int(v)}")
        self.want = None

    def activate(self):
        self._title()
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
        cur = self._target()
        shown = self.want if self.want is not None else cur
        self.tlbl.set_label(f"→ {shown:.0f}°" if shown else "OFF")
        return self._timer is not None
