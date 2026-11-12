# Revo OS – pionowy, segmentowy pasek statusu przez całą wysokość ekranu
import logging
import threading

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

from ks_includes import revo_status as rs


class RevoStatusBar(Gtk.DrawingArea):
    WIDTH = 32  # = KlippyGtk.revo_bar_width
    GAP = 3

    def __init__(self, screen):
        super().__init__()
        self._screen = screen
        self.state = "offline"
        self.progress = 0.0
        self.service = False
        self.set_size_request(self.WIDTH, -1)
        self.set_vexpand(True)
        self.get_style_context().add_class("revo_statusbar")
        self.connect("draw", self._draw)
        GLib.timeout_add(500, self._tick)          # odśwież stan + miganie
        GLib.timeout_add_seconds(5, self._poll_agent)

    def _poll_agent(self):
        def run():
            active = rs.agent_service_active()
            GLib.idle_add(self._set_service, active)
        threading.Thread(target=run, daemon=True).start()
        return True

    def _set_service(self, active):
        self.service = active
        if self._screen.printer is not None:
            self._screen.printer.revo_service = active  # menu: opcje serwisowe tylko w trybie serwisowym
        return False

    def _tick(self):
        try:
            p = self._screen.printer
            if p is None:
                self.state = "offline"
            else:
                ps = p.get_stat("print_stats", "state") or "standby"
                progress = p.get_stat("virtual_sdcard", "progress") or 0.0
                heating = False
                if ps == "printing":
                    for dev in p.get_temp_devices():
                        target = p.get_stat(dev, "target") or 0
                        temp = p.get_stat(dev, "temperature") or 0
                        if target > 0 and temp < target - 5:
                            heating = True
                            break
                busy = (p.get_stat("idle_timeout", "state") or "") == "Printing" or getattr(p, "revo_calibrating", False)
                if p.state != "ready":
                    p.revo_calibrating = False
                self.state = rs.machine_state(p.state, ps, heating, self.service, busy)
                self.progress = progress
        except Exception as e:  # pasek nigdy nie może wywrócić ekranu
            logging.debug(f"RevoStatusBar: {e}")
        self.queue_draw()
        return True

    def _draw(self, widget, ctx):
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()
        ctx.set_source_rgb(0.024, 0.027, 0.031)
        ctx.paint()
        n = rs.SEGMENTS
        seg_h = (h - self.GAP * (n + 1)) / n
        (r, g, b), _ = rs.COLORS[self.state]
        lit = rs.lit_segments(self.state, self.progress, n)
        on = rs.blink_on(self.state)
        x = 6
        sw = w - 16  # 10 px odstępu od treści po prawej
        for i in range(n):
            # segmenty liczone od dołu
            y = h - self.GAP - (i + 1) * seg_h - i * self.GAP
            if i < lit and on:
                # poświata + jasny rdzeń
                ctx.set_source_rgba(r, g, b, 0.25)
                ctx.rectangle(x - 2, y - 1, sw + 4, seg_h + 2)
                ctx.fill()
                ctx.set_source_rgba(r, g, b, 1.0)
            else:
                ctx.set_source_rgba(0.137, 0.149, 0.169, 1.0)  # #23262B
            ctx.rectangle(x, y, sw, seg_h)
            ctx.fill()
            if i == lit - 1 and lit < n and on:
                # czoło postępu – jasna kreska
                ctx.set_source_rgba(0.6, 0.63, 0.66, 1.0)
                ctx.rectangle(x, y, sw, 2)
                ctx.fill()
        return False
