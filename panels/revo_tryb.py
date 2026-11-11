# Revo OS – tryb ekranu: awaryjne przełączenie na standardowy KlipperScreen i powrót do ekranu Revo.
# Ten sam panel działa w obu wyglądach, więc zawsze da się wrócić. Potwierdzenie drugim dotknięciem.
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

from ks_includes.screen_panel import ScreenPanel

AWARYJNY = "material-dark"


class Panel(ScreenPanel):
    def __init__(self, screen, title, **kwargs):
        super().__init__(screen, title or "Tryb ekranu")
        self.revo = self._config.get_main_config().get("theme", "") == "revo"
        self.uzbrojony = False
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, margin=16)
        self.content.add(box)
        opis = Gtk.Label(wrap=True, xalign=0.0)
        if self.revo:
            opis.set_markup("<b>Tryb awaryjny</b>\n\nPrzełącza ekran na standardowy KlipperScreen – na wypadek problemów "
                            "z ekranem Revo. Wrócisz tutaj: Więcej → Tryb ekranu → Wróć do ekranu Revo.")
            self.txt = "PRZEŁĄCZ NA KLIPPERSCREEN"
        else:
            opis.set_markup("<b>Ekran awaryjny (KlipperScreen)</b>\n\nWróć do ekranu Revo OS.")
            self.txt = "WRÓĆ DO EKRANU REVO"
        box.pack_start(opis, False, False, 0)
        self.btn = Gtk.Button(label=self.txt)
        self.btn.set_size_request(-1, 96)
        if self.revo:
            self.btn.get_style_context().add_class("revo_t_plain")
        self.btn.connect("clicked", self._klik)
        box.pack_start(self.btn, False, False, 0)
        self.info = Gtk.Label(label="Dotknij, a potem dotknij jeszcze raz, aby potwierdzić. Ekran uruchomi się ponownie.",
                              wrap=True, xalign=0.0)
        box.pack_start(self.info, False, False, 0)

    def _klik(self, *a):
        if not self.uzbrojony:
            self.uzbrojony = True
            self.btn.set_label("DOTKNIJ PONOWNIE, ABY POTWIERDZIĆ")
            GLib.timeout_add_seconds(5, self._reset)
            return
        self._config.set("main", "theme", AWARYJNY if self.revo else "revo")
        self._config.save_user_config_options()
        self._screen.restart_ks()

    def _reset(self):
        self.uzbrojony = False
        self.btn.set_label(self.txt)
        return False
