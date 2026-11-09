# Revo OS – kod QR rysowany cairo (biały na ciemnym tle ekranu → czarne moduły na białej karcie).
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

try:
    import qrcode
except ImportError:          # brak biblioteki – widżet pokaże sam adres
    qrcode = None


def matrix(text):
    if qrcode is None or not text:
        return None
    q = qrcode.QRCode(border=2, error_correction=qrcode.constants.ERROR_CORRECT_M)
    q.add_data(text)
    q.make(fit=True)
    return q.get_matrix()


class QR(Gtk.DrawingArea):
    def __init__(self, text, size=220):
        super().__init__()
        self.m = matrix(text)
        self.set_size_request(size, size)
        self.set_halign(Gtk.Align.CENTER)
        self.connect("draw", self._draw)

    def _draw(self, w, cr):
        if not self.m:
            return
        a = min(w.get_allocated_width(), w.get_allocated_height())
        n = len(self.m)
        s = a / n
        cr.set_source_rgb(1, 1, 1)
        cr.rectangle(0, 0, a, a)
        cr.fill()
        cr.set_source_rgb(0, 0, 0)
        for y, row in enumerate(self.m):
            for x, v in enumerate(row):
                if v:
                    cr.rectangle(x * s, y * s, s + 0.5, s + 0.5)
        cr.fill()
