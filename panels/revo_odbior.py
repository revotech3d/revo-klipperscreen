# Revo OS – po wydruku: operator potwierdza zdjęcie części (ile dobrych, ile wadliwych, dlaczego)
# i wybiera raport: podstawowy dla odbiorcy części albo pełny ze zdjęciami (operator, serwis).
# Raport zapisuje agent Revo (/raporty/<id>/odbior); PDF drukuje Revo Panel → History → Reports.
import threading

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

from ks_includes import revo_agent_client as agent
from ks_includes.screen_panel import ScreenPanel
from ks_includes.widgets.revo_home import _lbl

POWODY = ["Warping", "Layer shift", "Detached", "Stringing", "Gaps", "Other"]
RAPORTY = [("odbiorca", "BASIC REPORT", "for the parts' recipient"), ("pelny", "FULL REPORT", "photos, operator, service")]


class Panel(ScreenPanel):
    def __init__(self, screen, title, **kwargs):
        super().__init__(screen, title or "Part removal")
        self.rap = None
        self.dobre, self.wadliwe = 1, 0
        self.powody = set()
        self.rodzaj = "odbiorca"
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.box.get_style_context().add_class("revo_home")
        self.content.add(self.box)
        self.box.pack_start(_lbl("Loading…", "revo_info"), False, False, 0)
        threading.Thread(target=self._load, daemon=True).start()

    def _load(self):
        code, st = agent.call("/status", timeout=2)
        self.rap = st.get("raport") if code == 200 else None
        if self.rap:
            self.dobre = int(self.rap.get("sztuk") or 1)
        GLib.idle_add(self.render)

    def _btn(self, label, cb, cls="revo_preset", h=60):
        b = Gtk.Button(label=label)
        b.get_style_context().add_class(cls)
        b.set_size_request(-1, h)
        b.get_child().set_line_wrap(True)
        b.connect("clicked", lambda w: cb())
        return b

    def _clear(self):
        for c in self.box.get_children():
            self.box.remove(c)

    def _liczniki(self):
        """DOBRE i WADLIWE w jednej siatce: tytuł nad −  liczba  + (wszystko w równych kolumnach)."""
        g = Gtk.Grid(column_homogeneous=True, column_spacing=4, row_spacing=4)
        for k, (tytul, attr) in enumerate((("GOOD PARTS", "dobre"), ("DEFECTIVE", "wadliwe"))):
            x = k * 4
            g.attach(_lbl(tytul, "revo_tile_title", 0.5), x, 0, 3, 1)
            val = _lbl(str(getattr(self, attr)), "revo_big", 0.5)

            def zmien(d, attr=attr, val=val):
                setattr(self, attr, max(0, min(999, getattr(self, attr) + d)))
                val.set_label(str(getattr(self, attr)))
                if attr == "wadliwe":
                    self.powod_box.set_visible(self.wadliwe > 0)
            g.attach(self._btn("−", lambda z=zmien: z(-1), "revo_preset", 58), x, 1, 1, 1)
            g.attach(val, x + 1, 1, 1, 1)
            g.attach(self._btn("+", lambda z=zmien: z(1), "revo_preset", 58), x + 2, 1, 1, 1)
        return g

    def render(self):
        self._clear()
        r = self.rap
        if not r or r.get("drukuje"):
            self.box.pack_start(_lbl("NO PRINT TO CONFIRM", "revo_test_name"), False, False, 8)
            t = _lbl("The report waits here after a print ends. Nothing is waiting now.", "revo_test_desc")
            t.set_line_wrap(True)
            self.box.pack_start(t, False, False, 0)
            self.box.pack_end(self._btn("BACK", self._screen._menu_go_back, "revo_t_plain", 64), False, False, 0)
            self.box.show_all()
            return False
        self.box.pack_start(_lbl(f"REPORT {r['id']}", "revo_test_head"), False, False, 0)
        name = _lbl(r.get("plik", ""), "revo_test_name")
        name.set_ellipsize(2)   # Pango.EllipsizeMode.MIDDLE – długa nazwa pliku nie poszerza ekranu
        self.box.pack_start(name, False, False, 4)
        d = r.get("drzwi")
        info = {"complete": "Print finished.", "cancelled": "Print cancelled.", "error": "Print stopped by an error."}.get(r.get("stan"), "")
        if d and d.get("stol_c") is not None:
            info += f" Door opened at bed {d['stol_c']:.0f}°C."
        t = _lbl(info, "revo_test_desc")
        t.set_line_wrap(True)
        self.box.pack_start(t, False, False, 0)
        self.box.pack_start(self._liczniki(), False, False, 4)
        self.powod_box = Gtk.Grid(column_homogeneous=True, column_spacing=6, row_spacing=6)
        for i, p in enumerate(POWODY):
            tb = Gtk.ToggleButton(label=p)
            tb.get_style_context().add_class("revo_preset")
            tb.set_size_request(-1, 46)
            tb.set_active(p in self.powody)
            tb.connect("toggled", lambda w, p=p: (self.powody.add if w.get_active() else self.powody.discard)(p))
            tb.get_child().set_ellipsize(3)   # Pango.EllipsizeMode.END
            self.powod_box.attach(tb, i % 3, i // 3, 1, 1)
        self.box.pack_start(self.powod_box, False, False, 0)
        g = Gtk.Grid(column_homogeneous=True, column_spacing=8)
        first = None
        for i, (k, nazwa, opis) in enumerate(RAPORTY):
            rb = Gtk.RadioButton.new_with_label_from_widget(first, f"{nazwa}\n{opis}")
            rb.set_mode(False)
            rb.get_style_context().add_class("revo_preset")
            rb.set_size_request(-1, 64)
            rb.get_child().set_line_wrap(True)
            first = first or rb
            rb.set_active(k == self.rodzaj)
            rb.connect("toggled", lambda w, k=k: w.get_active() and setattr(self, "rodzaj", k))
            g.attach(rb, i, 0, 1, 1)
        self.box.pack_start(g, False, False, 0)
        self.err = _lbl("", "revo_err")
        self.box.pack_start(self.err, False, False, 0)
        nav = Gtk.Grid(column_homogeneous=True, column_spacing=8)
        nav.attach(self._btn("LATER", self._screen._menu_go_back, "revo_t_plain", 64), 0, 0, 1, 1)
        nav.attach(self._btn("I CONFIRM PART REMOVAL", self.potwierdz, "revo_t_ok", 64), 1, 0, 2, 1)
        self.box.pack_end(nav, False, False, 0)
        self.box.show_all()
        self.powod_box.set_visible(self.wadliwe > 0)
        return False

    def potwierdz(self):
        body = {"dobre": self.dobre, "wadliwe": self.wadliwe, "rodzaj": self.rodzaj,
                "powod": ", ".join(p for p in POWODY if p in self.powody) if self.wadliwe else ""}

        def run():
            code, res = agent.call(f"/raporty/{self.rap['id']}/odbior", body, timeout=5)
            GLib.idle_add(self.done if code == 200 else self.fail, res)
        threading.Thread(target=run, daemon=True).start()

    def fail(self, res):
        self.err.set_label(res.get("message") or "The report was not saved.")
        return False

    def done(self, res):
        self._clear()
        self.box.pack_start(_lbl("SAVED", "revo_test_name"), False, False, 8)
        t = _lbl(f"Report {self.rap['id']}: {self.dobre} good, {self.wadliwe} defective. "
                 "Print the PDF in Revo Panel → History → Print reports.", "revo_test_desc")
        t.set_line_wrap(True)
        self.box.pack_start(t, False, False, 0)
        self.box.pack_end(self._btn("DONE", lambda: self._screen._menu_go_back(home=True), "revo_t_ok", 70), False, False, 0)
        self.box.show_all()
        return False
