"""
Organiza la grilla del set GRAVITY-LIKE: nombres de sección por clip, colores por
familia y mapa HTML interactivo del arreglo.

Uso:
    PYTHONPATH=src:masterclasses/scripts python3 masterclasses/scripts/organize_gravity_grid.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ableton_live12_mcp.client import Live12Client  # noqa: E402

import organize_grid_and_export_html as og  # noqa: E402
from organize_grid_and_export_html import ABLETON_COLOR_HEX  # noqa: E402

OUT_HTML = "/Users/juancruz/ableton-live12-mcp/masterclasses/peak/space92_gravity_v3_map.html"

# (start_beat, end_beat, etiqueta corta, color de clip)
SECTIONS = [
    (0.0, 128.0, "INTRO", 14),
    (128.0, 256.0, "GROOVE", 15),
    (256.0, 336.0, "BREAKDOWN", 60),
    (336.0, 352.0, "BUILD", 55),
    (352.0, 356.0, "SILENCE", 69),
    (356.0, 484.0, "DROP 1", 11),
    (484.0, 500.0, "MINI BREAK", 58),
    (500.0, 564.0, "DROP 2", 19),
    (564.0, 806.0, "OUTRO", 49),
]

TRACKS = [
    (0, "LOW-END CHASSIS", 14, "Kick G1 (49Hz)",
     "Golpe fundamental en Sol (49 Hz). Dueño exclusivo del transiente del '1'."),
    (1, "LOW-END CHASSIS", 15, "K-B-B-B Rolling Sub",
     "Galope de 3 semicorcheas por negra (e, &, a). Nunca en el '1' (ahí está el kick)."),
    (2, "LOW-END CHASSIS", 16, "Rumble 125-360Hz",
     "Textura de caverna en medios-graves, con high-pass para no chocar con el sub."),
    (3, "HOOK & LEAD", 17, "Hook 92",
     "Motivo hipnótico de 4 negras en repetición exacta (firma Space 92)."),
    (4, "HOOK & LEAD", 60, "Hoover Anthem",
     "Supersaw de octavas que abre el filtro en el breakdown."),
    (5, "HOOK & LEAD", 49, "Dark Reese Drone",
     "Suelo grave del breakdown, con el kick fuera."),
    (6, "DRUMS", 10, "909 Closed Hat",
     "Hi-hats en semicorcheas, high-pass a ~3 kHz para que no muerda."),
    (7, "DRUMS", 12, "909 Open Hat",
     "Open hat en el contratiempo '&'."),
    (8, "DRUMS", 13, "909 Acid Ride",
     "Ride que sólo entra en el clímax."),
    (9, "DRUMS", 11, "Peak Clap",
     "Clap en el drop y el clímax."),
    (10, "BUILD & FX", 55, "Riser + Snare Roll",
     "Riser que corta en el compás 89 para dejar el silencio pre-drop."),
    (11, "BUILD & FX", 19, "Galope 1/8T",
     "Tresillos de corchea (firma Space 92) en el Drop 2."),
    (12, "ATMOS", 58, "Vocal Pad G3",
     "Colchón de aire para el breakdown y el mini-break."),
    (13, "BUILD & FX", 69, "Sub Impact",
     "Golpe de sub en cada impacto del drop."),
]


def section_for(beat: float) -> tuple[str, int]:
    for start, end, label, color in SECTIONS:
        if start <= beat < end:
            return label, color
    return "OUTRO", 49


def main() -> None:
    c = Live12Client()
    tracks_data = []

    for idx, group, color, clip_label, role in TRACKS:
        arr = c.call("live12_lom_get", {
            "target_path": f"song.tracks.{idx}", "property_name": "arrangement_clips",
        }).get("value", [])
        clips = []
        for j in range(len(arr)):
            p = f"song.tracks.{idx}.arrangement_clips.{j}"
            st = float(c.call("live12_lom_get", {"target_path": p, "property_name": "start_time"})["value"])
            et = float(c.call("live12_lom_get", {"target_path": p, "property_name": "end_time"})["value"])
            label, sec_color = section_for(st)
            base = os.path.splitext(clip_label)[0]
            name = f"[{label} c.{int(st // 4) + 1}] {base}"
            c.call("live12_lom_set", {"target_path": p, "property_name": "name", "value": name})
            c.call("live12_lom_set", {"target_path": p, "property_name": "color_index", "value": int(sec_color)})
            clips.append({
                "clip_index": j,
                "name": name,
                "start_beat": st,
                "end_beat": et,
                "start_bar": int(st // 4) + 1,
                "end_bar": int(round(et / 4)),
                "color_index": sec_color,
                "hex": ABLETON_COLOR_HEX.get(sec_color, "#00C8FF"),
            })
        tracks_data.append({
            "index": idx,
            "group": group,
            "name": c.call("live12_lom_get", {"target_path": f"song.tracks.{idx}", "property_name": "name"})["value"],
            "color": color,
            "hex": ABLETON_COLOR_HEX.get(color, "#00C8FF"),
            "role": role,
            "eq": "",
            "fader_db": "",
            "clip_label": clip_label,
            "clips": clips,
        })

    og.HTML_OUT_PATH = OUT_HTML
    og.build_interactive_html(tracks_data)
    print(f"GRAVITY GRILL ORGANIZED ({len(tracks_data)} tracks) & HTML EXPORTED TO: {OUT_HTML}")


if __name__ == "__main__":
    main()
