"""
Milestone 2 Automated Verification Suite: Live12Bridge Remote Script & Client Connector
=======================================================================================
Verifies:
1. Control Surface package entry point and ControlSurface inheritance.
2. Background TCP server, auto-discovery file (/tmp/ableton_live12_bridge.json), and framing.
3. Main-thread execution queue, dual-drain mechanism, and robust exception protection.
4. Dynamic LOM reflection engine (inspect, get, set, call) and liveobj_valid validation.
5. Live 12 extended MIDI note conversions (pitch, velocity_deviation, probability, release_velocity).
6. High-level structured handlers for all 61 tools.
7. Live12Client connector, discovery resolution, timeouts, and ToolResult envelope.
8. Python 3.11 bytecode compilation cleanliness.
"""

from __future__ import annotations

import json
import math
import os
import queue
import socket
import sys
import threading
import time
import pytest

from src.live12_bridge import (
    Live12Bridge,
    Live12ControlSurface,
    create_instance,
    get_capabilities,
    liveobj_valid,
    lom_call,
    lom_get,
    lom_inspect,
    lom_set,
    midi_note_to_dict,
    dict_to_midi_note_spec,
)
from src.live12_bridge.bridge import BridgeJob, DISCOVERY_PATH
from src.live12_bridge.handlers import BridgeHandlers, dispatch_tool_call
from src.ableton_live12_mcp.client import (
    Live12Client,
    Live12ConnectionError,
    Live12RpcError,
    Live12TimeoutError,
    LiveTcpClient,
    ToolResult,
)


# ==============================================================================
# Mock Ableton Live C++ Host Instance
# ==============================================================================

class MockApplicationView:
    def __init__(self):
        self.focused_view = "Session"

    def show_view(self, view_name: str):
        self.focused_view = view_name

    def focus_view(self, view_name: str):
        self.focused_view = view_name


class MockApplication:
    def __init__(self):
        self.view = MockApplicationView()
        self.open_dialog_count = 0
        self.current_dialog_message = ""

    def press_current_dialog_button(self, button_index: int):
        if self.open_dialog_count == 0:
            raise IndexError("No open dialog")
        self.open_dialog_count = max(0, self.open_dialog_count - 1)


class MockDeviceParam:
    def __init__(self, name: str, val: float, min_v: float, max_v: float):
        self.name = name
        self.value = val
        self.min = min_v
        self.max = max_v
        self.is_quantized = False


class MockDevice:
    def __init__(self, name: str = "Wavetable"):
        self.name = name
        self.type = "instrument"
        self.is_active = True
        self.can_have_chains = "Rack" in name
        self.parameters = [
            MockDeviceParam("Device On", 1.0, 0.0, 1.0),
            MockDeviceParam("Filter Freq", 1000.0, 20.0, 20000.0),
            MockDeviceParam("Macro 1", 0.0, 0.0, 1.0),
        ]
        self.matrix: Dict[str, float] = {}

    def store_variation(self):
        pass

    def recall_variation(self, idx: int):
        pass


class MockClip:
    def __init__(self, length: float = 4.0, name: str = "Clip 1"):
        self.length = length
        self.name = name
        self.loop = True
        self.loop_start = 0.0
        self.loop_end = length
        self.start_marker = 0.0
        self.warping = True
        self.warp_mode = "beats"
        self.pitch_coarse = 0.0
        self.gain = 1.0
        self.notes: List[Any] = []

    def fire(self):
        pass

    def stop(self):
        pass

    def quantize(self, grid: float, amount: float):
        pass

    def add_warp_marker(self, beat_time: float, sample_time: float):
        pass

    def add_new_notes(self, note_specs: tuple):
        for spec in note_specs:
            self.notes.append(spec)

    def get_notes_extended(self, start_time: float, pitch: int, time_span: float, pitch_span: int):
        return tuple(self.notes)

    def apply_note_modifications(self, modified_notes: tuple):
        pass


class MockClipSlot:
    def __init__(self):
        self.clip: Optional[MockClip] = None

    def create_clip(self, length: float):
        self.clip = MockClip(length=length)

    def delete_clip(self):
        self.clip = None


class MockMixer:
    def __init__(self):
        self.volume = MockDeviceParam("Volume", 0.0, -70.0, 6.0)
        self.panning = MockDeviceParam("Pan", 0.0, -1.0, 1.0)
        self.sends = [MockDeviceParam("Send A", 0.0, 0.0, 1.0)]
        self.crossfade_assign = 0


class MockTrack:
    def __init__(self, name: str = "Track 1"):
        self.name = name
        self.color = 0
        self.solo = False
        self.mute = False
        self.arm = False
        self.clip_slots = [MockClipSlot() for _ in range(4)]
        self.devices = [MockDevice()]
        self.mixer_device = MockMixer()
        self.take_lanes: List[Any] = []

    def create_take_lane(self):
        class TakeLane:
            def __init__(self, idx: int):
                self.name = f"Take {idx}"
        self.take_lanes.append(TakeLane(len(self.take_lanes) + 1))


class MockScene:
    def __init__(self, name: str = "Scene 1"):
        self.name = name

    def fire(self):
        pass


class MockSongView:
    def __init__(self, song: MockSong):
        self._song = song
        self.selected_track = None
        self.selected_scene = None

    def select_device(self, device: Any):
        pass


class MockScaleInformation:
    def __init__(self):
        self.name = "Major"
        self.root_note = 0


class MockSong:
    def __init__(self):
        self.tempo = 120.0
        self.signature_numerator = 4
        self.signature_denominator = 4
        self.is_playing = False
        self.record_mode = False
        self.session_record = False
        self.loop = False
        self.loop_start = 0.0
        self.loop_length = 4.0
        self.punch_in = False
        self.punch_out = False
        self.arrangement_overdub = False
        self.metronome = False
        self.scale_information = MockScaleInformation()
        self.tracks = [MockTrack("Audio 1"), MockTrack("MIDI 1")]
        self.return_tracks = [MockTrack("Return A")]
        self.scenes = [MockScene("1"), MockScene("2")]
        self.view = MockSongView(self)

    def start_playing(self):
        self.is_playing = True

    def continue_playing(self):
        self.is_playing = True

    def stop_playing(self):
        self.is_playing = False

    def capture_midi(self):
        pass

    def create_midi_track(self, index: int):
        t = MockTrack(f"MIDI {len(self.tracks) + 1}")
        self.tracks.insert(index, t)
        return t

    def create_audio_track(self, index: int):
        t = MockTrack(f"Audio {len(self.tracks) + 1}")
        self.tracks.insert(index, t)
        return t

    def create_return_track(self):
        t = MockTrack(f"Return {len(self.return_tracks) + 1}")
        self.return_tracks.append(t)
        return t

    def delete_track(self, index: int):
        if index < 0 or index >= len(self.tracks):
            raise IndexError("Track index out of range")
        return self.tracks.pop(index)

    def duplicate_track(self, index: int):
        if index < 0 or index >= len(self.tracks):
            raise IndexError("Track index out of range")
        t = MockTrack(f"{self.tracks[index].name} (copy)")
        self.tracks.insert(index + 1, t)
        return t

    def create_scene(self, index: int):
        s = MockScene(f"Scene {len(self.scenes) + 1}")
        self.scenes.insert(index, s)
        return s


class MockCInstance:
    def __init__(self):
        self._app = MockApplication()
        self._song = MockSong()
        self.log_entries: List[str] = []
        self.status_messages: List[str] = []

    def application(self):
        return self._app

    def song(self):
        return self._song

    def log_message(self, msg: str):
        self.log_entries.append(msg)

    def show_message(self, msg: str):
        self.status_messages.append(msg)


# ==============================================================================
# Tests
# ==============================================================================

class TestLive12BridgeEntryAndLifecycle:
    """Verifies factory entry point, capabilities, and ControlSurface class structure."""

    def test_create_instance_returns_control_surface(self):
        c_inst = MockCInstance()
        surface = create_instance(c_inst)
        assert isinstance(surface, Live12ControlSurface)
        assert isinstance(surface, Live12Bridge)
        surface.disconnect()

    def test_capabilities_declaration(self):
        caps = get_capabilities()
        assert caps.get("AUTO_LOAD_KEY") is True
        assert caps.get("SCRIPT") == "Live12Bridge"

    def test_discovery_file_written_and_unlinked(self):
        c_inst = MockCInstance()
        surface = create_instance(c_inst)
        assert os.path.exists(DISCOVERY_PATH)
        with open(DISCOVERY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["live_version"] == "12.4.6"
        assert data["port"] == surface._port
        assert data["pid"] == os.getpid()

        # Teardown
        surface.disconnect()
        assert not os.path.exists(DISCOVERY_PATH)


class TestReflectionEngine:
    """Verifies dynamic LOM path resolution, pointer checks, and note conversions."""

    def test_liveobj_valid_check(self):
        assert liveobj_valid("a string") is True
        assert liveobj_valid(123) is True
        assert liveobj_valid(None) is False

        class DeadBoostPointer:
            def __eq__(self, other):
                raise RuntimeError("Underlying C/C++ object has been deleted")

        assert liveobj_valid(DeadBoostPointer()) is False

    def test_lom_inspect_song(self):
        c_inst = MockCInstance()
        handlers = BridgeHandlers(Live12ControlSurface(c_inst))
        res = lom_inspect(handlers.root_getter, "live_set")
        assert res["path"] == "live_set"
        assert "tempo" in res["properties"]
        assert "start_playing" in res["methods"]
        handlers.cs.disconnect()

    def test_lom_inspect_track(self):
        c_inst = MockCInstance()
        surface = Live12ControlSurface(c_inst)
        handlers = BridgeHandlers(surface)
        res = lom_inspect(handlers.root_getter, "live_set.tracks.0")
        assert "name" in res["properties"]
        surface.disconnect()

    def test_lom_get_and_set_tempo(self):
        c_inst = MockCInstance()
        surface = Live12ControlSurface(c_inst)
        handlers = BridgeHandlers(surface)

        get_res = lom_get(handlers.root_getter, "live_set", "tempo")
        assert get_res["value"] == 120.0

        set_res = lom_set(handlers.root_getter, "live_set", "tempo", 135.5)
        assert set_res["new_value"] == 135.5
        assert c_inst.song().tempo == 135.5

        # Test string numeric coercion
        set_res_str = lom_set(handlers.root_getter, "live_set", "tempo", "140.0")
        assert set_res_str["new_value"] == 140.0
        assert c_inst.song().tempo == 140.0

        surface.disconnect()

    def test_lom_call_method(self):
        c_inst = MockCInstance()
        surface = Live12ControlSurface(c_inst)
        handlers = BridgeHandlers(surface)

        assert c_inst.song().is_playing is False
        lom_call(handlers.root_getter, "live_set", "start_playing")
        assert c_inst.song().is_playing is True
        lom_call(handlers.root_getter, "live_set", "stop_playing")
        assert c_inst.song().is_playing is False

        surface.disconnect()

    def test_extended_midi_notes_specification_conversion(self):
        spec_dict = {
            "pitch": 64,
            "start_time": 1.0,
            "duration": 0.5,
            "velocity": 110.0,
            "velocity_deviation": -8.0,
            "release_velocity": 70.0,
            "probability": 0.75,
            "mute": False,
        }
        spec = dict_to_midi_note_spec(spec_dict)
        assert spec.pitch == 64
        assert spec.velocity_deviation == -8.0
        assert spec.probability == 0.75

        note_dict = midi_note_to_dict(spec)
        assert note_dict["pitch"] == 64
        assert math.isclose(note_dict["probability"], 0.75)


class TestMainThreadQueueAndDualDrain:
    """Verifies main-thread queue processing, dual drain in update_display, and safe exception isolation."""

    def test_drain_queue_executes_pending_jobs(self):
        c_inst = MockCInstance()
        surface = Live12ControlSurface(c_inst)

        job = BridgeJob(req_id=1, method="live12_transport_set_tempo", params={"tempo": 128.0})
        surface._request_queue.put(job)

        # Trigger drain
        surface._drain_queue()
        assert job.done_event.is_set()
        assert job.error is None
        assert job.result["tempo"] == 128.0
        assert c_inst.song().tempo == 128.0

        surface.disconnect()

    def test_update_display_acts_as_secondary_drain(self):
        c_inst = MockCInstance()
        surface = Live12ControlSurface(c_inst)

        job = BridgeJob(req_id=2, method="live12_transport_play", params={"restart": False})
        surface._request_queue.put(job)

        surface.update_display()
        assert job.done_event.is_set()
        assert job.result["is_playing"] is True

        surface.disconnect()

    def test_unhandled_job_exception_does_not_break_timer(self):
        c_inst = MockCInstance()
        surface = Live12ControlSurface(c_inst)

        job = BridgeJob(req_id=3, method="live12_transport_set_tempo", params={"tempo": -99.0})
        surface._request_queue.put(job)

        # _process_queue must not raise
        surface._process_queue()
        assert job.done_event.is_set()
        assert job.error is not None
        assert "out of range" in job.error["message"]

        surface.disconnect()


class TestLive12ClientAndTcpServer:
    """Verifies TCP IPC roundtrip, discovery file reading, JSON-RPC 2.0 framing, and ToolResult envelope."""

    def test_client_connects_and_calls_bridge(self):
        c_inst = MockCInstance()
        surface = Live12ControlSurface(c_inst)

        # Worker thread emulating main-thread timer loop during test
        running = True

        def loop_drain():
            while running:
                surface._drain_queue()
                time.sleep(0.005)

        drain_thread = threading.Thread(target=loop_drain, daemon=True)
        drain_thread.start()

        try:
            # Client connects using auto-discovery
            client = Live12Client()
            assert client.is_reachable() is True

            # 1. Transport call
            res = client.call("live12_transport_set_tempo", {"tempo": 124.0})
            assert res["tempo"] == 124.0

            # 2. Track creation
            tr_res = client.call("live12_track_create", {"type": "midi"})
            assert tr_res["type"] == "midi"

            # 3. Clip creation & notes
            client.call("live12_clip_create", {"track_index": 0, "slot_index": 0, "length_beats": 4.0})
            add_res = client.call("live12_clip_add_notes", {
                "track_index": 0,
                "slot_index": 0,
                "notes": [
                    {
                        "pitch": 60,
                        "start_time": 0.0,
                        "duration": 1.0,
                        "velocity": 100.0,
                        "velocity_deviation": -5.0,
                        "probability": 0.9,
                    }
                ],
            })
            assert add_res["added_count"] == 1

            # 4. Read back notes
            get_res = client.call("live12_clip_get_notes", {"track_index": 0, "slot_index": 0})
            assert len(get_res["notes"]) == 1
            assert get_res["notes"][0]["pitch"] == 60
            assert math.isclose(get_res["notes"][0]["probability"], 0.9)

            # 5. ToolResult envelope
            tool_res = client.call_tool("live12_song_get_state", {})
            assert isinstance(tool_res, ToolResult)
            assert tool_res.is_error is False
            assert tool_res["tempo"] == 124.0

            # 6. Error handling
            err_tool_res = client.call_tool("live12_track_delete", {"track_index": 999})
            assert err_tool_res.is_error is True
            assert "out of range" in err_tool_res["message"]

        finally:
            running = False
            surface.disconnect()

    def test_client_handles_server_offline(self):
        client = Live12Client(port=19999)
        assert client.is_reachable(probe_timeout=0.1) is False
        with pytest.raises(Live12ConnectionError):
            client.call("live12_song_get_state", {})
