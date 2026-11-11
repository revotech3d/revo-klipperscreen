# Revo OS – test maszyny: obrazek kroku, opis, postęp, czas do końca i przyciski odpowiedzi.
# Cała logika testu siedzi w makrach (REVO_SELFTEST); panel tylko pokazuje stan _REVO_TEST i wysyła odpowiedzi.
import os
import time

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GdkPixbuf, GLib, Gtk

from ks_includes import revo_test_logic as L
from ks_includes.screen_panel import ScreenPanel

IMG_DIRS = [os.path.expanduser("~/revo-config/web/test"),
            os.path.join(os.path.dirname(__file__), "..", "styles", "revo", "images", "test")]
OBJ = "gcode_macro _REVO_TEST"


def img_path(key, sub=""):
    for d in ([os.path.join(x, sub) for x in IMG_DIRS] if sub else []) + IMG_DIRS:
        p = os.path.join(d, f"{key}.png")
        if os.path.isfile(p):
            return p
    return None


class Panel(ScreenPanel):
    def __init__(self, screen, title, **kwargs):
        super().__init__(screen, title or "Test maszyny")
        self.sig = None
        self.step_key = None
        self.step_t0 = time.monotonic()
        self.cur_img = None
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.get_style_context().add_class("revo_home")
        top = Gtk.Box(spacing=6)
        self.l_step = self._lbl("", "revo_test_head")
        self.l_eta = self._lbl("", "revo_test_head", 1.0)
        top.pack_start(self.l_step, True, True, 0)
        top.pack_end(self.l_eta, False, False, 0)
        box.pack_start(top, False, False, 0)
        self.bar = Gtk.ProgressBar()
        self.bar.get_style_context().add_class("revo_progress")
        box.pack_start(self.bar, False, False, 0)
        self.l_left = self._lbl("", "revo_test_head")
        box.pack_start(self.l_left, False, False, 0)
        frame = Gtk.EventBox()
        frame.get_style_context().add_class("revo_test_img")
        self.img = Gtk.Image()
        frame.add(self.img)
        box.pack_start(frame, False, False, 2)
        self.l_name = self._lbl("", "revo_test_name", wrap=True)
        self.l_q = self._lbl("", "revo_test_q", wrap=True)
        self.l_desc = self._lbl("", "revo_test_desc", wrap=True)
        self.l_note = self._lbl("", "revo_warn", wrap=True)
        self.l_skip = self._lbl("", "revo_test_skip", wrap=True)
        for w in (self.l_name, self.l_q, self.l_desc, self.l_skip, self.l_note):
            box.pack_start(w, False, False, 0)
        self.btns = Gtk.Grid(row_spacing=8, column_spacing=8, column_homogeneous=True)
        box.pack_end(self.btns, False, False, 0)
        self.content.add(box)
        self.width = max(200, int(self._gtk.content_width) - 24)

    @staticmethod
    def _lbl(text, cls, xalign=0.0, wrap=False):
        lb = Gtk.Label(label=text, xalign=xalign)
        lb.get_style_context().add_class(cls)
        lb.set_line_wrap(wrap)
        return lb

    def activate(self):
        self.refresh()
        if self.timer is None:
            self.timer = GLib.timeout_add_seconds(1, self.refresh)

    timer = None

    def deactivate(self):
        if self.timer:
            GLib.source_remove(self.timer)
            self.timer = None

    def process_update(self, action, data):
        if action == "notify_status_update" and OBJ in data:
            self.refresh()

    def _state(self):
        d = self._printer.data.get(OBJ) or {}
        return d

    def refresh(self):
        t = self._state()
        key = (t.get("step"), t.get("faza") in L.ACTIVE)
        if key != self.step_key:
            self.step_key, self.step_t0 = key, time.monotonic()
        v = L.view(t, time.monotonic() - self.step_t0)
        if v["faza"] in L.ACTIVE:
            self.l_step.set_text(f"KROK {v['num']} / {v['total']}")
            self.l_eta.set_text(v["eta"])
            self.l_left.set_text(v["left"])
        else:
            self.l_step.set_text("TEST MASZYNY")
            self.l_eta.set_text("")
            self.l_left.set_text("")
        self.bar.set_fraction(v["progress"])
        from ks_includes.revo_i18n import tr
        self.l_name.set_text(tr(v["name"]).upper())
        self.l_q.set_text(v["title"])
        desc = v["desc"]
        if v["problems"]:
            desc += "\n\nProblemy:\n" + "\n".join("• " + p for p in v["problems"])
        self.l_desc.set_text(desc)
        self.l_skip.set_text("Skipped (no effect on the result):\n" + "\n".join("• " + k for k in v["skipped"]) if v["skipped"] else "")
        self.l_skip.set_visible(bool(v["skipped"]))
        self.l_note.set_text(v["note"])
        self.l_note.set_visible(bool(v["note"]))
        img = v["img"] or ("intro" if v["faza"] == "idle" else "conn")
        if img != self.cur_img:
            self.cur_img = img
            from ks_includes import revo_home_logic as lg
            p = img_path(img, "" if lg.is_belt(self._printer) else "stol")
            if p:
                h = int(self.width * 300 / 440)
                self.img.set_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_size(p, self.width, h))
            else:
                self.img.clear()
        sig = tuple(v["buttons"])
        if sig != self.sig:
            self.sig = sig
            for c in self.btns.get_children():
                self.btns.remove(c)
            n = len(v["buttons"])
            cols = 2 if n == 4 else n
            for i, (label, script, style) in enumerate(v["buttons"]):
                b = Gtk.Button(label=label)
                b.get_style_context().add_class(f"revo_t_{style}")
                b.get_child().set_line_wrap(True)
                b.connect("clicked", self.send, script)
                # 3 przyciski: ostatni (główny) na całą szerokość pod spodem
                if n == 3 and i == 2:
                    self.btns.attach(b, 0, 1, 2, 1)
                elif n == 3:
                    self.btns.attach(b, i, 0, 1, 1)
                else:
                    self.btns.attach(b, i % cols, i // cols, 1, 1)
            self.btns.show_all()
        return True

    def send(self, widget, script):
        self._screen._ws.api.gcode_script(script)
