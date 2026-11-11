# Revo OS – wygaszacz OrionUI: zegar, stan maszyny, przygaszony schemat, heksagony temperatur, „TOUCH TO WAKE”.
import math
import time

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import GLib, Gtk, Pango, PangoCairo

COLORS = {"revo_ok": (0.24, 0.84, 0.39), "revo_warn": (0.88, 0.64, 0.23), "revo_err": (1.0, 0.30, 0.32)}
FPS = 8          # animacja tylko przez pierwsze minuty
ANIM_S = 120     # potem spokój: logo stoi, odświeżenie raz na 5 s (Raspberry Pi i Xorg prawie bez obciążenia)
SPOKOJ_CO = 5


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
            parts.append(f"{int(left // 3600)} h {int(left % 3600 // 60):02d} min left")
    temps = f"nozzle {v['nozzle_temp']}  ·  {'belt' if lg.is_belt(printer) else 'bed'} {v['bed_temp']}"
    return "  ·  ".join(parts), v["state_class"], temps


class Glow(Gtk.DrawingArea):
    """Pulsująca poświata wzdłuż krawędzi ekranu."""

    def __init__(self):
        super().__init__()
        self.rgb = COLORS["revo_ok"]
        self.connect("draw", self._draw)

    def _draw(self, w, cr):
        W, H = w.get_allocated_width(), w.get_allocated_height()
        a = 0.21 if getattr(self, "spokoj", False) else 0.14 + 0.14 * (0.5 + 0.5 * math.sin(time.time() * 1.6))
        r, g, b = self.rgb
        for i in range(14):                       # miękka krawędź z kilku warstw
            cr.set_source_rgba(r, g, b, a * (1 - i / 14) ** 2)
            cr.set_line_width(3)
            cr.rectangle(i * 3 + 1.5, i * 3 + 1.5, W - i * 6 - 3, H - i * 6 - 3)
            cr.stroke()


def _ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


class GalaxyLogo(Gtk.DrawingArea):
    """Galaktyka ze świecących heksagonów, która co ~22 s zlatuje się w logo [r]evo3d, migocze i rozprasza.
    Pod spodem cichy napis „Dotknij, aby odblokować”."""

    CYCLE = 22.0      # s: 0–6 galaktyka · 6–9.5 zlot · 9.5–17 logo · 17–20.5 rozproszenie · 20.5–22 galaktyka

    def __init__(self, width, height, logo_path, text="DOTKNIJ, ABY ODBLOKOWAĆ", seed=7):
        super().__init__()
        import random
        self.text = text
        self.W, self.H = width, height
        self.set_size_request(width, height)
        self.set_halign(Gtk.Align.CENTER)
        rnd = random.Random(seed)
        targets = self._logo_points(logo_path, width, height - 34, rnd)
        n = max(len(targets), 120)
        rnd.shuffle(targets)
        self.stars = []
        for k in range(n):
            arm = k % 2
            r = rnd.random() ** 0.6
            ang = arm * math.pi + r * 3.2 + rnd.gauss(0, 0.28)
            gx, gy = 0.5 + 0.47 * r * math.cos(ang), 0.5 + 0.46 * r * math.sin(ang) * 0.8
            tx, ty = targets[k] if k < len(targets) else (gx, gy)
            in_logo = k < len(targets)
            size = (1.2 + 0.9 * rnd.random()) if in_logo else (0.8 + 1.8 * (1 - r) * rnd.random())
            tint = rnd.choice(((0.78, 0.86, 1.0), (0.92, 0.90, 1.0), (0.70, 0.95, 0.98), (1.0, 0.93, 0.85)))
            self.stars.append((gx, gy, tx, ty, in_logo, size, tint, rnd.uniform(0.6, 2.4), rnd.uniform(0, 6.28),
                               rnd.uniform(0.30, 0.75), r, ang, rnd.uniform(0, 0.25)))
        self.t0 = time.time()
        self.connect("draw", self._draw)

    @staticmethod
    def _logo_points(path, W, H, rnd):
        """Punkty (0–1) na kształcie logo – próbkowanie kanału alfa co kilka pikseli."""
        try:
            from gi.repository import GdkPixbuf
            pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, int(W * 0.86), -1, True)
            w, h, rs, ch = pb.get_width(), pb.get_height(), pb.get_rowstride(), pb.get_n_channels()
            px = pb.get_pixels()
            ox, oy = (W - w) / 2, (H - h) / 2
            pts, step = [], 5
            for y in range(0, h, step):
                for x in range(0, w, step):
                    o = y * rs + x * ch
                    a = px[o + 3] if ch == 4 else 255
                    if a > 120 and px[o] + px[o + 1] + px[o + 2] > 150:
                        pts.append(((ox + x + rnd.uniform(-0.8, 0.8)) / W, (oy + y + rnd.uniform(-0.8, 0.8)) / H))
            if len(pts) > 250:
                pts = rnd.sample(pts, 250)
            return pts
        except Exception:
            return []

    @staticmethod
    def _hex(cr, x, y, r):
        for i in range(6):
            a = math.pi / 6 + i * math.pi / 3
            (cr.move_to if i == 0 else cr.line_to)(x + r * math.cos(a), y + r * math.sin(a))
        cr.close_path()

    def _phase(self, t):
        """Ile gwiazdy są „w logo” (0 = galaktyka, 1 = logo)."""
        if getattr(self, "spokoj", False):
            return 1.0
        c = (t - self.t0) % self.CYCLE
        if c < 6:
            return 0.0
        if c < 9.5:
            return _ease((c - 6) / 3.5)
        if c < 17:
            return 1.0
        if c < 20.5:
            return 1 - _ease((c - 17) / 3.5)
        return 0.0

    def _draw(self, w, cr):
        import cairo
        W, H0 = w.get_allocated_width(), w.get_allocated_height()
        H = H0 - 34
        t = time.time()
        p = self._phase(t)
        spin = (t - self.t0) * 0.05                       # powolny obrót galaktyki
        # mgławica w jądrze – słabnie, gdy powstaje logo
        cr.save()
        cr.translate(W / 2, H / 2)
        cr.scale(1.0, 0.6)
        g = cairo.RadialGradient(0, 0, 0, 0, 0, min(W, H) * 0.42)
        g.add_color_stop_rgba(0, 0.62, 0.68, 0.92, (0.16 + 0.04 * math.sin(t * 0.7)) * (1 - 0.7 * p))
        g.add_color_stop_rgba(0.5, 0.45, 0.50, 0.75, 0.05 * (1 - 0.7 * p))
        g.add_color_stop_rgba(1, 0, 0, 0, 0)
        cr.set_source(g)
        cr.arc(0, 0, min(W, H) * 0.42, 0, 2 * math.pi)
        cr.fill()
        cr.restore()
        for gx, gy, tx, ty, in_logo, size, (r, gg, b), sp, ph, base, rr, ang, lag in self.stars:
            # pozycja w obracającej się galaktyce
            a2 = ang + spin * (1.2 - rr)
            gx2, gy2 = 0.5 + 0.47 * rr * math.cos(a2), 0.5 + 0.46 * rr * math.sin(a2) * 0.8
            q = _ease((p - lag) / (1 - lag)) if in_logo and p > lag else 0.0
            x, y = (gx2 + (tx - gx2) * q) * W, (gy2 + (ty - gy2) * q) * H
            tw = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(t * sp + ph))
            al = base * tw
            if not in_logo:
                al *= 1 - 0.75 * p                         # tło przygasa, gdy świeci logo
            elif q > 0.95:
                al = max(al, 0.48)                         # logo czytelne, ale delikatne
            cr.set_source_rgba(r, gg, b, al * 0.10)
            self._hex(cr, x, y, size * 2.2)
            cr.fill()
            cr.set_source_rgba(r, gg, b, al)
            self._hex(cr, x, y, size)
            cr.fill()
        lay = PangoCairo.create_layout(cr)
        lay.set_font_description(Pango.FontDescription.from_string("Sans 11"))
        from ks_includes.revo_i18n import tr
        lay.set_text(tr(self.text), -1)
        tw_, th = lay.get_pixel_size()
        cr.set_source_rgba(0.88, 0.90, 0.95, 0.32 + 0.12 * math.sin(t * 1.3))
        cr.move_to((W - tw_) / 2, H0 - th - 4)
        PangoCairo.show_layout(cr, lay)


def build(screen, schematic_factory, logo_path):
    """OrionUI: duży zegar, nazwa i stan maszyny, przygaszony schemat, heksagony temperatur, „TOUCH TO WAKE”.
    Bez ciągłej animacji – odświeżenie raz na sekundę (Raspberry Pi prawie bez obciążenia).
    Zwraca (widżet, funkcja_stop)."""
    from ks_includes import revo_home_logic as lg
    from ks_includes.revo_i18n import tr
    from ks_includes.widgets.revo_home import HexGauge
    W, H = screen.width, screen.height
    ov = Gtk.Overlay()
    bg = Gtk.Box()
    bg.get_style_context().add_class("revo_saver_bg")
    bg.set_hexpand(True)
    bg.set_vexpand(True)
    ov.add(bg)
    strip = Gtk.DrawingArea()
    strip.set_size_request(6, -1)
    strip.set_halign(Gtk.Align.START)
    strip.rgb = COLORS["revo_ok"]

    def draw_strip(w, cr):
        r, g, b = strip.rgb
        cr.set_source_rgb(r, g, b)
        cr.rectangle(0, 0, 6, w.get_allocated_height())
        cr.fill()
    strip.connect("draw", draw_strip)
    ov.add_overlay(strip)

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    box.set_margin_top(int(H * 0.08))
    box.set_margin_bottom(28)
    clock = Gtk.Label(xalign=0.5)
    clock.get_style_context().add_class("revo_saver_clock")
    box.pack_start(clock, False, False, 0)
    name = Gtk.Label(xalign=0.5)
    name.get_style_context().add_class("revo_saver_sub")
    box.pack_start(name, False, False, 4)
    bar = Gtk.Label(xalign=0.5)
    bar.get_style_context().add_class("revo_saver_bar")
    bar.set_ellipsize(Pango.EllipsizeMode.END)
    box.pack_start(bar, False, False, 14)
    sch = schematic_factory()
    sch.alpha = 0.35
    sch.set_size_request(int(W * 0.66), int(H * 0.30))
    sch.set_halign(Gtk.Align.CENTER)
    box.pack_start(sch, True, True, 0)
    hexes = Gtk.Box(spacing=6, halign=Gtk.Align.CENTER)
    hx = [HexGauge("NOZZLE", 300), HexGauge("BELT" if lg.is_belt(screen.printer) else "BED", 120), HexGauge("CHAMBER", 60)]
    for h in hx:
        h.set_size_request(120, 76)
        h.set_hexpand(False)
        hexes.pack_start(h, False, False, 0)
    box.pack_start(hexes, False, False, 10)
    hint = Gtk.Label(label="TOUCH TO WAKE", xalign=0.5)
    hint.get_style_context().add_class("revo_saver_hint")
    box.pack_end(hint, False, False, 0)
    ov.add_overlay(box)

    try:
        vars_ = screen.printer.get_stat("save_variables", "variables") or {}
        name.set_label(("REVON BELT" if lg.is_belt(screen.printer) else "REVON") + (f" · {vars_['revo_nazwa']}".upper() if vars_.get("revo_nazwa") else ""))
    except Exception:
        name.set_label("REVON")
    state = {"on": True}

    def num(o, k):
        x = (screen.printer.get_stat(o) or {}).get(k)
        return float(x) if isinstance(x, (int, float)) else None

    def tick():
        if not state["on"]:
            return False
        clock.set_label(time.strftime("%H:%M"))
        try:
            text, cls, _temps = status(screen.printer)
            bar.set_label(tr(text))
            ctx = bar.get_style_context()
            for c in COLORS:
                ctx.remove_class(c)
            ctx.add_class(cls)
            strip.rgb = COLORS.get(cls, COLORS["revo_ok"])
            strip.queue_draw()
            hx[0].set(num("extruder", "temperature"), num("extruder", "target"))
            hx[1].set(num("heater_bed", "temperature"), num("heater_bed", "target"))
            hx[2].set(num(lg.cfg(screen.printer, "chamber", "temperature_sensor chamber"), "temperature"), None)
        except Exception:
            pass
        return True
    tick()
    GLib.timeout_add_seconds(1, tick)
    return ov, lambda: state.update(on=False)
