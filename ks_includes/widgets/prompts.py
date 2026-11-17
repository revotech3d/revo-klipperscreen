import logging

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gtk, Pango


class Prompt:
    def __init__(self, screen):
        self.screen = screen
        self.gtk = screen.gtk
        self.window_title = "KlipperScreen"
        self.text = self.header = ""
        self.buttons = []
        self.id = 1
        self.prompt = None
        self.scroll_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
        )
        self.groups = []

    def _key_press_event(self, widget, event):
        keyval_name = Gdk.keyval_name(event.keyval)
        if keyval_name in ["Escape", "BackSpace"]:
            self.close()

    def decode(self, data):
        logging.info(f"{data}")
        if data.startswith("prompt_begin"):
            self.header = data.replace("prompt_begin", "")
            if self.header:
                self.window_title = self.header
            self.text = ""
            self.buttons = []
            return
        elif data.startswith("prompt_text"):
            self.text = data.replace("prompt_text ", "")
            return
        elif data.startswith("prompt_button "):
            data = data.replace("prompt_button ", "")
            params = data.split("|")
            if len(params) == 1:
                params.append(self.text)
            if len(params) > 3:
                logging.error("Unexpected number of parameters on the button")
                return
            self.set_button(*params)
            return
        elif data.startswith("prompt_footer_button"):
            data = data.replace("prompt_footer_button ", "")
            params = data.split("|")
            if len(params) == 1:
                params.append(self.text)
            if len(params) > 3:
                logging.error("Unexpected number of parameters on the button")
                return
            self.set_footer_button(*params)
            return
        elif data == "prompt_show":
            if not self.prompt:
                self.show()
            return
        elif data == "prompt_end":
            self.end()
        elif data == "prompt_button_group_start":
            self.groups.append(
                Gtk.FlowBox(
                    selection_mode=Gtk.SelectionMode.NONE,
                    orientation=Gtk.Orientation.HORIZONTAL,
                )
            )
        elif data == "prompt_button_group_end":
            if self.groups:
                self.scroll_box.add(self.groups.pop())
        else:
            logging.debug(f"Unknown option {data}")

    def set_button(self, name, gcode, style="default"):
        button = self.gtk.Button(image_name=None, label=f"{name}", style=f"dialog-{style}")
        button.connect(
            "clicked", self.screen._send_action, "printer.gcode.script", {"script": gcode}
        )
        if self.groups:
            self.groups[-1].add(button)
            # Workaround to expand the buttons horizontally
            max_childs = len(self.groups[-1].get_children())
            self.groups[-1].set_max_children_per_line(min(4, max_childs))
            self.groups[-1].set_min_children_per_line(min(4, max_childs))
        else:
            self.scroll_box.add(button)

    def set_footer_button(self, name, gcode, style="default"):
        self.buttons.append(
            {"name": name, "response": self.id, "gcode": gcode, "style": f"dialog-{style}"}
        )
        self.id += 1

    def _revo_help(self, code):
        """WHAT TO DO for a REVO code from Revo Panel's code list (revo-config web/kody.json)."""
        import json
        import os
        for path in ("~/revo-config/web/kody.json",):
            try:
                with open(os.path.expanduser(path), encoding="utf-8") as f:
                    for k in json.load(f).get("kody", []):
                        if k.get("kod") == code:
                            return k.get("rozwiazanie_en", "")
            except (OSError, ValueError):
                pass
        return ""

    def _revo_show(self):
        """Revo OS look (like the stop screen): ACTION REQUIRED, code, title, question, what to do, answers."""
        import re
        m = re.match(r"\s*(REVO-\d{4})\s*·\s*(.*)$", self.header or "")
        code, title = (m.group(1), m.group(2)) if m else ("", self.header.strip())
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, vexpand=True)
        box.get_style_context().add_class("revo_prompt")

        def lab(text, cls, wrap=True):
            lb = Gtk.Label(label=text, wrap=wrap, xalign=0, halign=Gtk.Align.FILL)
            lb.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
            lb.get_style_context().add_class(cls)
            box.pack_start(lb, False, False, 0)
            return lb

        lab("■  ACTION REQUIRED · THE MACHINE IS WAITING", "revo_stop_head")
        if code:
            lab(code, "revo_prompt_code")
        lab(title.upper(), "revo_prompt_title")
        if self.text:
            lab(self.text, "revo_prompt_q")
        helptext = self._revo_help(code) if code else ""
        if helptext:
            lab("WHAT TO DO", "revo_stop_head")
            lab(helptext, "revo_stop_detail")
        if self.scroll_box.get_children():   # buttons sent with prompt_button (rare) – below the text
            box.pack_start(self.scroll_box, False, False, 0)
        box.pack_start(Gtk.Box(vexpand=True), True, True, 0)

        self.prompt = self.gtk.Dialog(self.window_title, self.buttons, box, self.response)
        self.prompt.get_style_context().add_class("revo_prompt_dialog")
        for b in self.buttons:   # answers: normal height, capitals, Revo colours (classes from the macro's style)
            w = self.prompt.get_widget_for_response(b["response"])
            if w is not None:
                w.set_size_request(int(self.screen.width * 0.92 / max(1, len(self.buttons))) - 12, 72)
                w.set_label(b["name"].upper())
        self.prompt.connect("key-press-event", self._key_press_event)
        self.prompt.connect("delete-event", self.close)
        self.screen.screensaver.close()

    def show(self):
        logging.info(f"Prompt {self.header} {self.text} {self.buttons}")
        if self.screen._config.get_main_config().get("theme", "") == "revo":
            self._revo_show()
            return

        title = Gtk.Label(
            wrap=True, hexpand=True, vexpand=False, halign=Gtk.Align.CENTER, label=self.header
        )

        close = self.gtk.Button("cancel", scale=self.gtk.bsidescale)
        close.set_hexpand(False)
        close.set_vexpand(False)
        close.connect("clicked", self.close)

        label = Gtk.Label(label=self.text, wrap=True, hexpand=True, vexpand=True)
        label.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        label.get_style_context().add_class("prompt")

        self.scroll_box.add(label)
        self.scroll_box.reorder_child(label, 0)

        scroll = self.gtk.ScrolledWindow(steppers=False)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.add(self.scroll_box)

        content = Gtk.Grid()
        if not self.screen.windowed:
            content.attach(title, 0, 0, 1, 1)
            content.attach(close, 1, 0, 1, 1)
        content.attach(scroll, 0, 1, 2, 1)

        self.prompt = self.gtk.Dialog(
            self.window_title,
            self.buttons,
            content,
            self.response,
        )
        self.prompt.connect("key-press-event", self._key_press_event)
        self.prompt.connect("delete-event", self.close)
        self.screen.screensaver.close()

    def response(self, dialog, response_id):
        for button in self.buttons:
            if button["response"] == response_id:
                self.screen._send_action(None, "printer.gcode.script", {"script": button["gcode"]})

    def close(self, *args):
        script = {"script": 'RESPOND type="command" msg="action:prompt_end"'}
        self.screen._send_action(None, "printer.gcode.script", script)

    def end(self):
        if self.prompt is not None:
            self.gtk.remove_dialog(self.prompt)
        self.prompt = None
        self.screen.prompt = None
