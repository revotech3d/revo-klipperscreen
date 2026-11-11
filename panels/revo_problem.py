# Revo OS – „Mam problem”: zgłoszenie do serwisu Revotech prosto z ekranu.
# Agent dołącza ostatni błąd, log maszyny i zdjęcie z kamery.
import threading

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

from ks_includes import revo_agent_client as agent
from ks_includes.screen_panel import ScreenPanel
from ks_includes.widgets.revo_home import _lbl

KATEGORIE = ["Wydruk się nie udał", "Dziwny dźwięk lub ruch", "Błąd na ekranie", "Grzanie / temperatura", "Inne"]


class Panel(ScreenPanel):
    def __init__(self, screen, title, **kwargs):
        super().__init__(screen, title or "Mam problem")
        self.kat = None
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.box.get_style_context().add_class("revo_home")
        self.content.add(self.box)
        self.form()

    def _clear(self):
        for c in self.box.get_children():
            self.box.remove(c)

    def form(self):
        self._clear()
        self.box.pack_start(_lbl("CO SIĘ DZIEJE?", "revo_test_name"), False, False, 4)
        g = Gtk.Grid(column_homogeneous=True, column_spacing=8, row_spacing=8)
        self.kbtn = {}
        for i, k in enumerate(KATEGORIE):
            b = Gtk.ToggleButton(label=k)
            b.get_style_context().add_class("revo_preset")
            b.set_size_request(-1, 60)
            b.get_child().set_line_wrap(True)
            b.connect("toggled", self.pick, k)
            self.kbtn[k] = b
            g.attach(b, i % 2, i // 2, 2 if i == len(KATEGORIE) - 1 and i % 2 == 0 else 1, 1)
        self.box.pack_start(g, False, False, 0)
        self.box.pack_start(_lbl("OPIS (NIEOBOWIĄZKOWY)", "revo_tile_title"), False, False, 4)
        self.opis = Gtk.Entry(placeholder_text="e.g. knocking when the Y axis moves")
        self.opis.connect("button-press-event", self._screen.show_keyboard)
        self.opis.connect("touch-event", self._screen.show_keyboard)
        self.box.pack_start(self.opis, False, False, 0)
        self.box.pack_start(_lbl("TELEFON DO KONTAKTU (NIEOBOWIĄZKOWY)", "revo_tile_title"), False, False, 4)
        self.tel = Gtk.Entry(placeholder_text="if different from the contract", input_purpose=Gtk.InputPurpose.PHONE)
        self.tel.connect("button-press-event", self._screen.show_keyboard)
        self.tel.connect("touch-event", self._screen.show_keyboard)
        self.box.pack_start(self.tel, False, False, 0)
        t = _lbl("Razem ze zgłoszeniem maszyna wyśle do Revotech ostatni błąd, log pracy i zdjęcie z kamery. "
                 "Odezwiemy się najszybciej, jak to możliwe.", "revo_test_desc")
        t.set_line_wrap(True)
        self.box.pack_start(t, False, False, 6)
        self.send_btn = Gtk.Button(label="WYŚLIJ ZGŁOSZENIE")
        self.send_btn.get_style_context().add_class("revo_t_ok")
        self.send_btn.set_size_request(-1, 70)
        self.send_btn.set_sensitive(False)
        self.send_btn.connect("clicked", lambda w: self.send())
        self.box.pack_end(self.send_btn, False, False, 0)
        self.box.show_all()

    def pick(self, w, k):
        if w.get_active():
            self.kat = k
            for kk, b in self.kbtn.items():
                if kk != k and b.get_active():
                    b.set_active(False)
        elif self.kat == k:
            self.kat = None
        self.send_btn.set_sensitive(self.kat is not None)

    def send(self):
        self._screen.remove_keyboard()
        self.send_btn.set_sensitive(False)
        self.send_btn.set_label("WYSYŁAM…")
        body = {"kategoria": self.kat, "opis": self.opis.get_text(), "telefon": self.tel.get_text()}

        def run():
            code, r = agent.call("/zgloszenie", body, timeout=30)
            GLib.idle_add(self.done, code, r)
        threading.Thread(target=run, daemon=True).start()

    def done(self, code, r):
        self._clear()
        if code == 200 and r.get("number"):
            head, text = "ZGŁOSZENIE WYSŁANE", f"Report number: {r['number']}. Revotech service received the description, log and camera photo."
        elif code == 200:
            head, text = "ZGŁOSZENIE ZAPISANE", "Maszyna nie ma teraz internetu. Zgłoszenie wyjdzie samo, gdy połączenie wróci."
        else:
            head, text = "FAILED", "Revo agent is not responding. Call or write: biuro@revo3d.pl."
        self.box.pack_start(_lbl(head, "revo_state", 0.5), False, False, 30)
        t = _lbl(text, "revo_test_desc", 0.5)
        t.set_line_wrap(True)
        self.box.pack_start(t, False, False, 0)
        b = Gtk.Button(label="OK")
        b.get_style_context().add_class("revo_t_ok")
        b.set_size_request(-1, 70)
        b.connect("clicked", lambda w: self._screen._menu_go_back(home=True))
        self.box.pack_end(b, False, False, 0)
        self.box.show_all()
        return False
