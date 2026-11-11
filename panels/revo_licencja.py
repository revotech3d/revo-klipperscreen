# Revo OS – licencja maszyny: stan i wpisanie numeru licencji (24 znaki z faktury / maila od Revotech).
# Blokada nigdy nie przerywa trwającego wydruku; ekran, serwis i zdalny serwis działają zawsze.
import threading

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

from ks_includes import revo_agent_client as agent
from ks_includes.screen_panel import ScreenPanel
from ks_includes.widgets.revo_home import _lbl


class Panel(ScreenPanel):
    def __init__(self, screen, title, **kwargs):
        super().__init__(screen, title or "Licencja")
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.box.get_style_context().add_class("revo_home")
        self.content.add(self.box)
        self.box.pack_start(_lbl("MACHINE LICENSE", "revo_test_name"), False, False, 6)
        self.stan = _lbl("Wczytywanie…", "revo_state")
        self.stan.set_line_wrap(True)
        self.box.pack_start(self.stan, False, False, 0)
        opis = _lbl("You get the license number (REVO-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX) from Revotech after purchase. "
                    "Enter it once – it activates the machine. Works without internet too.", "revo_test_desc")
        opis.set_line_wrap(True)
        self.box.pack_start(opis, False, False, 0)
        self.entry = Gtk.Entry()
        self.entry.set_placeholder_text("REVO-…")
        self.entry.connect("button-press-event", self._screen.show_keyboard)
        self.entry.connect("activate", lambda *a: self._send())
        self.box.pack_start(self.entry, False, False, 6)
        self.btn = Gtk.Button(label="ACTIVATE")
        self.btn.get_style_context().add_class("revo_t_plain")
        self.btn.set_size_request(-1, 64)
        self.btn.connect("clicked", lambda *a: self._send())
        self.box.pack_start(self.btn, False, False, 0)
        self.msg = _lbl("", "revo_test_desc")
        self.msg.set_line_wrap(True)
        self.box.pack_start(self.msg, False, False, 0)
        threading.Thread(target=self._load, daemon=True).start()

    def _load(self):
        code, lic = agent.call("/licencja", timeout=3)
        GLib.idle_add(self._show, lic if code == 200 else {"stan": "?", "powod": lic.get("message", "")})

    def _show(self, lic):
        st = lic.get("stan")
        if st == "ok":
            self.stan.set_text("Licencja aktywna. Dziękujemy!")
        elif st == "proba":
            self.stan.set_text(f"Trial – days left: {lic.get('dni')}. {lic.get('powod', '')}")
        elif st == "blokada":
            self.stan.set_text(lic.get("powod", "Maszyna zablokowana."))
        else:
            self.stan.set_text(lic.get("powod") or "Nie udało się sprawdzić licencji.")
        return False

    def _send(self):
        numer = self.entry.get_text().strip()
        if not numer:
            return
        self._screen.remove_keyboard()
        self.btn.set_sensitive(False)
        self.msg.set_text("Sprawdzam numer…")

        def run():
            code, r = agent.call("/licencja", {"numer": numer}, timeout=25)
            GLib.idle_add(self._done, code, r)
        threading.Thread(target=run, daemon=True).start()

    def _done(self, code, r):
        self.btn.set_sensitive(True)
        if code == 200 and r.get("ok"):
            self.msg.set_text("Gotowe – maszyna aktywowana.")
            self.entry.set_text("")
        else:
            self.msg.set_text(r.get("message") or "Nie udało się aktywować.")
        self._load()
        return False
