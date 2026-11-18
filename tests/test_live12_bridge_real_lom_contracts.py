"""
Strict Live 12 Real-LOM & Client/Server Contract Tests
======================================================
Verifies BridgeHandlers, lom_inspect, McpServer, and Live12Client against strict
Ableton Live 12 LOM semantics (using __slots__ and type-checked properties so
nonexistent fallback attributes like Clip.loop / Clip.notes, writable note_id,
string warp_mode, float pitch_coarse, or deprecated LOM attributes fail immediately).
"""

from __future__ import annotations

import json
import os
import socket
import threading
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

import pytest

from ableton_live12_mcp.client import (
    DEFAULT_PORT,
    Live12Client,
    Live12ClientError,
    Live12ConnectionError,
    Live12TimeoutError,
)
from ableton_live12_mcp.server import McpServer
from live12_bridge.handlers import BridgeHandlers
from live12_bridge.reflection import lom_inspect


# ==============================================================================
# Strict Live 12 LOM Stubs (enforcing real C++/Python Boost LOM invariants)
# ==============================================================================

class StrictMidiNote:
    """Models Live 12 MidiNote where note_id is read-only and slots are fixed."""

    __slots__ = (
        "_note_id",
        "pitch",
        "start_time",
        "duration",
        "velocity",
        "mute",
        "probability",
        "velocity_deviation",
        "release_velocity",
    )

    def __init__(
        self,
        note_id: int,
        pitch: int,
        start_time: float,
        duration: float,
        velocity: float = 100.0,
        mute: bool = False,
        probability: float = 1.0,
        velocity_deviation: float = 0.0,
        release_velocity: float = 64.0,
    ):
        self._note_id = int(note_id)
        self.pitch = int(pitch)
        self.start_time = float(start_time)
        self.duration = float(duration)
        self.velocity = float(velocity)
        self.mute = bool(mute)
        self.probability = float(probability)
        self.velocity_deviation = float(velocity_deviation)
        self.release_velocity = float(release_velocity)

    @property
    def note_id(self) -> int:
        return self._note_id


class StrictMidiClip:
    """
    Models Live 12 Live.Clip.Clip for MIDI clips:
    - Exposes .looping (NO .loop, NO .notes attributes!)
    - Only supports Live 12 extended MIDI note APIs (add_new_notes, get_notes_extended,
      apply_note_modifications, remove_notes_by_id).
    """

    __slots__ = (
        "name",
        "length",
        "looping",
        "loop_start",
        "loop_end",
        "start_marker",
        "is_midi_clip",
        "is_audio_clip",
        "has_envelopes",
        "_notes",
        "_next_note_id",
        "_envelopes",
        "applied_modifications",
        "view",
    )

    def __init__(self, length: float = 4.0):
        self.name = "StrictMidiClip"
        self.length = float(length)
        self.looping = False
        self.loop_start = 0.0
        self.loop_end = float(length)
        self.start_marker = 0.0
        self.is_midi_clip = True
        self.is_audio_clip = False
        self.has_envelopes = False
        self._notes: List[StrictMidiNote] = []
        self._next_note_id = 1
        self._envelopes: Dict[int, "StrictClipEnvelope"] = {}
        self.applied_modifications: List[tuple] = []
        self.view = SimpleNamespace(
            show_envelope=lambda: None,
            select_envelope_parameter=lambda p: None,
        )

    def add_new_notes(self, note_specs: tuple) -> None:
        for spec in note_specs:
            if isinstance(spec, dict):
                pitch = spec["pitch"]
                start_time = spec["start_time"]
                duration = spec["duration"]
                velocity = spec.get("velocity", 100.0)
                mute = spec.get("mute", False)
                probability = spec.get("probability", 1.0)
                velocity_deviation = spec.get("velocity_deviation", 0.0)
                release_velocity = spec.get("release_velocity", 64.0)
            else:
                pitch = spec.pitch
                start_time = spec.start_time
                duration = spec.duration
                velocity = getattr(spec, "velocity", 100.0)
                mute = getattr(spec, "mute", False)
                probability = getattr(spec, "probability", 1.0)
                velocity_deviation = getattr(spec, "velocity_deviation", 0.0)
                release_velocity = getattr(spec, "release_velocity", 64.0)
            self._notes.append(
                StrictMidiNote(
                    note_id=self._next_note_id,
                    pitch=pitch,
                    start_time=start_time,
                    duration=duration,
                    velocity=velocity,
                    mute=mute,
                    probability=probability,
                    velocity_deviation=velocity_deviation,
                    release_velocity=release_velocity,
                )
            )
            self._next_note_id += 1

    def get_notes_extended(
        self, from_pitch: int, pitch_span: int, from_time: float, time_span: float
    ) -> tuple:
        end_pitch = from_pitch + pitch_span
        end_time = from_time + time_span
        return tuple(
            n
            for n in self._notes
            if from_pitch <= n.pitch < end_pitch
            and from_time <= n.start_time < end_time
        )

    def apply_note_modifications(self, notes: tuple) -> None:
        for n in notes:
            if not isinstance(n, StrictMidiNote):
                raise TypeError(f"Expected StrictMidiNote, got {type(n).__name__}")
        self.applied_modifications.append(notes)

    def remove_notes_by_id(self, note_ids: tuple) -> None:
        id_set = set(note_ids)
        self._notes = [n for n in self._notes if n.note_id not in id_set]

    def automation_envelope(self, param: Any) -> Optional["StrictClipEnvelope"]:
        return self._envelopes.get(id(param))

    def create_automation_envelope(self, param: Any) -> "StrictClipEnvelope":
        env = StrictClipEnvelope()
        self._envelopes[id(param)] = env
        self.has_envelopes = True
        return env

    def clear_envelope(self, param: Any) -> None:
        self._envelopes.pop(id(param), None)

    def clear_all_envelopes(self) -> None:
        self._envelopes.clear()
        self.has_envelopes = False


class StrictAudioClip:
    """
    Models Live 12 Audio Clip LOM strict type constraints:
    - warp_mode accepts strictly int (WarpMode enum), rejects str
    - pitch_coarse accepts strictly int, rejects float
    - add_warp_marker accepts a single dict {"beat_time": ..., "sample_time": ...}
    """

    __slots__ = (
        "name",
        "length",
        "looping",
        "loop_start",
        "loop_end",
        "start_marker",
        "is_midi_clip",
        "is_audio_clip",
        "warping",
        "_warp_mode",
        "_pitch_coarse",
        "gain",
        "warp_markers",
    )

    def __init__(self, length: float = 8.0):
        self.name = "StrictAudioClip"
        self.length = float(length)
        self.looping = False
        self.loop_start = 0.0
        self.loop_end = float(length)
        self.start_marker = 0.0
        self.is_midi_clip = False
        self.is_audio_clip = True
        self.warping = False
        self._warp_mode = 0
        self._pitch_coarse = 0
        self.gain = 1.0
        self.warp_markers: List[Dict[str, float]] = []

    @property
    def warp_mode(self) -> int:
        return self._warp_mode

    @warp_mode.setter
    def warp_mode(self, val: int) -> None:
        if isinstance(val, bool) or not isinstance(val, int):
            raise TypeError(f"Live.Clip.warp_mode requires int enum, got {type(val).__name__}: {val!r}")
        if not 0 <= val <= 6:
            raise ValueError(f"warp_mode {val} out of enum range [0, 6]")
        self._warp_mode = val

    @property
    def pitch_coarse(self) -> int:
        return self._pitch_coarse

    @pitch_coarse.setter
    def pitch_coarse(self, val: int) -> None:
        if isinstance(val, bool) or not isinstance(val, int):
            raise TypeError(f"Live.Clip.pitch_coarse requires int, got {type(val).__name__}: {val!r}")
        if not -48 <= val <= 48:
            raise ValueError(f"pitch_coarse {val} out of range [-48, 48]")
        self._pitch_coarse = val

    def add_warp_marker(self, marker: Dict[str, float]) -> None:
        if not isinstance(marker, dict):
            raise TypeError(f"add_warp_marker expects dict, got {type(marker).__name__}")
        if "beat_time" not in marker or "sample_time" not in marker:
            raise ValueError("add_warp_marker dict must contain 'beat_time' and 'sample_time'")
        self.warp_markers.append({
            "beat_time": float(marker["beat_time"]),
            "sample_time": float(marker["sample_time"]),
        })


class StrictClipEnvelope:
    __slots__ = ("steps",)

    def __init__(self):
        self.steps: List[tuple] = []

    def insert_step(self, time: float, length: float, value: float) -> None:
        self.steps.append((float(time), float(length), float(value)))


class StrictDeviceParameter:
    __slots__ = ("name", "value", "min", "max", "is_quantized")

    def __init__(
        self,
        name: str,
        value: float = 0.0,
        min_val: float = 0.0,
        max_val: float = 1.0,
        is_quantized: bool = False,
    ):
        self.name = name
        self.value = float(value)
        self.min = float(min_val)
        self.max = float(max_val)
        self.is_quantized = is_quantized


class StrictRoutingOption:
    __slots__ = ("display_name",)

    def __init__(self, display_name: str):
        self.display_name = display_name


class StrictClipSlot:
    __slots__ = ("clip",)

    def __init__(self, clip: Any = None):
        self.clip = clip


class StrictMixerDevice:
    __slots__ = ("volume", "panning", "sends", "crossfade_assign")

    def __init__(self):
        self.volume = StrictDeviceParameter("Track Volume", 0.85, 0.0, 1.0)
        self.panning = StrictDeviceParameter("Track Panning", 0.0, -1.0, 1.0)
        self.sends = [StrictDeviceParameter("Send A", 0.0, 0.0, 1.0)]
        self.crossfade_assign = 1


class StrictRackDevice:
    __slots__ = ("name", "can_have_chains", "parameters", "macros_mapped", "variation_count")

    def __init__(self, name: str = "Audio Effect Rack"):
        self.name = name
        self.can_have_chains = True
        self.parameters = [
            StrictDeviceParameter("Device On", 1.0, 0.0, 1.0, True),
            StrictDeviceParameter("Cutoff", 0.0, 0.0, 127.0),  # Macro 1 renamed to "Cutoff"
            StrictDeviceParameter("Macro 2", 0.0, 0.0, 127.0),
            StrictDeviceParameter("Macro 3", 0.0, 0.0, 127.0),
        ]
        self.macros_mapped = [True, True, False]
        self.variation_count = 0


class StrictDevice:
    __slots__ = ("name", "can_have_chains", "parameters")

    def __init__(self, name: str, params: List[StrictDeviceParameter]):
        self.name = name
        self.can_have_chains = False
        self.parameters = params


class StrictTrack:
    __slots__ = (
        "name",
        "clip_slots",
        "devices",
        "mixer_device",
        "available_input_routing_types",
        "available_input_routing_channels",
        "available_output_routing_types",
        "available_output_routing_channels",
        "input_routing_type",
        "input_routing_channel",
        "output_routing_type",
        "output_routing_channel",
        "current_monitoring_state",
        "mute",
        "solo",
        "arm",
    )

    def __init__(self, name: str = "Track 1", clips: Optional[List[Any]] = None, devices: Optional[List[Any]] = None):
        self.name = name
        self.clip_slots = [StrictClipSlot(c) for c in (clips if clips is not None else [None])]
        self.devices = list(devices) if devices is not None else []
        self.mixer_device = StrictMixerDevice()
        self.available_input_routing_types = [
            StrictRoutingOption("All Ins"),
            StrictRoutingOption("Ext. In"),
        ]
        self.available_input_routing_channels = [
            StrictRoutingOption("All Channels"),
            StrictRoutingOption("1/2"),
        ]
        self.available_output_routing_types = [
            StrictRoutingOption("Master"),
            StrictRoutingOption("Sends Only"),
        ]
        self.available_output_routing_channels = [
            StrictRoutingOption("Master"),
            StrictRoutingOption("1/2"),
        ]
        self.input_routing_type = self.available_input_routing_types[0]
        self.input_routing_channel = self.available_input_routing_channels[0]
        self.output_routing_type = self.available_output_routing_types[0]
        self.output_routing_channel = self.available_output_routing_channels[0]
        self.current_monitoring_state = 1
        self.mute = False
        self.solo = False
        self.arm = False


class StrictSong:
    __slots__ = ("tracks", "return_tracks", "master_track", "tempo")

    def __init__(self, tracks: Optional[List[StrictTrack]] = None):
        self.tracks = list(tracks) if tracks is not None else []
        self.return_tracks = [StrictTrack("A-Reverb")]
        self.master_track = StrictTrack("Master")
        self.tempo = 120.0


def _make_handlers(tracks: List[StrictTrack]) -> tuple[BridgeHandlers, StrictSong]:
    song = StrictSong(tracks=tracks)
    cs = SimpleNamespace(song=lambda: song, application=lambda: None)
    return BridgeHandlers(cs), song


# ==============================================================================
# 1. Clip.looping (no .loop / .notes attributes)
# ==============================================================================

def test_clip_uses_looping_and_extended_notes_without_loop_or_notes_attrs():
    clip = StrictMidiClip()
    assert not hasattr(clip, "loop")
    assert not hasattr(clip, "notes")

    handlers, _ = _make_handlers([StrictTrack(clips=[clip])])

    res_props = handlers.live12_clip_set_properties(
        track_index=0, slot_index=0, loop=True, loop_start=0.5, loop_end=3.5
    )
    assert clip.looping is True
    assert res_props["looping"] is True
    assert res_props["loop"] is True
    assert clip.loop_start == 0.5
    assert clip.loop_end == 3.5

    res_add = handlers.live12_clip_add_notes(
        track_index=0,
        slot_index=0,
        notes=[{"pitch": 60, "start_time": 0.0, "duration": 0.5, "velocity": 100}],
    )
    assert res_add["added_count"] == 1

    res_get = handlers.live12_clip_get_notes(track_index=0, slot_index=0)
    assert res_get["notes_count"] == 1
    assert len(res_get["notes"]) == 1
    assert res_get["notes"][0]["pitch"] == 60


# ==============================================================================
# 2. MidiNote with read-only note_id
# ==============================================================================

def test_midi_note_modify_skips_readonly_note_id():
    clip = StrictMidiClip()
    clip.add_new_notes(({"pitch": 60, "start_time": 0.0, "duration": 0.5, "velocity": 90},))
    note_id = clip.get_notes_extended(0, 128, 0.0, 100.0)[0].note_id

    # Verify the stub actually forbids writing note_id
    with pytest.raises(AttributeError):
        clip.get_notes_extended(0, 128, 0.0, 100.0)[0].note_id = 999  # type: ignore[misc]

    handlers, _ = _make_handlers([StrictTrack(clips=[clip])])
    res = handlers.live12_clip_modify_notes(
        track_index=0,
        slot_index=0,
        note_modifications=[{"note_id": note_id, "pitch": 64, "velocity": 115}],
    )
    assert res["modified_count"] == 1
    updated = clip.get_notes_extended(0, 128, 0.0, 100.0)[0]
    assert updated.pitch == 64
    assert updated.velocity == 115
    assert len(clip.applied_modifications) == 1

    # Also verify new_pitch placed BEFORE matcher pitch in dict is never overwritten by matcher pitch
    res2 = handlers.live12_clip_modify_notes(
        track_index=0,
        slot_index=0,
        note_modifications=[{"new_pitch": 67, "pitch": 64, "start_time": 0.0, "velocity": 120}],
    )
    assert res2["modified_count"] == 1
    updated2 = clip.get_notes_extended(0, 128, 0.0, 100.0)[0]
    assert updated2.pitch == 67
    assert updated2.velocity == 120


# ==============================================================================
# 3. Audio clip warp_mode int-only, pitch_coarse int-only, add_warp_marker dict,
#    and rejection on MIDI clips
# ==============================================================================

def test_audio_clip_warp_uses_int_enums_dict_marker_and_rejects_midi_clip():
    audio_clip = StrictAudioClip()
    midi_clip = StrictMidiClip()
    handlers, _ = _make_handlers([
        StrictTrack("Audio 1", clips=[audio_clip]),
        StrictTrack("MIDI 1", clips=[midi_clip]),
    ])

    res_warp = handlers.live12_audio_clip_set_warp(
        track_index=0,
        slot_index=0,
        warping=True,
        warp_mode="complex",
        pitch_shift=5.0,
        gain=0.75,
    )
    assert audio_clip.warping is True
    assert audio_clip.warp_mode == 4 and isinstance(audio_clip.warp_mode, int)
    assert audio_clip.pitch_coarse == 5 and isinstance(audio_clip.pitch_coarse, int)
    assert res_warp["warp_mode"] == "complex"

    res_marker = handlers.live12_audio_clip_add_warp_marker(
        track_index=0, slot_index=0, beat_time=4.0, sample_time=2.0
    )
    assert res_marker["beat_time"] == 4.0
    assert audio_clip.warp_markers == [{"beat_time": 4.0, "sample_time": 2.0}]

    # MIDI clip must be rejected rather than silently returning fake warp success
    with pytest.raises(ValueError, match="audio clip"):
        handlers.live12_audio_clip_set_warp(track_index=1, slot_index=0, warping=True)

    with pytest.raises(ValueError, match="audio clip"):
        handlers.live12_audio_clip_add_warp_marker(
            track_index=1, slot_index=0, beat_time=1.0, sample_time=0.5
        )


# ==============================================================================
# 4. Rack macros: parameters[0] is Device On, renamed Macro 1 -> "Cutoff",
#    macro_index=1 targets parameters[2]
# ==============================================================================

def test_rack_macro_control_indexes_by_position_after_device_on_despite_renaming():
    rack = StrictRackDevice()
    handlers, _ = _make_handlers([StrictTrack("Synth", devices=[rack])])

    res = handlers.live12_rack_macro_control(
        track_index=0, device_index=0, macro_index=1, value=0.5
    )
    assert res["macro_index"] == 1
    assert rack.parameters[0].value == 1.0  # Device On untouched
    assert rack.parameters[1].value == 0.0  # Renamed macro 0 ("Cutoff") untouched
    assert rack.parameters[2].value == pytest.approx(63.5)

    handlers.live12_rack_macro_control(
        track_index=0, device_index=0, macro_index=0, value=1.0
    )
    assert rack.parameters[1].value == pytest.approx(127.0)


# ==============================================================================
# 5. mixer_set: volume=0.0 vs volume_db=0.0, crossfader assignment
# ==============================================================================

def test_mixer_set_normalized_volume_vs_volume_db_and_crossfader():
    tr = StrictTrack("Mix Track")
    handlers, _ = _make_handlers([tr])

    # Normalized 0.0 means silence (-inf dB), NOT 0 dB unity
    res_silent = handlers.live12_mixer_set(track_index=0, volume=0.0)
    assert tr.mixer_device.volume.value == pytest.approx(0.0)
    assert res_silent["volume"] == pytest.approx(0.0)

    # Explicit volume_db=0.0 maps to ~0.85 unity fader position
    res_unity = handlers.live12_mixer_set(track_index=0, volume_db=0.0)
    assert tr.mixer_device.volume.value == pytest.approx(0.85, abs=0.02)
    assert res_unity["volume_db"] == pytest.approx(0.0)

    res_xf = handlers.live12_mixer_set(track_index=0, crossfader="A")
    assert tr.mixer_device.crossfade_assign == 0
    assert res_xf["crossfader"] == "A"


# ==============================================================================
# 6. clip_envelope_control: literal value=0.0 on [-15, 15] vs normalized=True
# ==============================================================================

def test_clip_envelope_control_literal_vs_normalized_on_bipolar_param():
    clip = StrictMidiClip()
    detune = StrictDeviceParameter("Detune", 0.0, -15.0, 15.0)
    dev = StrictDevice("Wavetable", [StrictDeviceParameter("Device On", 1.0, 0.0, 1.0, True), detune])
    handlers, _ = _make_handlers([StrictTrack("Bass", clips=[clip], devices=[dev])])

    res_literal = handlers.live12_clip_envelope_control(
        track_index=0,
        slot_index=0,
        action="set_step",
        device_index=0,
        parameter_identifier="Detune",
        time=0.0,
        length=0.5,
        value=0.0,
        normalized=False,
    )
    assert res_literal["actual_value"] == pytest.approx(0.0)

    res_norm = handlers.live12_clip_envelope_control(
        track_index=0,
        slot_index=0,
        action="set_step",
        device_index=0,
        parameter_identifier="Detune",
        time=1.0,
        length=0.5,
        value=0.0,
        normalized=True,
    )
    assert res_norm["actual_value"] == pytest.approx(-15.0)

    env = clip.automation_envelope(detune)
    assert env is not None
    assert env.steps == [(0.0, 0.5, 0.0), (1.0, 0.5, -15.0)]


# ==============================================================================
# 7. routing_set assigns real LOM routing option objects on track
# ==============================================================================

def test_routing_set_mutates_real_track_routing_objects():
    tr = StrictTrack("Audio In")
    handlers, _ = _make_handlers([tr])

    res = handlers.live12_routing_set(
        track_index=0,
        input_type="Ext. In",
        input_channel="1/2",
        output_type="Sends Only",
        output_channel="1/2",
        monitoring="in",
    )
    assert tr.input_routing_type.display_name == "Ext. In"
    assert tr.input_routing_channel.display_name == "1/2"
    assert tr.output_routing_type.display_name == "Sends Only"
    assert tr.output_routing_channel.display_name == "1/2"
    assert tr.current_monitoring_state == 0
    assert res["input_type"] == "Ext. In"
    assert res["output_type"] == "Sends Only"

    with pytest.raises(ValueError, match="input_type"):
        handlers.live12_routing_set(track_index=0, input_type="Nonexistent Input Bus")


# ==============================================================================
# 8. device_index=0 on empty track raises IndexError instead of fabricating data
# ==============================================================================

def test_device_index_zero_on_empty_track_raises_index_error():
    handlers, _ = _make_handlers([StrictTrack("Empty Track", devices=[])])

    with pytest.raises(IndexError):
        handlers.live12_device_get_parameters(track_index=0, device_index=0)

    with pytest.raises(IndexError):
        handlers.live12_device_set_parameter(
            track_index=0, device_index=0, parameter_identifier="Device On", value=1.0
        )

    with pytest.raises(IndexError):
        handlers.live12_device_toggle(track_index=0, device_index=0, enabled=True)

    with pytest.raises(IndexError):
        handlers.live12_rack_macro_control(
            track_index=0, device_index=0, macro_index=0, value=0.5
        )


# ==============================================================================
# 9. McpServer(mode="auto") returns isError=True when offline (no silent mock)
# ==============================================================================

def test_mcp_server_auto_mode_returns_error_when_offline_and_recovers_on_start(
    monkeypatch, tmp_path
):
    monkeypatch.delenv("ABLETON_TEST_MODE", raising=False)
    monkeypatch.delenv("ABLETON_BRIDGE_HOST", raising=False)
    monkeypatch.delenv("ABLETON_BRIDGE_PORT", raising=False)

    disc_path = tmp_path / "ableton_live12_bridge.json"
    # Point at an unused local port where nothing is listening
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        unused_port = probe.getsockname()[1]

    disc_path.write_text(
        json.dumps({"host": "127.0.0.1", "port": unused_port, "pid": os.getpid()}),
        encoding="utf-8",
    )

    server = McpServer(mode="auto", discovery_path=str(disc_path))
    assert server.mode == "live"
    assert server._mock_bridge is None

    res_offline = server.execute_tool("live12_song_get_state", {})
    assert res_offline.is_error is True
    assert "Is Ableton Live 12 running with Live12Bridge enabled?" in res_offline.content[0]["text"]
    assert server._mock_bridge is None

    # Now launch a real TCP JSON-RPC server and update discovery file
    def _serve_once(srv_sock: socket.socket) -> None:
        conn, _ = srv_sock.accept()
        with conn:
            line = conn.recv(4096).split(b"\n", 1)[0]
            req = json.loads(line.decode("utf-8"))
            resp = {"jsonrpc": "2.0", "id": req["id"], "result": {"tempo": 128.0}}
            conn.sendall((json.dumps(resp) + "\n").encode("utf-8"))

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.bind(("127.0.0.1", 0))
        srv.listen(2)
        live_port = srv.getsockname()[1]
        disc_path.write_text(
            json.dumps({"host": "127.0.0.1", "port": live_port, "pid": os.getpid()}),
            encoding="utf-8",
        )
        t = threading.Thread(target=_serve_once, args=(srv,), daemon=True)
        t.start()

        res_online = server.execute_tool("live12_song_get_state", {})
        t.join(timeout=2.0)

    assert res_online.is_error is False
    assert res_online.raw["tempo"] == 128.0


# ==============================================================================
# 10. lom_inspect skips deprecated Live 12 properties
# ==============================================================================

def test_lom_inspect_skips_deprecated_live12_properties():
    class Live12TrackWithDeprecatedProperties:
        name = "Acid Bass"
        mute = False

        @property
        def current_input_routing(self):
            raise RuntimeError("current_input_routing is removed/deprecated in Live 12")

        @property
        def current_output_routing(self):
            raise RuntimeError("current_output_routing is removed/deprecated in Live 12")

        @property
        def input_routings(self):
            raise RuntimeError("input_routings is removed/deprecated in Live 12")

        def get_notes(self, *args):
            raise RuntimeError("get_notes is deprecated in Live 12")

        def stop_all_clips(self):
            pass

    tr = Live12TrackWithDeprecatedProperties()
    song = SimpleNamespace(tracks=[tr])
    live_app = SimpleNamespace(song=song)

    inspected = lom_inspect(
        lambda r: live_app if r == "application" else song,
        "live_app/song/tracks/0",
    )
    assert "name" in inspected["properties"]
    assert "mute" in inspected["properties"]
    assert "stop_all_clips" in inspected["methods"]
    for deprecated in ("current_input_routing", "current_output_routing", "input_routings", "get_notes"):
        assert deprecated not in inspected["properties"]
        assert deprecated not in inspected["methods"]


# ==============================================================================
# 11. Live12Client default timeout, socket cleanup, dead-PID ignore, dynamic
#     discovery reload, first-frame parsing, and id mismatch rejection
# ==============================================================================

def test_live12_client_timeout_socket_cleanup_and_discovery_reload(monkeypatch, tmp_path):
    monkeypatch.delenv("ABLETON_BRIDGE_HOST", raising=False)
    monkeypatch.delenv("ABLETON_BRIDGE_PORT", raising=False)

    disc_path = tmp_path / "discovery.json"
    # Dead PID discovery entry must be ignored in favor of default port
    disc_path.write_text(
        json.dumps({"host": "127.0.0.1", "port": 19998, "pid": 999999999}),
        encoding="utf-8",
    )
    client = Live12Client(discovery_path=str(disc_path))
    assert client.timeout == 25.0
    assert client.port == DEFAULT_PORT

    # Start server A, close it (ConnectionRefusedError), update discovery to server B -> retry succeeds
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as dead_srv:
        dead_srv.bind(("127.0.0.1", 0))
        port_a = dead_srv.getsockname()[1]

    disc_path.write_text(
        json.dumps({"host": "127.0.0.1", "port": port_a, "pid": os.getpid()}),
        encoding="utf-8",
    )

    # Pre-refresh client to port_a, then overwrite discovery file right before dialing
    client._refresh_endpoint()
    assert client.port == port_a

    def _serve_multi_frame(srv_sock: socket.socket) -> None:
        conn, _ = srv_sock.accept()
        with conn:
            line = conn.recv(4096).split(b"\n", 1)[0]
            req = json.loads(line.decode("utf-8"))
            first = json.dumps({"jsonrpc": "2.0", "id": req["id"], "result": {"ok": True}})
            trailing = json.dumps({"jsonrpc": "2.0", "id": 999, "result": {"stale": True}})
            conn.sendall((first + "\n" + trailing + "\n").encode("utf-8"))

    created_sockets: List[socket.socket] = []
    real_socket = socket.socket

    def tracked_socket(*args, **kwargs):
        s = real_socket(*args, **kwargs)
        created_sockets.append(s)
        return s

    monkeypatch.setattr(socket, "socket", tracked_socket)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv_b:
        srv_b.bind(("127.0.0.1", 0))
        srv_b.listen(2)
        port_b = srv_b.getsockname()[1]

        # Simulate Ableton restarting onto port_b after MCP cached port_a
        real_refresh = client._refresh_endpoint
        refresh_calls = {"n": 0}

        def refresh_on_retry():
            refresh_calls["n"] += 1
            if refresh_calls["n"] >= 2:
                disc_path.write_text(
                    json.dumps({"host": "127.0.0.1", "port": port_b, "pid": os.getpid()}),
                    encoding="utf-8",
                )
            return real_refresh()

        monkeypatch.setattr(client, "_refresh_endpoint", refresh_on_retry)
        t = threading.Thread(target=_serve_multi_frame, args=(srv_b,), daemon=True)
        t.start()
        result = client.call("live12_song_get_state")
        t.join(timeout=2.0)

    assert result == {"ok": True}
    # All client sockets created (refused port_a + successful port_b) must be closed (no FD leak)
    assert len(created_sockets) >= 2
    assert all(s.fileno() == -1 for s in created_sockets)


def test_live12_client_rejects_mismatched_id_and_closes_socket_on_timeout(monkeypatch, tmp_path):
    monkeypatch.delenv("ABLETON_BRIDGE_HOST", raising=False)
    monkeypatch.delenv("ABLETON_BRIDGE_PORT", raising=False)

    created_sockets: List[socket.socket] = []
    real_socket = socket.socket

    def tracked_socket(*args, **kwargs):
        s = real_socket(*args, **kwargs)
        created_sockets.append(s)
        return s

    monkeypatch.setattr(socket, "socket", tracked_socket)

    def _serve_bad_id(srv_sock: socket.socket) -> None:
        conn, _ = srv_sock.accept()
        with conn:
            conn.recv(4096)
            conn.sendall(b'{"jsonrpc": "2.0", "id": 99999, "result": {"ok": false}}\n')

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.bind(("127.0.0.1", 0))
        srv.listen(2)
        port = srv.getsockname()[1]
        client = Live12Client(host="127.0.0.1", port=port, timeout=1.0, discovery_path=str(tmp_path / "none.json"))
        t = threading.Thread(target=_serve_bad_id, args=(srv,), daemon=True)
        t.start()
        with pytest.raises(Live12ClientError, match="Mismatched JSON-RPC response id"):
            client.call("live12_song_get_state")
        t.join(timeout=2.0)

    # Also verify timeout closes socket cleanly
    stall_done = threading.Event()

    def _serve_stall(srv_sock: socket.socket) -> None:
        conn, _ = srv_sock.accept()
        with conn:
            conn.recv(4096)
            stall_done.wait(timeout=2.0)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv_t:
        srv_t.bind(("127.0.0.1", 0))
        srv_t.listen(2)
        t_port = srv_t.getsockname()[1]
        client_t = Live12Client(host="127.0.0.1", port=t_port, timeout=0.05, discovery_path=str(tmp_path / "none.json"))
        t2 = threading.Thread(target=_serve_stall, args=(srv_t,), daemon=True)
        t2.start()
        try:
            with pytest.raises(Live12TimeoutError):
                client_t.call("live12_song_get_state")
        finally:
            stall_done.set()
            t2.join(timeout=2.0)

    assert len(created_sockets) >= 2
    assert all(s.fileno() == -1 for s in created_sockets)
