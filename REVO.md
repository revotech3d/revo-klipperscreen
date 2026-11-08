# Revo OS – KlipperScreen (fork Revotech)

Zmiany względem upstream KlipperScreen (AGPL-3.0):
- `styles/revo/` – motyw Revo (paleta: tło #0A0B0D, akcent #F0A04B, OK #4CC38A, błąd #FF4D52, serwis #5BA8FF).
- `ks_includes/revo_status.py` – logika stanu maszyny dla paska (bez GTK, testy w `tests_revo/`).
- `ks_includes/widgets/revo_statusbar.py` – pionowy pasek 40 segmentów przez całą wysokość ekranu:
  zielony = gotowa, biały = druk (postęp od dołu), bursztyn = nagrzewanie/pauza (pauza miga),
  czerwony migający = błąd, niebieski = tryb serwisowy (z agenta Revo, 127.0.0.1:7130).
- `panels/base_panel.py`, `ks_includes/KlippyGtk.py` – miejsce na pasek w układzie.
- `panels/job_status.py` – pierścień postępu w kolorach Revo.

W `KlipperScreen.conf`: `theme: revo`, `language: pl`.

Podgląd bez drukarki: `python tests_revo/fake_moonraker.py drukowanie` i KlipperScreen z `moonraker_port: 7125`.
