# Revo OS – sieć: stan połączenia (LAN / Wi-Fi, adres IP) i podłączenie do Wi-Fi w wyglądzie Revo.
# Zastępuje standardowy panel sieci KlipperScreena; korzysta z NetworkManagera (ks_includes/sdbus_nm.py).
import logging

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

from ks_includes import revo_net
from ks_includes.screen_panel import ScreenPanel
from ks_includes.widgets.revo_home import _lbl


def _btn(text, cb, cls="revo_t_plain", h=64):
    b = Gtk.Button(label=text)
    b.get_style_context().add_class(cls)
    b.set_size_request(-1, h)
    b.connect("clicked", lambda *a: cb())
    return b


class Panel(ScreenPanel):
    def __init__(self, screen, title, **kwargs):
        super().__init__(screen, title or "Sieć")
        self.nm = None
        self.timer = None
        self.wybrana = None
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.box.get_style_context().add_class("revo_home")
        self.content.add(self.box)
        self.box.pack_start(_lbl("SIEĆ", "revo_test_name"), False, False, 6)
        self.stan = _lbl("", "revo_state")
        self.stan.set_line_wrap(True)
        self.box.pack_start(self.stan, False, False, 0)
        self.info = _lbl("", "revo_test_desc")
        self.info.set_line_wrap(True)
        self.box.pack_start(self.info, False, False, 0)
        try:
            from ks_includes.sdbus_nm import SdbusNm
            self.nm = SdbusNm(self._popup)
        except Exception:   # brak NetworkManagera – pokaż sam stan
            logging.exception("Sieć: NetworkManager niedostępny")
        if not self.nm or not self.nm.wifi:
            self.info.set_text("Ta maszyna nie ma Wi-Fi – podłącz kabel sieciowy (LAN).")
            self._stan()
            return
        self.info.set_text("Dotknij sieć Wi-Fi, aby się połączyć. Najpewniejsze połączenie daje kabel LAN.")

        # formularz hasła (pokazywany po wybraniu nowej sieci)
        self.form = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.form_tytul = _lbl("", "revo_test_name")
        self.form.pack_start(self.form_tytul, False, False, 0)
        self.haslo = Gtk.Entry()
        self.haslo.set_placeholder_text("Hasło Wi-Fi")
        self.haslo.set_visibility(False)
        self.haslo.connect("button-press-event", self._screen.show_keyboard)
        self.haslo.connect("activate", lambda *a: self._polacz_nowa())
        self.form.pack_start(self.haslo, False, False, 0)
        row = Gtk.Box(spacing=8, homogeneous=True)
        row.pack_start(_btn("ANULUJ", self._lista), True, True, 0)
        row.pack_start(_btn("POŁĄCZ", self._polacz_nowa), True, True, 0)
        self.form.pack_start(row, False, False, 0)
        self.box.pack_start(self.form, False, False, 0)

        self.lista = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        scroll = self._gtk.ScrolledWindow()
        scroll.add(self.lista)
        scroll.set_vexpand(True)
        self.scroll = scroll
        self.box.pack_start(scroll, True, True, 0)
        self.dol = Gtk.Box(spacing=8, homogeneous=True)
        self.dol.pack_start(_btn("ODŚWIEŻ LISTĘ", self._skanuj), True, True, 0)
        self.zapomnij = _btn("ROZŁĄCZ I ZAPOMNIJ", self._zapomnij)
        self.dol.pack_start(self.zapomnij, True, True, 0)
        self.box.pack_start(self.dol, False, False, 0)
        self._lista()

    # ---------- widok ----------
    def activate(self):
        if self.nm and self.nm.wifi:
            self._skanuj()
            self.nm.set_connection_monitoring(True)
            self.timer = GLib.timeout_add_seconds(2, self._odswiez)
        else:
            self._stan()

    def deactivate(self):
        if self.timer:
            GLib.source_remove(self.timer)
            self.timer = None
        if self.nm:
            self.nm.set_connection_monitoring(False)

    def _popup(self, msg, level=3):
        self._screen.show_popup_message(msg, level)

    def _stan(self):
        txt = revo_net.describe()
        ssid = None
        if self.nm and self.nm.wifi:
            try:
                ap = self.nm.get_connected_ap()
                ssid = ap.ssid.decode("utf-8", errors="ignore") if ap else None
            except Exception:
                ssid = None
        self.stan.set_text(txt + (f"  ·  {ssid}" if ssid and "Wi" in txt else ""))
        self.polaczona = ssid
        return ssid

    def _odswiez(self):
        if self.nm:
            self.nm.monitor_connection_status()
        self._stan()
        return True

    def _lista(self):
        self.wybrana = None
        self._screen.remove_keyboard()
        self.form.hide()
        self.form.set_no_show_all(True)
        self.scroll.show()
        self.dol.show()
        self._wypelnij()

    def _wypelnij(self):
        for c in self.lista.get_children():
            self.lista.remove(c)
        ssid_teraz = self._stan()
        widziane = set()
        try:
            sieci = self.nm.get_networks()
        except Exception:
            logging.exception("Sieć: lista Wi-Fi")
            sieci = []
        for n in sieci:
            ssid = n["SSID"]
            if not ssid or ssid in widziane:
                continue
            widziane.add(ssid)
            znak = "✓  " if ssid == ssid_teraz else ""
            zamek = "  ·  hasło" if n.get("security") not in (None, "", "Open", "--") else ""
            zapis = "  ·  zapisana" if n.get("known") and ssid != ssid_teraz else ""
            b = _btn(f"{znak}{ssid}   {n.get('signal_level', 0)}%{zamek}{zapis}", lambda s=ssid, k=n.get("known"): self._wybierz(s, k), h=56)
            b.get_child().set_xalign(0.0)
            self.lista.pack_start(b, False, False, 0)
        if not widziane:
            self.lista.pack_start(_lbl("Nie widać żadnej sieci Wi-Fi. Dotknij ODŚWIEŻ LISTĘ.", "revo_test_desc"), False, False, 0)
        self.zapomnij.set_sensitive(bool(ssid_teraz))
        self.lista.show_all()
        return False

    # ---------- akcje ----------
    def _skanuj(self):
        try:
            self.nm.rescan()
        except Exception:
            logging.exception("Sieć: skanowanie")
        GLib.timeout_add_seconds(4, self._wypelnij)
        self._wypelnij()

    def _wybierz(self, ssid, known):
        if ssid == getattr(self, "polaczona", None):
            return
        if known:
            self.nm.connect(ssid)
            return
        sec = self.nm.get_security_type(ssid) or ""
        if "802.1x" in sec:
            self._popup("Ta sieć wymaga logowania firmowego (802.1X). Podłącz maszynę kablem LAN albo poproś serwis Revotech.", 2)
            return
        if sec in ("", "Open", "--"):
            r = self.nm.add_network(ssid, "")
            if "error" in r:
                self._popup(r.get("message", "Nie udało się dodać sieci."))
                return
            self.nm.connect(ssid)
            return
        self.wybrana = ssid
        self.form_tytul.set_text(f"WI-FI: {ssid}")
        self.haslo.set_text("")
        self.scroll.hide()
        self.dol.hide()
        self.form.set_no_show_all(False)
        self.form.show_all()
        self.haslo.grab_focus()
        self._screen.show_keyboard(entry=self.haslo)

    def _polacz_nowa(self):
        if not self.wybrana:
            return
        psk = self.haslo.get_text()
        if len(psk) < 8:
            self._popup("Hasło Wi-Fi ma co najmniej 8 znaków.", 2)
            return
        r = self.nm.add_network(self.wybrana, psk)
        if "error" in r:
            self._popup(r.get("message", "Nie udało się dodać sieci."))
            return
        self.nm.connect(self.wybrana)
        self._lista()

    def _zapomnij(self):
        ssid = getattr(self, "polaczona", None)
        if not ssid:
            return
        try:
            self.nm.disconnect_network()
            self.nm.delete_network(ssid)
        except Exception:
            logging.exception("Sieć: zapomnij")
        self._popup(f"Rozłączono i zapomniano sieć {ssid}.", 1)
        GLib.timeout_add_seconds(2, self._wypelnij)
