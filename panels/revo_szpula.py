# Revo OS – wymiana filamentu krok po kroku (materiał → wyładuj → załaduj → szpula) albo samo ustawienie szpuli.
# Stan szpuli trzyma agent Revo (odejmuje zużycie w czasie druku); ekran i Panel Revo tylko go ustawiają.
import threading

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

from ks_includes import revo_agent_client as agent
from ks_includes import revo_filament_logic as fl
from ks_includes.screen_panel import ScreenPanel
from ks_includes.widgets.revo_home import _lbl
from ks_includes.widgets.revo_pin import PinPad

STEPS = ["material", "wyladuj", "zaladuj", "szpula", "koniec"]


class Panel(ScreenPanel):
    def __init__(self, screen, title, mode="zmiana", **kwargs):
        super().__init__(screen, title or ("Wymiana filamentu" if mode == "zmiana" else "Szpula"))
        self.mode = mode
        self.steps = STEPS if mode == "zmiana" else ["szpula", "koniec"]
        self.step = 0
        self.sz = {"mat": "", "pelna_g": 1000.0, "zostalo_g": None}
        self.new_mat = None
        self._timer = None
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.box.get_style_context().add_class("revo_home")
        self.content.add(self.box)
        self.box.pack_start(_lbl("Wczytywanie…", "revo_info"), False, False, 0)
        threading.Thread(target=self._load, daemon=True).start()

    def _load(self):
        code, st = agent.call("/status", timeout=2)
        if code == 200 and st.get("szpula"):
            self.sz = st["szpula"]
        GLib.idle_add(self.render)

    # ---------- pomocnicze ----------
    def gcode(self, s):
        self._screen._ws.api.gcode_script(s)

    def save(self, body):
        threading.Thread(target=agent.call, args=("/szpula", body), kwargs={"timeout": 3}, daemon=True).start()

    def _btn(self, label, cb, cls="revo_preset", h=60):
        b = Gtk.Button(label=label)
        b.get_style_context().add_class(cls)
        b.set_size_request(-1, h)
        b.get_child().set_line_wrap(True)
        b.connect("clicked", lambda w: cb())
        return b

    def _head(self, title, text):
        if self.mode == "zmiana":
            self.box.pack_start(_lbl(f"KROK {self.step + 1} / {len(self.steps)}", "revo_test_head"), False, False, 0)
            bar = Gtk.ProgressBar(fraction=(self.step + 1) / len(self.steps))
            bar.get_style_context().add_class("revo_progress")
            self.box.pack_start(bar, False, False, 0)
        self.box.pack_start(_lbl(title, "revo_test_name"), False, False, 8)
        t = _lbl(text, "revo_test_desc")
        t.set_line_wrap(True)
        self.box.pack_start(t, False, False, 0)

    def _nav(self, label="DALEJ", cb=None, sensitive=True):
        g = Gtk.Grid(column_homogeneous=True, column_spacing=8)
        g.attach(self._btn("PRZERWIJ", self.abort, "revo_t_plain", 64), 0, 0, 1, 1)
        self.next_btn = self._btn(label, cb or self.next, "revo_t_ok", 64)
        self.next_btn.set_sensitive(sensitive)
        g.attach(self.next_btn, 1, 0, 1, 1)
        self.box.pack_end(g, False, False, 0)

    def _temp(self):
        e = self._printer.get_stat("extruder") or {}
        return float(e.get("temperature") or 0)

    def render(self):
        if self._timer:
            GLib.source_remove(self._timer)
            self._timer = None
        for c in self.box.get_children():
            self.box.remove(c)
        getattr(self, "s_" + self.steps[self.step])()
        self.box.show_all()
        return False

    def next(self):
        self.step += 1
        self.render()

    def abort(self):
        if self.mode == "zmiana":
            self.gcode("SET_HEATER_TEMPERATURE HEATER=extruder TARGET=0")
        self._screen._menu_go_back()

    def deactivate(self):
        if self._timer:
            GLib.source_remove(self._timer)
            self._timer = None

    # ---------- kroki ----------
    def s_material(self):
        self._head("JAKI FILAMENT ZAKŁADASZ?", f"Teraz: {fl.label(self.sz)}. Choose the new material – the machine sets the temperature.")
        g = Gtk.Grid(column_homogeneous=True, column_spacing=8, row_spacing=8)
        first = None
        for i, (m, t) in enumerate(fl.MATERIALS):
            rb = Gtk.RadioButton.new_with_label_from_widget(first, f"{m}\n{t}°")
            rb.set_mode(False)
            rb.get_style_context().add_class("revo_preset")
            rb.set_size_request(-1, 64)
            first = first or rb
            if self.new_mat is None:
                self.new_mat = self.sz.get("mat") if self.sz.get("mat") in fl.TEMP else "PLA"
            rb.set_active(m == self.new_mat)
            rb.connect("toggled", lambda w, mm=m: w.get_active() and setattr(self, "new_mat", mm))
            g.attach(rb, i % 3, i // 3, 1, 1)
        self.box.pack_start(g, False, False, 6)
        busy = self._printer.state in ("printing",)
        if busy:
            self.box.pack_start(_lbl("Podczas druku wymiana jest możliwa tylko po pauzie.", "revo_err"), False, False, 4)
        self._nav(sensitive=not busy)

    def s_wyladuj(self):
        self.temp = fl.swap_temp(self.sz.get("mat"), self.new_mat)
        self._head("WYŁADUJ STARY FILAMENT", f"The nozzle heats to {self.temp}°. When it is hot, press UNLOAD "
                   "and pull the filament out of the head. If the head is empty – continue.")
        self.gcode(f"SET_HEATER_TEMPERATURE HEATER=extruder TARGET={self.temp}")
        self.tlbl = _lbl("", "revo_big", 0.5)
        self.box.pack_start(self.tlbl, False, False, 10)
        self.act = self._btn("WYŁADUJ", lambda: self.gcode("UNLOAD_FILAMENT"), "revo_print", 70)
        self.box.pack_start(self.act, False, False, 0)
        self._nav()
        self._timer = GLib.timeout_add(1000, self._tick)
        self._tick()

    def _tick(self):
        t = self._temp()
        self.tlbl.set_label(f"{t:.0f}° / {self.temp}°")
        self.act.set_sensitive(t >= self.temp - 5)
        return True

    def s_zaladuj(self):
        self._head("ZAŁÓŻ NOWY FILAMENT", f"Push {self.new_mat} into the head until you feel resistance and press LOAD. "
                   "When clean new colour comes out of the nozzle – continue. If not, load again.")
        self.tlbl = _lbl("", "revo_big", 0.5)
        self.box.pack_start(self.tlbl, False, False, 10)
        self.act = self._btn("ZAŁADUJ", lambda: self.gcode("LOAD_FILAMENT"), "revo_print", 70)
        self.box.pack_start(self.act, False, False, 0)
        self._nav("CZYSTY KOLOR – DALEJ")
        self._timer = GLib.timeout_add(1000, self._tick)
        self._tick()

    def s_szpula(self):
        mat = self.new_mat or self.sz.get("mat") or ""
        self._head("ILE FILAMENTU NA SZPULI?", "The machine subtracts usage with every print and warns if it may run out. "
                   f"Now: {fl.label(self.sz)}.")
        self.box.pack_start(_lbl("NOWA, PEŁNA SZPULA (NETTO)", "revo_tile_title"), False, False, 4)
        g = Gtk.Grid(column_homogeneous=True, column_spacing=8, row_spacing=8)
        for i, w in enumerate(fl.SPOOLS):
            g.attach(self._btn(f"{w / 1000:g} kg", lambda w=w: self.done({"mat": mat, "pelna_g": w, "nowa": True})), i % 3, i // 3, 1, 1)
        self.box.pack_start(g, False, False, 0)
        r = Gtk.Grid(column_homogeneous=True, column_spacing=8)
        r.attach(self._btn("WPISZ ILE ZOSTAŁO (g)", lambda: self.enter(mat)), 0, 0, 1, 1)
        if self.mode == "szpula" and self.sz.get("pelna_g"):
            r.attach(self._btn("RESET: PEŁNA", lambda: self.done({"mat": mat, "nowa": True})), 1, 0, 1, 1)
        r.attach(self._btn("NIE WIEM", lambda: self.done({"mat": mat, "nieznana": True})), 2 if self.mode == "szpula" else 1, 0, 1, 1)
        self.box.pack_start(r, False, False, 6)
        g2 = Gtk.Grid(column_homogeneous=True)
        g2.attach(self._btn("ANULUJ", self.abort, "revo_t_plain", 64), 0, 0, 1, 1)
        self.box.pack_end(g2, False, False, 0)

    def enter(self, mat):
        for c in self.box.get_children():
            self.box.remove(c)
        pad = PinPad(self._screen, "ILE GRAMÓW ZOSTAŁO?", lambda v, p: self.done({"mat": mat, "zostalo_g": int(v)}),
                     self.render, length=(1, 5), secret=False, suffix=" g")
        pad.set_size_request(-1, -1)
        self.box.pack_start(pad, True, True, 0)
        self.box.show_all()

    def done(self, body):
        if self.mode == "zmiana":
            self.gcode("SET_HEATER_TEMPERATURE HEATER=extruder TARGET=0")
        self.save(body)
        self.sz.update({k: v for k, v in body.items() if k in ("mat", "pelna_g", "zostalo_g")})
        if body.get("nowa"):
            self.sz["zostalo_g"] = self.sz.get("pelna_g") or 1000
        if body.get("nieznana"):
            self.sz["zostalo_g"] = None
        self.step = len(self.steps) - 1
        self.render()

    def s_koniec(self):
        self._head("GOTOWE", f"Zapisano: {fl.label(self.sz)}." + (" Nozzle heating off." if self.mode == "zmiana" else ""))
        self.box.pack_end(self._btn("ZAKOŃCZ", lambda: self._screen._menu_go_back(home=True), "revo_t_ok", 70), False, False, 0)
