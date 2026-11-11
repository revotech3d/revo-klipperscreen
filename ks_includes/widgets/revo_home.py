# Revo OS – ekran główny „Gotowa”: schemat maszyny, kafelki temperatur, DRUKUJ, presety, menu
import logging
import math

import cairo
import threading

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, GLib, Gtk

from ks_includes.widgets.revo_hold import Hold, hold_steps
from ks_includes import revo_home_logic as logic
from ks_includes import revo_serwis_logic as serwis
from ks_includes import revo_lock_logic as rl
from ks_includes import revo_agent_client as agent

PRESETS = [("PLA", 210, 60), ("PETG", 240, 80), ("ABS/ASA", 250, 100)]


def _lbl(text, cls, xalign=0.0):
    lb = Gtk.Label(label=text, xalign=xalign)
    lb.get_style_context().add_class(cls)
    return lb


class HexGauge(Gtk.DrawingArea):
    """OrionUI: heksagon z kropek – kropki zapalają się wraz z temperaturą (cel albo max)."""
    N = 44

    def __init__(self, title, tmax, on_click=None):
        super().__init__()
        self.title, self.tmax = title, tmax
        self.temp = self.target = None
        self.set_size_request(140, 88)
        self.set_hexpand(True)
        self.connect("draw", self._draw)
        if on_click:
            self.add_events(Gdk.EventMask.BUTTON_RELEASE_MASK)
            self.connect("button-release-event", lambda *a: on_click())

    def set(self, temp, target):
        if (temp, target) != (self.temp, self.target):
            self.temp, self.target = temp, target
            self.queue_draw()

    def _draw(self, w, ctx):
        W, H = w.get_allocated_width(), w.get_allocated_height()
        hw = min(W - 4, 150)
        x0 = (W - hw) / 2
        P = [(x0 + hw * .22, 3), (x0 + hw * .78, 3), (x0 + hw - 3, H / 2), (x0 + hw * .78, H - 3), (x0 + hw * .22, H - 3), (x0 + 3, H / 2)]
        P.append(P[0])
        L = [math.hypot(P[i + 1][0] - P[i][0], P[i + 1][1] - P[i][1]) for i in range(6)]
        T = sum(L)
        t = self.temp or 0
        base = self.target if self.target else self.tmax
        on = round(self.N * max(0.0, min(1.0, t / base))) if self.temp is not None else 0
        for j in range(self.N):
            d, k = T * j / self.N, 0
            while d > L[k]:
                d -= L[k]
                k += 1
            f = d / L[k]
            x = P[k][0] + (P[k + 1][0] - P[k][0]) * f
            y = P[k][1] + (P[k + 1][1] - P[k][1]) * f
            if j < on:
                ctx.set_source_rgba(0.353, 0.663, 0.902, 0.35)
                ctx.arc(x, y, 3.5, 0, 2 * math.pi)
                ctx.fill()
                ctx.set_source_rgb(1, 1, 1)
                ctx.arc(x, y, 1.6, 0, 2 * math.pi)
            else:
                ctx.set_source_rgba(0.867, 0.902, 0.933, 0.18)
                ctx.arc(x, y, 1.0, 0, 2 * math.pi)
            ctx.fill()
        cx = W / 2

        def text(s, size, y, rgb, font="Rajdhani"):
            ctx.select_font_face(font, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD if font == "Rajdhani" else cairo.FONT_WEIGHT_NORMAL)
            ctx.set_font_size(size)
            e = ctx.text_extents(s)
            ctx.set_source_rgb(*rgb)
            ctx.move_to(cx - e.width / 2 - e.x_bearing, y)
            ctx.show_text(s)
        text(self.title, 11, H * .27, (0.353, 0.663, 0.902))
        text("–" if self.temp is None else f"{self.temp:.0f}°", 28, H * .62, (0.867, 0.902, 0.933), "Share Tech Mono")
        sub = f"→ {self.target:.0f}°" if self.target else ("PASSIVE" if self.tmax <= 80 and self.title == "CHAMBER" else "OFF")
        text(sub, 10, H * .83, (0.369, 0.459, 0.525), "Share Tech Mono")


def window(title, child, code=""):
    """OrionUI: okno z paskiem tytułu (■ TITLE ... code)."""
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    box.get_style_context().add_class("revo_win")
    bar = Gtk.Box(spacing=6)
    bar.get_style_context().add_class("revo_win_bar")
    sq = _lbl("■", "revo_win_sq")
    bar.pack_start(sq, False, False, 0)
    bar.pack_start(_lbl(title, "revo_win_title"), False, False, 0)
    if code:
        bar.pack_end(_lbl(code, "revo_win_code", 1.0), False, False, 0)
    box.pack_start(bar, False, False, 0)
    box.pack_start(child, True, True, 0)
    return box


class Tile(Gtk.EventBox):
    """Kafelek z podpisem i wartością, klikany."""

    def __init__(self, title, on_click=None):
        super().__init__()
        self.get_style_context().add_class("revo_tile")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.title = _lbl(title, "revo_tile_title", 0.5)
        self.value = _lbl("–", "revo_tile_value", 0.5)
        self.sub = _lbl("", "revo_tile_sub", 0.5)
        box.pack_start(self.title, False, False, 0)
        box.pack_start(self.value, False, False, 0)
        box.pack_start(self.sub, False, False, 0)
        self.add(box)
        if on_click:
            self.connect("button-release-event", lambda *a: on_click())


class Schematic(Gtk.DrawingArea):
    """Schemat Revo Belt (CoreXY + taśma) rysowany cairo, układ jak w makiecie (viewBox 436×380)."""

    def __init__(self, model):
        super().__init__()
        self.model = model
        self.light = True
        self.wire = False      # sam szkielet (bez wypełnień) – wygaszacz
        self.alpha = 1.0
        self.set_vexpand(True)
        self.set_hexpand(True)
        self.connect("draw", self._draw)

    @staticmethod
    def _rgb(ctx, hexc, a=1.0):
        h = hexc.lstrip("#")
        ctx.set_source_rgba(int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255, a)

    def _poly(self, ctx, pts, fill=None, stroke=None, lw=1.5):
        if self.wire:
            fill, stroke = None, stroke or fill
        ctx.move_to(*pts[0])
        for p in pts[1:]:
            ctx.line_to(*p)
        ctx.close_path()
        if fill:
            self._rgb(ctx, fill)
            ctx.fill_preserve() if stroke else ctx.fill()
        if stroke:
            self._rgb(ctx, stroke)
            ctx.set_line_width(lw)
            ctx.stroke()

    def _line(self, ctx, a, b, color, lw):
        self._rgb(ctx, color)
        ctx.set_line_width(lw)
        ctx.move_to(*a)
        ctx.line_to(*b)
        ctx.stroke()

    def _draw(self, w, ctx):
        if self.alpha < 1.0:
            ctx.push_group()
            self._draw_inner(w, ctx)
            ctx.pop_group_to_source()
            ctx.paint_with_alpha(self.alpha)
            return False
        return self._draw_inner(w, ctx)

    def _draw_inner(self, w, ctx):
        W, H = w.get_allocated_width(), w.get_allocated_height()
        # kadr samej maszyny (x 84–356, y 86–336 w układzie makiety)
        s = min(W / 272, H / 250)
        ctx.translate((W - 272 * s) / 2, (H - 250 * s) / 2)
        ctx.scale(s, s)
        ctx.translate(-84, -86)
        # cień, dach, bok, kolumna
        self._rgb(ctx, "#14171A")
        ctx.save(); ctx.translate(224, 324); ctx.scale(150, 10); ctx.arc(0, 0, 1, 0, 6.2832); ctx.restore(); ctx.fill()
        self._poly(ctx, [(100, 112), (126, 92), (348, 92), (322, 112)], "#15181C", "#5B616A")
        self._poly(ctx, [(322, 112), (348, 92), (348, 286), (322, 306)], "#0D0F11", "#5B616A")
        self._poly(ctx, [(100, 112), (322, 112), (322, 306), (100, 306)], "#0F1114", "#9AA0A8", 2.5)
        self._line(ctx, (274, 112), (274, 306), "#9AA0A8", 2.5)
        self._poly(ctx, [(282, 132), (314, 132), (314, 186), (282, 186)], "#0A0B0D", "#C9CDD2")
        self._poly(ctx, [(283, 133), (286, 133), (286, 185), (283, 185)], "#3ED663")
        for y in (270, 278, 286):
            self._line(ctx, (284, y), (312, y), "#3A3F46", 1.5)
        # światło
        if self.light:
            self._rgb(ctx, "#E6E8EB", 0.10)
            ctx.rectangle(108, 126, 158, 120); ctx.fill()
        self._line(ctx, (112, 126), (262, 126), "#E6E8EB" if self.light else "#3A3F46", 2.5)
        # szyba drzwi
        self._rgb(ctx, "#1A1E23", 0.4); ctx.rectangle(108, 120, 158, 178); ctx.fill()
        self._rgb(ctx, "#4A4F57"); ctx.set_line_width(1); ctx.rectangle(108, 120, 158, 178); ctx.stroke()
        # CoreXY: rama górna, belka X, głowica
        self._poly(ctx, [(112, 140), (124, 132), (252, 132), (262, 140)], None, "#3A3F46")
        self._line(ctx, (108, 152), (266, 152), "#9AA0A8", 2)
        self._poly(ctx, [(220, 142), (246, 142), (246, 162), (220, 162)], "#2A2E34", "#C9CDD2")
        self._poly(ctx, [(227, 162), (239, 162), (233, 170)], "#C9CDD2")
        if self.model != "belt":
            self._draw_bed(ctx)
            return False
        # taśma (stół ruchomy) – biegnie od tyłu komory do przodu i wysuwa się przodem
        def roller(x0, x1, y, r):
            ctx.set_line_cap(1)
            self._line(ctx, (x0, y), (x1, y), "#9AA0A8", 2 * r + 3)
            self._line(ctx, (x0, y), (x1, y), "#15181C", 2 * r)
            ctx.set_line_cap(0)
            for x in (x0, x1):
                self._rgb(ctx, "#9AA0A8"); ctx.arc(x, y, r * 0.45, 0, 6.2832); ctx.fill()
        # wąski pas biegnący w głąb (tył → przód), wystaje przez front maszyny
        self._poly(ctx, [(122, 306), (214, 306), (256, 274), (164, 274)], "#111317", "#3A3F46", 1)
        roller(164, 256, 269, 5)
        self._poly(ctx, [(122, 298), (214, 298), (256, 266), (164, 266)], "#2A2E34", "#9AA0A8")
        for t in (0.2, 0.4, 0.6, 0.8):
            self._line(ctx, (122 + 42 * t, 298 - 32 * t), (214 + 42 * t, 298 - 32 * t), "#3A3F46", 1)
        roller(122, 214, 303, 5)
        self._rgb(ctx, "#C9CDD2"); ctx.rectangle(258, 192, 3, 42); ctx.fill()
        for a, b in (((104, 306), (104, 314)), ((318, 306), (318, 314)), ((344, 286), (344, 294))):
            self._line(ctx, a, b, "#5B616A", 2.5)
        return False


def _draw_bed_impl(self, ctx):
    """Sztywny stół: płyta w perspektywie na 4 śrubach Z."""
    self._poly(ctx, [(114, 250), (256, 250), (266, 240), (124, 240)], "#2A2E34", "#C9CDD2")
    self._poly(ctx, [(114, 250), (256, 250), (256, 256), (114, 256)], "#1A1E23", "#5B616A")
    for x in (120, 250):
        self._line(ctx, (x, 256), (x, 298), "#5B616A", 2.5)
    for x in (130, 260):
        self._line(ctx, (x, 132), (x, 240), "#3A3F46", 1.5)
    self._rgb(ctx, "#C9CDD2"); ctx.rectangle(258, 192, 3, 42); ctx.fill()
    for a, b in (((104, 306), (104, 314)), ((318, 306), (318, 314)), ((344, 286), (344, 294))):
        self._line(ctx, a, b, "#5B616A", 2.5)


Schematic._draw_bed = _draw_bed_impl


class RevoActions:
    """Wspólne okna Revo (temperatura, dysza). Wymaga: self.p (panel z _gtk), self.printer, self.screen."""

    def gcode(self, script):
        self.screen._ws.api.gcode_script(script)

    def preheat(self, widget, ext, bed):
        self.gcode(f"SET_HEATER_TEMPERATURE HEATER=extruder TARGET={ext}\nSET_HEATER_TEMPERATURE HEATER=heater_bed TARGET={bed}")

    def toggle_light(self):
        pin = logic.light_pin(self.printer)
        if pin:
            on = (self.printer.get_stat(f"output_pin {pin}", "value") or 0) > 0
            self.gcode(f"SET_PIN PIN={pin} VALUE={0 if on else 1}")

    def heater_dialog(self, heater, title, presets, tmax):
        """Ustawienie temperatury docelowej: presety + korekta ±5°C."""
        st = self.printer.get_stat(heater) or {}
        self._ht = {"h": heater, "t": int(st.get("target") or 0), "max": tmax}
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        box.get_style_context().add_class("revo_home")
        box.pack_start(_lbl(f"{title} – TEMPERATURA", "revo_state", 0.5), False, False, 4)
        now = st.get("temperature")
        box.pack_start(_lbl(f"Teraz: {now:.0f}°C" if now is not None else "Teraz: –", "revo_info", 0.5), False, False, 0)
        self._ht_lbl = _lbl("", "revo_big", 0.5)
        box.pack_start(self._ht_lbl, False, False, 4)
        adj = Gtk.Grid(column_homogeneous=True, column_spacing=8)
        self._holds = []
        for i, sign in enumerate((-1, 1)):
            b = Gtk.Button(label="−" if sign < 0 else "+")
            b.get_style_context().add_class("revo_preset")
            b.set_size_request(-1, 72)
            self._holds.append(Hold(b, lambda held, sign=sign: self._ht_set(self._ht["t"] + sign * hold_steps(held))))
            adj.attach(b, i, 0, 1, 1)
        box.pack_start(adj, False, False, 0)
        box.pack_start(_lbl("Przytrzymaj − / +, żeby zmieniać szybciej", "revo_info", 0.5), False, False, 0)
        box.pack_start(_lbl("PRESETY", "revo_tile_title"), False, False, 4)
        g = Gtk.Grid(column_homogeneous=True, column_spacing=8, row_spacing=8)
        for i, v in enumerate(presets):
            b = Gtk.Button(label="WYŁ." if v == 0 else f"{v}°")
            b.get_style_context().add_class("revo_preset")
            b.set_size_request(-1, 56)
            b.connect("clicked", lambda w, v=v: self._ht_set(v))
            g.attach(b, i % 4, i // 4, 1, 1)
        box.pack_start(g, False, False, 0)
        self._ht_set(self._ht["t"])
        buttons = [{"name": "Set", "response": Gtk.ResponseType.OK, "style": "dialog-primary"},
                   {"name": "Cancel", "response": Gtk.ResponseType.CANCEL, "style": "dialog-secondary"}]
        self.p._gtk.Dialog(title, buttons, box, self._heater_response)

    def _ht_set(self, v):
        self._ht["t"] = max(0, min(self._ht["max"], int(v)))
        self._ht_lbl.set_label("WYŁĄCZONE" if self._ht["t"] == 0 else f"{self._ht['t']}°C")

    def _heater_response(self, dialog, response):
        self.p._gtk.remove_dialog(dialog)
        if response == Gtk.ResponseType.OK:
            self.gcode(f"SET_HEATER_TEMPERATURE HEATER={self._ht['h']} TARGET={self._ht['t']}")

    def nozzle_dialog(self):
        """Wybór zamontowanej dyszy: średnica + materiał → REVO_SET_NOZZLE."""
        self._noz = {"d": None, "t": None}
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        box.get_style_context().add_class("revo_home")
        title = _lbl("ZAMONTOWANA DYSZA", "revo_state", 0.5)
        box.pack_start(title, False, False, 0)
        vars_ = self.printer.get_stat("save_variables", "variables") or {}
        cur = str(vars_.get("revo_nozzle", "")).split()
        rows = (("ŚREDNICA", "d", ["0.25", "0.4", "0.6", "0.8"]),
                ("MATERIAŁ", "t", ["mosiadz", "stal", "wolfram"]))
        names = {"mosiadz": "Brass", "stal": "Hardened steel", "wolfram": "Tungsten"}
        for head, key, opts in rows:
            box.pack_start(_lbl(head, "revo_tile_title"), False, False, 0)
            g = Gtk.Grid(column_homogeneous=True, column_spacing=8)
            first = None
            for i, o in enumerate(opts):
                rb = Gtk.RadioButton.new_with_label_from_widget(first, names.get(o, f"Ø{o}"))
                rb.set_mode(False)
                rb.get_style_context().add_class("revo_preset")
                first = first or rb
                if (key == "d" and cur and cur[0] == o) or (key == "t" and len(cur) > 1 and cur[1] == o):
                    rb.set_active(True)
                    self._noz[key] = o
                rb.connect("toggled", lambda w, k=key, v=o: w.get_active() and self._noz.__setitem__(k, v))
                g.attach(rb, i, 0, 1, 1)
            if self._noz[key] is None:
                self._noz[key] = opts[1] if key == "d" else opts[0]
            box.pack_start(g, False, False, 0)
        hint = _lbl("Maszyna porówna ją z dyszą zapisaną w pliku przy każdym starcie druku.", "revo_info", 0.0)
        hint.set_line_wrap(True)
        box.pack_start(hint, False, False, 0)
        buttons = [{"name": "Save", "response": Gtk.ResponseType.OK, "style": "dialog-primary"},
                   {"name": "Replace\nnozzle", "response": Gtk.ResponseType.APPLY, "style": "dialog-secondary"},
                   {"name": "Cancel", "response": Gtk.ResponseType.CANCEL, "style": "dialog-secondary"}]
        self.p._gtk.Dialog("Dysza", buttons, box, self._nozzle_response)

    def _nozzle_response(self, dialog, response):
        self.p._gtk.remove_dialog(dialog)
        if response == Gtk.ResponseType.APPLY:   # prowadzona wymiana dyszy krok po kroku
            self.screen.show_panel("revo_dysza", "Wymiana dyszy")
            return
        if response == Gtk.ResponseType.OK:
            self.gcode(f"REVO_SET_NOZZLE DIAMETER={self._noz['d']} TYPE={self._noz['t']}")
            # save_variables nie jest subskrybowane – od razu pokaż nową dyszę
            sv = self.printer.data.setdefault("save_variables", {}).setdefault("variables", {})
            sv["revo_nozzle_diameter"] = float(self._noz["d"])
            sv["revo_nozzle"] = f"{self._noz['d']} {self._noz['t']}"
            self.refresh()

    def refresh(self):
        return True


class RevoHome(RevoActions, Gtk.Box):
    def __init__(self, panel):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.p = panel
        self.screen = panel._screen
        self.printer = panel._printer
        self.hours = None
        self.get_style_context().add_class("revo_home")

        top = Gtk.Box(spacing=8)
        self.state_lbl = _lbl("GOTOWA", "revo_state")
        self.info_lbl = _lbl("", "revo_info", 1.0)
        top.pack_start(self.state_lbl, False, False, 0)
        top.pack_end(self.info_lbl, True, True, 0)
        self.pack_start(top, False, False, 0)

        # zdalny podgląd aktywny: widoczny pasek z możliwością zakończenia
        self.live_btn = Gtk.Button(label="REVOTECH WIDZI KAMERĘ I EKRAN · ZAKOŃCZ")
        self.live_btn.get_style_context().add_class("revo_live_alert")
        self.live_btn.set_no_show_all(True)
        self.live_btn.connect("clicked", lambda *a: threading.Thread(target=agent.call, args=("/podglad/koniec", {}), daemon=True).start() or self.live_btn.hide())
        self.pack_start(self.live_btn, False, False, 0)

        # przypomnienie serwisowe – widoczne tylko, gdy przegląd jest po terminie
        self.serwis_btn = Gtk.Button(label="")
        self.serwis_btn.get_style_context().add_class("revo_serwis_alert")
        self.serwis_btn.set_no_show_all(True)
        self.serwis_btn.connect("clicked", lambda *a: self.screen.show_panel("revo_serwis", "Przeglądy"))
        self.pack_start(self.serwis_btn, False, False, 0)

        # schemat w środku, kafelki w kolumnach po bokach
        self.schem = Schematic(logic.machine_type(self.printer))
        self.schem.set_size_request(200, 190)
        self.schem.set_margin_start(8)
        self.schem.set_margin_end(8)
        self.t_nozzle = Tile("DYSZA", self.nozzle_dialog)
        bl = logic.bed_label(self.printer)
        self.t_bed = Tile(bl, lambda: self.heater_dialog("heater_bed", bl, [0, 60, 70, 80, 90, 100, 110], 130))
        self.t_chamber = Tile("KOMORA")
        self.t_light = Tile("OŚWIETLENIE", self.toggle_light)
        self.t_light.value.get_style_context().add_class("revo_tile_value_small")
        self.hx_noz = HexGauge("NOZZLE", 300, lambda: self.heater_dialog("extruder", "NOZZLE", [0, 200, 210, 220, 240, 250, 260], 300))
        self.hx_bed = HexGauge({"PAS": "BELT", "STÓŁ": "BED"}.get(bl.upper(), bl.upper()), 120, lambda: self.heater_dialog("heater_bed", bl, [0, 60, 70, 80, 90, 100, 110], 130))
        self.hx_ch = HexGauge("CHAMBER", 60)
        hexes = Gtk.Box(spacing=4, homogeneous=True)
        for h in (self.hx_noz, self.hx_bed, self.hx_ch):
            hexes.pack_start(h, True, True, 0)
        sv = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        sv.pack_start(self.schem, True, True, 0)
        sv.pack_start(hexes, False, False, 0)
        self.pack_start(window("SCHEMATIC VIEW", sv, "R.00"), True, True, 0)
        self.t_nozzle.title.set_label("NOZZLE")
        self.t_nozzle.sub.set_no_show_all(True)
        self.t_nozzle.sub.hide()
        self.t_light.title.set_label("LIGHTS")
        tele = Gtk.Grid(column_homogeneous=True, column_spacing=5, row_spacing=5)
        tele.attach(self.t_nozzle, 0, 0, 1, 1)
        tele.attach(self.t_light, 1, 0, 1, 1)
        self.pack_start(window("TELEMETRY", tele, "R.03"), False, False, 0)

        # szpula: ile filamentu zostało (agent odejmuje zużycie); dotknięcie → ustaw / reset
        self.sz_btn = Gtk.Button(label="FILAMENT · spool level unknown")
        self.sz_btn.get_style_context().add_class("revo_spool")
        self.sz_btn.connect("clicked", lambda *a: self.screen.show_panel("revo_szpula", "Szpula", panel_name="revo_szpula_s", mode="szpula"))
        self.pack_start(self.sz_btn, False, False, 0)
        # operator (gdy kierownik założył operatorów): kto pracuje na maszynie
        self.op_btn = Gtk.Button(label="")
        self.op_btn.get_style_context().add_class("revo_spool")
        self.op_btn.set_no_show_all(True)
        self.op_btn.connect("clicked", lambda *a: self.screen.show_panel("revo_operator", "Operator"))
        self.pack_start(self.op_btn, False, False, 0)
        # licencja: pasek tylko gdy trzeba działać (okres próbny / blokada)
        self.lic_btn = Gtk.Button(label="")
        self.lic_btn.get_style_context().add_class("revo_spool")
        self.lic_btn.set_no_show_all(True)
        self.lic_btn.connect("clicked", lambda *a: self.screen.show_panel("revo_licencja", "Licencja"))
        self.pack_start(self.lic_btn, False, False, 0)
        self._op_asked = False
        self.szpula = None
        self.system = None

        druk = Gtk.Button(label="ROZPOCZNIJ DRUK")
        druk.get_style_context().add_class("revo_print")
        druk.connect("clicked", lambda *a: self.p.menu_item_clicked(None, {"panel": "revo_files", "name": "Pliki"}))
        self.pack_start(druk, False, False, 0)

        pre = Gtk.Grid(column_homogeneous=True, column_spacing=8)
        for i, (name, e, b) in enumerate(PRESETS):
            bt = Gtk.Button(label=name)
            bt.get_style_context().add_class("revo_preset")
            bt.connect("clicked", self.preheat, e, b)
            pre.attach(bt, i, 0, 1, 1)
        cool = Gtk.Button(label="Wyłącz\ngrzanie")
        cool.get_child().set_justify(Gtk.Justification.CENTER)
        cool.get_style_context().add_class("revo_preset")
        cool.connect("clicked", self.preheat, 0, 0)
        pre.attach(cool, 3, 0, 1, 1)
        self.pack_start(pre, False, False, 0)

        nav = Gtk.Grid(column_homogeneous=True, column_spacing=4)
        items = [("spool", "Filament", lambda: self.p.menu_item_clicked(None, {"panel": "revo_filament", "name": "Filament"})),
                 ("extruder", "Dysza", self.nozzle_dialog),
                 ("file", "Pliki", lambda: self.p.menu_item_clicked(None, {"panel": "revo_files", "name": "Pliki"})),
                 ("settings", "Menu", self.open_menu)]
        for i, (icon, name, cb) in enumerate(items):
            bt = self.p._gtk.Button(icon, name, None, 0.9)
            bt.get_style_context().add_class("revo_nav")
            bt.connect("clicked", lambda w, c=cb: c())
            nav.attach(bt, i, 0, 1, 1)
        self.pack_start(nav, False, False, 0)

        self._timer = None
        self._asked = False

    # --- akcje ---
    def selftest(self):
        self.gcode("REVO_SELFTEST")

    def open_menu(self):
        self.screen.show_panel("menu", title="Menu", panel_name="revo_menu",
                               items=self.screen._config.get_menu_items("__main"))

    # --- odświeżanie ---
    def first_run_pending(self):
        vars_ = self.printer.get_stat("save_variables", "variables") or {}
        return "revo_first_run_done" not in vars_ and self.printer.get_stat("save_variables") is not None

    def start(self):
        # nowa maszyna: kreator pierwszego uruchomienia (raz na sesję ekranu, do zapisania revo_first_run_done)
        if self.first_run_pending() and not getattr(self.screen, "_revo_wizard_shown", False):
            self.screen._revo_wizard_shown = True
            GLib.idle_add(lambda: self.screen.show_panel("revo_wizard", "Pierwsze uruchomienie") and False)
        if self._timer is None:
            self.refresh()
            self._timer = GLib.timeout_add_seconds(1, self.refresh)
            self._poll_agent()
            GLib.timeout_add_seconds(60, self._poll_agent)

    def stop(self):
        if self._timer:
            GLib.source_remove(self._timer)
            self._timer = None

    def _poll_agent(self):
        def run():
            code, st = agent.call("/status", timeout=1)
            if code == 200:
                GLib.idle_add(self._set_hours, st.get("hours"))
                self.szpula = st.get("szpula")
                GLib.idle_add(self._set_operator, st.get("operatorzy") or [], st.get("operator"))
                self.system = st.get("system")
                GLib.idle_add(self._consent_check, st)
            code, lic = agent.call("/licencja", timeout=1)
            if code == 200:
                GLib.idle_add(self._set_lic, lic)
        threading.Thread(target=run, daemon=True).start()
        return self._timer is not None

    def _set_lic(self, lic):
        ctx = self.lic_btn.get_style_context()
        for c in ("revo_lic_proba", "revo_lic_blok"):
            ctx.remove_class(c)
        if lic.get("stan") == "proba":
            d = lic.get("dni") or 0
            self.lic_btn.set_label(f"ACTIVATE LICENSE · {d} {'dzień' if d == 1 else 'dni'} do blokady")
            ctx.add_class("revo_lic_proba")
        elif lic.get("stan") == "blokada":
            self.lic_btn.set_label("MASZYNA ZABLOKOWANA · WPISZ NUMER LICENCJI")
            ctx.add_class("revo_lic_blok")
        else:
            self.lic_btn.hide()
            return False
        self.lic_btn.show()
        return False

    def _set_operator(self, ops, cur):
        if not ops:
            self.op_btn.hide()
            return False
        self.op_btn.set_label(f"OPERATOR · {cur['imie']}" if cur else "ZALOGUJ OPERATORA")
        self.op_btn.show()
        # nikt nie zalogowany: raz zaproponuj logowanie (bez blokowania – druk i STOP działają zawsze)
        cp = getattr(self.screen, "_cur_panels", [])
        ss = getattr(self.screen, "screensaver", None)
        if ss is not None and ss.is_showing:
            return False   # przy wygaszaczu nie otwieraj nic w tle – zapytamy po wybudzeniu
        if not cur and not self._op_asked and cp and cp[-1] == "main_menu":
            self._op_asked = True
            self.screen.show_panel("revo_operator", "Operator")
        if cur:
            self._op_asked = False
        return False

    def _consent_check(self, st):
        """Powitanie: pierwsze uruchomienie – pytanie o zgody (alerty ON, statystyki OFF)."""
        if self._asked or st.get("consent", {}).get("asked", True) or self.first_run_pending():
            return False
        self._asked = True
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        box.get_style_context().add_class("revo_home")
        box.pack_start(_lbl("WITAJ W REVO OS", "revo_state", 0.5), False, False, 6)
        t = _lbl("Maszyna może wysyłać do Revotech informacje, które pomagają szybciej reagować na usterki. "
                 "Możesz to zmienić później w Menu.", "revo_splash_text", 0.0)
        t.set_line_wrap(True)
        box.pack_start(t, False, False, 0)
        self._sw = {}
        for key, title, desc, default in (
                ("alerts", "Alerty o błędach", "Gdy maszyna zgłosi błąd lub 3 nieudane wydruki z rzędu, serwis dostaje powiadomienie.", True),
                ("stats", "Statystyki (dobrowolnie)", "Przebieg oraz liczba udanych i nieudanych wydruków tej maszyny – pomagają nam ulepszać maszyny.", False)):
            row = Gtk.Box(spacing=12)
            col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            col.add(_lbl(title, "revo_tile_value_small"))
            d = _lbl(desc, "revo_info")
            d.set_line_wrap(True)
            col.add(d)
            sw = Gtk.Switch(active=default, valign=Gtk.Align.CENTER)
            self._sw[key] = sw
            row.pack_start(col, True, True, 0)
            row.pack_end(sw, False, False, 0)
            box.pack_start(row, False, False, 6)
        buttons = [{"name": "Save", "response": Gtk.ResponseType.OK, "style": "dialog-primary"}]
        self.p._gtk.Dialog("Powitanie", buttons, box, self._consent_resp)
        return False

    def _consent_resp(self, dialog, resp):
        body = {k: sw.get_active() for k, sw in self._sw.items()}
        self.p._gtk.remove_dialog(dialog)
        threading.Thread(target=agent.call, args=("/zgody", body), daemon=True).start()

    def _set_hours(self, h):
        self.hours = h
        return False

    def refresh(self):
        try:
            v = logic.view(self.printer, self.hours)
            self.state_lbl.set_label(v["state"])
            ctx = self.state_lbl.get_style_context()
            for c in ("revo_ok", "revo_warn", "revo_err"):
                ctx.remove_class(c)
            ctx.add_class(v["state_class"])
            sysv = (self.system or {}).get("revo_os")
            self.info_lbl.set_label(v["info"] + (f" · Revo OS {sysv}" if sysv and sysv != "?" else ""))
            self.t_nozzle.value.set_label(v["nozzle_size"])
            self.t_nozzle.sub.set_label(v["nozzle_temp"])
            self.t_bed.value.set_label(v["bed_temp"])
            self.t_chamber.value.set_label(v["chamber_temp"])
            num = lambda o, k: (lambda x: float(x) if isinstance(x, (int, float)) else None)((self.printer.get_stat(o) or {}).get(k))
            self.hx_noz.set(num("extruder", "temperature"), num("extruder", "target"))
            self.hx_bed.set(num("heater_bed", "temperature"), num("heater_bed", "target"))
            ch = logic.cfg(self.printer, "chamber", "temperature_sensor chamber")
            self.hx_ch.set(num(ch, "temperature"), None)
            self.t_light.value.set_label(v["light"])
            from ks_includes import revo_live
            self.live_btn.set_visible(revo_live.active())
            if self.szpula is not None:
                from ks_includes import revo_filament_logic as fl
                f = fl.fraction(self.szpula)
                self.sz_btn.set_label("FILAMENT · " + fl.label(self.szpula) + (f"  ({f * 100:.0f}%)" if f is not None else ""))
                ctx = self.sz_btn.get_style_context()
                (ctx.add_class if f is not None and f < 0.1 else ctx.remove_class)("revo_spool_low")
            vars_ = self.printer.get_stat("save_variables", "variables") or {}
            lock = rl.settings(vars_)
            want = lock["min"] * 60 if lock["on"] else 0
            if self.screen.lock_screen.autolock_time != want:   # blokada ekranu z ustawień klienta
                self.screen.lock_screen.set_autolock_timeout(want)
            txt = serwis.banner(serwis.status(self.hours, vars_, logic.is_belt(self.printer)))
            self.serwis_btn.set_label(txt + "  ›" if txt else "")
            self.serwis_btn.set_visible(bool(txt))
            self.schem.light = v["light_on"]
            self.schem.queue_draw()
        except Exception as e:
            logging.debug(f"RevoHome: {e}")
        return self._timer is not None


def orionize(box, first_title=None, first_code="", skip=()):
    """OrionUI: przebudowuje pionowy box panelu na okna z paskiem ■ – nowe okno zaczyna się na każdej etykiecie
    sekcji (klasa revo_tile_title), elementy przed pierwszą etykietą trafiają do okna first_title (jeśli podane).
    Widżety z `skip` (np. E-STOP, dolne przyciski) zostają poza oknami."""
    kids = box.get_children()
    packing = {c: box.query_child_packing(c) for c in kids}
    groups, cur = [], None
    if first_title:
        cur = (first_title, first_code, [])
        groups.append(cur)
    for c in kids:
        if c in skip:
            groups.append((None, None, [c]))
            cur = None
            continue
        if isinstance(c, Gtk.Label) and (c.get_style_context().has_class("revo_tile_title") or c.get_style_context().has_class("revo_test_name")):
            cur = (c.get_label(), "", [])
            groups.append(cur)
            box.remove(c)
            continue
        if cur is None:
            groups.append((None, None, [c]))
        else:
            cur[2].append(c)
    for c in kids:
        if c.get_parent() is box:
            box.remove(c)
    for title, code, ws in groups:
        if title is None:
            for w in ws:
                exp, fill, pad, pt = packing[w]
                (box.pack_end if pt == Gtk.PackType.END else box.pack_start)(w, exp, fill, pad)
            continue
        if not ws:
            continue
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        for m in (inner.set_margin_start, inner.set_margin_end, inner.set_margin_top, inner.set_margin_bottom):
            m(6)
        expand = False
        for w in ws:
            exp, fill, pad, pt = packing[w]
            expand = expand or exp
            inner.pack_start(w, exp, fill, pad)
        box.pack_start(window(title.upper(), inner, code), expand, True, 0)
    box.show_all()
    return box
