# Revo OS – Ruch: pozycja, bazowanie, osie, taśma, E-STOP (przytrzymanie 1 s)
import time

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

from ks_includes.screen_panel import ScreenPanel
from ks_includes.widgets.revo_home import RevoActions, Tile, _lbl

STEPS = [0.1, 1, 10, 50, 100]


class Panel(RevoActions, ScreenPanel):
    def __init__(self, screen, title, **kwargs):
        super().__init__(screen, title or "Ruch")
        self.p, self.printer, self.screen = self, self._printer, self._screen
        self.step, self._timer, self._estop = 10, None, None
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        box.get_style_context().add_class("revo_home")

        pos = Gtk.Grid(column_homogeneous=True, column_spacing=8)
        self.tp = {a: Tile(a) for a in "XYZ"}
        for i, a in enumerate("XYZ"):
            self.tp[a].sub.set_no_show_all(True)
            pos.attach(self.tp[a], i, 0, 1, 1)
        box.pack_start(pos, False, False, 0)
        self.homed = _lbl("", "revo_info", 0.5)
        box.pack_start(self.homed, False, False, 0)

        hg = Gtk.Grid(column_homogeneous=True, column_spacing=6, row_spacing=6)
        for i, (lab, g, cls) in enumerate((("BAZUJ", "G28", "revo_print"), ("X", "G28 X", "revo_preset"),
                                           ("Y", "G28 Y", "revo_preset"), ("Z", "G28 Z", "revo_preset"))):
            hg.attach(self._btn(lab, lambda w, g=g: self.gcode(g), cls, 44), i, 0, 1, 1)
        hg.attach(self._btn("POZIOMUJ BRAMĘ", lambda w: self.gcode("CQGL"), "revo_preset", 40), 0, 1, 2, 1)
        hg.attach(self._btn("WYŁĄCZ SILNIKI", lambda w: self.gcode("M84"), "revo_preset", 40), 2, 1, 2, 1)
        box.pack_start(hg, False, False, 0)

        box.pack_start(_lbl("KROK (mm)", "revo_tile_title"), False, False, 2)
        sg = Gtk.Grid(column_homogeneous=True, column_spacing=6)
        first = None
        for i, st in enumerate(STEPS):
            rb = Gtk.RadioButton.new_with_label_from_widget(first, f"{st:g}")
            rb.set_mode(False)
            rb.get_style_context().add_class("revo_preset")
            rb.get_style_context().add_class("revo_compact")
            first = first or rb
            rb.set_active(st == self.step)
            rb.connect("toggled", lambda w, st=st: w.get_active() and setattr(self, "step", st))
            sg.attach(rb, i, 0, 1, 1)
        box.pack_start(sg, False, False, 0)

        jg = Gtk.Grid(column_homogeneous=True, row_homogeneous=True, column_spacing=6, row_spacing=6)
        for (lab, ax, d, c, r) in (("Y+", "Y", 1, 1, 0), ("X−", "X", -1, 0, 1), ("X+", "X", 1, 2, 1), ("Y−", "Y", -1, 1, 2),
                                   ("Z+", "Z", 1, 3, 0), ("Z−", "Z", -1, 3, 2)):
            jg.attach(self._btn(lab, lambda w, ax=ax, d=d: self.jog(ax, d), "revo_preset", 44), c, r, 1, 1)
        box.pack_start(jg, False, False, 0)

        box.pack_start(_lbl("TAŚMA", "revo_tile_title"), False, False, 2)
        bg = Gtk.Grid(column_homogeneous=True, column_spacing=6)
        bg.attach(self._btn("◂ COFNIJ", lambda w: self.belt(-1), "revo_preset", 42), 0, 0, 1, 1)
        bg.attach(self._btn("NAPRZÓD ▸", lambda w: self.belt(1), "revo_preset", 42), 1, 0, 1, 1)
        bg.attach(self._btn("ZRZUĆ WYDRUK", lambda w: self.gcode("CLEAR_BELT"), "revo_preset", 42), 2, 0, 1, 1)
        box.pack_start(bg, False, False, 0)

        self.es = Gtk.Button(label="E-STOP · PRZYTRZYMAJ 1 s")
        self.es.get_style_context().add_class("revo_estop")
        self.es.set_size_request(-1, 48)
        self.es.connect("pressed", self._es_down)
        self.es.connect("released", self._es_up)
        box.pack_end(self.es, False, False, 0)
        self.content.add(box)

    def _btn(self, lab, cb, cls, h):
        b = Gtk.Button(label=lab)
        b.get_style_context().add_class(cls)
        b.get_style_context().add_class("revo_compact")
        b.set_size_request(-1, h)
        b.connect("clicked", cb)
        return b

    def jog(self, ax, d):
        f = 600 if ax == "Z" else 6000
        self.gcode(f"G91\nG1 {ax}{self.step * d:g} F{f}\nG90")

    def belt(self, d):
        self.gcode(f"MANUAL_STEPPER STEPPER=belt_drives SET_POSITION=0 MOVE={self.step * d:g} SPEED=50")

    def _es_down(self, w):
        self._estop = time.monotonic()
        GLib.timeout_add(100, self._es_tick)

    def _es_up(self, w):
        self._estop = None
        self.es.set_label("E-STOP · PRZYTRZYMAJ 1 s")

    def _es_tick(self):
        if self._estop is None:
            return False
        left = 1.0 - (time.monotonic() - self._estop)
        if left <= 0:
            self._estop = None
            self._screen._ws.api.emergency_stop()
            self.es.set_label("ZATRZYMANO")
            return False
        self.es.set_label(f"PRZYTRZYMAJ… {left:.1f} s")
        return True

    def refresh(self):
        th = self._printer.get_stat("toolhead") or {}
        p = th.get("position") or []
        for i, a in enumerate("XYZ"):
            self.tp[a].value.set_label(f"{p[i]:.2f}" if len(p) > i else "–")
        hm = th.get("homed_axes", "")
        self.homed.set_label(f"Zbazowane: {', '.join(hm.upper())}" if hm else "Osie niezbazowane – najpierw BAZUJ")
        return self._timer is not None

    def activate(self):
        self.refresh()
        self._timer = GLib.timeout_add(500, self.refresh)

    def deactivate(self):
        if self._timer:
            GLib.source_remove(self._timer)
            self._timer = None
