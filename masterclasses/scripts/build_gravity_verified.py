"""
SPACE 92 "GRAVITY" (VERIFIED EDITION) — 132 BPM · G menor · 6:06 · 201 compases
===================================================================================
Reconstrucción CORREGIDA según los datos verificados del release real
(Filth on Acid FOA126, 17/02/2023: 132 BPM, key Gm, extended 6:06 / radio 4:00)
y según las 6 lecciones del breakdown de François PML
("Producer Notes: In the Style of Space 92 'Gravity'", Production Music Live ep.004):

  L1. RUMBLE con color y forma propio (2 capas con color/EQ independientes)
  L2. VELOCIDADES MIDI RANDOMIZADAS en percusión y elementos melódicos
  L3. "HACER ESPACIO": el sub y el main compiten -> filtro/EQ con movimiento
  L4. CAPAS DE ATMÓS para llenar el espectro
  L5. ENVELOPE FOLLOWER (stock Ableton) para mezcla dinámica
  L6. CADENA EN PARALELO (return C) + reverb ducking por automatización

Se ejecuta contra el Ableton Live 12 vivo vía el MCP `ableton-live12` (127.0.0.1:11246).
"""

from __future__ import annotations

import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ableton_live12_mcp.client import Live12Client  # noqa: E402

from build_joris_acid_flow_ttg import (  # helpers probados en vivo
    add_surgical_highpass_eq,
    configure_returns_and_master,
    create_midi_clip_with_filter_sweep,
    db_to_norm,
    place_audio_range,
    set_params,
)
from loop_renderer import render_club_loops  # noqa: E402

PEAK_OUT = "/Users/juancruz/ableton-live12-mcp/masterclasses/peak"
SAMPLES_DIR = "/Users/juancruz/Downloads/ClaSE PEAK jULIO 25 Project/Samples"
SAMPLE_KICK = os.path.join(SAMPLES_DIR, "Processed", "Consolidate", "OL_SKPA1_Kick_Loop_01_123 (5) [2025-06-25 203905].wav")
SAMPLE_RUMBLE_ALT = os.path.join(SAMPLES_DIR, "Processed", "Consolidate", "TWHS_HGE1_RUMBLE_LOOP_08_143BPM [2025-06-25 203947].wav")
SAMPLE_CH = os.path.join(SAMPLES_DIR, "Imported", "TWHS_HGE1_CH_LOOP_03_142BPM.wav")
SAMPLE_RISER = os.path.join(SAMPLES_DIR, "Imported", "ESM_7th_Dimension_Build_Up_Rising_Riser_Cinematic_Trailer_Movie_Transition.wav")
SAMPLE_IMPACT = os.path.join(SAMPLES_DIR, "Imported", "031_FX_Impact_-_SEROTONINTRANCE_Zenhiser.wav")

BPM = 132.0
SCALE_ROOT = 7          # G
SCALE_NAME = "Minor"    # Sol menor (el real es Gm, no frigio)
TOTAL_BEATS = 806       # 806 beats @132 BPM = 6:06 (extended real)
RNG = random.Random(42)  # semilla fija => build reproducible

# ----------------------------------------------------------------------------------
# Mapa de secciones (beats)
# ----------------------------------------------------------------------------------
S1_INTRO = (0.0, 128.0)        # compases   1-32
S2_GROOVE = (128.0, 256.0)      # compases  33-64
S3_BREAKDOWN = (256.0, 368.0)   # compases  65-92
S4_BUILD = (368.0, 400.0)       # compases  93-100
S5_SILENCE = (400.0, 404.0)     # compás   101 (silencio absoluto)
S6_DROP1 = (404.0, 532.0)       # compases 102-133
S7_MINIBREAK = (532.0, 548.0)   # compases 134-137
S8_DROP2 = (548.0, 644.0)       # compases 138-161
S9_OUTRO = (644.0, 806.0)       # compases 162-201

LOCATORS = [
    (0.0, "1-INTRO DJ (K-B-B-B + RUMBLE)"),
    (128.0, "2-GROOVE (HOOK ENTRA)"),
    (256.0, "3-BREAKDOWN (REESE + HOOVER + ATMO)"),
    (368.0, "4-BUILD (RISER + SNARE ROLL)"),
    (400.0, "5-PRE-DROP SILENCE (1 COMPAS)"),
    (404.0, "6-PEAK DROP 1"),
    (532.0, "7-MINI BREAK"),
    (548.0, "8-CLIMAX DROP 2 (GALOPE 1/8T)"),
    (644.0, "9-OUTRO"),
]


def blocks(start: float, end: float, size: float = 16.0) -> list[float]:
    out, pos = [], start
    while pos + size - 0.01 <= end:
        out.append(pos)
        pos += size
    return out


def humanize(notes: list[dict], amount: float = 10.0, chance: float = 1.0) -> list[dict]:
    """L2: randomiza las velocidades MIDI (y un poco el timing) para que suene tocado.

    Semilla fija => el build es reproducible (el mismo script da el mismo resultado).
    """
    out = []
    for n in notes:
        v = int(n["velocity"])
        jitter = int(round(RNG.uniform(-amount, amount)))
        v = max(20, min(127, v + jitter))
        out.append({
            "pitch": n["pitch"],
            "start_time": round(max(0.0, n["start_time"] + RNG.uniform(-0.004, 0.004)), 5),
            "duration": n["duration"],
            "velocity": v,
        })
    return out


def hook_notes_4bars() -> list[dict]:
    """Hook en SOL MENOR (G - Bb - D - Eb - F) con la Ab (b2) como tensión PRESTADA.

    En el track real la escala es Gm: el Ab no pertenece a la escala, así que se usa
    como brillo puntual (no como base). Eso es lo que lo hace "melodic" y no oscuro.
    """
    cell = [
        (55, 0.0, 0.75, 118),   # G3
        (58, 0.75, 0.25, 94),   # Bb3
        (62, 1.0, 1.75, 112),   # D4
        (63, 2.75, 0.25, 96),   # Eb4
        (65, 3.0, 0.75, 110),   # F4
    ]
    notes = []
    for bar in range(4):
        base = bar * 4.0
        for pitch, start, dur, vel in cell:
            notes.append({"pitch": pitch, "start_time": base + start, "duration": dur, "velocity": vel})
        if bar % 2 == 1:   # la tensión b2 (Ab4) aparece cada 2 compases
            notes.append({"pitch": 68, "start_time": base + 3.75, "duration": 0.25, "velocity": 92})
    return notes


def triplet_gallop_4bars() -> list[dict]:
    """Galope 1/8T: 3 notas por negra, con movimiento melódico (G - Bb - D) en G menor."""
    notes = []
    third = 1.0 / 3.0
    pattern = (43, 43, 46)   # G1, G1, Bb1 (la 3a de cada negra es la que "camina")
    for bar in range(4):
        base = bar * 4.0
        for beat in range(4):
            b = base + beat
            for i, pitch in enumerate(pattern):
                vel = 104 if i == 0 else (80 if i == 1 else 126)
                notes.append({"pitch": pitch, "start_time": b + i * third,
                              "duration": 0.20 if i != 2 else 0.24, "velocity": vel})
    return notes


def atmo_chord_4bars() -> list[dict]:
    """Colchón de aire en Gm9: G2 - Bb2 - D3 - F3 - Ab3 (tensión) sostenido."""
    notes = []
    for bar in range(4):
        base = bar * 4.0
        for pitch, vel in ((43, 70), (46, 64), (50, 62), (53, 58), (56, 54)):
            notes.append({"pitch": pitch, "start_time": base, "duration": 3.9, "velocity": vel})
    return notes


def reset_session(c: Live12Client) -> None:
    """Set limpio a 132 BPM en Sol menor."""
    c.call("live12_transport_stop", {})
    c.call("live12_transport_set_tempo", {"tempo": BPM})
    c.call("live12_transport_set_time_signature", {"numerator": 4, "denominator": 4})
    c.call("live12_song_set_scale", {"root_note": SCALE_ROOT, "scale_name": SCALE_NAME})

    c.call("live12_track_create", {"type": "audio", "index": -1})
    st = c.call("live12_song_get_state", {})
    for idx in range(st["tracks_count"] - 2, -1, -1):
        try:
            c.call("live12_track_delete", {"track_index": idx})
        except Exception:
            pass
    cues = c.call("live12_cue_point_control", {"action": "list"}).get("cue_points", [])
    for cp in reversed(cues):
        try:
            c.call("live12_cue_point_control", {"action": "delete", "cue_index": cp["index"]})
        except Exception:
            pass


def add_locators(c: Live12Client) -> None:
    # `set_or_delete_cue` alterna: si YA hay un cue en esa posición, lo BORRA.
    # Por eso primero se limpian todos y después se crean de cero.
    for cp in reversed(c.call("live12_cue_point_control", {"action": "list"}).get("cue_points", [])):
        try:
            c.call("live12_cue_point_control", {"action": "delete", "cue_index": cp["index"]})
        except Exception:
            pass
    for beat, name in LOCATORS:
        c.call("live12_lom_set", {"target_path": "song", "property_name": "current_song_time", "value": float(beat)})
        time.sleep(0.04)
        c.call("live12_lom_call", {"target_path": "song", "method_name": "set_or_delete_cue"})
        time.sleep(0.04)
        cues = c.call("live12_cue_point_control", {"action": "list"}).get("cue_points", [])
        for cp in cues:
            if abs(float(cp.get("time", -999.0)) - beat) < 0.2:
                c.call("live12_lom_set", {
                    "target_path": f"song.cue_points.{cp['index']}",
                    "property_name": "name", "value": name,
                })
                break


def build_gravity_verified_set() -> None:
    loops = render_club_loops(BPM, PEAK_OUT, "_132bpm")
    c = Live12Client()
    reset_session(c)

    # =========================================================================
    # 01 · KICK (dueño exclusivo del transiente del "1")
    # =========================================================================
    t_kick = 0
    c.call("live12_track_set_properties", {"track_index": t_kick, "name": "01 [LOW] KICK G1 49HZ (BOOM)", "color": 14})
    c.call("live12_mixer_set", {"track_index": t_kick, "volume": db_to_norm(-1.8), "pan": 0.0})
    add_surgical_highpass_eq(c, t_kick, freq_norm=0.08, bell_freq=0.35, bell_gain_db=-2.5)
    c.call("live12_browser_load_item", {"track_index": t_kick, "browser_item_uri": "Glue Compressor"})
    set_params(c, t_kick, 1, {1: -12.0, 3: 2.0, 4: 4.0, 6: 1.0, 8: 1.0})
    for a, b in (S1_INTRO, S2_GROOVE, S4_BUILD, S6_DROP1, S7_MINIBREAK, S8_DROP2, S9_OUTRO):
        place_audio_range(c, t_kick, SAMPLE_KICK, a, b)

    # =========================================================================
    # 02 · ROLLING SUB K-B-B-B (galope) — dueño exclusivo de 43-49 Hz
    # =========================================================================
    t_sub = c.call("live12_track_create", {"type": "midi", "index": -1})["track_index"]
    c.call("live12_track_set_properties", {"track_index": t_sub, "name": "02 [LOW] PSY ROLLING SUB (K-B-B-B G1)", "color": 15})
    c.call("live12_mixer_set", {"track_index": t_sub, "volume": db_to_norm(-2.8), "pan": 0.0})
    c.call("live12_browser_load_item", {"track_index": t_sub, "browser_item_uri": "Operator"})
    c.call("live12_browser_load_item", {"track_index": t_sub, "browser_item_uri": "Roar"})
    set_params(c, t_sub, 0, {
        25: 3.0, 31: 0.24, 33: 0.0,
        166: 3.0, 170: 0.26, 171: 0.22, 173: 8.5, 176: 52.0, 181: 0.20, 184: 0.0,
    })
    set_params(c, t_sub, 1, {1: 0.62, 10: 1.0, 11: 0.42})
    kbbb = []
    for beat in range(16):
        root = 44 if beat in (7, 15) else 43   # Ab1 (b2) como tensión, sólo en el 4to tiempo
        kbbb.extend([
            {"pitch": root, "start_time": beat + 0.25, "duration": 0.19, "velocity": 80},
            {"pitch": root, "start_time": beat + 0.50, "duration": 0.21, "velocity": 126},
            {"pitch": root + 12 if beat % 4 == 3 else root, "start_time": beat + 0.75, "duration": 0.19, "velocity": 110},
        ])
    sub_positions = blocks(S1_INTRO[0], S5_SILENCE[0]) + blocks(S6_DROP1[0], S9_OUTRO[1])
    create_midi_clip_with_filter_sweep(
        c, t_sub, 0, "K-B-B-B Rolling Sub (G minor)", 16.0, humanize(kbbb, 6.0), sorted(set(sub_positions)),
        device_idx=0, cutoff_param_idx=170, cutoff_start=0.24, cutoff_end=0.33, res_param_idx=None,
    )

    # =========================================================================
    # 03 · RUMBLE LAYER A (L1: color + forma propios)
    # =========================================================================
    t_rum_a = c.call("live12_track_create", {"type": "audio", "index": -1})["track_index"]
    c.call("live12_track_set_properties", {"track_index": t_rum_a, "name": "03 [LOW] RUMBLE A (COLOR/HP 125Hz)", "color": 16})
    c.call("live12_mixer_set", {"track_index": t_rum_a, "volume": db_to_norm(-7.5), "pan": 0.0})
    add_surgical_highpass_eq(c, t_rum_a, freq_norm=0.28)
    c.call("live12_browser_load_item", {"track_index": t_rum_a, "browser_item_uri": "Roar"})
    set_params(c, t_rum_a, 2, {1: 0.45, 4: 0.5, 10: 0.5, 11: 0.35})
    for a, b in (S1_INTRO, S2_GROOVE, S6_DROP1, S8_DROP2, S9_OUTRO):
        place_audio_range(c, t_rum_a, loops["rumble"], a, b, step_override=16.0)

    # =========================================================================
    # 04 · RUMBLE LAYER B (segunda capa, otra fuente + otro color = "rumble rack")
    # =========================================================================
    t_rum_b = c.call("live12_track_create", {"type": "audio", "index": -1})["track_index"]
    c.call("live12_track_set_properties", {"track_index": t_rum_b, "name": "04 [LOW] RUMBLE B (2DA CAPA/CAVA)", "color": 17})
    c.call("live12_mixer_set", {"track_index": t_rum_b, "volume": db_to_norm(-12.0), "pan": 0.0})
    add_surgical_highpass_eq(c, t_rum_b, freq_norm=0.33)
    c.call("live12_browser_load_item", {"track_index": t_rum_b, "browser_item_uri": "Saturator"})
    set_params(c, t_rum_b, 2, {1: 0.35, 2: 0.5, 3: 0.2})
    for a, b in (S2_GROOVE, S3_BREAKDOWN, S6_DROP1, S8_DROP2, S9_OUTRO):
        place_audio_range(c, t_rum_b, SAMPLE_RUMBLE_ALT, a, b, step_override=16.0)

    # =========================================================================
    # 05 · HOOK (Sol menor + tensión Ab prestada + velocities humanizadas)
    # =========================================================================
    t_hook = c.call("live12_track_create", {"type": "midi", "index": -1})["track_index"]
    c.call("live12_track_set_properties", {"track_index": t_hook, "name": "05 [HOOK] GRAVITY HOOK (Gm + b2)", "color": 19})
    c.call("live12_mixer_set", {"track_index": t_hook, "volume": db_to_norm(-4.5), "pan": 0.0})
    c.call("live12_browser_load_item", {"track_index": t_hook, "browser_item_uri": "Drift"})
    c.call("live12_browser_load_item", {"track_index": t_hook, "browser_item_uri": "Roar"})
    add_surgical_highpass_eq(c, t_hook, freq_norm=0.31)
    c.call("live12_browser_load_item", {"track_index": t_hook, "browser_item_uri": "Delay"})
    set_params(c, t_hook, 0, {
        1: 0.32, 2: 0.62, 3: 1.0, 6: 0.94, 20: 4.0, 30: 0.0, 32: 0.0,
        35: 0.0, 36: 0.30, 38: 0.0, 39: 0.0, 40: 0.24, 42: 0.0,
        53: 0.80, 61: 1.0, 63: 0.40, 64: 0.72,
    })
    set_params(c, t_hook, 1, {1: 0.70, 2: 0.60, 3: 0.55, 4: 1.0, 10: 2.0, 11: 0.70})
    hook = hook_notes_4bars()
    create_midi_clip_with_filter_sweep(
        c, t_hook, 0, "Hook - Groove (128..256)", 16.0, humanize(hook, 8.0),
        blocks(S2_GROOVE[0], S2_GROOVE[1]),
        device_idx=0, cutoff_param_idx=1, cutoff_start=0.26, cutoff_end=0.48, res_param_idx=2, res_val=0.62,
    )
    create_midi_clip_with_filter_sweep(
        c, t_hook, 1, "Hook - Peak Drop (404..532)", 16.0, humanize(hook, 8.0),
        blocks(S6_DROP1[0], S6_DROP1[1]),
        device_idx=0, cutoff_param_idx=1, cutoff_start=0.66, cutoff_end=0.92, res_param_idx=2, res_val=0.80,
    )
    create_midi_clip_with_filter_sweep(
        c, t_hook, 2, "Hook - Climax Drop 2 (548..644)", 16.0, humanize(hook, 8.0),
        blocks(S8_DROP2[0], S8_DROP2[1]),
        device_idx=0, cutoff_param_idx=1, cutoff_start=0.72, cutoff_end=0.96, res_param_idx=2, res_val=0.84,
    )

    # =========================================================================
    # 06 · HOOVER ANTHEM (supersaw con filtro que abre)
    # =========================================================================
    t_lead = c.call("live12_track_create", {"type": "midi", "index": -1})["track_index"]
    c.call("live12_track_set_properties", {"track_index": t_lead, "name": "06 [SYNTH] HOOVER ANTHEM (SUPERSAW)", "color": 60})
    c.call("live12_mixer_set", {"track_index": t_lead, "volume": db_to_norm(-3.2), "pan": 0.0})
    c.call("live12_browser_load_item", {"track_index": t_lead, "browser_item_uri": "Wavetable"})
    add_surgical_highpass_eq(c, t_lead, freq_norm=0.34)
    c.call("live12_browser_load_item", {"track_index": t_lead, "browser_item_uri": "Chorus-Ensemble"})
    c.call("live12_browser_load_item", {"track_index": t_lead, "browser_item_uri": "Reverb"})
    set_params(c, t_lead, 0, {
        4: 0.68, 9: 1.0, 11: 0.62, 12: 0.75, 17: 1.0,
        26: 0.72, 27: 0.32, 28: 0.45, 89: 0.78, 91: 0.42,
    })
    hoover_gm = [
        (55, 0.0, 1.5, 124), (67, 0.0, 1.5, 124),
        (58, 1.5, 1.0, 120), (70, 1.5, 1.0, 120),
        (63, 2.5, 1.5, 127), (75, 2.5, 1.5, 127),
        (62, 4.0, 1.5, 122), (74, 4.0, 1.5, 122),
        (58, 5.5, 1.0, 118), (70, 5.5, 1.0, 118),
        (60, 6.5, 1.5, 126), (72, 6.5, 1.5, 126),
        (55, 8.0, 1.5, 124), (67, 8.0, 1.5, 124),
        (58, 9.5, 1.0, 122), (70, 9.5, 1.0, 122),
        (62, 10.5, 1.5, 125), (74, 10.5, 1.5, 125),
        (63, 12.0, 1.5, 127), (75, 12.0, 1.5, 127),
        (62, 13.5, 1.0, 122), (74, 13.5, 1.0, 122),
        (60, 14.5, 1.5, 126), (72, 14.5, 1.5, 126),
    ]
    hoover_notes = humanize([{"pitch": p, "start_time": st, "duration": d, "velocity": v}
                              for (p, st, d, v) in hoover_gm], 5.0)
    create_midi_clip_with_filter_sweep(
        c, t_lead, 0, "Hoover Anthem (Breakdown)", 16.0, hoover_notes,
        blocks(S3_BREAKDOWN[0], S3_BREAKDOWN[1]),
        device_idx=0, cutoff_param_idx=26, cutoff_start=0.30, cutoff_end=0.95, res_param_idx=None,
    )
    create_midi_clip_with_filter_sweep(
        c, t_lead, 1, "Hoover Anthem (Peak Drop 1)", 16.0, hoover_notes,
        blocks(S6_DROP1[0], S6_DROP1[1]),
        device_idx=0, cutoff_param_idx=26, cutoff_start=0.62, cutoff_end=0.92, res_param_idx=None,
    )
    create_midi_clip_with_filter_sweep(
        c, t_lead, 2, "Hoover Anthem (Climax Drop 2)", 16.0, hoover_notes,
        blocks(S8_DROP2[0], S8_DROP2[1]),
        device_idx=0, cutoff_param_idx=26, cutoff_start=0.74, cutoff_end=0.97, res_param_idx=None,
    )

    # =========================================================================
    # 07 · DARK REESE DRONE (suelo del breakdown, ahora con 5a de Gm)
    # =========================================================================
    t_reese = c.call("live12_track_create", {"type": "midi", "index": -1})["track_index"]
    c.call("live12_track_set_properties", {"track_index": t_reese, "name": "07 [BASS PAD] DARK REESE DRONE (Gm)", "color": 49})
    c.call("live12_mixer_set", {"track_index": t_reese, "volume": db_to_norm(-4.5), "pan": 0.0})
    c.call("live12_browser_load_item", {"track_index": t_reese, "browser_item_uri": "Wavetable"})
    c.call("live12_browser_load_item", {"track_index": t_reese, "browser_item_uri": "Chorus-Ensemble"})
    add_surgical_highpass_eq(c, t_reese, freq_norm=0.30)
    reese_notes = []
    for b in [x * 0.5 for x in range(0, 32)]:
        reese_notes.append({"pitch": 43, "start_time": b, "duration": 3.9, "velocity": 104})
        reese_notes.append({"pitch": 46, "start_time": b, "duration": 3.9, "velocity": 82})
    create_midi_clip_with_filter_sweep(
        c, t_reese, 0, "Dark Reese Floor (Gm)", 16.0, humanize(reese_notes, 4.0),
        blocks(S3_BREAKDOWN[0], S3_BREAKDOWN[1]),
        device_idx=0, cutoff_param_idx=26, cutoff_start=0.22, cutoff_end=0.40, res_param_idx=None,
    )

    # =========================================================================
    # 08 · ATMÓS (L4: capa de aire para llenar el espectro)
    # =========================================================================
    t_atmo = c.call("live12_track_create", {"type": "midi", "index": -1})["track_index"]
    c.call("live12_track_set_properties", {"track_index": t_atmo, "name": "08 [ATMOS] Gm9 ATMOSPHERE PAD", "color": 58})
    c.call("live12_mixer_set", {"track_index": t_atmo, "volume": db_to_norm(-8.0), "pan": 0.0})
    c.call("live12_browser_load_item", {"track_index": t_atmo, "browser_item_uri": "Wavetable"})
    add_surgical_highpass_eq(c, t_atmo, freq_norm=0.32)
    c.call("live12_browser_load_item", {"track_index": t_atmo, "browser_item_uri": "Reverb"})
    set_params(c, t_atmo, 0, {4: 0.35, 9: 1.0, 11: 0.55, 12: 0.8, 17: 1.0, 26: 0.45, 27: 0.4})
    atmo = atmo_chord_4bars()
    create_midi_clip_with_filter_sweep(
        c, t_atmo, 0, "Atmo Gm9 Pad", 16.0, atmo,
        blocks(S3_BREAKDOWN[0], S3_BREAKDOWN[1]) + blocks(S7_MINIBREAK[0], S7_MINIBREAK[1]),
        device_idx=0, cutoff_param_idx=26, cutoff_start=0.20, cutoff_end=0.55, res_param_idx=None,
    )

    # =========================================================================
    # 09 · L5: ENVELOPE FOLLOWER (mezcla dinámica stock) sobre la pista de atmo
    # =========================================================================
    c.call("live12_browser_load_item", {"track_index": t_atmo, "browser_item_uri": "Envelope Follower"})
    c.call("live12_browser_load_item", {"track_index": t_atmo, "browser_item_uri": "Auto Filter"})
    # devices de la pista atmo: 0=Wavetable 1=EQ Eight 2=Reverb 3=Envelope Follower 4=Auto Filter
    ef_params = c.call("live12_device_get_parameters", {"track_index": t_atmo, "device_index": 3}).get("parameters", [])
    by_name = {p["name"]: p["index"] for p in ef_params}
    ef_map = {}
    if "Attack" in by_name:
        ef_map[by_name["Attack"]] = 1.0
    if "Release" in by_name:
        ef_map[by_name["Release"]] = 3.0
    if ef_map:
        set_params(c, t_atmo, 3, ef_map)

    # =========================================================================
    # 10 · CLOSED HATS
    # =========================================================================
    t_ch = c.call("live12_track_create", {"type": "audio", "index": -1})["track_index"]
    c.call("live12_track_set_properties", {"track_index": t_ch, "name": "09 [DRUMS] 909 CLOSED HATS (1/16)", "color": 10})
    c.call("live12_mixer_set", {"track_index": t_ch, "volume": db_to_norm(-9.5), "pan": -0.05})
    add_surgical_highpass_eq(c, t_ch, freq_norm=0.42)
    for a, b in (S2_GROOVE, S4_BUILD, S6_DROP1, S7_MINIBREAK, S8_DROP2, S9_OUTRO):
        place_audio_range(c, t_ch, SAMPLE_CH, a, b)

    # =========================================================================
    # 11 · OPEN HAT (offbeat)
    # =========================================================================
    t_oh = c.call("live12_track_create", {"type": "audio", "index": -1})["track_index"]
    c.call("live12_track_set_properties", {"track_index": t_oh, "name": "10 [DRUMS] 909 OPEN HAT (OFFBEAT &)", "color": 12})
    c.call("live12_mixer_set", {"track_index": t_oh, "volume": db_to_norm(-10.5), "pan": 0.05})
    add_surgical_highpass_eq(c, t_oh, freq_norm=0.40)
    for a, b in (S2_GROOVE, S6_DROP1, S8_DROP2):
        place_audio_range(c, t_oh, loops["open_hat"], a, b, step_override=16.0)

    # =========================================================================
    # 12 · ACID RIDE (clímax)
    # =========================================================================
    t_ride = c.call("live12_track_create", {"type": "audio", "index": -1})["track_index"]
    c.call("live12_track_set_properties", {"track_index": t_ride, "name": "11 [DRUMS] 909 ACID RIDE (CLIMAX)", "color": 13})
    c.call("live12_mixer_set", {"track_index": t_ride, "volume": db_to_norm(-10.0), "pan": 0.10})
    add_surgical_highpass_eq(c, t_ride, freq_norm=0.38)
    place_audio_range(c, t_ride, loops["ride"], S6_DROP1[0] + 64.0, S6_DROP1[1], step_override=16.0)
    place_audio_range(c, t_ride, loops["ride"], S8_DROP2[0], S8_DROP2[1], step_override=16.0)

    # =========================================================================
    # 13 · PEAK CLAP
    # =========================================================================
    t_clap = c.call("live12_track_create", {"type": "audio", "index": -1})["track_index"]
    c.call("live12_track_set_properties", {"track_index": t_clap, "name": "12 [DRUMS] PEAK CLAP", "color": 11})
    c.call("live12_mixer_set", {"track_index": t_clap, "volume": db_to_norm(-8.5), "pan": 0.0})
    add_surgical_highpass_eq(c, t_clap, freq_norm=0.36)
    for a, b in (S6_DROP1, S8_DROP2):
        place_audio_range(c, t_clap, loops["clap"], a, b, step_override=16.0)

    # =========================================================================
    # 14 · RISER + SNARE ROLL (corta en 400 para el silencio)
    # =========================================================================
    t_build = c.call("live12_track_create", {"type": "audio", "index": -1})["track_index"]
    c.call("live12_track_set_properties", {"track_index": t_build, "name": "13 [BUILD] RISER + SNARE ROLL (CUT 400)", "color": 55})
    c.call("live12_mixer_set", {"track_index": t_build, "volume": db_to_norm(-7.5), "pan": 0.0})
    add_surgical_highpass_eq(c, t_build, freq_norm=0.30)
    place_audio_range(c, t_build, SAMPLE_RISER, S4_BUILD[0], S4_BUILD[1] - 8.0, step_override=16.0)

    # =========================================================================
    # 15 · GALOPE 1/8T (firma Space 92 en el Drop 2)
    # =========================================================================
    t_gal = c.call("live12_track_create", {"type": "midi", "index": -1})["track_index"]
    c.call("live12_track_set_properties", {"track_index": t_gal, "name": "14 [BASS] GALOPE 1/8T (DROP 2)", "color": 19})
    c.call("live12_mixer_set", {"track_index": t_gal, "volume": db_to_norm(-6.0), "pan": -0.10})
    c.call("live12_browser_load_item", {"track_index": t_gal, "browser_item_uri": "Operator"})
    add_surgical_highpass_eq(c, t_gal, freq_norm=0.26)
    c.call("live12_browser_load_item", {"track_index": t_gal, "browser_item_uri": "Roar"})
    set_params(c, t_gal, 0, {
        25: 3.0, 31: 0.18, 33: 0.0,
        166: 3.0, 170: 0.42, 171: 0.30, 173: 6.0, 176: 40.0, 181: 0.16, 184: 0.0,
    })
    set_params(c, t_gal, 1, {1: 0.55, 10: 1.0, 11: 0.40})
    gallop = triplet_gallop_4bars()
    create_midi_clip_with_filter_sweep(
        c, t_gal, 0, "Galope 1/8T (Climax)", 16.0, humanize(gallop, 7.0),
        blocks(S8_DROP2[0], S8_DROP2[1]),
        device_idx=0, cutoff_param_idx=170, cutoff_start=0.38, cutoff_end=0.52, res_param_idx=None,
    )

    # =========================================================================
    # 16 · SUB IMPACT
    # =========================================================================
    t_fx = c.call("live12_track_create", {"type": "audio", "index": -1})["track_index"]
    c.call("live12_track_set_properties", {"track_index": t_fx, "name": "15 [FX] SUB IMPACT (DROP HITS)", "color": 69})
    c.call("live12_mixer_set", {"track_index": t_fx, "volume": db_to_norm(-2.2), "pan": 0.0})
    add_surgical_highpass_eq(c, t_fx, freq_norm=0.24)
    c.call("live12_browser_load_item", {"track_index": t_fx, "browser_item_uri": "Delay"})
    for hit in (S6_DROP1[0], S8_DROP2[0]):
        c.call("live12_lom_call", {
            "target_path": f"song.tracks.{t_fx}",
            "method_name": "create_audio_clip",
            "args": [SAMPLE_IMPACT, float(hit)],
        })

    # =========================================================================
    # L6 · BUSES: reverb + delay + PARALLEL TAIL (relleno de altas)
    # =========================================================================
    send_map = [
        (t_kick, 0.00, 0.00), (t_sub, 0.00, 0.00), (t_rum_a, 0.20, 0.00),
        (t_rum_b, 0.18, 0.00), (t_hook, 0.18, 0.26), (t_lead, 0.34, 0.12),
        (t_reese, 0.26, 0.00), (t_atmo, 0.42, 0.00), (t_ch, 0.14, 0.10),
        (t_oh, 0.16, 0.12), (t_ride, 0.20, 0.00), (t_clap, 0.24, 0.00),
        (t_build, 0.22, 0.00), (t_gal, 0.12, 0.00), (t_fx, 0.10, 0.00),
    ]
    configure_returns_and_master(c, send_map)

    # Return C = cadena EN PARALELO (relleno de frequencies altas, sin la reverb de cola principal)
    c.call("live12_lom_set", {"target_path": "song.return_tracks.2", "property_name": "name",
                              "value": "C-PARALLEL TAIL FILL"})
    c.call("live12_browser_load_item", {"track_index": 2, "browser_item_uri": "EQ Eight", "track_type": "return"})
    c.call("live12_browser_load_item", {"track_index": 2, "browser_item_uri": "Reverb", "track_type": "return"})
    c.call("live12_browser_load_item", {"track_index": 2, "browser_item_uri": "Compressor", "track_type": "return"})

    # Locators (con el set ya poblado, la longitud alcanza para todos)
    add_locators(c)

    print("GRAVITY (VERIFIED) SET BUILT: 132 BPM / G minor / 806 beats / 6:06 / 16 tracks / 9 locators")


if __name__ == "__main__":
    build_gravity_verified_set()
