# Revo OS – wyłączanie i ponowne uruchomienie maszyny w wyglądzie Revo (zamiast panelu KlipperScreena).
# Potwierdzenie drugim dotknięciem tego samego przycisku – bez okien dialogowych.
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

from ks_includes.screen_panel import ScreenPanel
from ks_includes.widgets.revo_home import _lbl, orionize


class Panel(ScreenPanel):
    AKCJE = {
        "wylacz": ("WYŁĄCZ MASZYNĘ", "machine.shutdown", "Maszyna się wyłącza. Odczekaj 30 s przed odcięciem zasilania."),
        "restart": ("URUCHOM PONOWNIE", "machine.reboot", "Maszyna uruchamia się ponownie."),
        # tylko w trybie serwisowym: przy następnym włączeniu pokaże się kreator pierwszego uruchomienia
        "kreator": ("RESET DO PIERWSZEGO STARTU", "machine.shutdown",
                    "Maszyna się wyłącza. Po włączeniu pokaże się kreator pierwszego uruchomienia."),
    }

    def __init__(self, screen, title, **kwargs):
        super().__init__(screen, "Power")
        self.uzbrojony = None
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.get_style_context().add_class("revo_home")
        self.content.add(box)
        box.pack_start(_lbl("ZASILANIE", "revo_test_name"), False, False, 6)
        self.info = _lbl("Dotknij przycisk, a potem dotknij go jeszcze raz, aby potwierdzić.", "revo_test_desc")
        self.info.set_line_wrap(True)
        box.pack_start(self.info, False, False, 0)
        self.btn = {}
        for k, (txt, _m, _ok) in self.AKCJE.items():
            b = Gtk.Button(label=txt)
            b.get_style_context().add_class("revo_t_plain")
            b.set_size_request(-1, 96)
            b.connect("clicked", lambda *a, k=k: self._klik(k))
            box.pack_start(b, False, False, 0)
            self.btn[k] = b
            if k == "kreator":
                b.set_no_show_all(True)
                b.set_visible(bool(getattr(self._printer, "revo_service", False)))
        orionize(box)

    def activate(self):
        self._reset()
        self.btn["kreator"].set_visible(bool(getattr(self._printer, "revo_service", False)))

    def _klik(self, k):
        if self._printer.state in ("printing", "paused"):
            self.info.set_text("Trwa wydruk – najpierw go zakończ albo przerwij.")
            return
        txt, method, ok = self.AKCJE[k]
        if self.uzbrojony != k:
            self._reset()
            self.uzbrojony = k
            self.btn[k].set_label(f"DOTKNIJ PONOWNIE: {txt}")
            self.btn[k].get_style_context().add_class("revo_t_warn")
            GLib.timeout_add_seconds(5, self._reset)
            return
        self.info.set_text(ok)
        if k == "kreator":
            self._screen._ws.api.gcode_script("SAVE_VARIABLE VARIABLE=revo_first_run_done VALUE=0")
            GLib.timeout_add_seconds(2, lambda: self._screen._ws.send_method(method) and False)
            return
        self._screen._ws.send_method(method)

    def _reset(self):
        self.uzbrojony = None
        for k, b in self.btn.items():
            b.set_label(self.AKCJE[k][0])
            b.get_style_context().remove_class("revo_t_warn")
        return False
