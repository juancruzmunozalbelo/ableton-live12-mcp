"""
Organizes the live Ableton Live 12 Arrangement Grid (Track Names, Track Colors,
Clip Names, Clip Colors by section/energy) via MCP and generates a live-synced
interactive HTML Studio Arrangement & Mix Blueprint.
"""

from __future__ import annotations

import json
import math
import os
import subprocess
from ableton_live12_mcp.client import Live12Client

HTML_OUT_PATH = "/Users/juancruz/ableton-live12-mcp/masterclasses/peak/acid_flow_ttg_arrangement_map.html"

# Ableton Live 12 Color Index -> Hex Palette Mapping for the Studio Grid
ABLETON_COLOR_HEX = {
    14: "#FF3B30",  # Crimson Red (Kick / Climax Scream)
    15: "#D92B2B",  # Deep Red (Sub Bass K-B-B-B)
    16: "#E05A2B",  # Rust Orange (Rumble / Closed Acid)
    17: "#FF7A00",  # Vivid Orange (TB-303 Main Lead)
    18: "#FFB800",  # Acid Amber (TB-303 Open Filter)
    19: "#E6C700",  # Acid Gold (TB-303 5/16 Counter)
    52: "#D4FF00",  # Acid Neon Lime (Peak Drop 303)
    60: "#FF2D78",  # Laser Magenta (Space 92 Hoover Anthem)
    49: "#8E44AD",  # Deep Purple (Dark Reese Drone Floor)
    10: "#1E6FD9",  # Club Blue (909 Closed Hats)
    12: "#00C8FF",  # Signal Cyan (909 Offbeat Open Hat)
    13: "#00F0D0",  # Bright Turquoise (909 Acid Ride Climax)
    11: "#3B82F6",  # Steel Blue (Peak Clap & Groove Storm)
    55: "#84CC16",  # Tension Lime (Breakdown Riser & Snare Roll)
    58: "#10B981",  # Emerald Green (Tuned G-Phrygian Vocal Pad)
    69: "#F43F5E",  # Coral Impact (Sub Impact Explosion)
}

TRACK_SPECS = [
    {
        "index": 0,
        "group": "LOW-END CHASSIS",
        "name": "01 [LOW] KICK 138 BPM (G1 49Hz)",
        "color": 14,
        "role": "Golpe fundamental en Sol (G1 = 49 Hz). Clava el pulso 4/4 y dispara el Sidechain de los bajos y sintes.",
        "eq": "Sub Puro 49 Hz + Click 3.5 kHz",
        "fader_db": "0.0 dB",
        "clip_label": "Kick G1 (49Hz)",
    },
    {
        "index": 1,
        "group": "LOW-END CHASSIS",
        "name": "02 [LOW] PSY K-B-B-B SUB (G1 Rolling)",
        "color": 15,
        "role": "Bajo rolling Psy-Tech en semicorcheas (corchea + 2 semicorcheas por tiempo) afinado en G1. Empuja el groove entre cada golpe de Kick.",
        "eq": "LPF 185 Hz (Saw + Sub Osc)",
        "fader_db": "-3.5 dB",
        "clip_label": "K-B-B-B Sub G1",
    },
    {
        "index": 2,
        "group": "LOW-END CHASSIS",
        "name": "03 [LOW] TECHNO RUMBLE (HPF 125Hz)",
        "color": 16,
        "role": "Textura de caverna techno en los medios-graves (125–360 Hz). Filtrado abajo de 125 Hz para no chocar jamás con el Sub K-B-B-B.",
        "eq": "HPF 125 Hz / LPF 360 Hz",
        "fader_db": "-9.0 dB",
        "clip_label": "Rumble 125-360Hz",
    },
    {
        "index": 3,
        "group": "DUAL TB-303 ACID ENGINE",
        "name": "04 [ACID] TB-303 MAIN LEAD (1/16 G Phrygian)",
        "color": 17,
        "role": "Línea ácida principal estilo Joris Voorn (Acid Flow). 16 semicorcheas hipnóticas en G Frigio (G - Ab - Bb - D - Eb) abriendo Cutoff y Resonancia.",
        "eq": "HPF 135 Hz + Cytomic OSR Reso",
        "fader_db": "-2.5 dB",
        "clip_label": "303 Main Lead",
    },
    {
        "index": 4,
        "group": "DUAL TB-303 ACID ENGINE",
        "name": "05 [ACID] TB-303 COUNTER (5/16 Polyrhythm)",
        "color": 19,
        "role": "Segunda TB-303 con ciclo polirrítmico de 5 semicorcheas sobre el 4/4 y filtro MS-20. Se desplaza en cada compás generando hipnosis.",
        "eq": "HPF 165 Hz + MS-20 Drive 3.5dB",
        "fader_db": "-8.5 dB",
        "clip_label": "303 Polyrhythm 5/16",
    },
    {
        "index": 5,
        "group": "SYNTHS & BREAKDOWN FLOOR",
        "name": "06 [SYNTH] SPACE92 HOOVER ANTHEM (Supersaw)",
        "color": 60,
        "role": "Himno de octavas Supersaw estilo Space 92 (Gravity). Aparece filtrándose en la mitad del Breakdown y explota en el Drop.",
        "eq": "HPF 210 Hz + Unison + Chorus",
        "fader_db": "-3.2 dB",
        "clip_label": "Space92 Hoover",
    },
    {
        "index": 6,
        "group": "SYNTHS & BREAKDOWN FLOOR",
        "name": "07 [BASS PAD] DARK REESE DRONE (G1 Floor)",
        "color": 49,
        "role": "Colchón grave de ondas sierra desafinadas en G1 + D3. Sostiene el peso del tema durante el Breakdown (compases 33–47) cuando se va el Kick.",
        "eq": "LPF 280 Hz Warm Reese",
        "fader_db": "-4.5 dB",
        "clip_label": "Dark Reese G1",
    },
    {
        "index": 7,
        "group": "909 DRUMS & TOP GROOVE",
        "name": "08 [DRUMS] 909 CLOSED HATS (1/16 Groove)",
        "color": 10,
        "role": "Hi-hat cerrado corriendo en semicorcheas desde el compás 1 para darle velocidad de bandeja al DJ.",
        "eq": "HPF 380 Hz",
        "fader_db": "-9.5 dB",
        "clip_label": "909 Closed Hat 1/16",
    },
    {
        "index": 8,
        "group": "909 DRUMS & TOP GROOVE",
        "name": "09 [DRUMS] 909 OPEN HAT (Offbeat &)",
        "color": 12,
        "role": "Hi-hat abierto clásico de TR-909 en el contratiempo ('&'), filtrado a 8.5 kHz con decaimiento suave. Entra en el compás 17.",
        "eq": "HPF 450 Hz / LPF 8.5 kHz",
        "fader_db": "-10.5 dB",
        "clip_label": "909 Open Hat (&)",
    },
    {
        "index": 9,
        "group": "909 DRUMS & TOP GROOVE",
        "name": "10 [DRUMS] 909 ACID RIDE (Drop 2 Climax)",
        "color": 13,
        "role": "Platillo Ride de 909 bombeado con envolvente de sidechain. Se guarda para los clímax (compás 25 y segunda mitad del Drop en compás 57).",
        "eq": "HPF 550 Hz / LPF 8.2 kHz",
        "fader_db": "-10.0 dB",
        "clip_label": "909 Acid Ride",
    },
    {
        "index": 10,
        "group": "909 DRUMS & TOP GROOVE",
        "name": "11 [DRUMS] PEAK CLAP & GROOVE STORM",
        "color": 11,
        "role": "Clap en tiempos 2 y 4 durante el bloque TTG (compases 17–32) y loop percusivo Groove Storm durante el Peak Drop (compases 49–64).",
        "eq": "HPF 220 Hz",
        "fader_db": "-8.5 dB",
        "clip_label": "Clap / Groove Storm",
    },
    {
        "index": 11,
        "group": "ATMOSPHERE & TRANSITIONS",
        "name": "12 [BUILD] RISER & SNARE ROLL (Cut @ 188)",
        "color": 55,
        "role": "Riser cinematográfico + Redoble de tambor (Snare Roll) que sube la tensión y corta en seco en el beat 188.0 antes del silencio pre-drop.",
        "eq": "HPF 210 Hz / LPF 7.0 kHz",
        "fader_db": "-7.5 dB",
        "clip_label": "Build / Snare Roll",
    },
    {
        "index": 12,
        "group": "ATMOSPHERE & TRANSITIONS",
        "name": "13 [ATMOS] TTG G-PHRYGIAN VOCAL PAD (G3)",
        "color": 58,
        "role": "Pad vocal etéreo re-afinado exactamente -5 semitonos de Do (C4) a Sol (G3) para calzar 100% en la escala G Frigio sin disonancias.",
        "eq": "HPF 220 Hz + Hall Reverb",
        "fader_db": "-5.0 dB",
        "clip_label": "Vocal Pad G3",
    },
    {
        "index": 13,
        "group": "ATMOSPHERE & TRANSITIONS",
        "name": "14 [FX] SUB IMPACT EXPLOSION (Bar 1/33/49)",
        "color": 69,
        "role": "Explosión sub-sísmica con cola de Delay que marca el inicio de las 3 grandes secciones (Intro, Breakdown y Peak Drop).",
        "eq": "HPF 140 Hz + Stereo Delay",
        "fader_db": "-2.2 dB",
        "clip_label": "Sub Impact FX",
    },
]


def section_tag_and_color(track_idx: int, base_color: int, start_beat: float, base_label: str) -> tuple[str, int]:
    """Determines the human-readable Clip Name and Ableton Color Index based on timeline position and track role."""
    bar_num = int(round(start_beat / 4.0)) + 1
    if start_beat < 64.0:
        sec = "INTRO"
        if track_idx == 3:
            return f"[INTRO c.{bar_num}] 303 Lead (Filtro Cerrado 25%)", 16
        return f"[INTRO c.{bar_num}] {base_label}", base_color
    elif start_beat < 128.0:
        sec = "TTG"
        if track_idx == 3:
            return f"[TTG c.{bar_num}] 303 Lead (Filtro Abriendo 68%)", 18
        if track_idx == 9:
            return f"[TTG PEAK c.{bar_num}] 909 Acid Ride", 13
        if track_idx == 10:
            return f"[TTG c.{bar_num}] 909 Clap (2 & 4)", 11
        return f"[TTG c.{bar_num}] {base_label}", base_color
    elif start_beat < 172.0:
        sec = "BREAK"
        if track_idx == 3:
            return f"[BREAK c.{bar_num}] 303 Meltdown Sweep (38→88%)", 17
        if track_idx == 5:
            return f"[BREAK c.{bar_num}] Hoover Reveal (Filtro Subiendo)", 60
        if track_idx == 11:
            return f"[BUILD c.{bar_num}] Cinematic Riser", 55
        return f"[BREAK c.{bar_num}] {base_label}", base_color
    elif start_beat < 192.0:
        if track_idx == 3:
            return f"[CLIMAX c.{bar_num}] 303 ACID SCREAM (95% Reso!)", 14
        if track_idx == 11:
            return f"[CLIMAX c.{bar_num}] Snare Roll (Corta en 188!)", 14
        return f"[CLIMAX c.{bar_num}] {base_label} (Cut @ 188)", base_color
    elif start_beat < 224.0:
        if track_idx == 3:
            return f"[DROP 1 c.{bar_num}] 303 Full Acid Lead", 52
        if track_idx == 10:
            return f"[DROP 1 c.{bar_num}] Groove Storm Loop", 11
        return f"[DROP 1 c.{bar_num}] {base_label}", base_color
    else:
        if track_idx == 3:
            return f"[DROP 2 c.{bar_num}] 303 Acid Lead Climax", 52
        if track_idx == 9:
            return f"[DROP 2 c.{bar_num}] 909 ACID RIDE CLIMAX", 13
        if track_idx == 10:
            return f"[DROP 2 c.{bar_num}] Groove Storm Loop", 11
        return f"[DROP 2 c.{bar_num}] {base_label}", base_color


def _set_track_palette_color(c: Live12Client, track_index: int, color_index: int) -> None:
    """Paint a track header with a Live 12 palette slot.

    `live12_track_set_properties(color=...)` only accepts palette indices from
    bridge build 2026-10-24 onwards; older running bridges silently wrote the
    packed-RGB property and left every track on the default slot 69. The LOM
    escape hatch (`color_index`) works on every build, so it is the fallback.
    """
    try:
        c.call("live12_track_set_properties", {
            "track_index": track_index,
            "color_index": int(color_index),
        })
    except Exception:
        c.call("live12_lom_set", {
            "target_path": f"song.tracks.{track_index}",
            "property_name": "color_index",
            "value": int(color_index),
        })


def organize_ableton_grid_and_collect() -> list[dict]:
    c = Live12Client()
    tracks_data = []

    for spec in TRACK_SPECS:
        t_idx = spec["index"]
        # 1. Update Track Name and Track Color Index in Ableton Live 12
        c.call("live12_track_set_properties", {
            "track_index": t_idx,
            "name": spec["name"],
        })
        _set_track_palette_color(c, t_idx, spec["color"])

        # 2. Inspect and organize every Arrangement Clip on this track
        arr_clips = c.call("live12_lom_get", {
            "target_path": f"song.tracks.{t_idx}",
            "property_name": "arrangement_clips",
        }).get("value", [])

        organized_clips = []
        for c_idx in range(len(arr_clips)):
            clip_path = f"song.tracks.{t_idx}.arrangement_clips.{c_idx}"
            st = float(c.call("live12_lom_get", {"target_path": clip_path, "property_name": "start_time"})["value"])
            et = float(c.call("live12_lom_get", {"target_path": clip_path, "property_name": "end_time"})["value"])
            clip_name, clip_color = section_tag_and_color(t_idx, spec["color"], st, spec["clip_label"])

            # Apply clean name and color to the Arrangement Clip in Ableton Live 12!
            c.call("live12_lom_set", {"target_path": clip_path, "property_name": "name", "value": clip_name})
            c.call("live12_lom_set", {"target_path": clip_path, "property_name": "color_index", "value": int(clip_color)})

            organized_clips.append({
                "clip_index": c_idx,
                "name": clip_name,
                "start_beat": st,
                "end_beat": et,
                "start_bar": int(round(st / 4.0)) + 1,
                "end_bar": int(round(et / 4.0)),
                "color_index": clip_color,
                "hex": ABLETON_COLOR_HEX.get(clip_color, "#00C8FF"),
            })

        tracks_data.append({
            **spec,
            "hex": ABLETON_COLOR_HEX.get(spec["color"], "#00C8FF"),
            "clips": organized_clips,
        })

    return tracks_data


def build_interactive_html(tracks_data: list[dict]) -> None:
    tracks_json = json.dumps(tracks_data, ensure_ascii=False, indent=2)
    html = f"""<!DOCTYPE html>
<html lang="es-AR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Ableton Live 12 — Mapa Visual de Grilla & Mezcla (Joris Voorn Acid Flow × Space 92)</title>
  <style>
    :root {{
      --void-bg: #050709;
      --panel-bg: #0c1015;
      --row-bg: #11161d;
      --row-alt: #0e1319;
      --border-dim: rgba(255, 255, 255, 0.08);
      --border-bright: rgba(255, 255, 255, 0.18);
      --text-main: #f1f5f9;
      --text-muted: #94a3b8;
      --accent-cyan: #00f0ff;
      --accent-acid: #d4ff00;
      --accent-red: #ff3b30;
      --accent-magenta: #ff2d78;
    }}

    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      scrollbar-width: thin;
      scrollbar-color: rgba(255, 255, 255, 0.2) transparent;
    }}

    ::selection {{
      background: var(--accent-cyan);
      color: var(--void-bg);
    }}

    body {{
      background: var(--void-bg);
      color: var(--text-main);
      font-family: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", Roboto, sans-serif;
      font-variant-numeric: tabular-nums;
      line-height: 1.45;
      padding: 24px 28px 64px;
    }}

    /* Header & Specs Bar */
    .top-bar {{
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: flex-end;
      gap: 16px;
      padding-bottom: 20px;
      border-bottom: 1px solid var(--border-dim);
      margin-bottom: 20px;
    }}

    .title-block h1 {{
      font-size: clamp(1.5rem, 2.6vw, 2.25rem);
      font-weight: 800;
      letter-spacing: -0.03em;
      text-wrap: balance;
      color: #ffffff;
    }}

    .title-block p {{
      color: var(--text-muted);
      font-size: 0.94rem;
      margin-top: 4px;
    }}

    .telemetry-pills {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}

    .pill {{
      background: var(--panel-bg);
      border: 1px solid var(--border-bright);
      padding: 6px 12px;
      border-radius: 2px;
      font-size: 0.8rem;
      font-weight: 600;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }}

    .pill span {{
      color: var(--accent-acid);
      margin-left: 6px;
    }}

    /* Legend & Stem Families */
    .stem-legend {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
      gap: 10px;
      margin-bottom: 22px;
    }}

    .legend-card {{
      background: var(--panel-bg);
      border: 1px solid var(--border-dim);
      border-left: 4px solid var(--stem-color, #00f0ff);
      padding: 10px 14px;
      border-radius: 2px;
    }}

    .legend-card h3 {{
      font-size: 0.78rem;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--stem-color);
      margin-bottom: 3px;
    }}

    .legend-card p {{
      font-size: 0.8rem;
      color: var(--text-muted);
    }}

    /* Arrangement Timeline Container */
    .arranger-shell {{
      background: var(--panel-bg);
      border: 1px solid var(--border-bright);
      border-radius: 2px;
      overflow-x: auto;
      margin-bottom: 24px;
    }}

    .arranger-minwidth {{
      min-width: 1180px;
    }}

    /* Section Locators Header */
    .locator-row {{
      display: grid;
      grid-template-columns: 310px 1fr;
      background: #080b0f;
      border-bottom: 1px solid var(--border-bright);
    }}

    .locator-label-col {{
      padding: 10px 14px;
      font-size: 0.75rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--text-muted);
      border-right: 1px solid var(--border-bright);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }}

    .locator-timeline {{
      position: relative;
      height: 52px;
      background: repeating-linear-gradient(
        to right,
        rgba(255, 255, 255, 0.04) 0,
        rgba(255, 255, 255, 0.04) 1px,
        transparent 1px,
        transparent 6.25%
      );
    }}

    .section-banner {{
      position: absolute;
      top: 0;
      bottom: 0;
      border-left: 2px solid var(--sec-color, #00f0ff);
      padding: 6px 8px;
      background: linear-gradient(180deg, rgba(255,255,255,0.05) 0%, transparent 100%);
      overflow: hidden;
      cursor: pointer;
      transition: background 0.15s ease;
    }}

    .section-banner:hover {{
      background: rgba(255, 255, 255, 0.09);
    }}

    .section-banner .sec-title {{
      font-size: 0.72rem;
      font-weight: 800;
      color: var(--sec-color, #fff);
      white-space: nowrap;
      letter-spacing: 0.03em;
    }}

    .section-banner .sec-sub {{
      font-size: 0.67rem;
      color: var(--text-muted);
      white-space: nowrap;
      margin-top: 2px;
    }}

    /* Track Rows */
    .track-row {{
      display: grid;
      grid-template-columns: 310px 1fr;
      border-bottom: 1px solid var(--border-dim);
      background: var(--row-bg);
      transition: background 0.12s ease;
    }}

    .track-row:nth-child(even) {{
      background: var(--row-alt);
    }}

    .track-row:hover {{
      background: #171f2a;
    }}

    .track-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 8px 12px;
      border-right: 1px solid var(--border-bright);
      border-left: 5px solid var(--track-color, #00f0ff);
      cursor: pointer;
      gap: 8px;
    }}

    .track-name {{
      font-size: 0.78rem;
      font-weight: 700;
      color: #f8fafc;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}

    .track-meta {{
      display: flex;
      align-items: center;
      gap: 6px;
      flex-shrink: 0;
    }}

    .badge-eq {{
      font-size: 0.66rem;
      padding: 2px 5px;
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid rgba(255, 255, 255, 0.12);
      color: #cbd5e1;
      border-radius: 2px;
    }}

    .badge-db {{
      font-size: 0.7rem;
      font-weight: 700;
      color: var(--accent-acid);
      min-width: 48px;
      text-align: right;
    }}

    .track-lane {{
      position: relative;
      height: 38px;
      background: repeating-linear-gradient(
        to right,
        rgba(255, 255, 255, 0.045) 0,
        rgba(255, 255, 255, 0.045) 1px,
        transparent 1px,
        transparent 6.25%
      );
    }}

    /* Vertical Section Guide Lines on Lanes */
    .lane-guide {{
      position: absolute;
      top: 0;
      bottom: 0;
      width: 1px;
      background: rgba(255, 255, 255, 0.14);
      pointer-events: none;
      z-index: 1;
    }}

    .lane-guide.silence-zone {{
      background: rgba(255, 59, 48, 0.18);
      border-left: 1px dashed #ff3b30;
      border-right: 1px dashed #ff3b30;
    }}

    /* Clips inside Arrangement Lane */
    .arr-clip {{
      position: absolute;
      top: 4px;
      bottom: 4px;
      background: var(--clip-bg, #00c8ff);
      border: 1px solid rgba(255, 255, 255, 0.38);
      border-top: 3px solid rgba(255, 255, 255, 0.75);
      border-radius: 2px;
      padding: 2px 5px;
      overflow: hidden;
      cursor: pointer;
      z-index: 2;
      display: flex;
      align-items: center;
      transition: transform 0.1s ease, filter 0.1s ease;
    }}

    .arr-clip:hover {{
      filter: brightness(1.22);
      transform: translateY(-1px);
      z-index: 5;
    }}

    .arr-clip span {{
      font-size: 0.66rem;
      font-weight: 800;
      color: #050709;
      white-space: nowrap;
      text-overflow: ellipsis;
      overflow: hidden;
      letter-spacing: -0.01em;
    }}

    /* Inspector Drawer & Energy Curve Section */
    .bottom-grid {{
      display: grid;
      grid-template-columns: 1.15fr 0.85fr;
      gap: 20px;
    }}

    @media (max-width: 980px) {{
      .bottom-grid {{
        grid-template-columns: 1fr;
      }}
    }}

    .inspector-box {{
      background: var(--panel-bg);
      border: 1px solid var(--border-bright);
      padding: 18px 20px;
      border-radius: 2px;
    }}

    .inspector-box h2 {{
      font-size: 0.9rem;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--accent-cyan);
      margin-bottom: 10px;
    }}

    .inspector-title {{
      font-size: 1.15rem;
      font-weight: 800;
      margin-bottom: 8px;
      color: #fff;
    }}

    .inspector-detail {{
      font-size: 0.9rem;
      color: #cbd5e1;
      margin-bottom: 12px;
    }}

    .inspector-specs {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }}

    .spec-chip {{
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--border-dim);
      padding: 6px 10px;
      font-size: 0.78rem;
      border-radius: 2px;
    }}

    .spec-chip strong {{
      color: var(--accent-acid);
    }}

    .section-steps {{
      display: flex;
      flex-direction: column;
      gap: 8px;
    }}

    .step-item {{
      padding: 8px 12px;
      background: rgba(255, 255, 255, 0.03);
      border-left: 3px solid var(--step-color, #00f0ff);
      font-size: 0.82rem;
    }}

    .step-item strong {{
      color: #fff;
    }}
  </style>
</head>
<body>

  <header class="top-bar">
    <div class="title-block">
      <h1> ESQUEMA DE GRILLA ABLETON LIVE 12 — JORIS VOORN "ACID FLOW (TTG)" × SPACE 92</h1>
      <p>Sincronizado en vivo por MCP con tu proyecto de Ableton Live 12 Suite. Hacé clic en cualquier pista o clip para inspeccionar su función, corte de EQ y automatización.</p>
    </div>
    <div class="telemetry-pills">
      <div class="pill">BPM<span>138.0</span></div>
      <div class="pill">ESCALA<span>G PHRYGIAN (Sol Frigio)</span></div>
      <div class="pill">ESTRUCTURA<span>64 COMPASES (256 BEATS)</span></div>
      <div class="pill">PRE-DROP SILENCE<span>COMPÁS 48 (BEATS 188–192)</span></div>
    </div>
  </header>

  <section class="stem-legend">
    <div class="legend-card" style="--stem-color: #FF3B30;">
      <h3>1. ROJO — CHASIS SUB & LOW-END</h3>
      <p>Pistas 01 a 03: Kick en Sol (49 Hz), Bajo Psy K-B-B-B en G1 y Rumble Techno filtrado en 125–360 Hz.</p>
    </div>
    <div class="legend-card" style="--stem-color: #FF7A00;">
      <h3>2. NARANJA / ÁMBAR — MOTOR DUAL TB-303</h3>
      <p>Pistas 04 y 05: 303 Principal (1/16) cambiando de color según abre el filtro + 303 Polirrítmica en 5/16.</p>
    </div>
    <div class="legend-card" style="--stem-color: #FF2D78;">
      <h3>3. MAGENTA / PÚRPURA — HOOVER & REESE</h3>
      <p>Pistas 06 y 07: Supersaw Hoover estilo Space 92 + Drone Reese en G1 que sostiene el Breakdown sin Kick.</p>
    </div>
    <div class="legend-card" style="--stem-color: #00C8FF;">
      <h3>4. CIAN / AZUL — BATERÍAS TR-909</h3>
      <p>Pistas 08 a 11: Closed Hat 1/16, 909 Open Hat en '&', 909 Acid Ride de clímax y Clap / Groove Storm.</p>
    </div>
    <div class="legend-card" style="--stem-color: #10B981;">
      <h3>5. ESMERALDA / CORAL — VOCAL PAD & FX</h3>
      <p>Pistas 12 a 14: Riser + Snare Roll (corta en 188), Pad Vocal afinado en G3 y Sub Impact en los cambios.</p>
    </div>
  </section>

  <main class="arranger-shell">
    <div class="arranger-minwidth">
      <!-- Locators Row -->
      <div class="locator-row">
        <div class="locator-label-col">
          <span>PISTA / CATEGORÍA</span>
          <span>EQ / FADER</span>
        </div>
        <div class="locator-timeline">
          <div class="section-banner" style="left: 0%; width: 25%; --sec-color: #FF3B30;" onclick="inspectSection(0)">
            <div class="sec-title">1-INTRO DJ GROOVE (Comp. 1–16)</div>
            <div class="sec-sub">Beats 0–64 • Kick + K-B-B-B + 303 Cerrada</div>
          </div>
          <div class="section-banner" style="left: 25%; width: 25%; --sec-color: #00C8FF;" onclick="inspectSection(1)">
            <div class="sec-title">2-TTG 909 HAT & DUAL 303 (Comp. 17–32)</div>
            <div class="sec-sub">Beats 64–128 • Entra 909 OH + 303 5/16 + Ride (c.25)</div>
          </div>
          <div class="section-banner" style="left: 50%; width: 23.4375%; --sec-color: #FF7A00;" onclick="inspectSection(2)">
            <div class="sec-title">3-BREAKDOWN MELTDOWN (Comp. 33–47)</div>
            <div class="sec-sub">Beats 128–188 • Sale Kick • Entra Reese G1 + 303 Scream</div>
          </div>
          <div class="section-banner" style="left: 73.4375%; width: 1.5625%; --sec-color: #FFFFFF; background: rgba(255,59,48,0.28);" onclick="inspectSection(3)" title="Compás 48 (Beats 188-192): Silencio total Pre-Drop">
            <div class="sec-title">4</div>
          </div>
          <div class="section-banner" style="left: 75%; width: 12.5%; --sec-color: #D4FF00;" onclick="inspectSection(4)">
            <div class="sec-title">5-PEAK DROP 1 (Comp. 49–56)</div>
            <div class="sec-sub">Beats 192–224 • Todo al 100% + Hoover</div>
          </div>
          <div class="section-banner" style="left: 87.5%; width: 12.5%; --sec-color: #00F0D0;" onclick="inspectSection(5)">
            <div class="sec-title">6-DROP 2 CLIMAX (Comp. 57–64)</div>
            <div class="sec-sub">Beats 224–256 • + 909 Acid Ride</div>
          </div>
        </div>
      </div>

      <!-- Dynamic Track Rows -->
      <div id="tracks-container"></div>
    </div>
  </main>

  <section class="bottom-grid">
    <div class="inspector-box" id="inspector-panel">
      <h2>INSPECTOR DE ELEMENTO (HACÉ CLIC EN UNA PISTA O CLIP ARRIBA)</h2>
      <div class="inspector-title" id="insp-title">04 [ACID] TB-303 MAIN LEAD (1/16 G Phrygian)</div>
      <div class="inspector-detail" id="insp-desc">
        Línea ácida principal estilo Joris Voorn (Acid Flow). Fijate cómo en la grilla los clips de esta pista cambian de color a medida que avanza el tema: empieza en Naranja Oscuro (Filtro cerrado al 25% en la Intro), pasa a Ámbar en el compás 17, sube a Naranja Vivo en el Breakdown, se pone Rojo Fuego en el clímax (compases 45–47 con resonancia al 95%) y estalla en Verde Lima Neón en el Drop (compás 49).
      </div>
      <div class="inspector-specs" id="insp-specs">
        <div class="spec-chip"><strong>Grupo:</strong> DUAL TB-303 ACID ENGINE</div>
        <div class="spec-chip"><strong>EQ Quirúrgico:</strong> HPF 135 Hz + Cytomic OSR Reso</div>
        <div class="spec-chip"><strong>Nivel Fader:</strong> -2.5 dB</div>
        <div class="spec-chip"><strong>Escala:</strong> G Phrygian (G - Ab - Bb - D - Eb)</div>
      </div>
    </div>

    <div class="inspector-box">
      <h2>LA REGLA DE LOS 8/16 COMPASES (CÓMO LEER EL ARREGLO)</h2>
      <div class="section-steps">
        <div class="step-item" style="--step-color: #FF3B30;">
          <strong>Compases 1–16 (Beats 0–64):</strong> Base limpia para mezclar con bandeja. Kick en G1 + Sub K-B-B-B + 303 bien cerrada murmurando abajo.
        </div>
        <div class="step-item" style="--step-color: #00C8FF;">
          <strong>Compases 17–32 (Beats 64–128):</strong> Entra el 909 Open Hat suave en '&' y la segunda 303 en 5/16. En el compás 25 (beat 96) se suma el 909 Ride.
        </div>
        <div class="step-item" style="--step-color: #FF7A00;">
          <strong>Compases 33–47 (Beats 128–188):</strong> Se apaga el Kick y entra el <em>Dark Reese Drone (pista 07)</em> para sostener el subgrave mientras las dos 303 abren el filtro al máximo y asoma el Hoover de Space 92.
        </div>
        <div class="step-item" style="--step-color: #D4FF00;">
          <strong>Compás 48 (Beats 188–192) → Compás 49 (Beat 192):</strong> 4 tiempos de vacío total (<em>Pre-Drop Silence</em>) y explosión del Drop 1 con Kick + K-B-B-B + 303 al tope + Hoover. En el compás 57 entra el 909 Acid Ride para el remate final.
        </div>
      </div>
    </div>
  </section>

  <script>
    const TRACKS = {tracks_json};

    const SECTIONS = [
      {{
        title: "1-INTRO DJ GROOVE (Compases 1–16 | Beats 0–64)",
        desc: "Chasis rítmico puro pensado para que cualquier DJ pueda mezclar el tema en club. Suenan el Kick en G1, el Sub K-B-B-B, el Rumble filtrado (125–360 Hz), los Closed Hats 1/16 y la TB-303 principal con el filtro bien cerrado (25% a 42%).",
        specs: ["Duración: 16 Compases (27.8 seg)", "Energía: 45%", "Protagonistas: Kick + K-B-B-B + 303 Cerrada"]
      }},
      {{
        title: "2-TTG 909 OPEN HAT & DUAL 303 ACID (Compases 17–32 | Beats 64–128)",
        desc: "Se abre el groove estilo Awakenings: entra el 909 Open Hat sedoso en el contratiempo ('&'), el Clap en 2 y 4, y la segunda TB-303 haciendo un polirritmo de 5 semicorcheas. En el compás 25 (Beat 96) entra por primera vez el 909 Acid Ride.",
        specs: ["Duración: 16 Compases (27.8 seg)", "Energía: 72%", "Protagonistas: 909 Open Hat + Dual 303"]
      }},
      {{
        title: "3-BREAKDOWN: ACID MELTDOWN (Compases 33–47 | Beats 128–188)",
        desc: "Desaparece el Kick para generar ingravidez, pero entra el Dark Reese Drone (Pista 07) en G1 + el Pad Vocal en G3 (Pista 13) para que la pista no quede vacía. La TB-303 abre el filtro desde 38% hasta gritar al 95% junto con el Snare Roll y el Hoover.",
        specs: ["Duración: 15 Compases (Beats 128–188)", "Energía: Tensión ascendente → 95%", "Protagonistas: Reese Drone + 303 Scream + Hoover"]
      }},
      {{
        title: "4-PRE-DROP SILENCE (Compás 48 | Beats 188–192)",
        desc: "La firma de Space 92 y Joris Voorn: exactamente 1 compás (4 negras = 1.74 segundos a 138 BPM) donde se cortan en seco todos los sintetizadores, bajos y redobles para limpiar los oídos antes del impacto del Drop.",
        specs: ["Duración: 1 Compás (4 Beats)", "Energía: Vacío de tensión", "Corte exacto en Beat 188.0"]
      }},
      {{
        title: "5-PEAK DROP PARTE 1 (Compases 49–56 | Beats 192–224)",
        desc: "Vuelve el chasis completo (Kick + K-B-B-B + Rumble + Sub Impact) chocando de frente con las dos TB-303 abiertas al máximo, el Hoover Supersaw de Space 92 y el loop Groove Storm.",
        specs: ["Duración: 8 Compases (Beats 192–224)", "Energía: 95%", "Impacto Peak-Time"]
      }},
      {{
        title: "6-PEAK DROP PARTE 2: 909 ACID RIDE CLIMAX (Compases 57–64 | Beats 224–256)",
        desc: "Para que los segundos 8 compases del Drop no suenen estáticos, entra el 909 Acid Ride (Pista 10) bombeando en semicorcheas y abriendo el brillo arriba de las 303 y el Hoover.",
        specs: ["Duración: 8 Compases (Beats 224–256)", "Energía: 100% Clímax", "Entra: 909 Acid Ride"]
      }}
    ];

    function renderGrid() {{
      const container = document.getElementById("tracks-container");
      container.innerHTML = "";

      TRACKS.forEach((tr) => {{
        const row = document.createElement("div");
        row.className = "track-row";

        const header = document.createElement("div");
        header.className = "track-header";
        header.style.setProperty("--track-color", tr.hex);
        header.onclick = () => inspectTrack(tr);

        header.innerHTML = `
          <div class="track-name" title="${{tr.name}}">${{tr.name}}</div>
          <div class="track-meta">
            <span class="badge-eq">${{tr.eq.split('+')[0].trim()}}</span>
            <span class="badge-db">${{tr.fader_db}}</span>
          </div>
        `;

        const lane = document.createElement("div");
        lane.className = "track-lane";

        // Add vertical section guides at 64, 128, 188..192, 224
        [25, 50, 75, 87.5].forEach((pct) => {{
          const g = document.createElement("div");
          g.className = "lane-guide";
          g.style.left = pct + "%";
          lane.appendChild(g);
        }});

        // Silence zone highlight (beats 188..192 = 73.4375% to 75%)
        const sz = document.createElement("div");
        sz.className = "lane-guide silence-zone";
        sz.style.left = "73.4375%";
        sz.style.width = "1.5625%";
        lane.appendChild(sz);

        tr.clips.forEach((cl) => {{
          const clipEl = document.createElement("div");
          clipEl.className = "arr-clip";
          const leftPct = (cl.start_beat / 256.0) * 100.0;
          const widthPct = ((cl.end_beat - cl.start_beat) / 256.0) * 100.0;
          clipEl.style.left = leftPct + "%";
          clipEl.style.width = `calc(${{widthPct}}% - 1px)`;
          clipEl.style.setProperty("--clip-bg", cl.hex);
          clipEl.title = `${{cl.name}} (Compás ${{cl.start_bar}} a ${{cl.end_bar}} | Beats ${{cl.start_beat}}–${{cl.end_beat}})`;
          clipEl.innerHTML = `<span>${{cl.name}}</span>`;
          clipEl.onclick = (e) => {{
            e.stopPropagation();
            inspectClip(tr, cl);
          }};
          lane.appendChild(clipEl);
        }});

        row.appendChild(header);
        row.appendChild(lane);
        container.appendChild(row);
      }});
    }}

    function inspectTrack(tr) {{
      document.getElementById("insp-title").textContent = tr.name;
      document.getElementById("insp-desc").textContent = tr.role;
      document.getElementById("insp-specs").innerHTML = `
        <div class="spec-chip"><strong>Grupo:</strong> ${{tr.group}}</div>
        <div class="spec-chip"><strong>EQ / Proceso:</strong> ${{tr.eq}}</div>
        <div class="spec-chip"><strong>Fader:</strong> ${{tr.fader_db}}</div>
        <div class="spec-chip"><strong>Clips en Grilla:</strong> ${{tr.clips.length}} bloques</div>
      `;
    }}

    function inspectClip(tr, cl) {{
      document.getElementById("insp-title").textContent = `${{cl.name}} — ${{tr.name}}`;
      document.getElementById("insp-desc").textContent = tr.role;
      document.getElementById("insp-specs").innerHTML = `
        <div class="spec-chip"><strong>Posición:</strong> Compás ${{cl.start_bar}} al ${{cl.end_bar}} (Beats ${{cl.start_beat}} – ${{cl.end_beat}})</div>
        <div class="spec-chip"><strong>Duración:</strong> ${{(cl.end_beat - cl.start_beat)}} beats (${{((cl.end_beat - cl.start_beat)/4)}} compases)</div>
        <div class="spec-chip"><strong>EQ Pista:</strong> ${{tr.eq}}</div>
        <div class="spec-chip"><strong>Nivel Fader:</strong> ${{tr.fader_db}}</div>
      `;
    }}

    function inspectSection(idx) {{
      const s = SECTIONS[idx];
      document.getElementById("insp-title").textContent = s.title;
      document.getElementById("insp-desc").textContent = s.desc;
      document.getElementById("insp-specs").innerHTML = s.specs
        .map((sp) => `<div class="spec-chip"><strong>•</strong> ${{sp}}</div>`)
        .join("");
    }}

    renderGrid();
  </script>
</body>
</html>
"""
    os.makedirs(os.path.dirname(HTML_OUT_PATH), exist_ok=True)
    with open(HTML_OUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)


if __name__ == "__main__":
    data = organize_ableton_grid_and_collect()
    build_interactive_html(data)
    print(f"GRID ORGANIZED ({len(data)} tracks) & HTML EXPORTED TO: {HTML_OUT_PATH}")
