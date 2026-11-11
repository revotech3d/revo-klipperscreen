# Revo OS – tryb serwisowy: PIN, a po wejściu wnioski o reset liczników części
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

from ks_includes import revo_agent_client as agent
from ks_includes.screen_panel import ScreenPanel
from ks_includes.widgets.revo_home import orionize, window

PARTS = [("dysza", "Nozzle"), ("can", "CAN cable"), ("ekstruder", "Extruder"),
         ("pasy", "Belts"), ("lozyska", "Bearing check")]


class Panel(ScreenPanel):
    def __init__(self, screen, title, **kwargs):
        super().__init__(screen, title or "Service mode")
        self.pin = ""
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.box.get_style_context().add_class("revo_home")
        self.content.add(self.box)

    def activate(self):
        code, st = agent.call("/status")
        if code == 200 and st.get("service"):
            self.show_service()
        else:
            self.show_pin()

    def _clear(self):
        for c in self.box.get_children():
            self.box.remove(c)

    def _lbl(self, text, cls, xalign=0.0, wrap=False):
        lb = Gtk.Label(label=text, xalign=xalign)
        lb.get_style_context().add_class(cls)
        lb.set_line_wrap(wrap)
        return lb

    # ---------- PIN ----------
    def show_pin(self):
        self._clear()
        self.pin = ""
        self.box.pack_start(self._lbl("SERVICE MODE", "revo_state", 0.5), False, False, 4)
        self.box.pack_start(self._lbl("Enter the 6-digit PIN from Revotech service.", "revo_info", 0.5), False, False, 0)
        self.dots = self._lbl("○ ○ ○ ○ ○ ○", "revo_big", 0.5)
        self.box.pack_start(self.dots, False, False, 6)
        self.msg = self._lbl("", "revo_err", 0.5, True)
        self.box.pack_start(self.msg, False, False, 0)
        grid = Gtk.Grid(row_homogeneous=True, column_homogeneous=True, row_spacing=8, column_spacing=8)
        keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "⌫", "0", "OK"]
        for i, k in enumerate(keys):
            b = Gtk.Button(label=k)
            b.get_style_context().add_class("revo_preset")
            b.set_size_request(-1, 70)
            b.connect("clicked", self.key, k)
            grid.attach(b, i % 3, i // 3, 1, 1)
        self.box.pack_start(window("PIN PAD", grid, "6 DIGITS"), True, True, 0)
        warn = self._lbl("Entering service mode notifies Revotech and sends machine data.", "revo_info", 0.5, True)
        self.box.pack_end(warn, False, False, 4)
        self.content.show_all()

    def key(self, w, k):
        if k == "⌫":
            self.pin = self.pin[:-1]
        elif k == "OK":
            return self.submit()
        elif len(self.pin) < 6:
            self.pin += k
        self.dots.set_label(" ".join("●" if i < len(self.pin) else "○" for i in range(6)))
        if len(self.pin) == 6:
            self.submit()

    def submit(self):
        code, r = agent.call("/serwis", {"pin": self.pin, "source": "ekran"})
        self.pin = ""
        self.dots.set_label("○ ○ ○ ○ ○ ○")
        if code == 200:
            self.show_service(r.get("minutes"))
        else:
            self.msg.set_label(r.get("message", "Failed."))

    # ---------- po wejściu ----------
    def show_service(self, minutes=None):
        self._clear()
        self.box.pack_start(self._lbl("SERVICE MODE ACTIVE", "revo_state", 0.5), False, False, 4)
        info = "Machine data is sent to Revotech every minute."
        if minutes:
            info += f" The mode ends by itself after {minutes} min."
        self.box.pack_start(self._lbl(info, "revo_info", 0.5, True), False, False, 0)
        self.box.pack_start(self._lbl("PART REPLACED – REQUEST COUNTER RESET", "revo_tile_title"), False, False, 8)
        for key, name in PARTS:
            b = Gtk.Button(label=name)
            b.get_style_context().add_class("revo_preset")
            b.set_size_request(-1, 56)
            b.connect("clicked", self.ask_reset, key, name)
            self.box.pack_start(b, False, False, 0)
        self.msg = self._lbl("The counter resets after Revotech approves.", "revo_info", 0.5, True)
        self.box.pack_start(self.msg, False, False, 8)
        end = Gtk.Button(label="END SERVICE MODE")
        end.get_style_context().add_class("revo_print")
        end.connect("clicked", self.logout)
        self.box.pack_end(end, False, False, 4)
        orionize(self.box, "SERVICE SESSION", "ACTIVE", skip=(end,))
        self.content.show_all()

    def logout(self, *args):
        agent.call("/serwis/koniec", {"source": "ekran"})
        self._screen._menu_go_back(home=True)

    def ask_reset(self, w, key, name):
        lb = self._lbl(f"Send Revotech a request to reset the counter: {name}?", "revo_splash_text", 0.5, True)
        buttons = [{"name": "Send", "response": Gtk.ResponseType.OK, "style": "dialog-primary"},
                   {"name": "Cancel", "response": Gtk.ResponseType.CANCEL, "style": "dialog-secondary"}]
        self._gtk.Dialog("Reset licznika", buttons, lb, self._reset_resp, key, name)

    def _reset_resp(self, dialog, resp, key, name):
        self._gtk.remove_dialog(dialog)
        if resp != Gtk.ResponseType.OK:
            return
        code, r = agent.call("/reset", {"part": key, "note": "zgłoszone z ekranu maszyny", "requested_by": "ekran"})
        self.msg.set_label(f"Request sent: {name}." if code == 200 else r.get("message", "Failed."))
        if code == 403:
            GLib.timeout_add_seconds(2, lambda: self.show_pin() and False)
