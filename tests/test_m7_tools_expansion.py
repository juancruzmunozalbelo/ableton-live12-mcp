"""Tests for Milestone 7: Expansion of Ableton Live 12 MCP catalog to 75 tools."""

import pytest
import jsonschema
from jsonschema import Draft7Validator

from ableton_live12_mcp.tools import ALL_TOOLS, get_tool_catalog
from tests.harness import MockAbletonBridge, Live12TestClient


NEW_14_TOOL_NAMES = [
    # Domain 1
    "live12_cue_point_control",
    "live12_tempo_sync_control",
    # Domain 2
    "live12_scene_set_properties",
    "live12_routing_get",
    # Domain 3
    "live12_clip_duplicate_to_arrangement",
    "live12_clip_remove_notes",
    "live12_clip_transform_midi",
    "live12_clip_envelope_control",
    "live12_groove_pool_control",
    # Domain 4
    "live12_browser_preview",
    "live12_rack_macro_config",
    "live12_drum_pad_control",
    "live12_cc_control",
    # Domain 5
    "live12_undo_redo",
]


class TestM7CatalogIntegrity:
    """Verifies total count, schema correctness, and presence of all 14 new tools."""

    def test_total_catalog_count_is_75(self):
        assert len(ALL_TOOLS) == 75, f"Expected 75 tools in ALL_TOOLS, found {len(ALL_TOOLS)}"
        catalog = get_tool_catalog()
        assert len(catalog) == 75, f"Expected 75 tools in get_tool_catalog(), found {len(catalog)}"

    def test_all_14_new_tools_present_and_valid_schema(self):
        catalog_map = {t["name"]: t for t in get_tool_catalog()}
        for tool_name in NEW_14_TOOL_NAMES:
            assert tool_name in catalog_map, f"Tool {tool_name} missing from catalog"
            tool = catalog_map[tool_name]
            assert tool["description"] and len(tool["description"]) > 10
            schema = tool["inputSchema"]
            assert schema["type"] == "object"
            assert "properties" in schema
            # Verify Draft-07 compliance
            Draft7Validator.check_schema(schema)


class TestM7Domain1SongAndTransport:
    """Tests cue points and tempo sync control in MockAbletonBridge."""

    @pytest.fixture
    def bridge(self):
        return MockAbletonBridge()

    def test_cue_point_lifecycle(self, bridge: MockAbletonBridge):
        # Create cue points
        c1 = bridge.execute_tool("live12_cue_point_control", {"action": "create", "name": "Intro", "time": 0.0})
        assert not c1.is_error
        assert c1.raw["cue_points_count"] == 1

        c2 = bridge.execute_tool("live12_cue_point_control", {"action": "create", "name": "Drop", "time": 32.0})
        assert not c2.is_error
        assert c2.raw["cue_points_count"] == 2

        # List cue points
        lst = bridge.execute_tool("live12_cue_point_control", {"action": "list"})
        assert not lst.is_error
        points = lst.raw["cue_points"]
        assert len(points) == 2
        assert points[0]["name"] == "Intro"
        assert points[1]["name"] == "Drop"
        assert points[1]["time"] == 32.0

        # Jump to cue point
        jmp = bridge.execute_tool("live12_cue_point_control", {"action": "jump", "cue_index": 1})
        assert not jmp.is_error
        assert jmp.raw["time"] == 32.0

        # Delete cue point
        del_res = bridge.execute_tool("live12_cue_point_control", {"action": "delete", "cue_index": 0})
        assert not del_res.is_error
        assert del_res.raw["success"] is True

    def test_tempo_sync_control(self, bridge: MockAbletonBridge):
        # Query initial status
        st = bridge.execute_tool("live12_tempo_sync_control", {"action": "get_status"})
        assert not st.is_error
        assert st.raw["link_enabled"] is False

        # Enable link
        link = bridge.execute_tool("live12_tempo_sync_control", {"action": "set_link", "enabled": True})
        assert not link.is_error
        assert link.raw["link_enabled"] is True

        # Enable follower
        fol = bridge.execute_tool("live12_tempo_sync_control", {"action": "set_follower", "enabled": True})
        assert not fol.is_error
        assert fol.raw["tempo_follower_enabled"] is True

        # Tap tempo
        tap = bridge.execute_tool("live12_tempo_sync_control", {"action": "tap_tempo"})
        assert not tap.is_error
        assert tap.raw["success"] is True


class TestM7Domain2TracksAndScenes:
    """Tests scene properties and routing queries."""

    @pytest.fixture
    def harness(self):
        h = Live12TestClient(mode="mock")
        h.call_tool("live12_track_create", {"type": "midi"})
        yield h
        h.teardown()

    def test_scene_set_properties_and_boundaries(self, harness: Live12TestClient):
        res = harness.call_tool("live12_scene_set_properties", {
            "scene_index": 0,
            "name": "Chorus Section",
            "tempo": 128.5,
            "tempo_enabled": True,
            "time_signature_numerator": 3,
            "time_signature_denominator": 4,
            "time_signature_enabled": True,
        })
        assert not res.is_error
        assert res.raw["name"] == "Chorus Section"
        assert res.raw["tempo"] == 128.5
        assert res.raw["tempo_enabled"] is True
        assert res.raw["time_signature_numerator"] == 3
        assert res.raw["time_signature_denominator"] == 4

        # Reject out of bounds tempo (< 20.0 or > 999.0)
        bad_tempo = harness.call_tool("live12_scene_set_properties", {"scene_index": 0, "tempo": 10.0})
        assert bad_tempo.is_error

    def test_routing_get(self, harness: Live12TestClient):
        res = harness.call_tool("live12_routing_get", {"track_index": 0})
        assert not res.is_error
        assert res.raw["track_index"] == 0
        assert "input_routing_type" in res.raw
        assert "available_input_routing_types" in res.raw
        assert "output_routing_type" in res.raw
        assert "available_output_routing_types" in res.raw


class TestM7Domain3ClipsAndMIDI:
    """Tests arrangement duplication, note removal, MIDI transforms, envelopes, and groove pool."""

    @pytest.fixture
    def harness(self):
        h = Live12TestClient(mode="mock")
        h.call_tool("live12_track_create", {"type": "midi"})
        h.call_tool("live12_clip_create", {"track_index": 0, "slot_index": 0, "length_beats": 4.0})
        h.call_tool("live12_clip_add_notes", {
            "track_index": 0, "slot_index": 0,
            "notes": [
                {"pitch": 60, "start_time": 0.0, "duration": 1.0, "velocity": 100.0},
                {"pitch": 64, "start_time": 1.0, "duration": 1.0, "velocity": 90.0},
                {"pitch": 67, "start_time": 2.0, "duration": 1.0, "velocity": 80.0},
                {"pitch": 72, "start_time": 3.0, "duration": 1.0, "velocity": 70.0},
            ]
        })
        yield h
        h.teardown()

    def test_clip_duplicate_to_arrangement(self, harness: Live12TestClient):
        res = harness.call_tool("live12_clip_duplicate_to_arrangement", {
            "track_index": 0,
            "slot_index": 0,
            "arrangement_time": 16.0,
        })
        assert not res.is_error
        assert res.raw["arrangement_time"] == 16.0
        # Check track arrangement clips in mock
        track = harness._mock_bridge.tracks[0]
        assert len(track.arrangement_clips) == 1
        arr_clip, arr_t = track.arrangement_clips[0]
        assert arr_t == 16.0
        assert len(arr_clip.notes) == 4

    def test_clip_remove_notes_by_time_pitch_span(self, harness: Live12TestClient):
        # Remove note at pitch 60 (time 0.0 to 1.0)
        res = harness.call_tool("live12_clip_remove_notes", {
            "track_index": 0,
            "slot_index": 0,
            "from_pitch": 60,
            "pitch_span": 2,
            "start_time": 0.0,
            "time_span": 1.0,
        })
        assert not res.is_error
        assert res.raw["removed_count"] == 1
        # 3 notes remaining
        notes_res = harness.call_tool("live12_clip_get_notes", {"track_index": 0, "slot_index": 0})
        assert len(notes_res.raw["notes"]) == 3

    def test_clip_transform_midi_humanize_and_ramp(self, harness: Live12TestClient):
        # Velocity ramp
        ramp = harness.call_tool("live12_clip_transform_midi", {
            "track_index": 0,
            "slot_index": 0,
            "transformation": "velocity_ramp",
            "params": {"start_velocity": 40.0, "end_velocity": 120.0}
        })
        assert not ramp.is_error
        assert ramp.raw["notes_affected"] == 4

        # Humanize
        hum = harness.call_tool("live12_clip_transform_midi", {
            "track_index": 0,
            "slot_index": 0,
            "transformation": "humanize",
            "params": {"timing_jitter": 0.05, "velocity_jitter": 5.0}
        })
        assert not hum.is_error
        assert hum.raw["notes_affected"] == 4

    def test_clip_envelope_control(self, harness: Live12TestClient):
        # Set envelope step
        step = harness.call_tool("live12_clip_envelope_control", {
            "track_index": 0,
            "slot_index": 0,
            "action": "set_step",
            "parameter_identifier": "Volume",
            "time": 2.0,
            "value": 0.75,
        })
        assert not step.is_error

        # Inspect
        insp = harness.call_tool("live12_clip_envelope_control", {
            "track_index": 0,
            "slot_index": 0,
            "action": "inspect",
        })
        assert not insp.is_error
        assert insp.raw["has_envelopes"] is True

        # Clear
        clr = harness.call_tool("live12_clip_envelope_control", {
            "track_index": 0,
            "slot_index": 0,
            "action": "clear_all",
        })
        assert not clr.is_error
        assert clr.raw["all_cleared"] is True

    def test_groove_pool_control(self, harness: Live12TestClient):
        # List pool
        pool = harness.call_tool("live12_groove_pool_control", {"action": "list_pool"})
        assert not pool.is_error
        assert len(pool.raw["grooves"]) >= 2

        # Set song amount
        amt = harness.call_tool("live12_groove_pool_control", {"action": "set_song_amount", "amount": 0.8})
        assert not amt.is_error
        assert amt.raw["groove_amount"] == 0.8

        # Assign groove to clip
        asn = harness.call_tool("live12_groove_pool_control", {
            "action": "assign_clip",
            "track_index": 0,
            "slot_index": 0,
            "groove_index": 0,
        })
        assert not asn.is_error

        # Get clip groove
        get_gr = harness.call_tool("live12_groove_pool_control", {
            "action": "get_clip_groove",
            "track_index": 0,
            "slot_index": 0,
        })
        assert not get_gr.is_error
        assert get_gr.raw["has_groove"] is True


class TestM7Domain4DevicesAndBrowser:
    """Tests browser preview, rack macro config, drum pad control, and CC control."""

    @pytest.fixture
    def harness(self):
        h = Live12TestClient(mode="mock")
        h.call_tool("live12_track_create", {"type": "midi"})
        h.call_tool("live12_browser_load_item", {"track_index": 0, "browser_item_uri": "query:Instrument Rack"})
        yield h
        h.teardown()

    def test_browser_preview(self, harness: Live12TestClient):
        # Preview
        p = harness.call_tool("live12_browser_preview", {"action": "preview", "browser_item_uri": "sample:kick.wav"})
        assert not p.is_error
        assert p.raw["preview_active"] is True

        # Stop
        s = harness.call_tool("live12_browser_preview", {"action": "stop"})
        assert not s.is_error
        assert s.raw["preview_active"] is False

    def test_rack_macro_config(self, harness: Live12TestClient):
        # Get config
        cfg = harness.call_tool("live12_rack_macro_config", {
            "track_index": 0, "device_index": 0, "action": "get_config"
        })
        assert not cfg.is_error
        assert cfg.raw["visible_macro_count"] == 8

        # Set count to 12
        set_c = harness.call_tool("live12_rack_macro_config", {
            "track_index": 0, "device_index": 0, "action": "set_count", "count": 12
        })
        assert not set_c.is_error
        assert set_c.raw["visible_macro_count"] == 12

        # Add macro
        add_m = harness.call_tool("live12_rack_macro_config", {
            "track_index": 0, "device_index": 0, "action": "add_macro"
        })
        assert not add_m.is_error
        assert add_m.raw["visible_macro_count"] == 13

        # Randomize
        rnd = harness.call_tool("live12_rack_macro_config", {
            "track_index": 0, "device_index": 0, "action": "randomize"
        })
        assert not rnd.is_error
        assert rnd.raw["randomized"] is True

    def test_drum_pad_control(self, harness: Live12TestClient):
        # Inspect pads
        pads = harness.call_tool("live12_drum_pad_control", {
            "track_index": 0, "device_index": 0, "action": "inspect_pads"
        })
        assert not pads.is_error
        assert len(pads.raw["pads"]) >= 1

        # Mute pad 36
        mute = harness.call_tool("live12_drum_pad_control", {
            "track_index": 0, "device_index": 0, "action": "mute_pad", "pad_note": 36, "state": True
        })
        assert not mute.is_error
        assert mute.raw["mute"] is True

        # Copy pad 36 to pad 38
        cp = harness.call_tool("live12_drum_pad_control", {
            "track_index": 0, "device_index": 0, "action": "copy_pad", "pad_note": 36, "target_note": 38
        })
        assert not cp.is_error
        assert cp.raw["target_note"] == 38

    def test_cc_control(self, harness: Live12TestClient):
        # Send CC 74 (Filter Cutoff) = 100 on Channel 1
        cc = harness.call_tool("live12_cc_control", {
            "track_index": 0, "device_index": 0, "action": "set_cc", "cc_number": 74, "value": 100, "channel": 1
        })
        assert not cc.is_error
        assert cc.raw["cc_number"] == 74
        assert cc.raw["value"] == 100

        # Get mappings
        maps = harness.call_tool("live12_cc_control", {
            "track_index": 0, "device_index": 0, "action": "get_mappings"
        })
        assert not maps.is_error
        assert "mappings" in maps.raw


class TestM7Domain5ViewAndUndo:
    """Tests undo/redo control."""

    @pytest.fixture
    def harness(self):
        h = Live12TestClient(mode="mock")
        yield h
        h.teardown()

    def test_undo_redo_control(self, harness: Live12TestClient):
        # Status
        st = harness.call_tool("live12_undo_redo", {"action": "status"})
        assert not st.is_error
        assert "can_undo" in st.raw
        assert "can_redo" in st.raw

        # Step management
        beg = harness.call_tool("live12_undo_redo", {"action": "begin_step"})
        assert not beg.is_error
        assert beg.raw["step_active"] is True

        end = harness.call_tool("live12_undo_redo", {"action": "end_step"})
        assert not end.is_error
        assert end.raw["step_active"] is False

        # Undo
        u = harness.call_tool("live12_undo_redo", {"action": "undo"})
        assert not u.is_error
        assert u.raw["undone"] is True

        # Redo
        r = harness.call_tool("live12_undo_redo", {"action": "redo"})
        assert not r.is_error
        assert r.raw["redone"] is True
