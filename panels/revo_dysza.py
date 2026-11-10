# Revo OS – prowadzona wymiana dyszy: wybór nowej, wyładowanie filamentu, nagrzanie, wymiana na gorąco, zapis.
# Na końcu: nowa dysza zapisana, przegląd „Dysza” wyzerowany, wniosek o reset licznika zużycia do Revotech.
import threading

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

from ks_includes import revo_agent_client as agent
from ks_includes import revo_serwis_logic as serwis
from ks_includes.screen_panel import ScreenPanel
from ks_includes.widgets.revo_home import _lbl

HOT = 250          # wymiana na gorąco – ta sama temperatura dla mosiądzu, stali i wolframu
D_OPTS = ["0.25", "0.4", "0.6", "0.8"]
T_OPTS = [("mosiadz", "Mosiądz"), ("stal", "Stal hart."), ("wolfram", "Wolfram")]
STEPS = ["wybor", "filament", "grzanie", "odkrec", "wkrec", "koniec"]


class Panel(ScreenPanel):
    def __init__(self, screen, title, **kwargs):
        super().__init__(screen, title or "Wymiana dyszy")
        self.step = 0
        vars_ = self._printer.get_stat("save_variables", "variables") or {}
        cur = str(vars_.get("revo_nozzle", "")).split()
        self.old = " ".join(cur) or "nie ustawiono"
        self.new = {"d": cur[0] if cur and cur[0] in D_OPTS else "0.4", "t": cur[1] if len(cur) > 1 else "stal"}
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.box.get_style_context().add_class("revo_home")
        self.content.add(self.box)
        self._timer = None
        self.render()

    # ---------- pomocnicze ----------
    def gcode(self, s):
        self._screen._ws.api.gcode_script(s)

    def _clear(self):
        for c in self.box.get_children():
            self.box.remove(c)

    def _btn(self, label, cb, cls="revo_preset", h=64):
        b = Gtk.Button(label=label)
        b.get_style_context().add_class(cls)
        b.set_size_request(-1, h)
        b.get_child().set_line_wrap(True)
        b.connect("clicked", lambda w: cb())
        return b

    def _head(self, title, text):
        n = self.step
        self.box.pack_start(_lbl(f"KROK {n + 1} / {len(STEPS)}", "revo_test_head"), False, False, 0)
        bar = Gtk.ProgressBar(fraction=(n + 1) / len(STEPS))
        bar.get_style_context().add_class("revo_progress")
        self.box.pack_start(bar, False, False, 0)
        self.box.pack_start(_lbl(title, "revo_test_name"), False, False, 8)
        t = _lbl(text, "revo_test_desc")
        t.set_line_wrap(True)
        self.box.pack_start(t, False, False, 0)

    def _nav(self, next_label="DALEJ", on_next=None, sensitive=True):
        g = Gtk.Grid(column_homogeneous=True, column_spacing=8)
        g.attach(self._btn("PRZERWIJ", self.abort, "revo_t_plain"), 0, 0, 1, 1)
        self.next_btn = self._btn(next_label, on_next or self.next, "revo_t_ok")
        self.next_btn.set_sensitive(sensitive)
        g.attach(self.next_btn, 1, 0, 1, 1)
        self.box.pack_end(g, False, False, 0)

    def _temp(self):
        e = self._printer.get_stat("extruder") or {}
        return float(e.get("temperature") or 0), float(e.get("target") or 0)

    def render(self):
        if self._timer:
            GLib.source_remove(self._timer)
            self._timer = None
        self._clear()
        getattr(self, "s_" + STEPS[self.step])()
        self.box.show_all()

    def next(self):
        self.step += 1
        self.render()

    def abort(self):
        self.gcode("SET_HEATER_TEMPERATURE HEATER=extruder TARGET=0")
        self.step = 0
        self._screen._menu_go_back()

    def deactivate(self):
        if self._timer:
            GLib.source_remove(self._timer)
            self._timer = None

    # ---------- kroki ----------
    def s_wybor(self):
        self._head("WYMIANA DYSZY", f"Teraz zamontowana: {self.old}. Wybierz dyszę, którą zakładasz. "
                   "Maszyna poprowadzi Cię krok po kroku; dyszę wymienia się na gorąco, w rękawicach.")
        for head, key, opts in (("ŚREDNICA", "d", [(o, f"Ø{o}") for o in D_OPTS]), ("MATERIAŁ", "t", T_OPTS)):
            self.box.pack_start(_lbl(head, "revo_tile_title"), False, False, 4)
            g = Gtk.Grid(column_homogeneous=True, column_spacing=8)
            first = None
            for i, (v, name) in enumerate(opts):
                rb = Gtk.RadioButton.new_with_label_from_widget(first, name)
                rb.set_mode(False)
                rb.get_style_context().add_class("revo_preset")
                rb.set_size_request(-1, 56)
                first = first or rb
                rb.set_active(self.new[key] == v)
                rb.connect("toggled", lambda w, k=key, val=v: w.get_active() and self.new.__setitem__(k, val))
                g.attach(rb, i, 0, 1, 1)
            self.box.pack_start(g, False, False, 0)
        if self._printer.state in ("printing", "paused"):
            self._nav(sensitive=False)
            self.box.pack_start(_lbl("Najpierw zakończ albo anuluj druk.", "revo_err"), False, False, 6)
        else:
            self._nav()

    def s_filament(self):
        self._head("WYŁADUJ FILAMENT", "Głowica przesunie się w wygodne miejsce i nagrzeje do 250°. "
                   "Potem wyładuj filament przyciskiem poniżej (albo pomiń, jeśli głowica jest pusta).")
        self.gcode(f"REVO_POZYCJA_SERWISOWA\nSET_HEATER_TEMPERATURE HEATER=extruder TARGET={HOT}")
        self.tlbl = _lbl("", "revo_big", 0.5)
        self.box.pack_start(self.tlbl, False, False, 10)
        self.unload = self._btn("WYŁADUJ FILAMENT", lambda: self.gcode("UNLOAD_FILAMENT"))
        self.box.pack_start(self.unload, False, False, 0)
        self._nav()
        self._timer = GLib.timeout_add(1000, self._tick_unload)
        self._tick_unload()

    def _tick_unload(self):
        t, _ = self._temp()
        self.tlbl.set_label(f"{t:.0f}° / {HOT}°")
        self.unload.set_sensitive(t >= 200)
        return True

    def s_grzanie(self):
        self._head("NAGRZEWANIE", f"Dysza nagrzewa się do {HOT}°. Mosiężna i stalowa dysza rozszerza się z blokiem grzewczym, "
                   "więc odkręcamy i dokręcamy ją na gorąco.")
        self.bar = Gtk.ProgressBar()
        self.bar.get_style_context().add_class("revo_progress")
        self.tlbl = _lbl("", "revo_big", 0.5)
        self.box.pack_start(self.tlbl, False, False, 10)
        self.box.pack_start(self.bar, False, False, 0)
        self.gcode(f"SET_HEATER_TEMPERATURE HEATER=extruder TARGET={HOT}")
        self._nav(sensitive=False)
        self._timer = GLib.timeout_add(1000, self._tick_heat)
        self._tick_heat()

    def _tick_heat(self):
        t, _ = self._temp()
        self.tlbl.set_label(f"{t:.0f}° / {HOT}°")
        self.bar.set_fraction(min(1.0, max(0.0, (t - 25) / (HOT - 25))))
        ok = t >= HOT - 5
        self.next_btn.set_sensitive(ok)
        if ok:
            self.next_btn.set_label("DYSZA GORĄCA – DALEJ")
        return True

    def s_odkrec(self):
        self._head("ODKRĘĆ STARĄ DYSZĘ", "1. Załóż rękawice – dysza ma 250°.\n"
                   "2. Przytrzymaj blok grzewczy kluczem 16 mm, żeby się nie obrócił.\n"
                   "3. Odkręć dyszę kluczem 7 mm (w lewo) i odłóż ją na niepalną podkładkę.")
        self._nav("ODKRĘCONA")

    def s_wkrec(self):
        self._head("WKRĘĆ NOWĄ DYSZĘ", f"Nowa dysza: Ø{self.new['d']} {dict(T_OPTS)[self.new['t']]}.\n"
                   "1. Wkręć ją ręcznie do oporu, potem cofnij o ćwierć obrotu.\n"
                   "2. Przytrzymując blok kluczem 16 mm, dokręć dyszę na gorąco – mocno, ale bez siłowania (ok. 1,5 Nm).\n"
                   "3. Sprawdź, czy między dyszą a blokiem nie ma szczeliny.")
        self._nav("WKRĘCONA I DOKRĘCONA", self.finish)

    def finish(self):
        nowa = f"{self.new['d']} {self.new['t']}"
        self.gcode(f"REVO_SET_NOZZLE DIAMETER={self.new['d']} TYPE={self.new['t']}\nSET_HEATER_TEMPERATURE HEATER=extruder TARGET=0")
        sv = self._printer.data.setdefault("save_variables", {}).setdefault("variables", {})
        sv["revo_nozzle"] = nowa
        sv["revo_nozzle_diameter"] = float(self.new["d"])

        def run():
            code, st = agent.call("/status", timeout=2)
            if code == 200 and st.get("hours") is not None:
                GLib.idle_add(self.gcode, serwis.done_gcode("dysza", st["hours"]))
            agent.call("/dysza/wymiana", {"nowa": nowa}, timeout=5)
        threading.Thread(target=run, daemon=True).start()
        self.next()

    def s_koniec(self):
        self._head("GOTOWE", f"Zapisano nową dyszę: Ø{self.new['d']} {dict(T_OPTS)[self.new['t']]}. "
                   "Przegląd „Dysza” liczy się od nowa, a wniosek o wyzerowanie licznika zużycia poszedł do Revotech.\n\n"
                   "Załaduj filament i przy pierwszym wydruku sprawdź pierwszą warstwę – po wymianie dyszy może być potrzebna "
                   "korekta wysokości (Z-offset).")
        b = self._btn("ZAKOŃCZ", lambda: self._screen._menu_go_back(home=True), "revo_t_ok", 70)
        self.box.pack_end(b, False, False, 0)
