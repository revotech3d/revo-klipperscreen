import logging

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk


class ScreenSaver:
    def __init__(self, screen):
        self.screen = screen
        self.printer = screen.printer
        self.config = screen._config
        self.screensaver_timeout = None
        self.blackbox = None
        self.delayed = None
        self.delayed_seconds = screen._config.get_main_config().getint("screensaver_wake_delay", 1)

    @property
    def is_showing(self):
        return self.blackbox is not None

    def reset_timeout(self, *args):
        if self.screensaver_timeout is not None:
            GLib.source_remove(self.screensaver_timeout)
            self.screensaver_timeout = None
        if self.printer and self.printer.state in ("printing", "paused"):
            use_screensaver = self.config.get_main_config().get("screen_blanking_printing") != "off"
        else:
            use_screensaver = self.config.get_main_config().get("screen_blanking") != "off"
        if use_screensaver:
            self.screensaver_timeout = GLib.timeout_add_seconds(
                self.screen.blanking_time, self.show
            )

    def show(self):
        self.screen.uninhibit_idle()
        if self.is_showing:
            logging.debug("Screensaver active")
            return
        logging.debug("Showing Screensaver")
        if self.screensaver_timeout is not None:
            GLib.source_remove(self.screensaver_timeout)
            self.screensaver_timeout = None
        if self.screen.blanking_time == 0:
            return False
        self.screen.remove_keyboard()
        self.screen.close_popup_message()
        for dialog in self.screen.dialogs:
            logging.debug("Hiding dialog")
            dialog.hide()

        close = Gtk.Button()
        close.connect("clicked", self.close)
        if self.config.get_main_config().get("theme", "") == "revo":
            self._revo_status(close)

        box = Gtk.Box(
            halign=Gtk.Align.CENTER,
            width_request=self.screen.width,
            height_request=self.screen.height,
        )
        box.pack_start(close, True, True, 0)
        box.get_style_context().add_class("screensaver")
        self.blackbox = box
        for child in self.screen.overlay.get_children():
            child.hide()
        self.screen.overlay.add(self.blackbox)

        # Avoid leaving a cursor-handle
        close.grab_focus()
        self.screen.gtk.set_cursor(False, window=self.screen.get_window())

        self.blackbox.show_all()
        self.screen.power_devices(
            None, self.config.get_main_config().get("screen_off_devices", ""), on=False
        )
        return False

    # ---- Revo OS: wygaszacz pokazuje przygaszony stan maszyny ----
    def _revo_status(self, button):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, valign=Gtk.Align.CENTER)
        self._rv = {k: Gtk.Label() for k in ("clock", "state", "temps", "hint")}
        for k, w in self._rv.items():
            w.get_style_context().add_class(f"revo_saver_{k}")
            box.pack_start(w, False, False, 0)
        self._rv["hint"].set_label("Dotknij, aby wybudzić")
        button.add(box)
        self._revo_tick()
        GLib.timeout_add_seconds(5, self._revo_tick)

    def _revo_tick(self):
        if not self.is_showing and getattr(self, "_rv", None) is None:
            return False
        try:
            import time as _t
            from ks_includes import revo_home_logic as lg
            v = lg.view(self.printer)
            st = v["state"]
            if st == "DRUKUJE":
                p = self.printer.get_stat("virtual_sdcard", "progress") or 0
                st += f"  {p * 100:.0f}%"
            self._rv["clock"].set_label(_t.strftime("%H:%M"))
            self._rv["state"].set_label(st)
            self._rv["temps"].set_label(f"Dysza {v['nozzle_temp']}   ·   {'Pas' if lg.is_belt(self.printer) else 'Stół'} {v['bed_temp']}")
        except Exception as e:  # wygaszacz nigdy nie może wywrócić ekranu
            logging.debug(f"revo saver: {e}")
        return self.is_showing

    def close(self, widget=None):
        if not self.is_showing:
            return False
        logging.debug("Closing Screensaver")
        if self.screen.use_dpms:
            self.screen.wake_screen()
        self.screen.gtk.set_cursor(self.screen.show_cursor, window=self.screen.get_window())
        self.screen.power_devices(
            None, self.config.get_main_config().get("screen_on_devices", ""), on=True
        )
        # Screens take a couple of seconds to wake, prevent mistouches during that period
        if self.delayed is None:
            self.delayed = GLib.timeout_add_seconds(self.delayed_seconds, self.delayed_wake)
        return False

    def delayed_wake(self):
        self.reset_timeout()
        self.screen.inhibit_idle()
        if self.delayed is not None:
            GLib.source_remove(self.delayed)
            self.delayed = None
        if not self.is_showing:
            return False
        self.screen.overlay.remove(self.blackbox)
        self.blackbox = None
        logging.debug("Closed Screensaver")
        for child in self.screen.overlay.get_children():
            child.show()
        for dialog in self.screen.dialogs:
            logging.info(f"Restoring Dialog {dialog}")
            dialog.show()
        self.screen.lock_screen.relock()
        return False

    def set_wake_delay(self, time):
        self.delayed_seconds = int(time)
        logging.debug(f"Screensaver Wake delay set to {time}")
