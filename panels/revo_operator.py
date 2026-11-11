# Revo OS – operatorzy: wybór osoby i PIN. Kto drukował i kto zgłosił problem trafia do historii.
# Listę operatorów zakłada kierownik w Panelu Revo (przeglądarka); na ekranie tylko logowanie i wylogowanie.
import threading

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

from ks_includes import revo_agent_client as agent
from ks_includes.screen_panel import ScreenPanel
from ks_includes.widgets.revo_home import _lbl
from ks_includes.widgets.revo_pin import PinPad


class Panel(ScreenPanel):
    def __init__(self, screen, title, **kwargs):
        super().__init__(screen, title or "Operator")
        self.st = {}
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.box.get_style_context().add_class("revo_home")
        self.content.add(self.box)
        self.box.pack_start(_lbl("Wczytywanie…", "revo_info"), False, False, 0)
        threading.Thread(target=self._load, daemon=True).start()

    def _load(self):
        code, st = agent.call("/status", timeout=3)
        self.st = st if code == 200 else {}
        GLib.idle_add(self.render)

    def _clear(self):
        for c in self.box.get_children():
            self.box.remove(c)

    def render(self):
        self._clear()
        ops = self.st.get("operatorzy") or []
        cur = self.st.get("operator")
        self.box.pack_start(_lbl("MACHINE OPERATOR", "revo_test_name"), False, False, 6)
        if not [o for o in ops if not o.get("bez_pinu")]:
            code, r = agent.call("/parowanie/kod", timeout=3)
            t = _lbl("Panel Revo in a browser needs a sign-in. The machine has no operators yet – "
                     "open Panel Revo, choose CODE FROM SCREEN and enter this code, then create the manager account. "
                     "Code valid for 10 minutes.", "revo_test_desc")
            t.set_line_wrap(True)
            self.box.pack_start(t, False, False, 0)
            self.box.pack_start(_lbl(" ".join((r.get("kod") or "------")), "revo_big", 0.5), False, False, 16)
            b = Gtk.Button(label="ODŚWIEŻ")
            b.get_style_context().add_class("revo_t_plain")
            b.set_size_request(-1, 56)
            b.connect("clicked", lambda w: threading.Thread(target=self._load, daemon=True).start())
            self.box.pack_start(b, False, False, 0)
        if ops:
            if cur:
                self.box.pack_start(_lbl(f"Signed in: {cur.get('imie', '')}", "revo_state"), False, False, 4)
                b = Gtk.Button(label="SIGN OUT")
                b.get_style_context().add_class("revo_t_plain")
                b.set_size_request(-1, 64)
                b.connect("clicked", lambda w: self._logout())
                self.box.pack_start(b, False, False, 6)
            self.box.pack_start(_lbl("WHO IS WORKING ON THE MACHINE?", "revo_tile_title"), False, False, 6)
            g = Gtk.Grid(column_homogeneous=True, column_spacing=8, row_spacing=8)
            for i, o in enumerate(ops):
                b = Gtk.Button(label=o["imie"] + (" ★" if o.get("rola") == "kierownik" else ""))
                b.get_style_context().add_class("revo_t_ok" if cur and cur.get("login") == o["login"] else "revo_preset")
                b.set_size_request(-1, 72)
                b.connect("clicked", lambda w, o=o: self._pin(o))
                g.attach(b, i % 2, i // 2, 1, 1)
            self.box.pack_start(g, False, False, 0)
        self.box.show_all()
        return False

    def _pin(self, o):
        if o.get("bez_pinu"):   # wspólne konto „Operator” – bez PIN-u
            code, r = agent.call("/operator/zaloguj", {"login": o["login"], "pin": "", "zrodlo": "ekran"}, timeout=4)
            if code == 200:
                self._screen.show_popup_message(f"Zalogowano: {o['imie']}", 1)
                self._screen._menu_go_back()
            else:
                self._screen.show_popup_message(r.get("message", "Nie udało się zalogować"), 2)
            return
        self._clear()

        def enter(pin, pad):
            code, r = agent.call("/operator/zaloguj", {"login": o["login"], "pin": pin, "zrodlo": "ekran"}, timeout=4)
            if code == 409:   # PIN zresetowany – ustaw nowy
                self._clear()

                def nowy(pin2, pad2):
                    c2, r2 = agent.call("/operator/zaloguj", {"login": o["login"], "pin": pin, "nowy": pin2, "zrodlo": "ekran"}, timeout=6)
                    if c2 == 200:
                        self._screen.show_popup_message(f"Nowy PIN ustawiony · {o['imie']}", 1)
                        self._screen._menu_go_back()
                    else:
                        pad2.error("4–8 cyfr, inny niż 0000")

                p2 = PinPad(self._screen, "PIN ZRESETOWANY · USTAW NOWY", nowy, self.render)
                p2.set_size_request(-1, -1)
                self.box.pack_start(p2, True, True, 0)
                self.box.show_all()
                return
            if code == 200:
                self._screen.show_popup_message(f"Zalogowano: {o['imie']}", 1)
                self._screen._menu_go_back()
            else:
                pad.error(r.get("message", "Zły PIN"))

        pad = PinPad(self._screen, f"PIN · {o['imie']}", enter, self.render)
        pad.set_size_request(-1, -1)
        self.box.pack_start(pad, True, True, 0)
        self.box.show_all()

    def _logout(self):
        agent.call("/operator/wyloguj", {}, timeout=3)
        threading.Thread(target=self._load, daemon=True).start()
