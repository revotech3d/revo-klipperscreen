# Revo OS – Filament: temperatura dyszy, ładowanie/wyładowanie, wytłaczanie objętościowe, dysza
import threading

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

from ks_includes.revo_flow import FIL_AREA, extrude_script, flow_limit
from ks_includes.screen_panel import ScreenPanel
from ks_includes.widgets.revo_home import RevoActions, Tile, _lbl

FLOWS = [5, 10, 15, 25, 35, 45, 60]
TIMES = [5, 10, 20]


class Panel(RevoActions, ScreenPanel):
    def __init__(self, screen, title, **kwargs):
        super().__init__(screen, title or "Filament")
        self.p, self.printer, self.screen = self, self._printer, self._screen
        self.flow, self.secs, self._timer = 10, 10, None
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.get_style_context().add_class("revo_home")

        top = Gtk.Grid(column_homogeneous=True, column_spacing=10)
        self.t_temp = Tile("TEMPERATURA DYSZY", lambda: self.heater_dialog("extruder", "DYSZA", [0, 200, 210, 220, 240, 250, 260, 280], 320))
        self.t_noz = Tile("DYSZA", self.nozzle_dialog)
        for t in (self.t_temp, self.t_noz):
            t.sub.set_line_wrap(True)
            t.sub.set_max_width_chars(18)
        self.t_sz = Tile("SZPULA", lambda: self._screen.show_panel("revo_szpula", "Szpula", panel_name="revo_szpula_s", mode="szpula"))
        self.t_sz.sub.set_line_wrap(True)
        top.attach(self.t_temp, 0, 0, 1, 1)
        top.attach(self.t_noz, 1, 0, 1, 1)
        top.attach(self.t_sz, 2, 0, 1, 1)
        box.pack_start(top, False, False, 0)
        wiz = Gtk.Button(label="WYMIANA FILAMENTU – KROK PO KROKU")
        wiz.get_style_context().add_class("revo_print")
        wiz.set_size_request(-1, 64)
        wiz.connect("clicked", lambda w: self._screen.show_panel("revo_szpula", "Wymiana filamentu", panel_name="revo_szpula_z", mode="zmiana"))
        box.pack_start(wiz, False, False, 4)
        self._sz, self._n = None, 0

        lu = Gtk.Grid(column_homogeneous=True, column_spacing=8)
        for i, (lab, mac) in enumerate((("ZAŁADUJ FILAMENT", "LOAD_FILAMENT"), ("WYŁADUJ FILAMENT", "UNLOAD_FILAMENT"))):
            b = Gtk.Button(label=lab)
            b.get_style_context().add_class("revo_print" if i == 0 else "revo_preset")
            b.set_size_request(-1, 60)
            b.connect("clicked", lambda w, m=mac: self.gcode(m))
            lu.attach(b, i, 0, 1, 1)
        box.pack_start(lu, False, False, 4)

        box.pack_start(_lbl("PRZEPŁYW (mm³/s)", "revo_tile_title"), False, False, 4)
        self.fg = Gtk.Grid(column_homogeneous=True, column_spacing=6, row_spacing=6)
        self.fbtn = {}
        first = None
        for i, f in enumerate(FLOWS):
            rb = Gtk.RadioButton.new_with_label_from_widget(first, str(f))
            rb.set_mode(False)
            rb.get_style_context().add_class("revo_preset")
            first = first or rb
            rb.set_active(f == self.flow)
            rb.connect("toggled", lambda w, f=f: w.get_active() and self._set("flow", f))
            self.fbtn[f] = rb
            self.fg.attach(rb, i % 4, i // 4, 1, 1)
        box.pack_start(self.fg, False, False, 0)

        box.pack_start(_lbl("CZAS (s)", "revo_tile_title"), False, False, 4)
        tg = Gtk.Grid(column_homogeneous=True, column_spacing=6)
        first = None
        for i, t in enumerate(TIMES):
            rb = Gtk.RadioButton.new_with_label_from_widget(first, f"{t} s")
            rb.set_mode(False)
            rb.get_style_context().add_class("revo_preset")
            first = first or rb
            rb.set_active(t == self.secs)
            rb.connect("toggled", lambda w, t=t: w.get_active() and self._set("secs", t))
            tg.attach(rb, i, 0, 1, 1)
        box.pack_start(tg, False, False, 0)

        self.calc = _lbl("", "revo_info", 0.5)
        self.calc.set_line_wrap(True)
        self.calc.set_max_width_chars(40)
        box.pack_start(self.calc, False, False, 4)
        ex = Gtk.Grid(column_homogeneous=True, column_spacing=8)
        b1 = Gtk.Button(label="COFNIJ 5 mm")
        b1.get_style_context().add_class("revo_preset")
        b1.connect("clicked", lambda w: self.gcode("M83\nG1 E-5 F1800\nM82"))
        b2 = Gtk.Button(label="WYTŁOCZ")
        b2.get_style_context().add_class("revo_print")
        b2.connect("clicked", self.extrude)
        for i, b in enumerate((b1, b2)):
            b.set_size_request(-1, 60)
            ex.attach(b, i, 0, 1, 1)
        box.pack_start(ex, False, False, 0)
        self.content.add(box)

    def _set(self, k, v):
        setattr(self, k, v)
        self.refresh()

    def _diam(self):
        return (self._printer.get_stat("save_variables", "variables") or {}).get("revo_nozzle_diameter", 0.4)

    def extrude(self, *a):
        if self.flow > flow_limit(self._diam()):
            self._screen.show_popup_message(f"Przepływ {self.flow} mm³/s przekracza możliwości dyszy.", 2)
            return
        self.gcode("M83\n" + extrude_script(self.flow, self.secs) + "\nM82")

    def refresh(self):
        lim = flow_limit(self._diam())
        for f, b in self.fbtn.items():
            b.set_sensitive(f <= lim)
        if self.flow > lim:
            self.fbtn[10].set_active(True)
        mm = self.flow * self.secs / FIL_AREA
        self.calc.set_label(f"{self.flow} mm³/s × {self.secs} s = {self.flow * self.secs} mm³ ({mm:.0f} mm filament)\nnozzle limit: {lim} mm³/s")
        st = self._printer.get_stat("extruder") or {}
        t, tg = st.get("temperature"), st.get("target") or 0
        self.t_temp.value.set_label("–" if t is None else f"{t:.0f}°")
        self.t_temp.sub.set_label(f"cel {tg:.0f}°" if tg else "grzanie wyłączone")
        v = str((self._printer.get_stat("save_variables", "variables") or {}).get("revo_nozzle", "")).split()
        self.t_noz.value.set_label(f"Ø{v[0]}" if v else "Ø?")
        self.t_noz.sub.set_label({"mosiadz": "mosiądz", "stal": "stal hart.", "wolfram": "wolfram"}.get(v[1], v[1]) if len(v) > 1 else "dotknij")
        self._n += 1
        if self._n % 5 == 1:
            threading.Thread(target=self._load_sz, daemon=True).start()
        if self._sz is not None:
            from ks_includes import revo_filament_logic as fl
            left = self._sz.get("zostalo_g")
            self.t_sz.value.set_label("?" if left is None else f"{left:.0f} g")
            self.t_sz.sub.set_label(self._sz.get("mat") or "dotknij")
        return self._timer is not None

    def _load_sz(self):
        from ks_includes import revo_agent_client as agent
        code, st = agent.call("/status", timeout=2)
        if code == 200:
            self._sz = st.get("szpula") or {}

    def activate(self):
        self.refresh()
        self._timer = GLib.timeout_add_seconds(1, self.refresh)

    def deactivate(self):
        if self._timer:
            GLib.source_remove(self._timer)
            self._timer = None
