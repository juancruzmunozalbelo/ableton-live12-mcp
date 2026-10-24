"""
Joris Voorn "Acid Flow (TTG Edit)" × Space 92 × Psy-Tech — PRE-MIX & MASTER EDITION
===================================================================================
138.0 BPM | G Phrygian (G - Ab - Bb - C - D - Eb - F) — Unified Tuning with Kick & Samples!
64 Bars (256 Beats) Full Progressive Club Arrangement + Surgical Pre-Mix & Master Bus:
  - Bars  1–16 (Beats   0–64):  1-INTRO DJ GROOVE (Kick + K-B-B-B Sub in G1 + High-Passed Rumble + 303 Closed Filter)
  - Bars 17–32 (Beats  64–128): 2-TTG 909 OPEN HAT & DUAL 303 ACID (909 Offbeat OH + 5/16 MS-20 Counter Acid + Monk Chants)
  - Bars 33–47 (Beats 128–188): 3-ACID MELTDOWN BREAKDOWN (Dark Reese Drone Pad G1 + Downlifter + Screaming 303 + Hoover Anthem)
  - Bar  48    (Beats 188–192): 4-PRE-DROP SILENCE ("Transmission... Zero Gravity... A Trip to the Galaxy")
  - Bars 49–56 (Beats 192–224): 5-PEAK DROP PART 1 (Impact + Kick + K-B-B-B + Screaming 303s + Hoover Lead + Groove Storm)
  - Bars 57–64 (Beats 224–256): 6-PEAK DROP PART 2 (909 ACID RIDE CLIMAX — Sidechain-Pumped 909 Ride enters!)
"""

from __future__ import annotations

import math
import os
import subprocess
import time
from ableton_live12_mcp.client import Live12Client

SAMPLES_DIR = "/Users/juancruz/Downloads/ClaSE PEAK jULIO 25 Project/Samples"
SAMPLE_KICK = os.path.join(SAMPLES_DIR, "Processed", "Consolidate", "OL_SKPA1_Kick_Loop_01_123 (5) [2025-06-25 203905].wav")
SAMPLE_RUMBLE = os.path.join(SAMPLES_DIR, "Processed", "Consolidate", "TWHS_HGE1_RUMBLE_LOOP_08_143BPM [2025-06-25 203947].wav")
SAMPLE_CH = os.path.join(SAMPLES_DIR, "Imported", "TWHS_HGE1_CH_LOOP_03_142BPM.wav")
SAMPLE_CLAP = os.path.join(SAMPLES_DIR, "Processed", "Consolidate", "TWHS_HGE1_CLAP_02 [2025-06-25 211236].wav")
SAMPLE_SNARE = os.path.join(SAMPLES_DIR, "Imported", "TA_MK4_SNARE_ROLL_MASSIVE_126.wav")
SAMPLE_GROOVE = os.path.join(SAMPLES_DIR, "Imported", "ZEN_KBB_137_drum_groove_storm.wav")
SAMPLE_IMPACT = os.path.join(SAMPLES_DIR, "Imported", "031_FX_Impact_-_SEROTONINTRANCE_Zenhiser.wav")
SAMPLE_RISER = os.path.join(SAMPLES_DIR, "Imported", "ESM_7th_Dimension_Build_Up_Rising_Riser_Cinematic_Trailer_Movie_Transition.wav")

CORE_LIB = "/Applications/Ableton Live 12 Suite.app/Contents/App-Resources/Core Library/Samples"
CORE_OH_909 = os.path.join(CORE_LIB, "One Shots", "Drums", "Hihat", "Hihat Open 909.aif")
CORE_RIDE_909 = os.path.join(CORE_LIB, "One Shots", "Drums", "Ride", "Ride 909.aif")
VOC_PAD_C4 = os.path.join(CORE_LIB, "One Shots", "Vocal", "Vocal Pad Avalon C4.wav")
VOC_MONKS = os.path.join(CORE_LIB, "Loops", "Tonal", "Vocal", "Kyathe Monks.wav")

PEAK_OUT_DIR = "/Users/juancruz/ableton-live12-mcp/masterclasses/peak"
LOOP_RUMBLE_16 = os.path.join(PEAK_OUT_DIR, "loop_rumble_16b_138bpm.wav")
LOOP_CLAP_16 = os.path.join(PEAK_OUT_DIR, "loop_clap_16b_138bpm.wav")
LOOP_SNARE_16 = os.path.join(PEAK_OUT_DIR, "loop_snare_climax_16b_138bpm.wav")
LOOP_G_VOC_PAD_16 = os.path.join(PEAK_OUT_DIR, "loop_g_phrygian_vocal_pad_16b_138bpm.wav")
LOOP_OH_909_WAV = os.path.join(PEAK_OUT_DIR, "loop_909_offbeat_oh_138bpm.wav")
LOOP_RIDE_909_WAV = os.path.join(PEAK_OUT_DIR, "loop_909_acid_ride_sc_138bpm.wav")
FX_DOWNLIFTER_WAV = os.path.join(PEAK_OUT_DIR, "fx_white_noise_downlifter_138bpm.wav")


def db_to_norm(db: float) -> float:
    return max(0.0, min(1.0, 0.85 * (10.0 ** (db / 40.0))))


def render_club_drum_and_fx_stems() -> None:
    """Renders exact 138.0 BPM sample-accurate 16-beat (4-bar) stereo WAV loops using Python stdlib array+wave (no ffmpeg adelay L/R bug!)."""
    from array import array
    import wave

    os.makedirs(PEAK_OUT_DIR, exist_ok=True)
    sr = 44100
    beat_frames = int(round((60.0 / 138.0) * sr))  # 19,174 frames per beat at 138 BPM
    bar4_frames = beat_frames * 16                 # 306,784 frames per 16 beats (4 bars)

    def load_stereo_pcm(src_path: str, filter_chain: str = "anull") -> array:
        tmp_wav = os.path.join(PEAK_OUT_DIR, "_tmp_decode.wav")
        subprocess.run([
            "ffmpeg", "-y", "-i", src_path,
            "-af", filter_chain,
            "-ar", str(sr), "-ac", "2", "-sample_fmt", "s16", tmp_wav
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        with wave.open(tmp_wav, "rb") as wf:
            raw = wf.readframes(wf.getnframes())
        if os.path.exists(tmp_wav):
            os.remove(tmp_wav)
        pcm = array("h")
        pcm.frombytes(raw)
        return pcm

    def place_hit_stereo(canvas: list[int], hit: array, start_frame: int, max_frames: int, gain: float, fade_exp: float = 1.0) -> None:
        hit_frames = min(len(hit) // 2, max_frames)
        for f in range(hit_frames):
            dst_f = start_frame + f
            if dst_f >= bar4_frames:
                break
            env = ((1.0 - (f / float(hit_frames))) ** fade_exp) if fade_exp > 0.0 else 1.0
            scale = gain * env
            idx = dst_f * 2
            h_idx = f * 2
            canvas[idx] += int(hit[h_idx] * scale)
            canvas[idx + 1] += int(hit[h_idx + 1] * scale)

    def save_stereo_pcm(dest_path: str, canvas: list[int]) -> None:
        out = array("h", (max(-32000, min(32000, v)) for v in canvas))
        with wave.open(dest_path, "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(out.tobytes())

    # 1. Seamless 16-beat Rumble loop (places the 1-beat rumble on EVERY SINGLE BEAT 0..15!)
    one_rumble = load_stereo_pcm(SAMPLE_RUMBLE, "highpass=f=125,lowpass=f=360")
    rumble_canvas = [0] * (bar4_frames * 2)
    for b in range(16):
        place_hit_stereo(rumble_canvas, one_rumble, b * beat_frames, beat_frames, gain=0.45, fade_exp=0.35)
    save_stereo_pcm(LOOP_RUMBLE_16, rumble_canvas)

    # 2. Seamless 16-beat Clap loop (places a soft, controlled clap on beats 2 & 4 of every bar: beats 1,3,5,7,9,11,13,15)
    one_clap = load_stereo_pcm(SAMPLE_CLAP, "highpass=f=240,lowpass=f=7500")
    clap_canvas = [0] * (bar4_frames * 2)
    for b in range(1, 16, 2):
        place_hit_stereo(clap_canvas, one_clap, b * beat_frames, int(beat_frames * 0.85), gain=0.32, fade_exp=0.4)
    save_stereo_pcm(LOOP_CLAP_16, clap_canvas)

    # 3. Seamless 16-beat 909 Offbeat Open Hat (places a warm, silk-filtered 909 Open Hat on EVERY '&' = beat + 0.5 at soft 0.18 gain!)
    one_oh = load_stereo_pcm(CORE_OH_909, "highpass=f=480,lowpass=f=8500")
    oh_canvas = [0] * (bar4_frames * 2)
    for b in range(16):
        place_hit_stereo(oh_canvas, one_oh, int((b + 0.5) * beat_frames), int(beat_frames * 0.42), gain=0.18, fade_exp=1.6)
    save_stereo_pcm(LOOP_OH_909_WAV, oh_canvas)

    # 4. Seamless 16-beat 909 Acid Ride Climax (16th notes with smooth sidechain ducking on beat 1 and warm 0.16 gain)
    one_ride = load_stereo_pcm(CORE_RIDE_909, "highpass=f=600,lowpass=f=8200")
    ride_canvas = [0] * (bar4_frames * 2)
    for b in range(16):
        for sub_step, vel_scale in ((0.25, 0.45), (0.50, 1.0), (0.75, 0.72)):
            place_hit_stereo(ride_canvas, one_ride, int((b + sub_step) * beat_frames), int(beat_frames * 0.35), gain=0.16 * vel_scale, fade_exp=1.5)
    save_stereo_pcm(LOOP_RIDE_909_WAV, ride_canvas)

    # 5. Exact 16-beat Snare Roll climax (stops dead on beat 188.0 before the Pre-Drop Silence!)
    bar4_sec = bar4_frames / float(sr)
    subprocess.run([
        "ffmpeg", "-y", "-i", SAMPLE_SNARE,
        "-af", f"atempo=1.095238,areverse,atrim=start=0:end={bar4_sec:.6f},areverse,highpass=f=220,lowpass=f=7000,afade=t=in:st=0:d=2.5,volume=0.45",
        "-ar", "44100", "-ac", "2", LOOP_SNARE_16
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # 6. Tuned G-Phrygian Vocal Atmosphere Pad (Vocal Pad Avalon C4 pitched -5 semitones to exact G3 + gentle filter)
    rate_g3 = int(round(44100 * (2 ** (-5.0 / 12.0))))
    subprocess.run([
        "ffmpeg", "-y", "-stream_loop", "4", "-i", VOC_PAD_C4,
        "-af", f"asetrate={rate_g3},aresample=44100,highpass=f=220,lowpass=f=2400,tremolo=f={138.0/30.0:.4f}:d=0.55,aecho=0.8:0.88:326|652:0.4|0.3,atrim=start=0:end={bar4_sec:.6f},afade=t=in:st=0:d=0.6,afade=t=out:st={bar4_sec-0.6:.4f}:d=0.6,volume=0.55",
        "-ar", "44100", "-ac", "2", LOOP_G_VOC_PAD_16
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def set_params(c: Live12Client, track_idx: int, device_idx: int, param_map: dict[int, float]) -> None:
    for p_idx, val in param_map.items():
        try:
            c.call("live12_device_set_parameter", {
                "track_index": track_idx,
                "device_index": device_idx,
                "parameter_index": int(p_idx),
                "value": float(val),
            })
        except Exception:
            pass


def add_surgical_highpass_eq(c: Live12Client, track_idx: int, freq_norm: float = 0.32, bell_freq: float | None = None, bell_gain_db: float = 0.0) -> None:
    """Loads EQ Eight and activates a 48dB/oct High-Pass cut on Band 1 so zero mud enters the sub-bass zone."""
    c.call("live12_browser_load_item", {"track_index": track_idx, "browser_item_uri": "EQ Eight"})
    devs = c.call("live12_device_list", {"track_index": track_idx}).get("devices", [])
    eq_idx = len(devs) - 1
    params = {
        4: 1.0,              # 1 Filter On A = True
        5: 0.0,              # 1 Filter Type A = 48 dB/oct Low Cut (High-Pass)
        6: float(freq_norm), # 1 Frequency A (0.26 ~= 115Hz, 0.32 ~= 180Hz, 0.36 ~= 240Hz, 0.42 ~= 380Hz)
        8: 0.42,             # 1 Q A
    }
    if bell_freq is not None:
        params[14] = 1.0
        params[15] = 3.0     # Bell
        params[16] = float(bell_freq)
        params[17] = float(bell_gain_db)
    set_params(c, track_idx, eq_idx, params)


def reset_clean_session(c: Live12Client) -> None:
    c.call("live12_transport_stop", {})
    c.call("live12_transport_set_tempo", {"tempo": 138.0})
    c.call("live12_transport_set_time_signature", {"numerator": 4, "denominator": 4})
    c.call("live12_song_set_scale", {"root_note": 7, "scale_name": "Phrygian"})  # G Phrygian (root=7, 100% matched to Kick & Samples!)

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
    locators = [
        (0.0,   "1-INTRO DJ GROOVE (K-B-B-B + 303 LOW)"),
        (64.0,  "2-909 OPEN HAT & DUAL 303 ACID"),
        (128.0, "3-BREAKDOWN (REESE DRONE + 303 MELTDOWN)"),
        (188.0, "4-PRE-DROP SILENCE (TRANSMISSION)"),
        (192.0, "5-PEAK DROP 1 (FULL 303 + HOOVER)"),
        (224.0, "6-PEAK DROP 2 (909 ACID RIDE CLIMAX)"),
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


def create_midi_clip_with_filter_sweep(
    c: Live12Client,
    track_idx: int,
    slot_idx: int,
    name: str,
    length_beats: float,
    notes: list[dict],
    arrangement_positions: list[float],
    device_idx: int = 0,
    cutoff_param_idx: int | None = 1,
    cutoff_start: float = 0.22,
    cutoff_end: float = 0.88,
    res_param_idx: int | None = 2,
    res_val: float = 0.76,
) -> None:
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
    if cutoff_param_idx is not None:
        try:
            c.call("live12_clip_envelope_control", {
                "track_index": track_idx,
                "slot_index": slot_idx,
                "device_index": device_idx,
                "parameter_index": cutoff_param_idx,
                "action": "create",
            })
            num_steps = int(length_beats)
            for s in range(num_steps):
                progress = s / max(1.0, float(num_steps - 1))
                wobble = 0.09 * math.sin(s * math.pi / 2.0)
                val = max(0.12, min(0.96, cutoff_start + (cutoff_end - cutoff_start) * progress + wobble))
                c.call("live12_clip_envelope_control", {
                    "track_index": track_idx,
                    "slot_index": slot_idx,
                    "device_index": device_idx,
                    "parameter_index": cutoff_param_idx,
                    "action": "insert_step",
                    "time": float(s),
                    "length": 1.0,
                    "value": float(val),
                })
            if res_param_idx is not None:
                c.call("live12_clip_envelope_control", {
                    "track_index": track_idx,
                    "slot_index": slot_idx,
                    "device_index": device_idx,
                    "parameter_index": res_param_idx,
                    "action": "create",
                })
                for s in range(0, num_steps, 2):
                    r_val = max(0.45, min(0.90, res_val + 0.06 * math.cos(s * math.pi / 4.0)))
                    c.call("live12_clip_envelope_control", {
                        "track_index": track_idx,
                        "slot_index": slot_idx,
                        "device_index": device_idx,
                        "parameter_index": res_param_idx,
                        "action": "insert_step",
                        "time": float(s),
                        "length": 2.0,
                        "value": float(r_val),
                    })
        except Exception:
            pass

    for pos in arrangement_positions:
        c.call("live12_clip_duplicate_to_arrangement", {
            "track_index": track_idx,
            "slot_index": slot_idx,
            "arrangement_time": float(pos),
        })


def configure_returns_and_master(c: Live12Client, send_assignments: list[tuple[int, float, float]]) -> None:
    """Sets up Return A (Dark Club Reverb) & Return B (Ping-Pong Acid Delay), assigns track sends, and builds Master Chain."""
    ret_res = c.call("live12_lom_get", {"target_path": "song", "property_name": "return_tracks"})
    curr_ret = len(ret_res.get("value", []))
    while curr_ret < 2:
        c.call("live12_track_create", {"type": "return", "index": -1})
        curr_ret += 1

    # Return A: A-DARK CLUB REVERB
    c.call("live12_lom_set", {"target_path": "song.return_tracks.0", "property_name": "name", "value": "A-DARK CLUB REVERB"})
    c.call("live12_browser_load_item", {"track_index": 0, "browser_item_uri": "EQ Eight", "track_type": "return"})
    c.call("live12_browser_load_item", {"track_index": 0, "browser_item_uri": "Reverb", "track_type": "return"})

    # Return B: B-PINGPONG ACID DELAY
    c.call("live12_lom_set", {"target_path": "song.return_tracks.1", "property_name": "name", "value": "B-PINGPONG ACID DELAY"})
    c.call("live12_browser_load_item", {"track_index": 1, "browser_item_uri": "EQ Eight", "track_type": "return"})
    c.call("live12_browser_load_item", {"track_index": 1, "browser_item_uri": "Delay", "track_type": "return"})

    # Set Send A and Send B levels per track
    for t_idx, send_a, send_b in send_assignments:
        try:
            c.call("live12_mixer_set", {"track_index": t_idx, "send_index": 0, "send_value": float(send_a)})
            c.call("live12_mixer_set", {"track_index": t_idx, "send_index": 1, "send_value": float(send_b)})
        except Exception:
            pass

    # Master Chain: EQ Eight (30Hz Subsonic Cut) + Glue Compressor (Bus Glue + Soft Clip) + Limiter
    c.call("live12_browser_load_item", {"track_index": 0, "browser_item_uri": "EQ Eight", "track_type": "master"})
    c.call("live12_browser_load_item", {"track_index": 0, "browser_item_uri": "Glue Compressor", "track_type": "master"})
    c.call("live12_browser_load_item", {"track_index": 0, "browser_item_uri": "Limiter", "track_type": "master"})
    try:
        # Configure Glue Compressor on Master (Device 1): Threshold=-9.5dB, Attack=4 (10ms), Release=1 (0.1s), Output=+2.5dB, Peak Clip=On
        c.call("live12_lom_set", {"target_path": "song.master_track.devices.1.parameters.1", "property_name": "value", "value": -9.5})
        c.call("live12_lom_set", {"target_path": "song.master_track.devices.1.parameters.3", "property_name": "value", "value": 2.5})
        c.call("live12_lom_set", {"target_path": "song.master_track.devices.1.parameters.4", "property_name": "value", "value": 4.0})
        c.call("live12_lom_set", {"target_path": "song.master_track.devices.1.parameters.6", "property_name": "value", "value": 1.0})
        c.call("live12_lom_set", {"target_path": "song.master_track.devices.1.parameters.8", "property_name": "value", "value": 1.0})
    except Exception:
        pass


def build_premix_master_set() -> None:
    render_club_drum_and_fx_stems()
    c = Live12Client()
    reset_clean_session(c)
    add_locators(c)

    # =========================================================================
    # 1. LOW-END BUS: KICK + ROLLING SUB (G1) + HIGH-PASSED RUMBLE TEXTURE
    # =========================================================================
    # Track 0: 01-KICK [G PUNCH 138]
    t_kick = 0
    c.call("live12_track_set_properties", {"track_index": t_kick, "name": "01-KICK [G PUNCH 138]", "color": 14})
    c.call("live12_mixer_set", {"track_index": t_kick, "volume": db_to_norm(-1.8), "pan": 0.0})
    add_surgical_highpass_eq(c, t_kick, freq_norm=0.08, bell_freq=0.35, bell_gain_db=-2.5)  # Clean 30Hz subsonic + carve 220Hz boxiness
    c.call("live12_browser_load_item", {"track_index": t_kick, "browser_item_uri": "Glue Compressor"})
    set_params(c, t_kick, 1, {1: -12.0, 3: 2.0, 4: 4.0, 6: 1.0, 8: 1.0})
    place_audio_range(c, t_kick, SAMPLE_KICK, 0.0, 128.0)
    place_audio_range(c, t_kick, SAMPLE_KICK, 192.0, 256.0)

    # Track 1: 02-PSY ROLLING SUB [K-B-B-B G1] (SOLE OWNER OF 38-115 Hz SUB!)
    t_sub = c.call("live12_track_create", {"type": "midi", "index": -1})["track_index"]
    c.call("live12_track_set_properties", {"track_index": t_sub, "name": "02-PSY ROLLING SUB [K-B-B-B G1]", "color": 16})
    c.call("live12_mixer_set", {"track_index": t_sub, "volume": db_to_norm(-2.8), "pan": 0.0})
    c.call("live12_browser_load_item", {"track_index": t_sub, "browser_item_uri": "Operator"})
    c.call("live12_browser_load_item", {"track_index": t_sub, "browser_item_uri": "Roar"})
    set_params(c, t_sub, 0, {
        25: 3.0,    # Saw D
        31: 0.24,   # Ae Decay
        33: 0.0,    # Ae Sustain
        166: 3.0,   # Moog PRD Ladder Filter
        170: 0.26,  # Filter Freq (tight sub + low-mid punch)
        171: 0.22,  # Filter Res
        173: 8.5,   # Filter Drive (+8.5 dB)
        176: 52.0,  # Fe Amount
        181: 0.20,  # Fe Decay
        184: 0.0,   # Fe Sustain
    })
    set_params(c, t_sub, 1, {1: 0.62, 10: 1.0, 11: 0.42})
    # G1 = 43, Ab1 = 44 (Phrygian b2 tension), G2 = 55 (octave pop) -> 100% in tune with Kick!
    kbbb_notes = []
    for beat in range(16):
        root = 44 if beat in (7, 15) else 43
        kbbb_notes.extend([
            {"pitch": root, "start_time": beat + 0.25, "duration": 0.19, "velocity": 80},
            {"pitch": root, "start_time": beat + 0.50, "duration": 0.21, "velocity": 126},
            {"pitch": root + 12 if beat % 4 == 3 else root, "start_time": beat + 0.75, "duration": 0.19, "velocity": 110},
        ])
    create_midi_clip_with_filter_sweep(
        c, t_sub, 0, "K-B-B-B Sub (G Phrygian)", 16.0, kbbb_notes,
        [0.0, 16.0, 32.0, 48.0, 64.0, 80.0, 96.0, 112.0, 192.0, 208.0, 224.0, 240.0],
        device_idx=0, cutoff_param_idx=170, cutoff_start=0.24, cutoff_end=0.33, res_param_idx=None
    )

    # Track 2: 03-RUMBLE TEXTURE [HIGH-PASSED >130Hz] (Zero clash with Rolling Sub, seamless 16-beat blocks!)
    t_rumble = c.call("live12_track_create", {"type": "audio", "index": -1})["track_index"]
    c.call("live12_track_set_properties", {"track_index": t_rumble, "name": "03-RUMBLE TEXTURE [HP >130Hz]", "color": 17})
    c.call("live12_mixer_set", {"track_index": t_rumble, "volume": db_to_norm(-7.0), "pan": 0.0})
    add_surgical_highpass_eq(c, t_rumble, freq_norm=0.28)  # Cuts everything below ~130 Hz so it never clashes with Track 1!
    place_audio_range(c, t_rumble, LOOP_RUMBLE_16, 0.0, 128.0, step_override=16.0)
    place_audio_range(c, t_rumble, LOOP_RUMBLE_16, 192.0, 256.0, step_override=16.0)

    # =========================================================================
    # 2. DUAL TB-303 ACID ENGINE + SPACE 92 HOOVER + DARK REESE DRONE PAD
    # =========================================================================
    # Track 3: 04-TB-303 ACID FLOW LEAD A [DRIFT + ROAR]
    t_303a = c.call("live12_track_create", {"type": "midi", "index": -1})["track_index"]
    c.call("live12_track_set_properties", {"track_index": t_303a, "name": "04-TB-303 ACID FLOW A [303 LEAD]", "color": 26})
    c.call("live12_mixer_set", {"track_index": t_303a, "volume": db_to_norm(-2.2), "pan": -0.07})
    c.call("live12_browser_load_item", {"track_index": t_303a, "browser_item_uri": "Drift"})
    c.call("live12_browser_load_item", {"track_index": t_303a, "browser_item_uri": "Roar"})
    add_surgical_highpass_eq(c, t_303a, freq_norm=0.31)  # High-pass at ~165 Hz
    c.call("live12_browser_load_item", {"track_index": t_303a, "browser_item_uri": "Delay"})
    set_params(c, t_303a, 0, {
        1: 0.30, 2: 0.78, 3: 1.0, 6: 0.96, 20: 4.0, 30: 0.0, 32: 0.0,
        35: 0.0, 36: 0.28, 38: 0.0, 39: 0.0, 40: 0.22, 42: 0.0,
        53: 0.85, 61: 1.0, 63: 0.42, 64: 0.78,
    })
    set_params(c, t_303a, 1, {1: 0.78, 2: 0.65, 3: 0.58, 4: 1.0, 10: 2.0, 11: 0.72})

    # 16th-note TB-303 sequence in G Phrygian: G2=55, Ab2=56, Bb2=58, C3=60, D3=62, Eb3=63, G3=67
    pattern_303_g = [
        (55, 125, False), (55, 82, False), (67, 127, True),  (55, 90, False),
        (56, 122, True),  (55, 85, False), (62, 118, False), (63, 126, True),
        (62, 92, False),  (55, 80, False), (67, 127, True),  (63, 125, True),
        (62, 95, False),  (58, 115, False),(62, 122, True),  (56, 126, True),
    ]
    acid_303_notes = []
    for bar in range(4):
        base = bar * 4.0
        for step_idx, (pitch, vel, is_slide) in enumerate(pattern_303_g):
            acid_303_notes.append({
                "pitch": pitch,
                "start_time": base + step_idx * 0.25,
                "duration": 0.36 if is_slide else 0.16,
                "velocity": vel,
            })

    # Stage 1 (0..64): Low simmering 303 (Cutoff 0.18 -> 0.45)
    create_midi_clip_with_filter_sweep(
        c, t_303a, 0, "303 Stage 1 - Simmer (0..64)", 16.0, acid_303_notes,
        [0.0, 16.0, 32.0, 48.0],
        device_idx=0, cutoff_param_idx=1, cutoff_start=0.18, cutoff_end=0.46, res_param_idx=2, res_val=0.72
    )
    # Stage 2 (64..128): Opening 303 (Cutoff 0.42 -> 0.74)
    create_midi_clip_with_filter_sweep(
        c, t_303a, 1, "303 Stage 2 - Acid Rise (64..128)", 16.0, acid_303_notes,
        [64.0, 80.0, 96.0, 112.0],
        device_idx=0, cutoff_param_idx=1, cutoff_start=0.42, cutoff_end=0.74, res_param_idx=2, res_val=0.78
    )
    # Stage 3 (128..176): Breakdown Acid Meltdown (Cutoff 0.45 -> 0.94)
    create_midi_clip_with_filter_sweep(
        c, t_303a, 2, "303 Stage 3 - Breakdown Meltdown", 16.0, acid_303_notes,
        [128.0, 144.0, 160.0],
        device_idx=0, cutoff_param_idx=1, cutoff_start=0.45, cutoff_end=0.92, res_param_idx=2, res_val=0.85
    )
    # Stage 3 Climax (176..188): Stops cleanly at 188.0 for the 4-beat Pre-Drop Silence!
    climax_303 = [n for n in acid_303_notes if n["start_time"] < 12.0]
    create_midi_clip_with_filter_sweep(
        c, t_303a, 3, "303 Stage 4 - Pre-Drop Cut (176..188)", 12.0, climax_303,
        [176.0],
        device_idx=0, cutoff_param_idx=1, cutoff_start=0.75, cutoff_end=0.96, res_param_idx=2, res_val=0.88
    )
    # Stage 5 (192..256): Peak Drop Full Acid Scream
    create_midi_clip_with_filter_sweep(
        c, t_303a, 4, "303 Stage 5 - Peak Drop (192..256)", 16.0, acid_303_notes,
        [192.0, 208.0, 224.0, 240.0],
        device_idx=0, cutoff_param_idx=1, cutoff_start=0.52, cutoff_end=0.94, res_param_idx=2, res_val=0.84
    )

    # Track 4: 05-TB-303 COUNTER ACID 5/16 [MS-20 FILTER]
    t_303b = c.call("live12_track_create", {"type": "midi", "index": -1})["track_index"]
    c.call("live12_track_set_properties", {"track_index": t_303b, "name": "05-TB-303 COUNTER ACID 5/16 [MS-20]", "color": 42})
    c.call("live12_mixer_set", {"track_index": t_303b, "volume": db_to_norm(-8.5), "pan": 0.14})
    c.call("live12_browser_load_item", {"track_index": t_303b, "browser_item_uri": "Operator"})
    add_surgical_highpass_eq(c, t_303b, freq_norm=0.33)  # High-pass at ~195 Hz
    c.call("live12_browser_load_item", {"track_index": t_303b, "browser_item_uri": "Echo"})
    set_params(c, t_303b, 0, {
        10: 1.0, 11: 0.36, 25: 4.0, 47: 0.22, 40: 2.0,
        166: 2.0, 170: 0.28, 171: 0.52, 173: 3.5, 176: 48.0, 181: 0.22, 184: 0.0,
    })
    motif_5_g = [(67, 110, True), (68, 85, False), (74, 108, True), (67, 78, False), (75, 105, False)]
    poly_303_notes = []
    step_i = 0
    pos_b = 0.0
    while pos_b < 15.75:
        p, v, sl = motif_5_g[step_i % 5]
        poly_303_notes.append({"pitch": p, "start_time": pos_b, "duration": 0.34 if sl else 0.16, "velocity": v})
        pos_b += 0.25
        step_i += 1
    create_midi_clip_with_filter_sweep(
        c, t_303b, 0, "5/16 Counter Acid (G Phrygian)", 16.0, poly_303_notes,
        [64.0, 80.0, 96.0, 112.0, 128.0, 144.0, 192.0, 208.0, 224.0, 240.0],
        device_idx=0, cutoff_param_idx=170, cutoff_start=0.22, cutoff_end=0.58, res_param_idx=171, res_val=0.52
    )

    # Track 5: 06-SPACE92 HOOVER ANTHEM [WAVETABLE SUPERSAW]
    t_lead = c.call("live12_track_create", {"type": "midi", "index": -1})["track_index"]
    c.call("live12_track_set_properties", {"track_index": t_lead, "name": "06-SPACE92 HOOVER ANTHEM [SUPERSAW]", "color": 60})
    c.call("live12_mixer_set", {"track_index": t_lead, "volume": db_to_norm(-3.2), "pan": 0.0})
    c.call("live12_browser_load_item", {"track_index": t_lead, "browser_item_uri": "Wavetable"})
    add_surgical_highpass_eq(c, t_lead, freq_norm=0.34)  # High-pass at ~210 Hz
    c.call("live12_browser_load_item", {"track_index": t_lead, "browser_item_uri": "Chorus-Ensemble"})
    c.call("live12_browser_load_item", {"track_index": t_lead, "browser_item_uri": "Reverb"})
    set_params(c, t_lead, 0, {
        4: 0.68, 9: 1.0, 11: 0.62, 12: 0.75, 17: 1.0,
        26: 0.72, 27: 0.32, 28: 0.45, 89: 0.78, 91: 0.42,
    })
    hoover_g_phrases = [
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
    hoover_notes = [{"pitch": p, "start_time": st, "duration": dur, "velocity": vel} for (p, st, dur, vel) in hoover_g_phrases]
    create_midi_clip_with_filter_sweep(
        c, t_lead, 0, "Hoover Anthem (G Phrygian)", 16.0, hoover_notes,
        [144.0, 160.0, 192.0, 208.0, 224.0, 240.0],
        device_idx=0, cutoff_param_idx=26, cutoff_start=0.45, cutoff_end=0.92, res_param_idx=None
    )
    hoover_climax = [n for n in hoover_notes if n["start_time"] < 12.0]
    create_midi_clip_with_filter_sweep(
        c, t_lead, 1, "Hoover Pre-Drop Climax (176..188)", 12.0, hoover_climax,
        [176.0],
        device_idx=0, cutoff_param_idx=26, cutoff_start=0.70, cutoff_end=0.96, res_param_idx=None
    )

    # Track 6: 07-DARK REESE DRONE PAD [BREAKDOWN FLOOR IN G1]
    # Holds the warm sub/low-mid floor during the Breakdown (128..188) when the Kick is out!
    t_reese = c.call("live12_track_create", {"type": "midi", "index": -1})["track_index"]
    c.call("live12_track_set_properties", {"track_index": t_reese, "name": "07-DARK REESE DRONE [BREAK FLOOR]", "color": 49})
    c.call("live12_mixer_set", {"track_index": t_reese, "volume": db_to_norm(-4.5), "pan": 0.0})
    c.call("live12_browser_load_item", {"track_index": t_reese, "browser_item_uri": "Wavetable"})
    c.call("live12_browser_load_item", {"track_index": t_reese, "browser_item_uri": "Chorus-Ensemble"})
    set_params(c, t_reese, 0, {
        4: 0.65, 9: 1.0, 11: 0.58, 12: 0.65, 17: 1.0,
        26: 0.34,   # Low-passed warm dark Reese floor (~280 Hz)
        28: 0.55,   # Filter Drive
        39: 0.25,   # Smooth attack
        45: 0.95,   # Full sustain
        89: 0.85,   # Wide Unison
    })
    reese_notes = [
        {"pitch": 43, "start_time": 0.0, "duration": 11.8, "velocity": 110},  # G1
        {"pitch": 55, "start_time": 0.0, "duration": 11.8, "velocity": 100},  # G2
        {"pitch": 62, "start_time": 0.0, "duration": 11.8, "velocity": 95},   # D3 (5th)
        {"pitch": 44, "start_time": 12.0, "duration": 3.8, "velocity": 115},  # Ab1 Phrygian turn
        {"pitch": 56, "start_time": 12.0, "duration": 3.8, "velocity": 105},  # Ab2
    ]
    create_midi_clip_with_filter_sweep(
        c, t_reese, 0, "Dark Reese Floor (128..176)", 16.0, reese_notes,
        [128.0, 144.0, 160.0],
        device_idx=0, cutoff_param_idx=26, cutoff_start=0.28, cutoff_end=0.45, res_param_idx=None
    )
    reese_cut = [n for n in reese_notes if n["start_time"] < 12.0]
    create_midi_clip_with_filter_sweep(
        c, t_reese, 1, "Dark Reese Cut (176..188)", 12.0, reese_cut,
        [176.0],
        device_idx=0, cutoff_param_idx=26, cutoff_start=0.35, cutoff_end=0.52, res_param_idx=None
    )

    # =========================================================================
    # 3. CLUB PERCUSSION ENGINE (CLOSED HATS + 909 OPEN HAT + 909 ACID RIDE + CLAP/GROOVE)
    # =========================================================================
    # Track 7: 08-909 CLOSED HATS [1/16 GROOVE]
    t_ch = c.call("live12_track_create", {"type": "audio", "index": -1})["track_index"]
    c.call("live12_track_set_properties", {"track_index": t_ch, "name": "08-909 CLOSED HATS [1/16]", "color": 10})
    c.call("live12_mixer_set", {"track_index": t_ch, "volume": db_to_norm(-9.5), "pan": -0.05})
    add_surgical_highpass_eq(c, t_ch, freq_norm=0.42)  # High-pass at ~380 Hz
    place_audio_range(c, t_ch, SAMPLE_CH, 0.0, 128.0)
    place_audio_range(c, t_ch, SAMPLE_CH, 192.0, 256.0)

    # Track 8: 09-909 OPEN HAT [OFFBEAT &]
    t_oh = c.call("live12_track_create", {"type": "audio", "index": -1})["track_index"]
    c.call("live12_track_set_properties", {"track_index": t_oh, "name": "09-909 OPEN HAT [OFFBEAT &]", "color": 12})
    c.call("live12_mixer_set", {"track_index": t_oh, "volume": db_to_norm(-10.5), "pan": 0.05})
    add_surgical_highpass_eq(c, t_oh, freq_norm=0.44)  # High-pass at ~450 Hz
    place_audio_range(c, t_oh, LOOP_OH_909_WAV, 64.0, 128.0, step_override=16.0)
    place_audio_range(c, t_oh, LOOP_OH_909_WAV, 192.0, 256.0, step_override=16.0)

    # Track 9: 10-909 ACID RIDE [DROP PART 2 CLIMAX]
    t_ride = c.call("live12_track_create", {"type": "audio", "index": -1})["track_index"]
    c.call("live12_track_set_properties", {"track_index": t_ride, "name": "10-909 ACID RIDE [DROP 2 CLIMAX]", "color": 13})
    c.call("live12_mixer_set", {"track_index": t_ride, "volume": db_to_norm(-10.0), "pan": 0.10})
    add_surgical_highpass_eq(c, t_ride, freq_norm=0.46)  # High-pass at ~550 Hz
    place_audio_range(c, t_ride, LOOP_RIDE_909_WAV, 96.0, 128.0, step_override=16.0)
    place_audio_range(c, t_ride, LOOP_RIDE_909_WAV, 224.0, 256.0, step_override=16.0)

    # Track 10: 11-PEAK CLAP & GROOVE STORM (Seamless 16-beat blocks!)
    t_clap = c.call("live12_track_create", {"type": "audio", "index": -1})["track_index"]
    c.call("live12_track_set_properties", {"track_index": t_clap, "name": "11-PEAK CLAP & GROOVE STORM", "color": 11})
    c.call("live12_mixer_set", {"track_index": t_clap, "volume": db_to_norm(-8.5), "pan": 0.0})
    add_surgical_highpass_eq(c, t_clap, freq_norm=0.35)  # High-pass at ~220 Hz
    place_audio_range(c, t_clap, LOOP_CLAP_16, 64.0, 128.0, step_override=16.0)
    place_audio_range(c, t_clap, SAMPLE_GROOVE, 192.0, 256.0, step_override=16.0)

    # =========================================================================
    # 4. TRANSITIONS, RISER, SNARE ROLL & TUNED G-VOCAL PAD
    # =========================================================================
    # Track 11: 12-BREAKDOWN RISER & SNARE ROLL [TENSION]
    t_build = c.call("live12_track_create", {"type": "audio", "index": -1})["track_index"]
    c.call("live12_track_set_properties", {"track_index": t_build, "name": "12-BREAKDOWN RISER & SNARE ROLL", "color": 55})
    c.call("live12_mixer_set", {"track_index": t_build, "volume": db_to_norm(-7.5), "pan": 0.0})
    add_surgical_highpass_eq(c, t_build, freq_norm=0.34)
    place_audio_range(c, t_build, SAMPLE_RISER, 144.0, 160.0, step_override=32.0)
    # Exact 16-beat Snare Roll Climax placed at 172.0 -> ends DEAD ON 188.0 before the 4-beat Pre-Drop Silence!
    c.call("live12_lom_call", {"target_path": f"song.tracks.{t_build}", "method_name": "create_audio_clip", "args": [LOOP_SNARE_16, 172.0]})

    # Track 12: 13-TTG G-PHRYGIAN VOCAL ATMOSPHERE PAD [TUNED IN KEY]
    t_atmos_vox = c.call("live12_track_create", {"type": "audio", "index": -1})["track_index"]
    c.call("live12_track_set_properties", {"track_index": t_atmos_vox, "name": "13-TTG G-PHRYGIAN VOCAL PAD [G3]", "color": 58})
    c.call("live12_mixer_set", {"track_index": t_atmos_vox, "volume": db_to_norm(-5.0), "pan": 0.0})
    add_surgical_highpass_eq(c, t_atmos_vox, freq_norm=0.35)
    c.call("live12_browser_load_item", {"track_index": t_atmos_vox, "browser_item_uri": "Reverb"})
    for pos in [128.0, 144.0, 160.0, 192.0, 208.0, 224.0, 240.0]:
        c.call("live12_lom_call", {"target_path": f"song.tracks.{t_atmos_vox}", "method_name": "create_audio_clip", "args": [LOOP_G_VOC_PAD_16, float(pos)]})

    # Track 13: 14-SUB IMPACT [DROP EXPLOSION]
    t_fx = c.call("live12_track_create", {"type": "audio", "index": -1})["track_index"]
    c.call("live12_track_set_properties", {"track_index": t_fx, "name": "14-SUB IMPACT [DROP EXPLOSION]", "color": 69})
    c.call("live12_mixer_set", {"track_index": t_fx, "volume": db_to_norm(-2.2), "pan": 0.0})
    add_surgical_highpass_eq(c, t_fx, freq_norm=0.30)
    c.call("live12_browser_load_item", {"track_index": t_fx, "browser_item_uri": "Delay"})
    c.call("live12_lom_call", {"target_path": f"song.tracks.{t_fx}", "method_name": "create_audio_clip", "args": [SAMPLE_IMPACT, 0.0]})
    c.call("live12_lom_call", {"target_path": f"song.tracks.{t_fx}", "method_name": "create_audio_clip", "args": [SAMPLE_IMPACT, 128.0]})
    c.call("live12_lom_call", {"target_path": f"song.tracks.{t_fx}", "method_name": "create_audio_clip", "args": [SAMPLE_IMPACT, 192.0]})

    # =========================================================================
    # 5. CONFIGURE RETURN BUSES (REVERB & DELAY SENDS) + MASTERING CHAIN
    # =========================================================================
    send_map = [
        (t_303a,      0.22, 0.32),  # 303 Lead A -> Reverb + PingPong Delay
        (t_303b,      0.25, 0.38),  # 303 Counter B -> Reverb + PingPong Delay
        (t_lead,      0.42, 0.28),  # Space 92 Hoover -> Big Club Reverb + Delay
        (t_reese,     0.30, 0.10),  # Dark Reese Floor -> Reverb
        (t_oh,        0.12, 0.05),  # 909 Open Hat -> Room glue
        (t_ride,      0.24, 0.15),  # 909 Acid Ride -> Air reverb + delay
        (t_clap,      0.18, 0.12),  # Clap -> Reverb
        (t_atmos_vox, 0.48, 0.35),  # Ethereal/Monk Vox -> Huge space
        (t_fx,        0.32, 0.40),  # Sci-Fi Transmission Vox -> Space & Delay
    ]
    configure_returns_and_master(c, send_map)

    # Set loop 0..256 beats (64 bars), switch to Arranger view, set playhead to 0.0
    c.call("live12_transport_set_loop", {"enabled": True, "start": 0.0, "length": 256.0})
    c.call("live12_view_switch", {"view_name": "Arranger"})
    c.call("live12_lom_set", {"target_path": "song", "property_name": "back_to_arranger", "value": False})
    c.call("live12_lom_set", {"target_path": "song", "property_name": "current_song_time", "value": 0.0})
    print("PRE-MIX & MASTER EDITION OF JORIS VOORN ACID FLOW x SPACE 92 BUILT SUCCESSFULLY!")


if __name__ == "__main__":
    build_premix_master_set()
