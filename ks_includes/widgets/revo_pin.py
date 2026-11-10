# Revo OS – klawiatura PIN (blokada ekranu, ustawianie PIN-u).
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk


class PinPad(Gtk.Box):
    def __init__(self, screen, title, on_enter, on_cancel=None, emergency=False, length=(4, 8), secret=True, suffix=""):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10,
                         width_request=screen.width, height_request=screen.height, valign=Gtk.Align.CENTER)
        self.get_style_context().add_class("revo_home")
        self.get_style_context().add_class("revo_pinpad")
        self.screen, self.on_enter, self.length = screen, on_enter, length
        self.pin = ""
        self.secret, self.suffix = secret, suffix
        self.title = Gtk.Label(label=title)
        self.title.get_style_context().add_class("revo_test_name")
        self.dots = Gtk.Label(label="")
        self.dots.get_style_context().add_class("revo_big")
        self.msg = Gtk.Label(label="")
        self.msg.get_style_context().add_class("revo_err")
        for w in (self.title, self.dots, self.msg):
            self.pack_start(w, False, False, 0)
        g = Gtk.Grid(column_homogeneous=True, row_homogeneous=True, column_spacing=10, row_spacing=10,
                     halign=Gtk.Align.CENTER)
        keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "⌫", "0", "OK"]
        for i, k in enumerate(keys):
            b = Gtk.Button(label=k)
            b.get_style_context().add_class("revo_t_ok" if k == "OK" else "revo_preset")
            b.set_size_request(110, 84)
            b.connect("clicked", self._key, k)
            g.attach(b, i % 3, i // 3, 1, 1)
        self.pack_start(g, False, False, 10)
        row = Gtk.Box(spacing=10, halign=Gtk.Align.CENTER)
        if on_cancel:
            c = Gtk.Button(label="ANULUJ")
            c.get_style_context().add_class("revo_t_plain")
            c.connect("clicked", lambda w: on_cancel())
            row.pack_start(c, False, False, 0)
        if emergency:
            self._estop_armed = False
            self.estop = Gtk.Button(label="STOP AWARYJNY")
            self.estop.get_style_context().add_class("revo_t_stop")
            self.estop.connect("clicked", self._estop)
            row.pack_start(self.estop, False, False, 0)
        self.pack_start(row, False, False, 6)

    def _key(self, w, k):
        self.msg.set_label("")
        if k == "⌫":
            self.pin = self.pin[:-1]
        elif k == "OK":
            if len(self.pin) >= self.length[0]:
                self.on_enter(self.pin, self)
            else:
                self.error(f"PIN ma co najmniej {self.length[0]} cyfry" if self.secret else "Wpisz wartość")
            return
        elif len(self.pin) < self.length[1]:
            self.pin += k
        self.dots.set_label(("●" * len(self.pin)) if self.secret else (self.pin + (self.suffix if self.pin else "")))

    def error(self, text):
        self.pin = ""
        self.dots.set_label("")
        self.msg.set_label(text)

    def set_title(self, text):
        self.title.set_label(text)
        self.error("")

    def _estop(self, w):
        # dwa dotknięcia w ciągu 3 s – żeby nie zatrzymać druku przypadkiem
        if self._estop_armed:
            self.screen._ws.api.emergency_stop()
            self.estop.set_label("ZATRZYMANO")
            return
        self._estop_armed = True
        self.estop.set_label("DOTKNIJ PONOWNIE")

        def disarm():
            self._estop_armed = False
            self.estop.set_label("STOP AWARYJNY")
            return False
        GLib.timeout_add_seconds(3, disarm)
