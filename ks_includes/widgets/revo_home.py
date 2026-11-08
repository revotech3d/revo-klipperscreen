# Revo OS – ekran główny „Gotowa”: schemat maszyny, kafelki temperatur, DRUKUJ, presety, menu
import json
import logging
import threading
import urllib.request

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

from ks_includes import revo_home_logic as logic

PRESETS = [("PLA", 210, 60), ("PETG", 240, 80), ("ABS/ASA", 250, 100)]


def _lbl(text, cls, xalign=0.0):
    lb = Gtk.Label(label=text, xalign=xalign)
    lb.get_style_context().add_class(cls)
    return lb


class Tile(Gtk.EventBox):
    """Kafelek z podpisem i wartością, klikany."""

    def __init__(self, title, on_click=None):
        super().__init__()
        self.get_style_context().add_class("revo_tile")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.title = _lbl(title, "revo_tile_title")
        self.value = _lbl("–", "revo_tile_value")
        self.sub = _lbl("", "revo_tile_sub")
        box.pack_start(self.title, False, False, 0)
        box.pack_start(self.value, False, False, 0)
        box.pack_start(self.sub, False, False, 0)
        self.add(box)
        if on_click:
            self.connect("button-release-event", lambda *a: on_click())


class Schematic(Gtk.DrawingArea):
    """Schemat Revo Belt (CoreXY + taśma) rysowany cairo, układ jak w makiecie (viewBox 436×380)."""

    def __init__(self, model):
        super().__init__()
        self.model = model
        self.light = True
        self.set_vexpand(True)
        self.set_hexpand(True)
        self.connect("draw", self._draw)

    @staticmethod
    def _rgb(ctx, hexc, a=1.0):
        h = hexc.lstrip("#")
        ctx.set_source_rgba(int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255, a)

    def _poly(self, ctx, pts, fill=None, stroke=None, lw=1.5):
        ctx.move_to(*pts[0])
        for p in pts[1:]:
            ctx.line_to(*p)
        ctx.close_path()
        if fill:
            self._rgb(ctx, fill)
            ctx.fill_preserve() if stroke else ctx.fill()
        if stroke:
            self._rgb(ctx, stroke)
            ctx.set_line_width(lw)
            ctx.stroke()

    def _line(self, ctx, a, b, color, lw):
        self._rgb(ctx, color)
        ctx.set_line_width(lw)
        ctx.move_to(*a)
        ctx.line_to(*b)
        ctx.stroke()

    def _draw(self, w, ctx):
        W, H = w.get_allocated_width(), w.get_allocated_height()
        # kadr samej maszyny (x 84–356, y 86–336 w układzie makiety)
        s = min(W / 272, H / 250)
        ctx.translate((W - 272 * s) / 2, (H - 250 * s) / 2)
        ctx.scale(s, s)
        ctx.translate(-84, -86)
        # cień, dach, bok, kolumna
        self._rgb(ctx, "#14171A")
        ctx.save(); ctx.translate(224, 324); ctx.scale(150, 10); ctx.arc(0, 0, 1, 0, 6.2832); ctx.restore(); ctx.fill()
        self._poly(ctx, [(100, 112), (126, 92), (348, 92), (322, 112)], "#15181C", "#5B616A")
        self._poly(ctx, [(322, 112), (348, 92), (348, 286), (322, 306)], "#0D0F11", "#5B616A")
        self._poly(ctx, [(100, 112), (322, 112), (322, 306), (100, 306)], "#0F1114", "#9AA0A8", 2.5)
        self._line(ctx, (274, 112), (274, 306), "#9AA0A8", 2.5)
        self._poly(ctx, [(282, 132), (314, 132), (314, 186), (282, 186)], "#0A0B0D", "#C9CDD2")
        self._poly(ctx, [(283, 133), (286, 133), (286, 185), (283, 185)], "#3ED663")
        for y in (270, 278, 286):
            self._line(ctx, (284, y), (312, y), "#3A3F46", 1.5)
        # światło
        if self.light:
            self._rgb(ctx, "#F0A04B", 0.18)
            ctx.rectangle(108, 126, 158, 120); ctx.fill()
        self._line(ctx, (112, 126), (262, 126), "#F0A04B" if self.light else "#3A3F46", 2.5)
        # szyba drzwi
        self._rgb(ctx, "#1A1E23", 0.4); ctx.rectangle(108, 120, 158, 178); ctx.fill()
        self._rgb(ctx, "#4A4F57"); ctx.set_line_width(1); ctx.rectangle(108, 120, 158, 178); ctx.stroke()
        # CoreXY: rama górna, belka X, głowica
        self._poly(ctx, [(112, 140), (124, 132), (252, 132), (262, 140)], None, "#3A3F46")
        self._line(ctx, (108, 152), (266, 152), "#9AA0A8", 2)
        self._poly(ctx, [(220, 142), (246, 142), (246, 162), (220, 162)], "#2A2E34", "#C9CDD2")
        self._poly(ctx, [(227, 162), (239, 162), (233, 170)], "#C9CDD2")
        # taśma (stół ruchomy)
        self._poly(ctx, [(112, 262), (258, 262), (266, 254), (120, 254)], "#2A2E34", "#9AA0A8")
        self._poly(ctx, [(112, 262), (258, 262), (258, 270), (112, 270)], "#1A1E23", "#5B616A")
        for x in (116, 254):
            self._rgb(ctx, "#15181C"); ctx.arc(x, 266, 6, 0, 6.2832); ctx.fill_preserve()
            self._rgb(ctx, "#9AA0A8"); ctx.set_line_width(1.5); ctx.stroke()
        self._poly(ctx, [(268, 258), (262, 255), (262, 261)], "#F0A04B")
        for x in (124, 246):
            self._line(ctx, (x, 272), (x, 298), "#3A3F46", 2)
        self._rgb(ctx, "#C9CDD2"); ctx.rectangle(258, 192, 3, 42); ctx.fill()
        for a, b in (((104, 306), (104, 314)), ((318, 306), (318, 314)), ((344, 286), (344, 294))):
            self._line(ctx, a, b, "#5B616A", 2.5)
        return False


class RevoHome(Gtk.Box):
    def __init__(self, panel):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.p = panel
        self.screen = panel._screen
        self.printer = panel._printer
        self.hours = None
        self.get_style_context().add_class("revo_home")

        top = Gtk.Box(spacing=8)
        self.state_lbl = _lbl("GOTOWA", "revo_state")
        self.info_lbl = _lbl("", "revo_info", 1.0)
        top.pack_start(self.state_lbl, False, False, 0)
        top.pack_end(self.info_lbl, True, True, 0)
        self.pack_start(top, False, False, 0)

        # schemat w środku, kafelki w kolumnach po bokach
        self.schem = Schematic("belt")
        self.schem.set_size_request(250, 330)
        self.schem.set_margin_start(8)
        self.schem.set_margin_end(8)
        self.t_nozzle = Tile("DYSZA", lambda: self.p.menu_item_clicked(None, {"panel": "temperature", "name": "Temperatura"}))
        self.t_bed = Tile("TAŚMA", lambda: self.p.menu_item_clicked(None, {"panel": "temperature", "name": "Temperatura"}))
        self.t_chamber = Tile("KOMORA")
        self.t_light = Tile("ŚWIATŁO", self.toggle_light)
        row = Gtk.Box(spacing=4)
        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, valign=Gtk.Align.CENTER)
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, valign=Gtk.Align.CENTER)
        left.pack_start(self.t_nozzle, False, False, 0)
        left.pack_start(self.t_bed, False, False, 0)
        right.pack_start(self.t_light, False, False, 0)
        right.pack_start(self.t_chamber, False, False, 0)
        row.pack_start(left, False, False, 0)
        row.pack_start(self.schem, True, True, 0)
        row.pack_start(right, False, False, 0)
        self.pack_start(row, True, True, 0)

        druk = Gtk.Button(label="DRUKUJ · WYBIERZ PLIK")
        druk.get_style_context().add_class("revo_print")
        druk.connect("clicked", lambda *a: self.p.menu_item_clicked(None, {"panel": "gcodes", "name": "Pliki"}))
        self.pack_start(druk, False, False, 0)

        pre = Gtk.Grid(column_homogeneous=True, column_spacing=8)
        for i, (name, e, b) in enumerate(PRESETS):
            bt = Gtk.Button(label=name)
            bt.get_style_context().add_class("revo_preset")
            bt.connect("clicked", self.preheat, e, b)
            pre.attach(bt, i, 0, 1, 1)
        cool = Gtk.Button(label="Chłodź")
        cool.get_style_context().add_class("revo_preset")
        cool.connect("clicked", self.preheat, 0, 0)
        pre.attach(cool, 3, 0, 1, 1)
        self.pack_start(pre, False, False, 0)

        nav = Gtk.Grid(column_homogeneous=True, column_spacing=4)
        items = [("move", "Ruch", lambda: self.p.menu_item_clicked(None, {"panel": "move", "name": "Ruch"})),
                 ("filament", "Filament", lambda: self.p.menu_item_clicked(None, {"panel": "extrude", "name": "Filament"})),
                 ("file", "Pliki", lambda: self.p.menu_item_clicked(None, {"panel": "gcodes", "name": "Pliki"})),
                 ("complete", "Test", self.selftest),
                 ("settings", "Menu", self.open_menu)]
        for i, (icon, name, cb) in enumerate(items):
            bt = self.p._gtk.Button(icon, name, None, 0.9)
            bt.get_style_context().add_class("revo_nav")
            bt.connect("clicked", lambda w, c=cb: c())
            nav.attach(bt, i, 0, 1, 1)
        self.pack_start(nav, False, False, 0)

        self._timer = None

    # --- akcje ---
    def gcode(self, script):
        self.screen._ws.api.gcode_script(script)

    def preheat(self, widget, ext, bed):
        self.gcode(f"SET_HEATER_TEMPERATURE HEATER=extruder TARGET={ext}\nSET_HEATER_TEMPERATURE HEATER=heater_bed TARGET={bed}")

    def toggle_light(self):
        pin = logic.light_pin(self.printer)
        if pin:
            on = (self.printer.get_stat(f"output_pin {pin}", "value") or 0) > 0
            self.gcode(f"SET_PIN PIN={pin} VALUE={0 if on else 1}")

    def selftest(self):
        self.gcode("REVO_SELFTEST")

    def open_menu(self):
        self.screen.show_panel("menu", title="Menu", panel_name="revo_menu",
                               items=self.screen._config.get_menu_items("__main"))

    # --- odświeżanie ---
    def start(self):
        if self._timer is None:
            self.refresh()
            self._timer = GLib.timeout_add_seconds(1, self.refresh)
            self._poll_agent()
            GLib.timeout_add_seconds(60, self._poll_agent)

    def stop(self):
        if self._timer:
            GLib.source_remove(self._timer)
            self._timer = None

    def _poll_agent(self):
        def run():
            try:
                with urllib.request.urlopen("http://127.0.0.1:7130/status", timeout=1) as r:
                    h = json.loads(r.read().decode()).get("hours")
                GLib.idle_add(self._set_hours, h)
            except Exception:
                pass
        threading.Thread(target=run, daemon=True).start()
        return self._timer is not None

    def _set_hours(self, h):
        self.hours = h
        return False

    def refresh(self):
        try:
            v = logic.view(self.printer, self.hours)
            self.state_lbl.set_label(v["state"])
            ctx = self.state_lbl.get_style_context()
            for c in ("revo_ok", "revo_warn", "revo_err"):
                ctx.remove_class(c)
            ctx.add_class(v["state_class"])
            self.info_lbl.set_label(v["info"])
            self.t_nozzle.value.set_label(v["nozzle_size"])
            self.t_nozzle.sub.set_label(v["nozzle_temp"])
            self.t_bed.value.set_label(v["bed_temp"])
            self.t_chamber.value.set_label(v["chamber_temp"])
            self.t_light.value.set_label(v["light"])
            self.schem.light = v["light_on"]
            self.schem.queue_draw()
        except Exception as e:
            logging.debug(f"RevoHome: {e}")
        return self._timer is not None
