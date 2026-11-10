# Revo OS – ustawienia blokady ekranu PIN-em (opcjonalne).
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

from ks_includes import revo_lock_logic as logic
from ks_includes.screen_panel import ScreenPanel
from ks_includes.widgets.revo_home import _lbl
from ks_includes.widgets.revo_pin import PinPad


class Panel(ScreenPanel):
    def __init__(self, screen, title, **kwargs):
        super().__init__(screen, title or "Blokada ekranu")
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.box.get_style_context().add_class("revo_home")
        self.content.add(self.box)
        self.render()

    def s(self):
        return logic.settings(self._printer.get_stat("save_variables", "variables") or {})

    def _clear(self):
        for c in self.box.get_children():
            self.box.remove(c)

    def _btn(self, label, cb, cls="revo_preset"):
        b = Gtk.Button(label=label)
        b.get_style_context().add_class(cls)
        b.set_size_request(-1, 64)
        b.connect("clicked", lambda w: cb())
        return b

    def render(self):
        self._clear()
        s = self.s()
        self.box.pack_start(_lbl("BLOKADA EKRANU", "revo_test_name"), False, False, 4)
        t = _lbl("Po chwili bezczynności ekran zablokuje się i odblokujesz go PIN-em. Druk trwa dalej, "
                 "a na ekranie blokady jest przycisk STOP AWARYJNY. PIN serwisowy Revotech też odblokowuje ekran.",
                 "revo_test_desc")
        t.set_line_wrap(True)
        self.box.pack_start(t, False, False, 0)
        st = _lbl("WŁĄCZONA" if s["on"] else "WYŁĄCZONA", "revo_state")
        st.get_style_context().add_class("revo_ok" if s["on"] else "revo_warn")
        self.box.pack_start(st, False, False, 6)
        if s["on"]:
            self.box.pack_start(_lbl("BLOKUJ PO BEZCZYNNOŚCI", "revo_tile_title"), False, False, 0)
            g = Gtk.Grid(column_homogeneous=True, column_spacing=6)
            for i, m in enumerate(logic.TIMES):
                b = Gtk.ToggleButton(label=f"{m} min", active=(m == s["min"]))
                b.get_style_context().add_class("revo_preset")
                b.set_size_request(-1, 56)
                b.connect("toggled", lambda w, m=m: w.get_active() and self.save(True, m, s["pin"]))
                g.attach(b, i, 0, 1, 1)
            self.box.pack_start(g, False, False, 0)
            self.box.pack_start(self._btn("ZABLOKUJ TERAZ", lambda: self._screen.lock_screen.lock(None), "revo_t_ok"), False, False, 6)
            self.box.pack_start(self._btn("ZMIEŃ PIN", lambda: self.ask_old(self.new_pin)), False, False, 0)
            self.box.pack_start(self._btn("WYŁĄCZ BLOKADĘ", lambda: self.ask_old(lambda: self.save(False, s["min"], ""))), False, False, 0)
        else:
            self.box.pack_start(self._btn("WŁĄCZ I USTAW PIN", self.new_pin, "revo_t_ok"), False, False, 6)
        self.box.show_all()

    # --- PIN ---
    def _pad(self, title, cb):
        self._clear()
        pad = PinPad(self._screen, title, cb, self.render)
        pad.set_size_request(-1, -1)
        self.box.pack_start(pad, True, True, 0)
        self.box.show_all()
        return pad

    def ask_old(self, then):
        def check(pin, pad):
            if logic.check(pin, self.s()):
                then()
            else:
                pad.error("Zły PIN")
        self._pad("OBECNY PIN", check)

    def new_pin(self):
        first = {}

        def enter(pin, pad):
            if "p" not in first:
                first["p"] = pin
                pad.set_title("POWTÓRZ PIN")
            elif first["p"] == pin:
                self.save(True, self.s()["min"], logic.hash_pin(pin))
            else:
                first.clear()
                pad.set_title("NOWY PIN (4–8 CYFR)")
                pad.error("PIN-y się różnią")
        self._pad("NOWY PIN (4–8 CYFR)", enter)

    def save(self, on, minutes, pin_hash):
        self._screen._ws.api.gcode_script(logic.save_gcode(on, minutes, pin_hash))
        self._screen.lock_screen.set_autolock_timeout(minutes * 60 if on else 0)
        self._screen.show_popup_message("Zapisano", level=1)
        GLib.timeout_add(700, lambda: self.render() and False)
