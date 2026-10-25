"""
Repara las cadenas de bus (returns + master) y los envíos (sends) del set vivo.

Problema que corrige: `configure_returns_and_master()` cargaba EQ/Reverb/Delay/Glue/Limiter
sin limpiar los dispositivos previos, así que cada corrida del builder apilaba otra copia
(hasta 4x) de la cadena de reverb, delay y master bus.

Este script:
  1. Deja UNA instancia activa de cada dispositivo de la cadena objetivo por bus
     (desactiva las duplicadas poniendo su parámetro "Device On" en 0).
  2. Configura los envíos a las reverb/delay con la API correcta (`sends` como dict).
  3. Reporta el antes/después.

Uso:
    PYTHONPATH=src python3 masterclasses/scripts/repair_bus_chains.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src"))

from ableton_live12_mcp.client import Live12Client  # noqa: E402

BUSES = [
    ("song.return_tracks.0", "A-DARK CLUB REVERB", ["EQ Eight", "Reverb"]),
    ("song.return_tracks.1", "B-PINGPONG ACID DELAY", ["EQ Eight", "Delay"]),
    ("song.master_track", "MASTER BUS", ["EQ Eight", "Glue Compressor", "Limiter"]),
]

# (track_index, send_A_reverb, send_B_delay)
SENDS = [
    (0, 0.00, 0.00),   # Kick
    (1, 0.00, 0.00),   # Rolling sub
    (2, 0.22, 0.00),   # Rumble
    (3, 0.18, 0.26),   # Hook
    (4, 0.34, 0.12),   # Hoover
    (5, 0.26, 0.00),   # Reese drone
    (6, 0.14, 0.10),   # Closed hats
    (7, 0.16, 0.12),   # Open hat
    (8, 0.20, 0.00),   # Acid ride
    (9, 0.24, 0.00),   # Clap
    (10, 0.22, 0.00),  # Riser
    (11, 0.12, 0.00),  # Gallop 1/8T
    (12, 0.38, 0.00),  # Vocal pad
    (13, 0.10, 0.00),  # Sub impact
]


def main() -> None:
    c = Live12Client()

    def g(path: str, prop: str = "value"):
        try:
            return c.call("live12_lom_get", {"target_path": path, "property_name": prop}).get("value")
        except Exception:
            return None

    for bus_path, label, wanted in BUSES:
        # La lista de dispositivos se pide al PADRE (propiedad "devices"); pedirla
        # sobre el propio vector devuelve "no attribute 'devices'".
        devices = g(bus_path, "devices") or []
        kept: dict[str, int] = {}
        disabled = 0
        for idx in range(len(devices)):
            name = g(f"{bus_path}.devices.{idx}", "name")
            if name is None:
                break
            if name in wanted and name not in kept:
                kept[name] = idx
                continue
            # Duplicada (o no deseada): se desactiva.
            if g(f"{bus_path}.devices.{idx}.parameters.0", "name") == "Device On":
                c.call("live12_lom_set", {
                    "target_path": f"{bus_path}.devices.{idx}.parameters.0",
                    "property_name": "value",
                    "value": 0.0,
                })
                disabled += 1
        total = len(kept) + disabled
        print(f"{label:<26} dispositivos: {total} -> activos {len(kept)} "
              f"({', '.join(f'{k}@{v}' for k, v in kept.items())}), desactivados {disabled}")

    for t_idx, send_a, send_b in SENDS:
        c.call("live12_mixer_set", {
            "track_index": t_idx,
            "sends": {"0": send_a, "1": send_b},
        })
    print("Sends aplicados: " + ", ".join(f"T{t}→A{a}/B{b}" for t, a, b in SENDS if a or b))

    print("\nVerificación (A=reverb, B=delay):")
    for t_idx in range(14):
        a = g(f"song.tracks.{t_idx}.mixer_device.sends.0", "value")
        b = g(f"song.tracks.{t_idx}.mixer_device.sends.1", "value")
        name = g(f"song.tracks.{t_idx}", "name")
        print(f"  {str(name)[:38]:38s} A={a if a is None else round(a, 2)}  B={b if b is None else round(b, 2)}")


if __name__ == "__main__":
    main()
