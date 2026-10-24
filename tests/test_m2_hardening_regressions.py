"""
Unit and Regression Tests for Milestone 2: Bridge & MCP Server Hardening
========================================================================
Validates:
1. reflection.py vector check extension for BrowserItemVector, TrackVector, WarpMarkerVector.
2. handlers.py get_notes_extended argument order (0, 128, 0.0, 65536.0).
3. handlers.py live12_browser_load_item real track selection and app.browser.load_item invocation.
4. handlers.py live12_clip_envelope_control action set_step invoking insert_step / create_event.
5. live12_take_lane_create_audio_clip tool schema, server registration, and bridge handler.
"""

import math
import os
import pytest
from jsonschema import Draft7Validator

from ableton_live12_mcp.tools.take_lane_tools import TAKE_LANE_TOOLS
from ableton_live12_mcp.tools import TOOL_MAP, get_tool_by_name, validate_tool_call
from ableton_live12_mcp.server import McpServer
from live12_bridge.reflection import serialize_lom_value
from live12_bridge.handlers import BridgeHandlers, dispatch_tool_call
from tests.harness import MockAbletonBridge, Live12TestClient


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
# 1. Vector Serialization (reflection.py)
# ==============================================================================

class BrowserItemVector(list):
    """Simulates Boost.Python BrowserItemVector."""
    pass


class TrackVector(list):
    """Simulates Boost.Python TrackVector."""
    pass


class WarpMarkerVector(list):
    """Simulates Boost.Python WarpMarkerVector."""
    pass


def test_vector_reflection_serialization():
    """Confirms BrowserItemVector, TrackVector, WarpMarkerVector serialize as lists."""
    b_vec = BrowserItemVector(["item1", "item2", 42])
    t_vec = TrackVector(["audio_track", "midi_track"])
    w_vec = WarpMarkerVector([1.0, 2.5, 4.0])

    res_b = serialize_lom_value(b_vec)
    res_t = serialize_lom_value(t_vec)
    res_w = serialize_lom_value(w_vec)

    assert isinstance(res_b, list)
    assert res_b == ["item1", "item2", 42]

    assert isinstance(res_t, list)
    assert res_t == ["audio_track", "midi_track"]

    assert isinstance(res_w, list)
    assert res_w == [1.0, 2.5, 4.0]


# ==============================================================================
# 2. get_notes_extended Argument Order (handlers.py)
# ==============================================================================

class MockNoteItem:
    def __init__(self, note_id: int = 1, pitch: int = 60):
        self.note_id = note_id
        self.pitch = pitch
        self.start_time = 0.0
        self.duration = 1.0
        self.velocity = 100.0


class MockClipWithExactNotesSignature:
    def __init__(self):
        self.notes = [MockNoteItem(101, 60), MockNoteItem(102, 64)]
        self.last_get_notes_args = None
        self.last_applied_notes = None

    def add_new_notes(self, specs):
        pass

    def get_notes_extended(self, from_pitch, pitch_span, from_time, time_span):
        self.last_get_notes_args = (from_pitch, pitch_span, from_time, time_span)
        # Verify pitch_span is 128 covering all MIDI notes, not 0
        assert pitch_span == 128, f"Expected pitch_span == 128, got {pitch_span}"
        assert from_pitch == 0, f"Expected from_pitch == 0, got {from_pitch}"
        assert math.isclose(from_time, 0.0), f"Expected from_time == 0.0, got {from_time}"
        assert math.isclose(time_span, 65536.0), f"Expected time_span == 65536.0, got {time_span}"
        return tuple(self.notes)

    def apply_note_modifications(self, modified_notes):
        self.last_applied_notes = modified_notes


def test_get_notes_extended_argument_order():
    """Validates get_notes_extended is called with (0, 128, 0.0, 65536.0)."""
    clip = MockClipWithExactNotesSignature()

    class MockSlot:
        def __init__(self, c):
            self.clip = c

    class MockTrack:
        def __init__(self, c):
            self.clip_slots = [MockSlot(c)]

    class MockSong:
        def __init__(self, c):
            self.tracks = [MockTrack(c)]

    song = MockSong(clip)
    cs = MockCS(song=song)
    handlers = BridgeHandlers(cs=cs)

    # 1. Test live12_clip_add_notes retrieval
    res_add = handlers.live12_clip_add_notes(
        track_index=0,
        slot_index=0,
        notes=[{"pitch": 60, "start_time": 0.0, "duration": 1.0, "velocity": 100.0}],
    )
    assert res_add["status"] == "success"
    assert clip.last_get_notes_args == (0, 128, 0.0, 65536.0)

    # 2. Test live12_clip_modify_notes retrieval
    res_mod = handlers.live12_clip_modify_notes(
        track_index=0,
        slot_index=0,
        note_modifications=[{"note_id": 101, "velocity": 120.0}],
    )
    assert res_mod["status"] == "success"
    assert clip.last_get_notes_args == (0, 128, 0.0, 65536.0)
    assert clip.last_applied_notes is not None


# ==============================================================================
# 3. live12_browser_load_item Track Selection & Loading (handlers.py)
# ==============================================================================

class MockBrowserItem:
    def __init__(self, name: str, uri: str, is_loadable: bool = True, is_folder: bool = False, children=()):
        self.name = name
        self.uri = uri
        self.is_loadable = is_loadable
        self.is_folder = is_folder
        self.children = children


class MockBrowser:
    def __init__(self):
        self.loaded_items = []
        self.wavetable_item = MockBrowserItem("Wavetable", "live:device:wavetable", is_loadable=True)
        self.instruments = MockBrowserItem("Instruments", "live:cat:instruments", is_folder=True, children=[self.wavetable_item])

    def load_item(self, item):
        self.loaded_items.append(item)


class MockApplication:
    def __init__(self, browser):
        self.browser = browser


class MockSongView:
    def __init__(self):
        self.selected_track = None


class MockSongForBrowser:
    def __init__(self, num_tracks: int = 2):
        self.tracks = [f"Track_{i}" for i in range(num_tracks)]
        self.view = MockSongView()


def test_browser_load_item_track_selection_and_invocation():
    """Validates that browser_load_item focuses track and invokes app.browser.load_item."""
    browser = MockBrowser()
    app = MockApplication(browser)
    song = MockSongForBrowser(num_tracks=3)
    cs = MockCS(song=song, app=app)

    handlers = BridgeHandlers(cs=cs)

    res = handlers.live12_browser_load_item(
        track_index=1,
        browser_item_uri="live:device:wavetable",
    )

    assert res["status"] == "loaded"
    assert res["track_index"] == 1
    # Verify track selection in UI view
    assert song.view.selected_track == song.tracks[1]
    # Verify app.browser.load_item was invoked with the resolved item
    assert len(browser.loaded_items) == 1
    assert browser.loaded_items[0].name == "Wavetable"
    assert browser.loaded_items[0].uri == "live:device:wavetable"


# ==============================================================================
# 4. live12_clip_envelope_control set_step (handlers.py)
# ==============================================================================

class MockEnvelope:
    def __init__(self):
        self.steps = []
        self.events = []

    def insert_step(self, time: float, length: float, value: float):
        self.steps.append((time, length, value))

    def create_event(self, time: float, value: float):
        self.events.append((time, value))


class MockClipWithEnvelope:
    def __init__(self):
        self.envelope = MockEnvelope()
        self.has_envelopes = True

    def automation_envelope(self, parameter):
        return self.envelope


class MockDeviceParam:
    def __init__(self, name: str):
        self.name = name


class MockDevice:
    def __init__(self):
        self.parameters = [MockDeviceParam("Filter Freq"), MockDeviceParam("Resonance")]


def test_clip_envelope_control_set_step():
    """Validates that action set_step calls insert_step on the automation envelope."""
    clip = MockClipWithEnvelope()
    dev = MockDevice()

    class MockSlot:
        def __init__(self, c):
            self.clip = c

    class MockTrack:
        def __init__(self, c, d):
            self.clip_slots = [MockSlot(c)]
            self.devices = [d]

    class MockSong:
        def __init__(self, tr):
            self.tracks = [tr]

    song = MockSong(MockTrack(clip, dev))
    cs = MockCS(song=song)
    handlers = BridgeHandlers(cs=cs)

    res = handlers.live12_clip_envelope_control(
        track_index=0,
        slot_index=0,
        action="set_step",
        device_index=0,
        parameter_identifier="Filter Freq",
        time=4.0,
        value=880.0,
    )

    assert res["status"] == "success"
    assert res["time"] == 4.0
    assert res["value"] == 880.0
    assert res.get("envelope_updated") is True
    # Verify insert_step was genuinely invoked on the envelope
    assert len(clip.envelope.steps) == 1
    assert clip.envelope.steps[0] == (4.0, 0.25, 880.0)


# ==============================================================================
# 5. live12_take_lane_create_audio_clip (take_lane_tools, server, handlers)
# ==============================================================================

def test_take_lane_create_audio_clip_schema():
    """Validates Draft-07 compliance of live12_take_lane_create_audio_clip schema."""
    tool = get_tool_by_name("live12_take_lane_create_audio_clip")
    assert tool is not None, "Tool 'live12_take_lane_create_audio_clip' not found in TOOL_MAP"
    assert tool["name"] == "live12_take_lane_create_audio_clip"
    schema = tool["inputSchema"]
    Draft7Validator.check_schema(schema)

    # Validate valid argument dictionary
    validate_tool_call("live12_take_lane_create_audio_clip", {
        "track_index": 0,
        "take_lane_index": 1,
        "file_path": "/Users/juancruz/samples/kick.wav",
        "time": 8.0,
    })


def test_take_lane_create_audio_clip_server_and_mock_execution():
    """Validates server execution of live12_take_lane_create_audio_clip in mock mode."""
    bridge = MockAbletonBridge()
    # Create an audio track and take lane
    bridge._tool_live12_track_create(type="audio", index=-1)
    bridge._tool_live12_take_lane_create(0)

    # Execute tool via bridge
    res = bridge._tool_live12_take_lane_create_audio_clip(
        track_index=0,
        take_lane_index=0,
        file_path="/Users/juancruz/samples/vocal_comp.wav",
        time=16.0,
    )
    assert res["status"] == "success"
    assert res["track_index"] == 0
    assert res["take_lane_index"] == 0
    assert res["time"] == 16.0
    assert res["file_path"] == "/Users/juancruz/samples/vocal_comp.wav"
    assert res["clip_name"] == "vocal_comp.wav"


def test_take_lane_create_audio_clip_bridge_handler_invocation():
    """Validates BridgeHandlers.live12_take_lane_create_audio_clip invokes TakeLane."""
    class MockClip:
        def __init__(self, name):
            self.name = name

    class MockTakeLane:
        def __init__(self):
            self.created_clips = []

        def create_audio_clip(self, file_path, time):
            self.created_clips.append((file_path, time))
            return MockClip("sample.wav")

    class MockTrack:
        def __init__(self):
            self.take_lanes = [MockTakeLane()]

    class MockSong:
        def __init__(self):
            self.tracks = [MockTrack()]

    song = MockSong()
    cs = MockCS(song=song)
    handlers = BridgeHandlers(cs=cs)

    res = handlers.live12_take_lane_create_audio_clip(
        track_index=0,
        take_lane_index=0,
        file_path="/path/to/sample.wav",
        time=32.0,
    )

    assert res["status"] == "success"
    assert res["track_index"] == 0
    assert res["take_lane_index"] == 0
    assert res["time"] == 32.0
    assert res["clip_name"] == "sample.wav"
    assert song.tracks[0].take_lanes[0].created_clips == [("/path/to/sample.wav", 32.0)]


def test_take_lane_create_audio_clip_boundaries():
    """Validates out-of-bounds error handling."""
    bridge = MockAbletonBridge()
    bridge._tool_live12_track_create(type="audio", index=-1)

    # Negative track index
    with pytest.raises(IndexError):
        bridge._tool_live12_take_lane_create_audio_clip(-1, 0, "/dummy.wav", 0.0)

    # Out of range take lane
    with pytest.raises(IndexError):
        bridge._tool_live12_take_lane_create_audio_clip(0, 99, "/dummy.wav", 0.0)

    # Negative time
    with pytest.raises(ValueError):
        bridge._tool_live12_take_lane_create_audio_clip(0, 0, "/dummy.wav", -1.0)

    # NaN time
    with pytest.raises(ValueError):
        bridge._tool_live12_take_lane_create_audio_clip(0, 0, "/dummy.wav", float("nan"))


# ==============================================================================
# 6. Track / Scene Palette Color (Live 12 `color_index`)
# ==============================================================================

def test_track_color_uses_palette_index_not_rgb():
    """`color` in 0..69 must set the Live 12 palette slot (`color_index`).

    Regression: the handler used to assign the raw integer to `Track.color`
    (the packed RGB property), which silently left every track on the default
    palette slot 69 in the GUI.
    """
    bridge = MockAbletonBridge()
    bridge._tool_live12_track_create(type="midi", index=-1)

    res = bridge._tool_live12_track_set_properties(track_index=0, color=14)

    assert res["color_index"] == 14
    assert bridge.tracks[0].color_index == 14


def test_track_color_index_explicit_and_rgb_fallback():
    """`color_index` sets the palette slot; values > 69 stay packed-RGB."""
    bridge = MockAbletonBridge()
    bridge._tool_live12_track_create(type="midi", index=-1)

    res = bridge._tool_live12_track_set_properties(track_index=0, color_index=42)
    assert res["color_index"] == 42
    assert bridge.tracks[0].color_index == 42

    res_rgb = bridge._tool_live12_track_set_properties(track_index=0, color=16711680)
    assert res_rgb["color_rgb"] == [255, 0, 0]
    assert bridge.tracks[0].color == (255, 0, 0)


def test_track_color_index_out_of_range_rejected():
    bridge = MockAbletonBridge()
    bridge._tool_live12_track_create(type="midi", index=-1)
    with pytest.raises(ValueError):
        bridge._tool_live12_track_set_properties(track_index=0, color_index=70)


def test_scene_color_uses_palette_index():
    bridge = MockAbletonBridge()
    res = bridge._tool_live12_scene_set_properties(scene_index=0, color=17)
    assert res["color_index"] == 17
    assert bridge.scenes[0].color_index == 17


def test_color_params_are_in_tool_schemas():
    """The MCP schemas must expose the palette-index parameters."""
    for tool_name in ("live12_track_set_properties", "live12_scene_set_properties"):
        tool = get_tool_by_name(tool_name)
        assert tool is not None
        props = tool["inputSchema"]["properties"]
        assert "color_index" in props
        assert props["color_index"]["maximum"] == 69
        assert "color_rgb" in props


# ==============================================================================
# 7. Arrangement clip deletion (Live 12 `Track.delete_clip`)
# ==============================================================================

def test_clip_delete_arrangement_removes_clip():
    """`live12_clip_delete_arrangement` removes a clip from the arrangement."""
    bridge = MockAbletonBridge()
    bridge._tool_live12_track_create(type="audio", index=-1)
    track = bridge.tracks[0]

    class _ArrangementClip:
        def __init__(self, name):
            self.name = name

    track.arrangement_clips.append((_ArrangementClip("A"), 0.0))
    track.arrangement_clips.append((_ArrangementClip("B"), 16.0))

    res = bridge._tool_live12_clip_delete_arrangement(track_index=0, clip_index=0)
    assert res["deleted"] is True
    assert res["remaining_clips"] == 1
    assert len(track.arrangement_clips) == 1


def test_clip_delete_arrangement_out_of_range():
    bridge = MockAbletonBridge()
    bridge._tool_live12_track_create(type="audio", index=-1)
    with pytest.raises(IndexError):
        bridge._tool_live12_clip_delete_arrangement(0, 5)
    with pytest.raises(IndexError):
        bridge._tool_live12_clip_delete_arrangement(9, 0)


def test_clip_delete_arrangement_tool_schema_registered():
    tool = get_tool_by_name("live12_clip_delete_arrangement")
    assert tool is not None
    assert tool["inputSchema"]["required"] == ["track_index", "clip_index"]
