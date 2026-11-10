# Revo OS – wygaszacz: pasek stanu maszyny, przygaszony szkielet maszyny, logo, pulsująca poświata wokół ekranu
# (w kolorze stanu) i podświetlone pole „Dotknij, aby odblokować” pod logo.
import math
import time

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk, Pango, PangoCairo

COLORS = {"revo_ok": (0.24, 0.84, 0.39), "revo_warn": (0.88, 0.64, 0.23), "revo_err": (1.0, 0.30, 0.32)}
FPS = 12   # wystarczy do płynnej poświaty, nie obciąża Raspberry Pi


def status(printer):
    """(tekst paska, klasa koloru) – stan, postęp druku, temperatury."""
    from ks_includes import revo_home_logic as lg
    if printer is None:
        return "ŁĄCZENIE…", "revo_warn", ""
    v = lg.view(printer, None)
    parts = [v["state"]]
    if v["state"] in ("DRUKUJE", "PAUZA"):
        prog = printer.get_stat("virtual_sdcard", "progress") or 0
        parts.append(f"{prog * 100:.0f}%")
        ps = printer.get_stat("print_stats") or {}
        dur, prog_f = ps.get("print_duration") or 0, prog or 0
        if prog_f > 0.02:
            left = dur / prog_f - dur
            parts.append(f"jeszcze ok. {int(left // 3600)} h {int(left % 3600 // 60):02d} min")
    temps = f"dysza {v['nozzle_temp']}  ·  {lg.bed_label(printer).lower()} {v['bed_temp']}"
    return "  ·  ".join(parts), v["state_class"], temps


class Glow(Gtk.DrawingArea):
    """Pulsująca poświata wzdłuż krawędzi ekranu."""

    def __init__(self):
        super().__init__()
        self.rgb = COLORS["revo_ok"]
        self.connect("draw", self._draw)

    def _draw(self, w, cr):
        W, H = w.get_allocated_width(), w.get_allocated_height()
        a = 0.14 + 0.14 * (0.5 + 0.5 * math.sin(time.time() * 1.6))
        r, g, b = self.rgb
        for i in range(14):                       # miękka krawędź z kilku warstw
            cr.set_source_rgba(r, g, b, a * (1 - i / 14) ** 2)
            cr.set_line_width(3)
            cr.rectangle(i * 3 + 1.5, i * 3 + 1.5, W - i * 6 - 3, H - i * 6 - 3)
            cr.stroke()


class UnlockField(Gtk.DrawingArea):
    """Prostokąt z poświatą i napisem – podpowiedź, gdzie dotknąć."""

    def __init__(self, width, height, text="DOTKNIJ, ABY ODBLOKOWAĆ"):
        super().__init__()
        self.text = text
        self.set_size_request(width, height)
        self.set_halign(Gtk.Align.CENTER)
        self.connect("draw", self._draw)

    @staticmethod
    def _rrect(cr, x, y, w, h, r):
        cr.new_sub_path()
        cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
        cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
        cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
        cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()

    def _draw(self, w, cr):
        W, H = w.get_allocated_width(), w.get_allocated_height()
        p = 0.5 + 0.5 * math.sin(time.time() * 2.2)
        pad = 14
        for i in range(pad, 0, -2):              # zewnętrzna poświata
            cr.set_source_rgba(0.85, 0.86, 0.88, (0.05 + 0.07 * p) * (1 - i / pad))
            self._rrect(cr, pad - i, pad - i, W - 2 * (pad - i), H - 2 * (pad - i), 16 + i)
            cr.fill()
        cr.set_source_rgba(0.08, 0.09, 0.10, 0.92)
        self._rrect(cr, pad, pad, W - 2 * pad, H - 2 * pad, 16)
        cr.fill_preserve()
        cr.set_source_rgba(0.85, 0.86, 0.88, 0.35 + 0.35 * p)
        cr.set_line_width(2)
        cr.stroke()
        lay = PangoCairo.create_layout(cr)
        lay.set_font_description(Pango.FontDescription.from_string("Sans Bold 15"))
        from ks_includes.revo_i18n import tr
        lay.set_text(tr(self.text), -1)
        tw, th = lay.get_pixel_size()
        cr.set_source_rgba(0.90, 0.91, 0.92, 0.55 + 0.4 * p)
        cr.move_to((W - tw) / 2, (H - th) / 2)
        PangoCairo.show_layout(cr, lay)


def build(screen, schematic_factory, logo_path):
    """Zwraca (widżet, funkcja_stop). Odświeża animację i pasek stanu, dopóki widżet jest na ekranie."""
    import os
    W, H = screen.width, screen.height
    ov = Gtk.Overlay()
    glow = Glow()
    glow.set_size_request(W, H)
    ov.add(glow)
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=26)
    box.set_margin_top(28)
    box.set_margin_bottom(40)
    bar = Gtk.Label(xalign=0.5)
    bar.get_style_context().add_class("revo_saver_bar")
    bar.set_ellipsize(Pango.EllipsizeMode.END)
    box.pack_start(bar, False, False, 0)
    sub = Gtk.Label(xalign=0.5)
    sub.get_style_context().add_class("revo_saver_sub")
    box.pack_start(sub, False, False, 0)
    mid = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=30, valign=Gtk.Align.CENTER)
    sch = schematic_factory()
    sch.set_size_request(int(W * 0.8), int(H * 0.36))
    mid.pack_start(sch, False, False, 0)
    if os.path.isfile(logo_path):
        from gi.repository import GdkPixbuf
        img = Gtk.Image.new_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_scale(logo_path, int(W * 0.5), -1, True))
        img.set_opacity(0.55)
        mid.pack_start(img, False, False, 0)
    field = UnlockField(int(W * 0.78), 96)
    mid.pack_start(field, False, False, 0)
    box.pack_start(mid, True, True, 0)
    ov.add_overlay(box)

    state = {"on": True, "n": 0}

    def tick():
        if not state["on"]:
            return False
        state["n"] += 1
        if state["n"] % FPS == 1:          # pasek stanu raz na sekundę
            try:
                text, cls, temps = status(screen.printer)
                bar.set_label(text)
                sub.set_label(temps)
                ctx = bar.get_style_context()
                for c in COLORS:
                    ctx.remove_class(c)
                ctx.add_class(cls)
                glow.rgb = COLORS.get(cls, COLORS["revo_ok"])
            except Exception:
                pass
        glow.queue_draw()
        field.queue_draw()
        return True
    tick()
    GLib.timeout_add(int(1000 / FPS), tick)
    return ov, lambda: state.update(on=False)
