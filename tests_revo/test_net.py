from ks_includes import revo_net as n


def test_describe():
    assert n.describe("eth0", "192.168.0.38") == "LAN 192.168.0.38"
    assert n.describe("end0", "10.0.0.5") == "LAN 10.0.0.5"
    assert n.describe("wlan0", "192.168.0.40", 72) == "Wi‑Fi 72% 192.168.0.40"
    assert n.describe("", None) == "BRAK SIECI"
