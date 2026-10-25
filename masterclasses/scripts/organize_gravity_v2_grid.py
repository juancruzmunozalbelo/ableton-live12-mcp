"""
Organiza la grilla del set "GRAVITY (VERIFIED)": nombres de sección por clip, colores
por familia y mapa HTML interactivo del arreglo (132 BPM / G menor / 6:06).

Uso:
    PYTHONPATH=src:masterclasses/scripts python3 masterclasses/scripts/organize_gravity_v2_grid.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ableton_live12_mcp.client import Live12Client  # noqa: E402

import organize_grid_and_export_html as og  # noqa: E402
from organize_grid_and_export_html import ABLETON_COLOR_HEX  # noqa: E402

from build_gravity_verified import (  # noqa: E402
    S1_INTRO, S2_GROOVE, S3_BREAKDOWN, S4_BUILD, S5_SILENCE,
    S6_DROP1, S7_MINIBREAK, S8_DROP2, S9_OUTRO,
)

OUT_HTML = "/Users/juancruz/ableton-live12-mcp/masterclasses/peak/space92_gravity_v2_map.html"

# (start, end, etiqueta, color de clip)
SECTIONS = [
    (S1_INTRO[0], S1_INTRO[1], "INTRO", 14),
    (S2_GROOVE[0], S2_GROOVE[1], "GROOVE", 15),
    (S3_BREAKDOWN[0], S3_BREAKDOWN[1], "BREAKDOWN", 60),
    (S4_BUILD[0], S4_BUILD[1], "BUILD", 55),
    (S5_SILENCE[0], S5_SILENCE[1], "SILENCE", 69),
    (S6_DROP1[0], S6_DROP1[1], "DROP 1", 11),
    (S7_MINIBREAK[0], S7_MINIBREAK[1], "MINI BREAK", 58),
    (S8_DROP2[0], S8_DROP2[1], "DROP 2", 19),
    (S9_OUTRO[0], S9_OUTRO[1], "OUTRO", 49),
]

TRACKS = [
    (0, "LOW-END", 14, "Kick G1 (49Hz)", "El bombo: dueño exclusivo del transiente del '1'."),
    (1, "LOW-END", 15, "K-B-B-B Rolling Sub", "El galope: 3 semicorcheas por negra, nunca en el '1'."),
    (2, "LOW-END", 16, "Rumble A", "Capa de rumble con color propio (Roar) y forma (EQ)."),
    (3, "LOW-END", 17, "Rumble B", "Segunda capa de rumble (otra fuente, otro color)."),
    (4, "HOOK & LEAD", 19, "Gravity Hook", "Motivo en Sol menor con tensión Ab prestada."),
    (5, "HOOK & LEAD", 60, "Hoover Anthem", "Supersaw que abre el filtro en el breakdown."),
    (6, "HOOK & LEAD", 49, "Dark Reese Drone", "Suelo grave del breakdown (sin bombo)."),
    (7, "ATMOS", 58, "Gm9 Atmo Pad", "Colchón de aire (rellena el espectro) + envelope follower."),
    (8, "DRUMS", 10, "909 Closed Hat", "Charles en semicorcheas."),
    (9, "DRUMS", 12, "909 Open Hat", "Charles abierta en el contratiempo."),
    (10, "DRUMS", 13, "909 Acid Ride", "Sólo en el clímax."),
    (11, "DRUMS", 11, "Peak Clap", "Clap en los drops."),
    (12, "BUILD & FX", 55, "Riser + Snare Roll", "Sube y corta en el compás 101."),
    (13, "BUILD & FX", 19, "Galope 1/8T", "Tresillos de corchea del Drop 2."),
    (14, "BUILD & FX", 69, "Sub Impact", "Golpe de sub en cada drop."),
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
    print(f"GRAVITY V2 GRILL ORGANIZED ({len(tracks_data)} tracks) & HTML EXPORTED TO: {OUT_HTML}")


if __name__ == "__main__":
    main()
