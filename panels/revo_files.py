# Revo OS – Pliki: kafelki z miniaturą, czasem, materiałem i dyszą; druk / usuń
import os

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk, Pango

from ks_includes.screen_panel import ScreenPanel
from ks_includes.widgets.revo_home import _lbl, window


def fmt_time(s):
    if not s:
        return ""
    s = int(s)
    h, m = s // 3600, s % 3600 // 60
    return f"{h} h {m} min" if h else f"{m} min"


class Panel(ScreenPanel):
    def __init__(self, screen, title, **kwargs):
        super().__init__(screen, title or "Files")
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
            lb = _lbl("Brak plików.\nWyślij plik z [r]evo Slicer albo przez Revo Panel w przeglądarce.", "revo_info", 0.5)
            lb.set_line_wrap(True)
            box.pack_start(lb, False, False, 40)
        grid = Gtk.Grid(column_homogeneous=True, column_spacing=10, row_spacing=10)
        for i, f in enumerate(files[:60]):
            grid.attach(self.card(f), i % 2, i // 2, 1, 1)
        for m in (grid.set_margin_start, grid.set_margin_end, grid.set_margin_top, grid.set_margin_bottom):
            m(6)
        box.pack_start(window("PRINT FILES", grid, f"{len(files)} FILES") if files else grid, False, False, 0)
        self.scroll.add(box)
        self.scroll.show_all()

    def card(self, f):
        path = f["path"]
        btn = Gtk.Button()
        btn.get_style_context().add_class("revo_file")
        v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        # two cards must fit the screen width (minus the status bar, margins and the window frame)
        cw = max(120, (int(self._gtk.content_width) - 56) // 2)
        img = Gtk.Image()
        img.set_size_request(-1, min(150, cw * 3 // 4))
        v.pack_start(img, False, False, 0)
        name = Gtk.Label(label=os.path.splitext(os.path.basename(path))[0], xalign=0)
        name.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        name.get_style_context().add_class("revo_tile_value_small")
        v.pack_start(name, False, False, 0)
        bits = [fmt_time(f.get("estimated_time")), f.get("filament_type") or "",
                f"Ø{f['nozzle_diameter']:g}" if f.get("nozzle_diameter") else ""]
        info = _lbl(" · ".join(b for b in bits if b) or " ", "revo_info")
        info.set_ellipsize(Pango.EllipsizeMode.END)
        v.pack_start(info, False, False, 0)
        # Belt: tryb i ilość z pliku ([r]evo Slicer), czytane w tle
        badge = _lbl("", "revo_belt_mode")
        badge.set_halign(Gtk.Align.START)
        badge.set_line_wrap(True)       # "SEQUENTIAL · 10 PIECES" wraps instead of widening the card
        badge.set_max_width_chars(24)
        badge.set_no_show_all(True)
        v.pack_start(badge, False, False, 0)
        self._belt_badge(path, badge)
        btn.add(v)
        btn.connect("clicked", self.confirm, path)
        if f.get("thumbnails"):
            self.load_image_async(path, cw - 20, min(150, cw * 3 // 4), small=True, callback=lambda p, img=img: p and img.set_from_pixbuf(p))
        else:
            img.set_from_pixbuf(self._gtk.PixbufFromIcon("file", 90, 90))
        return btn

    def _belt_path(self, path):
        root = self._files.gcodes_path
        return os.path.join(root, path) if root else None

    def _belt_badge(self, path, badge):
        from ks_includes import revo_belt_logic as bl
        full = self._belt_path(path)
        if not full:
            return

        def done(info):
            text = bl.file_badge(info)
            if text and badge.get_parent():
                badge.set_label(text)
                badge.set_no_show_all(False)
                badge.show()
            return False
        self._gtk._executor.submit(lambda: GLib.idle_add(done, bl.read_info(full)))

    def confirm(self, w, path):
        from ks_includes import revo_belt_logic as bl
        full = self._belt_path(path)
        self._belt = bl.read_info(full) if full else None
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
        b = self._belt
        if b and b["loop"]:
            box.pack_start(self._belt_stepper(b, f.get("estimated_time")), False, False, 0)
        elif b and b["mode"] == "long":
            pass   # długość wynika z modelu
        elif lg.is_belt(self._printer):   # seria tylko z pasem – sztywny stół wymaga zdjęcia wydruku ręcznie
            box.pack_start(sr, False, False, 0)
            if b and b["eject"] not in ("", "off"):
                box.pack_start(_lbl("Eject: after each part the bed cools and the belt drops it", "revo_info", 0.5), False, False, 0)
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
        self._gtk.Dialog("Print", buttons, box, self._resp, path)
        if f.get("thumbnails"):
            self.load_image_async(path, self._screen.width * 0.8, self._screen.height * 0.4,
                                  callback=lambda p: p and img.set_from_pixbuf(p))

    def _belt_stepper(self, b, est):
        """Sequential, Plates, Endless: quantity (or length) for this print, − / + / ∞, sent as FLAT_BELT_NEXT."""
        from ks_includes import revo_belt_logic as bl
        from ks_includes.widgets.revo_hold import Hold
        self._bt = b["target"]
        fb = dict(bl.info_fb(b), done=0, min_target=2 if b["mode"] == "endless" else 1)
        v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        top = Gtk.Box(spacing=10)
        mode = _lbl(bl.MODES[b["mode"]][0], "revo_belt_mode")
        top.pack_start(mode, False, False, 0)
        title = "LENGTH" if b["mode"] == "endless" else "PLATES" if b["mode"] == "plates" else "QUANTITY"
        top.pack_start(_lbl(title, "revo_tile_title"), True, True, 0)
        v.pack_start(top, False, False, 0)
        g = Gtk.Grid(column_homogeneous=True, column_spacing=8)
        minus, plus, inf = Gtk.Button(label="−"), Gtk.Button(label="+"), Gtk.Button(label="∞")
        self._bt_lbl = _lbl("", "revo_big", 0.5)
        for btn in (minus, plus, inf):
            btn.get_style_context().add_class("revo_preset")
            btn.set_size_request(-1, 56)
        self._bt_holds = [Hold(minus, lambda h: self._bt_set(bl.step_target(fb, self._bt, -(1 if h < 2 else 5)), b, fb, est)),
                          Hold(plus, lambda h: self._bt_set(max(fb["min_target"], self._bt + (1 if h < 2 else 5)), b, fb, est))]
        inf.connect("clicked", lambda w: self._bt_set(0, b, fb, est))
        g.attach(minus, 0, 0, 1, 1)
        g.attach(self._bt_lbl, 1, 0, 2, 1)
        g.attach(plus, 3, 0, 1, 1)
        g.attach(inf, 4, 0, 1, 1)
        v.pack_start(g, False, False, 0)
        self._bt_info = _lbl("", "revo_info", 0.5)
        self._bt_info.set_line_wrap(True)
        v.pack_start(self._bt_info, False, False, 0)
        self._bt_set(self._bt, b, fb, est)
        return v

    def _bt_set(self, t, b, fb, est):
        from ks_includes import revo_belt_logic as bl
        self._bt = max(0, t)
        self._bt_lbl.set_label(bl.target_text(fb, self._bt))
        per = bl.per_unit(b, est)
        whole = bl.series_time(b, est, self._bt)
        unit = "segment" if b["mode"] == "endless" else "plate" if b["mode"] == "plates" else "piece"
        bits = [f"{fmt_time(per)} per {unit}" if per else "",
                f"all: {fmt_time(whole)}" if whole else "until stopped" if self._bt == 0 else "",
                "can be changed while printing"]
        self._bt_info.set_label(" · ".join(x for x in bits if x))

    def _ile_set(self, n):
        self._ile = max(1, min(99, n))
        self._ile_lbl.set_label(str(self._ile))
        self._ile_info.set_label("" if self._ile == 1 else f"Seria {self._ile} pcs – the belt ejects each part")

    def _resp(self, dialog, resp, path):
        self._gtk.remove_dialog(dialog)
        if resp == Gtk.ResponseType.OK and self._tl is not None:
            self._screen._ws.send_method("machine.timelapse.post_settings", {"enabled": self._tl.get_active()})
        if resp == Gtk.ResponseType.OK and self._belt and self._belt["loop"]:
            # ilość z okna startu: Revo OS bierze ją zamiast celu z pliku (FLAT_BELT_INFO)
            self._screen._ws.api.gcode_script(f"FLAT_BELT_NEXT TARGET={self._bt}",
                                              lambda *a: self._screen._ws.api.print_start(path) and False)
        elif resp == Gtk.ResponseType.OK and getattr(self, "_ile", 1) > 1:
            # kolejka Moonrakera: N razy ten sam plik, przejście między sztukami = REVO_SERIA_PRZERWA
            self._screen._ws.send_method("server.job_queue.post_job", {"filenames": [path] * self._ile, "reset": True},
                                         lambda *a: self._screen._ws.send_method("server.job_queue.start") and False)
        elif resp == Gtk.ResponseType.OK:
            self._screen._ws.api.print_start(path)
        elif resp == Gtk.ResponseType.REJECT:
            self._screen._confirm_send_action(None, f"Delete file?\n\n{path}", "server.files.delete_file", {"path": f"gcodes/{path}"})
