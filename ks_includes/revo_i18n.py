# Revo OS – angielska wersja ekranu Revo.
# Teksty Revo są pisane po polsku; gdy język ekranu to angielski, napisy etykiet i przycisków są
# tłumaczone w locie wspólnym słownikiem z Revo Panel (revo-config/web/lang/en.json).
import json
import logging
import os
import re

PATHS = [os.path.expanduser("~/revo-config/web/lang/en.json"),
         os.path.join(os.path.dirname(__file__), "..", "styles", "revo", "lang_en.json")]
_on = False
_exact, _re, _norm = {}, [], {}
_SP = re.compile(r"\s+")
_WS = re.compile(r"^(\s*)([\s\S]*?)(\s*)$")
_KOD = re.compile(r"^(REVO-\d{4} · )([\s\S]+)$")


def tr(text):
    """PL → EN (dokładne dopasowanie albo wzorzec). Bez zmian, gdy brak tłumaczenia lub język ≠ en."""
    if not _on or not isinstance(text, str) or not text.strip():
        return text
    a, k, b = _WS.match(text).groups()
    m = _KOD.match(k)
    if m:   # „REVO-0102 · tytuł” – kod zostaje, tytuł tłumaczony
        return a + m.group(1) + tr(m.group(2)) + b
    if k in _exact:
        return a + _exact[k] + b
    n = _SP.sub(" ", k)   # KlippyGtk.Button turns "\n" into spaces: "ZABLOKOWANE\n\ndotknij…" arrives as "ZABLOKOWANE  dotknij…"
    if n in _norm:
        return a + _norm[n] + b
    for pat, rep in _re:
        if pat.search(k):
            return a + pat.sub(rep, k) + b
    return text


def load(lang):
    """Both dictionaries together: the screen's own (styles/revo/lang_en.json) under Revo Panel's (revo-config),
    so a text the screen adds is translated even before revo-config ships it."""
    global _on, _exact, _re, _norm
    _on = str(lang or "").lower().startswith("en")
    if not _on:
        return False
    exact, pats, found = {}, [], []
    for p in reversed(PATHS):
        if os.path.isfile(p):
            d = json.load(open(p, encoding="utf-8"))
            exact.update(d.get("exact", {}))
            pats = d.get("re", []) + [x for x in pats if x not in d.get("re", [])]
            found.append(p)
    if not found:
        _on = False
        return False
    _exact = exact
    _re = [(re.compile(pat), rep.replace("$", "\\")) for pat, rep in pats]
    _norm = {_SP.sub(" ", k): v for k, v in exact.items()}
    logging.info(f"Revo i18n: EN z {found} ({len(_exact)} tekstów)")
    return True


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
