# Revo OS – przeglądy okresowe: stan liczników i przycisk ZROBIONE (przytrzymaj).
import threading

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

from ks_includes import revo_agent_client as agent
from ks_includes import revo_home_logic as hl
from ks_includes import revo_serwis_logic as logic
from ks_includes.screen_panel import ScreenPanel
from ks_includes.widgets.revo_home import _lbl


class Panel(ScreenPanel):
    def __init__(self, screen, title, **kwargs):
        super().__init__(screen, title or "Przeglądy")
        self.hours = None
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.box.get_style_context().add_class("revo_home")
        sc = self._gtk.ScrolledWindow()
        sc.add(self.box)
        self.content.add(sc)
        self.box.pack_start(_lbl("Wczytywanie…", "revo_info"), False, False, 0)
        self.load()

    def load(self):
        def run():
            code, st = agent.call("/status", timeout=2)
            GLib.idle_add(self.render, st.get("hours") if code == 200 else None)
        threading.Thread(target=run, daemon=True).start()

    def render(self, hours):
        self.hours = hours
        for c in self.box.get_children():
            self.box.remove(c)
        if hours is None:
            self.box.pack_start(_lbl("Brak licznika godzin (agent Revo nie odpowiada).", "revo_info"), False, False, 20)
            self.box.show_all()
            return False
        vars_ = self._printer.get_stat("save_variables", "variables") or {}
        self.box.pack_start(_lbl(f"Przepracowane: {round(hours)} h", "revo_test_head"), False, False, 4)
        for it in logic.status(hours, vars_, hl.is_belt(self._printer)):
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            card.get_style_context().add_class("revo_tile")
            head = Gtk.Box(spacing=8)
            head.pack_start(_lbl(it["name"].upper(), "revo_test_name"), True, True, 0)
            cls = {"ok": "revo_ok", "wkrótce": "revo_warn", "po terminie": "revo_err"}[it["state"]]
            st = _lbl(it["state"].upper(), "revo_state", 1.0)
            st.get_style_context().add_class(cls)
            head.pack_end(st, False, False, 0)
            card.pack_start(head, False, False, 0)
            bar = Gtk.ProgressBar(fraction=it["fraction"])
            bar.get_style_context().add_class("revo_progress")
            card.pack_start(bar, False, False, 0)
            left = (f"left {round(it['left'])} h" if it["left"] > 0 else f"overdue by {round(-it['left'])} h")
            card.pack_start(_lbl(f"{round(it['since'])} h of {it['every']} h · {left}", "revo_info"), False, False, 0)
            d = _lbl(it["desc"], "revo_test_desc")
            d.set_line_wrap(True)
            card.pack_start(d, False, False, 0)
            b = Gtk.Button(label="ZROBIONE")
            b.get_style_context().add_class("revo_preset")
            b.connect("clicked", lambda w, i=it: self.confirm(i))
            card.pack_start(b, False, False, 4)
            self.box.pack_start(card, False, False, 4)
        self.box.show_all()
        return False

    def confirm(self, it):
        t = _lbl(f"Potwierdź wykonanie: {it['name']}. This maintenance counter starts again from zero.", "revo_test_desc")
        t.set_line_wrap(True)
        buttons = [{"name": "Cancel", "response": Gtk.ResponseType.CANCEL},
                   {"name": "ZROBIONE", "response": Gtk.ResponseType.OK, "style": "dialog-primary"}]

        def resp(dialog, r):
            self._gtk.remove_dialog(dialog)
            if r == Gtk.ResponseType.OK:
                self.done(it["key"])
        self._gtk.Dialog("Przegląd", buttons, t, resp)

    def done(self, key):
        self._screen._ws.api.gcode_script(logic.done_gcode(key, self.hours))
        GLib.timeout_add(800, lambda: self.render(self.hours) and False)
