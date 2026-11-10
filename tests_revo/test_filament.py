from ks_includes import revo_filament_logic as f


def test_swap_temp_and_label():
    assert f.swap_temp("PLA", "PETG") == 240 and f.swap_temp("PC", "PLA") == 280 and f.swap_temp(None, None) == 240
    assert f.label({"mat": "PETG", "zostalo_g": 823.4}) == "PETG · 823 g"
    assert f.label({"mat": "PLA", "zostalo_g": None}) == "PLA · stan szpuli nieznany"
    assert f.fraction({"zostalo_g": 250, "pelna_g": 1000}) == 0.25 and f.fraction({}) is None
