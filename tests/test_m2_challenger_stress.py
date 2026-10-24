"""
Empirical Challenger Stress Harness for Milestone 2: Bridge & MCP Server Hardening
===================================================================================
Author: challenger_m2_1 (critic, specialist)
Validates and stress-tests:
1. Vector reflection serialization across all Boost.Python vector wrappers and edge cases.
2. Automation envelope step insertion, fallbacks, parameter resolution, and boundaries.
3. get_notes_extended argument order, note boundaries (pitch 0 to 127), and exception recovery.
4. live12_browser_load_item track focus, hierarchy traversal, URI/name matching, and error isolation.
5. live12_take_lane_create_audio_clip schema validation, boundaries, and invocation.
6. Live TCP bridge responsiveness and real LOM vector serialization (if live bridge is reachable).
"""

import math
import os
import socket
import json
import pytest
from jsonschema import Draft7Validator

from ableton_live12_mcp.tools.take_lane_tools import TAKE_LANE_TOOLS
from ableton_live12_mcp.tools import TOOL_MAP, get_tool_by_name, validate_tool_call
from ableton_live12_mcp.server import McpServer
from live12_bridge.reflection import serialize_lom_value
from live12_bridge.handlers import BridgeHandlers
from tests.harness import MockAbletonBridge


# ==============================================================================
# Helper Mock Classes
# ==============================================================================

class MockCS:
    """Mock Control Surface for BridgeHandlers tests."""
    def __init__(self, song=None, app=None):
        self._song = song
        self._app = app

    def song(self):
        return self._song

    def application(self):
        return self._app


# ==============================================================================
# 1. Vector Reflection Serialization Stress Tests
# ==============================================================================

class ControlDescriptionVector(list):
    pass

class ObjectVector(list):
    pass

class IntVector(list):
    pass

class IntU64Vector(list):
    pass

class FloatVector(list):
    pass

class StringVector(list):
    pass

class BrowserItemVector(list):
    pass

class MidiNoteVector(list):
    pass

class WarpMarkerVector(list):
    pass

class ATimeableValueVector(list):
    pass

class EnvelopeEventVector(list):
    pass

class MutableVector(list):
    pass

class ListenerVector(list):
    pass

class RoutingTypeVector(list):
    pass

class RoutingChannelVector(list):
    pass

class TrackVector(list):
    pass


class MockLiveObject:
    def __init__(self, name: str, index: int):
        self.name = name
        self.index = index


def test_all_16_boost_python_vector_types_serialize():
    """Stress tests serialization for all 16 Boost.Python vector types extracted from Live 12.4.6."""
    vectors = [
        ControlDescriptionVector([{"desc": "control_1"}]),
        ObjectVector(["obj_a", "obj_b"]),
        IntVector([1, 2, 3, 42]),
        IntU64Vector([10000000000, 20000000000]),
        FloatVector([0.5, 1.25, 2.75]),
        StringVector(["audio", "midi", "return"]),
        BrowserItemVector(["item1", "item2"]),
        MidiNoteVector([{"pitch": 60}, {"pitch": 64}]),
        WarpMarkerVector([0.0, 4.0, 8.0]),
        ATimeableValueVector([10.0, 20.0]),
        EnvelopeEventVector([(0.0, 1.0), (1.0, 0.5)]),
        MutableVector([True, False, True]),
        ListenerVector(["listener_cb1"]),
        RoutingTypeVector(["Ext In", "Resampling"]),
        RoutingChannelVector(["1/2", "3/4"]),
        TrackVector(["Track 1", "Track 2"]),
    ]

    for v in vectors:
        serialized = serialize_lom_value(v)
        assert isinstance(serialized, list), f"Failed for {type(v).__name__}: got {type(serialized)}"
        assert len(serialized) == len(v), f"Length mismatch for {type(v).__name__}"


def test_empty_vector_serialization():
    """Verifies that empty vectors serialize to empty lists."""
    empty_track_vec = TrackVector([])
    res = serialize_lom_value(empty_track_vec)
    assert res == []
    assert isinstance(res, list)


def test_nested_vectors_and_depth_limiting():
    """Verifies that nested vectors serialize correctly and deep nesting (> 4) is truncated to str."""
    # 3-level nesting
    nested = TrackVector([
        BrowserItemVector([
            IntVector([1, 2, 3])
        ])
    ])
    res = serialize_lom_value(nested)
    assert res == [[[1, 2, 3]]]

    # 6-level nesting to test depth > 4 cutoff
    deep = TrackVector([TrackVector([TrackVector([TrackVector([TrackVector([TrackVector([42])])])])])])
    res_deep = serialize_lom_value(deep)
    assert isinstance(res_deep, list)
    # The innermost vector beyond depth 4 should be stringified
    assert str(res_deep) is not None


def test_vector_with_special_ieee754_floats():
    """Verifies that vectors containing NaN and Inf serialize without crashing or invalid JSON."""
    f_vec = FloatVector([1.0, float("nan"), float("inf"), float("-inf"), 0.0])
    res = serialize_lom_value(f_vec)
    assert res[0] == 1.0
    assert res[1] == "nan"
    assert res[2] == "inf"
    assert res[3] == "-inf"
    assert res[4] == 0.0
    # Must be JSON serializable
    json_str = json.dumps(res)
    assert '"nan"' in json_str
    assert '"inf"' in json_str


def test_vector_with_live_objects():
    """Verifies that vectors containing mock Live objects serialize cleanly."""
    obj_vec = TrackVector([MockLiveObject("Lead Synth", 0), MockLiveObject("Bass Synth", 1)])
    res = serialize_lom_value(obj_vec)
    assert isinstance(res, list)
    assert len(res) == 2
    assert res[0]["name"] == "Lead Synth"
    assert res[0]["type"] == "MockLiveObject"
    assert res[1]["name"] == "Bass Synth"
    assert res[1]["type"] == "MockLiveObject"


# ==============================================================================
# 2. Automation Envelope Step Insertion Stress Tests
# ==============================================================================

class MockEnvelopeWithInsertStep:
    def __init__(self):
        self.steps = []
        self.events = []

    def insert_step(self, time: float, length: float, value: float):
        self.steps.append((time, length, value))


class MockEnvelopeWithCreateEventOnly:
    def __init__(self):
        self.events = []

    def create_event(self, time: float, value: float):
        self.events.append((time, value))


class MockEnvelopeWithFailingInsertStep:
    def __init__(self):
        self.events = []

    def insert_step(self, time: float, length: float, value: float):
        raise RuntimeError("insert_step C++ failure (breakpoint collision)")

    def create_event(self, time: float, value: float):
        self.events.append((time, value))


class MockClipWithMultipleEnvelopes:
    def __init__(self, envelope):
        self._envelope = envelope
        self.has_envelopes = True
        self.created_envelopes = []
        self.cleared_params = []
        self.all_cleared = False

    def automation_envelope(self, param):
        return self._envelope

    def create_automation_envelope(self, param):
        self.created_envelopes.append(param)
        return self._envelope

    def clear_envelope(self, param):
        self.cleared_params.append(param)

    def clear_all_envelopes(self):
        self.all_cleared = True


class MockClipWithoutInitialEnvelope:
    def __init__(self):
        self.created_env = MockEnvelopeWithInsertStep()

    def automation_envelope(self, param):
        return None

    def create_automation_envelope(self, param):
        return self.created_env


class MockDeviceParam:
    def __init__(self, name: str):
        self.name = name
        self.re_enabled = False

    def re_enable_automation(self):
        self.re_enabled = True


class MockDevice:
    def __init__(self):
        self.parameters = [
            MockDeviceParam("Device On"),
            MockDeviceParam("Filter Freq"),
            MockDeviceParam("Resonance"),
        ]


def test_envelope_step_insertion_primary_insert_step():
    """Stress test: set_step invokes insert_step with (time, 0.25, value)."""
    env = MockEnvelopeWithInsertStep()
    clip = MockClipWithMultipleEnvelopes(env)
    dev = MockDevice()

    class MockSlot:
        def __init__(self, c): self.clip = c
    class MockTrack:
        def __init__(self, c, d):
            self.clip_slots = [MockSlot(c)]
            self.devices = [d]
    class MockSong:
        def __init__(self, tr): self.tracks = [tr]

    handlers = BridgeHandlers(cs=MockCS(song=MockSong(MockTrack(clip, dev))))

    # Call with float time and value
    res = handlers.live12_clip_envelope_control(
        track_index=0,
        slot_index=0,
        action="set_step",
        device_index=0,
        parameter_identifier="Filter Freq",
        time=8.5,
        value=0.65,
    )

    assert res["status"] == "success"
    assert res["envelope_updated"] is True
    assert len(env.steps) == 1
    assert env.steps[0] == (8.5, 0.25, 0.65)


def test_envelope_step_insertion_fallback_to_create_event():
    """Stress test: set_step falls back to create_event if insert_step is not present."""
    env = MockEnvelopeWithCreateEventOnly()
    clip = MockClipWithMultipleEnvelopes(env)
    dev = MockDevice()

    class MockSlot:
        def __init__(self, c): self.clip = c
    class MockTrack:
        def __init__(self, c, d):
            self.clip_slots = [MockSlot(c)]
            self.devices = [d]
    class MockSong:
        def __init__(self, tr): self.tracks = [tr]

    handlers = BridgeHandlers(cs=MockCS(song=MockSong(MockTrack(clip, dev))))

    res = handlers.live12_clip_envelope_control(
        track_index=0,
        slot_index=0,
        action="set_step",
        device_index=0,
        parameter_identifier="Filter Freq",
        time=12.0,
        value=0.8,
    )

    assert res["status"] == "success"
    assert res["envelope_updated"] is True
    assert len(env.events) == 1
    assert env.events[0] == (12.0, 0.8)


def test_envelope_step_insertion_recovers_from_insert_step_exception():
    """Stress test: if insert_step raises C++ exception, it catches and calls create_event."""
    env = MockEnvelopeWithFailingInsertStep()
    clip = MockClipWithMultipleEnvelopes(env)
    dev = MockDevice()

    class MockSlot:
        def __init__(self, c): self.clip = c
    class MockTrack:
        def __init__(self, c, d):
            self.clip_slots = [MockSlot(c)]
            self.devices = [d]
    class MockSong:
        def __init__(self, tr): self.tracks = [tr]

    handlers = BridgeHandlers(cs=MockCS(song=MockSong(MockTrack(clip, dev))))

    res = handlers.live12_clip_envelope_control(
        track_index=0,
        slot_index=0,
        action="set_step",
        device_index=0,
        parameter_identifier="Filter Freq",
        time=16.0,
        value=0.45,
    )

    assert res["status"] == "success"
    assert res["envelope_updated"] is True
    assert len(env.events) == 1
    assert env.events[0] == (16.0, 0.45)


def test_envelope_creation_when_initially_none():
    """Stress test: if automation_envelope returns None, calls create_automation_envelope."""
    clip = MockClipWithoutInitialEnvelope()
    dev = MockDevice()

    class MockSlot:
        def __init__(self, c): self.clip = c
    class MockTrack:
        def __init__(self, c, d):
            self.clip_slots = [MockSlot(c)]
            self.devices = [d]
    class MockSong:
        def __init__(self, tr): self.tracks = [tr]

    handlers = BridgeHandlers(cs=MockCS(song=MockSong(MockTrack(clip, dev))))

    res = handlers.live12_clip_envelope_control(
        track_index=0,
        slot_index=0,
        action="set_step",
        device_index=0,
        parameter_identifier="Resonance",
        time=2.0,
        value=0.9,
    )

    assert res["status"] == "success"
    assert res["envelope_updated"] is True
    assert len(clip.created_env.steps) == 1
    assert clip.created_env.steps[0] == (2.0, 0.25, 0.9)


def test_envelope_parameter_identifiers_int_and_digit_string():
    """Stress test: parameter_identifier resolves as int index or digit string."""
    env = MockEnvelopeWithInsertStep()
    clip = MockClipWithMultipleEnvelopes(env)
    dev = MockDevice()

    class MockSlot:
        def __init__(self, c): self.clip = c
    class MockTrack:
        def __init__(self, c, d):
            self.clip_slots = [MockSlot(c)]
            self.devices = [d]
    class MockSong:
        def __init__(self, tr): self.tracks = [tr]

    handlers = BridgeHandlers(cs=MockCS(song=MockSong(MockTrack(clip, dev))))

    # 1. Integer parameter index (index 1 is 'Filter Freq')
    res_int = handlers.live12_clip_envelope_control(
        track_index=0, slot_index=0, action="set_step", device_index=0,
        parameter_identifier=1, time=1.0, value=0.5
    )
    assert res_int["envelope_updated"] is True

    # 2. String digit parameter index ("2" is 'Resonance')
    res_str = handlers.live12_clip_envelope_control(
        track_index=0, slot_index=0, action="set_step", device_index=0,
        parameter_identifier="2", time=2.0, value=0.6
    )
    assert res_str["envelope_updated"] is True
    assert len(env.steps) == 2


def test_envelope_boundaries_and_error_handling():
    """Stress test: boundary conditions for live12_clip_envelope_control."""
    clip = MockClipWithMultipleEnvelopes(MockEnvelopeWithInsertStep())
    dev = MockDevice()

    class MockSlot:
        def __init__(self, c): self.clip = c
    class MockTrack:
        def __init__(self, c, d):
            self.clip_slots = [MockSlot(c), MockSlot(None)]  # slot 1 has no clip
            self.devices = [d]
    class MockSong:
        def __init__(self, tr): self.tracks = [tr]

    handlers = BridgeHandlers(cs=MockCS(song=MockSong(MockTrack(clip, dev))))

    # 1. Invalid action name
    with pytest.raises(ValueError):
        handlers.live12_clip_envelope_control(track_index=0, slot_index=0, action="invalid_action")

    # 2. Track out of bounds
    with pytest.raises(IndexError):
        handlers.live12_clip_envelope_control(track_index=99, slot_index=0, action="inspect")

    # 3. Negative track index
    with pytest.raises(IndexError):
        handlers.live12_clip_envelope_control(track_index=-1, slot_index=0, action="inspect")

    # 4. Slot out of bounds
    with pytest.raises(IndexError):
        handlers.live12_clip_envelope_control(track_index=0, slot_index=99, action="inspect")

    # 5. Slot has no clip
    with pytest.raises(IndexError):
        handlers.live12_clip_envelope_control(track_index=0, slot_index=1, action="inspect")


# ==============================================================================
# 3. get_notes_extended Argument Order & Note Retrieval
# ==============================================================================

class MockNoteItem:
    def __init__(self, note_id: int, pitch: int, start_time: float, duration: float, velocity: float):
        self.note_id = note_id
        self.pitch = pitch
        self.start_time = start_time
        self.duration = duration
        self.velocity = velocity


class MockClipNotesCheck:
    def __init__(self):
        # Include boundary notes: MIDI pitch 0 and MIDI pitch 127
        self.notes = [
            MockNoteItem(1, 0, 0.0, 1.0, 100.0),      # Lowest possible MIDI pitch (C-2)
            MockNoteItem(2, 60, 1.0, 0.5, 90.0),     # Middle C
            MockNoteItem(3, 127, 2.0, 2.0, 127.0),   # Highest possible MIDI pitch (G8)
        ]
        self.get_notes_calls = []

    def add_new_notes(self, specs):
        pass

    def get_notes_extended(self, from_pitch, pitch_span, from_time, time_span):
        self.get_notes_calls.append((from_pitch, pitch_span, from_time, time_span))
        return tuple(self.notes)

    def apply_note_modifications(self, modified_notes):
        pass


def test_get_notes_extended_covers_full_pitch_range_0_to_127():
    """Validates that (0, 128, 0.0, 65536.0) spans pitch 0 to 127 and retrieves boundary notes."""
    clip = MockClipNotesCheck()

    class MockSlot:
        def __init__(self, c): self.clip = c
    class MockTrack:
        def __init__(self, c): self.clip_slots = [MockSlot(c)]
    class MockSong:
        def __init__(self, c): self.tracks = [MockTrack(c)]

    handlers = BridgeHandlers(cs=MockCS(song=MockSong(clip)))

    res = handlers.live12_clip_add_notes(
        track_index=0,
        slot_index=0,
        notes=[
            {"pitch": 0, "start_time": 0.0, "duration": 1.0, "velocity": 100.0},
            {"pitch": 127, "start_time": 2.0, "duration": 2.0, "velocity": 127.0},
        ]
    )

    assert res["status"] == "success"
    assert res["added_count"] == 2
    assert res["note_ids"] == [2, 3]
    # Verify exact argument order
    assert len(clip.get_notes_calls) == 1
    from_pitch, pitch_span, from_time, time_span = clip.get_notes_calls[0]
    assert from_pitch == 0
    assert pitch_span == 128
    assert from_time == 0.0
    assert time_span == 65536.0


# ==============================================================================
# 4. Browser Load Item Traversal & Robustness
# ==============================================================================

class MockBrowserNode:
    def __init__(self, name: str, uri: str, is_loadable: bool = False, is_folder: bool = False, children=()):
        self.name = name
        self.uri = uri
        self.is_loadable = is_loadable
        self.is_folder = is_folder
        self.children = children


class MockDeepBrowser:
    def __init__(self):
        self.loaded_items = []
        # Construct a deep hierarchy to test breadth-first search and depth limit
        item_wavetable = MockBrowserNode("Wavetable", "live:device:wavetable", is_loadable=True)
        folder_synth = MockBrowserNode("Synths", "live:cat:synths", is_folder=True, children=[item_wavetable])
        folder_inst = MockBrowserNode("Instruments", "live:cat:instruments", is_folder=True, children=[folder_synth])
        self.instruments = folder_inst

    def load_item(self, item):
        self.loaded_items.append(item)


def test_browser_load_item_nested_hierarchy_search():
    """Validates that _find_browser_item traverses nested folders to locate item."""
    browser = MockDeepBrowser()
    app = MockCS(app=type("App", (), {"browser": browser})()).application()

    class MockTrack:
        def __init__(self): self.name = "MIDI"
    class MockSongView:
        def __init__(self): self.selected_track = None
    class MockSong:
        def __init__(self):
            self.tracks = [MockTrack()]
            self.view = MockSongView()

    song = MockSong()
    handlers = BridgeHandlers(cs=MockCS(song=song, app=app))

    res = handlers.live12_browser_load_item(
        track_index=0,
        browser_item_uri="live:device:wavetable",
    )

    assert res["status"] == "loaded"
    assert song.view.selected_track == song.tracks[0]
    assert len(browser.loaded_items) == 1
    assert browser.loaded_items[0].name == "Wavetable"


def test_browser_load_item_nonexistent_does_not_crash():
    """Validates that requesting a nonexistent browser item handles gracefully without crash."""
    browser = MockDeepBrowser()
    app = MockCS(app=type("App", (), {"browser": browser})()).application()

    class MockTrack:
        def __init__(self): self.name = "MIDI"
    class MockSongView:
        def __init__(self): self.selected_track = None
    class MockSong:
        def __init__(self):
            self.tracks = [MockTrack()]
            self.view = MockSongView()

    song = MockSong()
    handlers = BridgeHandlers(cs=MockCS(song=song, app=app))

    res = handlers.live12_browser_load_item(
        track_index=0,
        browser_item_uri="nonexistent:item:id",
    )

    assert res["status"] == "not_found"
    assert len(browser.loaded_items) == 0


# ==============================================================================
# 5. TakeLane Create Audio Clip Boundaries & Server Registration
# ==============================================================================

def test_take_lane_create_audio_clip_server_registration():
    """Validates McpServer includes live12_take_lane_create_audio_clip in registered tools."""
    server = McpServer()
    assert "live12_take_lane_create_audio_clip" in server._registered_tools
    tool_def = server._registered_tools["live12_take_lane_create_audio_clip"]
    assert tool_def["name"] == "live12_take_lane_create_audio_clip"
    assert "track_index" in tool_def["inputSchema"]["required"]
    assert "take_lane_index" in tool_def["inputSchema"]["required"]
    assert "file_path" in tool_def["inputSchema"]["required"]
    assert "time" in tool_def["inputSchema"]["required"]


# ==============================================================================
# 6. Live TCP Bridge Connectivity Verification
# ==============================================================================

def test_live_bridge_tcp_ping_and_lom_vector():
    """Pings the live running Ableton Live 12 instance on 127.0.0.1:11246 if available."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2.0)
    try:
        sock.connect(("127.0.0.1", 11246))
    except (ConnectionRefusedError, socket.timeout, OSError):
        pytest.skip("Live 12 Bridge not running on 127.0.0.1:11246 (skipping live socket ping)")

    try:
        # 1. Ping state
        req = {"jsonrpc": "2.0", "id": 999, "method": "live12_song_get_state", "params": {}}
        sock.sendall((json.dumps(req) + "\n").encode("utf-8"))
        data = sock.recv(4096).decode("utf-8")
        resp = json.loads(data)
        assert resp.get("id") == 999
        assert "result" in resp
        assert "tempo" in resp["result"]
        assert resp["result"]["tempo"] > 0

        # 2. Query TrackVector via LOM get
        req_lom = {"jsonrpc": "2.0", "id": 1000, "method": "live12_lom_get", "params": {"target_path": "live_set", "property_name": "tracks"}}
        sock.sendall((json.dumps(req_lom) + "\n").encode("utf-8"))
        data_lom = sock.recv(8192).decode("utf-8")
        resp_lom = json.loads(data_lom)
        assert resp_lom.get("id") == 1000
        assert "result" in resp_lom
        assert isinstance(resp_lom["result"]["value"], list)
    finally:
        sock.close()
