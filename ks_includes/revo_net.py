# Revo OS – stan sieci do paska u góry: przez co maszyna jest połączona (LAN / Wi‑Fi) i jaki ma adres IP.
import socket


def default_iface():
    """Interfejs trasy domyślnej z /proc/net/route (bez zewnętrznych programów)."""
    try:
        with open("/proc/net/route") as f:
            for line in f.readlines()[1:]:
                p = line.split()
                if len(p) > 3 and p[1] == "00000000" and int(p[3], 16) & 2:
                    return p[0]
    except OSError:
        pass
    return None


def wifi_quality(iface):
    """Jakość Wi‑Fi 0–100 % z /proc/net/wireless (link quality /70)."""
    try:
        with open("/proc/net/wireless") as f:
            for line in f.readlines()[2:]:
                if line.split(":")[0].strip() == iface:
                    return max(0, min(100, round(float(line.split()[2].rstrip(".")) / 70 * 100)))
    except (OSError, ValueError, IndexError):
        pass
    return None


def local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return None


def describe(iface=None, ip=None, quality=None):
    """Tekst do paska, np. „LAN 192.168.0.38”, „Wi‑Fi 72% 192.168.0.40”, „BRAK SIECI”."""
    iface = iface if iface is not None else default_iface()
    if not iface:
        return "BRAK SIECI"
    ip = ip if ip is not None else local_ip()
    if iface.startswith(("wl", "wlan")):
        q = quality if quality is not None else wifi_quality(iface)
        kind = "Wi‑Fi" + (f" {q}%" if q is not None else "")
    elif iface.startswith(("eth", "en", "end")):
        kind = "LAN"
    elif iface.startswith(("usb", "rndis")):
        kind = "USB"
    else:
        kind = iface
    return f"{kind} {ip}" if ip else kind
