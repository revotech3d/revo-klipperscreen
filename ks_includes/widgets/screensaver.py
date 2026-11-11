import logging

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, GLib, Gtk


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
        logging.info("Showing Screensaver")
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

        # Revo OS: zamiast przycisku – EventBox na cały ekran, a budzenie podpięte też do okna,
        # żeby dotyk zawsze odblokował ekran, nawet gdy widżet wygaszacza nie dostanie zdarzenia
        close = Gtk.EventBox()
        close.set_above_child(True)
        close.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.TOUCH_MASK)
        close.connect("button-press-event", lambda *a: self.close() or True)
        close.connect("touch-event", lambda *a: self.close() or True)
        self._wake_ids = [self.screen.connect(sig, lambda *a: self.close() or False)
                          for sig in ("button-press-event", "touch-event", "key-press-event")]
        if self.config.get_main_config().get("theme", "") == "revo":
            try:
                self._revo_status(close)
            except Exception as e:  # wygaszacz nigdy nie może wywrócić ekranu
                logging.exception(e)

        box = Gtk.Box(
            halign=Gtk.Align.CENTER,
            width_request=self.screen.width,
            height_request=self.screen.height,
        )
        box.pack_start(close, True, True, 0)
        box.get_style_context().add_class("screensaver")
        self.blackbox = box
        # Revo OS: zapamiętaj, co było widoczne – po wybudzeniu pokaż tylko to (nie odsłaniaj ukrytego pulpitu KlipperScreena)
        self._widoczne = [c for c in self.screen.overlay.get_children() if c.get_visible()]
        for child in self._widoczne:
            child.hide()
        self.screen.overlay.add(self.blackbox)

        # Avoid leaving a cursor-handle
        self.screen.gtk.set_cursor(False, window=self.screen.get_window())

        self.blackbox.show_all()
        self.screen.power_devices(
            None, self.config.get_main_config().get("screen_off_devices", ""), on=False
        )
        return False

    # ---- Revo OS: wygaszacz – przygaszony szkielet maszyny i logo Revo ----
    def _revo_status(self, button):
        import os
        from ks_includes import revo_home_logic as lg
        from ks_includes.widgets.revo_home import Schematic
        from ks_includes.widgets import revo_saver
        printer = self.screen.printer

        def schem():
            sch = Schematic(lg.machine_type(printer) if printer else "belt")
            sch.wire, sch.light, sch.alpha = True, False, 0.5
            return sch
        logo = os.path.join(os.path.dirname(__file__), "..", "..", "styles", "revo", "images", "revo-logo.png")
        widget, self._revo_stop = revo_saver.build(self.screen, schem, logo)
        button.add(widget)

    def close(self, widget=None):
        if not self.is_showing:
            return False
        logging.info("Closing Screensaver")
        for i in getattr(self, "_wake_ids", []):
            try:
                self.screen.disconnect(i)
            except Exception:
                pass
        self._wake_ids = []
        if getattr(self, "_revo_stop", None):
            self._revo_stop()
            self._revo_stop = None
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
        for child in getattr(self, "_widoczne", None) or self.screen.overlay.get_children():
            child.show()
        self._widoczne = []
        for dialog in self.screen.dialogs:
            logging.info(f"Restoring Dialog {dialog}")
            dialog.show()
        self.screen.lock_screen.relock()
        return False

    def set_wake_delay(self, time):
        self.delayed_seconds = int(time)
        logging.debug(f"Screensaver Wake delay set to {time}")
