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
    assert res_warp["warp_mode"] == "Complex"

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

    import ableton_live12_mcp.client as client_mod
    monkeypatch.setattr(client_mod, "DEFAULT_PORT", unused_port)

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


# =============================================================================
# R2 Hardening & Real Live 12 LOM Contract Regressions
# =============================================================================

import time
from live12_bridge.bridge import BridgeJob, Live12ControlSurface
from live12_bridge.handlers import dispatch_tool_call
from live12_bridge.reflection import (
    DEPRECATED_LOM_ATTRS,
    lom_call,
    lom_inspect,
    lom_set,
    resolve_path,
    serialize_lom_value,
)


class _StrictContinuousParam:
    """Real Live 12 DeviceParameter: value_items raises RuntimeError if is_quantized=False."""

    def __init__(
        self,
        name: str,
        value: float = 0.0,
        min_v: float = 0.0,
        max_v: float = 1.0,
        is_quantized: bool = False,
        value_items: tuple = (),
    ):
        self.name = name
        self._value = float(value)
        self.min = float(min_v)
        self.max = float(max_v)
        self.is_quantized = bool(is_quantized)
        self._value_items = tuple(value_items)

    @property
    def value(self) -> float:
        return self._value

    @value.setter
    def value(self, val: float) -> None:
        if isinstance(val, bool) or not isinstance(val, (int, float)):
            raise TypeError(f"Boost.Python DeviceParameter.value requires float, got {type(val)}")
        f = float(val)
        if not (self.min <= f <= self.max):
            raise ValueError(f"Value {f} out of [{self.min}, {self.max}]")
        self._value = f

    @property
    def value_items(self):
        if not self.is_quantized:
            raise RuntimeError("Only quantized parameters have value_items")
        return self._value_items

    def str_for_value(self, val: float) -> str:
        if self.is_quantized and self._value_items:
            idx = int(round(val - self.min))
            if 0 <= idx < len(self._value_items):
                return str(self._value_items[idx])
        return f"{val:.3f}"


def _make_r2_handlers(tracks=None, return_tracks=None, master_track=None, app=None, song_obj=None):
    import types

    if song_obj is None:
        song_obj = types.SimpleNamespace(
            tracks=list(tracks or []),
            return_tracks=list(return_tracks or []),
            master_track=master_track,
            scenes=[],
            cue_points=[],
            is_playing=False,
            current_song_time=0.0,
            nudge_up=False,
            nudge_down=False,
            tempo=125.0,
            _live_ptr=id(tracks) or 1,
        )

    class _CS:
        def song(self):
            return song_obj

        def application(self):
            return app

    return BridgeHandlers(_CS()), song_obj


# --- 1. bridge.py lifecycle, job races, queue bounds, socket half-close, discovery ---


def test_bridge_job_atomic_state_transitions():
    job = BridgeJob("id-1", "live12_song_get_state", {})
    assert job.state == "pending"
    assert job.try_start() is True
    assert job.state == "running"
    # Once running, wait timeout cannot cancel it
    assert job.try_cancel() is False
    assert job.state == "running"
    job.mark_done()
    assert job.state == "done"
    assert job.try_start() is False

    job2 = BridgeJob("id-2", "live12_song_get_state", {})
    assert job2.try_cancel() is True
    assert job2.state == "cancelled"
    assert job2.try_start() is False


def test_bridge_queue_bounds_tick_budget_reentrancy_and_params_validation(monkeypatch, tmp_path):
    import json
    import queue as queue_mod
    import types
    import live12_bridge.bridge as bridge_mod

    disc = tmp_path / "disc.json"
    monkeypatch.setattr(bridge_mod, "DISCOVERY_PATH", str(disc))
    monkeypatch.setattr(bridge_mod, "DEFAULT_PORT", 0)

    class _FakeCInstance:
        def song(self):
            return types.SimpleNamespace(tracks=[], return_tracks=[], scenes=[], master_track=None)

        def application(self):
            return None

        def log_message(self, msg):
            pass

        def show_message(self, msg):
            pass

    cs = Live12ControlSurface(_FakeCInstance())
    try:
        # Invalid non-dict params rejected before queueing
        s_client, s_server = socket.socketpair()
        try:
            keep = cs._process_raw_frame(
                s_server,
                json.dumps({"id": 1, "method": "song_get_state", "params": [1, 2]}).encode("utf-8"),
            )
            assert keep is True
            s_client.settimeout(1.0)
            resp = json.loads(s_client.recv(4096).decode("utf-8").strip())
            assert resp["error"]["code"] == -32602
        finally:
            s_client.close()
            s_server.close()

        # Drain any active items, fill queue to maxsize=256, verify 257th gets -32001 Server busy
        while not cs._request_queue.empty():
            cs._request_queue.get_nowait()

        for i in range(bridge_mod.MAX_REQUEST_QUEUE_SIZE):
            cs._request_queue.put_nowait(BridgeJob(i, "live12_song_get_state", {}))

        s_client2, s_server2 = socket.socketpair()
        try:
            keep2 = cs._process_raw_frame(
                s_server2,
                json.dumps({"id": 999, "method": "song_get_state", "params": {}}).encode("utf-8"),
            )
            assert keep2 is True
            s_client2.settimeout(1.0)
            resp2 = json.loads(s_client2.recv(4096).decode("utf-8").strip())
            assert resp2["error"]["code"] == -32001
            assert "busy" in resp2["error"]["message"].lower()
        finally:
            s_client2.close()
            s_server2.close()

        # Re-entrancy guard: if _drain_lock is held, _drain_queue returns immediately without touching queue
        with cs._drain_lock:
            before_size = cs._request_queue.qsize()
            cs._drain_queue()
            assert cs._request_queue.qsize() == before_size

        # Wall-clock tick budget stops draining early when a dispatch exceeds MAX_DRAIN_SECONDS_PER_TICK
        while not cs._request_queue.empty():
            cs._request_queue.get_nowait()
        for i in range(5):
            cs._request_queue.put_nowait(BridgeJob(i, "slow_op", {}))

        import live12_bridge.handlers as handlers_mod

        def _slow_dispatch(handlers, method, params):
            time.sleep(0.02)
            return {"ok": True}

        monkeypatch.setattr(handlers_mod, "dispatch_tool_call", _slow_dispatch)
        cs._drain_queue()
        assert cs._request_queue.qsize() >= 1
    finally:
        cs.disconnect()


def test_bridge_is_socket_closed_allows_shut_wr_half_close_and_detects_rst():
    import struct

    # Half-closed client write side (SHUT_WR) is NOT dead for sending reply
    s_client, s_server = socket.socketpair()
    try:
        s_client.shutdown(socket.SHUT_WR)
        t0 = time.monotonic()
        assert Live12ControlSurface._is_socket_closed(s_server) is False
        assert (time.monotonic() - t0) < 0.25
        # Server can still send reply back across half-closed TCP/socketpair
        s_server.sendall(b'{"result":{"ok":true}}\n')
        assert s_client.recv(1024) == b'{"result":{"ok":true}}\n'
    finally:
        s_client.close()
        s_server.close()

    # RST / peer abort via TCP SO_LINGER(1, 0) IS detected as closed
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    port = srv.getsockname()[1]
    cli = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    cli.connect(("127.0.0.1", port))
    peer, _ = srv.accept()
    try:
        cli.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
        cli.close()
        time.sleep(0.03)
        assert Live12ControlSurface._is_socket_closed(peer) is True
    finally:
        peer.close()
        srv.close()


def test_bridge_discovery_unlink_pid_port_guard_and_disconnect_cleanup(monkeypatch, tmp_path):
    import json
    import types
    import live12_bridge.bridge as bridge_mod

    disc = tmp_path / "disc.json"
    monkeypatch.setattr(bridge_mod, "DISCOVERY_PATH", str(disc))
    monkeypatch.setattr(bridge_mod, "DEFAULT_PORT", 0)

    class _FakeCInstance:
        def song(self):
            return None

        def application(self):
            return None

        def log_message(self, msg):
            pass

        def show_message(self, msg):
            pass

    cs = Live12ControlSurface(_FakeCInstance())
    own_port = cs._port
    assert disc.exists()
    meta = json.loads(disc.read_text(encoding="utf-8"))
    assert meta["pid"] == os.getpid()
    assert meta["port"] == own_port

    # Overwrite discovery file with ANOTHER pid/port -> disconnect() MUST NOT unlink it
    foreign = {"host": "127.0.0.1", "port": own_port + 1, "pid": os.getpid() + 99999}
    disc.write_text(json.dumps(foreign), encoding="utf-8")

    pending_job = BridgeJob("j1", "song_get_state", {})
    cs._request_queue.put_nowait(pending_job)
    cs.disconnect()

    assert disc.exists()
    assert json.loads(disc.read_text(encoding="utf-8")) == foreign
    assert pending_job.done_event.is_set()
    assert pending_job.error["code"] == -32000
    assert "disconnected" in pending_job.error["message"].lower()

    # Matching pid AND port -> disconnect() DOES unlink
    cs2 = Live12ControlSurface(_FakeCInstance())
    assert disc.exists()
    cs2.disconnect()
    assert not disc.exists()

    # _setup_timer failure triggers cleanup via disconnect()
    def _boom_timer(self):
        raise RuntimeError("timer init failed")

    monkeypatch.setattr(Live12ControlSurface, "_setup_timer", _boom_timer)
    with pytest.raises(RuntimeError, match="timer init failed"):
        Live12ControlSurface(_FakeCInstance())
    assert not disc.exists()


# --- 2. reflection.py real-LOM fixes ---


def test_reflection_liveobj_invalid_bool_str_none_return_deprecated_and_structs():
    import types

    assert "get_selected_notes" in DEPRECATED_LOM_ATTRS

    # Invalid / deleted liveobj raises RuntimeError in lom_inspect
    deleted_obj = types.SimpleNamespace(_live_ptr=0, name="Deleted")
    with pytest.raises(RuntimeError, match="invalid or deleted"):
        lom_inspect(lambda k: deleted_obj, "song")

    class _Target:
        flag: bool = True
        count: int = 1

        def do_void(self) -> None:
            return None

        def add_new_notes(self, notes=()):
            self.received = notes
            return None

    target = _Target()
    root_fn = lambda k: target

    # Bool string coercion and rejecting bool for int attr
    res_f = lom_set(root_fn, "song", "flag", "false")
    assert target.flag is False and res_f["new_value"] is False
    res_t = lom_set(root_fn, "song", "flag", "on")
    assert target.flag is True and res_t["new_value"] is True
    with pytest.raises(ValueError):
        lom_set(root_fn, "song", "flag", "maybe")
    with pytest.raises(TypeError):
        lom_set(root_fn, "song", "count", True)

    # lom_call preserves None instead of turning into True, and accepts kwargs={"notes": [...]}
    call_res = lom_call(root_fn, "song", "do_void")
    assert call_res["result"] is None

    notes_res = lom_call(root_fn, "song", "add_new_notes", kwargs={"notes": [{"pitch": 60, "start_time": 0.0, "duration": 0.5}]})
    assert notes_res["result"] is None
    assert len(target.received) == 1
    assert target.received[0].pitch == 60

    # resolve_path does not coerce string dict keys into ints when string key exists
    d = {"0": "string_key_val", 0: "int_key_val"}
    assert resolve_path(lambda k: {"d": d}, "song.d.0") == "string_key_val"

    # serialize_lom_value handles WarpMarker, BeatTime, RoutingType, RoutingChannel
    class WarpMarker:
        def __init__(self, bt, st):
            self.beat_time = bt
            self.sample_time = st

    class BeatTime:
        def __init__(self):
            self.bars = 2
            self.beats = 3
            self.sub_division = 1
            self.ticks = 40

    class RoutingType:
        def __init__(self, name):
            self.display_name = name
            self.category = 1

    class RoutingChannel:
        def __init__(self, name):
            self.display_name = name
            self.layout = 2

    assert serialize_lom_value(WarpMarker(1.5, 44100.0)) == {"type": "WarpMarker", "beat_time": 1.5, "sample_time": 44100.0}
    assert serialize_lom_value(BeatTime()) == {"type": "BeatTime", "bars": 2, "beats": 3, "sub_division": 1, "ticks": 40}
    assert serialize_lom_value(RoutingType("Master"))["display_name"] == "Master"
    assert serialize_lom_value(RoutingChannel("1/2"))["display_name"] == "1/2"


# --- 3. handlers.py real-LOM fixes ---


def test_device_set_parameter_numeric_strings_quantized_guard_and_device_type_enum():
    import types

    class _DeviceTypeInt(int):
        pass

    freq = _StrictContinuousParam("Filter Freq", value=0.2, min_v=0.0, max_v=1.0, is_quantized=False)
    mode = _StrictContinuousParam("Filter Type", value=0.0, min_v=0.0, max_v=2.0, is_quantized=True, value_items=("LP", "HP", "BP"))
    dev = types.SimpleNamespace(name="Auto Filter", type=_DeviceTypeInt(2), is_active=True, can_have_chains=False, parameters=[freq, mode])
    tr = StrictTrack("Audio 1", devices=[dev])
    handlers, _ = _make_handlers([tr])

    # Enum int -> string device type
    dlist = handlers.live12_device_list(0)
    assert dlist["devices"][0]["type"] == "audio_effect"

    # Numeric strings ("+0.5", "1e-3") with normalized=True & non-finite rejection
    r1 = handlers.live12_device_set_parameter(0, 0, "Filter Freq", value="+0.5", normalized=True)
    assert r1["value"] == pytest.approx(0.5)
    r2 = handlers.live12_device_set_parameter(0, 0, "Filter Freq", value="1e-3", normalized=False)
    assert r2["value"] == pytest.approx(0.001)
    with pytest.raises(ValueError):
        handlers.live12_device_set_parameter(0, 0, "Filter Freq", value="NaN")
    # Non-numeric string on continuous param raises ValueError cleanly (never touches .value_items)
    with pytest.raises(ValueError, match="continuous"):
        handlers.live12_device_set_parameter(0, 0, "Filter Freq", value="Bogus")

    # Quantized string resolves via value_items
    r3 = handlers.live12_device_set_parameter(0, 0, "Filter Type", value="BP")
    assert r3["value"] == 2.0


def test_flagship_devices_lom_properties_reverse_match_guard_and_unmatched():
    import types

    a_param = _StrictContinuousParam("A", value=0.5, min_v=0.0, max_v=1.0)
    cutoff = _StrictContinuousParam("Filter Cutoff", value=0.2, min_v=0.0, max_v=1.0)
    quant = _StrictContinuousParam("Osc Shape", value=0.0, min_v=0.0, max_v=1.0, is_quantized=True, value_items=("Sine", "Saw"))

    meld_dev = types.SimpleNamespace(
        name="Meld",
        selected_engine=0,
        unison_voices=0,
        mono_poly=0,
        poly_voices=4,
        parameters=[a_param, cutoff, quant],
    )
    roar_dev = types.SimpleNamespace(
        name="Roar",
        routing_mode_list=("Single", "Serial", "Parallel", "Mid/Side"),
        routing_mode_index=0,
        env_listen=False,
        parameters=[cutoff],
    )
    drift_dev = types.SimpleNamespace(
        name="Drift",
        voice_mode_list=["Poly", "Mono", "Stereo", "Legato"],
        voice_mode_index=0,
        voice_count_list=["2", "4", "8"],
        voice_count_index=0,
        pitch_bend_range=2,
        parameters=[cutoff],
    )
    handlers, _ = _make_handlers([StrictTrack("T1", devices=[meld_dev, roar_dev, drift_dev])])

    # Meld LOM props + parameter + reverse substring protection ("banana" must NOT match param "A") + unmatched_params
    res_meld = handlers.live12_meld_control(
        0, 0, {"selected_engine": 1, "poly_voices": 8, "Osc Shape": "Saw", "banana": 0.9}
    )
    assert meld_dev.selected_engine == 1
    assert meld_dev.poly_voices == 8
    assert quant.value == 1.0
    assert a_param.value == pytest.approx(0.5)  # Untouched by "banana"
    assert res_meld["meld_params_updated"] == 3
    assert "banana" not in res_meld["parameters"]
    assert res_meld["unmatched_params"] == {"banana": 0.9}

    # Invalid value raises ValueError instead of silent pass
    with pytest.raises(ValueError):
        handlers.live12_meld_control(0, 0, {"Filter Cutoff": "invalid_str"})

    # Roar routing_mode label + env_listen bool
    res_roar = handlers.live12_roar_control(0, 1, {"routing_mode": "Parallel", "env_listen": "true"})
    assert roar_dev.routing_mode_index == 2
    assert roar_dev.env_listen is True
    assert res_roar["roar_stages_updated"] == 2

    # Drift voice_mode_index + voice_count + pitch_bend_range
    res_drift = handlers.live12_drift_control(0, 2, {"voice_mode": "Mono", "voice_count": "8", "pitch_bend_range": 12})
    assert drift_dev.voice_mode_index == 1
    assert drift_dev.voice_count_index == 2
    assert drift_dev.pitch_bend_range == 12
    assert res_drift["drift_voice_updated"] == 3


def test_simpler_control_and_slice_to_drum_rack(monkeypatch):
    import types
    import live12_bridge.handlers as handlers_mod

    class _Sample:
        def __init__(self):
            self.file_path = "/tmp/kick.wav"
            self.slices = [0.0, 1000.0, 2000.0]
            self.slicing_sensitivity = 0.5
            self.slicing_style = 0
            self.slicing_beat_division = 4

    simpler_dev = types.SimpleNamespace(
        name="Simpler",
        class_name="OriginalSimpler",
        playback_mode=0,
        sample=_Sample(),
        parameters=[],
    )
    comp_dev = types.SimpleNamespace(name="Compressor", class_name="Compressor2", parameters=[])
    handlers, song_obj = _make_r2_handlers(tracks=[StrictTrack("T1", devices=[simpler_dev, comp_dev])])

    # Non-simpler rejected
    with pytest.raises(ValueError, match="not a Simpler"):
        handlers.live12_simpler_control(0, 1, "get_state")

    # String/int playback modes including "one shot" and "1"
    for mode_arg, expected_int, expected_name in [
        ("one shot", 1, "1-Shot"),
        (2, 2, "Slicing"),
        ("0", 0, "Classic"),
    ]:
        out = handlers.live12_simpler_control(0, 0, "set_playback_mode", playback_mode=mode_arg)
        assert simpler_dev.playback_mode == expected_int
        assert out["playback_mode"] == expected_name

    # Sensitivity > 1.0 normalized via / 100.0; string slicing_style and beat_division mapped
    handlers.live12_simpler_control(
        0,
        0,
        "slice",
        params={"slicing_style": "beat", "beat_division": "1/16"},
        sensitivity=75.0,
    )
    assert simpler_dev.sample.slicing_sensitivity == pytest.approx(0.75)
    assert simpler_dev.sample.slicing_style == 1
    assert simpler_dev.sample.slicing_beat_division == 2

    with pytest.raises(ValueError):
        handlers.live12_simpler_control(0, 0, "slice", sensitivity=120.0)
    with pytest.raises(ValueError):
        handlers.live12_simpler_control(0, 0, "slice", sensitivity=-1.0)

    # Live.Conversions.sliced_simpler_to_drum_rack called when available
    conv_calls = []
    fake_live = types.SimpleNamespace(
        Conversions=types.SimpleNamespace(
            sliced_simpler_to_drum_rack=lambda s, d: conv_calls.append((s, d))
        )
    )
    monkeypatch.setattr(handlers_mod, "Live", fake_live)
    res_conv = handlers.live12_simpler_control(0, 0, "slice_to_drum_rack")
    assert res_conv["status"] == "success"
    assert conv_calls == [(song_obj, simpler_dev)]


def test_audio_clip_warp_db_gain_and_warp_marker_live_ctor(monkeypatch):
    import types
    import live12_bridge.handlers as handlers_mod

    audio_clip = StrictAudioClip()
    tr = StrictTrack("Audio", clips=[audio_clip])
    handlers, _ = _make_handlers([tr])

    # Negative dB gain & > 1.0 gain cleanly converted to [0.0, 1.0]
    res = handlers.live12_audio_clip_set_warp(0, 0, warp_mode="complex pro", gain=-6.0)
    assert res["warp_mode"] == "Complex Pro"
    assert 0.15 < audio_clip.gain < 0.25

    handlers.live12_audio_clip_set_warp(0, 0, gain=2.5)
    assert 0.0 <= audio_clip.gain <= 1.0

    # Live.Clip.WarpMarker used when Live module present
    class _FakeWarpMarker:
        def __init__(self, beat_time, sample_time):
            self.beat_time = beat_time
            self.sample_time = sample_time

    class _MarkerClip(StrictAudioClip):
        def add_warp_marker(self, marker):
            assert isinstance(marker, _FakeWarpMarker)
            self.warp_markers.append(marker)

    mclip = _MarkerClip()
    handlers2, _ = _make_handlers([StrictTrack("Audio", clips=[mclip])])
    fake_live = types.SimpleNamespace(Clip=types.SimpleNamespace(WarpMarker=_FakeWarpMarker))
    monkeypatch.setattr(handlers_mod, "Live", fake_live)
    handlers2.live12_audio_clip_add_warp_marker(0, 0, beat_time=4.0, sample_time=88200.0)
    assert len(mclip.warp_markers) == 1
    assert isinstance(mclip.warp_markers[0], _FakeWarpMarker)


def test_track_mixer_routing_drum_pad_and_cc_control_guards():
    import types

    # Group/non-armable track: can_be_armed=False, current_monitoring_state raises RuntimeError
    class _GroupTrack:
        can_be_armed = False

        def __init__(self, name: str, devices):
            self.name = name
            self.devices = list(devices)
            self.clip_slots = []
            self.mute = False
            self.solo = False
            self.color = 0
            self.color_index = 0
            self.has_midi_input = True
            self.has_audio_input = True
            self.has_audio_output = True
            self.mixer_device = StrictMixerDevice()
            self.available_input_routing_types = []
            self.available_output_routing_types = []
            self.input_routing_type = StrictRoutingOption("All Ins")
            self.output_routing_type = StrictRoutingOption("Master")
            self.available_input_routing_channels = []
            self.available_output_routing_channels = []
            self.input_routing_channel = StrictRoutingOption("1/2")
            self.output_routing_channel = StrictRoutingOption("1/2")

        @property
        def arm(self):
            raise RuntimeError("Cannot read arm on group track")

        @arm.setter
        def arm(self, _val):
            raise RuntimeError("Cannot arm group track")

        @property
        def current_monitoring_state(self):
            raise RuntimeError("Monitoring not supported on group track")

        @current_monitoring_state.setter
        def current_monitoring_state(self, _val):
            raise RuntimeError("Monitoring not supported on group track")

    class _MasterMixer:
        def __init__(self):
            self.volume = StrictDeviceParameter("Volume", 0.85, 0.0, 1.0)
            self.panning = StrictDeviceParameter("Pan", 0.0, -1.0, 1.0)
            self.sends = []

        @property
        def crossfade_assign(self):
            raise RuntimeError("Master track has no crossfade_assign")

        @crossfade_assign.setter
        def crossfade_assign(self, _v):
            raise RuntimeError("Master track has no crossfade_assign")

    # CC Control with 'Channel Pressure', 0-based 'Channel' (0..15), and CcControlDevice LOM props
    ch_pressure = _StrictContinuousParam("Channel Pressure", value=0.0, min_v=0.0, max_v=1.0)
    ch_param = _StrictContinuousParam("Channel", value=0.0, min_v=0.0, max_v=15.0)
    cf0 = _StrictContinuousParam("Custom Float 0", value=0.0, min_v=0.0, max_v=1.0)

    class _CcCtrl:
        name = "CC Control"
        custom_float_target_0 = 1
        custom_float_target_0_list = ["0", "1 (Mod Wheel)", "74 (Cutoff)"]
        parameters = [ch_pressure, ch_param, cf0]
        resent = 0

        def resend(self):
            self.resent += 1

    # Instrument Rack with can_have_drum_pads=False whose .drum_pads raises RuntimeError
    class _InstRack:
        name = "Instrument Rack"
        can_have_drum_pads = False

        @property
        def drum_pads(self):
            raise RuntimeError("Not a Drum Rack")

    grp = _GroupTrack("Group 1", devices=[_InstRack(), _CcCtrl()])
    master = types.SimpleNamespace(name="Master", mixer_device=_MasterMixer(), devices=[])
    handlers, _ = _make_r2_handlers(tracks=[grp], master_track=master)

    # Guarded arm on non-armable track succeeds without RuntimeError
    r_tr = handlers.live12_track_set_properties(0, arm=True, mute=True)
    assert r_tr["mute"] is True

    # Guarded monitoring state on group track
    r_rt = handlers.live12_routing_get(0)
    assert r_rt["monitoring"] == "N/A"
    with pytest.raises(ValueError, match="input monitoring"):
        handlers.live12_routing_set(0, monitoring="In")

    # Invalid send_index raises IndexError/ValueError, Master crossfader safely ignored
    with pytest.raises(IndexError):
        handlers.live12_mixer_set(0, send_index=3, send_value=0.5)
    with pytest.raises(ValueError):
        handlers.live12_mixer_set(0, send_index=True, send_value=0.5)
    with pytest.raises(ValueError, match="crossfade_assign"):
        handlers.live12_mixer_set(-100, track_type="master", crossfader="A")
    r_mix = handlers.live12_mixer_set(-100, track_type="master", volume=0.7)
    assert r_mix["volume"] == pytest.approx(0.7)

    # Drum pad checks can_have_drum_pads before touching .drum_pads
    with pytest.raises(ValueError, match="not a Drum Rack"):
        handlers.live12_drum_pad_control(0, 0, "inspect_pads")

    # CcControlDevice LOM target + strict Channel (p.min=0 -> ch-1) + Channel Pressure untouched + resend()
    cc_dev = grp.devices[1]
    res_cc = handlers.live12_cc_control(0, 1, "set_cc", cc_number=74, value=127, channel=5)
    assert ch_pressure.value == 0.0
    assert ch_param.value == 4.0  # channel 5 mapped cleanly to 0-indexed [0..15]
    assert cc_dev.custom_float_target_0 == 2
    assert cf0.value == pytest.approx(1.0)
    assert cc_dev.resent == 1
    assert res_cc["resent"] is True
    assert len(handlers.live12_cc_control(0, 1, "get_mappings")["custom_targets"]) == 1


def test_cue_delete_while_playing_nudge_reset_rack_variation_and_clip_ops():
    import types

    # 1. Cue delete while playing sets current_song_time and verifies snap
    cp = types.SimpleNamespace(name="Drop", time=32.0)

    class _PlayingSong:
        def __init__(self):
            self.is_playing = True
            self.current_song_time = 0.0
            self.cue_points = [cp]
            self.tracks = []
            self.return_tracks = []
            self.scenes = []
            self.nudge_up = False
            self.nudge_down = False
            self._live_ptr = 777

        def set_or_delete_cue(self):
            self.cue_points = [c for c in self.cue_points if abs(c.time - self.current_song_time) > 1e-3]

    psong = _PlayingSong()
    handlers_ps, _ = _make_r2_handlers(song_obj=psong)
    handlers_ps.live12_cue_point_control("delete", cue_index=0)
    assert psong.current_song_time == 32.0
    assert psong.cue_points == []

    # Nudge momentary reset (active omitted -> returns to False), explicit active=True stays True
    handlers_ps.live12_tempo_sync_control("nudge_up")
    assert psong.nudge_up is False
    handlers_ps.live12_tempo_sync_control("nudge_up", active=True)
    assert psong.nudge_up is True

    # 2. Rack variation recall + randomize return normalized float list [0.0..1.0]
    class _VarRack(StrictRackDevice):
        def __init__(self, name: str):
            super().__init__(name)
            self.variation_count = 1

        def recall_variation(self, _v_idx: int) -> None:
            self.parameters[1].value = 63.5

        def randomize_macros(self) -> None:
            self.parameters[1].value = 127.0

    rack = _VarRack("FX Rack")
    handlers, _ = _make_handlers([StrictTrack("T1", devices=[rack])])
    res_rec = handlers.live12_rack_variation_control(0, 0, "recall", variation_index=0)
    assert isinstance(res_rec["macros"], list) and all(isinstance(x, float) and 0.0 <= x <= 1.0 for x in res_rec["macros"])
    assert res_rec["macros"][0] == pytest.approx(0.5)
    res_rand = handlers.live12_rack_variation_control(0, 0, "randomize")
    assert res_rand["randomized"] is True
    assert isinstance(res_rand["macros"], list) and len(res_rand["macros"]) == len(rack.parameters) - 1
    assert res_rand["macros"][0] == pytest.approx(1.0)

    # 3. Rightward loop shift writes loop_end BEFORE loop_start
    class _LoopStrictClip(StrictMidiClip):
        def __init__(self, length: float = 4.0):
            self._loop_start = 0.0
            self._loop_end = float(length)
            super().__init__(length=length)

        @property
        def loop_start(self):
            return self._loop_start

        @loop_start.setter
        def loop_start(self, val):
            if float(val) >= self._loop_end:
                raise RuntimeError("loop_start must be < loop_end")
            self._loop_start = float(val)

        @property
        def loop_end(self):
            return self._loop_end

        @loop_end.setter
        def loop_end(self, val):
            if float(val) <= self._loop_start:
                raise RuntimeError("loop_end must be > loop_start")
            self._loop_end = float(val)

    lclip = _LoopStrictClip(length=4.0)
    lclip._loop_start = 0.0
    lclip._loop_end = 4.0
    aclip = StrictAudioClip()
    class _ScaleSong(StrictSong):
        def get_all_scales_ordered(self):
            return [("Custom_Dorian", [0, 2, 3, 5, 7, 9, 10])]

    h_clip, _ = _make_r2_handlers(song_obj=_ScaleSong([StrictTrack("M1", clips=[lclip]), StrictTrack("A1", clips=[aclip])]))

    res_loop = h_clip.live12_clip_set_properties(0, 0, loop_start=8.0, loop_end=16.0)
    assert res_loop["loop_start"] == 8.0 and res_loop["loop_end"] == 16.0

    # Modify multiple notes without note_id mutates distinct notes (not existing[0] twice)
    h_clip.live12_clip_add_notes(0, 0, [
        {"pitch": 60, "start_time": 0.0, "duration": 0.5, "velocity": 80},
        {"pitch": 60, "start_time": 1.0, "duration": 0.5, "velocity": 80},
    ])
    h_clip.live12_clip_modify_notes(0, 0, [
        {"pitch": 60, "velocity": 100},
        {"pitch": 60, "velocity": 50},
    ])
    assert [n.velocity for n in lclip._notes] == [100.0, 50.0]

    # remove_notes rejects audio clips
    with pytest.raises(ValueError, match="audio clip"):
        h_clip.live12_clip_remove_notes(1, 0)

    # arpeggiate preserves note_ids via apply_note_modifications & fit_to_scale uses get_all_scales_ordered
    orig_ids = [n.note_id for n in lclip._notes]
    h_clip.live12_clip_transform_midi(0, 0, "arpeggiate", {"rate": 0.25})
    assert [n.note_id for n in lclip._notes] == orig_ids

    lclip._notes[0].pitch = 61  # C# -> snaps into Custom_Dorian (0,2,3,5,7,9,10)
    h_clip.live12_clip_transform_midi(0, 0, "fit_to_scale", {"scale_name": "Custom_Dorian", "root_note": 0})
    assert (lclip._notes[0].pitch % 12) in {0, 2, 3, 5, 7, 9, 10}

    # Euclidean rejects clip.length <= 0
    lclip.length = 0.0
    with pytest.raises(ValueError, match="Clip length"):
        h_clip.live12_clip_transform_midi(0, 0, "euclidean", {"steps": 16, "pulses": 4})


def test_wavetable_readonly_get_browser_budget_os_raise_undo_isolation_dup_dialog_dispatch():
    import types
    import live12_bridge.handlers as handlers_mod

    # 1. Wavetable action="get" is strictly read-only
    wt_filter = _StrictContinuousParam("Filter 1 Freq", value=0.5)

    class _StrictWt:
        name = "Wavetable"
        visible_modulation_target_names = ()
        parameters = [wt_filter]
        add_calls = 0

        class ModulationSource:
            lfo_1 = 3

        def is_parameter_modulatable(self, p):
            return True

        def add_parameter_to_modulation_matrix(self, p):
            self.add_calls += 1

        def set_modulation_value(self, target_idx, src, amt):
            pass

        def get_modulation_value(self, target_idx, src):
            return 0.0

    wt = _StrictWt()
    handlers, song_obj = _make_handlers([StrictTrack("T1", devices=[wt])])
    res_wt = handlers.live12_wavetable_modulation_matrix(0, 0, "get", source="lfo_1", target="Filter 1 Freq")
    assert res_wt["amount"] == 0.0
    assert wt.add_calls == 0

    # 2. _find_browser_item reserves budget so deep Pass 2 & drums cannot starve samples
    def _item(name, uri=None, children=(), loadable=True):
        return types.SimpleNamespace(
            name=name,
            uri=uri or f"uri:{name}",
            children=list(children),
            is_folder=bool(children),
            is_loadable=loadable,
        )

    huge_presets = [_item(f"PresetFolder_{i}", children=[_item(f"P_{i}")], loadable=False) for i in range(2500)]
    inst_cat = _item("Instruments", children=[_item("Wavetable", children=huge_presets, loadable=True)], loadable=False)
    huge_drums = [_item(f"DrumFolder_{i}", children=[_item(f"Kit_{i}")], loadable=False) for i in range(2500)]
    drums_cat = _item("Drums", children=huge_drums, loadable=False)
    samples_cat = _item(
        "Samples",
        children=[_item("Techno", children=[_item("Target_Kick.wav", uri="query:Target_Kick", loadable=True)], loadable=False)],
        loadable=False,
    )
    browser = types.SimpleNamespace(instruments=inst_cat, drums=drums_cat, samples=samples_cat)
    found = handlers._find_browser_item(browser, "Target_Kick.wav")
    assert found is not None and found.name == "Target_Kick.wav"

    # 3. live12_os_* raise NotImplementedError when connected to Live song
    for fn, arg in [
        (handlers.live12_os_save_set, "/tmp/out.als"),
        (handlers.live12_os_open_set, "/tmp/in.als"),
        (handlers.live12_os_export_audio, "/tmp/out.wav"),
    ]:
        with pytest.raises(NotImplementedError):
            fn(arg)

    # 4. _undo_depth isolated per song pointer
    song_a = types.SimpleNamespace(_live_ptr=101, tracks=[], return_tracks=[], scenes=[], begin_undo_step=lambda: None, end_undo_step=lambda: None)
    song_b = types.SimpleNamespace(_live_ptr=202, tracks=[], return_tracks=[], scenes=[])
    cur = [song_a]
    h_multi = BridgeHandlers(types.SimpleNamespace(song=lambda: cur[0], application=lambda: None))
    assert h_multi.live12_undo_redo("begin_step")["undo_depth"] == 1
    cur[0] = song_b
    assert h_multi.live12_undo_redo("status")["undo_depth"] == 0
    cur[0] = song_a
    assert h_multi.live12_undo_redo("end_step")["undo_depth"] == 0

    # 5. track_duplicate finds the actual returned track in s.tracks
    t0 = StrictTrack("Bass")
    t1 = StrictTrack("Lead")
    dup = StrictTrack("Bass Dup")

    class _CustomDupSong:
        tracks = [t0, t1]
        return_tracks = []
        scenes = []

        def duplicate_track(self, idx):
            self.tracks.append(dup)
            return dup

    h_dup, _ = _make_r2_handlers(song_obj=_CustomDupSong())
    assert h_dup.live12_track_duplicate(0)["track_index"] == 2

    # 6. dialog_press raises IndexError on out-of-range button when dialog stays open
    class _AppDialog:
        open_dialog_count = 1
        current_dialog_message = "Save changes?"
        current_dialog_button_count = 2

        def press_current_dialog_button(self, idx):
            if idx >= 2 or idx < 0:
                raise RuntimeError("Invalid button index")

    h_dlg, _ = _make_r2_handlers(app=_AppDialog())
    with pytest.raises(IndexError):
        h_dlg.live12_dialog_press(5)

    # 7. dispatch_tool_call restricts to public live12_* methods only
    for bad in ("_find_browser_item", "close_open_undo_steps", "__init__", "song", "live12__secret"):
        with pytest.raises(AttributeError):
            dispatch_tool_call(handlers, bad, {})
