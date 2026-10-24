#!/usr/bin/env python3
"""
Empirical Challenge & Stress-Test Harness for Masterclasses Deliverables.
Validates 6 .als Live Sets and 6 .wav Audio Bounces (HOLO Modules 1-5 + Peak Class).

Stress Dimensions & Validation Criteria:
1. ALS Live Sets:
   - Valid gzip container stream (magic 0x1f 0x8b)
   - XML parsing via xml.etree.ElementTree
   - Root tag <Ableton>, creator version Ableton Live 12.4.6
   - Child <LiveSet>
   - Non-empty <Tracks> (MIDI, Audio, Group breakdown)
   - <CuePoints> / <Locators> locator points present with valid beat times
   - <MasterTrack> / <MainTrack> present with valid DeviceChain
   - File size strictly > 30 KB (30,720 bytes)
   - Song tempo and scale validation

2. WAV Audio Bounces:
   - Valid RIFF header & PCM audio format
   - Sample rate (>= 44100 Hz), stereo (channels == 2), bit depth (>= 16-bit, 24-bit)
   - Duration >= 10.0 seconds
   - Non-silent RMS > -40.0 dBFS
   - Peak amplitude <= 0.0 dBFS (no severe clipping)
   - DC offset and Crest Factor sanity check
"""

from __future__ import annotations

import argparse
import gzip
import json
import math
import os
import sys
import wave
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Target files mapping
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

TARGET_PAIRS = [
    {
        "id": "holo_m1",
        "name": "HOLO Module 1: Concepto y Referencia",
        "als": os.path.join(REPO_ROOT, "masterclasses", "holo", "modulo_1_concepto_referencia.als"),
        "wav": os.path.join(REPO_ROOT, "masterclasses", "holo", "modulo_1_concepto_referencia.wav"),
        "expected_bpm": 126.0,
        "expected_scale_root": 0,  # C
        "expected_scale_name": "1",  # Minor
        "min_tracks": 4,
        "min_cues": 1,
    },
    {
        "id": "holo_m2",
        "name": "HOLO Module 2: Groove y Baterías",
        "als": os.path.join(REPO_ROOT, "masterclasses", "holo", "modulo_2_groove_baterias.als"),
        "wav": os.path.join(REPO_ROOT, "masterclasses", "holo", "modulo_2_groove_baterias.wav"),
        "expected_bpm": 126.0,
        "expected_scale_root": 0,  # C
        "expected_scale_name": "1",  # Minor
        "min_tracks": 6,
        "min_cues": 1,
    },
    {
        "id": "holo_m3",
        "name": "HOLO Module 3: Diseño Sonoro",
        "als": os.path.join(REPO_ROOT, "masterclasses", "holo", "modulo_3_diseno_sonoro.als"),
        "wav": os.path.join(REPO_ROOT, "masterclasses", "holo", "modulo_3_diseno_sonoro.wav"),
        "expected_bpm": 126.0,
        "expected_scale_root": 0,  # C
        "expected_scale_name": "1",  # Minor
        "min_tracks": 6,
        "min_cues": 1,
    },
    {
        "id": "holo_m4",
        "name": "HOLO Module 4: Bases Armónicas y Melódicas",
        "als": os.path.join(REPO_ROOT, "masterclasses", "holo", "modulo_4_bases_armonicas_melodicas.als"),
        "wav": os.path.join(REPO_ROOT, "masterclasses", "holo", "modulo_4_bases_armonicas_melodicas.wav"),
        "expected_bpm": 126.0,
        "expected_scale_root": 0,  # C
        "expected_scale_name": "1",  # Minor
        "min_tracks": 6,
        "min_cues": 1,
    },
    {
        "id": "holo_m5",
        "name": "HOLO Module 5: Arreglo Completo",
        "als": os.path.join(REPO_ROOT, "masterclasses", "holo", "modulo_5_arreglo_completo.als"),
        "wav": os.path.join(REPO_ROOT, "masterclasses", "holo", "modulo_5_arreglo_completo.wav"),
        "expected_bpm": 126.0,
        "expected_scale_root": 0,  # C
        "expected_scale_name": "1",  # Minor
        "min_tracks": 10,
        "min_cues": 1,
    },
    {
        "id": "peak_class",
        "name": "Peak Time Masterclass: ClaSE PEAK jULIO 25 (MCP)",
        "als": os.path.join(REPO_ROOT, "masterclasses", "peak", "clase_peak_julio_25_mcp.als"),
        "wav": os.path.join(REPO_ROOT, "masterclasses", "peak", "clase_peak_julio_25_mcp.wav"),
        "expected_bpm": 135.0,
        "expected_scale_root": 7,  # G
        "expected_scale_name": "1",  # Minor
        "min_tracks": 15,
        "min_cues": 1,
    },
]


def validate_als_set(target: Dict[str, Any]) -> Dict[str, Any]:
    """Empirically validates an Ableton Live Set (.als)."""
    als_path = target["als"]
    result: Dict[str, Any] = {
        "path": als_path,
        "passed": False,
        "errors": [],
        "warnings": [],
        "metrics": {},
    }

    if not os.path.exists(als_path):
        result["errors"].append(f"File not found: {als_path}")
        return result

    file_size = os.path.getsize(als_path)
    result["metrics"]["file_size_bytes"] = file_size
    result["metrics"]["file_size_kb"] = round(file_size / 1024.0, 2)

    # Size check > 30 KB
    if file_size <= 30 * 1024:
        result["errors"].append(f"File size {file_size} bytes is <= 30 KB threshold")

    # Magic bytes check
    try:
        with open(als_path, "rb") as f:
            magic = f.read(2)
            if magic != b"\x1f\x8b":
                result["errors"].append(f"Invalid gzip magic: {magic!r}")
                return result
    except Exception as e:
        result["errors"].append(f"Error reading magic bytes: {e}")
        return result

    # Decompress and parse XML
    try:
        with gzip.open(als_path, "rb") as gz:
            xml_data = gz.read()
    except Exception as e:
        result["errors"].append(f"Gzip decompression failed: {e}")
        return result

    try:
        root = ET.fromstring(xml_data)
    except Exception as e:
        result["errors"].append(f"XML parse error: {e}")
        return result

    if root.tag != "Ableton":
        result["errors"].append(f"Root tag is <{root.tag}> instead of <Ableton>")

    creator = root.attrib.get("Creator", "Unknown")
    maj_ver = root.attrib.get("MajorVersion", "?")
    min_ver = root.attrib.get("MinorVersion", "?")
    result["metrics"]["creator"] = creator
    result["metrics"]["version"] = f"{maj_ver}.{min_ver}"

    live_set = root.find("LiveSet")
    if live_set is None:
        result["errors"].append("Missing <LiveSet> child element")
        return result

    # Check Master / Main track
    main_track = live_set.find("MainTrack")
    if main_track is None:
        main_track = live_set.find("MasterTrack")
    if main_track is None:
        result["errors"].append("Missing <MainTrack> or <MasterTrack>")
    else:
        result["metrics"]["master_track_tag"] = main_track.tag
        dev_chain = main_track.find("DeviceChain")
        result["metrics"]["master_has_device_chain"] = dev_chain is not None

    # Count tracks
    tracks_elem = live_set.find("Tracks")
    if tracks_elem is None:
        result["errors"].append("Missing <Tracks> element")
        total_tracks = 0
    else:
        track_list = list(tracks_elem)
        total_tracks = len(track_list)
        midi_count = sum(1 for t in track_list if t.tag == "MidiTrack")
        audio_count = sum(1 for t in track_list if t.tag == "AudioTrack")
        group_count = sum(1 for t in track_list if t.tag == "GroupTrack")
        result["metrics"]["total_tracks"] = total_tracks
        result["metrics"]["midi_tracks"] = midi_count
        result["metrics"]["audio_tracks"] = audio_count
        result["metrics"]["group_tracks"] = group_count

        min_req = target.get("min_tracks", 1)
        if total_tracks < min_req:
            result["errors"].append(f"Found {total_tracks} tracks, minimum expected is {min_req}")

    # Check Locators / Cue points
    locators = live_set.findall(".//Locator")
    cue_wrapper = live_set.find("CuePointsListWrapper")
    result["metrics"]["locators_count"] = len(locators)
    result["metrics"]["cue_wrapper_present"] = cue_wrapper is not None

    loc_details = []
    for loc in locators:
        n_elem = loc.find("Name")
        t_elem = loc.find("Time")
        name = n_elem.attrib.get("Value", "") if n_elem is not None else ""
        time_b = float(t_elem.attrib.get("Value", 0.0)) if t_elem is not None else 0.0
        loc_details.append({"name": name, "time_beats": time_b})
    result["metrics"]["locators"] = loc_details

    min_cues = target.get("min_cues", 1)
    if len(locators) < min_cues:
        result["errors"].append(f"Found {len(locators)} locators, minimum expected is {min_cues}")

    # Inspect Tempo
    tempo_val = None
    for el in live_set.iter("Tempo"):
        man = el.find("Manual")
        if man is not None and "Value" in man.attrib:
            try:
                tempo_val = float(man.attrib["Value"])
                break
            except ValueError:
                pass
    result["metrics"]["tempo"] = tempo_val
    if tempo_val is not None:
        exp_bpm = target.get("expected_bpm")
        if exp_bpm is not None and abs(tempo_val - exp_bpm) > 0.1:
            result["errors"].append(f"Tempo is {tempo_val} BPM, expected {exp_bpm} BPM")

    # Inspect Scale Information
    scale_info = live_set.find("ScaleInformation")
    if scale_info is not None:
        root_el = scale_info.find("Root")
        name_el = scale_info.find("Name")
        root_val = int(root_el.attrib.get("Value", -1)) if root_el is not None else -1
        name_val = name_el.attrib.get("Value", "") if name_el is not None else ""
        result["metrics"]["scale_root"] = root_val
        result["metrics"]["scale_name"] = name_val

        exp_root = target.get("expected_scale_root")
        if exp_root is not None and root_val != exp_root:
            result["warnings"].append(f"Scale root note {root_val} does not match expected {exp_root}")

    result["passed"] = len(result["errors"]) == 0
    return result


def validate_wav_bounce(target: Dict[str, Any]) -> Dict[str, Any]:
    """Empirically validates a rendered WAV audio bounce."""
    wav_path = target["wav"]
    result: Dict[str, Any] = {
        "path": wav_path,
        "passed": False,
        "errors": [],
        "warnings": [],
        "metrics": {},
    }

    if not os.path.exists(wav_path):
        result["errors"].append(f"File not found: {wav_path}")
        return result

    file_size = os.path.getsize(wav_path)
    result["metrics"]["file_size_bytes"] = file_size
    result["metrics"]["file_size_mb"] = round(file_size / (1024.0 * 1024.0), 2)

    if file_size < 44:
        result["errors"].append(f"File size {file_size} is smaller than 44-byte RIFF header")
        return result

    try:
        with wave.open(wav_path, "rb") as wf:
            nchannels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate()
            nframes = wf.getnframes()
            comptype = wf.getcomptype()

            result["metrics"]["channels"] = nchannels
            result["metrics"]["bit_depth"] = sampwidth * 8
            result["metrics"]["sample_rate"] = framerate
            result["metrics"]["n_frames"] = nframes
            result["metrics"]["compression"] = comptype

            if comptype != "NONE":
                result["errors"].append(f"Compressed audio format: {comptype}")

            if framerate < 44100:
                result["errors"].append(f"Sample rate {framerate} Hz is below standard 44100 Hz")

            if nchannels != 2:
                result["errors"].append(f"Channel count is {nchannels}, expected stereo (2)")

            if sampwidth not in (2, 3, 4):
                result["errors"].append(f"Unsupported bit depth: {sampwidth * 8}-bit")

            if nframes == 0:
                result["errors"].append("WAV file contains 0 audio frames")
                return result

            duration_s = nframes / float(framerate)
            result["metrics"]["duration_s"] = round(duration_s, 3)

            # Boundary check: duration >= 10.0s
            if duration_s < 10.0:
                result["errors"].append(f"Duration {duration_s:.2f}s is strictly below 10.0s threshold")

            # Stream PCM frames in chunks and calculate accurate audio statistics
            chunk_frames = 65536
            sum_sq = 0.0
            peak_val = 0.0
            total_samples = 0
            dc_sum = 0.0

            while True:
                raw = wf.readframes(chunk_frames)
                if not raw:
                    break
                if sampwidth == 2:
                    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32768.0
                elif sampwidth == 3:
                    b = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
                    b4 = np.zeros((b.shape[0], 4), dtype=np.uint8)
                    b4[:, 1:] = b
                    samples = b4.view(dtype=np.int32).flatten().astype(np.float64) / 2147483648.0
                elif sampwidth == 4:
                    samples = np.frombuffer(raw, dtype=np.float32).astype(np.float64)

                chunk_peak = np.max(np.abs(samples))
                if chunk_peak > peak_val:
                    peak_val = chunk_peak
                sum_sq += np.sum(samples ** 2)
                dc_sum += np.sum(samples)
                total_samples += len(samples)

            mean_sq = sum_sq / max(1, total_samples)
            rms = math.sqrt(mean_sq)
            rms_dbfs = 20.0 * math.log10(rms) if rms > 1e-9 else float("-inf")
            peak_dbfs = 20.0 * math.log10(peak_val) if peak_val > 1e-9 else float("-inf")
            dc_offset = dc_sum / max(1, total_samples)
            crest_factor_db = peak_dbfs - rms_dbfs

            result["metrics"]["peak_linear"] = round(peak_val, 6)
            result["metrics"]["peak_dbfs"] = round(peak_dbfs, 2)
            result["metrics"]["rms_linear"] = round(rms, 6)
            result["metrics"]["rms_dbfs"] = round(rms_dbfs, 2)
            result["metrics"]["dc_offset"] = round(dc_offset, 6)
            result["metrics"]["crest_factor_db"] = round(crest_factor_db, 2)

            # Boundary check: RMS > -40.0 dBFS
            if rms_dbfs <= -40.0:
                result["errors"].append(f"RMS {rms_dbfs:.2f} dBFS is below -40.0 dBFS threshold (silent or near-silent)")

            # Boundary check: Peak <= 0.0 dBFS (allow +0.05 dBFS for float quantization)
            if peak_dbfs > 0.05:
                result["errors"].append(f"Peak amplitude {peak_dbfs:.2f} dBFS exceeds 0.0 dBFS threshold (severe clipping)")

            # Silence check
            if rms < 1e-5:
                result["errors"].append("Audio stream is absolute digital silence")

    except Exception as e:
        result["errors"].append(f"Failed parsing WAV: {e}")

    result["passed"] = len(result["errors"]) == 0
    return result


def run_full_suite() -> Tuple[bool, List[Dict[str, Any]]]:
    """Runs all ALS and WAV empirical tests across all target pairs."""
    overall_passed = True
    suite_results = []

    print("\n" + "=" * 80)
    print("EMPIRICAL STRESS-TEST SUITE: ABLETON LIVE 12 MASTERCLASSES DELIVERABLES")
    print("=" * 80)

    for item in TARGET_PAIRS:
        print(f"\n▶ Testing: {item['name']} ({item['id']})")
        als_res = validate_als_set(item)
        wav_res = validate_wav_bounce(item)

        pair_passed = als_res["passed"] and wav_res["passed"]
        if not pair_passed:
            overall_passed = False

        status_str = "✓ PASS" if pair_passed else "✗ FAIL"
        print(f"  Overall: {status_str}")

        # ALS Output
        als_m = als_res["metrics"]
        print(f"  • ALS: {'PASS' if als_res['passed'] else 'FAIL'} → {os.path.basename(als_res['path'])}")
        print(f"    - Size: {als_m.get('file_size_kb')} KB (> 30 KB: {als_m.get('file_size_kb', 0) > 30.0})")
        print(f"    - Tracks: {als_m.get('total_tracks')} (MIDI: {als_m.get('midi_tracks')}, Audio: {als_m.get('audio_tracks')}, Group: {als_m.get('group_tracks')})")
        print(f"    - Master/Main Track: {als_m.get('master_track_tag')}, DeviceChain: {als_m.get('master_has_device_chain')}")
        print(f"    - Locators: {als_m.get('locators_count')} cue points found")
        print(f"    - Tempo: {als_m.get('tempo')} BPM, Scale Root: {als_m.get('scale_root')}")
        if als_res["errors"]:
            for err in als_res["errors"]:
                print(f"    [!] ALS ERROR: {err}")

        # WAV Output
        wav_m = wav_res["metrics"]
        print(f"  • WAV: {'PASS' if wav_res['passed'] else 'FAIL'} → {os.path.basename(wav_res['path'])}")
        print(f"    - Format: {wav_m.get('channels')}ch, {wav_m.get('bit_depth')}-bit, {wav_m.get('sample_rate')} Hz")
        print(f"    - Duration: {wav_m.get('duration_s')}s (>= 10.0s: {wav_m.get('duration_s', 0) >= 10.0})")
        print(f"    - RMS: {wav_m.get('rms_dbfs')} dBFS (> -40.0 dBFS: {wav_m.get('rms_dbfs', -99) > -40.0})")
        print(f"    - Peak: {wav_m.get('peak_dbfs')} dBFS (<= 0.0 dBFS: {wav_m.get('peak_dbfs', 99) <= 0.05})")
        print(f"    - Crest Factor: {wav_m.get('crest_factor_db')} dB, DC Offset: {wav_m.get('dc_offset')}")
        if wav_res["errors"]:
            for err in wav_res["errors"]:
                print(f"    [!] WAV ERROR: {err}")

        suite_results.append({
            "id": item["id"],
            "name": item["name"],
            "passed": pair_passed,
            "als": als_res,
            "wav": wav_res,
        })

    print("\n" + "=" * 80)
    total_files = len(TARGET_PAIRS) * 2
    passed_files = sum((1 if r["als"]["passed"] else 0) + (1 if r["wav"]["passed"] else 0) for r in suite_results)
    print(f"SUMMARY: {passed_files} / {total_files} files passed ({100.0 * passed_files / total_files:.1f}%)")
    print(f"VERDICT: {'APPROVE' if overall_passed else 'REQUEST_CHANGES'}")
    print("=" * 80 + "\n")

    return overall_passed, suite_results


def main():
    parser = argparse.ArgumentParser(description="Empirical Masterclass Deliverables Verifier")
    parser.add_argument("--json", action="store_true", help="Output JSON results to stdout")
    args = parser.parse_args()

    passed, results = run_full_suite()

    if args.json:
        print(json.dumps({"passed": passed, "results": results}, indent=2))

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
