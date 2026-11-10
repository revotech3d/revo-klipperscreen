# Revo OS – zdalny podgląd ekranu: gdy agent Revo ma aktywny podgląd (po zgodzie klienta, plik-flaga),
# ekran co 3 s zapisuje zrzut swojego okna; agent wysyła go do Revotech razem z obrazem z kamery.
import logging
import os

import gi

gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GLib

DIR = os.path.expanduser("~/printer_data/revo")
FLAG = os.path.join(DIR, "podglad.flag")
OUT = os.path.join(DIR, "ekran.jpg")


def active():
    return os.path.exists(FLAG)


def install(screen):
    def tick():
        if not active():
            return True
        try:
            win = screen.get_window()
            pb = Gdk.pixbuf_get_from_window(win, 0, 0, win.get_width(), win.get_height())
            if pb:
                tmp = OUT + ".tmp"
                pb.savev(tmp, "jpeg", ["quality"], ["70"])
                os.replace(tmp, OUT)
        except Exception as e:  # podgląd nigdy nie może wywrócić ekranu
            logging.debug(f"revo_live: {e}")
        return True
    GLib.timeout_add_seconds(3, tick)
