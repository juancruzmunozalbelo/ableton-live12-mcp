"""
Adversarial Empirical Challenge Test Suite for Milestone 1
==========================================================
Validates:
1. Every one of the 184 Boost.Python demangled symbols exists in the Mach-O binary
   symbol table (arm64 & x86_64) with 0 false positives and 0 omissions.
2. JSON schema validity of docs/lom_surface_12_4_6.json:
   - Metadata accuracy (SHA256, version, counts)
   - Strict absence of null values (except root canonical_parents)
   - Strict absence of empty strings, dummy objects, TODOs, stubs
   - Complete property and method descriptors
   - Enums and MxD reflection completeness
3. Specific Live 12 method signatures:
   - Live.TakeLane.TakeLane.create_audio_clip
   - Live.TakeLane.TakeLane.create_midi_clip
   - Live.Clip.Clip.get_notes_extended
   - Live.Application.Application.open_dialog_count
4. Verbatim string and symbol presence directly in the Mach-O binary image.
"""

import hashlib
import json
import re
import subprocess
from pathlib import Path
try:
    import pytest
    fixture = pytest.fixture
except ImportError:
    class DummyPytest:
        @staticmethod
        def fixture(*args, **kwargs):
            def decorator(fn):
                return fn
            return decorator

        @staticmethod
        def skip(msg=""):
            return None
    pytest = DummyPytest()
    fixture = pytest.fixture

REPO_ROOT = Path(__file__).resolve().parent.parent
JSON_PATH = REPO_ROOT / "docs" / "lom_surface_12_4_6.json"
LIVE_BINARY_PATH = Path("/Applications/Ableton Live 12 Suite.app/Contents/MacOS/Live")


@fixture(scope="module")
def lom_catalog():
    assert JSON_PATH.exists(), f"LOM catalog JSON not found at {JSON_PATH}"
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@fixture(scope="module")
def arm64_binary_symbols():
    if not LIVE_BINARY_PATH.exists():
        pytest.skip(f"Live binary not found at {LIVE_BINARY_PATH} (skipping binary inspection in CI)")
    p1 = subprocess.Popen(
        ["nm", "-arch", "arm64", str(LIVE_BINARY_PATH)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    p2 = subprocess.Popen(
        ["c++filt"],
        stdin=p1.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    p1.stdout.close()
    out, _ = p2.communicate()
    assert p2.returncode == 0, "c++filt failed"

    pattern = re.compile(r"registered_base<([^>]+(?:<[^>]+>)*) const volatile&>")
    symbols = set()
    for line in out.splitlines():
        if "__ZN5boost6python9converter6detail15registered_base" in line or "registered_base<" in line:
            m = pattern.search(line)
            if m:
                symbols.add(m.group(1))
    return symbols


@fixture(scope="module")
def x86_64_binary_symbols():
    if not LIVE_BINARY_PATH.exists():
        pytest.skip(f"Live binary not found at {LIVE_BINARY_PATH} (skipping binary inspection in CI)")
    p1 = subprocess.Popen(
        ["nm", "-arch", "x86_64", str(LIVE_BINARY_PATH)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    p2 = subprocess.Popen(
        ["c++filt"],
        stdin=p1.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    p1.stdout.close()
    out, _ = p2.communicate()
    assert p2.returncode == 0, "c++filt failed"

    pattern = re.compile(r"registered_base<([^>]+(?:<[^>]+>)*) const volatile&>")
    symbols = set()
    for line in out.splitlines():
        if "__ZN5boost6python9converter6detail15registered_base" in line or "registered_base<" in line:
            m = pattern.search(line)
            if m:
                symbols.add(m.group(1))
    return symbols


@fixture(scope="module")
def binary_bytes():
    if not LIVE_BINARY_PATH.exists():
        pytest.skip(f"Live binary not found at {LIVE_BINARY_PATH} (skipping binary inspection in CI)")
    with open(LIVE_BINARY_PATH, "rb") as f:
        return f.read()


# ==============================================================================
# 1. Mach-O Binary & Symbol Table Verification
# ==============================================================================


class TestMachOSymbolTable:
    def test_binary_exists_and_sha256_matches_metadata(self, lom_catalog):
        if not LIVE_BINARY_PATH.exists():
            pytest.skip(f"Live binary not found at {LIVE_BINARY_PATH} (skipping binary inspection in CI)")
        h = hashlib.sha256()
        with open(LIVE_BINARY_PATH, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        actual_sha = h.hexdigest()
        expected_sha = lom_catalog["metadata"]["binary_sha256"]
        assert actual_sha == expected_sha
        assert actual_sha == "5e8832e06fe92d42ceebac4fad153e44422c90923f426dcb05c760c6d80b3949"

    def test_symbol_count_is_exactly_184(self, lom_catalog):
        types = lom_catalog["boost_python_types"]["all_types"]
        assert len(types) == 184
        assert len(set(types)) == 184, "Found duplicate symbols in all_types"

    def test_every_symbol_exists_in_arm64_symbol_table(self, lom_catalog, arm64_binary_symbols):
        json_types = set(lom_catalog["boost_python_types"]["all_types"])
        missing = json_types - arm64_binary_symbols
        assert not missing, f"Symbols in JSON but missing in arm64 binary symbol table: {missing}"

    def test_no_unaccounted_boost_python_symbols_in_arm64(self, lom_catalog, arm64_binary_symbols):
        json_types = set(lom_catalog["boost_python_types"]["all_types"])
        extra = arm64_binary_symbols - json_types
        assert not extra, f"Symbols in arm64 binary missing in JSON catalog: {extra}"

    def test_every_symbol_exists_in_x86_64_symbol_table(self, lom_catalog, x86_64_binary_symbols):
        json_types = set(lom_catalog["boost_python_types"]["all_types"])
        missing = json_types - x86_64_binary_symbols
        assert not missing, f"Symbols in JSON but missing in x86_64 binary symbol table: {missing}"

    def test_arm64_and_x86_64_symbols_are_identical(self, arm64_binary_symbols, x86_64_binary_symbols):
        diff = arm64_binary_symbols ^ x86_64_binary_symbols
        assert not diff, f"Architecture discrepancy in symbol table: {diff}"


# ==============================================================================
# 2. JSON Schema & Anti-Dummy/Stub Verification
# ==============================================================================


class TestJsonSchemaAndQuality:
    def test_top_level_structure(self, lom_catalog):
        expected_keys = {
            "metadata",
            "boost_python_types",
            "lom_classes",
            "enums",
            "mxd_reflection",
            "binary_string_table",
        }
        assert set(lom_catalog.keys()) == expected_keys

    def test_metadata_fields(self, lom_catalog):
        meta = lom_catalog["metadata"]
        assert meta["live_version"] == "12.4.6"
        assert meta["bundle_identifier"] == "com.ableton.live"
        assert meta["embedded_python_version"] == "3.11.6"
        assert meta["boost_python_types_count"] == 184
        assert meta["cataloged_classes_count"] >= 29
        assert meta["mxd_classes_count"] >= 43

    def test_no_null_values_except_canonical_roots(self, lom_catalog):
        allowed_null_paths = {
            "lom_classes.Live.Application.Application.canonical_parent",
            "lom_classes.Live.Base.Timer.canonical_parent",
        }
        null_paths = []

        def check_nulls(obj, path=""):
            if obj is None:
                null_paths.append(path)
            elif isinstance(obj, dict):
                for k, v in obj.items():
                    check_nulls(v, f"{path}.{k}" if path else k)
            elif isinstance(obj, list):
                for i, v in enumerate(obj):
                    check_nulls(v, f"{path}[{i}]")

        check_nulls(lom_catalog)
        unexpected_nulls = set(null_paths) - allowed_null_paths
        assert not unexpected_nulls, f"Unexpected null values found at: {unexpected_nulls}"

    def test_no_empty_strings(self, lom_catalog):
        empty_str_paths = []

        def check_empty_strings(obj, path=""):
            if isinstance(obj, str):
                if not obj.strip():
                    empty_str_paths.append(path)
            elif isinstance(obj, dict):
                for k, v in obj.items():
                    check_empty_strings(v, f"{path}.{k}" if path else k)
            elif isinstance(obj, list):
                for i, v in enumerate(obj):
                    check_empty_strings(v, f"{path}[{i}]")

        check_empty_strings(lom_catalog)
        assert not empty_str_paths, f"Found empty strings at: {empty_str_paths[:10]}"

    def test_no_dummy_or_stub_markers(self, lom_catalog):
        forbidden_patterns = [
            re.compile(r"\b" + re.escape(f.lower()) + r"\b")
            for f in ["TODO", "FIXME", "placeholder", "dummy_value", "mock_value", "stub_value"]
        ]
        detected = []

        def scan_text(obj, path=""):
            if isinstance(obj, str):
                for p in forbidden_patterns:
                    if p.search(obj.lower()):
                        detected.append((path, p.pattern, obj[:50]))
            elif isinstance(obj, dict):
                for k, v in obj.items():
                    scan_text(v, f"{path}.{k}" if path else k)
            elif isinstance(obj, list):
                for i, v in enumerate(obj):
                    scan_text(v, f"{path}[{i}]")

        scan_text(lom_catalog)
        assert not detected, f"Detected dummy/stub markers: {detected}"

    def test_all_lom_classes_are_populated(self, lom_catalog):
        classes = lom_catalog["lom_classes"]
        assert len(classes) >= 29
        for name, cls in classes.items():
            assert "description" in cls and len(cls["description"]) > 10, f"{name} missing description"
            assert "properties" in cls and isinstance(cls["properties"], dict), f"{name} missing properties"
            assert "methods" in cls and isinstance(cls["methods"], dict), f"{name} missing methods"
            # Cannot be both empty
            assert len(cls["properties"]) > 0 or len(cls["methods"]) > 0, f"{name} is an empty stub class!"

    def test_property_descriptors_schema(self, lom_catalog):
        for c_name, cls in lom_catalog["lom_classes"].items():
            for p_name, prop in cls["properties"].items():
                assert "type" in prop and prop["type"], f"{c_name}.{p_name} missing type"
                if c_name == "Live.Clip.MidiNoteSpecification":
                    assert ("mandatory" in prop and isinstance(prop["mandatory"], bool)) or ("default" in prop), f"{c_name}.{p_name} missing mandatory/default"
                else:
                    assert "access" in prop and prop["access"] in ("read-only", "read/write"), f"{c_name}.{p_name} invalid access"
                if "has_listener" in prop:
                    assert isinstance(prop["has_listener"], bool), f"{c_name}.{p_name} invalid has_listener type"
                assert "doc" in prop and len(prop["doc"]) > 0, f"{c_name}.{p_name} missing doc"

    def test_method_descriptors_schema(self, lom_catalog):
        for c_name, cls in lom_catalog["lom_classes"].items():
            for m_name, meth in cls["methods"].items():
                assert "args" in meth and isinstance(meth["args"], list), f"{c_name}.{m_name} missing args"
                for arg in meth["args"]:
                    assert "name" in arg and arg["name"], f"{c_name}.{m_name} arg missing name"
                    assert "type" in arg and arg["type"], f"{c_name}.{m_name} arg missing type"
                assert "returns" in meth and meth["returns"], f"{c_name}.{m_name} missing returns"
                assert "doc" in meth and len(meth["doc"]) > 0, f"{c_name}.{m_name} missing doc"

    def test_enums_catalog(self, lom_catalog):
        enums = lom_catalog["enums"]
        assert len(enums) == 28
        for e_name, values in enums.items():
            assert isinstance(values, list)
            assert len(values) >= 1, f"Enum {e_name} has no values"
            for v in values:
                assert isinstance(v, str) and v.strip(), f"Enum {e_name} has invalid value {v}"

    def test_mxd_reflection_classes(self, lom_catalog):
        mxd_classes = lom_catalog["mxd_reflection"]["classes"]
        assert len(mxd_classes) == 43
        for c_name, prop_list in mxd_classes.items():
            assert isinstance(prop_list, list)
            assert len(prop_list) >= 1, f"MxD class {c_name} has empty property list"
            for p in prop_list:
                assert "name" in p and p["name"]
                assert "format" in p and isinstance(p["format"], int)
                assert "min_epii_version" in p and isinstance(p["min_epii_version"], list) and len(p["min_epii_version"]) == 2
                assert "hidden" in p and isinstance(p["hidden"], bool)


# ==============================================================================
# 3. Live 12 Specific Method Signatures & Binary Verbatim Verification
# ==============================================================================


class TestLive12SpecificMethodSignatures:
    def test_takelane_create_audio_clip_signature(self, lom_catalog):
        takelane = lom_catalog["lom_classes"]["Live.TakeLane.TakeLane"]
        assert "create_audio_clip" in takelane["methods"]
        m = takelane["methods"]["create_audio_clip"]
        args = {a["name"]: a["type"] for a in m["args"]}
        assert args == {"file_path": "str", "time": "float"}
        assert m["returns"] == "Live.Clip.Clip"
        assert "Creates an audio clip referencing the file" in m["doc"]
        assert "[0., 1576800.]" in m["doc"]

    def test_takelane_create_midi_clip_signature(self, lom_catalog):
        takelane = lom_catalog["lom_classes"]["Live.TakeLane.TakeLane"]
        assert "create_midi_clip" in takelane["methods"]
        m = takelane["methods"]["create_midi_clip"]
        args = {a["name"]: a["type"] for a in m["args"]}
        assert args == {"time": "float", "length": "float"}
        assert m["returns"] == "Live.Clip.Clip"
        assert "Creates an empty MIDI clip" in m["doc"]
        assert "non-MIDI track" in m["doc"]

    def test_clip_get_notes_extended_signature(self, lom_catalog):
        clip = lom_catalog["lom_classes"]["Live.Clip.Clip"]
        assert "get_notes_extended" in clip["methods"]
        m = clip["methods"]["get_notes_extended"]
        args = {a["name"]: a["type"] for a in m["args"]}
        assert args == {
            "from_pitch": "int",
            "pitch_span": "int",
            "from_time": "float",
            "time_span": "float",
        }
        assert m["returns"] == "tuple[Live.Clip.MidiNote]"
        assert "Returns a list of MIDI notes" in m["doc"]

    def test_application_open_dialog_count_signature(self, lom_catalog):
        app = lom_catalog["lom_classes"]["Live.Application.Application"]
        assert "open_dialog_count" in app["properties"]
        p = app["properties"]["open_dialog_count"]
        assert p["type"] == "int"
        assert p["access"] == "read-only"
        assert p["has_listener"] is True
        assert "number of open dialogs in Live" in p["doc"]

    def test_verbatim_docstrings_in_binary_image(self, binary_bytes):
        # 1. TakeLane create_audio_clip docstring
        assert b"Creates an audio clip referencing the file at the given path and inserts it into the arrangement at the specified time." in binary_bytes
        # 2. TakeLane create_midi_clip docstring
        assert b"Creates an empty MIDI clip and inserts it into the arrangement at the specified time." in binary_bytes
        # 3. Clip get_notes_extended docstring
        assert b"Returns a list of MIDI notes from the given pitch and time range.\nEach note is represented by a Live.Clip.MidiNote object." in binary_bytes
        # 4. Application open_dialog_count docstring
        assert b"The number of open dialogs in Live. 0 if not dialog is open." in binary_bytes

    def test_live12_extended_midi_note_attributes(self, lom_catalog):
        midi_note = lom_catalog["lom_classes"]["Live.Clip.MidiNote"]
        props = set(midi_note["properties"].keys())
        expected_attrs = {
            "note_id",
            "pitch",
            "start_time",
            "duration",
            "velocity",
            "mute",
            "probability",
            "velocity_deviation",
            "release_velocity",
        }
        assert props == expected_attrs, f"MidiNote properties mismatch: {props ^ expected_attrs}"

    def test_live12_specialized_devices_present(self, lom_catalog):
        classes = lom_catalog["lom_classes"]
        specialized = [
            "Live.MeldDevice.MeldDevice",
            "Live.RoarDevice.RoarDevice",
            "Live.DriftDevice.DriftDevice",
            "Live.CcControlDevice.CcControlDevice",
            "Live.SpectralResonatorDevice.SpectralResonatorDevice",
            "Live.WavetableDevice.WavetableDevice",
            "Live.SimplerDevice.SimplerDevice",
            "Live.RackDevice.RackDevice",
            "Live.TuningSystem.TuningSystem",
        ]
        for s in specialized:
            assert s in classes, f"Specialized Live 12 class {s} missing from LOM classes catalog"

    def test_takelane_arrangement_clips_not_clips(self, lom_catalog):
        takelane = lom_catalog["lom_classes"]["Live.TakeLane.TakeLane"]
        assert "arrangement_clips" in takelane["properties"], "TakeLane must have arrangement_clips"
        assert "clips" not in takelane["properties"], "TakeLane must not have hallucinated clips property"
        assert takelane["properties"]["arrangement_clips"]["access"] == "read-only"
        assert "get_data" in takelane["methods"]
        assert "set_data" in takelane["methods"]

    def test_simpler_device_replace_sample_and_sample_slicing(self, lom_catalog):
        simpler = lom_catalog["lom_classes"]["Live.SimplerDevice.SimplerDevice"]
        assert "replace_sample" in simpler["methods"], "SimplerDevice missing replace_sample"
        assert simpler["methods"]["replace_sample"]["args"][0]["name"] == "file_path"
        assert simpler["methods"]["replace_sample"]["args"][0]["type"] == "str"
        assert "slice_to_drum_rack" not in simpler["methods"], "SimplerDevice contains hallucinated slice_to_drum_rack"
        assert "guess_playback_length" in simpler["methods"]
        assert "warp_as" in simpler["methods"]
        sample = lom_catalog["lom_classes"]["Live.Sample.Sample"]
        assert "slicing_style" in sample["properties"]
        assert "slicing_beat_division" in sample["properties"]
        assert "slicing_region_count" in sample["properties"]

    def test_rack_device_variation_and_macro_mutators(self, lom_catalog):
        rack = lom_catalog["lom_classes"]["Live.RackDevice.RackDevice"]
        assert "store_variation" in rack["methods"]
        assert "recall_selected_variation" in rack["methods"]
        assert "delete_selected_variation" in rack["methods"]
        assert "recall_last_used_variation" in rack["methods"]
        assert "add_macro" in rack["methods"]
        assert "remove_macro" in rack["methods"]
        assert "randomize_macros" in rack["methods"]
        assert "store_macro_variation" not in rack["methods"]
        assert "recall_macro_variation" not in rack["methods"]
        assert "delete_macro_variation" not in rack["methods"]
        assert "selected_variation_index" in rack["properties"]
        assert "variation_count" in rack["properties"]
        assert "visible_macro_count" in rack["properties"]

    def test_spectral_resonator_specialized_properties(self, lom_catalog):
        spectral = lom_catalog["lom_classes"]["Live.SpectralResonatorDevice.SpectralResonatorDevice"]
        props = spectral["properties"]
        for p in [
            "frequency_dial_mode_list", "frequency_dial_mode",
            "midi_gate_list", "midi_gate",
            "mod_mode_list", "mod_mode",
            "mono_poly_list", "mono_poly",
            "pitch_mode", "pitch_bend_range", "polyphony"
        ]:
            assert p in props, f"SpectralResonatorDevice missing {p}"

    def test_drift_device_and_cc_control_device_targets(self, lom_catalog):
        drift = lom_catalog["lom_classes"]["Live.DriftDevice.DriftDevice"]
        dprops = drift["properties"]
        assert "voice_count_list" in dprops
        assert "voice_count_index" in dprops
        assert "pitch_bend_range" in dprops
        assert "mod_matrix_shape_source_list" in dprops
        cc = lom_catalog["lom_classes"]["Live.CcControlDevice.CcControlDevice"]
        cprops = cc["properties"]
        assert "custom_bool_target_list" in cprops
        assert "custom_float_target_0_list" in cprops
        assert "custom_float_target_11" in cprops
        assert "resend" in cc["methods"]

    def test_clip_playback_and_audio_warping_properties(self, lom_catalog):
        clip = lom_catalog["lom_classes"]["Live.Clip.Clip"]
        cprops = clip["properties"]
        for p in [
            "warping", "warp_mode", "available_warp_modes", "gain",
            "file_path", "length", "position", "playing_position",
            "is_playing", "is_recording", "start_marker", "end_marker"
        ]:
            assert p in cprops, f"Clip missing {p}"
        assert "fire" in clip["methods"]
        assert "stop" in clip["methods"]
        assert "duplicate_loop" in clip["methods"]
        assert "crop" in clip["methods"]

    def test_browser_item_definition(self, lom_catalog):
        assert "Live.Browser.BrowserItem" in lom_catalog["lom_classes"]
        bprops = lom_catalog["lom_classes"]["Live.Browser.BrowserItem"]["properties"]
        for p in ["name", "source", "uri", "is_folder", "is_device", "is_loadable", "is_selected", "children", "iter_children"]:
            assert p in bprops, f"BrowserItem missing {p}"

    def test_scene_and_song_signature_and_transport(self, lom_catalog):
        scene = lom_catalog["lom_classes"]["Live.Scene.Scene"]
        sprops = scene["properties"]
        assert "time_signature_numerator" in sprops
        assert "time_signature_denominator" in sprops
        assert "time_signature_enabled" in sprops
        assert "tempo_enabled" in sprops
        assert "time_signature" not in sprops
        song = lom_catalog["lom_classes"]["Live.Song.Song"]
        song_props = song["properties"]
        assert "metronome" in song_props
        assert "groove_amount" in song_props
        assert "swing_amount" in song_props
        assert "tap_tempo" in song["methods"]
        assert "jump_to_next_cue" in song["methods"]
        assert "jump_to_prev_cue" in song["methods"]
        assert "set_or_delete_cue" in song["methods"]
        assert "duplicate_scene" in song["methods"]

    def test_all_49_classes_cataloged(self, lom_catalog):
        classes = lom_catalog["lom_classes"]
        assert len(classes) == 49, f"Expected 49 classes, found {len(classes)}"
        mxd_classes = lom_catalog["mxd_reflection"]["classes"]
        for mxd_cls in mxd_classes:
            assert mxd_cls in classes, f"MxD class {mxd_cls} missing from lom_classes"

    def test_binary_string_table_retention(self, lom_catalog):
        assert "binary_string_table" in lom_catalog
        bst = lom_catalog["binary_string_table"]
        assert "class_blocks" in bst
        assert len(bst["class_blocks"]) >= 49
        assert bst["raw_tokens_count"] > 1000


def run_all_checks():
    """Execute all test methods directly without pytest for standalone verification."""
    print("Executing Standalone Empirical Verification Suite for Milestone 1...")
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    # 1. MachO
    p1 = subprocess.Popen(["nm", "-arch", "arm64", str(LIVE_BINARY_PATH)], stdout=subprocess.PIPE, text=True)
    p2 = subprocess.Popen(["c++filt"], stdin=p1.stdout, stdout=subprocess.PIPE, text=True)
    p1.stdout.close()
    out_arm, _ = p2.communicate()
    pattern = re.compile(r"registered_base<([^>]+(?:<[^>]+>)*) const volatile&>")
    arm_syms = {pattern.search(l).group(1) for l in out_arm.splitlines() if pattern.search(l)}

    p3 = subprocess.Popen(["nm", "-arch", "x86_64", str(LIVE_BINARY_PATH)], stdout=subprocess.PIPE, text=True)
    p4 = subprocess.Popen(["c++filt"], stdin=p3.stdout, stdout=subprocess.PIPE, text=True)
    p3.stdout.close()
    out_x86, _ = p4.communicate()
    x86_syms = {pattern.search(l).group(1) for l in out_x86.splitlines() if pattern.search(l)}

    with open(LIVE_BINARY_PATH, "rb") as f:
        bin_data = f.read()

    test_classes = [
        (TestMachOSymbolTable(), {
            "lom_catalog": catalog,
            "arm64_binary_symbols": arm_syms,
            "x86_64_binary_symbols": x86_syms,
        }),
        (TestJsonSchemaAndQuality(), {
            "lom_catalog": catalog,
        }),
        (TestLive12SpecificMethodSignatures(), {
            "lom_catalog": catalog,
            "binary_bytes": bin_data,
        }),
    ]

    passed = 0
    total = 0
    for instance, fixture_map in test_classes:
        class_name = instance.__class__.__name__
        print(f"\n--- {class_name} ---")
        for attr in dir(instance):
            if attr.startswith("test_"):
                total += 1
                method = getattr(instance, attr)
                import inspect
                sig = inspect.signature(method)
                kwargs = {k: fixture_map[k] for k in sig.parameters if k in fixture_map}
                try:
                    method(**kwargs)
                    print(f"  [PASS] {attr}")
                    passed += 1
                except Exception as e:
                    print(f"  [FAIL] {attr}: {e}")
                    raise

    print(f"\n==================================================")
    print(f"Empirical Challenge Suite PASSED: {passed}/{total} tests green!")
    print(f"==================================================")


if __name__ == "__main__":
    run_all_checks()
