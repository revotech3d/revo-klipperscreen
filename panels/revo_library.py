# Revo OS – Biblioteka Revo (poradniki, materiały, profile, modele) z repozytorium revo-content
import json
import os

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from ks_includes.revo_agent_client import strip_markdown
from ks_includes.screen_panel import ScreenPanel
from ks_includes.widgets.revo_home import orionize, window

CONTENT_DIRS = [os.path.expanduser("~/revo-content"), os.path.expanduser("~/printer_data/revo-content")]


def content_dir():
    for d in CONTENT_DIRS:
        if os.path.isfile(os.path.join(d, "biblioteka.json")):
            return d
    return None


class Panel(ScreenPanel):
    def __init__(self, screen, title, **kwargs):
        super().__init__(screen, title or "Revo Library")
        self.root = content_dir()
        self.scroll = self._gtk.ScrolledWindow()
        self.scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.content.add(self.scroll)
        self.show_list()

    def _set(self, widget):
        for c in self.scroll.get_children():
            self.scroll.remove(c)
        self.scroll.add(widget)
        self.scroll.show_all()

    def show_list(self, *args):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.get_style_context().add_class("revo_home")
        if not self.root:
            lb = Gtk.Label(label="Brak Biblioteki Revo na tej maszynie.\nZainstaluje się z aktualizacją Revo OS.")
            lb.get_style_context().add_class("revo_info")
            box.add(lb)
            return self._set(box)
        with open(os.path.join(self.root, "biblioteka.json"), encoding="utf-8") as f:
            lib = json.load(f)
        for kat in lib["kategorie"]:
            items = [p for p in lib["pozycje"] if p["kategoria"] == kat["id"]]
            if not items:
                continue
            h = Gtk.Label(label=kat["nazwa"].upper(), xalign=0)
            h.get_style_context().add_class("revo_tile_title")
            box.pack_start(h, False, False, 4)
            for p in items:
                b = Gtk.Button()
                b.get_style_context().add_class("revo_preset")
                inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
                t = Gtk.Label(label=p["tytul"], xalign=0)
                t.get_style_context().add_class("revo_tile_value_small")
                d = Gtk.Label(label=p.get("opis", ""), xalign=0)
                d.set_line_wrap(True)
                d.get_style_context().add_class("revo_info")
                inner.add(t)
                inner.add(d)
                b.add(inner)
                b.connect("clicked", self.show_item, p)
                box.pack_start(b, False, False, 0)
        orionize(box)
        self._set(box)

    def show_item(self, w, p):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.get_style_context().add_class("revo_home")
        back = Gtk.Button(label="‹ Library")
        back.get_style_context().add_class("revo_preset")
        back.connect("clicked", self.show_list)
        box.pack_start(back, False, False, 0)
        try:
            with open(os.path.join(self.root, p["plik"]), encoding="utf-8") as f:
                text = strip_markdown(f.read())
        except OSError:
            text = "Could not open the file."
        lb = Gtk.Label(label=text, xalign=0)
        lb.set_line_wrap(True)
        lb.set_selectable(False)
        lb.get_style_context().add_class("revo_doc")
        for m in (lb.set_margin_start, lb.set_margin_end, lb.set_margin_top, lb.set_margin_bottom):
            m(8)
        box.pack_start(window(p["tytul"].upper(), lb, "REVO LIBRARY"), False, False, 0)
        self._set(box)
