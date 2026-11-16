# Revo OS – E-STOP trzymany: czerwone pole, wypełnia się podczas trzymania, po HOLD_S sekundach zatrzymanie awaryjne.
# Puszczenie przed czasem niczego nie robi. Wentylator hotendu zostaje włączony: [heater_fan] ma shutdown_speed 1.0.
import time

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

HOLD_S = 1.0


def hold_state(elapsed, hold=HOLD_S, done=False):
    """(fill 0..1, small text) for the time the button has been held."""
    if done:
        return 1.0, "STOPPED"
    if elapsed is None:
        return 0.0, f"HOLD {hold:g} S"
    left = max(1, int(hold - elapsed + 0.999))
    return min(1.0, max(0.0, elapsed / hold)), f"HOLD · {left} S"


class EStopHold(Gtk.Button):
    """E-STOP button: hold it HOLD_S seconds to call on_stop()."""

    def __init__(self, on_stop, hold=HOLD_S, width=136, height=48):
        super().__init__()
        self.on_stop, self.hold = on_stop, hold
        self.t0, self.done, self.src = None, False, None
        self.get_style_context().add_class("revo_estop_hold")
        self.set_tooltip_text("Emergency stop – hold for 1 second")
        self.set_size_request(width, height)
        self.da = Gtk.DrawingArea()
        self.da.connect("draw", self._draw)
        self.add(self.da)
        self.connect("pressed", self._down)
        self.connect("released", self._up)
        self.connect("leave-notify-event", lambda *a: self._up())

    def reset(self):
        """Machine is back (ready): the button can stop it again."""
        if self.done:
            self.done = False
            self.da.queue_draw()

    def _down(self, *a):
        if self.done or self.src:
            return
        self.t0 = time.monotonic()
        self.src = GLib.timeout_add(50, self._tick)
        self.da.queue_draw()

    def _up(self, *a):
        if self.src:
            GLib.source_remove(self.src)
            self.src = None
        self.t0 = None
        self.da.queue_draw()

    def _tick(self):
        if self.t0 is None:
            self.src = None
            return False
        if time.monotonic() - self.t0 >= self.hold:
            self.src, self.t0, self.done = None, None, True
            self.da.queue_draw()
            self.on_stop()
            return False
        self.da.queue_draw()
        return True

    def _draw(self, w, ctx):
        W, H = w.get_allocated_width(), w.get_allocated_height()
        elapsed = None if self.t0 is None else time.monotonic() - self.t0
        fill, sub = hold_state(elapsed, self.hold, self.done)
        ctx.set_source_rgb(0.227, 0.059, 0.071)                     # #3A0F12
        ctx.rectangle(0, 0, W, H)
        ctx.fill()
        ctx.set_source_rgb(1.0, 0.302, 0.322)                       # #FF4D52
        ctx.rectangle(0, 0, W * fill, H)
        ctx.fill()
        ctx.set_line_width(2)
        ctx.rectangle(1, 1, W - 2, H - 2)
        ctx.stroke()

        def text(s, size, y, rgb):
            ctx.select_font_face("Barlow Semi Condensed", 0, 1)
            ctx.set_font_size(size)
            ext = ctx.text_extents(s)
            ctx.set_source_rgb(*rgb)
            ctx.move_to((W - ext.width) / 2 - ext.x_bearing, y)
            ctx.show_text(s)
        text("E-STOP", 20, H * 0.56, (1, 1, 1))
        text(sub, 11, H * 0.85, (1.0, 0.89, 0.894))
