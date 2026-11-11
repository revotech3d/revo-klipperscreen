# Revo OS – Temperatury: dysza, taśma, komora + presety
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

from ks_includes import revo_home_logic as logic
from ks_includes.screen_panel import ScreenPanel
from ks_includes.widgets.revo_home import PRESETS, RevoActions, Tile, _lbl


class Panel(RevoActions, ScreenPanel):
    def __init__(self, screen, title, **kwargs):
        super().__init__(screen, title or "Temperatura")
        self.p, self.printer, self.screen = self, self._printer, self._screen
        self._timer = None
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.get_style_context().add_class("revo_home")
        g = Gtk.Grid(column_homogeneous=True, column_spacing=10)
        self.t = {
            "extruder": Tile("DYSZA", lambda: self.heater_dialog("extruder", "DYSZA", [0, 200, 210, 220, 240, 250, 260, 280], 320)),
            "heater_bed": Tile(logic.bed_label(self._printer), lambda: self.heater_dialog("heater_bed", logic.bed_label(self._printer), [0, 60, 70, 80, 90, 100, 110], 130)),
            "chamber": Tile("KOMORA"),
        }
        for i, t in enumerate(self.t.values()):
            t.set_size_request(-1, 110)
            g.attach(t, i, 0, 1, 1)
        box.pack_start(g, False, False, 0)
        box.pack_start(_lbl("Dotknij kafelka, żeby ustawić temperaturę.", "revo_info", 0.5), False, False, 0)
        box.pack_start(_lbl("PRESETY MATERIAŁÓW", "revo_tile_title"), False, False, 6)
        pg = Gtk.Grid(column_homogeneous=True, column_spacing=8, row_spacing=8)
        for i, (name, e, b) in enumerate(PRESETS + [("Wyłącz grzanie", 0, 0)]):
            bt = Gtk.Button(label=name if e else "Wyłącz grzanie")
            bt.get_style_context().add_class("revo_preset")
            bt.set_size_request(-1, 64)
            bt.connect("clicked", lambda w, e=e, b=b: self.gcode(
                f"SET_HEATER_TEMPERATURE HEATER=extruder TARGET={e}\nSET_HEATER_TEMPERATURE HEATER=heater_bed TARGET={b}"))
            pg.attach(bt, i % 2, i // 2, 1, 1)
        box.pack_start(pg, False, False, 0)
        for name, e, b in PRESETS:
            box.pack_start(_lbl(f"{name}: nozzle {e}°C, belt/bed {b}°C", "revo_info"), False, False, 0)
        self.content.add(box)

    def activate(self):
        self._tick()
        self._timer = GLib.timeout_add_seconds(1, self._tick)

    def deactivate(self):
        if self._timer:
            GLib.source_remove(self._timer)
            self._timer = None

    def _tick(self):
        for dev, tile in self.t.items():
            if dev == "chamber":
                dev = logic.cfg(self._printer, "chamber", "temperature_sensor chamber")
            st = self._printer.get_stat(dev) or {}
            t = st.get("temperature")
            tile.value.set_label("–" if t is None else f"{t:.0f}°")
            tg = st.get("target") or 0
            tile.sub.set_label(f"cel {tg:.0f}°" if tg else ("wył." if "target" in st else ""))
        return self._timer is not None
