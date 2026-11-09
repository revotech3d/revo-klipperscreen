# Revo OS – angielska wersja ekranu Revo.
# Teksty Revo są pisane po polsku; gdy język ekranu to angielski, napisy etykiet i przycisków są
# tłumaczone w locie wspólnym słownikiem z Panelem Revo (revo-config/web/lang/en.json).
import json
import logging
import os
import re

PATHS = [os.path.expanduser("~/revo-config/web/lang/en.json"),
         os.path.join(os.path.dirname(__file__), "..", "styles", "revo", "lang_en.json")]
_on = False
_exact, _re = {}, []
_WS = re.compile(r"^(\s*)([\s\S]*?)(\s*)$")


def tr(text):
    """PL → EN (dokładne dopasowanie albo wzorzec). Bez zmian, gdy brak tłumaczenia lub język ≠ en."""
    if not _on or not isinstance(text, str) or not text.strip():
        return text
    a, k, b = _WS.match(text).groups()
    if k in _exact:
        return a + _exact[k] + b
    for pat, rep in _re:
        if pat.search(k):
            return a + pat.sub(rep, k) + b
    return text


def load(lang):
    global _on, _exact, _re
    _on = str(lang or "").lower().startswith("en")
    if not _on:
        return False
    for p in PATHS:
        if os.path.isfile(p):
            d = json.load(open(p, encoding="utf-8"))
            _exact = d.get("exact", {})
            _re = [(re.compile(pat), rep.replace("$", "\\")) for pat, rep in d.get("re", [])]
            logging.info(f"Revo i18n: EN z {p} ({len(_exact)} tekstów)")
            return True
    _on = False
    return False


def install(lang):
    """Podmienia napisy w Gtk.Label / Gtk.Button tworzonych i zmienianych przez panele."""
    if not load(lang):
        return
    from gi.repository import Gtk
    if getattr(Gtk.Label, "_revo_i18n", False):
        return
    for cls, setters in ((Gtk.Label, ("set_text", "set_label")), (Gtk.Button, ("set_label",))):
        for name in setters:
            orig = getattr(cls, name)
            setattr(cls, name, (lambda o: lambda self, t, *a: o(self, tr(t), *a))(orig))
        init = cls.__init__

        def _init(self, *args, _o=init, **kw):
            if "label" in kw:
                kw["label"] = tr(kw["label"])
            elif args and isinstance(args[0], str):
                args = (tr(args[0]),) + args[1:]
            _o(self, *args, **kw)
        cls.__init__ = _init
    Gtk.Label._revo_i18n = True
