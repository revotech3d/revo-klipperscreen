# Revo OS – wytłaczanie objętościowe (bez GTK, testowalne)
import math

FIL_AREA = math.pi * (1.75 / 2) ** 2          # mm² dla filamentu 1,75 mm
NOZZLE_MAX = {0.25: 8, 0.4: 25, 0.6: 45, 0.8: 60}  # mm³/s, mosiądz – wartości startowe
MAX_MOVE = 45.0                                 # Klipper: max_extrude_only_distance 50 mm


def flow_limit(diameter):
    try:
        return NOZZLE_MAX.get(round(float(diameter), 2), 25)
    except (TypeError, ValueError):
        return 25


def extrude_script(flow, seconds):
    """Wytłoczenie flow [mm³/s] przez seconds [s] → G-code, podzielony na ruchy ≤ MAX_MOVE."""
    length = flow * seconds / FIL_AREA
    feed = flow / FIL_AREA * 60
    n = max(1, math.ceil(length / MAX_MOVE))
    part = length / n
    return "\n".join([f"G1 E{part:.2f} F{feed:.0f}"] * n)
