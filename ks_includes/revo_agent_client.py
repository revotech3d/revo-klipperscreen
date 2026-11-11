# Revo OS – klient lokalnego API agenta Revo (127.0.0.1:7130)
import json
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:7130"


def call(path, body=None, timeout=3):
    """Zwraca (kod, dane). Brak agenta = (0, {"message": ...})."""
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(BASE + path, data=data, method="POST" if body is not None else "GET",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode() or "{}")
        except ValueError:
            return e.code, {"message": f"Error {e.code}"}
    except Exception:
        return 0, {"message": "Revo agent is not responding."}


def strip_markdown(md):
    """Prosty markdown → tekst dla etykiety GTK (nagłówki, pogrubienia, tabele)."""
    out = []
    for line in md.splitlines():
        t = line.strip()
        if t.startswith("|") and set(t.replace("|", "").strip()) <= set("-: "):
            continue
        if t.startswith("|"):
            cells = [c.strip() for c in t.strip("|").split("|")]
            t = " · ".join(c for c in cells if c)
        while t.startswith("#"):
            t = t[1:]
        t = t.strip().replace("**", "").replace("`", "")
        if t.startswith("- "):
            t = "• " + t[2:]
        out.append(t)
    return "\n".join(out).strip()
