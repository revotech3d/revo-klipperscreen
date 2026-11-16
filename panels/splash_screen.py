import logging

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Pango

from ks_includes.functions import run_systemctl
from ks_includes.screen_panel import ScreenPanel


class Panel(ScreenPanel):
    def __init__(self, screen, title):
        super().__init__(screen, title)
        self.revo = self._config.get_main_config().get("theme", "") == "revo"
        if self.revo:
            # Revo OS: logotyp Revo3D nad komunikatem
            image = self._gtk.Image("revo-logo", self._gtk.content_width * 0.8, 120)
        else:
            image = self._gtk.Image(
                "klipper", self._gtk.content_width * 0.2, self._gtk.content_height * 0.5
            )
        self.labels["text"] = Gtk.Label(
            label=_("Initializing printer..."),
            wrap=True,
            wrap_mode=Pango.WrapMode.WORD_CHAR,
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER,
        )

        self.labels["menu"] = self._gtk.Button("settings", _("Menu"), "color4")
        self.labels["menu"].connect("clicked", self._screen._go_to_submenu, "")
        self.labels["restart"] = self._gtk.Button("refresh", _("Klipper Restart"), "color1")
        self.labels["restart"].connect("clicked", self.restart_klipper)
        self.labels["firmware_restart"] = self._gtk.Button(
            "refresh", _("Firmware Restart"), "color2"
        )
        self.labels["firmware_restart"].connect("clicked", self.firmware_restart)
        if self.revo:
            self.labels["firmware_restart"] = Gtk.Button(label="FULL RESTART")
            self.labels["firmware_restart"].get_style_context().add_class("revo_restart_blink")
            self.labels["firmware_restart"].set_size_request(-1, 96)
            self.labels["firmware_restart"].connect("clicked", self.firmware_restart)
        self.labels["restart_system"] = self._gtk.Button("refresh", _("System Restart"), "color1")
        if self.revo:
            self.labels["restart_system"] = Gtk.Button(label="SYSTEM REBOOT")
            self.labels["restart_system"].get_style_context().add_class("revo_preset")
            self.labels["restart_system"].set_size_request(-1, 60)
        self.labels["restart_system"].connect("clicked", self.reboot_poweroff, "reboot")
        self.labels["shutdown"] = self._gtk.Button("shutdown", _("System Shutdown"), "color2")
        self.labels["shutdown"].connect("clicked", self.reboot_poweroff, "shutdown")
        self.labels["retry"] = self._gtk.Button("load", _("Retry"), "color3")
        self.labels["retry"].connect("clicked", self.retry)

        self.labels["actions"] = Gtk.Box(hexpand=True, vexpand=False, homogeneous=True)

        scroll = self._gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.add(self.labels["text"])
        self._raw = scroll

        if self.revo:
            info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
            image.set_margin_top(16)
            self.labels["text"].get_style_context().add_class("revo_splash_text")
        else:
            info = Gtk.Box()
        info.pack_start(image, False, True, 8)
        if self.revo:
            # stop screen: plain-language title, reason, what to do, REVO code (revo_stop_logic)
            self.stop = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            self.stop.set_no_show_all(True)
            self.stop.set_margin_start(16)
            self.stop.set_margin_end(16)
            self.stop_lbl = {}
            for key, cls, head in (("title", "revo_stop_title", None),
                                   ("reason", "revo_stop_reason", "WHAT HAPPENED"),
                                   ("detail", "revo_stop_detail", "WHAT TO DO"),
                                   ("code", "revo_stop_code", None)):
                if head:
                    hl = Gtk.Label(label=head, xalign=0)
                    hl.get_style_context().add_class("revo_stop_head")
                    hl.show()
                    self.stop.pack_start(hl, False, False, 0)
                lb = Gtk.Label(wrap=True, wrap_mode=Pango.WrapMode.WORD_CHAR, xalign=0)
                lb.get_style_context().add_class(cls)
                lb.show()
                self.stop_lbl[key] = lb
                self.stop.pack_start(lb, False, False, 0)
            info.pack_start(self.stop, False, False, 8)
            tel = Gtk.Label(label="Revotech service: +48 512 960 411", halign=Gtk.Align.CENTER)
            tel.get_style_context().add_class("revo_info")
            info.pack_end(tel, False, False, 8)
        info.pack_end(scroll, True, True, 8)

        main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        main.pack_start(info, True, True, 8)
        main.pack_end(self.labels["actions"], False, False, 0)

        self.show_restart_buttons()

        self.content.add(main)

    def update_text(self, text):
        self.labels["text"].set_label(f"{text}")
        if self.revo:
            stopped = str(text).startswith(("Klipper has shutdown", "Klipper has encountered an error"))
            if stopped:
                from ks_includes import revo_stop_logic as sl
                belt = bool((self._printer.get_stat("gcode_macro _REVO_CFG") or {}).get("belt_stepper")) if self._printer else True
                d = sl.describe(text, belt)
                self.stop_lbl["title"].set_label(d["title"])
                self.stop_lbl["reason"].set_label(d["reason"])
                self.stop_lbl["detail"].set_label(d["detail"])
                self.stop_lbl["code"].set_label(d["code"] + (f" · Klipper: {d['klipper']}" if d["klipper"] else ""))
            self.stop.set_visible(stopped)
            self._raw.set_visible(not stopped)   # the raw Klipper text, replaced by the plain-language one
        self.show_restart_buttons()

    def clear_action_bar(self):
        for child in self.labels["actions"].get_children():
            if child not in self.labels.values():   # Revo: the row box holding two buttons
                for b in child.get_children():
                    child.remove(b)
            self.labels["actions"].remove(child)
        if self.revo:
            self.labels["actions"].set_orientation(Gtk.Orientation.HORIZONTAL)
            self.labels["actions"].set_homogeneous(True)

    def show_restart_buttons(self):
        self.clear_action_bar()
        if self.ks_printer_cfg is not None and self._screen.state.connected:
            power_devices = self.ks_printer_cfg.get("power_devices", "")
            if power_devices and self._printer and self._printer.get_power_devices():
                logging.info(f"Associated power devices: {power_devices}")
                self.add_power_button(power_devices)

        if self.revo and self._screen.state.initialized:
            # Revo OS: after a shutdown or an error only FIRMWARE_RESTART brings the boards back; it blinks
            self.labels["actions"].set_orientation(Gtk.Orientation.VERTICAL)
            self.labels["actions"].set_homogeneous(False)
            self.labels["actions"].add(self.labels["firmware_restart"])
            row = Gtk.Box(homogeneous=True)
            row.add(self.labels["restart_system"])
            row.add(self.labels["menu"])
            self.labels["actions"].add(row)
            self.labels["actions"].show_all()
            return
        if self._screen.state.initialized:
            self.labels["actions"].add(self.labels["restart"])
            self.labels["actions"].add(self.labels["firmware_restart"])
        else:
            self.labels["actions"].add(self.labels["restart_system"])
            self.labels["actions"].add(self.labels["shutdown"])
        self.labels["actions"].add(self.labels["menu"])
        if (
            self._screen.state.reinit_count > self._screen.MAX_RETRIES
            or self._screen.state.klippy_retry_count > self._screen.MAX_RETRIES
            or not self._screen.state.connecting
        ):
            self.labels["actions"].add(self.labels["retry"])
        self.labels["actions"].show_all()

    def add_power_button(self, powerdevs):
        self.labels["power"] = self._gtk.Button("shutdown", _("Power On Printer"), "color3")
        self.labels["power"].connect("clicked", self._screen.power_devices, powerdevs, True)
        self.check_power_status()
        self.labels["actions"].add(self.labels["power"])

    def activate(self):
        self.check_power_status()

    def check_power_status(self):
        if "power" not in self.labels:
            return
        devices = self._printer.get_power_devices()
        any_off = any(self._printer.get_power_device_status(device) == "off" for device in devices)
        self.labels["power"].set_sensitive(any_off)

    def firmware_restart(self, widget):
        self._screen._ws.api.restart_firmware()

    def restart_klipper(self, widget):
        self._screen._ws.api.restart()

    def retry(self, widget):
        logging.debug("User retrying connection")
        self._screen.state.reinit_count = 0
        self._screen.state.klippy_retry_count = 0
        self._screen._init_printer(_("Connecting to %s") % self._screen.state.printer_name)
        self.show_restart_buttons()

    def reboot_poweroff(self, widget, method):
        response = self.power_action_response(method)
        if response is not None:
            self.reboot_poweroff_confirm(None, response, method)
            return
        label = Gtk.Label(wrap=True, hexpand=True, vexpand=True)
        label.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        if method == "reboot":
            label.set_label(_("Are you sure you wish to reboot the system?"))
            title = _("Restart")
        else:
            label.set_label(_("Are you sure you wish to shutdown the system?"))
            title = _("Shutdown")
        buttons = [
            {
                "name": _("Host"),
                "response": Gtk.ResponseType.OK,
                "style": "dialog-info",
            },
            {
                "name": _("Cancel"),
                "response": Gtk.ResponseType.CANCEL,
                "style": "dialog-error",
            },
        ]
        if self._screen.state.connected:
            buttons.insert(
                1,
                {
                    "name": _("Printer"),
                    "response": Gtk.ResponseType.APPLY,
                    "style": "dialog-warning",
                },
            )
        self._gtk.Dialog(title, buttons, label, self.reboot_poweroff_confirm, method)

    def reboot_poweroff_confirm(self, dialog, response_id, method):
        if dialog is not None:
            self._gtk.remove_dialog(dialog)

        if response_id == Gtk.ResponseType.ACCEPT:
            self.reboot_poweroff_confirm(None, Gtk.ResponseType.APPLY, method)
            self.reboot_poweroff_confirm(None, Gtk.ResponseType.OK, method)
        elif response_id == Gtk.ResponseType.OK:
            if method == "reboot":
                ret, err = run_systemctl("reboot")
                if ret != 0:
                    self._screen.show_popup_message(
                        f"Failed to reboot host: {err if err else f'exit code {ret}'}"
                    )
            else:
                ret, err = run_systemctl("poweroff")
                if ret != 0:
                    self._screen.show_popup_message(
                        f"Failed to power off host: {err if err else f'exit code {ret}'}"
                    )
        elif response_id == Gtk.ResponseType.APPLY:
            if method == "reboot":
                self._screen._ws.send_method("machine.reboot")
            else:
                if self.ks_printer_cfg is not None and self._screen.state.connected:
                    power_devices = self.ks_printer_cfg.get("power_devices", "")
                    if power_devices and self._printer.get_power_devices():
                        logging.info(f"Turning off associated power devices: {power_devices}")
                        self._screen.power_devices(widget=None, devices=power_devices, on=False)
                self._screen._ws.send_method("machine.shutdown")
