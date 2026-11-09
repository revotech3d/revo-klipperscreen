# Revo OS – Panel Revo na telefonie: kod QR z adresem maszyny.
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from ks_includes.screen_panel import ScreenPanel
from ks_includes.widgets.revo_home import _lbl
from ks_includes.widgets.revo_qr import QR
from panels.revo_wizard import local_ip


class Panel(ScreenPanel):
    def __init__(self, screen, title, **kwargs):
        super().__init__(screen, title or "Panel na telefonie")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        box.get_style_context().add_class("revo_home")
        ip = local_ip()
        if ip:
            url = f"http://{ip}"
            box.pack_start(_lbl("ZESKANUJ TELEFONEM", "revo_test_name", 0.5), False, False, 12)
            box.pack_start(QR(url, 260), False, False, 0)
            box.pack_start(_lbl(url, "revo_tile_value_small", 0.5), False, False, 6)
            t = _lbl("Telefon musi być w tej samej sieci co maszyna. Otworzy się Panel Revo: "
                     "podgląd druku, wysyłanie plików, historia i test maszyny.", "revo_test_desc", 0.5)
            t.set_line_wrap(True)
            box.pack_start(t, False, False, 0)
        else:
            box.pack_start(_lbl("Maszyna nie jest w sieci. Podłącz kabel albo ustaw Wi‑Fi.", "revo_test_desc", 0.5),
                           False, False, 40)
        self.content.add(box)
