from ks_includes import revo_i18n as I


def test_translate():
    assert I.load("en")
    assert I.tr("GOTOWA") == "READY"
    assert I.tr("  DZIAŁA ") == "  WORKS "
    assert I.tr("KROK 5 / 27") == "STEP 5 / 27"
    assert I.tr("Czas druku 1 h 05 min · filament 3.2 m") == "Print time 1 h 05 min · filament 3.2 m"
    assert I.tr("coś nieznanego") == "coś nieznanego"
    I.load("pl")
    assert I.tr("GOTOWA") == "GOTOWA"
