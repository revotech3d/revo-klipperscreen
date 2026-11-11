# Revo OS – Narzędzia serwisowe: wszystkie ważne komendy jako przyciski (bez wpisywania).
# Katalog wspólny z Panelem Revo (revo-config/web/komendy.json); widać tylko komendy, które ta maszyna zna.
import time

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

from ks_includes import revo_tools_logic as T
from ks_includes.screen_panel import ScreenPanel


def _lbl(text, cls, xalign=0.0, wrap=True):
    lb = Gtk.Label(label=text, xalign=xalign)
    lb.get_style_context().add_class(cls)
    lb.set_line_wrap(wrap)
    return lb


class Panel(ScreenPanel):
    def __init__(self, screen, title, **kwargs):
        super().__init__(screen, title or "Narzędzia serwisowe")
        self.srcs = T.sources(self._printer.get_config_section_list())
        avail = list(self._printer.available_commands.keys()) if self._printer.available_commands else None
        cats = T.visible(T.load(), avail, self.srcs)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.get_style_context().add_class("revo_home")
        box.pack_start(_lbl("Dotknij komendy. Zmiany w maszynie wymagają potwierdzenia, odczyty pokazują wynik od razu.",
                            "revo_info"), False, False, 0)
        for k in cats:
            box.pack_start(_lbl(k["nazwa"].upper(), "revo_tile_title"), False, False, 6)
            g = Gtk.Grid(column_homogeneous=True, column_spacing=8, row_spacing=8)
            for i, c in enumerate(k["komendy"]):
                b = Gtk.Button(label=c["n"])
                b.get_style_context().add_class("revo_preset")
                b.get_child().set_line_wrap(True)
                b.set_size_request(-1, 56)
                b.connect("clicked", self.pick, c)
                g.attach(b, i % 2, i // 2, 1, 1)
            box.pack_start(g, False, False, 0)
        sc = self._gtk.ScrolledWindow()
        sc.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sc.add(box)
        self.content.add(sc)

    # 1) wybór parametru (silnik, sterownik, temperatura)
    def pick(self, w, c):
        params = c.get("p") or {}
        if not params:
            return self.confirm(c, c["g"])
        name, src = next(iter(params.items()))
        opts = self.srcs.get(src, []) if isinstance(src, str) else src
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.get_style_context().add_class("revo_home")
        box.pack_start(_lbl(c["n"], "revo_state", 0.5), False, False, 4)
        box.pack_start(_lbl(c["opis"], "revo_info", 0.5), False, False, 0)
        g = Gtk.Grid(column_homogeneous=True, column_spacing=8, row_spacing=8)
        dlg = {}
        for i, o in enumerate(opts):
            b = Gtk.Button(label=f"{o}°C" if isinstance(o, int) else str(o).replace("stepper_", "").upper())
            b.get_style_context().add_class("revo_preset")
            b.set_size_request(-1, 56)
            b.connect("clicked", lambda bw, o=o: (self._gtk.remove_dialog(dlg["d"]), self.confirm(c, T.fill(c["g"], name, o))))
            g.attach(b, i % 2, i // 2, 1, 1)
        box.pack_start(g, False, False, 0)
        dlg["d"] = self._gtk.Dialog(c["n"], [{"name": "Cancel", "response": Gtk.ResponseType.CANCEL, "style": "dialog-secondary"}],
                                    box, lambda d, r: self._gtk.remove_dialog(d))

    # 2) potwierdzenie (pomijane dla odczytów)
    def confirm(self, c, gcode):
        if not T.needs_confirm(gcode):
            return self.run(gcode)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.get_style_context().add_class("revo_home")
        box.pack_start(_lbl(c["n"], "revo_state", 0.5), False, False, 4)
        box.pack_start(_lbl(c["opis"], "revo_info", 0.5), False, False, 0)
        box.pack_start(_lbl(gcode.replace("\n", "  ·  "), "revo_tile_value_small", 0.5), False, False, 6)
        buttons = [{"name": "Run", "response": Gtk.ResponseType.OK, "style": "dialog-primary"},
                   {"name": "Cancel", "response": Gtk.ResponseType.CANCEL, "style": "dialog-secondary"}]
        self._gtk.Dialog(c["n"], buttons, box, self._resp, gcode)

    def _resp(self, dialog, resp, gcode):
        self._gtk.remove_dialog(dialog)
        if resp == Gtk.ResponseType.OK:
            self.run(gcode)

    # 3) wykonanie i wynik z konsoli
    def run(self, gcode):
        t0 = time.time() - 1
        self._screen._ws.api.gcode_script(gcode)
        GLib.timeout_add(1500, self._fetch, gcode, t0)

    def _fetch(self, gcode, t0):
        self._screen._ws.send_method("server.gcode_store", {"count": 40}, self._show, gcode, t0)
        return False

    def _show(self, result, method, params, gcode, t0):
        try:
            lines = [x["message"] for x in result["result"]["gcode_store"] if x.get("time", 0) >= t0 and x.get("type") == "response"]
        except (KeyError, TypeError):
            lines = []
        text = "\n".join(l.replace("// ", "") for l in lines[-14:]) or "Sent. The result appears in the console when the machine finishes."
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.get_style_context().add_class("revo_home")
        box.pack_start(_lbl(gcode.split("\n")[-1], "revo_tile_title", 0.5), False, False, 0)
        out = _lbl(text, "revo_info", 0.0)
        out.set_selectable(False)
        box.pack_start(out, False, False, 0)
        self._gtk.Dialog("Wynik", [{"name": "OK", "response": Gtk.ResponseType.OK, "style": "dialog-primary"}],
                         box, lambda d, r: self._gtk.remove_dialog(d))
        return False
