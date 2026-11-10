# Revo OS – „O systemie”: wersja Revo OS i składników, identyfikator maszyny, sieć.
import socket
import threading

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

from ks_includes import revo_agent_client as agent
from ks_includes.screen_panel import ScreenPanel
from ks_includes.widgets.revo_home import _lbl


def ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        a = s.getsockname()[0]
        s.close()
        return a
    except OSError:
        return "brak sieci"


class Panel(ScreenPanel):
    def __init__(self, screen, title, **kwargs):
        super().__init__(screen, title or "O systemie")
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.box.get_style_context().add_class("revo_home")
        self.content.add(self.box)
        self.box.pack_start(_lbl("Wczytywanie…", "revo_info"), False, False, 0)
        threading.Thread(target=self._load, daemon=True).start()

    def _load(self):
        code, st = agent.call("/status", timeout=12)
        GLib.idle_add(self.render, st if code == 200 else {})

    def render(self, st):
        for c in self.box.get_children():
            self.box.remove(c)
        s = st.get("system") or {}
        self.box.pack_start(_lbl("REVO OS", "revo_tile_title", 0.5), False, False, 10)
        self.box.pack_start(_lbl(s.get("revo_os", "?"), "revo_big", 0.5), False, False, 0)
        self.box.pack_start(_lbl(f"linia {s.get('linia', '?')}", "revo_info", 0.5), False, False, 0)
        g = Gtk.Grid(column_spacing=16, row_spacing=10)
        rows = [("Maszyna", st.get("machine_id", "?")), ("Makra i konfiguracja", s.get("makra", "?")), ("Ekran", s.get("ekran", "?")),
                ("Agent Revo", s.get("agent", "?")), ("Oprogramowanie sterujące", s.get("firmware", "?")),
                ("Biblioteka", s.get("tresci") or "–"), ("Adres w sieci", ip())]
        for i, (k, v) in enumerate(rows):
            g.attach(_lbl(k.upper(), "revo_tile_title"), 0, i, 1, 1)
            g.attach(_lbl(str(v), "revo_tile_value_small"), 1, i, 1, 1)
        g.set_halign(Gtk.Align.CENTER)
        self.box.pack_start(g, False, False, 20)
        d = st.get("diagnostyka") or {}
        if d.get("kontrole"):
            lab = {"ok": "OK", "uwaga": "UWAGA", "blad": "WYMAGA SERWISU"}.get(d.get("wynik"), "")
            self.box.pack_start(_lbl(f"AUTODIAGNOSTYKA · {lab}", "revo_tile_title", 0.5), False, False, 4)
            bad = [c for c in d["kontrole"] if c.get("stan") != "ok"]
            txt = "\n".join(f"• {c['nazwa']}: {c.get('wartosc') or c['stan']}" for c in bad) or f"Wszystkie {len(d['kontrole'])} kontrole w porządku."
            w = _lbl(txt, "revo_warn" if bad else "revo_info", 0.5)
            w.set_line_wrap(True)
            self.box.pack_start(w, False, False, 8)
        t = _lbl("Aktualizacje przychodzą wyłącznie z serwerów Revotech. Pomoc: biuro@revo3d.pl · +48 512 960 411", "revo_test_desc", 0.5)
        t.set_line_wrap(True)
        self.box.pack_start(t, False, False, 0)
        self.box.show_all()
        return False
