# Revo OS – Ruch: pozycja, bazowanie, osie, taśma (E-STOP na dolnym pasku)

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

from ks_includes.screen_panel import ScreenPanel
from ks_includes.widgets.revo_home import RevoActions, Tile, _lbl, window

STEPS = [0.1, 1, 10, 50, 100]


class Panel(RevoActions, ScreenPanel):
    def __init__(self, screen, title, **kwargs):
        super().__init__(screen, title or "Motion")
        self.p, self.printer, self.screen = self, self._printer, self._screen
        self.step, self._timer = 10, None
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        box.get_style_context().add_class("revo_home")

        pos = Gtk.Grid(column_homogeneous=True, column_spacing=8)
        self.tp = {a: Tile(a) for a in "XYZ"}
        for i, a in enumerate("XYZ"):
            self.tp[a].sub.set_no_show_all(True)
            pos.attach(self.tp[a], i, 0, 1, 1)
        w1 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        w1.set_margin_start(6); w1.set_margin_end(6); w1.set_margin_top(6); w1.set_margin_bottom(6)
        w1.pack_start(pos, False, False, 0)
        self.homed = _lbl("", "revo_info", 0.5)
        w1.pack_start(self.homed, False, False, 0)

        hg = Gtk.Grid(column_homogeneous=True, column_spacing=6, row_spacing=6)
        for i, (lab, g, cls) in enumerate((("HOME", "G28", "revo_print"), ("X", "G28 X", "revo_preset"),
                                           ("Y", "G28 Y", "revo_preset"), ("Z", "G28 Z", "revo_preset"))):
            hg.attach(self._btn(lab, lambda w, g=g: self.gcode(g), cls, 38), i, 0, 1, 1)
        hg.attach(self._btn("GANTRY LEVELING", lambda w: self.gcode("CQGL"), "revo_preset", 36), 0, 1, 2, 1)
        hg.attach(self._btn("DISABLE MOTORS", lambda w: self.gcode("M84"), "revo_preset", 36), 2, 1, 2, 1)
        w1.pack_start(hg, False, False, 0)
        box.pack_start(window("POSITION", w1, "X · Y · Z"), False, False, 0)

        w2 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        w2.set_margin_start(6); w2.set_margin_end(6); w2.set_margin_top(6); w2.set_margin_bottom(6)
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
        w2.pack_start(sg, False, False, 0)

        jg = Gtk.Grid(column_homogeneous=True, row_homogeneous=True, column_spacing=6, row_spacing=6)
        # a plain cross (as seen from above: ▲ = to the back, ◀ = to the left) and Z as UP / DOWN of the head
        for (lab, ax, d, c, r) in (("▲", "Y", 1, 1, 0), ("◀", "X", -1, 0, 1), ("▶", "X", 1, 2, 1), ("▼", "Y", -1, 1, 2),
                                   ("▲ UP", "Z", 1, 3, 0), ("▼ DOWN", "Z", -1, 3, 2)):
            jg.attach(self._btn(lab, lambda w, ax=ax, d=d: self.jog(ax, d), "revo_preset", 34), c, r, 1, 1)
        for (lab, c) in (("X · Y", 1), ("Z", 3)):   # the axis names in the middle row, for service
            jg.attach(_lbl(lab, "revo_tile_title", 0.5), c, 1, 1, 1)
        w2.pack_start(jg, False, False, 0)
        box.pack_start(window("JOG", w2, "STEP mm"), False, False, 0)

        from ks_includes import revo_home_logic as lg0
        belt_on = lg0.is_belt(self._printer)
        bg = Gtk.Grid(column_homogeneous=True, column_spacing=6)
        bg.attach(self._btn("◂ BACK", lambda w: self.belt(-1), "revo_preset", 36), 0, 0, 1, 1)
        bg.attach(self._btn("FORWARD ▸", lambda w: self.belt(1), "revo_preset", 36), 1, 0, 1, 1)
        ej = Gtk.Button(label="EJECT\n(hold)")
        ej.get_style_context().add_class("revo_preset")
        ej.set_size_request(-1, 36)
        from ks_includes.widgets.revo_hold import BeltHold
        from ks_includes import revo_home_logic as lg
        self._belt_hold = BeltHold(ej, self._screen._ws.api.gcode_script, lambda: lg.cfg(self._printer, "belt_stepper", ""))
        bg.attach(ej, 2, 0, 1, 1)
        if belt_on:
            bg.set_margin_start(6); bg.set_margin_end(6); bg.set_margin_top(6); bg.set_margin_bottom(6)
            box.pack_start(window("BELT", bg, "EJECT"), False, False, 0)

        # E-STOP: the red E-STOP · HOLD 1 S of the bottom bar (on every screen) – a second one here pushed the bar
        # off the bottom of the screen
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

    def _belt(self):
        from ks_includes import revo_home_logic as lg
        return lg.cfg(self._printer, "belt_stepper", "belt_drives")

    def belt(self, d):
        self.gcode(f"MANUAL_STEPPER STEPPER={self._belt()} SET_POSITION=0 MOVE={self.step * d:g} SPEED=50")

    def refresh(self):
        th = self._printer.get_stat("toolhead") or {}
        p = th.get("position") or []
        for i, a in enumerate("XYZ"):
            self.tp[a].value.set_label(f"{p[i]:.2f}" if len(p) > i else "–")
        hm = th.get("homed_axes", "")
        self.homed.set_label(f"Homed: {', '.join(hm.upper())}" if hm else "Axes not homed – HOME first")
        return self._timer is not None

    def activate(self):
        self.refresh()
        self._timer = GLib.timeout_add(500, self.refresh)

    def deactivate(self):
        if self._timer:
            GLib.source_remove(self._timer)
            self._timer = None
