"""
Space 92 "Gravity" × Joris Voorn "Trip to Galaxy" × Psy-Tech Live Builder
=========================================================================
Builds a complete, playable 32-bar (128-beat) multi-section arrangement in
Ableton Live 12 Suite via MCP at 136.0 BPM in G Phrygian / G Minor:
  - Bars  1–8  (Beats   0–32): 1-INTRO K-B-B-B GROOVE (Kick + Rolling Psy Sub + Rumble + Hats)
  - Bars  9–16 (Beats  32–64): 2-TTG POLYRHYTHM & ACID CALL (5/16 Polyrhythm + Acid 303 Call + FM Squelch Response)
  - Bars 17–23 (Beats  64–92): 3-GRAVITY BREAKDOWN (Kick cuts out, Hoover Supersaw Lead + Riser + Snare Roll)
  - Bar  24    (Beats  92–96): 4-PRE-DROP SILENCE (Vocal hook in the gap before impact)
  - Bars 25–32 (Beats 96–128): 5-SPACE92 x PSYTECH PEAK DROP (Full Impact + Kick + K-B-B-B + Hoover Lead + Acid + Groove)
"""

from __future__ import annotations

import os
import time
from ableton_live12_mcp.client import Live12Client

SAMPLES_DIR = "/Users/juancruz/Downloads/ClaSE PEAK jULIO 25 Project/Samples"
SAMPLE_KICK = os.path.join(SAMPLES_DIR, "Processed", "Consolidate", "OL_SKPA1_Kick_Loop_01_123 (5) [2025-06-25 203905].wav")
SAMPLE_RUMBLE = os.path.join(SAMPLES_DIR, "Processed", "Consolidate", "TWHS_HGE1_RUMBLE_LOOP_08_143BPM [2025-06-25 203947].wav")
SAMPLE_CH = os.path.join(SAMPLES_DIR, "Imported", "TWHS_HGE1_CH_LOOP_03_142BPM.wav")
SAMPLE_CLAP = os.path.join(SAMPLES_DIR, "Processed", "Consolidate", "TWHS_HGE1_CLAP_02 [2025-06-25 211236].wav")
SAMPLE_VOCAL = os.path.join(SAMPLES_DIR, "Processed", "Consolidate", "AU_MTF2_126_vocal_rap_doubles_female_get_naughty_sex_pills_dry_Gmin [2025-06-25 211605].wav")
SAMPLE_SNARE = os.path.join(SAMPLES_DIR, "Imported", "TA_MK4_SNARE_ROLL_MASSIVE_126.wav")
SAMPLE_GROOVE = os.path.join(SAMPLES_DIR, "Imported", "ZEN_KBB_137_drum_groove_storm.wav")
SAMPLE_IMPACT = os.path.join(SAMPLES_DIR, "Imported", "031_FX_Impact_-_SEROTONINTRANCE_Zenhiser.wav")
SAMPLE_RISER = os.path.join(SAMPLES_DIR, "Imported", "ESM_7th_Dimension_Build_Up_Rising_Riser_Cinematic_Trailer_Movie_Transition.wav")
SAMPLE_OMNI = os.path.join(SAMPLES_DIR, "Processed", "Bounce", "Bounce 7-Omnisphere [2025-06-25 210111]-2.wav")


def db_to_norm(db: float) -> float:
    return max(0.0, min(1.0, 0.85 * (10.0 ** (db / 40.0))))


def reset_clean_session(c: Live12Client) -> None:
    c.call("live12_transport_stop", {})
    c.call("live12_transport_set_tempo", {"tempo": 136.0})
    c.call("live12_transport_set_time_signature", {"numerator": 4, "denominator": 4})
    c.call("live12_song_set_scale", {"root_note": 7, "scale_name": "Phrygian"})

    # Create 1 clean anchor audio track at the end, then delete all previous tracks
    c.call("live12_track_create", {"type": "audio", "index": -1})
    st = c.call("live12_song_get_state", {})
    for idx in range(st["tracks_count"] - 2, -1, -1):
        try:
            c.call("live12_track_delete", {"track_index": idx})
        except Exception:
            pass

    # Delete existing cue points
    cues = c.call("live12_cue_point_control", {"action": "list"}).get("cue_points", [])
    for cp in reversed(cues):
        try:
            c.call("live12_cue_point_control", {"action": "delete", "cue_index": cp["index"]})
        except Exception:
            pass


def add_locators(c: Live12Client) -> None:
    locators = [
        (0.0, "1-INTRO K-B-B-B GROOVE"),
        (32.0, "2-TTG POLYRHYTHM & ACID CALL"),
        (64.0, "3-GRAVITY BREAKDOWN (HOOVER)"),
        (92.0, "4-PRE-DROP SILENCE"),
        (96.0, "5-SPACE92 x PSYTECH DROP"),
    ]
    for beat, name in locators:
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


def place_audio_range(c: Live12Client, track_idx: int, sample_path: str, start_beat: float, end_beat: float, step_override: float | None = None) -> None:
    if not os.path.exists(sample_path):
        return
    c.call("live12_lom_call", {"target_path": f"song.tracks.{track_idx}", "method_name": "create_audio_clip", "args": [sample_path, float(start_beat)]})
    ac = c.call("live12_lom_get", {"target_path": f"song.tracks.{track_idx}", "property_name": "arrangement_clips"}).get("value", [])
    if not ac:
        return
    clip_len = float(c.call("live12_lom_get", {"target_path": f"song.tracks.{track_idx}.arrangement_clips.{len(ac)-1}", "property_name": "length"}).get("value", 8.0))
    step = step_override or max(4.0, clip_len)
    pos = start_beat + step
    while pos + 0.1 < end_beat:
        c.call("live12_lom_call", {"target_path": f"song.tracks.{track_idx}", "method_name": "create_audio_clip", "args": [sample_path, float(pos)]})
        pos += step


def create_midi_section(c: Live12Client, track_idx: int, slot_idx: int, name: str, length_beats: float, notes: list[dict], arrangement_positions: list[float]) -> None:
    c.call("live12_clip_create", {
        "track_index": track_idx,
        "slot_index": slot_idx,
        "length_beats": float(length_beats),
        "name": name,
    })
    c.call("live12_clip_add_notes", {
        "track_index": track_idx,
        "slot_index": slot_idx,
        "notes": notes,
    })
    for pos in arrangement_positions:
        c.call("live12_clip_duplicate_to_arrangement", {
            "track_index": track_idx,
            "slot_index": slot_idx,
            "arrangement_time": float(pos),
        })


def build_gravity_psytech_set() -> None:
    c = Live12Client()
    reset_clean_session(c)
    add_locators(c)

    # Track 0 is already our anchor audio track -> configure as 01-KICK [SPACE92 PUNCH]
    t_kick = 0
    c.call("live12_track_set_properties", {"track_index": t_kick, "name": "01-KICK [SPACE92 PUNCH]", "color": 14})
    c.call("live12_mixer_set", {"track_index": t_kick, "volume": db_to_norm(-2.0), "pan": 0.0})
    c.call("live12_browser_load_item", {"track_index": t_kick, "browser_item_uri": "EQ Eight"})
    c.call("live12_browser_load_item", {"track_index": t_kick, "browser_item_uri": "Glue Compressor"})
    # Kick plays in Intro/Groove (0..64), cuts in Breakdown (64..96), slams in Drop (96..128)
    place_audio_range(c, t_kick, SAMPLE_KICK, 0.0, 64.0)
    place_audio_range(c, t_kick, SAMPLE_KICK, 96.0, 128.0)

    # Track 1: 02-PSY ROLLING SUB [K-B-B-B] (MIDI - Operator + Roar + EQ Eight)
    t_sub = c.call("live12_track_create", {"type": "midi", "index": -1})["track_index"]
    c.call("live12_track_set_properties", {"track_index": t_sub, "name": "02-PSY ROLLING SUB [K-B-B-B]", "color": 16})
    c.call("live12_mixer_set", {"track_index": t_sub, "volume": db_to_norm(-3.5), "pan": 0.0})
    c.call("live12_browser_load_item", {"track_index": t_sub, "browser_item_uri": "Operator"})
    c.call("live12_browser_load_item", {"track_index": t_sub, "browser_item_uri": "Roar"})
    c.call("live12_browser_load_item", {"track_index": t_sub, "browser_item_uri": "EQ Eight"})
    # Program exact K-B-B-B (steps e, &, a = +0.25, +0.50, +0.75 of every beat) in G1 (43) with Phrygian Ab1 (44) turn
    kbbb_notes = []
    for beat in range(16):
        root = 44 if beat in (7, 15) else 43  # G1 -> Ab1 Phrygian tension on end of 2-bar & 4-bar phrases
        kbbb_notes.extend([
            {"pitch": root, "start_time": beat + 0.25, "duration": 0.20, "velocity": 82},
            {"pitch": root, "start_time": beat + 0.50, "duration": 0.22, "velocity": 124},
            {"pitch": root + 12 if beat % 4 == 3 else root, "start_time": beat + 0.75, "duration": 0.20, "velocity": 108},
        ])
    create_midi_section(c, t_sub, 0, "Psy-Tech K-B-B-B (G Phrygian)", 16.0, kbbb_notes, [0.0, 16.0, 32.0, 48.0, 96.0, 112.0])

    # Track 2: 03-RUMBLE SUB TEXTURE [SPACE92 LOW] (Audio)
    t_rumble = c.call("live12_track_create", {"type": "audio", "index": -1})["track_index"]
    c.call("live12_track_set_properties", {"track_index": t_rumble, "name": "03-RUMBLE SUB TEXTURE [LOW]", "color": 17})
    c.call("live12_mixer_set", {"track_index": t_rumble, "volume": db_to_norm(-6.5), "pan": 0.0})
    place_audio_range(c, t_rumble, SAMPLE_RUMBLE, 0.0, 64.0)
    place_audio_range(c, t_rumble, SAMPLE_RUMBLE, 96.0, 128.0)

    # Track 3: 04-ACID 303 STAB [CALL - DRIFT] (MIDI)
    t_acid = c.call("live12_track_create", {"type": "midi", "index": -1})["track_index"]
    c.call("live12_track_set_properties", {"track_index": t_acid, "name": "04-ACID 303 STAB [CALL - DRIFT]", "color": 26})
    c.call("live12_mixer_set", {"track_index": t_acid, "volume": db_to_norm(-5.0), "pan": -0.15})
    c.call("live12_browser_load_item", {"track_index": t_acid, "browser_item_uri": "Drift"})
    c.call("live12_browser_load_item", {"track_index": t_acid, "browser_item_uri": "Roar"})
    c.call("live12_browser_load_item", {"track_index": t_acid, "browser_item_uri": "Delay"})
    # Call pattern on Bars 1 & 3 (beats 2..4 and 10..12)
    acid_notes = []
    for bar_base in [0.0, 8.0]:
        acid_notes.extend([
            {"pitch": 55, "start_time": bar_base + 2.00, "duration": 0.25, "velocity": 120},  # G2
            {"pitch": 56, "start_time": bar_base + 2.25, "duration": 0.50, "velocity": 125},  # Ab2 (Phrygian b2 accent!)
            {"pitch": 55, "start_time": bar_base + 3.00, "duration": 0.25, "velocity": 115},  # G2
            {"pitch": 62, "start_time": bar_base + 3.25, "duration": 0.25, "velocity": 122},  # D3
            {"pitch": 63, "start_time": bar_base + 3.50, "duration": 0.40, "velocity": 126},  # Eb3 (b6 accent!)
        ])
    create_midi_section(c, t_acid, 0, "Acid 303 Call (G->Ab)", 16.0, acid_notes, [32.0, 48.0, 96.0, 112.0])

    # Track 4: 05-PSY FM SQUELCH [RESPONSE - OPERATOR] (MIDI)
    t_squelch = c.call("live12_track_create", {"type": "midi", "index": -1})["track_index"]
    c.call("live12_track_set_properties", {"track_index": t_squelch, "name": "05-PSY FM SQUELCH [RESPONSE]", "color": 42})
    c.call("live12_mixer_set", {"track_index": t_squelch, "volume": db_to_norm(-5.5), "pan": 0.18})
    c.call("live12_browser_load_item", {"track_index": t_squelch, "browser_item_uri": "Operator"})
    c.call("live12_browser_load_item", {"track_index": t_squelch, "browser_item_uri": "Echo"})
    # Response pattern on Bars 2 & 4 (beats 6..8 and 14..16)
    squelch_notes = []
    for bar_base in [4.0, 12.0]:
        squelch_notes.extend([
            {"pitch": 67, "start_time": bar_base + 2.00, "duration": 0.18, "velocity": 118},  # G3
            {"pitch": 68, "start_time": bar_base + 2.25, "duration": 0.18, "velocity": 124},  # Ab3
            {"pitch": 74, "start_time": bar_base + 2.50, "duration": 0.35, "velocity": 127},  # D4
            {"pitch": 68, "start_time": bar_base + 3.00, "duration": 0.20, "velocity": 115},  # Ab3
            {"pitch": 67, "start_time": bar_base + 3.50, "duration": 0.40, "velocity": 122},  # G3
        ])
    create_midi_section(c, t_squelch, 0, "Psy FM Squelch Response", 16.0, squelch_notes, [32.0, 48.0, 96.0, 112.0])

    # Track 5: 06-TTG POLYRHYTHM 5/16 [JORIS VOORN - MELD] (MIDI)
    t_poly = c.call("live12_track_create", {"type": "midi", "index": -1})["track_index"]
    c.call("live12_track_set_properties", {"track_index": t_poly, "name": "06-TTG POLYRHYTHM 5/16 [MELD]", "color": 48})
    c.call("live12_mixer_set", {"track_index": t_poly, "volume": db_to_norm(-6.0), "pan": 0.0})
    c.call("live12_browser_load_item", {"track_index": t_poly, "browser_item_uri": "Meld"})
    c.call("live12_browser_load_item", {"track_index": t_poly, "browser_item_uri": "Reverb"})
    # 5-sixteenth-note cycle (5 * 0.25 = 1.25 beats per cycle) rotating over 16 beats
    motif_5_16 = [67, 68, 74, 70, 75]  # G3, Ab3, D4, Bb3, Eb4
    poly_notes = []
    step_idx = 0
    t_pos = 0.0
    while t_pos < 15.75:
        pitch = motif_5_16[step_idx % 5]
        vel = 122 if (step_idx % 5 == 0) else 94  # Accent step 1 of every 5-step group!
        poly_notes.append({"pitch": pitch, "start_time": t_pos, "duration": 0.22, "velocity": vel})
        t_pos += 0.25
        step_idx += 1
    create_midi_section(c, t_poly, 0, "TTG 5/16 Polyrhythm", 16.0, poly_notes, [32.0, 48.0, 64.0, 96.0, 112.0])

    # Track 6: 07-GRAVITY HOOVER LEAD [SPACE92 SUPERSAW] (MIDI - Wavetable + Chorus + Overdrive + Reverb)
    t_lead = c.call("live12_track_create", {"type": "midi", "index": -1})["track_index"]
    c.call("live12_track_set_properties", {"track_index": t_lead, "name": "07-GRAVITY HOOVER LEAD [SPACE92]", "color": 60})
    c.call("live12_mixer_set", {"track_index": t_lead, "volume": db_to_norm(-3.0), "pan": 0.0})
    c.call("live12_browser_load_item", {"track_index": t_lead, "browser_item_uri": "Wavetable"})
    c.call("live12_browser_load_item", {"track_index": t_lead, "browser_item_uri": "Chorus-Ensemble"})
    c.call("live12_browser_load_item", {"track_index": t_lead, "browser_item_uri": "Reverb"})
    # Iconic Space 92 "Gravity" style soaring Phrygian Lead (Octave-stacked G3/G4 -> D4/D5 -> Eb4/Eb5 -> Bb3/Bb4 -> Ab3/Ab4 -> G3/G4)
    lead_phrases = [
        # Bar 1: G -> D -> Eb
        (55, 0.0, 1.5, 124), (67, 0.0, 1.5, 124),
        (62, 1.5, 1.0, 120), (74, 1.5, 1.0, 120),
        (63, 2.5, 1.5, 127), (75, 2.5, 1.5, 127),
        # Bar 2: D -> Bb -> Ab -> G
        (62, 4.0, 1.5, 122), (74, 4.0, 1.5, 122),
        (58, 5.5, 1.0, 118), (70, 5.5, 1.0, 118),
        (56, 6.5, 1.5, 126), (68, 6.5, 1.5, 126),
        # Bar 3: G -> Ab -> Bb -> D
        (55, 8.0, 1.5, 124), (67, 8.0, 1.5, 124),
        (56, 9.5, 1.0, 122), (68, 9.5, 1.0, 122),
        (58, 10.5, 1.5, 125), (70, 10.5, 1.5, 125),
        # Bar 4: Eb -> D -> Ab -> G
        (63, 12.0, 1.5, 127), (75, 12.0, 1.5, 127),
        (62, 13.5, 1.0, 122), (74, 13.5, 1.0, 122),
        (56, 14.5, 1.5, 126), (68, 14.5, 1.5, 126),
    ]
    gravity_notes = [
        {"pitch": p, "start_time": st, "duration": dur, "velocity": vel}
        for (p, st, dur, vel) in lead_phrases
    ]
    # Breakdown (64..80) + Peak Drop (96..128)
    create_midi_section(c, t_lead, 0, "Gravity Hoover Anthem", 16.0, gravity_notes, [64.0, 96.0, 112.0])

    # Shorter 12-beat Breakdown Climax phrase (80..92) stopping cleanly at 92.0 for the 4-beat Pre-Drop Silence!
    climax_notes = [n for n in gravity_notes if n["start_time"] < 12.0]
    create_midi_section(c, t_lead, 1, "Gravity Pre-Drop Climax", 12.0, climax_notes, [80.0])

    # Track 7: 08-909 HATS & RIDE DRIVE (Audio)
    t_hats = c.call("live12_track_create", {"type": "audio", "index": -1})["track_index"]
    c.call("live12_track_set_properties", {"track_index": t_hats, "name": "08-909 HATS & OFFBEAT DRIVE", "color": 10})
    c.call("live12_mixer_set", {"track_index": t_hats, "volume": db_to_norm(-6.5), "pan": 0.0})
    place_audio_range(c, t_hats, SAMPLE_CH, 0.0, 64.0)
    place_audio_range(c, t_hats, SAMPLE_CH, 96.0, 128.0)

    # Track 8: 09-PEAK CLAP & GROOVE STORM (Audio)
    t_clap = c.call("live12_track_create", {"type": "audio", "index": -1})["track_index"]
    c.call("live12_track_set_properties", {"track_index": t_clap, "name": "09-PEAK CLAP & GROOVE STORM", "color": 11})
    c.call("live12_mixer_set", {"track_index": t_clap, "volume": db_to_norm(-5.5), "pan": 0.0})
    place_audio_range(c, t_clap, SAMPLE_CLAP, 32.0, 64.0)
    place_audio_range(c, t_clap, SAMPLE_GROOVE, 96.0, 128.0)

    # Track 9: 10-BREAKDOWN RISER & SNARE ROLL (Audio)
    t_build = c.call("live12_track_create", {"type": "audio", "index": -1})["track_index"]
    c.call("live12_track_set_properties", {"track_index": t_build, "name": "10-BREAKDOWN RISER & SNARE ROLL", "color": 55})
    c.call("live12_mixer_set", {"track_index": t_build, "volume": db_to_norm(-5.0), "pan": 0.0})
    place_audio_range(c, t_build, SAMPLE_RISER, 64.0, 80.0, step_override=32.0)
    place_audio_range(c, t_build, SAMPLE_SNARE, 76.0, 92.0, step_override=16.0)

    # Track 10: 11-TTG ETHEREAL & MONK CHANT [VOX] (Audio)
    core_voc_dir = "/Applications/Ableton Live 12 Suite.app/Contents/App-Resources/Core Library/Samples/Loops/Tonal/Vocal"
    voc_rev_swell = os.path.join(core_voc_dir, "L10 Demo Voc Reverse.aif")
    voc_ethereal = os.path.join(core_voc_dir, "L10 Demo Voc Reverb 1.aif")
    voc_monks = os.path.join(core_voc_dir, "Kyathe Monks.wav")
    ttg_vox_wav = "/Users/juancruz/ableton-live12-mcp/masterclasses/peak/ttg_gravity_transmission_vox.wav"

    t_atmos_vox = c.call("live12_track_create", {"type": "audio", "index": -1})["track_index"]
    c.call("live12_track_set_properties", {"track_index": t_atmos_vox, "name": "11-TTG ETHEREAL & MONK CHANT [VOX]", "color": 58})
    c.call("live12_mixer_set", {"track_index": t_atmos_vox, "volume": db_to_norm(-4.0), "pan": 0.0})
    c.call("live12_browser_load_item", {"track_index": t_atmos_vox, "browser_item_uri": "EQ Eight"})
    c.call("live12_browser_load_item", {"track_index": t_atmos_vox, "browser_item_uri": "Reverb"})
    for pos in [32.0, 48.0]:
        c.call("live12_lom_call", {"target_path": f"song.tracks.{t_atmos_vox}", "method_name": "create_audio_clip", "args": [voc_monks, float(pos)]})
    for pos in [64.0, 96.0, 112.0]:
        c.call("live12_lom_call", {"target_path": f"song.tracks.{t_atmos_vox}", "method_name": "create_audio_clip", "args": [voc_ethereal, float(pos)]})
    c.call("live12_lom_call", {"target_path": f"song.tracks.{t_atmos_vox}", "method_name": "create_audio_clip", "args": [voc_rev_swell, 80.0]})

    # Track 11: 12-TRANSMISSION SCI-FI VOX & IMPACT [GRAVITY] (Audio)
    t_fx = c.call("live12_track_create", {"type": "audio", "index": -1})["track_index"]
    c.call("live12_track_set_properties", {"track_index": t_fx, "name": "12-TRANSMISSION SCI-FI VOX & IMPACT", "color": 69})
    c.call("live12_mixer_set", {"track_index": t_fx, "volume": db_to_norm(-2.5), "pan": 0.0})
    c.call("live12_browser_load_item", {"track_index": t_fx, "browser_item_uri": "Delay"})
    c.call("live12_lom_call", {"target_path": f"song.tracks.{t_fx}", "method_name": "create_audio_clip", "args": [SAMPLE_IMPACT, 0.0]})
    if os.path.exists(ttg_vox_wav):
        c.call("live12_lom_call", {"target_path": f"song.tracks.{t_fx}", "method_name": "create_audio_clip", "args": [ttg_vox_wav, 64.0]})
        c.call("live12_lom_call", {"target_path": f"song.tracks.{t_fx}", "method_name": "create_audio_clip", "args": [ttg_vox_wav, 84.0]})
    c.call("live12_lom_call", {"target_path": f"song.tracks.{t_fx}", "method_name": "create_audio_clip", "args": [SAMPLE_IMPACT, 96.0]})

    # Set loop 0..128 beats (32 bars), switch to Arranger view, disable back_to_arranger, set playhead to 0.0
    c.call("live12_transport_set_loop", {"enabled": True, "start": 0.0, "length": 128.0})
    c.call("live12_view_switch", {"view_name": "Arranger"})
    c.call("live12_lom_set", {"target_path": "song", "property_name": "back_to_arranger", "value": False})
    c.call("live12_lom_set", {"target_path": "song", "property_name": "current_song_time", "value": 0.0})
    print("SPACE 92 GRAVITY x TTG x PSY-TECH SET BUILT SUCCESSFULLY!")


if __name__ == "__main__":
    build_gravity_psytech_set()
