# Revo OS – przyciski "przytrzymaj": powtarzanie akcji dopóki palec jest na ekranie.
import time

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib


def hold_steps(held_s):
    """Krok zmiany w zależności od czasu przytrzymania: 1° → 5° → 10°."""
    if held_s < 1.5:
        return 1
    if held_s < 3.5:
        return 5
    return 10


class Hold:
    """Podpina do przycisku: on_tick(sekundy_przytrzymania) wołane od razu i potem co `every` ms
    (pierwsze powtórzenie po `delay` ms), on_release() po puszczeniu."""

    def __init__(self, button, on_tick, on_release=None, delay=400, every=90):
        self.b, self.on_tick, self.on_release = button, on_tick, on_release
        self.delay, self.every = delay, every
        self.src, self.t0 = None, 0.0
        button.connect("pressed", self._press)
        button.connect("released", self._release)
        button.connect("leave-notify-event", lambda *a: self._release(None))

    def _press(self, *a):
        self._stop()
        self.t0 = time.monotonic()
        self.on_tick(0.0)
        self.src = GLib.timeout_add(self.delay, self._first)

    def _first(self):
        self.on_tick(time.monotonic() - self.t0)
        self.src = GLib.timeout_add(self.every, self._tick)
        return False

    def _tick(self):
        self.on_tick(time.monotonic() - self.t0)
        return True

    def _stop(self):
        if self.src:
            GLib.source_remove(self.src)
            self.src = None

    def _release(self, *a):
        was = self.src is not None
        self._stop()
        if was and self.on_release:
            self.on_release()


class BeltHold:
    """Pas jedzie do przodu dopóki przycisk jest wciśnięty (porcje po 10 mm co 0,25 s, 40 mm/s)."""

    STEP, SPEED, EVERY = 10, 40, 250

    def __init__(self, button, send, belt_name):
        self.send, self.belt, self.pos = send, belt_name, 0
        self.hold = Hold(button, self._tick, self._release, delay=self.EVERY, every=self.EVERY)

    def _tick(self, held):
        name = self.belt() if callable(self.belt) else self.belt
        if not name:
            return
        if held == 0.0:
            self.pos = 0
            self.send(f"MANUAL_STEPPER STEPPER={name} SET_POSITION=0")
        self.pos += self.STEP
        self.send(f"MANUAL_STEPPER STEPPER={name} MOVE={self.pos} SPEED={self.SPEED} SYNC=0")

    def _release(self):
        pass
