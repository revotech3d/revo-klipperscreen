# Revo OS – podgląd z kamery na ekranie: zdjęcie z kamery Mainsaila odświeżane co ~1,5 s.
# Pobiera tylko, gdy widżet jest widoczny – nie obciąża maszyny, kiedy nikt nie patrzy.
import logging
import threading
import urllib.request

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf, GLib, Gtk

SNAPSHOT = "http://127.0.0.1/webcam/?action=snapshot"


def fetch(url=None, timeout=3):
    try:
        with urllib.request.urlopen(url or SNAPSHOT, timeout=timeout) as r:
            data = r.read(3_000_000)
        return data if data[:2] == b"\xff\xd8" else None
    except Exception:
        return None


def available():
    return fetch(timeout=2) is not None


class Cam(Gtk.EventBox):
    def __init__(self, width, height, every_ms=1500, on_click=None):
        super().__init__()
        self.w, self.h = width, height
        self.img = Gtk.Image()
        self.add(self.img)
        self.set_size_request(width, height)
        self._busy = False
        self._timer = GLib.timeout_add(every_ms, self._tick)
        if on_click:
            self.connect("button-release-event", lambda *a: on_click())
        self.connect("destroy", lambda *a: self.stop())
        self._tick()

    def stop(self):
        if self._timer:
            GLib.source_remove(self._timer)
            self._timer = None

    def _tick(self):
        if self._timer is None:
            return False
        if self._busy or not self.get_mapped():
            return True
        self._busy = True
        threading.Thread(target=self._load, daemon=True).start()
        return True

    def _load(self):
        data = fetch()
        GLib.idle_add(self._show, data)

    def _show(self, data):
        self._busy = False
        if not data:
            return False
        try:
            loader = GdkPixbuf.PixbufLoader.new_with_type("jpeg")
            loader.write(data)
            loader.close()
            pb = loader.get_pixbuf()
            s = min(self.w / pb.get_width(), self.h / pb.get_height())
            self.img.set_from_pixbuf(pb.scale_simple(int(pb.get_width() * s), int(pb.get_height() * s),
                                                     GdkPixbuf.InterpType.BILINEAR))
        except Exception as e:
            logging.debug(f"Kamera: {e}")
        return False
