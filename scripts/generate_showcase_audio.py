#!/usr/bin/env python3
"""
Electronic Music Audio Showcase & Manifest Generator for Ableton Live 12 MCP.
Synthesizes an 8-bar Melodic Techno / Deep Tech audio track in C Minor at 124 BPM.
Zero external dependencies (pure Python wave, struct, math, json, pathlib).

Specs:
- Format: 44.1 kHz, 16-bit signed PCM stereo WAV
- Tempo: 124.0 BPM (4/4 time signature)
- Musical Structure: C Minor, 8 bars, 32 beats, ~15.48s
- Peak Normalization: -1.0 dBFS (peak amplitude ~0.89125)
- Session Manifest: Full tracks, devices, extended LOM notes, and MCP recipe
"""

import argparse
import json
import math
import os
from pathlib import Path
import struct
import wave

SAMPLE_RATE = 44100
BPM = 124.0
BEATS_PER_BAR = 4
TOTAL_BARS = 8
TOTAL_BEATS = TOTAL_BARS * BEATS_PER_BAR
BEAT_DURATION = 60.0 / BPM
TOTAL_DURATION = TOTAL_BEATS * BEAT_DURATION
NUM_SAMPLES = int(TOTAL_DURATION * SAMPLE_RATE)


def generate_showcase_audio(output_wav_path: str) -> None:
    left_buf = [0.0] * NUM_SAMPLES
    right_buf = [0.0] * NUM_SAMPLES

    def add_sample(buf, idx, val):
        if 0 <= idx < NUM_SAMPLES:
            buf[idx] += val

    def midi_to_freq(note: float) -> float:
        return 440.0 * (2.0 ** ((note - 69.0) / 12.0))

    # 1. Kick Drum (4-on-the-floor, pitch sweep 160Hz -> 45Hz)
    kick_len = int(0.24 * SAMPLE_RATE)
    for beat in range(TOTAL_BEATS):
        start_sample = int(beat * BEAT_DURATION * SAMPLE_RATE)
        for i in range(kick_len):
            t = i / SAMPLE_RATE
            idx = start_sample + i
            if idx >= NUM_SAMPLES:
                break
            phase = 2.0 * math.pi * (45.0 * t - (115.0 / 32.0) * math.exp(-32.0 * t))
            body = math.sin(phase) * math.exp(-14.0 * t)
            click = (1.0 - 2.0 * (t / 0.005)) if t < 0.005 else 0.0
            val = (0.85 * body + 0.15 * click) * 0.75
            add_sample(left_buf, idx, val)
            add_sample(right_buf, idx, val)

    # 2. Closed & Open Hi-Hats (16th-note grid)
    hat_state = 0x12345678

    def noise() -> float:
        nonlocal hat_state
        hat_state = (hat_state * 1664525 + 1013904223) & 0xFFFFFFFF
        return (hat_state / 0x80000000) - 1.0

    sixteenth_beats = TOTAL_BEATS * 4
    for s_idx in range(sixteenth_beats):
        beat_pos = s_idx / 4.0
        start_sample = int(beat_pos * BEAT_DURATION * SAMPLE_RATE)
        is_offbeat = (s_idx % 4 == 2)
        is_regular = (s_idx % 4 != 0)

        if is_offbeat:
            # Open hat (accent on offbeat 16ths)
            oh_len = int(0.18 * SAMPLE_RATE)
            for i in range(oh_len):
                t = i / SAMPLE_RATE
                idx = start_sample + i
                n = noise() * math.exp(-18.0 * t) * 0.22
                add_sample(left_buf, idx, n * 0.7)
                add_sample(right_buf, idx, n * 1.0)
        elif is_regular:
            # Closed hat with velocity groove
            ch_len = int(0.04 * SAMPLE_RATE)
            vel = 0.12 if (s_idx % 2 == 1) else 0.18
            for i in range(ch_len):
                t = i / SAMPLE_RATE
                idx = start_sample + i
                n = noise() * math.exp(-85.0 * t) * vel
                add_sample(left_buf, idx, n * 0.9)
                add_sample(right_buf, idx, n * 0.7)

    # 3. Snare / Clap on beats 2 and 4 (beat indices 1 and 3)
    for bar in range(TOTAL_BARS):
        for snare_beat in [1, 3]:
            beat_num = bar * BEATS_PER_BAR + snare_beat
            start_sample = int(beat_num * BEAT_DURATION * SAMPLE_RATE)
            snare_len = int(0.20 * SAMPLE_RATE)
            for i in range(snare_len):
                t = i / SAMPLE_RATE
                idx = start_sample + i
                env = math.exp(-22.0 * t)
                tone = math.sin(2.0 * math.pi * 185.0 * t) * math.exp(-35.0 * t) * 0.3
                val = (noise() * 0.7 + tone) * env * 0.35
                add_sample(left_buf, idx, val * 0.8)
                add_sample(right_buf, idx, val * 0.8)

    # 4. Acid / Sub Bassline (C Minor)
    bass_pattern = [
        (0.0, 36, 0.75, 0.5),
        (0.75, 36, 0.6, 0.25),
        (1.25, 39, 0.7, 0.25),
        (1.75, 36, 0.6, 0.25),
        (2.25, 41, 0.75, 0.5),
        (3.0, 43, 0.8, 0.5),
        (3.75, 46, 0.65, 0.25),
    ]

    for bar in range(TOTAL_BARS):
        bar_start_beat = bar * 4
        octave_shift = 12 if (bar in [3, 7]) else 0
        for rel_beat, note, vel, dur in bass_pattern:
            pitch = note + octave_shift
            freq = midi_to_freq(pitch)
            start_sample = int((bar_start_beat + rel_beat) * BEAT_DURATION * SAMPLE_RATE)
            note_len = int(dur * BEAT_DURATION * SAMPLE_RATE)
            for i in range(note_len):
                t = i / SAMPLE_RATE
                idx = start_sample + i
                saw = 2.0 * ((t * freq) % 1.0) - 1.0
                sub_sine = math.sin(2.0 * math.pi * (freq / 2.0) * t) * 0.4
                env = math.exp(-5.0 * (t / (dur * BEAT_DURATION)))
                raw = (saw * 0.6 + sub_sine) * env * vel * 0.45
                sat = math.tanh(raw * 1.5)
                add_sample(left_buf, idx, sat * 0.8)
                add_sample(right_buf, idx, sat * 0.8)

    # 5. Wavetable / Meld Arpeggiator with Stereo Ping-Pong Delay
    chords = [
        [48, 55, 60, 63], [48, 55, 60, 63],
        [44, 51, 56, 60], [44, 51, 56, 60],
        [41, 48, 53, 56], [41, 48, 53, 56],
        [43, 50, 55, 59], [43, 50, 55, 62],
    ]
    delay_time_l = int((BEAT_DURATION * 0.75) * SAMPLE_RATE)
    delay_time_r = int((BEAT_DURATION * 0.5) * SAMPLE_RATE)
    delay_fb = 0.38
    arp_buf_l = [0.0] * NUM_SAMPLES
    arp_buf_r = [0.0] * NUM_SAMPLES

    for bar_idx in range(TOTAL_BARS):
        chord = chords[bar_idx % len(chords)]
        bar_start_beat = bar_idx * 4
        for step in range(16):
            step_beat = bar_start_beat + (step * 0.25)
            note = chord[step % len(chord)] + (12 if step % 2 == 1 else 0)
            freq = midi_to_freq(note)
            start_sample = int(step_beat * BEAT_DURATION * SAMPLE_RATE)
            note_len = int(0.20 * BEAT_DURATION * SAMPLE_RATE)
            pan = math.sin(step * 0.7)
            pan_l = 0.5 * (1.0 - pan)
            pan_r = 0.5 * (1.0 + pan)

            for i in range(note_len):
                t = i / SAMPLE_RATE
                idx = start_sample + i
                if idx >= NUM_SAMPLES:
                    break
                p1 = (t * freq) % 1.0
                sq = 1.0 if p1 > 0.5 else -1.0
                sw = 2.0 * p1 - 1.0
                env = math.exp(-16.0 * (t / (0.20 * BEAT_DURATION)))
                val = (0.5 * sw + 0.5 * sq) * env * 0.16
                add_sample(arp_buf_l, idx, val * pan_l)
                add_sample(arp_buf_r, idx, val * pan_r)

    # Delay feedback cross-channel
    for i in range(NUM_SAMPLES):
        if i >= delay_time_l:
            arp_buf_l[i] += arp_buf_r[i - delay_time_l] * delay_fb
        if i >= delay_time_r:
            arp_buf_r[i] += arp_buf_l[i - delay_time_r] * delay_fb
        add_sample(left_buf, i, arp_buf_l[i])
        add_sample(right_buf, i, arp_buf_r[i])

    # 6. Peak Normalization to exact -1.0 dBFS (amplitude = 10^(-1/20) ~ 0.8912509)
    target_peak = 0.8912509
    current_max = max(0.0001, max(max(abs(l), abs(r)) for l, r in zip(left_buf, right_buf)))
    gain = target_peak / current_max

    out_path = Path(output_wav_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with wave.open(str(out_path), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        pcm_bytes = bytearray()
        for i in range(NUM_SAMPLES):
            l_clamped = max(-1.0, min(1.0, left_buf[i] * gain))
            r_clamped = max(-1.0, min(1.0, right_buf[i] * gain))
            l_int = int(round(l_clamped * 32767.0))
            r_int = int(round(r_clamped * 32767.0))
            pcm_bytes.extend(struct.pack("<hh", l_int, r_int))
        wav.writeframes(pcm_bytes)

    print(f"Generated {out_path} ({len(pcm_bytes)} PCM bytes, {TOTAL_DURATION:.2f}s, peak: -1.0 dBFS)")


def generate_manifest(output_json_path: str) -> None:
    manifest = {
        "manifest_version": "1.0.0",
        "project": "ableton-live12-mcp",
        "session": {
            "title": "Deep Pulse (Ableton Live 12 MCP Showcase)",
            "producer": "Antigravity (agy)",
            "artist": "Juan Cruz Muñoz Albelo",
            "genre": "Melodic Techno / Deep Tech",
            "tempo_bpm": 124.0,
            "time_signature": "4/4",
            "scale_name": "Minor",
            "root_note": "C",
            "duration_seconds": round(TOTAL_DURATION, 2),
            "total_bars": TOTAL_BARS,
            "rendered_audio_file": "assets/showcase_demo.wav",
            "sample_rate": SAMPLE_RATE,
            "bit_depth": 16,
            "channels": 2,
        },
        "tracks": [
            {
                "index": 0,
                "name": "Kick & Percussion",
                "type": "midi",
                "color": "#ffbe00",
                "devices": [
                    {
                        "name": "DrumGroupDevice",
                        "preset": "909 Core Kit",
                        "pads": [
                            {"note": 36, "name": "Kick 909", "choke_group": 0},
                            {"note": 38, "name": "Snare 909", "choke_group": 0},
                            {"note": 42, "name": "Closed HH 909", "choke_group": 1},
                            {"note": 46, "name": "Open HH 909", "choke_group": 1},
                        ],
                    }
                ],
                "clip_slot_0": {
                    "length_beats": 32.0,
                    "is_looping": True,
                    "notes_count": 80,
                    "live12_extended_spec": {"probability": 1.0, "velocity_deviation": 5},
                },
            },
            {
                "index": 1,
                "name": "Acid Sub Bass",
                "type": "midi",
                "color": "#00d2ff",
                "devices": [
                    {
                        "name": "DriftDevice",
                        "preset": "Analog Sub Mono",
                        "parameters": {
                            "Filter Freq": 420.0,
                            "Filter Res": 0.45,
                            "Drift": 0.25,
                            "Drive": 0.30,
                        },
                    }
                ],
                "clip_slot_0": {
                    "length_beats": 32.0,
                    "is_looping": True,
                    "scale_locked": True,
                    "pitches": [36, 39, 41, 43, 46],
                    "live12_extended_spec": {"probability": 0.95, "velocity_deviation": 8},
                },
            },
            {
                "index": 2,
                "name": "Melodic Wavetable Arp",
                "type": "midi",
                "color": "#ff007f",
                "devices": [
                    {
                        "name": "WavetableDevice",
                        "preset": "Dual Morphing Saw/Square",
                        "parameters": {
                            "Filter 1 Freq": 1850.0,
                            "Filter 1 Res": 0.35,
                            "Osc 1 Pos": 0.45,
                            "Unison": "Classic 4",
                        },
                        "modulation_matrix": [
                            {"source": "LFO 1", "target": "Filter 1 Freq", "amount": 0.40}
                        ],
                    }
                ],
                "mixer": {
                    "volume": 0.85,
                    "panning": 0.0,
                    "sends": [
                        {"send_index": 0, "name": "Delay Dotted 8th", "amount": 0.38},
                        {"send_index": 1, "name": "Reverb Hall", "amount": 0.25},
                    ],
                },
            },
            {
                "index": 3,
                "name": "Atmospheric Pad",
                "type": "midi",
                "color": "#00ff88",
                "devices": [
                    {
                        "name": "MeldDevice",
                        "preset": "Swarm & Formant Bi-Timbral",
                        "engine_a": "Swarm",
                        "engine_b": "Formant",
                    }
                ],
                "mixer": {
                    "volume": 0.70,
                    "sends": [{"send_index": 1, "name": "Reverb Hall", "amount": 0.60}],
                },
            },
        ],
        "mcp_pipeline_recipe": [
            {"tool": "live12_song_set_scale", "params": {"scale_name": "Minor", "root_note": 0}},
            {"tool": "live12_transport_set_tempo", "params": {"tempo": 124.0}},
            {"tool": "live12_track_create", "params": {"type": "midi", "name": "Kick & Percussion"}},
            {"tool": "live12_browser_load_item", "params": {"track_index": 0, "uri": "query:drums#909 Core Kit"}},
            {"tool": "live12_clip_create", "params": {"track_index": 0, "slot_index": 0, "length": 32.0}},
            {"tool": "live12_clip_add_notes", "params": {"track_index": 0, "slot_index": 0, "notes": "[80 drum events]"}},
            {"tool": "live12_track_create", "params": {"type": "midi", "name": "Acid Sub Bass"}},
            {"tool": "live12_browser_load_item", "params": {"track_index": 1, "uri": "query:devices#Drift"}},
            {"tool": "live12_device_set_parameter", "params": {"track_index": 1, "device_index": 0, "parameter_name": "Filter Freq", "value": 420.0}},
            {"tool": "live12_clip_create", "params": {"track_index": 1, "slot_index": 0, "length": 32.0}},
            {"tool": "live12_clip_add_notes", "params": {"track_index": 1, "slot_index": 0, "notes": "[Acid bassline]"}},
            {"tool": "live12_track_create", "params": {"type": "midi", "name": "Melodic Wavetable Arp"}},
            {"tool": "live12_browser_load_item", "params": {"track_index": 2, "uri": "query:devices#Wavetable"}},
            {"tool": "live12_wavetable_modulation_matrix", "params": {"track_index": 2, "device_index": 0, "source": "LFO1", "target": "Filter 1 Freq", "amount": 0.4}},
            {"tool": "live12_mixer_set", "params": {"track_index": 2, "send_index": 0, "send_amount": 0.38}},
            {"tool": "live12_clip_create", "params": {"track_index": 2, "slot_index": 0, "length": 32.0}},
            {"tool": "live12_clip_add_notes", "params": {"track_index": 2, "slot_index": 0, "notes": "[128 arpeggio notes]"}},
            {"tool": "live12_transport_play", "params": {}},
        ],
    }

    out_path = Path(output_json_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"Generated {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate Ableton Live 12 MCP showcase audio and manifest.")
    parser.add_argument(
        "--wav",
        type=str,
        default="assets/showcase_demo.wav",
        help="Target path for showcase WAV file (default: assets/showcase_demo.wav)",
    )
    parser.add_argument(
        "--manifest",
        type=str,
        default="assets/showcase_session_manifest.json",
        help="Target path for showcase session manifest JSON (default: assets/showcase_session_manifest.json)",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    wav_path = Path(args.wav) if Path(args.wav).is_absolute() else (repo_root / args.wav)
    manifest_path = Path(args.manifest) if Path(args.manifest).is_absolute() else (repo_root / args.manifest)

    generate_showcase_audio(str(wav_path))
    generate_manifest(str(manifest_path))


if __name__ == "__main__":
    main()
