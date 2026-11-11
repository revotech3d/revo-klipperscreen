# Revo OS – Pliki: kafelki z miniaturą, czasem, materiałem i dyszą; druk / usuń
import os

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk, Pango

from ks_includes.screen_panel import ScreenPanel
from ks_includes.widgets.revo_home import _lbl


def fmt_time(s):
    if not s:
        return ""
    s = int(s)
    h, m = s // 3600, s % 3600 // 60
    return f"{h} h {m} min" if h else f"{m} min"


class Panel(ScreenPanel):
    def __init__(self, screen, title, **kwargs):
        super().__init__(screen, title or "Pliki")
        self.scroll = self._gtk.ScrolledWindow()
        self.scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.content.add(self.scroll)
        self._pending = None
        self._tl = None
        self._files.add_callback(self._changed)

    def deactivate(self):
        pass

    def activate(self):
        self._files.refresh_files()
        self.build()

    def _changed(self, *a):
        if self._pending is None:
            self._pending = GLib.timeout_add(400, self._rebuild)

    def _rebuild(self):
        self._pending = None
        if self.content.get_parent():
            self.build()
        return False

    def build(self):
        for c in self.scroll.get_children():
            self.scroll.remove(c)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.get_style_context().add_class("revo_home")
        files = [f for f in self._files.files.values() if self._files.is_gcode(f.get("path", ""))]
        files.sort(key=lambda f: f.get("modified", 0), reverse=True)
        if not files:
            lb = _lbl("Brak plików.\nWyślij plik z Orca Slicer albo przez Panel Revo w przeglądarce.", "revo_info", 0.5)
            lb.set_line_wrap(True)
            box.pack_start(lb, False, False, 40)
        grid = Gtk.Grid(column_homogeneous=True, column_spacing=10, row_spacing=10)
        for i, f in enumerate(files[:60]):
            grid.attach(self.card(f), i % 2, i // 2, 1, 1)
        box.pack_start(grid, False, False, 0)
        self.scroll.add(box)
        self.scroll.show_all()

    def card(self, f):
        path = f["path"]
        btn = Gtk.Button()
        btn.get_style_context().add_class("revo_file")
        v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        img = Gtk.Image()
        img.set_size_request(-1, 150)
        v.pack_start(img, False, False, 0)
        name = Gtk.Label(label=os.path.splitext(os.path.basename(path))[0], xalign=0)
        name.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        name.get_style_context().add_class("revo_tile_value_small")
        v.pack_start(name, False, False, 0)
        bits = [fmt_time(f.get("estimated_time")), f.get("filament_type") or "",
                f"Ø{f['nozzle_diameter']:g}" if f.get("nozzle_diameter") else ""]
        v.pack_start(_lbl(" · ".join(b for b in bits if b) or " ", "revo_info"), False, False, 0)
        btn.add(v)
        btn.connect("clicked", self.confirm, path)
        if f.get("thumbnails"):
            self.load_image_async(path, 200, 150, small=True, callback=lambda p, img=img: p and img.set_from_pixbuf(p))
        else:
            img.set_from_pixbuf(self._gtk.PixbufFromIcon("file", 90, 90))
        return btn

    def confirm(self, w, path):
        f = self._files.get_file_info(path)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.get_style_context().add_class("revo_home")
        title = _lbl(os.path.splitext(os.path.basename(path))[0], "revo_state", 0.5)
        title.set_line_wrap(True)
        box.pack_start(title, False, False, 6)
        img = Gtk.Image()
        box.pack_start(img, True, True, 0)
        rows = [("Czas", fmt_time(f.get("estimated_time"))), ("Materiał", f.get("filament_type") or ""),
                ("Dysza", f"Ø{f['nozzle_diameter']:g}" if f.get("nozzle_diameter") else ""),
                ("Wysokość", f"{f['object_height']:g} mm" if f.get("object_height") else "")]
        g = Gtk.Grid(column_homogeneous=True, column_spacing=8, row_spacing=4)
        for i, (k, val) in enumerate(r for r in rows if r[1]):
            g.attach(_lbl(k.upper(), "revo_tile_title"), i % 2, (i // 2) * 2, 1, 1)
            g.attach(_lbl(val, "revo_tile_value_small"), i % 2, (i // 2) * 2 + 1, 1, 1)
        box.pack_start(g, False, False, 0)
        # seria: ile sztuk wydrukować po kolei (pas wysuwa wydruk między sztukami)
        self._ile = 1
        sr = Gtk.Grid(column_homogeneous=True, column_spacing=8)
        sr.attach(_lbl("SZTUK", "revo_tile_title"), 0, 0, 1, 1)
        minus, plus = Gtk.Button(label="−"), Gtk.Button(label="+")
        self._ile_lbl = _lbl("1", "revo_big", 0.5)
        for b in (minus, plus):
            b.get_style_context().add_class("revo_preset")
            b.set_size_request(-1, 56)
        from ks_includes.widgets.revo_hold import Hold
        self._ile_holds = [Hold(minus, lambda h: self._ile_set(self._ile - 1)),
                           Hold(plus, lambda h: self._ile_set(self._ile + (1 if h < 2 else 5)))]
        sr.attach(minus, 1, 0, 1, 1)
        sr.attach(self._ile_lbl, 2, 0, 1, 1)
        sr.attach(plus, 3, 0, 1, 1)
        from ks_includes import revo_home_logic as lg
        if lg.is_belt(self._printer):   # seria tylko z pasem – sztywny stół wymaga zdjęcia wydruku ręcznie
            box.pack_start(sr, False, False, 0)
        # timelapse: film z druku (tylko gdy maszyna ma kamerę i moonraker-timelapse)
        self._tl = None
        if self._printer.config_section_exists("gcode_macro TIMELAPSE_TAKE_FRAME"):
            row = Gtk.Box(spacing=12)
            row.pack_start(_lbl("FILM Z DRUKU (TIMELAPSE)", "revo_tile_title"), True, True, 0)
            self._tl = Gtk.Switch(valign=Gtk.Align.CENTER)
            row.pack_end(self._tl, False, False, 0)
            box.pack_start(row, False, False, 0)

            def got(resp, *a):
                r = resp.get("result") or {}
                if self._tl is not None:
                    self._tl.set_active(bool(r.get("enabled")))
                return False
            self._screen._ws.send_method("machine.timelapse.get_settings", {}, got)
        self._ile_info = _lbl("", "revo_info", 0.5)
        box.pack_start(self._ile_info, False, False, 0)
        box.pack_start(_lbl("Maszyna sprawdzi zgodność dyszy przed startem.", "revo_info", 0.5), False, False, 0)
        # czy wystarczy filamentu na szpuli (stan z agenta Revo)
        need = f.get("filament_weight_total")
        if need:
            from ks_includes import revo_agent_client as agent
            code, st = agent.call("/status", timeout=1)
            left = (st.get("szpula") or {}).get("zostalo_g") if code == 200 else None
            if left is not None and float(need) * getattr(self, "_ile", 1) > left:
                w = _lbl(f"Filament may run out: needs about {float(need) * getattr(self, '_ile', 1):.0f} g, na szpuli ok. {left:.0f} g.", "revo_err", 0.5)
                w.set_line_wrap(True)
                box.pack_start(w, False, False, 0)
        buttons = [{"name": "Delete", "response": Gtk.ResponseType.REJECT, "style": "dialog-error"},
                   {"name": "Print", "response": Gtk.ResponseType.OK, "style": "dialog-primary"},
                   {"name": "Cancel", "response": Gtk.ResponseType.CANCEL, "style": "dialog-secondary"}]
        self._gtk.Dialog("Drukuj", buttons, box, self._resp, path)
        if f.get("thumbnails"):
            self.load_image_async(path, self._screen.width * 0.8, self._screen.height * 0.4,
                                  callback=lambda p: p and img.set_from_pixbuf(p))

    def _ile_set(self, n):
        self._ile = max(1, min(99, n))
        self._ile_lbl.set_label(str(self._ile))
        self._ile_info.set_label("" if self._ile == 1 else f"Seria {self._ile} pcs – the belt ejects each part")

    def _resp(self, dialog, resp, path):
        self._gtk.remove_dialog(dialog)
        if resp == Gtk.ResponseType.OK and self._tl is not None:
            self._screen._ws.send_method("machine.timelapse.post_settings", {"enabled": self._tl.get_active()})
        if resp == Gtk.ResponseType.OK and getattr(self, "_ile", 1) > 1:
            # kolejka Moonrakera: N razy ten sam plik, przejście między sztukami = REVO_SERIA_PRZERWA
            self._screen._ws.send_method("server.job_queue.post_job", {"filenames": [path] * self._ile, "reset": True},
                                         lambda *a: self._screen._ws.send_method("server.job_queue.start") and False)
        elif resp == Gtk.ResponseType.OK:
            self._screen._ws.api.print_start(path)
        elif resp == Gtk.ResponseType.REJECT:
            self._screen._confirm_send_action(None, f"Delete file?\n\n{path}", "server.files.delete_file", {"path": f"gcodes/{path}"})
