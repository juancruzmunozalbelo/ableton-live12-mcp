#!/usr/bin/env python3
"""
Empirical Challenge & Verification Script for Milestone 1 (LOM Surface Extraction)
Ableton Live 12.4.6 Suite

Validates:
1. Every one of the 184 Boost.Python demangled symbols in docs/lom_surface_12_4_6.json
   exists in the Mach-O binary symbol table (arm64 & x86_64) with 0 false positives
   and 0 omissions.
2. JSON schema validity, metadata accuracy, and strict absence of nulls/stubs/empty objects.
3. Verification of specific Live 12 signatures:
   - Live.TakeLane.TakeLane.create_audio_clip
   - Live.TakeLane.TakeLane.create_midi_clip
   - Live.Clip.Clip.get_notes_extended
   - Live.Application.Application.open_dialog_count
4. Verbatim string verification in the Mach-O binary.
"""

import sys
import os
import re
import json
import hashlib
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
JSON_PATH = REPO_ROOT / "docs" / "lom_surface_12_4_6.json"
BINARY_PATH = Path("/Applications/Ableton Live 12 Suite.app/Contents/MacOS/Live")


def log_check(name: str, passed: bool, detail: str = ""):
    status = "✓ PASS" if passed else "✗ FAIL"
    print(f"[{status}] {name}")
    if detail:
        print(f"       -> {detail}")
    if not passed:
        sys.exit(1)


def main():
    print("=" * 70)
    print("EMPIRICAL CHALLENGE HARNESS: Milestone 1 LOM API Surface")
    print(f"Target Binary: {BINARY_PATH}")
    print(f"Target JSON:   {JSON_PATH}")
    print("=" * 70)

    # 1. Binary existence and SHA256
    log_check("Live 12.4.6 Mach-O binary exists", BINARY_PATH.exists(), str(BINARY_PATH))
    h = hashlib.sha256()
    with open(BINARY_PATH, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    actual_sha = h.hexdigest()
    expected_sha = "5e8832e06fe92d42ceebac4fad153e44422c90923f426dcb05c760c6d80b3949"
    log_check("Mach-O SHA256 integrity match", actual_sha == expected_sha, f"sha256: {actual_sha}")

    # 2. JSON load and metadata
    log_check("docs/lom_surface_12_4_6.json exists", JSON_PATH.exists(), str(JSON_PATH))
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    meta = catalog.get("metadata", {})
    log_check("Metadata binary_sha256 match", meta.get("binary_sha256") == actual_sha)
    log_check("Metadata live_version is 12.4.6", meta.get("live_version") == "12.4.6")
    log_check("Metadata embedded python is 3.11.6", meta.get("embedded_python_version") == "3.11.6")

    # 3. Boost.Python symbols extraction from binary
    print("\n--- Testing 184 Boost.Python Symbols Against Mach-O Symbol Table ---")
    p1 = subprocess.Popen(["nm", "-arch", "arm64", str(BINARY_PATH)], stdout=subprocess.PIPE, text=True)
    p2 = subprocess.Popen(["c++filt"], stdin=p1.stdout, stdout=subprocess.PIPE, text=True)
    p1.stdout.close()
    out_arm, _ = p2.communicate()
    pattern = re.compile(r"registered_base<([^>]+(?:<[^>]+>)*) const volatile&>")
    arm_symbols = {pattern.search(l).group(1) for l in out_arm.splitlines() if pattern.search(l)}

    p3 = subprocess.Popen(["nm", "-arch", "x86_64", str(BINARY_PATH)], stdout=subprocess.PIPE, text=True)
    p4 = subprocess.Popen(["c++filt"], stdin=p3.stdout, stdout=subprocess.PIPE, text=True)
    p3.stdout.close()
    out_x86, _ = p4.communicate()
    x86_symbols = {pattern.search(l).group(1) for l in out_x86.splitlines() if pattern.search(l)}

    json_symbols = set(catalog.get("boost_python_types", {}).get("all_types", []))
    log_check("Symbol count is exactly 184", len(json_symbols) == 184, f"Found {len(json_symbols)} symbols")

    missing_in_arm = json_symbols - arm_symbols
    log_check("All 184 symbols exist in arm64 Mach-O symbol table", len(missing_in_arm) == 0, f"Missing: {missing_in_arm}")

    extra_in_arm = arm_symbols - json_symbols
    log_check("No unaccounted Boost.Python symbols in arm64", len(extra_in_arm) == 0, f"Extra: {extra_in_arm}")

    missing_in_x86 = json_symbols - x86_symbols
    log_check("All 184 symbols exist in x86_64 Mach-O symbol table", len(missing_in_x86) == 0, f"Missing: {missing_in_x86}")

    sym_diff = arm_symbols ^ x86_symbols
    log_check("Universal binary arm64 & x86_64 symbol bijection", len(sym_diff) == 0)

    # 4. JSON Schema & Quality: No dummy/stub objects
    print("\n--- Validating JSON Schema & Quality (Anti-Dummy/Anti-Stub) ---")
    allowed_null_paths = {
        "lom_classes.Live.Application.Application.canonical_parent",
        "lom_classes.Live.Base.Timer.canonical_parent",
    }
    null_paths = []
    empty_strings = []

    def check_traversal(obj, path=""):
        if obj is None:
            null_paths.append(path)
        elif isinstance(obj, str):
            if not obj.strip():
                empty_strings.append(path)
        elif isinstance(obj, dict):
            for k, v in obj.items():
                check_traversal(v, f"{path}.{k}" if path else k)
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                check_traversal(v, f"{path}[{i}]")

    check_traversal(catalog)
    unexpected_nulls = set(null_paths) - allowed_null_paths
    log_check("Absence of unexpected null values", len(unexpected_nulls) == 0, f"Unexpected: {unexpected_nulls}")
    log_check("Absence of empty strings in catalog", len(empty_strings) == 0, f"Empty: {empty_strings}")

    classes = catalog.get("lom_classes", {})
    log_check("LOM classes count >= 29", len(classes) >= 29, f"Total classes: {len(classes)}")

    empty_classes = [c for c, data in classes.items() if not data.get("properties") and not data.get("methods")]
    log_check("Zero empty/stub classes", len(empty_classes) == 0, f"Empty: {empty_classes}")

    enums = catalog.get("enums", {})
    log_check("Enums count == 28", len(enums) == 28, f"Total enums: {len(enums)}")

    mxd_classes = catalog.get("mxd_reflection", {}).get("classes", {})
    log_check("MxD reflection classes count == 43", len(mxd_classes) == 43, f"Total MxD classes: {len(mxd_classes)}")

    # 5. Method Signatures for Live 12
    print("\n--- Verifying Live 12 Method Signatures & Binary Verbatim Strings ---")
    
    # 5.1 TakeLane create_audio_clip
    takelane = classes.get("Live.TakeLane.TakeLane", {})
    tl_audio_m = takelane.get("methods", {}).get("create_audio_clip")
    log_check("TakeLane.create_audio_clip exists", tl_audio_m is not None)
    audio_args = {a["name"]: a["type"] for a in tl_audio_m.get("args", [])}
    log_check("TakeLane.create_audio_clip args match (file_path: str, time: float)", audio_args == {"file_path": "str", "time": "float"})
    log_check("TakeLane.create_audio_clip returns Live.Clip.Clip", tl_audio_m.get("returns") == "Live.Clip.Clip")

    # 5.2 TakeLane create_midi_clip
    tl_midi_m = takelane.get("methods", {}).get("create_midi_clip")
    log_check("TakeLane.create_midi_clip exists", tl_midi_m is not None)
    midi_args = {a["name"]: a["type"] for a in tl_midi_m.get("args", [])}
    log_check("TakeLane.create_midi_clip args match (time: float, length: float)", midi_args == {"time": "float", "length": "float"})
    log_check("TakeLane.create_midi_clip returns Live.Clip.Clip", tl_midi_m.get("returns") == "Live.Clip.Clip")

    # 5.3 Clip get_notes_extended
    clip = classes.get("Live.Clip.Clip", {})
    clip_notes_m = clip.get("methods", {}).get("get_notes_extended")
    log_check("Clip.get_notes_extended exists", clip_notes_m is not None)
    notes_args = {a["name"]: a["type"] for a in clip_notes_m.get("args", [])}
    expected_notes_args = {"from_pitch": "int", "pitch_span": "int", "from_time": "float", "time_span": "float"}
    log_check("Clip.get_notes_extended args match (pitch/time range)", notes_args == expected_notes_args)
    log_check("Clip.get_notes_extended returns tuple[Live.Clip.MidiNote]", clip_notes_m.get("returns") == "tuple[Live.Clip.MidiNote]")

    # 5.4 Application open_dialog_count
    app = classes.get("Live.Application.Application", {})
    dialog_prop = app.get("properties", {}).get("open_dialog_count")
    log_check("Application.open_dialog_count property exists", dialog_prop is not None)
    log_check("Application.open_dialog_count is read-only int with listener",
              dialog_prop.get("type") == "int" and dialog_prop.get("access") == "read-only" and dialog_prop.get("has_listener") is True)

    # 5.5 Binary verbatim string verification
    with open(BINARY_PATH, "rb") as f:
        bin_bytes = f.read()

    log_check("Verbatim binary string: TakeLane create_audio_clip docstring",
              b"Creates an audio clip referencing the file at the given path and inserts it into the arrangement at the specified time." in bin_bytes)
    log_check("Verbatim binary string: TakeLane create_midi_clip docstring",
              b"Creates an empty MIDI clip and inserts it into the arrangement at the specified time." in bin_bytes)
    log_check("Verbatim binary string: Clip get_notes_extended docstring",
              b"Returns a list of MIDI notes from the given pitch and time range.\nEach note is represented by a Live.Clip.MidiNote object." in bin_bytes)
    log_check("Verbatim binary string: Application open_dialog_count docstring",
              b"The number of open dialogs in Live. 0 if not dialog is open." in bin_bytes)

    print("\n" + "=" * 70)
    print("VERDICT: CONFIRMED. Milestone 1 deliverables 100% verified.")
    print("=" * 70)


if __name__ == "__main__":
    main()
