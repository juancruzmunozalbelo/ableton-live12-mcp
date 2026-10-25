"""
SPACE 92 "GRAVITY"-LIKE — Peak-Time / Rolling Psy-Tech (176 compases ≈ 5:05)
===================================================================================
138.0 BPM | G Frigio (G - Ab - Bb - C - D - Eb - F)

LA FÓRMULA DE SPACE 92 APLICADA (7 piezas):
  1. K-B-B-B ROLLING SUB   -> galope de 3 semicorcheas por negra, nunca en el "1"
                             (el kick es dueño exclusivo del transiente del "1")
  2. ESCALA FRIGIA        -> b2 (Ab) contra la tónica: tensión oscura sin acordes de jazz
  3. HOOK HIPNÓTICO       -> motivo corto de 4 negras en repetición exacta (no "coración")
  4. HOOVER SUPERSAW      -> octavas massive con filtro que abre en el breakdown
  5. SILENCIO PRE-DROP    -> 1 compás de silencio absoluto antes del impacto
  6. GALOPE 1/8T          -> tresillos de corchea en el Drop 2 (firma Space 92)
  7. ARQUITECTURA 176c    -> Intro 32c / Groove 32c / Breakdown 16c / Build 4c /
                             PRE-DROP 1c / Drop 1 32c / Mini-break 4c / Drop 2 16c / Outro 35c

Se ejecuta contra el Ableton Live 12 vivo vía el MCP `ableton-live12` (TCP 127.0.0.1:11246).
"""

from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ableton_live12_mcp.client import Live12Client

from build_joris_acid_flow_ttg import (  # noqa: E402  (helpers ya probados en vivo)
    LOOP_CLAP_16,
    LOOP_OH_909_WAV,
    LOOP_RIDE_909_WAV,
    LOOP_RUMBLE_16,
    SAMPLE_CH,
    SAMPLE_IMPACT,
    SAMPLE_KICK,
    SAMPLE_RISER,
    add_surgical_highpass_eq,
    configure_returns_and_master,
    create_midi_clip_with_filter_sweep,
    db_to_norm,
    place_audio_range,
    reset_clean_session,
    set_params,
)

# ----------------------------------------------------------------------------------
# Mapa de secciones (en beats; 4 beats = 1 compás)
# ----------------------------------------------------------------------------------
S1_INTRO = (0.0, 128.0)        # compases  1-32
S2_GROOVE = (128.0, 256.0)      # compases 33-64
S3_BREAKDOWN = (256.0, 336.0)   # compases 65-84
S4_BUILD = (336.0, 352.0)       # compases 85-88
S5_SILENCE = (352.0, 356.0)     # compás 89  (silencio absoluto)
S6_DROP1 = (356.0, 484.0)       # compases 90-121
S7_MINIBREAK = (484.0, 500.0)   # compases 122-125
S8_DROP2 = (500.0, 564.0)       # compases 126-141
S9_OUTRO = (564.0, 704.0)       # compases 142-176

LOCATORS = [
    (0.0, "1-INTRO DJ (K-B-B-B + RUMBLE)"),
    (128.0, "2-GROOVE (HOOK ENTRA)"),
    (256.0, "3-BREAKDOWN (REESE + HOOVER)"),
    (336.0, "4-BUILD (RISER + SNARE ROLL)"),
    (352.0, "5-PRE-DROP SILENCE (1 COMPAS)"),
    (356.0, "6-PEAK DROP 1 (FULL)"),
    (484.0, "7-MINI BREAK (RESPIRA)"),
    (500.0, "8-CLIMAX DROP 2 (GALOPE 1/8T)"),
    (564.0, "9-OUTRO (DESCARTE)"),
]


def add_locators(c: Live12Client) -> None:
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
                    "property_name": "name",
                    "value": name,
                })
                break


def blocks(start: float, end: float, size: float = 16.0) -> list[float]:
    """Devuelve los inicios de bloque de `size` beats dentro de [start, end)."""
    out, pos = [], start
    while pos + size - 0.01 <= end:
        out.append(pos)
        pos += size
    return out


def hook_notes_4bars() -> list[dict]:
    """Motivo hipnótico de 4 negras (célula) repetido 4 veces por clip de 16 beats.

    G3 - Ab3 (b2) - Eb3 - D3 : la tensión del b2 sobre la tónica, con el D resolviendo.
    """
    cell = [
        (55, 0.0, 0.75, 118),   # G3
        (56, 0.75, 0.25, 92),   # Ab3 (b2) roce
        (51, 1.0, 1.75, 112),   # Eb3
        (50, 2.75, 0.25, 96),   # D3 roce
        (55, 3.0, 0.75, 110),   # G3 (repite la célula)
        (63, 3.75, 0.25, 88),   # Eb4 destello
    ]
    notes = []
    for bar in range(4):
        base = bar * 4.0
        for pitch, start, dur, vel in cell:
            notes.append({"pitch": pitch, "start_time": base + start, "duration": dur, "velocity": vel})
    return notes


def triplet_gallop_4bars() -> list[dict]:
    """Galope 1/8T: 3 notas por negra (0, 1/3, 2/3), octava acentuada en el 'a'."""
    notes = []
    third = 1.0 / 3.0
    for bar in range(4):
        base = bar * 4.0
        for beat in range(4):
            b = base + beat
            notes.append({"pitch": 43, "start_time": b, "duration": 0.20, "velocity": 104})          # G1
            notes.append({"pitch": 43, "start_time": b + third, "duration": 0.20, "velocity": 80})    # G1
            notes.append({"pitch": 55, "start_time": b + 2 * third, "duration": 0.22, "velocity": 126})  # G2 pop
    return notes


def build_gravity_like_set() -> None:
    c = Live12Client()
    reset_clean_session(c)
    # NOTE: los locators se crean AL FINAL: Live impide mover el playhead más allá
    # de la longitud del set, y al principio el set está vacío (longitud 0).

    # =========================================================================
    # 00 - KICK (dueño exclusivo del transiente del "1")
    # =========================================================================
    t_kick = 0
    c.call("live12_track_set_properties", {"track_index": t_kick, "name": "01 [LOW] KICK G1 49HZ (BOOM)", "color": 14})
    c.call("live12_mixer_set", {"track_index": t_kick, "volume": db_to_norm(-1.8), "pan": 0.0})
    add_surgical_highpass_eq(c, t_kick, freq_norm=0.08, bell_freq=0.35, bell_gain_db=-2.5)
    c.call("live12_browser_load_item", {"track_index": t_kick, "browser_item_uri": "Glue Compressor"})
    set_params(c, t_kick, 1, {1: -12.0, 3: 2.0, 4: 4.0, 6: 1.0, 8: 1.0})
    # Kick ausente en el breakdown (256..336) y durante el silencio pre-drop.
    for a, b in (S1_INTRO, S2_GROOVE, S4_BUILD, S6_DROP1, S7_MINIBREAK, S8_DROP2, S9_OUTRO):
        place_audio_range(c, t_kick, SAMPLE_KICK, a, b)

    # =========================================================================
    # 01 - ROLLING SUB K-B-B-B (la galope de Space 92)
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
    # K-B-B-B: 3 semicorcheas por negra (e, &, a). NUNCA en el "1" (ahí está el kick).
    kbbb = []
    for beat in range(16):
        root = 44 if beat in (7, 15) else 43          # Ab1 (b2) en el 4to tiempo
        kbbb.extend([
            {"pitch": root, "start_time": beat + 0.25, "duration": 0.19, "velocity": 80},
            {"pitch": root, "start_time": beat + 0.50, "duration": 0.21, "velocity": 126},
            {"pitch": root + 12 if beat % 4 == 3 else root, "start_time": beat + 0.75, "duration": 0.19, "velocity": 110},
        ])
    # El sub calla SOLO durante el compás de silencio pre-drop (352..356).
    sub_positions = blocks(S1_INTRO[0], S5_SILENCE[0]) + blocks(S6_DROP1[0], S9_OUTRO[1])
    create_midi_clip_with_filter_sweep(
        c, t_sub, 0, "K-B-B-B Rolling Sub (G Phrygian)", 16.0, kbbb, sorted(set(sub_positions)),
        device_idx=0, cutoff_param_idx=170, cutoff_start=0.24, cutoff_end=0.33, res_param_idx=None,
    )

    # =========================================================================
    # 02 - RUMBLE TEXTURE (HP >130 Hz, jamás toca el sub)
    # =========================================================================
    t_rumble = c.call("live12_track_create", {"type": "audio", "index": -1})["track_index"]
    c.call("live12_track_set_properties", {"track_index": t_rumble, "name": "03 [LOW] TECHNO RUMBLE (HPF 125Hz)", "color": 16})
    c.call("live12_mixer_set", {"track_index": t_rumble, "volume": db_to_norm(-7.0), "pan": 0.0})
    add_surgical_highpass_eq(c, t_rumble, freq_norm=0.28)
    for a, b in (S1_INTRO, S2_GROOVE, S6_DROP1, S8_DROP2, S9_OUTRO):
        place_audio_range(c, t_rumble, LOOP_RUMBLE_16, a, b, step_override=16.0)

    # =========================================================================
    # 03 - HOOK HIPNÓTICO (el "corazón" de Space 92: repetición exacta)
    # =========================================================================
    t_hook = c.call("live12_track_create", {"type": "midi", "index": -1})["track_index"]
    c.call("live12_track_set_properties", {"track_index": t_hook, "name": "04 [HOOK] SPACE 92 HOOK (G FRIGIO)", "color": 17})
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
    # Groove: el hook entra filtrado (cutoff cerrado) y se abre de a poco.
    create_midi_clip_with_filter_sweep(
        c, t_hook, 0, "Hook - Groove (128..256)", 16.0, hook,
        blocks(S2_GROOVE[0], S2_GROOVE[1]),
        device_idx=0, cutoff_param_idx=1, cutoff_start=0.26, cutoff_end=0.48, res_param_idx=2, res_val=0.62,
    )
    # Drop 1: hook a full con el filtro bien abierto (corte de navaja).
    create_midi_clip_with_filter_sweep(
        c, t_hook, 1, "Hook - Peak Drop (356..484)", 16.0, hook,
        blocks(S6_DROP1[0], S6_DROP1[1]),
        device_idx=0, cutoff_param_idx=1, cutoff_start=0.66, cutoff_end=0.92, res_param_idx=2, res_val=0.80,
    )
    # Drop 2: el hook se multiplica con el galope 1/8T.
    create_midi_clip_with_filter_sweep(
        c, t_hook, 2, "Hook - Climax Drop 2 (500..564)", 16.0, hook,
        blocks(S8_DROP2[0], S8_DROP2[1]),
        device_idx=0, cutoff_param_idx=1, cutoff_start=0.72, cutoff_end=0.96, res_param_idx=2, res_val=0.84,
    )

    # =========================================================================
    # 04 - HOOVER ANTHEM (supersaw que abre el filtro en el breakdown)
    # =========================================================================
    t_lead = c.call("live12_track_create", {"type": "midi", "index": -1})["track_index"]
    c.call("live12_track_set_properties", {"track_index": t_lead, "name": "05 [SYNTH] HOOVER ANTHEM (SUPERSAW)", "color": 60})
    c.call("live12_mixer_set", {"track_index": t_lead, "volume": db_to_norm(-3.2), "pan": 0.0})
    c.call("live12_browser_load_item", {"track_index": t_lead, "browser_item_uri": "Wavetable"})
    add_surgical_highpass_eq(c, t_lead, freq_norm=0.34)
    c.call("live12_browser_load_item", {"track_index": t_lead, "browser_item_uri": "Chorus-Ensemble"})
    c.call("live12_browser_load_item", {"track_index": t_lead, "browser_item_uri": "Reverb"})
    set_params(c, t_lead, 0, {
        4: 0.68, 9: 1.0, 11: 0.62, 12: 0.75, 17: 1.0,
        26: 0.72, 27: 0.32, 28: 0.45, 89: 0.78, 91: 0.42,
    })
    hoover_g = [
        (55, 0.0, 1.5, 124), (67, 0.0, 1.5, 124),
        (62, 1.5, 1.0, 120), (74, 1.5, 1.0, 120),
        (63, 2.5, 1.5, 127), (75, 2.5, 1.5, 127),
        (62, 4.0, 1.5, 122), (74, 4.0, 1.5, 122),
        (58, 5.5, 1.0, 118), (70, 5.5, 1.0, 118),
        (56, 6.5, 1.5, 126), (68, 6.5, 1.5, 126),
        (55, 8.0, 1.5, 124), (67, 8.0, 1.5, 124),
        (56, 9.5, 1.0, 122), (68, 9.5, 1.0, 122),
        (58, 10.5, 1.5, 125), (70, 10.5, 1.5, 125),
        (63, 12.0, 1.5, 127), (75, 12.0, 1.5, 127),
        (62, 13.5, 1.0, 122), (74, 13.5, 1.0, 122),
        (56, 14.5, 1.5, 126), (68, 14.5, 1.5, 126),
    ]
    hoover_notes = [{"pitch": p, "start_time": st, "duration": dur, "velocity": vel} for (p, st, dur, vel) in hoover_g]
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
    # 05 - DARK REESE DRONE (suelo del breakdown, con el kick fuera)
    # =========================================================================
    t_reese = c.call("live12_track_create", {"type": "midi", "index": -1})["track_index"]
    c.call("live12_track_set_properties", {"track_index": t_reese, "name": "06 [BASS PAD] DARK REESE DRONE (G1)", "color": 49})
    c.call("live12_mixer_set", {"track_index": t_reese, "volume": db_to_norm(-4.5), "pan": 0.0})
    c.call("live12_browser_load_item", {"track_index": t_reese, "browser_item_uri": "Wavetable"})
    c.call("live12_browser_load_item", {"track_index": t_reese, "browser_item_uri": "Chorus-Ensemble"})
    add_surgical_highpass_eq(c, t_reese, freq_norm=0.30)
    reese_notes = [
        {"pitch": 43, "start_time": b, "duration": 3.9, "velocity": 104}
        for b in [x * 0.5 for x in range(0, 32)]
    ]
    create_midi_clip_with_filter_sweep(
        c, t_reese, 0, "Dark Reese Floor (G1)", 16.0, reese_notes,
        blocks(S3_BREAKDOWN[0], S3_BREAKDOWN[1]),
        device_idx=0, cutoff_param_idx=26, cutoff_start=0.22, cutoff_end=0.40, res_param_idx=None,
    )

    # =========================================================================
    # 06 - 909 CLOSED HATS
    # =========================================================================
    t_ch = c.call("live12_track_create", {"type": "audio", "index": -1})["track_index"]
    c.call("live12_track_set_properties", {"track_index": t_ch, "name": "07 [DRUMS] 909 CLOSED HATS (1/16)", "color": 10})
    c.call("live12_mixer_set", {"track_index": t_ch, "volume": db_to_norm(-9.5), "pan": -0.05})
    add_surgical_highpass_eq(c, t_ch, freq_norm=0.42)
    for a, b in (S2_GROOVE, S4_BUILD, S6_DROP1, S7_MINIBREAK, S8_DROP2, S9_OUTRO):
        place_audio_range(c, t_ch, SAMPLE_CH, a, b)

    # =========================================================================
    # 07 - 909 OPEN HAT (contratiempo "&")
    # =========================================================================
    t_oh = c.call("live12_track_create", {"type": "audio", "index": -1})["track_index"]
    c.call("live12_track_set_properties", {"track_index": t_oh, "name": "08 [DRUMS] 909 OPEN HAT (OFFBEAT &)", "color": 12})
    c.call("live12_mixer_set", {"track_index": t_oh, "volume": db_to_norm(-10.5), "pan": 0.05})
    add_surgical_highpass_eq(c, t_oh, freq_norm=0.40)
    for a, b in (S2_GROOVE, S6_DROP1, S8_DROP2):
        place_audio_range(c, t_oh, LOOP_OH_909_WAV, a, b, step_override=16.0)

    # =========================================================================
    # 08 - 909 ACID RIDE (clímax)
    # =========================================================================
    t_ride = c.call("live12_track_create", {"type": "audio", "index": -1})["track_index"]
    c.call("live12_track_set_properties", {"track_index": t_ride, "name": "09 [DRUMS] 909 ACID RIDE (CLIMAX)", "color": 13})
    c.call("live12_mixer_set", {"track_index": t_ride, "volume": db_to_norm(-10.0), "pan": 0.10})
    add_surgical_highpass_eq(c, t_ride, freq_norm=0.38)
    place_audio_range(c, t_ride, LOOP_RIDE_909_WAV, S6_DROP1[0] + 64.0, S6_DROP1[1], step_override=16.0)
    place_audio_range(c, t_ride, LOOP_RIDE_909_WAV, S8_DROP2[0], S8_DROP2[1], step_override=16.0)

    # =========================================================================
    # 09 - PEAK CLAP
    # =========================================================================
    t_clap = c.call("live12_track_create", {"type": "audio", "index": -1})["track_index"]
    c.call("live12_track_set_properties", {"track_index": t_clap, "name": "10 [DRUMS] PEAK CLAP", "color": 11})
    c.call("live12_mixer_set", {"track_index": t_clap, "volume": db_to_norm(-8.5), "pan": 0.0})
    add_surgical_highpass_eq(c, t_clap, freq_norm=0.36)
    for a, b in (S6_DROP1, S8_DROP2):
        place_audio_range(c, t_clap, LOOP_CLAP_16, a, b, step_override=16.0)

    # =========================================================================
    # 10 - RISER + SNARE ROLL (build hacia el silencio pre-drop)
    # =========================================================================
    t_build = c.call("live12_track_create", {"type": "audio", "index": -1})["track_index"]
    c.call("live12_track_set_properties", {"track_index": t_build, "name": "11 [BUILD] RISER + SNARE ROLL (CUT 352)", "color": 55})
    c.call("live12_mixer_set", {"track_index": t_build, "volume": db_to_norm(-7.5), "pan": 0.0})
    add_surgical_highpass_eq(c, t_build, freq_norm=0.30)
    place_audio_range(c, t_build, SAMPLE_RISER, S4_BUILD[0], S4_BUILD[1] - 4.0, step_override=16.0)

    # =========================================================================
    # 11 - GALOPE 1/8T (firma Space 92 en el Drop 2)
    # =========================================================================
    t_gal = c.call("live12_track_create", {"type": "midi", "index": -1})["track_index"]
    c.call("live12_track_set_properties", {"track_index": t_gal, "name": "12 [BASS] GALOPE 1/8T (DROP 2)", "color": 19})
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
        c, t_gal, 0, "Galope 1/8T (Climax)", 16.0, gallop,
        blocks(S8_DROP2[0], S8_DROP2[1]),
        device_idx=0, cutoff_param_idx=170, cutoff_start=0.38, cutoff_end=0.52, res_param_idx=None,
    )

    # =========================================================================
    # 12 - VOCAL PAD (atmósfera del breakdown y del mini-break)
    # =========================================================================
    t_voc = c.call("live12_track_create", {"type": "audio", "index": -1})["track_index"]
    c.call("live12_track_set_properties", {"track_index": t_voc, "name": "13 [ATMOS] G-FRIGIO VOCAL PAD", "color": 58})
    c.call("live12_mixer_set", {"track_index": t_voc, "volume": db_to_norm(-5.0), "pan": 0.0})
    add_surgical_highpass_eq(c, t_voc, freq_norm=0.34)
    c.call("live12_browser_load_item", {"track_index": t_voc, "browser_item_uri": "Reverb"})
    place_audio_range(c, t_voc, os.path.join(
        "/Users/juancruz/ableton-live12-mcp/masterclasses/peak", "loop_g_phrygian_vocal_pad_16b_138bpm.wav"),
        S3_BREAKDOWN[0], S3_BREAKDOWN[1], step_override=16.0)
    place_audio_range(c, t_voc, os.path.join(
        "/Users/juancruz/ableton-live12-mcp/masterclasses/peak", "loop_g_phrygian_vocal_pad_16b_138bpm.wav"),
        S7_MINIBREAK[0], S7_MINIBREAK[1], step_override=16.0)

    # =========================================================================
    # 13 - SUB IMPACT (el golpe del drop)
    # =========================================================================
    t_fx = c.call("live12_track_create", {"type": "audio", "index": -1})["track_index"]
    c.call("live12_track_set_properties", {"track_index": t_fx, "name": "14 [FX] SUB IMPACT (DROP HITS)", "color": 69})
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
    # RETURNS + MASTER BUS
    # =========================================================================
    send_map = [
        (t_kick, 0.0, 0.0), (t_sub, 0.0, 0.0), (t_rumble, 0.22, 0.0),
        (t_hook, 0.18, 0.26), (t_lead, 0.34, 0.12), (t_reese, 0.26, 0.0),
        (t_ch, 0.14, 0.10), (t_oh, 0.16, 0.12), (t_ride, 0.20, 0.0),
        (t_clap, 0.24, 0.0), (t_build, 0.22, 0.0), (t_gal, 0.12, 0.0),
        (t_voc, 0.38, 0.0), (t_fx, 0.10, 0.0),
    ]
    configure_returns_and_master(c, send_map)

    # =========================================================================
    # LOCATORS (con el set ya poblado, la longitud del tema alcanza para todos)
    # =========================================================================
    add_locators(c)

    # =========================================================================
    # NOMBRES + COLORES POR SECCIÓN (grilla legible)
    # =========================================================================
    print("GRAVITY-LIKE SET BUILT: 14 tracks / 176 bars / 138 BPM / G Phrygian")


if __name__ == "__main__":
    build_gravity_like_set()
