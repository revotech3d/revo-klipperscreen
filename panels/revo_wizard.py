# Revo OS – kreator pierwszego uruchomienia: język, sieć, zgody, dysza, test maszyny.
# Pokazuje się sam, dopóki w zmiennych maszyny nie ma revo_first_run_done (ekran główny Revo).
import socket
import threading

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

from ks_includes import revo_agent_client as agent
from ks_includes.screen_panel import ScreenPanel
from ks_includes.widgets.revo_home import RevoActions, _lbl
from ks_includes.widgets.revo_qr import QR

STEPS = ["witaj", "siec", "zgody", "dysza", "test"]   # interfejs tylko po angielsku – bez wyboru języka
STATE = {"step": 0}          # przetrwa przeładowanie paneli po zmianie języka


def local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return ""


class Panel(ScreenPanel, RevoActions):
    def __init__(self, screen, title, **kwargs):
        super().__init__(screen, title or "Pierwsze uruchomienie")
        self.p, self.screen, self.printer = self, self._screen, self._printer
        self.sw = {}
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.box.get_style_context().add_class("revo_home")
        self.content.add(self.box)
        self.render()

    # ---------- budowa kroku ----------
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
        n = STATE["step"]
        top = Gtk.Box(spacing=6)
        top.pack_start(_lbl(f"KROK {n + 1} / {len(STEPS)}", "revo_test_head"), True, True, 0)
        self.box.pack_start(top, False, False, 0)
        bar = Gtk.ProgressBar()
        bar.get_style_context().add_class("revo_progress")
        bar.set_fraction((n + 1) / len(STEPS))
        self.box.pack_start(bar, False, False, 0)
        self.box.pack_start(_lbl(title, "revo_test_name"), False, False, 10)
        t = _lbl(text, "revo_test_desc")
        t.set_line_wrap(True)
        self.box.pack_start(t, False, False, 0)

    def _nav(self, next_label="DALEJ", on_next=None, back=True):
        g = Gtk.Grid(column_homogeneous=True, column_spacing=8)
        col = 0
        if back and STATE["step"] > 0:
            g.attach(self._btn("WSTECZ", self.back, "revo_t_plain"), 0, 0, 1, 1)
            col = 1
        g.attach(self._btn(next_label, on_next or self.next, "revo_t_ok"), col, 0, 2 - col if col == 0 else 1, 1)
        self.box.pack_end(g, False, False, 0)

    def render(self):
        self._clear()
        getattr(self, "step_" + STEPS[STATE["step"]])()
        self.box.show_all()

    def next(self):
        STATE["step"] = min(STATE["step"] + 1, len(STEPS) - 1)
        self.render()

    def back(self):
        STATE["step"] = max(STATE["step"] - 1, 0)
        self.render()

    # ---------- kroki ----------
    def step_witaj(self):
        self._head("WELCOME TO REVO OS",
                   "A few short steps prepare the machine: network, consents, installed nozzle "
                   "and finally the machine test. Setup takes a few minutes, the test about 15–25 min.")
        self._nav("LET'S START", back=False)

    def step_jezyk(self):
        self._head("JĘZYK · LANGUAGE", "Wybierz język ekranu i Panelu Revo. Choose the screen language.")
        g = Gtk.Grid(column_homogeneous=True, column_spacing=8)
        for i, (code, name) in enumerate((("pl", "POLSKI"), ("en", "ENGLISH"))):
            g.attach(self._btn(name, lambda c=code: self.set_lang(c), "revo_preset", 80), i, 0, 1, 1)
        self.box.pack_start(g, False, False, 12)
        self._nav()

    def set_lang(self, code):
        STATE["step"] = STEPS.index("jezyk") + 1
        cur = self._config.get_main_config().get("language", "pl")
        if cur == code:
            return self.render()
        self._screen.change_language(None, code)   # przeładuje panele – kreator wróci na kolejny krok

    def step_siec(self):
        ip = local_ip()
        self._head("SIEĆ",
                   (f"Maszyna jest w sieci: {ip}. Zeskanuj kod telefonem, żeby otworzyć Panel Revo (http://{ip})"
                    if ip else "Maszyna nie jest połączona z siecią. Podłącz kabel albo ustaw Wi‑Fi.")
                   + " Sieć jest potrzebna do aktualizacji i kontaktu z serwisem Revotech.")
        if ip:
            self.box.pack_start(QR(f"http://{ip}", 180), False, False, 8)
        self.box.pack_start(self._btn("USTAW WI‑FI", lambda: self._screen.show_panel("revo_siec", "Sieć")), False, False, 12)
        self._nav()

    def step_zgody(self):
        self._head("ZGODY",
                   "Maszyna może wysyłać do Revotech informacje, które pomagają szybciej reagować na usterki. "
                   "Możesz to zmienić później w Menu.")
        for key, title, desc, default in (
                ("alerts", "Alerty o błędach", "Gdy maszyna zgłosi błąd lub 3 nieudane wydruki z rzędu, serwis dostaje powiadomienie.", True),
                ("stats", "Statystyki (dobrowolnie)", "Przebieg oraz liczba udanych i nieudanych wydruków tej maszyny – pomagają nam ulepszać maszyny.", False)):
            row = Gtk.Box(spacing=12)
            col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            col.add(_lbl(title, "revo_tile_value_small"))
            d = _lbl(desc, "revo_info")
            d.set_line_wrap(True)
            col.add(d)
            sw = self.sw.get(key) or Gtk.Switch(active=default, valign=Gtk.Align.CENTER)
            if sw.get_parent():
                sw.get_parent().remove(sw)
            self.sw[key] = sw
            row.pack_start(col, True, True, 0)
            row.pack_end(sw, False, False, 0)
            self.box.pack_start(row, False, False, 6)
        self._nav(on_next=self.save_consent)

    def save_consent(self):
        body = {k: sw.get_active() for k, sw in self.sw.items()}
        threading.Thread(target=agent.call, args=("/zgody", body), daemon=True).start()
        self.next()

    def step_dysza(self):
        vars_ = self._printer.get_stat("save_variables", "variables") or {}
        cur = vars_.get("revo_nozzle") or "nie ustawiono"
        self._head("ZAMONTOWANA DYSZA",
                   f"Teraz: {cur}. Maszyna porówna dyszę z plikiem przy każdym starcie druku i zatrzyma druk, "
                   "gdy plik był przygotowany pod inną dyszę.")
        self.box.pack_start(self._btn("WYBIERZ DYSZĘ", self.nozzle_dialog), False, False, 12)
        self._nav()

    def step_test(self):
        self._head("TEST MASZYNY",
                   "Na koniec maszyna sprawdzi po kolei elektronikę, silniki, osie, grzanie, wentylatory i oświetlenie. "
                   "Przy każdym kroku potwierdzasz, czy działa. Zdejmij wydruki ze stołu i załaduj filament. "
                   "Test możesz też zrobić później: Menu → Więcej → Test maszyny.")
        g = Gtk.Grid(column_homogeneous=True, column_spacing=8)
        g.attach(self._btn("PÓŹNIEJ", lambda: self.finish(False), "revo_t_plain"), 0, 0, 1, 1)
        g.attach(self._btn("ROZPOCZNIJ TEST", lambda: self.finish(True), "revo_t_ok"), 1, 0, 1, 1)
        self.box.pack_end(g, False, False, 0)

    def finish(self, run_test):
        STATE["step"] = 0
        script = "SAVE_VARIABLE VARIABLE=revo_first_run_done VALUE=1"
        if run_test:
            script += "\nREVO_SELFTEST"
        self._screen._ws.api.gcode_script(script)
        GLib.timeout_add(600, lambda: (self._screen._menu_go_back(home=True), False)[1])
