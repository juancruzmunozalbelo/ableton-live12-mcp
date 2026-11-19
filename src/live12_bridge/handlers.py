"""
Live 12 Bridge - High-Level Structured Handlers
===============================================
Implements all 77 high-level structured handlers for Ableton Live 12.4.6,
covering Transport/Song, Tracks/TakeLanes/Scenes/Routing, Clips/Extended MIDI/Warping,
Browser/Devices/Specialized Instruments & Effects, Views/Dialogs/OS Actions,
and the Universal LOM reflection interface.
"""

from __future__ import annotations

import collections
import math
import os
import re
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

try:
    import Live
except ImportError:
    Live = None

from .reflection import (
    dict_to_midi_note_spec,
    liveobj_valid,
    lom_call,
    lom_get,
    lom_inspect,
    lom_set,
    midi_note_to_dict,
    resolve_path,
    serialize_lom_value,
)

MAX_UNDO_DEPTH = 8
MAX_BROWSER_SEARCH_NODES = 2000

VALID_TRACK_TYPES = ("midi", "audio", "return")
VALID_MONITORING_STATES = ("in", "auto", "off")
LIVE_COLOR_INDEX_MAX = 69  # Live 12 palette slots 0..69
VALID_VIEW_NAMES = (
    "Session",
    "Arranger",
    "Detail",
    "Detail/Clip",
    "Detail/DeviceChain",
    "Browser",
)


class BridgeHandlers:
    """
    Registry of high-level handlers executed on Ableton Live's main thread.
    Each handler accepts the control surface bridge instance and keyword arguments.
    """

    def __init__(self, cs: Any):
        self.cs = cs
        self._undo_depths: Dict[Any, int] = {}

    def _undo_song_key(self, s: Any) -> Any:
        if s is None:
            return "__offline__"
        return getattr(s, "_live_ptr", id(s))

    @property
    def _undo_depth(self) -> int:
        if not hasattr(self, "_undo_depths"):
            self._undo_depths = {}
        return self._undo_depths.get(self._undo_song_key(self.song()), 0)

    @_undo_depth.setter
    def _undo_depth(self, value: int) -> None:
        if not hasattr(self, "_undo_depths"):
            self._undo_depths = {}
        key = self._undo_song_key(self.song())
        if int(value) <= 0:
            self._undo_depths.pop(key, None)
        else:
            self._undo_depths[key] = int(value)

    def song(self) -> Any:
        if self.cs is None:
            return None
        return self.cs.song()

    def application(self) -> Any:
        if self.cs is None:
            return None
        return self.cs.application()

    def root_getter(self, key: str) -> Any:
        if key == "song":
            return self.song()
        elif key == "application":
            return self.application()
        elif key == "control_surfaces":
            app = self.application()
            return getattr(app, "control_surfaces", [self.cs]) if app is not None else [self.cs]
        elif key == "this_device":
            return self.cs
        return self.song()

    # -------------------------------------------------------------------------
    # Domain 1: Transport & Song Tools
    # -------------------------------------------------------------------------

    def live12_transport_play(self, restart: bool = False) -> Dict[str, Any]:
        s = self.song()
        if s:
            if restart:
                s.start_playing()
            else:
                s.continue_playing()
            return {"is_playing": bool(getattr(s, "is_playing", True))}
        return {"is_playing": True}

    def live12_transport_stop(self) -> Dict[str, Any]:
        s = self.song()
        if s:
            s.stop_playing()
            return {"is_playing": bool(getattr(s, "is_playing", False))}
        return {"is_playing": False}

    def live12_transport_record(self, record_mode: str = "arrangement") -> Dict[str, Any]:
        mode = str(record_mode or "arrangement").lower()
        if mode not in ("arrangement", "session"):
            raise ValueError(f"Invalid record_mode '{record_mode}', must be 'arrangement' or 'session'")
        s = self.song()
        if s:
            if mode == "session":
                if hasattr(s, "session_record"):
                    s.session_record = True
            else:
                s.record_mode = True
            rec_mode = bool(getattr(s, "record_mode", False))
            sess_rec = bool(getattr(s, "session_record", False))
            return {
                "status": "recording",
                "record_mode": rec_mode,
                "session_record": sess_rec,
                "is_recording": rec_mode or sess_rec,
            }
        return {"status": "recording", "record_mode": True, "session_record": False, "is_recording": True}

    def live12_transport_set_tempo(self, tempo: float) -> Dict[str, Any]:
        val = float(tempo)
        if math.isnan(val) or math.isinf(val) or val < 20.0 or val > 999.0:
            raise ValueError(f"Tempo {val} out of range [20.0, 999.0]")
        s = self.song()
        if s:
            s.tempo = val
            return {"tempo": s.tempo}
        return {"tempo": val}

    def live12_transport_set_time_signature(self, numerator: int, denominator: int) -> Dict[str, Any]:
        num = int(numerator)
        den = int(denominator)
        if num < 1 or num > 99:
            raise ValueError(f"Time signature numerator {num} out of range [1, 99]")
        if den not in (1, 2, 4, 8, 16):
            raise ValueError(f"Time signature denominator {den} must be 1, 2, 4, 8, or 16")
        s = self.song()
        if s:
            s.signature_numerator = num
            s.signature_denominator = den
            return {"numerator": s.signature_numerator, "denominator": s.signature_denominator}
        return {"numerator": num, "denominator": den}

    def live12_transport_set_loop(self, enabled: bool, start: float, length: float) -> Dict[str, Any]:
        en = bool(enabled)
        st = float(start)
        ln = float(length)
        if math.isnan(st) or math.isinf(st) or st < 0.0:
            raise ValueError(f"Loop start must be non-negative, got {st}")
        if math.isnan(ln) or math.isinf(ln) or ln <= 0.0:
            raise ValueError(f"Loop length must be positive, got {ln}")
        s = self.song()
        if s:
            s.loop = en
            s.loop_start = st
            s.loop_length = ln
            return {"loop": s.loop, "loop_start": s.loop_start, "loop_length": s.loop_length}
        return {"loop": en, "loop_start": st, "loop_length": ln}

    def live12_transport_set_punch(self, punch_in: bool, punch_out: bool) -> Dict[str, Any]:
        pi = bool(punch_in)
        po = bool(punch_out)
        s = self.song()
        if s:
            s.punch_in = pi
            s.punch_out = po
            return {"punch_in": s.punch_in, "punch_out": s.punch_out}
        return {"punch_in": pi, "punch_out": po}

    def live12_transport_set_overdub(self, overdub: bool) -> Dict[str, Any]:
        od = bool(overdub)
        s = self.song()
        if s:
            s.arrangement_overdub = od
            return {"overdub": s.arrangement_overdub}
        return {"overdub": od}

    def live12_transport_set_metronome(self, enabled: bool) -> Dict[str, Any]:
        en = bool(enabled)
        s = self.song()
        if s:
            s.metronome = en
            return {"metronome": s.metronome}
        return {"metronome": en}

    def live12_song_capture_midi(self) -> Dict[str, Any]:
        s = self.song()
        if s:
            can_capture = bool(getattr(s, "can_capture_midi", True))
            if not can_capture:
                return {
                    "status": "success",
                    "captured": False,
                    "can_capture_midi": False,
                    "reason": "No recently played MIDI available to capture",
                }
            if hasattr(s, "capture_midi"):
                s.capture_midi()
            return {"status": "success", "captured": True, "can_capture_midi": True}
        return {"status": "success", "captured": True}

    def live12_song_get_state(self) -> Dict[str, Any]:
        s = self.song()
        tuning = getattr(self, "_current_tuning_system", "Equal Temperament")
        if not s:
            return {
                "tempo": 120.0,
                "signature_numerator": 4,
                "signature_denominator": 4,
                "is_playing": False,
                "record_mode": False,
                "is_recording": False,
                "loop": False,
                "loop_start": 0.0,
                "loop_length": 4.0,
                "metronome": False,
                "scale_name": "Major",
                "root_note": 0,
                "scale_root_note": 0,
                "tuning_system": tuning,
                "tracks_count": 0,
                "scenes_count": 0,
            }

        if hasattr(s, "scale_name"):
            scale_name = str(getattr(s, "scale_name", "Major"))
        elif hasattr(s, "scale_information") and hasattr(s.scale_information, "name"):
            scale_name = str(s.scale_information.name)
        else:
            scale_name = "Major"

        if hasattr(s, "root_note"):
            root_note = int(getattr(s, "root_note", 0))
        elif hasattr(s, "scale_information") and hasattr(s.scale_information, "root_note"):
            root_note = int(s.scale_information.root_note)
        else:
            root_note = 0

        ts = getattr(s, "tuning_system", None)
        live_tuning = str(getattr(ts, "name", "Equal Temperament")) if ts is not None else "Equal Temperament"

        is_rec = bool(getattr(s, "record_mode", False) or getattr(s, "session_record", False))
        return {
            "tempo": s.tempo,
            "signature_numerator": s.signature_numerator,
            "signature_denominator": s.signature_denominator,
            "is_playing": getattr(s, "is_playing", False),
            "record_mode": getattr(s, "record_mode", False),
            "is_recording": is_rec,
            "session_record": getattr(s, "session_record", False),
            "loop": getattr(s, "loop", False),
            "loop_start": getattr(s, "loop_start", 0.0),
            "loop_length": getattr(s, "loop_length", 4.0),
            "metronome": getattr(s, "metronome", False),
            "scale_name": scale_name,
            "root_note": root_note,
            "scale_root_note": root_note,
            "tuning_system": live_tuning,
            "tracks_count": len(getattr(s, "tracks", [])),
            "scenes_count": len(getattr(s, "scenes", [])),
        }

    def live12_song_set_scale(self, root_note: int, scale_name: str) -> Dict[str, Any]:
        rn = int(root_note)
        sn = str(scale_name)
        if rn < 0 or rn > 11:
            raise ValueError(f"Root note {rn} out of range [0, 11]")
        valid_scales = [
            "Major", "Minor", "Dorian", "Mixolydian", "Lydian", "Phrygian", "Locrian",
            "Whole Tone", "Half-whole Dim.", "Whole-half Dim.", "Minor Blues",
            "Minor Pentatonic", "Major Pentatonic", "Harmonic Minor", "Harmonic Major",
            "Dorian #4", "Phrygian Dominant", "Melodic Minor", "Lydian Augmented",
            "Lydian Dominant", "Super Locrian", "Bhairav", "Hungarian Minor",
            "8-Tone Spanish", "Hirajoshi", "In-Sen", "Iwato", "Kumoi", "Pelog Selisir",
            "Pelog Tembung", "Messiaen 3", "Messiaen 4", "Messiaen 5", "Messiaen 6",
            "Messiaen 7",
            "Diminished", "Pentatonic",
        ]
        if sn not in valid_scales:
            raise ValueError(f"Invalid scale name: {sn}")

        # Map common aliases to canonical Live 12 names
        live_scale_name = sn
        if sn == "Pentatonic":
            live_scale_name = "Minor Pentatonic"
        elif sn == "Diminished":
            live_scale_name = "Half-whole Dim."

        s = self.song()
        if s:
            if hasattr(s, "root_note"):
                s.root_note = rn
            if hasattr(s, "scale_name"):
                try:
                    s.scale_name = live_scale_name
                except (ValueError, RuntimeError):
                    if sn != live_scale_name:
                        s.scale_name = sn
                    else:
                        raise
            if hasattr(s, "scale_information") and hasattr(s.scale_information, "name"):
                s.scale_information.root_note = rn
                s.scale_information.name = live_scale_name
        return {"root_note": rn, "scale_name": sn}

    def live12_song_set_tuning_system(self, tuning_name: str) -> Dict[str, Any]:
        if not isinstance(tuning_name, str):
            raise ValueError("tuning_name must be a string")
        if "\x00" in tuning_name:
            raise ValueError("tuning_name cannot contain null bytes")
        if ".." in tuning_name or "/" in tuning_name or "\\" in tuning_name:
            raise ValueError("tuning_name cannot contain path traversal sequences")
        if "\n" in tuning_name or "\r" in tuning_name:
            raise ValueError("tuning_name cannot contain newline characters")
        if len(tuning_name) > 256:
            raise ValueError("tuning_name exceeds maximum length of 256 characters")
        if not tuning_name.strip():
            raise ValueError("tuning_name cannot be empty")
        s = self.song()
        if s is None:
            self._current_tuning_system = str(tuning_name)
            return {"tuning_system": tuning_name, "status": "loaded"}

        if hasattr(s, "load_tuning_system") and callable(getattr(s, "load_tuning_system")):
            s.load_tuning_system(tuning_name)
            return {"tuning_system": tuning_name, "status": "loaded"}

        ts = getattr(s, "tuning_system", None)
        cleaned = tuning_name.strip().lower()
        if ts is not None and str(getattr(ts, "name", "")).strip().lower() == cleaned:
            return {"tuning_system": str(getattr(ts, "name", tuning_name)), "status": "already_active"}
        if ts is None and cleaned in ("equal temperament", "12-tet", "default"):
            return {"tuning_system": "Equal Temperament", "status": "already_active"}
        raise NotImplementedError(
            f"Ableton Live 12's Python LOM exposes Song.tuning_system as read-only and cannot programmatically load '{tuning_name}'."
        )

    def live12_cue_point_control(
        self,
        action: str,
        time: Optional[float] = None,
        name: Optional[str] = None,
        cue_index: Optional[int] = None,
    ) -> Dict[str, Any]:
        s = self.song()
        valid_actions = ("create", "delete", "jump", "list")
        if action not in valid_actions:
            raise ValueError(f"Invalid cue action '{action}', must be one of {valid_actions}")

        if action == "create" and time is not None:
            t_check = float(time)
            if t_check < 0.0 or math.isnan(t_check) or math.isinf(t_check):
                raise ValueError("Cue point time must be non-negative")

        if not s:
            return {"action": action, "cue_points": [], "success": True}

        cue_points = list(getattr(s, "cue_points", []))

        if action == "list":
            res = []
            for i, cp in enumerate(cue_points):
                res.append({
                    "index": i,
                    "name": str(getattr(cp, "name", f"Cue {i}")),
                    "time": float(getattr(cp, "time", 0.0)),
                })
            return {"action": "list", "cue_points": res}

        elif action == "create":
            target_time = float(time) if time is not None else float(getattr(s, "current_song_time", 0.0))
            if target_time < 0.0 or math.isnan(target_time) or math.isinf(target_time):
                raise ValueError("Cue point time must be non-negative")
            existing_cp = None
            for cp in getattr(s, "cue_points", []):
                if abs(float(getattr(cp, "time", -1.0)) - target_time) < 0.01:
                    existing_cp = cp
                    break
            if not existing_cp and hasattr(s, "set_or_delete_cue"):
                if time is not None and hasattr(s, "current_song_time"):
                    orig_time = float(s.current_song_time)
                    if abs(orig_time - target_time) > 1e-6:
                        try:
                            s.current_song_time = target_time
                            s.set_or_delete_cue()
                        finally:
                            s.current_song_time = orig_time
                    else:
                        s.set_or_delete_cue()
                else:
                    s.set_or_delete_cue()
            updated_cues = list(getattr(s, "cue_points", []))
            created_cp = None
            for cp in updated_cues:
                if abs(float(getattr(cp, "time", -1.0)) - target_time) < 0.01:
                    created_cp = cp
                    break
            if created_cp and name:
                created_cp.name = str(name)
            return {
                "action": "create",
                "success": True,
                "time": target_time,
                "name": name or (getattr(created_cp, "name", "") if created_cp else ""),
                "cue_points_count": len(updated_cues),
            }

        elif action == "delete":
            if cue_index is None:
                raise ValueError("cue_index is required for delete action")
            idx = int(cue_index)
            if idx < 0 or idx >= len(cue_points):
                raise IndexError(f"Cue index {idx} out of range (0..{len(cue_points)-1})")
            target_cp = cue_points[idx]
            cp_time = float(getattr(target_cp, "time", 0.0))
            orig_time = float(s.current_song_time) if hasattr(s, "current_song_time") else None
            try:
                if getattr(s, "is_playing", False) and hasattr(s, "current_song_time"):
                    s.current_song_time = cp_time
                    if abs(float(s.current_song_time) - cp_time) >= 1e-3:
                        raise RuntimeError(
                            f"Failed to position song time at cue point {cp_time} while playing "
                            f"(current_song_time={s.current_song_time})"
                        )
                elif hasattr(target_cp, "jump"):
                    target_cp.jump()
                elif hasattr(s, "current_song_time"):
                    s.current_song_time = cp_time
                if hasattr(s, "set_or_delete_cue"):
                    s.set_or_delete_cue()
            finally:
                if (
                    orig_time is not None
                    and not getattr(s, "is_playing", False)
                    and hasattr(s, "current_song_time")
                ):
                    s.current_song_time = orig_time
            return {"action": "delete", "success": True, "cue_index": idx}

        elif action == "jump":
            if cue_index is None:
                raise ValueError("cue_index is required for jump action")
            idx = int(cue_index)
            if idx < 0 or idx >= len(cue_points):
                raise IndexError(f"Cue index {idx} out of range (0..{len(cue_points)-1})")
            target_cp = cue_points[idx]
            if hasattr(target_cp, "jump"):
                target_cp.jump()
            return {
                "action": "jump",
                "success": True,
                "cue_index": idx,
                "time": float(getattr(target_cp, "time", 0.0)),
            }
        return {"action": action, "success": True}

    def live12_tempo_sync_control(
        self,
        action: str,
        enabled: Optional[bool] = None,
        active: Optional[bool] = None,
    ) -> Dict[str, Any]:
        s = self.song()
        valid_actions = ("get_status", "set_link", "set_follower", "tap_tempo", "nudge_up", "nudge_down")
        if action not in valid_actions:
            raise ValueError(f"Invalid sync action '{action}', must be one of {valid_actions}")

        if not s:
            res_off: Dict[str, Any] = {"action": action, "success": True, "tempo": 120.0}
            if action in ("nudge_up", "nudge_down"):
                res_off["active"] = bool(active) if active is not None else False
            return res_off

        if action == "get_status":
            return {
                "action": "get_status",
                "link_enabled": bool(getattr(s, "is_ableton_link_enabled", False)),
                "tempo_follower_enabled": bool(getattr(s, "tempo_follower_enabled", False)),
                "tempo": float(getattr(s, "tempo", 120.0)),
            }
        elif action == "set_link":
            if enabled is not None and hasattr(s, "is_ableton_link_enabled"):
                s.is_ableton_link_enabled = bool(enabled)
            return {
                "action": "set_link",
                "success": True,
                "link_enabled": bool(getattr(s, "is_ableton_link_enabled", enabled if enabled is not None else False)),
            }
        elif action == "set_follower":
            if enabled is not None and hasattr(s, "tempo_follower_enabled"):
                s.tempo_follower_enabled = bool(enabled)
            return {
                "action": "set_follower",
                "success": True,
                "tempo_follower_enabled": bool(getattr(s, "tempo_follower_enabled", enabled if enabled is not None else False)),
            }
        elif action == "tap_tempo":
            if hasattr(s, "tap_tempo"):
                s.tap_tempo()
            return {"action": "tap_tempo", "success": True, "tempo": float(getattr(s, "tempo", 120.0))}
        elif action in ("nudge_up", "nudge_down"):
            other_attr = "nudge_down" if action == "nudge_up" else "nudge_up"
            if hasattr(s, action):
                target_val = getattr(s, action)
                if callable(target_val):
                    target_val()
                elif active is not None:
                    if bool(active) and hasattr(s, other_attr) and not callable(getattr(s, other_attr)):
                        setattr(s, other_attr, False)
                    setattr(s, action, bool(active))
                else:
                    if hasattr(s, other_attr) and not callable(getattr(s, other_attr)):
                        setattr(s, other_attr, False)
                    try:
                        setattr(s, action, True)
                    finally:
                        setattr(s, action, False)
            return {
                "action": action,
                "success": True,
                "active": bool(active) if active is not None else False,
            }
        return {"action": action, "success": True}

    # -------------------------------------------------------------------------
    # Domain 2: Tracks, TakeLanes, Scenes & Routing
    # -------------------------------------------------------------------------

    def live12_track_create(self, type: str = "midi", index: int = -1) -> Dict[str, Any]:
        t_type = type.lower()
        if t_type not in VALID_TRACK_TYPES:
            raise ValueError(f"Invalid track type: {type}. Must be one of {VALID_TRACK_TYPES}")

        s = self.song()
        if not s:
            return {"track_index": 0, "type": t_type}

        num_tracks = len(s.tracks)
        target_idx = num_tracks if index < 0 or index > num_tracks else int(index)

        if t_type == "audio":
            s.create_audio_track(target_idx)
        elif t_type == "return":
            s.create_return_track()
            target_idx = len(s.return_tracks) - 1
        else:
            s.create_midi_track(target_idx)

        # In Live, track created at index target_idx
        return {"track_index": target_idx, "type": t_type}

    def live12_track_delete(self, track_index: int, track_type: str = "regular") -> Dict[str, Any]:
        t_idx = int(track_index)
        t_type = str(track_type or "regular").lower()
        if t_type not in ("regular", "return", "master"):
            raise ValueError(f"Invalid track_type '{track_type}'. Must be 'regular', 'return', or 'master'")
        if t_type == "master" or t_idx == -100:
            raise ValueError("Cannot delete master track")
        s = self.song()
        if s:
            if t_type == "return":
                ret_tracks = getattr(s, "return_tracks", [])
                if t_idx < 0 or t_idx >= len(ret_tracks):
                    raise IndexError(f"Return track index {t_idx} out of range [0, {len(ret_tracks)})")
                if not hasattr(s, "delete_return_track"):
                    raise NotImplementedError("Song.delete_return_track is not available")
                s.delete_return_track(t_idx)
            else:
                if t_idx < 0 or t_idx >= len(s.tracks):
                    raise IndexError(f"Track index {t_idx} out of range [0, {len(s.tracks)})")
                s.delete_track(t_idx)
        res: Dict[str, Any] = {"deleted": True, "track_index": t_idx}
        if t_type != "regular":
            res["track_type"] = t_type
        return res

    def live12_track_duplicate(self, track_index: int) -> Dict[str, Any]:
        t_idx = int(track_index)
        dup_idx = t_idx + 1
        s = self.song()
        if s:
            if t_idx < 0 or t_idx >= len(s.tracks):
                raise IndexError(f"Track index {t_idx} out of range [0, {len(s.tracks)})")
            dup_track = s.duplicate_track(t_idx)
            if dup_track is not None:
                tracks_list = list(s.tracks)
                try:
                    dup_idx = tracks_list.index(dup_track)
                except ValueError:
                    dup_idx = next(
                        (i for i, tr in enumerate(tracks_list) if tr is dup_track),
                        t_idx + 1,
                    )
        return {"duplicated": True, "source_track_index": t_idx, "track_index": dup_idx}

    @staticmethod
    def _track_can_be_armed(tr: Any) -> bool:
        """Safely determines whether a Track supports arming without crashing on Return/Master/Group tracks."""
        if hasattr(tr, "can_be_armed"):
            try:
                return bool(getattr(tr, "can_be_armed", False))
            except (RuntimeError, AttributeError):
                return False
        return hasattr(tr, "arm")

    @classmethod
    def _safe_get_track_arm(cls, tr: Any) -> bool:
        if not cls._track_can_be_armed(tr):
            return False
        try:
            return bool(getattr(tr, "arm", False))
        except (RuntimeError, AttributeError):
            return False

    def live12_track_set_properties(
        self,
        track_index: int,
        name: Optional[str] = None,
        color: Optional[int] = None,
        color_index: Optional[int] = None,
        color_rgb: Optional[List[int]] = None,
        solo: Optional[bool] = None,
        mute: Optional[bool] = None,
        arm: Optional[bool] = None,
        track_type: str = "regular",
    ) -> Dict[str, Any]:
        t_idx = int(track_index)
        s = self.song()
        res: Dict[str, Any] = {"track_index": t_idx}
        if track_type != "regular":
            res["track_type"] = track_type
        if s:
            tr = self._resolve_target_track(s, t_idx, track_type)
            if name is not None:
                tr.name = str(name)
            color_state = self._apply_color(tr, color, color_index, color_rgb)
            if solo is not None:
                tr.solo = bool(solo)
            if mute is not None:
                tr.mute = bool(mute)
            if arm is not None and self._track_can_be_armed(tr):
                try:
                    tr.arm = bool(arm)
                except RuntimeError:
                    pass

            res.update({
                "name": tr.name,
                "color": getattr(tr, "color", color),
                "solo": tr.solo,
                "mute": tr.mute,
                "arm": self._safe_get_track_arm(tr),
            })
            res.update(color_state)
        else:
            if name is not None:
                res["name"] = name
            if color is not None:
                res["color"] = color
            if solo is not None:
                res["solo"] = solo
            if mute is not None:
                res["mute"] = mute
            if arm is not None:
                res["arm"] = arm
            if color_index is not None:
                res["color_index"] = int(color_index)
            if color_rgb is not None:
                res["color_rgb"] = list(color_rgb)
        return res

    def live12_track_group(self, track_indices: List[int]) -> Dict[str, Any]:
        s = self.song()
        if not track_indices:
            raise ValueError("track_indices must not be empty")
        indices = [int(i) for i in track_indices]
        if s is None:
            return {"grouped": True, "group_track_index": indices[0], "tracks": indices}

        for idx in indices:
            if idx < 0 or idx >= len(s.tracks):
                raise IndexError(f"Track index {idx} out of range [0, {len(s.tracks)})")
        if hasattr(s, "group_tracks") and callable(getattr(s, "group_tracks")):
            grp_track = s.group_tracks(indices)
            grp_idx = list(s.tracks).index(grp_track) if grp_track in s.tracks else min(indices)
            return {"grouped": True, "group_track_index": grp_idx, "tracks": indices}
        raise NotImplementedError(
            "Ableton Live 12's Python LOM does not expose Song.group_tracks; grouping tracks must be performed in the Live GUI."
        )

    def live12_track_ungroup(self, group_track_index: int) -> Dict[str, Any]:
        idx = int(group_track_index)
        s = self.song()
        if s is None:
            return {"ungrouped": True, "group_track_index": idx}

        if idx < 0 or idx >= len(s.tracks):
            raise IndexError(f"Track index {idx} out of range [0, {len(s.tracks)})")
        tr = s.tracks[idx]
        if hasattr(s, "ungroup_track") and callable(getattr(s, "ungroup_track")):
            s.ungroup_track(idx)
            return {"ungrouped": True, "group_track_index": idx, "name": getattr(tr, "name", "")}
        if hasattr(tr, "ungroup") and callable(getattr(tr, "ungroup")):
            tr.ungroup()
            return {"ungrouped": True, "group_track_index": idx, "name": getattr(tr, "name", "")}
        if not getattr(tr, "is_foldable", False):
            raise ValueError(f"Track {idx} ('{getattr(tr, 'name', '')}') is not a group track")
        raise NotImplementedError(
            "Ableton Live 12's Python LOM does not expose an ungroup_track/ungroup API; ungrouping must be performed in the Live GUI."
        )

    def live12_take_lane_create(self, track_index: int) -> Dict[str, Any]:
        t_idx = int(track_index)
        s = self.song()
        lane_idx = 0
        if s:
            if t_idx < 0 or t_idx >= len(s.tracks):
                raise IndexError(f"Track index {t_idx} out of range")
            tr = s.tracks[t_idx]
            if hasattr(tr, "create_take_lane"):
                tr.create_take_lane()
            lane_idx = len(getattr(tr, "take_lanes", [])) - 1
        return {"track_index": t_idx, "take_lane_index": max(0, lane_idx), "lane_index": max(0, lane_idx)}

    def live12_take_lane_list(self, track_index: int) -> Dict[str, Any]:
        t_idx = int(track_index)
        s = self.song()
        lanes = []
        if s:
            if t_idx < 0 or t_idx >= len(s.tracks):
                raise IndexError(f"Track index {t_idx} out of range")
            tr = s.tracks[t_idx]
            for i, lane in enumerate(getattr(tr, "take_lanes", [])):
                lanes.append({"index": i, "name": getattr(lane, "name", f"Take {i+1}")})
        return {"take_lanes": lanes}

    def live12_take_lane_comp_region(
        self,
        track_index: int,
        lane_index: int,
        start: float,
        length: float,
    ) -> Dict[str, Any]:
        t_idx = int(track_index)
        l_idx = int(lane_index)
        st = float(start)
        ln = float(length)
        if math.isnan(st) or math.isinf(st) or st < 0.0:
            raise ValueError(f"Comp region start must be non-negative, got {st}")
        if math.isnan(ln) or math.isinf(ln) or ln <= 0.0:
            raise ValueError(f"Comp region length must be positive, got {ln}")
        if t_idx < 0:
            raise IndexError(f"Track index {t_idx} out of range")
        if l_idx < 0:
            raise IndexError(f"Lane index {l_idx} out of range")
        s = self.song()
        if s is None:
            return {
                "comped": True,
                "track_index": t_idx,
                "lane_index": l_idx,
                "start": st,
                "length": ln,
            }

        if t_idx >= len(s.tracks):
            raise IndexError(f"Track index {t_idx} out of range [0, {len(s.tracks)})")
        tr = s.tracks[t_idx]
        take_lanes = getattr(tr, "take_lanes", [])
        if l_idx >= len(take_lanes):
            raise IndexError(f"Lane index {l_idx} out of range [0, {len(take_lanes)})")
        lane = take_lanes[l_idx]
        if hasattr(lane, "comp_region") and callable(getattr(lane, "comp_region")):
            lane.comp_region(st, ln)
            return {"comped": True, "track_index": t_idx, "lane_index": l_idx, "start": st, "length": ln}
        if hasattr(tr, "comp_region") and callable(getattr(tr, "comp_region")):
            tr.comp_region(l_idx, st, ln)
            return {"comped": True, "track_index": t_idx, "lane_index": l_idx, "start": st, "length": ln}
        raise NotImplementedError(
            "Ableton Live 12's Python LOM (Live.TakeLane.TakeLane) does not expose a comp_region API; comping must be performed in the Live GUI."
        )

    def live12_take_lane_create_audio_clip(
        self,
        track_index: int,
        take_lane_index: int,
        file_path: str,
        time: float,
    ) -> Dict[str, Any]:
        t_idx = int(track_index)
        l_idx = int(take_lane_index)
        f_path = str(file_path)
        t_time = float(time)
        if math.isnan(t_time) or math.isinf(t_time) or t_time < 0.0:
            raise ValueError(f"Clip time must be non-negative, got {t_time}")
        if t_idx < 0:
            raise IndexError(f"Track index {t_idx} out of range")
        if l_idx < 0:
            raise IndexError(f"Lane index {l_idx} out of range")

        s = self.song()
        clip_name = os.path.basename(f_path)
        if s:
            if t_idx >= len(s.tracks):
                raise IndexError(f"Track index {t_idx} out of range [0, {len(s.tracks)})")
            tr = s.tracks[t_idx]
            take_lanes = getattr(tr, "take_lanes", [])
            if l_idx >= len(take_lanes):
                raise IndexError(f"Lane index {l_idx} out of range [0, {len(take_lanes)})")
            lane = take_lanes[l_idx]
            if hasattr(lane, "create_audio_clip"):
                clip_obj = lane.create_audio_clip(f_path, t_time)
                if clip_obj and hasattr(clip_obj, "name"):
                    clip_name = clip_obj.name

        return {
            "status": "success",
            "track_index": t_idx,
            "take_lane_index": l_idx,
            "file_path": f_path,
            "time": t_time,
            "clip_name": clip_name,
        }

    def live12_scene_create(self, index: int = -1) -> Dict[str, Any]:
        s = self.song()
        idx = int(index)
        if s:
            num_scenes = len(s.scenes)
            target_idx = num_scenes if idx < 0 or idx > num_scenes else idx
            s.create_scene(target_idx)
            return {"scene_index": target_idx}
        return {"scene_index": 0}

    def live12_scene_fire(self, index: int) -> Dict[str, Any]:
        idx = int(index)
        s = self.song()
        if s:
            if idx < 0 or idx >= len(s.scenes):
                raise IndexError(f"Scene index {idx} out of range")
            s.scenes[idx].fire()
        return {"fired": True, "is_playing": True, "scene_index": idx}

    @staticmethod
    def _match_routing_option(options: Any, target: str, label: str) -> Any:
        opts = list(options or [])
        target_s = str(target).strip()
        target_l = target_s.lower()
        for opt in opts:
            name = str(getattr(opt, "display_name", opt))
            if name == target_s:
                return opt
        for opt in opts:
            name = str(getattr(opt, "display_name", opt))
            if name.lower() == target_l:
                return opt
        avail = [str(getattr(o, "display_name", o)) for o in opts]
        raise ValueError(f"Requested {label} '{target}' is not available. Available: {avail}")

    def live12_routing_set(
        self,
        track_index: int,
        input_type: Optional[str] = None,
        input_channel: Optional[str] = None,
        output_type: Optional[str] = None,
        output_channel: Optional[str] = None,
        monitoring: Optional[str] = None,
        track_type: str = "regular",
    ) -> Dict[str, Any]:
        t_idx = int(track_index)
        if monitoring is not None and monitoring.lower() not in VALID_MONITORING_STATES:
            raise ValueError(f"Invalid monitoring state '{monitoring}'. Must be one of {VALID_MONITORING_STATES}")

        res: Dict[str, Any] = {"track_index": t_idx}
        if track_type != "regular":
            res["track_type"] = track_type
        s = self.song()
        if s:
            tr = self._resolve_target_track(s, t_idx, track_type)
            if input_type is not None:
                if hasattr(tr, "available_input_routing_types"):
                    matched = self._match_routing_option(tr.available_input_routing_types, input_type, "input_type")
                    tr.input_routing_type = matched
                    res["input_type"] = str(getattr(matched, "display_name", matched))
                else:
                    res["input_type"] = input_type
            if input_channel is not None:
                if hasattr(tr, "available_input_routing_channels"):
                    matched = self._match_routing_option(tr.available_input_routing_channels, input_channel, "input_channel")
                    tr.input_routing_channel = matched
                    res["input_channel"] = str(getattr(matched, "display_name", matched))
                else:
                    res["input_channel"] = input_channel
            if output_type is not None:
                if hasattr(tr, "available_output_routing_types"):
                    matched = self._match_routing_option(tr.available_output_routing_types, output_type, "output_type")
                    tr.output_routing_type = matched
                    res["output_type"] = str(getattr(matched, "display_name", matched))
                else:
                    res["output_type"] = output_type
            if output_channel is not None:
                if hasattr(tr, "available_output_routing_channels"):
                    matched = self._match_routing_option(tr.available_output_routing_channels, output_channel, "output_channel")
                    tr.output_routing_channel = matched
                    res["output_channel"] = str(getattr(matched, "display_name", matched))
                else:
                    res["output_channel"] = output_channel
            if monitoring is not None:
                m_map = {"in": 0, "auto": 1, "off": 2}
                m_val = m_map.get(monitoring.lower() if isinstance(monitoring, str) else monitoring)
                if m_val is not None:
                    try:
                        if hasattr(tr, "current_monitoring_state"):
                            tr.current_monitoring_state = m_val
                    except RuntimeError as e:
                        raise ValueError(
                            f"Track '{getattr(tr, 'name', t_idx)}' does not support input monitoring: {e}"
                        ) from e
                res["monitoring"] = monitoring
        else:
            if input_type is not None:
                res["input_type"] = input_type
            if input_channel is not None:
                res["input_channel"] = input_channel
            if output_type is not None:
                res["output_type"] = output_type
            if output_channel is not None:
                res["output_channel"] = output_channel
            if monitoring is not None:
                res["monitoring"] = monitoring
        return res

    @staticmethod
    def _parse_send_index(key: Any) -> Optional[int]:
        if isinstance(key, bool):
            return None
        if isinstance(key, int):
            return key
        if isinstance(key, str):
            k = key.strip().upper()
            if len(k) == 1 and "A" <= k <= "Z":
                return ord(k) - ord("A")
            if k.startswith("RETURN_") or k.startswith("SEND_"):
                suffix = k.split("_", 1)[1]
                if len(suffix) == 1 and "A" <= suffix <= "Z":
                    return ord(suffix) - ord("A")
                try:
                    return int(suffix)
                except ValueError:
                    return None
            try:
                return int(k)
            except ValueError:
                return None
        return None

    def _resolve_target_track(self, s: Any, track_index: int, track_type: str = "regular") -> Any:
        t_idx = int(track_index)
        t_type = str(track_type or "regular").lower()
        if t_type not in ("regular", "return", "master"):
            raise ValueError(f"Invalid track_type '{track_type}'. Must be 'regular', 'return', or 'master'")
        if t_type == "master" or t_idx == -100:
            master = getattr(s, "master_track", None)
            if master is None:
                raise IndexError("Master track is not available")
            return master
        if t_type == "return":
            ret_tracks = getattr(s, "return_tracks", [])
            if 0 <= t_idx < len(ret_tracks):
                return ret_tracks[t_idx]
            raise IndexError(f"Return track index {t_idx} out of range")
        tracks = getattr(s, "tracks", [])
        if 0 <= t_idx < len(tracks):
            return tracks[t_idx]
        raise IndexError(f"Track index {t_idx} out of range")

    @staticmethod
    def _db_to_fader(db: float) -> float:
        """Converts Ableton Live dB [-70.0..+6.0] continuously to normalized fader [0.0..1.0]."""
        db_f = float(db)
        if math.isnan(db_f) or math.isinf(db_f) or db_f < -70.0 or db_f > 6.0:
            raise ValueError(f"Volume dB {db_f} out of range [-70.0, 6.0]")
        if db_f <= -70.0:
            return 0.0
        if db_f == 0.0:
            return 0.85
        if db_f < 0.0:
            return max(0.0, min(1.0, 0.85 * (10.0 ** (db_f / 40.0))))
        return max(0.0, min(1.0, 0.85 + (db_f / 6.0) * 0.15))

    def live12_mixer_set(
        self,
        track_index: int,
        volume: Optional[float] = None,
        volume_db: Optional[float] = None,
        pan: Optional[float] = None,
        sends: Optional[Dict[str, float]] = None,
        crossfader: Optional[str] = None,
        track_type: str = "regular",
        send_index: Optional[Union[str, int]] = None,
        send_value: Optional[float] = None,
    ) -> Dict[str, Any]:
        t_idx = int(track_index)
        vol_amp: Optional[float] = None
        if volume_db is not None:
            vol_amp = self._db_to_fader(float(volume_db))
        elif volume is not None:
            vol_f = float(volume)
            if math.isnan(vol_f) or math.isinf(vol_f) or vol_f < -70.0 or vol_f > 6.0:
                raise ValueError(f"Volume {vol_f} out of range [-70.0, 6.0]")
            if 0.0 <= vol_f <= 1.0:
                vol_amp = vol_f
            else:
                vol_amp = self._db_to_fader(vol_f)

        if pan is not None:
            p = float(pan)
            if math.isnan(p) or math.isinf(p) or p < -1.0 or p > 1.0:
                raise ValueError(f"Pan {p} out of range [-1.0, 1.0]")

        xf_val: Optional[int] = None
        if crossfader is not None:
            xf_map = {"a": 0, "none": 1, "b": 2}
            xf_key = str(crossfader).strip().lower()
            if xf_key not in xf_map:
                raise ValueError(f"Invalid crossfader '{crossfader}'. Must be 'A', 'None', or 'B'")
            xf_val = xf_map[xf_key]

        merged_sends: Optional[Dict[str, float]] = dict(sends) if sends else None
        if send_index is not None and send_value is not None:
            if merged_sends is None:
                merged_sends = {}
            merged_sends[str(send_index)] = float(send_value)

        s = self.song()
        res: Dict[str, Any] = {"track_index": t_idx}
        if track_type != "regular":
            res["track_type"] = track_type
        if volume_db is not None:
            res["volume_db"] = float(volume_db)
        if s:
            tr = self._resolve_target_track(s, t_idx, track_type)
            mixer = getattr(tr, "mixer_device", None)
            if mixer:
                if vol_amp is not None and hasattr(mixer, "volume"):
                    v_min = float(getattr(mixer.volume, "min", 0.0))
                    v_max = float(getattr(mixer.volume, "max", 1.0))
                    mixer.volume.value = max(v_min, min(v_max, vol_amp))
                    res["volume"] = mixer.volume.value
                if pan is not None and hasattr(mixer, "panning"):
                    p_min = float(getattr(mixer.panning, "min", -1.0))
                    p_max = float(getattr(mixer.panning, "max", 1.0))
                    mixer.panning.value = max(p_min, min(p_max, float(pan)))
                    res["pan"] = mixer.panning.value
                if merged_sends is not None:
                    sends_list = getattr(mixer, "sends", None)
                    if sends_list is None:
                        raise ValueError("Target track mixer does not expose sends")
                    res_sends = {}
                    for k, v in merged_sends.items():
                        s_idx = self._parse_send_index(k)
                        if s_idx is None:
                            raise ValueError(f"Invalid send identifier {k!r}")
                        if not (0 <= s_idx < len(sends_list)):
                            raise IndexError(
                                f"Send index {s_idx} out of range [0, {len(sends_list)})"
                                if sends_list
                                else f"Send index {s_idx} out of range: track has no sends"
                            )
                        val = float(v)
                        if math.isnan(val) or math.isinf(val):
                            raise ValueError(f"Send value must be finite, got {val}")
                        if val < 0.0 or val > 1.0:
                            raise ValueError(f"Send value {val} out of range [0.0, 1.0]")
                        s_min = float(getattr(sends_list[s_idx], "min", 0.0))
                        s_max = float(getattr(sends_list[s_idx], "max", 1.0))
                        sends_list[s_idx].value = max(s_min, min(s_max, val))
                        res_sends[str(s_idx)] = sends_list[s_idx].value
                    res["sends"] = res_sends
                if xf_val is not None:
                    is_master = (
                        str(track_type or "regular").lower() == "master"
                        or t_idx == -100
                        or tr is getattr(s, "master_track", None)
                    )
                    if is_master or not hasattr(mixer, "crossfade_assign"):
                        raise ValueError("Master track mixer does not support crossfade_assign")
                    try:
                        mixer.crossfade_assign = xf_val
                    except RuntimeError as e:
                        raise ValueError(f"Track does not support crossfade_assign: {e}") from e
                    res["crossfader"] = crossfader
        else:
            if vol_amp is not None:
                res["volume"] = vol_amp
            if pan is not None:
                res["pan"] = float(pan)
            if merged_sends is not None:
                res_sends = {}
                for k, v in merged_sends.items():
                    s_idx = self._parse_send_index(k)
                    if s_idx is None:
                        raise ValueError(f"Invalid send identifier {k!r}")
                    if s_idx < 0:
                        raise IndexError(f"Send index {s_idx} out of range")
                    val = float(v)
                    if math.isnan(val) or math.isinf(val):
                        raise ValueError(f"Send value must be finite, got {val}")
                    res_sends[str(s_idx)] = val
                res["sends"] = res_sends
            if crossfader is not None:
                res["crossfader"] = crossfader
        return res

    @staticmethod
    def _apply_color(
        obj: Any,
        color: Optional[int],
        color_index: Optional[int],
        color_rgb: Optional[List[int]],
    ) -> Dict[str, Any]:
        """Apply a palette index (Live 12 `color_index`, 0..69) or an RGB color.

        Live 12 exposes two distinct properties:
          * `color_index` -> the 70-slot palette index used by the GUI (0..69).
          * `color`       -> the packed RGB value of the current palette slot.

        Historically this handler assigned the raw integer to `color`, which silently
        did nothing in the GUI (every track kept the default palette slot 69).
        `color` is therefore interpreted as a palette index when it fits in 0..69
        and as a packed RGB integer otherwise; `color_rgb` sets an explicit RGB.
        """
        state: Dict[str, Any] = {}
        idx_val = color_index if color_index is not None else (
            int(color) if color is not None and 0 <= int(color) <= LIVE_COLOR_INDEX_MAX else None
        )
        if idx_val is not None:
            idx_val = int(idx_val)
            if idx_val < 0 or idx_val > LIVE_COLOR_INDEX_MAX:
                raise ValueError(
                    f"color_index {idx_val} out of range [0, {LIVE_COLOR_INDEX_MAX}]"
                )
            if hasattr(obj, "color_index"):
                obj.color_index = idx_val
            else:
                obj.color = idx_val
            state["color_index"] = getattr(obj, "color_index", idx_val)
        if color_rgb is not None:
            rgb = [int(v) for v in color_rgb]
            if len(rgb) not in (3, 4):
                raise ValueError("color_rgb must contain 3 (RGB) or 4 (RGBA) components")
            for v in rgb[:3]:
                if v < 0 or v > 255:
                    raise ValueError(f"color_rgb component {v} out of range [0, 255]")
            packed_rgb = ((rgb[0] & 0xFF) << 16) | ((rgb[1] & 0xFF) << 8) | (rgb[2] & 0xFF)
            obj.color = packed_rgb
            state["color_rgb"] = rgb
        elif color is not None and not (0 <= int(color) <= LIVE_COLOR_INDEX_MAX):
            packed = int(color)
            rgb = [(packed >> 16) & 0xFF, (packed >> 8) & 0xFF, packed & 0xFF]
            obj.color = packed
            state["color_rgb"] = rgb
        return state

    def live12_scene_set_properties(
        self,
        scene_index: int,
        name: Optional[str] = None,
        color: Optional[int] = None,
        color_index: Optional[int] = None,
        color_rgb: Optional[List[int]] = None,
        tempo: Optional[float] = None,
        tempo_enabled: Optional[bool] = None,
        time_signature_numerator: Optional[int] = None,
        time_signature_denominator: Optional[int] = None,
        time_signature_enabled: Optional[bool] = None,
    ) -> Dict[str, Any]:
        s = self.song()
        idx = int(scene_index)
        if idx < 0:
            raise IndexError("Scene index must be non-negative")
        res: Dict[str, Any] = {"scene_index": idx, "status": "success"}
        if s:
            scenes = getattr(s, "scenes", [])
            if idx >= len(scenes):
                raise IndexError(f"Scene index {idx} out of range [0, {len(scenes)})")
            scene = scenes[idx]
            if name is not None:
                scene.name = str(name)
            color_state = self._apply_color(scene, color, color_index, color_rgb)
            if tempo is not None:
                t_val = float(tempo)
                if t_val < 20.0 or t_val > 999.0 or math.isnan(t_val) or math.isinf(t_val):
                    raise ValueError(f"Tempo {t_val} out of range [20.0, 999.0]")
                scene.tempo = t_val
            if tempo_enabled is not None:
                scene.tempo_enabled = bool(tempo_enabled)
            if time_signature_numerator is not None:
                ts_num = int(time_signature_numerator)
                if ts_num < 1 or ts_num > 99:
                    raise ValueError("time_signature_numerator out of range [1, 99]")
                scene.time_signature_numerator = ts_num
            if time_signature_denominator is not None:
                ts_den = int(time_signature_denominator)
                if ts_den not in (1, 2, 4, 8, 16):
                    raise ValueError("time_signature_denominator must be 1, 2, 4, 8, or 16")
                scene.time_signature_denominator = ts_den
            if time_signature_enabled is not None:
                scene.time_signature_enabled = bool(time_signature_enabled)
            res.update(color_state)
            raw_color = getattr(scene, "color", color or 0)
            if isinstance(raw_color, (tuple, list)) and len(raw_color) >= 3:
                color_out = ((int(raw_color[0]) & 0xFF) << 16) | ((int(raw_color[1]) & 0xFF) << 8) | (int(raw_color[2]) & 0xFF)
            else:
                color_out = int(raw_color) if raw_color is not None else 0
            res.update({
                "name": str(getattr(scene, "name", name or "")),
                "color": color_out,
                "tempo": float(getattr(scene, "tempo", tempo or 120.0)),
                "tempo_enabled": bool(getattr(scene, "tempo_enabled", tempo_enabled or False)),
                "time_signature_numerator": int(getattr(scene, "time_signature_numerator", time_signature_numerator or 4)),
                "time_signature_denominator": int(getattr(scene, "time_signature_denominator", time_signature_denominator or 4)),
                "time_signature_enabled": bool(getattr(scene, "time_signature_enabled", time_signature_enabled or False)),
            })
        else:
            if name is not None:
                res["name"] = str(name)
            if color is not None:
                res["color"] = int(color)
            if tempo is not None:
                res["tempo"] = float(tempo)
            if tempo_enabled is not None:
                res["tempo_enabled"] = bool(tempo_enabled)
            if time_signature_numerator is not None:
                res["time_signature_numerator"] = int(time_signature_numerator)
            if time_signature_denominator is not None:
                res["time_signature_denominator"] = int(time_signature_denominator)
            if time_signature_enabled is not None:
                res["time_signature_enabled"] = bool(time_signature_enabled)
        return res

    def live12_routing_get(self, track_index: int, track_type: str = "regular") -> Dict[str, Any]:
        s = self.song()
        idx = int(track_index)
        if s:
            tr = self._resolve_target_track(s, idx, track_type)

            def _safe_routing_name(attr_name: str, default: str) -> str:
                try:
                    val = getattr(tr, attr_name, None)
                except RuntimeError:
                    return default
                if val is None:
                    return default
                return getattr(val, "display_name", str(val))

            def _safe_routing_list(attr_name: str) -> List[str]:
                try:
                    items = getattr(tr, attr_name, ()) or ()
                except RuntimeError:
                    return []
                return [getattr(item, "display_name", str(item)) for item in items]

            in_type = _safe_routing_name("input_routing_type", "None")
            in_channel = _safe_routing_name("input_routing_channel", "None")
            out_type = _safe_routing_name("output_routing_type", "Master")
            out_channel = _safe_routing_name("output_routing_channel", "1/2")
            monitoring = "Auto"
            try:
                if hasattr(tr, "current_monitoring_state"):
                    cms = tr.current_monitoring_state
                    monitoring = ["In", "Auto", "Off"][cms] if isinstance(cms, int) and 0 <= cms < 3 else str(cms)
                elif hasattr(tr, "monitoring"):
                    monitoring = str(tr.monitoring)
            except RuntimeError:
                monitoring = "N/A"

            avail_in_types = _safe_routing_list("available_input_routing_types")
            avail_in_channels = _safe_routing_list("available_input_routing_channels")
            avail_out_types = _safe_routing_list("available_output_routing_types")
            avail_out_channels = _safe_routing_list("available_output_routing_channels")

            res: Dict[str, Any] = {
                "track_index": idx,
                "input_routing_type": in_type,
                "input_routing_channel": in_channel,
                "output_routing_type": out_type,
                "output_routing_channel": out_channel,
                "monitoring": monitoring,
                "available_input_routing_types": avail_in_types,
                "available_input_routing_channels": avail_in_channels,
                "available_output_routing_types": avail_out_types,
                "available_output_routing_channels": avail_out_channels,
            }
            if track_type != "regular":
                res["track_type"] = track_type
            return res
        if idx < 0 and track_type == "regular":
            raise IndexError("Track index must be non-negative")
        return {
            "track_index": idx,
            "input_routing_type": "All Ins",
            "input_routing_channel": "All Channels",
            "output_routing_type": "Master",
            "output_routing_channel": "1/2",
            "monitoring": "Auto",
            "available_input_routing_types": ["All Ins", "Ext. In"],
            "available_input_routing_channels": ["All Channels", "1", "2"],
            "available_output_routing_types": ["Master"],
            "available_output_routing_channels": ["1/2"],
        }

    # -------------------------------------------------------------------------
    # Domain 3: Clips, Extended MIDI & Warping
    # -------------------------------------------------------------------------

    def live12_clip_create(
        self,
        track_index: int,
        slot_index: int,
        length_beats: float = 4.0,
        name: Optional[str] = None,
    ) -> Dict[str, Any]:
        t_idx = int(track_index)
        s_idx = int(slot_index)
        lb = float(length_beats)
        if math.isnan(lb) or math.isinf(lb) or lb <= 0.0:
            raise ValueError(f"Clip length_beats must be positive (> 0.0), got {lb}")
        s = self.song()
        clip_name = name or "New Clip"
        actual_len = lb
        is_audio = False
        if s:
            if t_idx < 0 or t_idx >= len(s.tracks):
                raise IndexError(f"Track index {t_idx} out of range")
            tr = s.tracks[t_idx]
            if s_idx < 0 or s_idx >= len(tr.clip_slots):
                raise IndexError(f"Slot index {s_idx} out of range")
            slot = tr.clip_slots[s_idx]
            slot.create_clip(lb)
            clip_obj = getattr(slot, "clip", None)
            if clip_obj:
                if name:
                    clip_obj.name = str(name)
                clip_name = getattr(clip_obj, "name", clip_name)
                actual_len = float(getattr(clip_obj, "length", lb))
                is_audio = bool(getattr(clip_obj, "is_audio_clip", getattr(clip_obj, "is_audio", False)))
        return {
            "status": "created",
            "track_index": t_idx,
            "slot_index": s_idx,
            "length": actual_len,
            "name": clip_name,
            "clip": {
                "name": clip_name,
                "length": actual_len,
                "is_audio": is_audio,
            },
        }

    def live12_clip_delete(self, track_index: int, slot_index: int) -> Dict[str, Any]:
        t_idx = int(track_index)
        s_idx = int(slot_index)
        s = self.song()
        if s:
            if t_idx < 0 or t_idx >= len(s.tracks):
                raise IndexError(f"Track index {t_idx} out of range")
            tr = s.tracks[t_idx]
            if s_idx < 0 or s_idx >= len(tr.clip_slots):
                raise IndexError(f"Slot index {s_idx} out of range")
            tr.clip_slots[s_idx].delete_clip()
        return {"deleted": True, "track_index": t_idx, "slot_index": s_idx}

    def live12_clip_delete_arrangement(
        self,
        track_index: int,
        clip_index: int,
    ) -> Dict[str, Any]:
        """Deletes an Arrangement View clip by its position on the track.

        `live12_clip_delete` only removes Session View slot clips; this handler
        covers the Arrangement View, which is where every clip of a produced
        track lives. Live's `Track.delete_clip(clip)` requires the clip object,
        so it is resolved from `track.arrangement_clips` here.
        """
        t_idx = int(track_index)
        c_idx = int(clip_index)
        s = self.song()
        if s:
            if t_idx < 0 or t_idx >= len(s.tracks):
                raise IndexError(f"Track index {t_idx} out of range")
            tr = s.tracks[t_idx]
            arr = list(getattr(tr, "arrangement_clips", []) or [])
            if c_idx < 0 or c_idx >= len(arr):
                raise IndexError(
                    f"Arrangement clip index {c_idx} out of range [0, {len(arr)})"
                )
            entry = arr[c_idx]
            clip = entry[0] if isinstance(entry, (tuple, list)) else entry
            tr.delete_clip(clip)
            return {
                "deleted": True,
                "track_index": t_idx,
                "clip_index": c_idx,
                "remaining_clips": len(list(getattr(tr, "arrangement_clips", []) or [])),
            }
        return {"deleted": True, "track_index": t_idx, "clip_index": c_idx}

    def live12_clip_fire(self, track_index: int, slot_index: int) -> Dict[str, Any]:
        t_idx = int(track_index)
        s_idx = int(slot_index)
        s = self.song()
        if s:
            if t_idx < 0 or t_idx >= len(s.tracks):
                raise IndexError(f"Track index {t_idx} out of range")
            tr = s.tracks[t_idx]
            if s_idx < 0 or s_idx >= len(tr.clip_slots):
                raise IndexError(f"Slot index {s_idx} out of range")
            slot = tr.clip_slots[s_idx]
            if not slot.clip:
                raise IndexError("Clip slot has no clip")
            slot.clip.fire()
        return {"fired": True, "is_playing": True, "track_index": t_idx, "slot_index": s_idx}

    def live12_clip_stop(self, track_index: int, slot_index: int) -> Dict[str, Any]:
        t_idx = int(track_index)
        s_idx = int(slot_index)
        s = self.song()
        if s:
            if t_idx < 0 or t_idx >= len(s.tracks):
                raise IndexError(f"Track index {t_idx} out of range")
            tr = s.tracks[t_idx]
            if s_idx < 0 or s_idx >= len(tr.clip_slots):
                raise IndexError(f"Slot index {s_idx} out of range")
            slot = tr.clip_slots[s_idx]
            if not slot.clip:
                raise IndexError("Clip slot has no clip")
            slot.clip.stop()
        return {"stopped": True, "is_playing": False, "track_index": t_idx, "slot_index": s_idx}

    def live12_clip_set_properties(
        self,
        track_index: int,
        slot_index: int,
        loop: Optional[bool] = None,
        loop_start: Optional[float] = None,
        loop_end: Optional[float] = None,
        start_marker: Optional[float] = None,
    ) -> Dict[str, Any]:
        t_idx = int(track_index)
        s_idx = int(slot_index)
        res: Dict[str, Any] = {"track_index": t_idx, "slot_index": s_idx}
        s = self.song()
        if s:
            if t_idx < 0 or t_idx >= len(s.tracks):
                raise IndexError(f"Track index {t_idx} out of range")
            tr = s.tracks[t_idx]
            if s_idx < 0 or s_idx >= len(tr.clip_slots):
                raise IndexError(f"Slot index {s_idx} out of range")
            clip = tr.clip_slots[s_idx].clip
            if not clip:
                raise IndexError("Clip slot has no clip")
            if loop is not None:
                if hasattr(clip, "looping"):
                    clip.looping = bool(loop)
                else:
                    clip.loop = bool(loop)
            if loop_start is not None and loop_end is not None:
                new_start = float(loop_start)
                new_end = float(loop_end)
                if new_start >= new_end:
                    raise ValueError(f"loop_start ({new_start}) must be less than loop_end ({new_end})")
                cur_end = float(getattr(clip, "loop_end", new_end))
                if new_start >= cur_end:
                    clip.loop_end = new_end
                    clip.loop_start = new_start
                else:
                    clip.loop_start = new_start
                    clip.loop_end = new_end
            elif loop_start is not None:
                clip.loop_start = float(loop_start)
            elif loop_end is not None:
                clip.loop_end = float(loop_end)
            if start_marker is not None:
                clip.start_marker = float(start_marker)
            loop_val = bool(clip.looping) if hasattr(clip, "looping") else bool(getattr(clip, "loop", False))
            res.update({
                "loop": loop_val,
                "looping": loop_val,
                "loop_start": clip.loop_start,
                "loop_end": clip.loop_end,
                "start_marker": clip.start_marker,
            })
        else:
            if loop is not None:
                res["loop"] = bool(loop)
                res["looping"] = bool(loop)
            if loop_start is not None:
                res["loop_start"] = float(loop_start)
            if loop_end is not None:
                res["loop_end"] = float(loop_end)
            if start_marker is not None:
                res["start_marker"] = float(start_marker)
        return res

    @staticmethod
    def _validate_note(n: Dict[str, Any]) -> None:
        if "pitch" not in n:
            raise ValueError("Note specification missing required field 'pitch'")
        pitch = int(n["pitch"])
        if not (0 <= pitch <= 127):
            raise ValueError(f"Pitch {pitch} out of range [0, 127]")

        if "duration" not in n:
            raise ValueError("Note specification missing required field 'duration'")
        dur = float(n["duration"])
        if math.isnan(dur) or math.isinf(dur) or dur <= 0.0:
            raise ValueError(f"Note duration must be positive (> 0.0), got {dur}")

        st = float(n.get("start_time", 0.0))
        if math.isnan(st) or math.isinf(st) or st < 0.0:
            raise ValueError(f"Note start_time must be non-negative (>= 0.0), got {st}")

        vel = float(n.get("velocity", 100.0))
        if math.isnan(vel) or math.isinf(vel) or not (0.0 <= vel <= 127.0):
            raise ValueError(f"Velocity {vel} out of range [0.0, 127.0]")

        rvel = float(n.get("release_velocity", 64.0))
        if math.isnan(rvel) or math.isinf(rvel) or not (0.0 <= rvel <= 127.0):
            raise ValueError(f"Release velocity {rvel} out of range [0.0, 127.0]")

        prob = float(n.get("probability", 1.0))
        if math.isnan(prob) or math.isinf(prob) or not (0.0 <= prob <= 1.0):
            raise ValueError(f"Probability {prob} out of range [0.0, 1.0]")

        v_dev = float(n.get("velocity_deviation", 0.0))
        if math.isnan(v_dev) or math.isinf(v_dev) or not (-127.0 <= v_dev <= 127.0):
            raise ValueError(f"Velocity deviation {v_dev} out of range [-127.0, 127.0]")

    _WRITABLE_MIDI_NOTE_ATTRS = frozenset({
        "pitch",
        "start_time",
        "duration",
        "velocity",
        "velocity_deviation",
        "release_velocity",
        "probability",
        "mute",
    })

    @staticmethod
    def _validate_note_modification(mod: Dict[str, Any]) -> None:
        for key in ("pitch", "new_pitch"):
            if key in mod:
                pitch = int(mod[key])
                if not (0 <= pitch <= 127):
                    raise ValueError(f"Pitch {pitch} out of range [0, 127]")

        if "duration" in mod:
            dur = float(mod["duration"])
            if math.isnan(dur) or math.isinf(dur) or dur <= 0.0:
                raise ValueError(f"Note duration must be positive (> 0.0), got {dur}")

        for key in ("start_time", "new_start_time"):
            if key in mod:
                st = float(mod[key])
                if math.isnan(st) or math.isinf(st) or st < 0.0:
                    raise ValueError(f"Note {key} must be non-negative (>= 0.0), got {st}")

        if "velocity" in mod:
            vel = float(mod["velocity"])
            if math.isnan(vel) or math.isinf(vel) or not (0.0 <= vel <= 127.0):
                raise ValueError(f"Velocity {vel} out of range [0.0, 127.0]")

        if "release_velocity" in mod:
            rvel = float(mod["release_velocity"])
            if math.isnan(rvel) or math.isinf(rvel) or not (0.0 <= rvel <= 127.0):
                raise ValueError(f"Release velocity {rvel} out of range [0.0, 127.0]")

        if "probability" in mod:
            prob = float(mod["probability"])
            if math.isnan(prob) or math.isinf(prob) or not (0.0 <= prob <= 1.0):
                raise ValueError(f"Probability {prob} out of range [0.0, 1.0]")

        if "velocity_deviation" in mod:
            v_dev = float(mod["velocity_deviation"])
            if math.isnan(v_dev) or math.isinf(v_dev) or not (-127.0 <= v_dev <= 127.0):
                raise ValueError(f"Velocity deviation {v_dev} out of range [-127.0, 127.0]")

    def live12_clip_add_notes(
        self,
        track_index: int,
        slot_index: int,
        notes: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        t_idx = int(track_index)
        s_idx = int(slot_index)
        for n in notes:
            self._validate_note(n)

        s = self.song()
        added_count = len(notes)
        note_ids: List[int] = []
        if s:
            if t_idx < 0 or t_idx >= len(s.tracks):
                raise IndexError(f"Track index {t_idx} out of range")
            tr = s.tracks[t_idx]
            if s_idx < 0 or s_idx >= len(tr.clip_slots):
                raise IndexError(f"Slot index {s_idx} out of range")
            clip = tr.clip_slots[s_idx].clip
            if not clip:
                raise IndexError("Clip slot has no clip")
            if getattr(clip, "is_audio_clip", False):
                raise ValueError("Cannot add MIDI notes to an audio clip")
            if added_count > 0:
                before_ids = None
                if hasattr(clip, "get_all_notes_extended"):
                    before_notes = list(clip.get_all_notes_extended())
                    before_ids = {
                        getattr(n, "note_id", None) for n in before_notes
                    } - {None}
                specs = [dict_to_midi_note_spec(n) for n in notes]
                clip.add_new_notes(tuple(specs))
                if before_ids is not None:
                    after_notes = list(clip.get_all_notes_extended())
                    note_ids = [
                        getattr(n, "note_id", i)
                        for i, n in enumerate(after_notes)
                        if getattr(n, "note_id", None) not in before_ids
                    ]
                else:
                    retrieved_notes = list(clip.get_notes_extended(0, 128, 0.0, 65536.0))
                    note_ids = [
                        getattr(n, "note_id", i) for i, n in enumerate(retrieved_notes)
                    ][-added_count:]
        else:
            note_ids = list(range(added_count))

        return {
            "status": "success",
            "added_count": added_count,
            "note_ids": note_ids,
        }

    def live12_clip_get_notes(
        self,
        track_index: int,
        slot_index: int,
        start_time: float = 0.0,
        time_span: float = 65536.0,
    ) -> Dict[str, Any]:
        t_idx = int(track_index)
        s_idx = int(slot_index)
        st = float(start_time)
        ts = float(time_span)
        if math.isnan(st) or math.isinf(st) or st < 0.0:
            raise ValueError(f"start_time must be non-negative, got {st}")
        if math.isnan(ts) or math.isinf(ts) or ts <= 0.0:
            raise ValueError(f"time_span must be positive, got {ts}")
        s = self.song()
        retrieved: List[Dict[str, Any]] = []
        if s:
            if t_idx < 0 or t_idx >= len(s.tracks):
                raise IndexError(f"Track index {t_idx} out of range")
            tr = s.tracks[t_idx]
            if s_idx < 0 or s_idx >= len(tr.clip_slots):
                raise IndexError(f"Slot index {s_idx} out of range")
            clip = tr.clip_slots[s_idx].clip
            if not clip:
                raise IndexError("Clip slot has no clip")
            if getattr(clip, "is_audio_clip", False):
                raise ValueError("Clip is an audio clip and has no MIDI notes")
            notes_raw = clip.get_notes_extended(0, 128, st, ts)
            for n in notes_raw:
                retrieved.append(midi_note_to_dict(n))

        return {
            "track_index": t_idx,
            "slot_index": s_idx,
            "notes": retrieved,
            "notes_count": len(retrieved),
        }

    def live12_clip_modify_notes(
        self,
        track_index: int,
        slot_index: int,
        note_modifications: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        t_idx = int(track_index)
        s_idx = int(slot_index)
        for mod in note_modifications:
            self._validate_note_modification(mod)

        s = self.song()
        modified_count = len(note_modifications)
        if s:
            if t_idx < 0 or t_idx >= len(s.tracks):
                raise IndexError(f"Track index {t_idx} out of range")
            tr = s.tracks[t_idx]
            if s_idx < 0 or s_idx >= len(tr.clip_slots):
                raise IndexError(f"Slot index {s_idx} out of range")
            clip = tr.clip_slots[s_idx].clip
            if not clip:
                raise IndexError("Clip slot has no clip")
            if getattr(clip, "is_audio_clip", False):
                raise ValueError("Clip is an audio clip and has no MIDI notes")
            if hasattr(clip, "get_all_notes_extended"):
                existing_notes = list(clip.get_all_notes_extended())
            else:
                span = max(float(getattr(clip, "length", 4.0) or 4.0), 65536.0)
                existing_notes = list(clip.get_notes_extended(0, 128, 0.0, span))

            modified_objs = []
            matched_indices: set = set()
            for mod in note_modifications:
                mod_id = mod.get("note_id")
                target_note = None
                target_idx: Optional[int] = None
                if mod_id is not None:
                    for idx, n in enumerate(existing_notes):
                        if getattr(n, "note_id", None) == mod_id:
                            target_note = n
                            target_idx = idx
                            break
                elif "pitch" in mod:
                    match_pitch = int(mod["pitch"])
                    if "start_time" in mod:
                        match_st = float(mod["start_time"])
                        for idx, n in enumerate(existing_notes):
                            if idx in matched_indices:
                                continue
                            if (
                                getattr(n, "pitch", None) == match_pitch
                                and abs(float(getattr(n, "start_time", -999.0)) - match_st) <= 1e-4
                            ):
                                target_note = n
                                target_idx = idx
                                break
                    else:
                        for idx, n in enumerate(existing_notes):
                            if idx in matched_indices:
                                continue
                            if getattr(n, "pitch", None) == match_pitch:
                                target_note = n
                                target_idx = idx
                                break
                elif "start_time" in mod:
                    match_st = float(mod["start_time"])
                    for idx, n in enumerate(existing_notes):
                        if idx in matched_indices:
                            continue
                        if abs(float(getattr(n, "start_time", -999.0)) - match_st) <= 1e-4:
                            target_note = n
                            target_idx = idx
                            break
                else:
                    for idx, n in enumerate(existing_notes):
                        if idx not in matched_indices:
                            target_note = n
                            target_idx = idx
                            break

                if target_note is not None:
                    if target_idx is not None:
                        matched_indices.add(target_idx)
                    updates: Dict[str, Any] = {}
                    for k, v in mod.items():
                        if k in self._WRITABLE_MIDI_NOTE_ATTRS:
                            updates[k] = v
                    if "new_pitch" in mod:
                        updates["pitch"] = int(mod["new_pitch"])
                    if "new_start_time" in mod:
                        updates["start_time"] = float(mod["new_start_time"])
                    for k, v in updates.items():
                        if hasattr(target_note, k):
                            setattr(target_note, k, v)
                    modified_objs.append(target_note)

            if modified_objs and hasattr(clip, "apply_note_modifications"):
                clip.apply_note_modifications(tuple(modified_objs))
            modified_count = len(modified_objs)

        return {"status": "success", "modified_count": modified_count}

    def live12_clip_quantize(
        self,
        track_index: int,
        slot_index: int,
        grid: float = 0.25,
        amount: float = 1.0,
    ) -> Dict[str, Any]:
        t_idx = int(track_index)
        s_idx = int(slot_index)
        g = float(grid)
        a = float(amount)
        if math.isnan(g) or math.isinf(g) or g <= 0.0:
            raise ValueError(f"Quantize grid must be positive, got {g}")
        if math.isnan(a) or math.isinf(a) or not (0.0 <= a <= 1.0):
            raise ValueError(f"Quantize amount must be in [0.0, 1.0], got {a}")
        s = self.song()
        if s:
            if t_idx < 0 or t_idx >= len(s.tracks):
                raise IndexError(f"Track index {t_idx} out of range")
            tr = s.tracks[t_idx]
            if s_idx < 0 or s_idx >= len(tr.clip_slots):
                raise IndexError(f"Slot index {s_idx} out of range")
            clip = tr.clip_slots[s_idx].clip
            if not clip:
                raise IndexError("Clip slot has no clip")
            if hasattr(clip, "quantize"):
                # Live RecordingQuantization values:
                # 1=quarter (1.0), 2=1/8 (0.5), 3=1/8T (1/3),
                # 5=1/16 (0.25), 6=1/16T (1/6), 8=1/32 (0.125)
                grid_map = (
                    (1.0, 1),
                    (0.5, 2),
                    (1.0 / 3.0, 3),
                    (0.25, 5),
                    (1.0 / 6.0, 6),
                    (0.125, 8),
                )
                grid_int = min(grid_map, key=lambda pair: abs(g - pair[0]))[1]
                clip.quantize(grid_int, a)
        return {"status": "quantized", "grid": g, "amount": a}

    _WARP_MODE_NAME_TO_INT = {
        "beats": 0,
        "tones": 1,
        "texture": 2,
        "re-pitch": 3,
        "repitch": 3,
        "complex": 4,
        "rex": 5,
        "complex pro": 6,
        "complex_pro": 6,
    }
    _WARP_MODE_INT_TO_NAME = {
        0: "Beats",
        1: "Tones",
        2: "Texture",
        3: "Re-Pitch",
        4: "Complex",
        5: "REX",
        6: "Complex Pro",
    }

    @staticmethod
    def _normalize_clip_gain(gain: float) -> float:
        g_val = float(gain)
        if math.isnan(g_val) or math.isinf(g_val) or g_val < -70.0 or g_val > 24.0:
            raise ValueError(f"gain {g_val} out of valid range [0.0, 1.0] or [-70.0, 24.0] dB")
        if 0.0 <= g_val <= 1.0:
            return g_val
        if g_val < 0.0:
            return max(0.0, min(1.0, 0.4 * (10.0 ** (g_val / 20.0))))
        # 1.0 < g_val <= 24.0: treat as positive dB gain boost mapped to Live's [0.4..1.0] range
        return max(0.0, min(1.0, 0.4 + (g_val / 24.0) * 0.6))

    def live12_audio_clip_set_warp(
        self,
        track_index: int,
        slot_index: int,
        warping: Optional[bool] = None,
        warp_mode: Optional[str] = None,
        pitch_shift: Optional[float] = None,
        gain: Optional[float] = None,
    ) -> Dict[str, Any]:
        t_idx = int(track_index)
        s_idx = int(slot_index)
        res: Dict[str, Any] = {"track_index": t_idx, "slot_index": s_idx}
        s = self.song()
        if s:
            if t_idx < 0 or t_idx >= len(s.tracks):
                raise IndexError(f"Track index {t_idx} out of range")
            tr = s.tracks[t_idx]
            if s_idx < 0 or s_idx >= len(tr.clip_slots):
                raise IndexError(f"Slot index {s_idx} out of range")
            clip = tr.clip_slots[s_idx].clip
            if not clip:
                raise IndexError("Clip slot has no clip")
            if not getattr(clip, "is_audio_clip", False):
                raise ValueError("Clip is not an audio clip")

            if warping is not None and hasattr(clip, "warping"):
                clip.warping = bool(warping)
            if warp_mode is not None and hasattr(clip, "warp_mode"):
                wm_key = str(warp_mode).strip().lower()
                if wm_key in self._WARP_MODE_NAME_TO_INT:
                    wm_int = self._WARP_MODE_NAME_TO_INT[wm_key]
                elif wm_key.isdigit() and int(wm_key) in self._WARP_MODE_INT_TO_NAME:
                    wm_int = int(wm_key)
                else:
                    raise ValueError(f"Invalid warp_mode {warp_mode!r}")
                clip.warp_mode = wm_int
            if pitch_shift is not None:
                ps = float(pitch_shift)
                if math.isnan(ps) or math.isinf(ps) or not (-48.0 <= ps <= 48.0):
                    raise ValueError(f"pitch_shift out of range [-48, 48]: {ps}")
                coarse = int(round(ps))
                fine_cents = int(round((ps - coarse) * 100.0))
                if hasattr(clip, "pitch_coarse"):
                    clip.pitch_coarse = coarse
                if hasattr(clip, "pitch_fine"):
                    clip.pitch_fine = fine_cents
            if gain is not None and hasattr(clip, "gain"):
                clip.gain = self._normalize_clip_gain(gain)

            raw_wm = getattr(clip, "warp_mode", 0)
            try:
                wm_str = self._WARP_MODE_INT_TO_NAME.get(int(raw_wm), str(raw_wm))
            except (TypeError, ValueError):
                wm_str = self._WARP_MODE_INT_TO_NAME.get(
                    self._WARP_MODE_NAME_TO_INT.get(str(raw_wm).strip().lower(), -1),
                    str(raw_wm),
                )
            actual_pitch = float(getattr(clip, "pitch_coarse", 0) or 0) + (
                float(getattr(clip, "pitch_fine", 0) or 0) / 100.0
            )
            res.update({
                "warping": bool(getattr(clip, "warping", True if warping is None else warping)),
                "warp_mode": wm_str,
                "pitch_shift": actual_pitch,
                "gain": float(getattr(clip, "gain", 1.0 if gain is None else clip.gain)),
            })
        else:
            if warping is not None:
                res["warping"] = bool(warping)
            if warp_mode is not None:
                wm_key = str(warp_mode).strip().lower()
                if wm_key in self._WARP_MODE_NAME_TO_INT:
                    res["warp_mode"] = self._WARP_MODE_INT_TO_NAME[self._WARP_MODE_NAME_TO_INT[wm_key]]
                elif wm_key.isdigit() and int(wm_key) in self._WARP_MODE_INT_TO_NAME:
                    res["warp_mode"] = self._WARP_MODE_INT_TO_NAME[int(wm_key)]
                else:
                    raise ValueError(f"Invalid warp_mode {warp_mode!r}")
            if pitch_shift is not None:
                res["pitch_shift"] = float(pitch_shift)
            if gain is not None:
                res["gain"] = self._normalize_clip_gain(gain)
        return res

    def live12_audio_clip_add_warp_marker(
        self,
        track_index: int,
        slot_index: int,
        beat_time: float,
        sample_time: float,
    ) -> Dict[str, Any]:
        t_idx = int(track_index)
        s_idx = int(slot_index)
        bt = float(beat_time)
        st = float(sample_time)
        if math.isnan(bt) or math.isinf(bt):
            raise ValueError(f"Invalid beat_time: {bt}")
        if math.isnan(st) or math.isinf(st):
            raise ValueError(f"Invalid sample_time: {st}")
        total_markers = 1
        s = self.song()
        if s:
            if t_idx < 0 or t_idx >= len(s.tracks):
                raise IndexError(f"Track index {t_idx} out of range")
            tr = s.tracks[t_idx]
            if s_idx < 0 or s_idx >= len(tr.clip_slots):
                raise IndexError(f"Slot index {s_idx} out of range")
            clip = tr.clip_slots[s_idx].clip
            if not clip:
                raise IndexError("Clip slot has no clip")
            if not getattr(clip, "is_audio_clip", False):
                raise ValueError("Clip is not an audio clip")
            if not hasattr(clip, "add_warp_marker"):
                raise RuntimeError("Clip object does not expose add_warp_marker")
            added = False
            if Live is not None and hasattr(Live, "Clip") and hasattr(Live.Clip, "WarpMarker"):
                try:
                    try:
                        marker_obj = Live.Clip.WarpMarker(beat_time=bt, sample_time=st)
                    except TypeError:
                        marker_obj = Live.Clip.WarpMarker(bt, st)
                    clip.add_warp_marker(marker_obj)
                    added = True
                except TypeError:
                    added = False
            if not added:
                try:
                    clip.add_warp_marker({"beat_time": bt, "sample_time": st})
                except TypeError:
                    try:
                        clip.add_warp_marker(bt, st)
                    except TypeError:
                        clip.add_warp_marker(bt)
            total_markers = len(getattr(clip, "warp_markers", ()) or ())
        return {
            "status": "added",
            "beat_time": bt,
            "sample_time": st,
            "total_warp_markers": total_markers,
        }

    def live12_clip_duplicate_to_arrangement(
        self,
        track_index: int,
        slot_index: int,
        arrangement_time: float,
    ) -> Dict[str, Any]:
        t_idx = int(track_index)
        s_idx = int(slot_index)
        arr_time = float(arrangement_time)
        if arr_time < 0.0 or math.isnan(arr_time) or math.isinf(arr_time):
            raise ValueError(f"arrangement_time must be non-negative, got {arr_time}")

        s = self.song()
        if s:
            if t_idx < 0 or t_idx >= len(s.tracks):
                raise IndexError(f"Track index {t_idx} out of range")
            tr = s.tracks[t_idx]
            if s_idx < 0 or s_idx >= len(tr.clip_slots):
                raise IndexError(f"Slot index {s_idx} out of range")
            clip = tr.clip_slots[s_idx].clip
            if not clip:
                raise IndexError("Clip slot has no clip")
            if hasattr(tr, "duplicate_clip_to_arrangement"):
                tr.duplicate_clip_to_arrangement(clip, arr_time)

        return {
            "status": "success",
            "success": True,
            "track_index": t_idx,
            "slot_index": s_idx,
            "arrangement_time": arr_time,
        }

    @staticmethod
    def _count_clip_notes(clip: Any) -> int:
        if hasattr(clip, "get_all_notes_extended"):
            return len(clip.get_all_notes_extended())
        if hasattr(clip, "get_notes_extended"):
            span = max(float(getattr(clip, "length", 4.0)), 65536.0)
            return len(clip.get_notes_extended(0, 128, 0.0, span))
        return len(getattr(clip, "notes", []))

    def live12_clip_remove_notes(
        self,
        track_index: int,
        slot_index: int,
        note_ids: Optional[List[int]] = None,
        start_time: Optional[float] = None,
        time_span: Optional[float] = None,
        from_pitch: Optional[int] = None,
        pitch_span: Optional[int] = None,
    ) -> Dict[str, Any]:
        t_idx = int(track_index)
        s_idx = int(slot_index)
        s = self.song()
        removed_count = 0
        if s:
            if t_idx < 0 or t_idx >= len(s.tracks):
                raise IndexError(f"Track index {t_idx} out of range")
            tr = s.tracks[t_idx]
            if s_idx < 0 or s_idx >= len(tr.clip_slots):
                raise IndexError(f"Slot index {s_idx} out of range")
            clip = tr.clip_slots[s_idx].clip
            if not clip:
                raise IndexError("Clip slot has no clip")
            if getattr(clip, "is_audio_clip", False):
                raise ValueError("Clip is an audio clip and has no MIDI notes")

            before_count = self._count_clip_notes(clip)
            if note_ids is not None:
                id_tuple = tuple(int(x) for x in note_ids)
                if hasattr(clip, "remove_notes_by_id"):
                    clip.remove_notes_by_id(id_tuple)
            else:
                st = float(start_time) if start_time is not None else 0.0
                ts = float(time_span) if time_span is not None else 65536.0
                fp = int(from_pitch) if from_pitch is not None else 0
                ps = int(pitch_span) if pitch_span is not None else 128
                if st < 0.0 or math.isnan(st) or math.isinf(st):
                    raise ValueError(f"start_time must be non-negative, got {st}")
                if ts <= 0.0 or math.isnan(ts) or math.isinf(ts):
                    raise ValueError(f"time_span must be positive, got {ts}")
                if not (0 <= fp <= 127) or ps < 1:
                    raise ValueError(f"Invalid pitch range from_pitch={fp}, pitch_span={ps}")
                if hasattr(clip, "remove_notes_extended"):
                    clip.remove_notes_extended(fp, ps, st, ts)
            after_count = self._count_clip_notes(clip)
            removed_count = max(0, before_count - after_count)

        return {
            "status": "success",
            "success": True,
            "track_index": t_idx,
            "slot_index": s_idx,
            "removed_count": removed_count,
        }

    _FALLBACK_SCALE_INTERVALS: Dict[str, Tuple[int, ...]] = {
        "major": (0, 2, 4, 5, 7, 9, 11),
        "minor": (0, 2, 3, 5, 7, 8, 10),
        "dorian": (0, 2, 3, 5, 7, 9, 10),
        "mixolydian": (0, 2, 4, 5, 7, 9, 10),
        "lydian": (0, 2, 4, 6, 7, 9, 11),
        "phrygian": (0, 1, 3, 5, 7, 8, 10),
        "locrian": (0, 1, 3, 5, 6, 8, 10),
        "whole tone": (0, 2, 4, 6, 8, 10),
        "half-whole dim.": (0, 1, 3, 4, 6, 7, 9, 10),
        "whole-half dim.": (0, 2, 3, 5, 6, 8, 9, 11),
        "diminished": (0, 1, 3, 4, 6, 7, 9, 10),
        "minor blues": (0, 3, 5, 6, 7, 10),
        "minor pentatonic": (0, 3, 5, 7, 10),
        "pentatonic": (0, 3, 5, 7, 10),
        "major pentatonic": (0, 2, 4, 7, 9),
        "harmonic minor": (0, 2, 3, 5, 7, 8, 11),
        "harmonic major": (0, 2, 4, 5, 7, 8, 11),
        "dorian #4": (0, 2, 3, 6, 7, 9, 10),
        "phrygian dominant": (0, 1, 4, 5, 7, 8, 10),
        "melodic minor": (0, 2, 3, 5, 7, 9, 11),
        "lydian augmented": (0, 2, 4, 6, 8, 9, 11),
        "lydian dominant": (0, 2, 4, 6, 7, 9, 10),
        "super locrian": (0, 1, 3, 4, 6, 8, 10),
        "bhairav": (0, 1, 4, 5, 7, 8, 11),
        "hungarian minor": (0, 2, 3, 6, 7, 8, 11),
        "8-tone spanish": (0, 1, 3, 4, 5, 6, 8, 10),
        "hirajoshi": (0, 2, 3, 7, 8),
        "in-sen": (0, 1, 5, 7, 10),
        "iwato": (0, 1, 5, 6, 10),
        "kumoi": (0, 2, 3, 7, 9),
        "pelog selisir": (0, 1, 3, 7, 8),
        "pelog tembung": (0, 1, 5, 7, 8),
        "messiaen 3": (0, 2, 3, 4, 6, 7, 8, 10, 11),
        "messiaen 4": (0, 1, 2, 5, 6, 7, 8, 11),
        "messiaen 5": (0, 1, 5, 6, 7, 11),
        "messiaen 6": (0, 2, 4, 5, 6, 8, 10, 11),
        "messiaen 7": (0, 1, 2, 3, 5, 6, 7, 8, 9, 11),
    }

    def _resolve_scale_intervals(self, s: Any, scale_name: str) -> set:
        raw_key = str(scale_name or "Minor").strip().lower()
        key = raw_key.replace("_", " ")
        alias = {"pentatonic": "minor pentatonic", "diminished": "half-whole dim."}.get(key, key)
        if s is not None and hasattr(s, "get_all_scales_ordered") and callable(s.get_all_scales_ordered):
            try:
                scales = s.get_all_scales_ordered() or ()
                scale_map = {
                    str(name).strip().lower().replace("_", " "): {int(iv) % 12 for iv in intervals}
                    for name, intervals in scales
                }
                for candidate in (key, raw_key, alias):
                    if candidate in scale_map:
                        return scale_map[candidate]
            except (RuntimeError, AttributeError, TypeError, ValueError):
                pass
        for candidate in (key, raw_key, alias):
            if candidate in self._FALLBACK_SCALE_INTERVALS:
                return set(self._FALLBACK_SCALE_INTERVALS[candidate])
        raise ValueError(f"Unknown scale name {scale_name!r}")

    def live12_clip_transform_midi(
        self,
        track_index: int,
        slot_index: int,
        transformation: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        t_idx = int(track_index)
        s_idx = int(slot_index)
        p = params or {}
        valid_transformations = ("humanize", "velocity_ramp", "euclidean", "arpeggiate", "quantize_pitch", "fit_to_scale")
        if transformation not in valid_transformations:
            raise ValueError(f"Invalid transformation '{transformation}', must be one of {valid_transformations}")

        s = self.song()
        notes_affected = 0
        if s:
            if t_idx < 0 or t_idx >= len(s.tracks):
                raise IndexError(f"Track index {t_idx} out of range")
            tr = s.tracks[t_idx]
            if s_idx < 0 or s_idx >= len(tr.clip_slots):
                raise IndexError(f"Slot index {s_idx} out of range")
            clip = tr.clip_slots[s_idx].clip
            if not clip:
                raise IndexError("Clip slot has no clip")
            if getattr(clip, "is_audio_clip", False):
                raise ValueError("Cannot apply MIDI transformation to an audio clip")

            max_span = max(float(getattr(clip, "length", 4.0)), 65536.0)
            if hasattr(clip, "get_notes_extended"):
                existing = list(clip.get_notes_extended(0, 128, 0.0, max_span))
            else:
                existing = list(getattr(clip, "notes", []))

            if transformation == "humanize":
                t_jitter = float(p.get("timing_jitter", 0.02))
                v_jitter = float(p.get("velocity_jitter", 8.0))
                for i, n in enumerate(existing):
                    delta_t = ((i * 17 + 7) % 11 - 5) / 5.0 * t_jitter
                    delta_v = ((i * 23 + 3) % 13 - 6) / 6.0 * v_jitter
                    if hasattr(n, "start_time"):
                        n.start_time = max(0.0, float(n.start_time) + delta_t)
                    if hasattr(n, "velocity"):
                        n.velocity = max(1.0, min(127.0, float(n.velocity) + delta_v))
                if existing and hasattr(clip, "apply_note_modifications"):
                    clip.apply_note_modifications(tuple(existing))
                notes_affected = len(existing)

            elif transformation == "velocity_ramp":
                v_start = float(p.get("start_velocity", 30.0))
                v_end = float(p.get("end_velocity", 110.0))
                if existing:
                    existing.sort(key=lambda n: getattr(n, "start_time", 0.0))
                    total = len(existing)
                    for i, n in enumerate(existing):
                        frac = i / float(max(1, total - 1))
                        n.velocity = max(1.0, min(127.0, v_start + frac * (v_end - v_start)))
                    if hasattr(clip, "apply_note_modifications"):
                        clip.apply_note_modifications(tuple(existing))
                    notes_affected = total

            elif transformation == "euclidean":
                steps = int(p.get("steps", 16))
                pulses = int(p.get("pulses", 4))
                pitch = int(p.get("pitch", 60))
                if steps < 1:
                    raise ValueError(f"Euclidean steps must be >= 1, got {steps}")
                if pulses < 0:
                    raise ValueError(f"Euclidean pulses must be >= 0, got {pulses}")
                if not (0 <= pitch <= 127):
                    raise ValueError(f"Euclidean pitch {pitch} out of range [0, 127]")
                clip_len = float(getattr(clip, "length", 4.0))
                if math.isnan(clip_len) or math.isinf(clip_len) or clip_len <= 0.0:
                    raise ValueError(f"Clip length must be positive for euclidean pattern, got {clip_len}")
                step_dur = clip_len / max(1, steps)
                pattern = [1 if (i * pulses) % steps < pulses else 0 for i in range(steps)]
                new_notes = []
                for i, hit in enumerate(pattern):
                    if hit:
                        new_notes.append({
                            "pitch": pitch,
                            "start_time": i * step_dur,
                            "duration": step_dur * 0.8,
                            "velocity": 100.0,
                        })
                if new_notes:
                    self.live12_clip_add_notes(t_idx, s_idx, new_notes)
                notes_affected = len(new_notes)

            elif transformation in ("quantize_pitch", "fit_to_scale"):
                scale_name = str(p.get("scale_name", "Minor"))
                root_note = int(p.get("root_note", 0))
                target_scale = self._resolve_scale_intervals(s, scale_name)
                for n in existing:
                    pitch = int(getattr(n, "pitch", 60))
                    degree = (pitch - root_note) % 12
                    if degree not in target_scale:
                        candidates = [
                            pitch + d - degree + octave_shift
                            for d in target_scale
                            for octave_shift in (-12, 0, 12)
                            if 0 <= pitch + d - degree + octave_shift <= 127
                        ]
                        if candidates:
                            n.pitch = min(candidates, key=lambda c: abs(c - pitch))
                if existing and hasattr(clip, "apply_note_modifications"):
                    clip.apply_note_modifications(tuple(existing))
                notes_affected = len(existing)

            elif transformation == "arpeggiate":
                rate = float(p.get("rate", 0.25))
                if math.isnan(rate) or math.isinf(rate) or rate <= 0.0:
                    raise ValueError(f"Arpeggiate rate must be positive, got {rate}")
                if existing:
                    existing.sort(key=lambda n: (getattr(n, "pitch", 60), getattr(n, "start_time", 0.0)))
                    if hasattr(clip, "apply_note_modifications"):
                        for i, n in enumerate(existing):
                            n.start_time = i * rate
                            n.duration = rate * 0.9
                        clip.apply_note_modifications(tuple(existing))
                    elif hasattr(clip, "remove_notes_extended") and hasattr(clip, "add_new_notes"):
                        arp_specs = []
                        for i, n in enumerate(existing):
                            d = midi_note_to_dict(n)
                            d["start_time"] = i * rate
                            d["duration"] = rate * 0.9
                            arp_specs.append(dict_to_midi_note_spec(d))
                        clip.remove_notes_extended(0, 128, 0.0, max_span)
                        clip.add_new_notes(tuple(arp_specs))
                    else:
                        for i, n in enumerate(existing):
                            n.start_time = i * rate
                            n.duration = rate * 0.9
                    notes_affected = len(existing)

        return {
            "status": "success",
            "success": True,
            "transformation": transformation,
            "notes_affected": notes_affected,
        }

    @staticmethod
    def _collect_track_parameters(tr: Any) -> List[Any]:
        """Collects mixer and device parameters on a track in deterministic order without duplicates."""
        params: List[Any] = []
        seen: set = set()
        mixer = getattr(tr, "mixer_device", None)
        if mixer is not None:
            for attr in ("volume", "panning", "track_activator"):
                p_obj = getattr(mixer, attr, None)
                if p_obj is not None and id(p_obj) not in seen:
                    seen.add(id(p_obj))
                    params.append(p_obj)
            for s_obj in getattr(mixer, "sends", []) or []:
                if s_obj is not None and id(s_obj) not in seen:
                    seen.add(id(s_obj))
                    params.append(s_obj)
        for dev in getattr(tr, "devices", []) or []:
            for p_obj in getattr(dev, "parameters", []) or []:
                if p_obj is not None and id(p_obj) not in seen:
                    seen.add(id(p_obj))
                    params.append(p_obj)
        return params

    @staticmethod
    def _resolve_track_parameter(
        tr: Any,
        device_index: Optional[int],
        parameter_identifier: Optional[Union[str, int]],
    ) -> Any:
        """Resolves a mixer or device parameter from a track for clip automation."""
        if parameter_identifier is None:
            return None

        mixer = getattr(tr, "mixer_device", None)
        if device_index is not None:
            d_idx = int(device_index)
            devices = getattr(tr, "devices", [])
            if d_idx < 0 or d_idx >= len(devices):
                raise IndexError(f"Device index {d_idx} out of range [0, {len(devices)})")
            dev = devices[d_idx]
            dev_params = getattr(dev, "parameters", [])
            if isinstance(parameter_identifier, int) or (isinstance(parameter_identifier, str) and parameter_identifier.isdigit()):
                p_idx = int(parameter_identifier)
                if 0 <= p_idx < len(dev_params):
                    return dev_params[p_idx]
                return None
            ident_l = str(parameter_identifier).strip().lower()
            for p_obj in dev_params:
                if getattr(p_obj, "name", "").lower() == ident_l:
                    return p_obj
            return None

        # device_index is None: check mixer aliases/names first, then track devices
        if isinstance(parameter_identifier, str) and not parameter_identifier.isdigit():
            ident_l = parameter_identifier.strip().lower()
            if mixer is not None:
                if ident_l in ("volume", "track volume"):
                    vol = getattr(mixer, "volume", None)
                    if vol is not None:
                        return vol
                elif ident_l in ("pan", "panning", "track panning"):
                    pan = getattr(mixer, "panning", None)
                    if pan is not None:
                        return pan
                elif ident_l in ("track activator", "speaker on", "mute"):
                    act = getattr(mixer, "track_activator", None)
                    if act is not None:
                        return act
                elif ident_l.startswith("send_") or ident_l.startswith("send "):
                    s_idx = BridgeHandlers._parse_send_index(ident_l.replace(" ", "_"))
                    sends = getattr(mixer, "sends", [])
                    if s_idx is not None and 0 <= s_idx < len(sends):
                        return sends[s_idx]
                for p_obj in BridgeHandlers._collect_track_parameters(tr):
                    if getattr(p_obj, "name", "").lower() == ident_l:
                        return p_obj

        devices = getattr(tr, "devices", [])
        if devices:
            dev = devices[0]
            dev_params = getattr(dev, "parameters", [])
            if isinstance(parameter_identifier, int) or (isinstance(parameter_identifier, str) and parameter_identifier.isdigit()):
                p_idx = int(parameter_identifier)
                if 0 <= p_idx < len(dev_params):
                    return dev_params[p_idx]
            else:
                ident_l = str(parameter_identifier).strip().lower()
                for d_obj in devices:
                    for p_obj in getattr(d_obj, "parameters", []):
                        if getattr(p_obj, "name", "").lower() == ident_l:
                            return p_obj
        elif mixer is not None and (isinstance(parameter_identifier, int) or (isinstance(parameter_identifier, str) and parameter_identifier.isdigit())):
            m_params = BridgeHandlers._collect_track_parameters(tr)
            p_idx = int(parameter_identifier)
            if 0 <= p_idx < len(m_params):
                return m_params[p_idx]

        return None

    def live12_clip_envelope_control(
        self,
        track_index: int,
        slot_index: int,
        action: str,
        device_index: Optional[int] = None,
        parameter_identifier: Optional[Union[str, int]] = None,
        time: Optional[float] = None,
        value: Optional[float] = None,
        parameter_index: Optional[Union[str, int]] = None,
        length: Optional[float] = None,
        normalized: bool = False,
    ) -> Dict[str, Any]:
        if parameter_identifier is None and parameter_index is not None:
            parameter_identifier = parameter_index
        t_idx = int(track_index)
        s_idx = int(slot_index)
        valid_actions = ("inspect", "create", "set_step", "insert_step", "clear", "clear_all", "re_enable")
        if action not in valid_actions:
            raise ValueError(f"Invalid envelope action '{action}', must be one of {valid_actions}")

        s = self.song()
        res: Dict[str, Any] = {"status": "success", "action": action, "track_index": t_idx, "slot_index": s_idx}
        if s:
            if t_idx < 0 or t_idx >= len(s.tracks):
                raise IndexError(f"Track index {t_idx} out of range")
            tr = s.tracks[t_idx]
            if s_idx < 0 or s_idx >= len(tr.clip_slots):
                raise IndexError(f"Slot index {s_idx} out of range")
            clip = tr.clip_slots[s_idx].clip
            if not clip:
                raise IndexError("Clip slot has no clip")

            target_param = None
            if action in ("create", "set_step", "insert_step", "clear") or (
                action == "re_enable" and parameter_identifier is not None
            ):
                target_param = self._resolve_track_parameter(tr, device_index, parameter_identifier)
                if target_param is None:
                    raise ValueError(
                        f"Parameter '{parameter_identifier}' could not be resolved on track {t_idx}"
                    )

            def _resolve_or_create_env(c_obj: Any, p_obj: Any) -> Any:
                if not p_obj:
                    return None
                env_obj = None
                if hasattr(c_obj, "automation_envelope"):
                    try:
                        env_obj = c_obj.automation_envelope(p_obj)
                    except (RuntimeError, ValueError):
                        env_obj = None
                if env_obj is None and hasattr(c_obj, "create_automation_envelope"):
                    env_obj = c_obj.create_automation_envelope(p_obj)
                if hasattr(c_obj, "view"):
                    try:
                        if hasattr(c_obj.view, "show_envelope"):
                            c_obj.view.show_envelope()
                        if hasattr(c_obj.view, "select_envelope_parameter"):
                            c_obj.view.select_envelope_parameter(p_obj)
                    except (RuntimeError, AttributeError):
                        pass
                return env_obj

            if action == "inspect":
                all_params = self._collect_track_parameters(tr)
                env_count = 0
                env_param_names: List[str] = []
                clip_has_env = getattr(clip, "has_envelopes", None)
                if hasattr(clip, "automation_envelope") and clip_has_env is not False:
                    for p_obj in all_params:
                        try:
                            env_found = clip.automation_envelope(p_obj)
                        except (RuntimeError, ValueError):
                            env_found = None
                        if env_found is not None:
                            env_count += 1
                            env_param_names.append(str(getattr(p_obj, "name", "")))
                has_env = bool(clip_has_env) if clip_has_env is not None else (env_count > 0)
                if clip_has_env is True and env_count == 0:
                    env_count = 1
                res["has_envelopes"] = has_env or (env_count > 0)
                res["envelopes_count"] = env_count
                if env_param_names:
                    res["envelope_parameters"] = env_param_names
            elif action == "create":
                env = _resolve_or_create_env(clip, target_param)
                res["envelope_created"] = env is not None
                res["parameter_name"] = getattr(target_param, "name", str(parameter_identifier))
            elif action in ("set_step", "insert_step"):
                step_time = float(time if time is not None else 0.0)
                step_len = float(length if length is not None else 0.25)
                step_val = float(value if value is not None else 1.0)
                if math.isnan(step_time) or math.isinf(step_time) or step_time < 0.0:
                    raise ValueError(f"Envelope step time must be non-negative, got {step_time}")
                if math.isnan(step_len) or math.isinf(step_len) or step_len <= 0.0:
                    raise ValueError(f"Envelope step length must be positive, got {step_len}")
                if math.isnan(step_val) or math.isinf(step_val):
                    raise ValueError(f"Envelope step value must be finite, got {step_val}")
                res["time"] = step_time
                res["length"] = step_len
                res["value"] = step_val
                env = _resolve_or_create_env(clip, target_param)
                if env is None:
                    raise RuntimeError(f"Failed to obtain automation envelope for '{getattr(target_param, 'name', parameter_identifier)}'")
                actual_val = step_val
                if hasattr(target_param, "min") and hasattr(target_param, "max"):
                    p_min = float(target_param.min)
                    p_max = float(target_param.max)
                    if normalized:
                        if step_val < 0.0 or step_val > 1.0:
                            raise ValueError(f"Normalized envelope value {step_val} out of range [0.0, 1.0]")
                        actual_val = p_min + step_val * (p_max - p_min)
                    else:
                        actual_val = max(p_min, min(p_max, step_val))
                if hasattr(env, "insert_step"):
                    try:
                        env.insert_step(step_time, step_len, actual_val)
                    except Exception:
                        if hasattr(env, "create_event"):
                            env.create_event(step_time, actual_val)
                        else:
                            raise
                elif hasattr(env, "create_event"):
                    env.create_event(step_time, actual_val)
                res["envelope_updated"] = True
                res["actual_value"] = actual_val
            elif action == "clear":
                if hasattr(clip, "clear_envelope"):
                    clip.clear_envelope(target_param)
                res["cleared_parameter"] = getattr(target_param, "name", str(parameter_identifier))
            elif action == "clear_all":
                if hasattr(clip, "clear_all_envelopes"):
                    clip.clear_all_envelopes()
                res["all_cleared"] = True
            elif action == "re_enable":
                if target_param is not None and hasattr(target_param, "re_enable_automation"):
                    target_param.re_enable_automation()
                elif hasattr(s, "re_enable_automation"):
                    s.re_enable_automation()
                res["automation_re_enabled"] = True

        return res

    def live12_groove_pool_control(
        self,
        action: str,
        groove_index: Optional[int] = None,
        amount: Optional[float] = None,
        track_index: Optional[int] = None,
        slot_index: Optional[int] = None,
    ) -> Dict[str, Any]:
        valid_actions = ("list_pool", "set_song_amount", "assign_clip", "clear_clip", "get_clip_groove")
        if action not in valid_actions:
            raise ValueError(f"Invalid groove action '{action}', must be one of {valid_actions}")

        s = self.song()
        res: Dict[str, Any] = {"status": "success", "action": action}
        gp = getattr(s, "groove_pool", None) if s else None

        if action == "list_pool":
            grooves_list = []
            if gp and hasattr(gp, "grooves"):
                for i, g in enumerate(gp.grooves):
                    grooves_list.append({
                        "index": i,
                        "name": str(getattr(g, "name", f"Groove {i}")),
                        "base": str(getattr(g, "base", "1/16")),
                        "timing_amount": float(getattr(g, "timing_amount", 0.5)),
                        "velocity_amount": float(getattr(g, "velocity_amount", 0.5)),
                        "quantization_amount": float(getattr(g, "quantization_amount", 1.0)),
                        "random_amount": float(getattr(g, "random_amount", 0.0)),
                    })
            res["grooves"] = grooves_list
            res["song_groove_amount"] = float(getattr(s, "groove_amount", 0.0)) if s else 0.75

        elif action == "set_song_amount":
            amt = float(amount if amount is not None else 1.0)
            if amt < 0.0 or amt > 1.0 or math.isnan(amt) or math.isinf(amt):
                raise ValueError("amount must be between 0.0 and 1.0")
            if s and hasattr(s, "groove_amount"):
                s.groove_amount = amt
            res["groove_amount"] = float(getattr(s, "groove_amount", amt)) if s else amt

        elif action == "assign_clip":
            t_idx = int(track_index if track_index is not None else 0)
            s_idx = int(slot_index if slot_index is not None else 0)
            g_idx = int(groove_index if groove_index is not None else 0)
            if s:
                if t_idx < 0 or t_idx >= len(s.tracks):
                    raise IndexError(f"Track index {t_idx} out of range")
                tr = s.tracks[t_idx]
                if s_idx < 0 or s_idx >= len(tr.clip_slots):
                    raise IndexError(f"Slot index {s_idx} out of range")
                clip = tr.clip_slots[s_idx].clip
                if not clip:
                    raise IndexError("Clip slot has no clip")
                grooves = list(getattr(gp, "grooves", [])) if gp else []
                if g_idx < 0 or g_idx >= len(grooves):
                    raise IndexError(f"Groove index {g_idx} out of range [0, {len(grooves)})")
                clip.groove = grooves[g_idx]
                res["groove_name"] = str(getattr(grooves[g_idx], "name", f"Groove {g_idx}"))
            res["track_index"] = t_idx
            res["slot_index"] = s_idx
            res["assigned_groove_index"] = g_idx

        elif action == "clear_clip":
            t_idx = int(track_index if track_index is not None else 0)
            s_idx = int(slot_index if slot_index is not None else 0)
            if s:
                if t_idx < 0 or t_idx >= len(s.tracks):
                    raise IndexError(f"Track index {t_idx} out of range")
                tr = s.tracks[t_idx]
                if s_idx < 0 or s_idx >= len(tr.clip_slots):
                    raise IndexError(f"Slot index {s_idx} out of range")
                clip = tr.clip_slots[s_idx].clip
                if not clip:
                    raise IndexError("Clip slot has no clip")
                if hasattr(clip, "groove"):
                    clip.groove = None
            res["track_index"] = t_idx
            res["slot_index"] = s_idx

        elif action == "get_clip_groove":
            t_idx = int(track_index if track_index is not None else 0)
            s_idx = int(slot_index if slot_index is not None else 0)
            has_gr = False
            gr_name = None
            if s:
                if t_idx < 0 or t_idx >= len(s.tracks):
                    raise IndexError(f"Track index {t_idx} out of range")
                tr = s.tracks[t_idx]
                if s_idx < 0 or s_idx >= len(tr.clip_slots):
                    raise IndexError(f"Slot index {s_idx} out of range")
                clip = tr.clip_slots[s_idx].clip
                if not clip:
                    raise IndexError("Clip slot has no clip")
                gr = getattr(clip, "groove", None)
                has_gr = (gr is not None)
                gr_name = getattr(gr, "name", str(gr)) if gr else None
            res["has_groove"] = has_gr
            res["groove_name"] = gr_name

        return res

    # -------------------------------------------------------------------------
    # Domain 4: Browser, Devices, Specialized Instruments & Effects, Parameters
    # -------------------------------------------------------------------------

    _DEVICE_NAME_ALIASES: Dict[str, str] = {
        "auto pan": "auto pan-tremolo",
        "chorus": "chorus-ensemble",
        "redux legacy": "redux",
    }

    _BROWSER_ALL_CATEGORIES = (
        "instruments",
        "audio_effects",
        "midi_effects",
        "drums",
        "sounds",
        "max_for_live",
        "plugins",
        "user_library",
        "packs",
        "samples",
        "clips",
        "current_project",
    )

    _BROWSER_CATEGORY_MAP = {
        "instruments": ("instruments",),
        "audio_effects": ("audio_effects",),
        "midi_effects": ("midi_effects",),
        "drums": ("drums",),
        "sounds": ("sounds",),
        "samples": ("samples",),
        "packs": ("packs",),
        "user_library": ("user_library",),
        "plugins": ("plugins",),
        "max": ("max_for_live",),
        "max_for_live": ("max_for_live",),
        "clips": ("clips",),
        "current_project": ("current_project",),
    }

    @staticmethod
    def _is_browser_item_valid(item: Any) -> bool:
        if item is None or not liveobj_valid(item):
            return False
        try:
            _ = getattr(item, "name", "")
            _ = getattr(item, "is_loadable", True)
        except (AttributeError, RuntimeError, ReferenceError):
            return False
        return True

    def live12_browser_search(self, query: str, category: str = "all") -> Dict[str, Any]:
        q_raw = str(query or "").strip()
        if not q_raw:
            raise ValueError("Browser search query must not be empty")
        q_clean = q_raw.lower()
        cat_clean = str(category or "all").strip().lower()
        if cat_clean == "all":
            target_cats = self._BROWSER_ALL_CATEGORIES
        elif cat_clean in self._BROWSER_CATEGORY_MAP:
            target_cats = self._BROWSER_CATEGORY_MAP[cat_clean]
        else:
            raise ValueError(f"Unknown browser category {category!r}")

        app = self.application()
        browser = getattr(app, "browser", None) if app else None
        q_alias = self._DEVICE_NAME_ALIASES.get(q_clean, q_clean)
        items: List[Dict[str, Any]] = []
        seen_keys = set()
        nodes_visited = 0

        if browser:
            queue = collections.deque()
            for cat_name in target_cats:
                root = getattr(browser, cat_name, None)
                if root is not None:
                    queue.append((root, 0))

            while queue and len(items) < 50 and nodes_visited < MAX_BROWSER_SEARCH_NODES:
                node, depth = queue.popleft()
                nodes_visited += 1
                if depth > 0:
                    c_name = str(getattr(node, "name", "") or "")
                    c_uri = str(getattr(node, "uri", "") or c_name)
                    if (
                        q_clean in c_name.lower()
                        or q_alias in c_name.lower()
                        or q_clean in c_uri.lower()
                    ):
                        dedup_key = (c_uri, c_name)
                        if dedup_key not in seen_keys:
                            seen_keys.add(dedup_key)
                            items.append({
                                "name": c_name,
                                "uri": c_uri,
                                "is_loadable": bool(getattr(node, "is_loadable", True)),
                            })
                            if len(items) >= 50:
                                break
                if depth < 5 and hasattr(node, "children") and (
                    depth == 0 or getattr(node, "is_folder", False) or getattr(node, "children", None)
                ):
                    for child in getattr(node, "children", ()) or ():
                        queue.append((child, depth + 1))

        return {
            "query": query,
            "category": category,
            "results_count": len(items),
            "count": len(items),
            "items": items,
            "results": items,
        }

    def _find_browser_item(self, browser: Any, target_uri: str, max_depth: int = 5) -> Any:
        """Finds a loadable BrowserItem matching URI, LOM path, or name in the browser hierarchy."""
        if not browser:
            return None
        target_str = str(target_uri).strip()
        if not target_str:
            return None
        if target_str.startswith(("live_app.browser.", "app.browser.", "application.browser.")):
            try:
                resolved = resolve_path(self.root_getter, target_str)
                if resolved is not None and self._is_browser_item_valid(resolved):
                    return resolved
            except (AttributeError, KeyError, IndexError, ValueError):
                pass
        target_clean = target_str.lower()
        short_target = target_clean.split(":")[-1].replace("_", " ")
        short_target = self._DEVICE_NAME_ALIASES.get(short_target, short_target)
        target_clean_alias = self._DEVICE_NAME_ALIASES.get(target_clean, target_clean)

        if not hasattr(self, "_top_device_cache"):
            self._top_device_cache: Dict[str, Any] = {}

        for cache_key in (target_clean, target_clean_alias, short_target):
            if cache_key and cache_key in self._top_device_cache:
                cached = self._top_device_cache[cache_key]
                if self._is_browser_item_valid(cached):
                    return cached
                self._top_device_cache.pop(cache_key, None)

        core_device_cats = ("instruments", "audio_effects", "midi_effects")

        # Pass 1: Direct children (depth=1) of core device categories
        core_depth1_items = []
        for cat in core_device_cats:
            root = getattr(browser, cat, None)
            if not root:
                continue
            for child in getattr(root, "children", ()) or ():
                c_uri = (getattr(child, "uri", "") or "").lower()
                c_name = (getattr(child, "name", "") or "").lower()
                if getattr(child, "is_loadable", True):
                    if c_name:
                        self._top_device_cache[c_name] = child
                    if c_uri:
                        self._top_device_cache[c_uri] = child
                if c_uri in (target_clean, target_clean_alias) or (
                    c_name and c_name in (target_clean, target_clean_alias, short_target)
                ):
                    if getattr(child, "is_loadable", True):
                        return child
                core_depth1_items.append(child)

        # Pass 2: Presets inside core device categories (depth 2..max_depth), capped at half budget
        pass2_limit = max(1, MAX_BROWSER_SEARCH_NODES // 2)
        pass2_visited = 0
        queue = collections.deque((child, 1) for child in core_depth1_items)
        while queue and pass2_visited < pass2_limit:
            item, depth = queue.popleft()
            pass2_visited += 1
            if depth >= max_depth:
                continue
            for child in getattr(item, "children", ()) or ():
                c_uri = (getattr(child, "uri", "") or "").lower()
                c_name = (getattr(child, "name", "") or "").lower()
                if c_uri in (target_clean, target_clean_alias) or (
                    c_name and c_name in (target_clean, target_clean_alias, short_target)
                ):
                    if getattr(child, "is_loadable", True):
                        return child
                if depth + 1 < max_depth and (
                    getattr(child, "is_folder", False) or bool(getattr(child, "children", None))
                ):
                    queue.append((child, depth + 1))

        # Pass 3: Fallback categories with reserved budget and fair round-robin scheduling
        # so huge trees (e.g., drums/sounds) cannot starve samples, plugins, user_library, or packs.
        pass3_budget = max(MAX_BROWSER_SEARCH_NODES // 2, MAX_BROWSER_SEARCH_NODES - pass2_visited)
        pass3_visited = 0
        slow_cats = (
            "drums",
            "sounds",
            "max_for_live",
            "plugins",
            "user_library",
            "packs",
            "samples",
            "clips",
            "current_project",
        )
        active_queues: List[collections.deque] = []
        for cat in slow_cats:
            root = getattr(browser, cat, None)
            if root is not None:
                active_queues.append(collections.deque([(root, 0)]))

        while active_queues and pass3_visited < pass3_budget:
            next_round: List[collections.deque] = []
            for q_slow in active_queues:
                if pass3_visited >= pass3_budget:
                    break
                if not q_slow:
                    continue
                item, depth = q_slow.popleft()
                pass3_visited += 1
                item_uri = (getattr(item, "uri", "") or "").lower()
                item_name = (getattr(item, "name", "") or "").lower()
                if item_uri in (target_clean, target_clean_alias) or (
                    item_name and item_name in (target_clean, target_clean_alias, short_target)
                ):
                    if getattr(item, "is_loadable", True):
                        return item
                if depth < max_depth and (
                    getattr(item, "is_folder", False) or bool(getattr(item, "children", None))
                ):
                    for child in getattr(item, "children", ()) or ():
                        c_uri = (getattr(child, "uri", "") or "").lower()
                        c_name = (getattr(child, "name", "") or "").lower()
                        if c_uri in (target_clean, target_clean_alias) or (
                            c_name and c_name in (target_clean, target_clean_alias, short_target)
                        ):
                            if getattr(child, "is_loadable", True):
                                return child
                        if depth + 1 < max_depth and (
                            getattr(child, "is_folder", False) or bool(getattr(child, "children", None))
                        ):
                            q_slow.append((child, depth + 1))
                if q_slow:
                    next_round.append(q_slow)
            active_queues = next_round
        return None

    def live12_browser_load_item(
        self,
        track_index: int,
        browser_item_uri: str,
        track_type: str = "regular",
        chain_index: int = -1,
        drum_pad_index: int = -1,
    ) -> Dict[str, Any]:
        t_idx = int(track_index)
        c_idx = int(chain_index)
        dp_idx = int(drum_pad_index)
        if dp_idx != -1 and not (0 <= dp_idx <= 127):
            raise IndexError(f"drum_pad_index {dp_idx} out of range [0, 127]")
        if c_idx < -1:
            raise IndexError(f"chain_index {c_idx} must be >= -1")

        s = self.song()
        if s:
            if t_idx == -100 and track_type == "regular":
                track_type = "master"
            target_track = self._resolve_target_track(s, t_idx, track_type)
            if hasattr(s, "view") and hasattr(s.view, "selected_track"):
                s.view.selected_track = target_track

            drum_rack = None
            if dp_idx >= 0:
                drum_rack = next(
                    (
                        d
                        for d in getattr(target_track, "devices", ()) or ()
                        if getattr(d, "can_have_drum_pads", False)
                    ),
                    None,
                )
                if drum_rack is None:
                    raise ValueError("Target track does not contain a Drum Rack for drum_pad_index")
                drum_pads = getattr(drum_rack, "drum_pads", ()) or ()
                if dp_idx >= len(drum_pads):
                    raise IndexError(f"drum_pad_index {dp_idx} out of range (0..{len(drum_pads) - 1})")
                pad = drum_pads[dp_idx]
                if hasattr(s, "view") and hasattr(s.view, "select_device"):
                    s.view.select_device(drum_rack)
                if hasattr(drum_rack, "view"):
                    if hasattr(drum_rack.view, "selected_drum_pad"):
                        drum_rack.view.selected_drum_pad = pad
                    pad_chains = getattr(pad, "chains", ()) or ()
                    if pad_chains and hasattr(drum_rack.view, "selected_chain"):
                        drum_rack.view.selected_chain = pad_chains[0]
            elif c_idx >= 0:
                rack = next(
                    (
                        d
                        for d in getattr(target_track, "devices", ()) or ()
                        if getattr(d, "can_have_chains", False)
                    ),
                    None,
                )
                if rack is None:
                    raise ValueError("Target track does not contain a Rack device for chain_index")
                chains = getattr(rack, "chains", ()) or ()
                if c_idx >= len(chains):
                    raise IndexError(f"chain_index {c_idx} out of range (0..{len(chains) - 1})")
                if hasattr(s, "view") and hasattr(s.view, "select_device"):
                    s.view.select_device(rack)
                if hasattr(rack, "view") and hasattr(rack.view, "selected_chain"):
                    rack.view.selected_chain = chains[c_idx]

            app = self.application()
            browser = getattr(app, "browser", None) if app else None
            if browser and hasattr(browser, "load_item"):
                if hasattr(browser_item_uri, "is_loadable"):
                    item = browser_item_uri
                else:
                    item = self._find_browser_item(browser, str(browser_item_uri))
                if item is None:
                    raise ValueError(f"Browser item '{browser_item_uri}' not found in browser")
                if not getattr(item, "is_loadable", True):
                    raise ValueError(f"Browser item '{browser_item_uri}' is not loadable")
                browser.load_item(item)
                if drum_rack is not None and drum_rack not in (getattr(target_track, "devices", ()) or ()):
                    raise RuntimeError(
                        "Browser load_item replaced or removed the Drum Rack instead of loading into the selected pad"
                    )

        res: Dict[str, Any] = {
            "status": "loaded",
            "track_index": t_idx,
            "track_type": track_type,
            "browser_item_uri": browser_item_uri,
        }
        if dp_idx >= 0:
            res["drum_pad_index"] = dp_idx
        if c_idx >= 0:
            res["chain_index"] = c_idx
        return res

    _DEVICE_TYPE_INT_TO_STR = {
        0: "undefined",
        1: "instrument",
        2: "audio_effect",
        4: "midi_effect",
    }

    @classmethod
    def _normalize_device_type(cls, raw_type: Any) -> str:
        if raw_type is None:
            return "instrument"
        if isinstance(raw_type, bool):
            return "instrument" if raw_type else "undefined"
        if isinstance(raw_type, int):
            return cls._DEVICE_TYPE_INT_TO_STR.get(raw_type, "undefined")
        name_attr = getattr(raw_type, "name", None)
        if isinstance(name_attr, str) and name_attr.lower() in ("undefined", "instrument", "audio_effect", "midi_effect"):
            return name_attr.lower()
        try:
            as_int = int(raw_type)
            if as_int in cls._DEVICE_TYPE_INT_TO_STR:
                return cls._DEVICE_TYPE_INT_TO_STR[as_int]
        except (TypeError, ValueError):
            pass
        s_val = str(raw_type).strip().lower()
        if s_val.startswith("devicetype."):
            s_val = s_val.split(".", 1)[1]
        if s_val in ("undefined", "instrument", "audio_effect", "midi_effect"):
            return s_val
        return str(raw_type)

    def live12_device_list(self, track_index: int, track_type: str = "regular") -> Dict[str, Any]:
        t_idx = int(track_index)
        s = self.song()
        devs: List[Dict[str, Any]] = []
        if s:
            tr = self._resolve_target_track(s, t_idx, track_type)
            for i, d in enumerate(getattr(tr, "devices", [])):
                devs.append({
                    "index": i,
                    "name": d.name,
                    "type": self._normalize_device_type(getattr(d, "type", "instrument")),
                    "is_active": getattr(d, "is_active", True),
                    "can_have_chains": getattr(d, "can_have_chains", False),
                    "parameters_count": len(getattr(d, "parameters", [])),
                })
        res: Dict[str, Any] = {"track_index": t_idx, "devices": devs}
        if track_type != "regular":
            res["track_type"] = track_type
        return res

    def live12_device_get_parameters(
        self,
        track_index: int,
        device_index: int,
        track_type: str = "regular",
    ) -> Dict[str, Any]:
        t_idx = int(track_index)
        d_idx = int(device_index)
        s = self.song()
        params: List[Dict[str, Any]] = []
        if s:
            tr = self._resolve_target_track(s, t_idx, track_type)
            devices = getattr(tr, "devices", ()) or ()
            if d_idx < 0 or d_idx >= len(devices):
                raise IndexError(f"Device index {d_idx} out of range (0..{len(devices) - 1})")
            dev = devices[d_idx]
            for i, p in enumerate(getattr(dev, "parameters", [])):
                min_v = float(p.min)
                max_v = float(p.max)
                val = float(p.value)
                norm = (val - min_v) / (max_v - min_v) if max_v > min_v else 0.0
                params.append({
                    "index": i,
                    "name": p.name,
                    "value": val,
                    "min": min_v,
                    "max": max_v,
                    "is_quantized": getattr(p, "is_quantized", False),
                    "normalized_value": norm,
                })
        res: Dict[str, Any] = {
            "track_index": t_idx,
            "device_index": d_idx,
            "parameters": params,
        }
        if track_type != "regular":
            res["track_type"] = track_type
        return res

    def live12_device_set_parameter(
        self,
        track_index: int,
        device_index: int,
        parameter_identifier: Optional[Union[str, int]] = None,
        value: Union[float, str] = 0.0,
        normalized: bool = False,
        parameter_index: Optional[Union[str, int]] = None,
        track_type: str = "regular",
    ) -> Dict[str, Any]:
        if parameter_identifier is None and parameter_index is not None:
            parameter_identifier = parameter_index
        t_idx = int(track_index)
        d_idx = int(device_index)
        s = self.song()
        if s:
            tr = self._resolve_target_track(s, t_idx, track_type)
            devices = getattr(tr, "devices", ()) or ()
            if d_idx < 0 or d_idx >= len(devices):
                raise IndexError(f"Device index {d_idx} out of range (0..{len(devices) - 1})")
            dev = devices[d_idx]

            param = None
            if (isinstance(parameter_identifier, int) and not isinstance(parameter_identifier, bool)) or (
                isinstance(parameter_identifier, str) and parameter_identifier.isdigit()
            ):
                p_idx = int(parameter_identifier)
                if 0 <= p_idx < len(dev.parameters):
                    param = dev.parameters[p_idx]
            else:
                for p in dev.parameters:
                    if p.name == str(parameter_identifier) or p.name.lower() == str(parameter_identifier).lower():
                        param = p
                        break

            if not param:
                raise IndexError(f"Parameter '{parameter_identifier}' not found on device")

            if isinstance(value, bool):
                raise ValueError(f"Boolean value {value!r} is invalid for parameter '{param.name}'")

            min_v = float(param.min)
            max_v = float(param.max)
            is_quantized = bool(getattr(param, "is_quantized", False))

            actual_val: Optional[float] = None
            if isinstance(value, str):
                val_stripped = value.strip()
                if is_quantized:
                    raw_items = list(getattr(param, "value_items", ()) or ())
                    items_lower = [str(x).strip().lower() for x in raw_items]
                    if val_stripped.lower() in items_lower:
                        actual_val = min_v + float(items_lower.index(val_stripped.lower()))
                if actual_val is None:
                    try:
                        val_f = float(val_stripped)
                    except ValueError:
                        if is_quantized:
                            raw_items = list(getattr(param, "value_items", ()) or ())
                            raise ValueError(
                                f"Invalid quantized value {value!r} for parameter '{param.name}'"
                                + (f" (valid: {raw_items})" if raw_items else "")
                            )
                        raise ValueError(
                            f"Non-numeric string {value!r} cannot be assigned to continuous parameter '{param.name}'"
                        )
                    if math.isnan(val_f) or math.isinf(val_f):
                        raise ValueError(f"Parameter value must be finite, got {value!r}")
                    actual_val = min_v + val_f * (max_v - min_v) if normalized else val_f
            else:
                val_f = float(value)
                if math.isnan(val_f) or math.isinf(val_f):
                    raise ValueError(f"Parameter value must be finite, got {value!r}")
                actual_val = min_v + val_f * (max_v - min_v) if normalized else val_f

            actual_val = max(min_v, min(max_v, actual_val))
            param.value = actual_val
            norm = (param.value - min_v) / (max_v - min_v) if max_v > min_v else 0.0
            res_dict: Dict[str, Any] = {
                "track_index": t_idx,
                "device_index": d_idx,
                "parameter_name": param.name,
                "value": param.value,
                "normalized_value": norm,
            }
            if track_type != "regular":
                res_dict["track_type"] = track_type
            return res_dict

        if isinstance(value, bool):
            raise ValueError(f"Boolean value {value!r} is invalid for parameter '{parameter_identifier}'")
        try:
            val_out = float(value)
            if math.isnan(val_out) or math.isinf(val_out):
                raise ValueError(f"Parameter value must be finite, got {value!r}")
        except (TypeError, ValueError):
            if isinstance(value, str):
                val_out = 0.0
            else:
                raise
        return {
            "track_index": t_idx,
            "device_index": d_idx,
            "parameter_name": str(parameter_identifier),
            "value": val_out,
            "normalized_value": 0.5,
        }

    def live12_device_toggle(
        self,
        track_index: int,
        device_index: int,
        enabled: bool,
        track_type: str = "regular",
    ) -> Dict[str, Any]:
        t_idx = int(track_index)
        d_idx = int(device_index)
        en = bool(enabled)
        s = self.song()
        if s:
            tr = self._resolve_target_track(s, t_idx, track_type)
            devices = getattr(tr, "devices", ()) or ()
            if d_idx < 0 or d_idx >= len(devices):
                raise IndexError(f"Device index {d_idx} out of range (0..{len(devices) - 1})")
            dev = devices[d_idx]
            if not getattr(dev, "parameters", None):
                raise RuntimeError(f"Device at index {d_idx} exposes no parameters")
            dev.parameters[0].value = 1.0 if en else 0.0
        res: Dict[str, Any] = {"track_index": t_idx, "device_index": d_idx, "is_active": en}
        if track_type != "regular":
            res["track_type"] = track_type
        return res

    def live12_rack_macro_control(
        self,
        track_index: int,
        device_index: int,
        macro_index: int,
        value: float,
    ) -> Dict[str, Any]:
        t_idx = int(track_index)
        d_idx = int(device_index)
        m_idx = int(macro_index)
        val = float(value)
        if m_idx < 0 or m_idx > 15:
            raise IndexError(f"Macro index {m_idx} out of range [0, 15]")
        if math.isnan(val) or math.isinf(val) or not (0.0 <= val <= 1.0):
            raise ValueError(f"Macro normalized value must be in [0.0, 1.0], got {val}")

        macro_name = f"Macro {m_idx + 1}"
        raw_val = val
        s = self.song()
        if s:
            if t_idx < 0 or t_idx >= len(s.tracks):
                raise IndexError(f"Track index {t_idx} out of range")
            tr = s.tracks[t_idx]
            devices = getattr(tr, "devices", ()) or ()
            if d_idx < 0 or d_idx >= len(devices):
                raise IndexError(f"Device index {d_idx} out of range (0..{len(devices) - 1})")
            dev = devices[d_idx]
            if hasattr(dev, "can_have_chains") and not getattr(dev, "can_have_chains", False):
                raise ValueError(f"Device '{getattr(dev, 'name', d_idx)}' is not a Rack device")
            params = list(getattr(dev, "parameters", ()) or ())
            # Parameter 0 on RackDevice is "Device On"; Macros occupy indices 1..16
            target_param_idx = m_idx + 1
            if target_param_idx >= len(params):
                raise IndexError(
                    f"Macro index {m_idx} out of range for device with {len(params)} parameters"
                )
            p = params[target_param_idx]
            p_min = float(getattr(p, "min", 0.0))
            p_max = float(getattr(p, "max", 127.0))
            target_raw = max(p_min, min(p_max, p_min + val * (p_max - p_min)))
            p.value = target_raw
            macro_name = str(getattr(p, "name", macro_name))
            raw_val = float(p.value)

        return {
            "track_index": t_idx,
            "device_index": d_idx,
            "macro_index": m_idx,
            "macro_name": macro_name,
            "value": val,
            "raw_value": raw_val,
        }

    def live12_rack_variation_control(
        self,
        track_index: int,
        device_index: int,
        action: str,
        variation_index: int = 0,
    ) -> Dict[str, Any]:
        t_idx = int(track_index)
        d_idx = int(device_index)
        act = str(action).strip().lower()
        if act not in ("store", "recall", "delete", "randomize"):
            raise ValueError(f"Unsupported rack variation action {action!r}")
        v_idx = int(variation_index)

        def _extract_normalized_macros(rack_dev: Any) -> List[float]:
            params = list(getattr(rack_dev, "parameters", ()) or ())
            macro_count = min(16, max(0, len(params) - 1))
            visible_cnt = getattr(rack_dev, "visible_macro_count", None)
            if visible_cnt is not None:
                try:
                    macro_count = min(macro_count, max(0, int(visible_cnt)))
                except (TypeError, ValueError):
                    pass
            out: List[float] = []
            for i in range(macro_count):
                pm = params[i + 1]
                min_m = float(getattr(pm, "min", 0.0))
                max_m = float(getattr(pm, "max", 127.0))
                val_m = float(getattr(pm, "value", 0.0))
                out.append(round((val_m - min_m) / (max_m - min_m), 6) if max_m > min_m else 0.0)
            return out

        res: Dict[str, Any] = {"status": "ok", "action": act, "variation_index": v_idx}
        s = self.song()
        if s:
            if t_idx < 0 or t_idx >= len(s.tracks):
                raise IndexError(f"Track index {t_idx} out of range")
            tr = s.tracks[t_idx]
            devices = getattr(tr, "devices", ()) or ()
            if d_idx < 0 or d_idx >= len(devices):
                raise IndexError(f"Device index {d_idx} out of range (0..{len(devices) - 1})")
            dev = devices[d_idx]
            if hasattr(dev, "can_have_chains") and not getattr(dev, "can_have_chains", False):
                raise ValueError(f"Device '{getattr(dev, 'name', d_idx)}' is not a Rack device")

            if act == "store":
                if not hasattr(dev, "store_variation"):
                    raise RuntimeError("Device does not support store_variation")
                dev.store_variation()
                v_count = getattr(dev, "variation_count", None)
                if v_count is not None:
                    res["variation_count"] = int(v_count)
                    res["variation_index"] = max(0, int(v_count) - 1)
                elif hasattr(dev, "selected_variation_index"):
                    res["variation_index"] = int(dev.selected_variation_index)
            elif act == "recall":
                v_count = getattr(dev, "variation_count", None)
                if v_count is not None and not (0 <= v_idx < int(v_count)):
                    raise IndexError(f"Variation index {v_idx} out of range (0..{int(v_count) - 1})")
                if hasattr(dev, "recall_variation"):
                    dev.recall_variation(v_idx)
                elif hasattr(dev, "recall_selected_variation"):
                    if hasattr(dev, "selected_variation_index"):
                        dev.selected_variation_index = v_idx
                    dev.recall_selected_variation()
                else:
                    raise RuntimeError("Device does not support recalling variations")
                res["macros"] = _extract_normalized_macros(dev)
            elif act == "delete":
                v_count = getattr(dev, "variation_count", None)
                if v_count is not None and not (0 <= v_idx < int(v_count)):
                    raise IndexError(f"Variation index {v_idx} out of range (0..{int(v_count) - 1})")
                if hasattr(dev, "delete_variation"):
                    dev.delete_variation(v_idx)
                elif hasattr(dev, "delete_selected_variation"):
                    if hasattr(dev, "selected_variation_index"):
                        dev.selected_variation_index = v_idx
                    dev.delete_selected_variation()
                else:
                    raise RuntimeError("Device does not support deleting variations")
            elif act == "randomize":
                if not hasattr(dev, "randomize_macros"):
                    raise RuntimeError("Device does not support randomize_macros")
                dev.randomize_macros()
                res["randomized"] = True
                res["macros"] = _extract_normalized_macros(dev)
        else:
            if act == "recall":
                res["macros"] = [0.5] * 8
            elif act == "randomize":
                res["randomized"] = True
                res["macros"] = [round(((i + 1) * 0.11) % 1.0, 4) for i in range(8)]
        return res

    def _validate_device_indices(self, track_index: int, device_index: int) -> Tuple[int, int]:
        t_idx = int(track_index)
        d_idx = int(device_index)
        if t_idx < 0:
            raise IndexError(f"Track index {t_idx} out of range")
        if d_idx < 0:
            raise IndexError(f"Device index {d_idx} out of range")
        s = self.song()
        if s:
            if t_idx >= len(s.tracks):
                raise IndexError(f"Track index {t_idx} out of range [0, {len(s.tracks)})")
            tr = s.tracks[t_idx]
            devices = getattr(tr, "devices", ()) or ()
            if d_idx >= len(devices):
                raise IndexError(
                    f"Device index {d_idx} out of range [0, {len(devices)})"
                    if devices
                    else f"Device index {d_idx} out of range: track has no devices"
                )
        return t_idx, d_idx

    def _coerce_device_param_value(
        self,
        param: Any,
        value: Union[float, int, str],
        normalized: bool = False,
    ) -> float:
        if isinstance(value, bool):
            raise ValueError(f"Boolean value {value!r} is invalid for parameter '{param.name}'")

        min_v = float(param.min)
        max_v = float(param.max)
        is_quantized = bool(getattr(param, "is_quantized", False))

        if isinstance(value, str):
            val_stripped = value.strip()
            if is_quantized:
                raw_items = list(getattr(param, "value_items", ()) or ())
                items_lower = [str(x).strip().lower() for x in raw_items]
                if val_stripped.lower() in items_lower:
                    return max(min_v, min(max_v, min_v + float(items_lower.index(val_stripped.lower()))))
            try:
                val_f = float(val_stripped)
            except ValueError:
                if is_quantized:
                    raw_items = list(getattr(param, "value_items", ()) or ())
                    raise ValueError(
                        f"Invalid quantized value {value!r} for parameter '{param.name}'"
                        + (f" (valid: {raw_items})" if raw_items else "")
                    )
                raise ValueError(
                    f"Non-numeric string {value!r} cannot be assigned to continuous parameter '{param.name}'"
                )
        else:
            val_f = float(value)

        if math.isnan(val_f) or math.isinf(val_f):
            raise ValueError(f"Parameter value must be finite, got {value!r}")

        actual_val = min_v + val_f * (max_v - min_v) if normalized else val_f
        return max(min_v, min(max_v, actual_val))

    _FLAGSHIP_INDEX_PROPS = frozenset({
        "routing_mode_index",
        "voice_mode_index",
        "voice_count_index",
        "mod_matrix_shape_source_index",
        "mod_matrix_lfo_source_index",
        "mod_matrix_filter_source_1_index",
        "mod_matrix_filter_source_2_index",
        "mod_matrix_pitch_source_1_index",
        "mod_matrix_pitch_source_2_index",
        "mod_matrix_source_1_index",
        "mod_matrix_source_2_index",
        "mod_matrix_source_3_index",
        "mod_matrix_target_1_index",
        "mod_matrix_target_2_index",
        "mod_matrix_target_3_index",
    })
    _FLAGSHIP_INT_PROPS = frozenset({
        "selected_engine",
        "unison_voices",
        "mono_poly",
        "poly_voices",
        "pitch_bend_range",
    })
    _FLAGSHIP_BOOL_PROPS = frozenset({"env_listen"})
    _FLAGSHIP_INT_LABEL_MAPS: Dict[str, Dict[str, int]] = {
        "selected_engine": {"engine a": 0, "engine_a": 0, "a": 0, "engine b": 1, "engine_b": 1, "b": 1},
        "mono_poly": {"mono": 0, "poly": 1},
        "unison_voices": {"off": 0},
    }

    def _mutate_flagship_device_params(
        self,
        track_index: int,
        device_index: int,
        params_dict: dict,
    ) -> Tuple[int, int, Dict[str, Any], Dict[str, Any]]:
        t_idx, d_idx = self._validate_device_indices(track_index, device_index)
        if not isinstance(params_dict, dict):
            raise ValueError("Device parameters payload must be a dict")
        s = self.song()
        dev = None
        if s and t_idx < len(s.tracks):
            tr = s.tracks[t_idx]
            if d_idx < len(tr.devices):
                dev = tr.devices[d_idx]

        updated_details: Dict[str, Any] = {}
        unmatched_params: Dict[str, Any] = {}

        for k, v in params_dict.items():
            k_str = str(k)
            k_norm = k_str.strip().lower().replace("-", "_").replace(" ", "_")

            if dev is not None:
                # 1. Check Live 12 device LOM properties first (Roar / Meld / Drift)
                idx_prop: Optional[str] = None
                if k_norm in self._FLAGSHIP_INDEX_PROPS and hasattr(dev, k_norm):
                    idx_prop = k_norm
                elif f"{k_norm}_index" in self._FLAGSHIP_INDEX_PROPS and hasattr(dev, f"{k_norm}_index"):
                    idx_prop = f"{k_norm}_index"

                if idx_prop is not None:
                    list_prop = idx_prop[:-6] + "_list"
                    raw_list = list(getattr(dev, list_prop, ()) or ()) if hasattr(dev, list_prop) else []
                    idx_val: Optional[int] = None
                    if isinstance(v, bool):
                        raise ValueError(f"Boolean value {v!r} is invalid for '{idx_prop}'")
                    if isinstance(v, str):
                        v_clean = v.strip().lower()
                        if raw_list:
                            list_lower = [str(item).strip().lower() for item in raw_list]
                            if v_clean in list_lower:
                                idx_val = list_lower.index(v_clean)
                        if idx_val is None:
                            try:
                                idx_val = int(v.strip())
                            except ValueError:
                                raise ValueError(
                                    f"Invalid label {v!r} for '{idx_prop}'"
                                    + (f" (valid: {raw_list})" if raw_list else "")
                                )
                    else:
                        if isinstance(v, float) and (math.isnan(v) or math.isinf(v) or not v.is_integer()):
                            raise ValueError(f"Index value for '{idx_prop}' must be an integer, got {v!r}")
                        idx_val = int(v)
                    if raw_list and not (0 <= idx_val < len(raw_list)):
                        raise IndexError(f"Index {idx_val} out of range for '{idx_prop}' (0..{len(raw_list) - 1})")
                    setattr(dev, idx_prop, idx_val)
                    actual_idx = int(getattr(dev, idx_prop))
                    updated_details[k_str] = {
                        "property": idx_prop,
                        "value": actual_idx,
                        "str_value": str(raw_list[actual_idx]) if raw_list and 0 <= actual_idx < len(raw_list) else str(actual_idx),
                    }
                    continue

                if k_norm in self._FLAGSHIP_BOOL_PROPS and hasattr(dev, k_norm):
                    if isinstance(v, bool):
                        b_val = v
                    elif isinstance(v, str):
                        vl = v.strip().lower()
                        if vl in ("true", "1", "yes", "on"):
                            b_val = True
                        elif vl in ("false", "0", "no", "off"):
                            b_val = False
                        else:
                            raise ValueError(f"Invalid boolean string {v!r} for '{k_norm}'")
                    elif isinstance(v, int) and v in (0, 1):
                        b_val = bool(v)
                    else:
                        raise ValueError(f"Invalid boolean value {v!r} for '{k_norm}'")
                    setattr(dev, k_norm, b_val)
                    actual_b = bool(getattr(dev, k_norm))
                    updated_details[k_str] = {"property": k_norm, "value": actual_b, "str_value": str(actual_b)}
                    continue

                if k_norm in self._FLAGSHIP_INT_PROPS and hasattr(dev, k_norm):
                    if isinstance(v, bool):
                        raise ValueError(f"Boolean value {v!r} is invalid for '{k_norm}'")
                    int_val: Optional[int] = None
                    list_prop = f"{k_norm}_list"
                    raw_list = list(getattr(dev, list_prop, ()) or ()) if hasattr(dev, list_prop) else []
                    if isinstance(v, str):
                        v_clean = v.strip().lower()
                        if raw_list:
                            list_lower = [str(item).strip().lower() for item in raw_list]
                            if v_clean in list_lower:
                                int_val = list_lower.index(v_clean)
                        if int_val is None:
                            lmap = self._FLAGSHIP_INT_LABEL_MAPS.get(k_norm, {})
                            if v_clean in lmap:
                                int_val = lmap[v_clean]
                        if int_val is None:
                            try:
                                int_val = int(v.strip())
                            except ValueError:
                                raise ValueError(f"Invalid value {v!r} for LOM property '{k_norm}'")
                    else:
                        if isinstance(v, float) and (math.isnan(v) or math.isinf(v) or not v.is_integer()):
                            raise ValueError(f"Value for '{k_norm}' must be an integer, got {v!r}")
                        int_val = int(v)
                    setattr(dev, k_norm, int_val)
                    actual_i = getattr(dev, k_norm)
                    updated_details[k_str] = {"property": k_norm, "value": actual_i, "str_value": str(actual_i)}
                    continue

            # 2. Match against dev.parameters
            param_found = None
            if dev is not None and hasattr(dev, "parameters"):
                k_clean = k_str.strip().lower().replace("_", " ")
                for p in dev.parameters:
                    p_name_clean = str(p.name).strip().lower().replace("_", " ")
                    if p_name_clean == k_clean:
                        param_found = p
                        break
                if param_found is None and len(k_clean) >= 2:
                    for p in dev.parameters:
                        p_name_clean = str(p.name).strip().lower().replace("_", " ")
                        if k_clean in p_name_clean:
                            param_found = p
                            break
                if param_found is None and (
                    (isinstance(k, int) and not isinstance(k, bool))
                    or (isinstance(k, str) and k.strip().isdigit())
                ):
                    p_idx = int(k)
                    if 0 <= p_idx < len(dev.parameters):
                        param_found = dev.parameters[p_idx]

            if param_found is not None:
                actual_val = self._coerce_device_param_value(param_found, v, normalized=False)
                param_found.value = actual_val
                str_rep = (
                    str(param_found.str_for_value(param_found.value))
                    if hasattr(param_found, "str_for_value")
                    else str(param_found.value)
                )
                updated_details[k_str] = {
                    "parameter_name": param_found.name,
                    "value": param_found.value,
                    "str_value": str_rep,
                }
            elif dev is not None:
                unmatched_params[k_str] = v
            else:
                updated_details[k_str] = {"target_value": v, "status": "recorded"}

        return t_idx, d_idx, updated_details, unmatched_params

    _WAVETABLE_MOD_SOURCE_ALIASES = {
        "amp": "amp_envelope",
        "amp_env": "amp_envelope",
        "amp_envelope": "amp_envelope",
        "env1": "amp_envelope",
        "env_1": "amp_envelope",
        "envelope1": "amp_envelope",
        "envelope_1": "amp_envelope",
        "env2": "envelope_2",
        "env_2": "envelope_2",
        "envelope2": "envelope_2",
        "envelope_2": "envelope_2",
        "env3": "envelope_3",
        "env_3": "envelope_3",
        "envelope3": "envelope_3",
        "envelope_3": "envelope_3",
        "lfo1": "lfo_1",
        "lfo_1": "lfo_1",
        "lfo2": "lfo_2",
        "lfo_2": "lfo_2",
        "velocity": "midi_velocity",
        "vel": "midi_velocity",
        "midi_velocity": "midi_velocity",
        "note": "midi_note",
        "key": "midi_note",
        "midi_note": "midi_note",
        "pitch_bend": "midi_pitch_bend",
        "pitchbend": "midi_pitch_bend",
        "pb": "midi_pitch_bend",
        "midi_pitch_bend": "midi_pitch_bend",
        "aftertouch": "midi_channel_pressure",
        "pressure": "midi_channel_pressure",
        "channel_pressure": "midi_channel_pressure",
        "midi_channel_pressure": "midi_channel_pressure",
        "mod_wheel": "midi_mod_wheel",
        "modwheel": "midi_mod_wheel",
        "mw": "midi_mod_wheel",
        "midi_mod_wheel": "midi_mod_wheel",
        "random": "midi_random",
        "rand": "midi_random",
        "midi_random": "midi_random",
    }

    def _resolve_wavetable_mod_source(self, dev: Any, source: str) -> Any:
        src_key = str(source or "").strip().lower().replace(" ", "_")
        canonical = self._WAVETABLE_MOD_SOURCE_ALIASES.get(src_key, src_key)
        enum_cls = None
        if Live is not None and hasattr(Live, "WavetableDevice"):
            enum_cls = getattr(Live.WavetableDevice, "ModulationSource", None)
        if enum_cls is None:
            enum_cls = getattr(dev, "ModulationSource", None)
        if enum_cls is not None:
            val = getattr(enum_cls, canonical, None)
            if val is None:
                raise ValueError(f"Unknown Wavetable modulation source {source!r}")
            return val
        if canonical not in self._WAVETABLE_MOD_SOURCE_ALIASES.values():
            raise ValueError(f"Unknown Wavetable modulation source {source!r}")
        return canonical

    def _resolve_wavetable_target_index(
        self,
        dev: Any,
        target: str,
        allow_add: bool = True,
    ) -> Tuple[Optional[int], str]:
        t_clean = str(target or "").strip().lower()
        if not t_clean:
            raise ValueError("Wavetable modulation target must not be empty")

        def _match_visible(names: List[str]) -> Optional[int]:
            for idx, name in enumerate(names):
                if str(name).lower() == t_clean:
                    return idx
            for idx, name in enumerate(names):
                if t_clean in str(name).lower():
                    return idx
            return None

        target_names = [str(n) for n in (getattr(dev, "visible_modulation_target_names", ()) or ())]
        found_idx = _match_visible(target_names)
        if found_idx is not None:
            return found_idx, target_names[found_idx]

        # Match against DeviceParameters; only add to matrix when allow_add=True (writes)
        candidates = list(getattr(dev, "parameters", ()) or ())
        matched_param = None
        for p in candidates:
            if str(getattr(p, "name", "")).lower() == t_clean:
                matched_param = p
                break
        if matched_param is None:
            for p in candidates:
                if t_clean in str(getattr(p, "name", "")).lower():
                    matched_param = p
                    break

        if matched_param is not None:
            if hasattr(dev, "is_parameter_modulatable") and not dev.is_parameter_modulatable(matched_param):
                raise ValueError(f"Parameter '{matched_param.name}' is not modulatable in Wavetable")
            if not allow_add:
                return None, str(getattr(matched_param, "name", target))
            if hasattr(dev, "add_parameter_to_modulation_matrix"):
                dev.add_parameter_to_modulation_matrix(matched_param)
                target_names = [str(n) for n in (getattr(dev, "visible_modulation_target_names", ()) or ())]
                p_name_l = str(getattr(matched_param, "name", "")).lower()
                for idx, name in enumerate(target_names):
                    if str(name).lower() == p_name_l or t_clean in str(name).lower():
                        return idx, str(name)
                found_idx = _match_visible(target_names)
                if found_idx is not None:
                    return found_idx, target_names[found_idx]

        raise ValueError(f"Wavetable modulation target {target!r} not found or not modulatable")

    def live12_wavetable_modulation_matrix(
        self,
        track_index: int,
        device_index: int,
        action: str,
        source: str = "",
        target: str = "",
        amount: float = 0.0,
    ) -> Dict[str, Any]:
        t_idx, d_idx = self._validate_device_indices(track_index, device_index)
        amt = float(amount)
        if math.isnan(amt) or math.isinf(amt) or amt < -1.0 or amt > 1.0:
            raise ValueError(f"Modulation amount {amt} out of range [-1.0, 1.0]")

        act = str(action).strip().lower()
        if act not in ("set", "get", "clear"):
            raise ValueError(f"Unknown matrix action: {action}")

        s = self.song()
        dev = None
        if s:
            dev = s.tracks[t_idx].devices[d_idx]

        if not hasattr(self, "_wavetable_matrices"):
            self._wavetable_matrices: Dict[Tuple[int, int], Dict[str, float]] = {}
        matrix_key = (t_idx, d_idx)
        current_matrix = self._wavetable_matrices.setdefault(matrix_key, {})

        if dev is not None:
            if not hasattr(dev, "set_modulation_value") or not hasattr(dev, "get_modulation_value"):
                raise RuntimeError(
                    f"Device '{getattr(dev, 'name', d_idx)}' does not expose Wavetable modulation matrix API"
                )
            if act == "set":
                mod_src = self._resolve_wavetable_mod_source(dev, source)
                target_idx, target_name = self._resolve_wavetable_target_index(dev, target, allow_add=True)
                try:
                    dev.set_modulation_value(target_idx, mod_src, amt)
                except TypeError:
                    dev.set_modulation_value(mod_src, target_idx, amt)
                actual_amt = amt
                try:
                    actual_amt = float(dev.get_modulation_value(target_idx, mod_src))
                except TypeError:
                    actual_amt = float(dev.get_modulation_value(mod_src, target_idx))
                return {
                    "status": "set",
                    "source": source,
                    "target": target_name,
                    "target_index": target_idx,
                    "amount": actual_amt,
                }
            elif act == "get":
                mod_src = self._resolve_wavetable_mod_source(dev, source)
                target_idx, target_name = self._resolve_wavetable_target_index(dev, target, allow_add=False)
                if target_idx is None:
                    stored_amt = 0.0
                else:
                    try:
                        stored_amt = float(dev.get_modulation_value(target_idx, mod_src))
                    except TypeError:
                        stored_amt = float(dev.get_modulation_value(mod_src, target_idx))
                return {
                    "status": "get",
                    "source": source,
                    "target": target_name,
                    "target_index": target_idx,
                    "amount": stored_amt,
                }
            else:  # clear
                target_names = list(getattr(dev, "visible_modulation_target_names", ()) or ())
                enum_cls = None
                if Live is not None and hasattr(Live, "WavetableDevice"):
                    enum_cls = getattr(Live.WavetableDevice, "ModulationSource", None)
                if enum_cls is None:
                    enum_cls = getattr(dev, "ModulationSource", None)
                sources: List[Any] = []
                if enum_cls is not None:
                    for src_name in dict.fromkeys(self._WAVETABLE_MOD_SOURCE_ALIASES.values()):
                        val = getattr(enum_cls, src_name, None)
                        if val is not None:
                            sources.append(val)
                cleared_count = 0
                for target_idx in range(len(target_names)):
                    for mod_src in sources:
                        try:
                            cur = float(dev.get_modulation_value(target_idx, mod_src))
                        except TypeError:
                            cur = float(dev.get_modulation_value(mod_src, target_idx))
                        if cur != 0.0:
                            try:
                                dev.set_modulation_value(target_idx, mod_src, 0.0)
                            except TypeError:
                                dev.set_modulation_value(mod_src, target_idx, 0.0)
                            cleared_count += 1
                current_matrix.clear()
                return {
                    "status": "cleared",
                    "track_index": t_idx,
                    "device_index": d_idx,
                    "cleared_count": cleared_count,
                }

        # Offline mock path (s is None)
        key = f"{source}->{target}" if source and target else ""
        if act == "set":
            if key:
                current_matrix[key] = amt
            return {"status": "set", "source": source, "target": target, "amount": amt}
        elif act == "get":
            return {
                "status": "get",
                "source": source,
                "target": target,
                "amount": current_matrix.get(key, 0.0) if key else 0.0,
            }
        else:
            current_matrix.clear()
            return {"status": "cleared", "track_index": t_idx, "device_index": d_idx, "cleared_count": 0}

    _SIMPLER_PLAYBACK_MAP = {
        "0": 0,
        "classic": 0,
        "1": 1,
        "one-shot": 1,
        "one shot": 1,
        "1-shot": 1,
        "1_shot": 1,
        "oneshot": 1,
        "one_shot": 1,
        "2": 2,
        "slicing": 2,
        "slice": 2,
    }
    _SIMPLER_PLAYBACK_NAMES = {
        0: "Classic",
        1: "1-Shot",
        2: "Slicing",
    }
    _SIMPLER_SLICING_STYLES = {
        "0": 0,
        "transient": 0,
        "1": 1,
        "beat": 1,
        "2": 2,
        "region": 2,
        "3": 3,
        "manual": 3,
    }
    _SIMPLER_BEAT_DIVISIONS = {
        "0": 0,
        "1/32": 0,
        "1": 1,
        "1/24": 1,
        "2": 2,
        "1/16": 2,
        "3": 3,
        "1/12": 3,
        "4": 4,
        "1/8": 4,
        "5": 5,
        "1/6": 5,
        "6": 6,
        "1/4": 6,
        "7": 7,
        "1/2": 7,
        "8": 8,
        "1 bar": 8,
        "1_bar": 8,
        "1bar": 8,
        "bar": 8,
    }

    @classmethod
    def _normalize_simpler_sensitivity(cls, raw_sens: Any) -> float:
        if isinstance(raw_sens, bool):
            raise ValueError(f"Boolean value {raw_sens!r} is invalid for Simpler slicing sensitivity")
        sens_f = float(raw_sens)
        if math.isnan(sens_f) or math.isinf(sens_f) or sens_f < 0.0 or sens_f > 100.0:
            raise ValueError(f"Simpler slicing sensitivity must be in [0.0, 100.0], got {sens_f}")
        return sens_f / 100.0 if sens_f > 1.0 else sens_f

    @classmethod
    def _parse_simpler_playback_mode(cls, mode_raw: Any) -> int:
        if isinstance(mode_raw, bool):
            raise ValueError(f"Invalid Simpler playback_mode {mode_raw!r}; expected Classic, 1-Shot, or Slicing")
        if isinstance(mode_raw, int):
            if mode_raw in cls._SIMPLER_PLAYBACK_NAMES:
                return mode_raw
            raise ValueError(f"Invalid Simpler playback_mode {mode_raw!r}; expected 0, 1, or 2")
        mode_key = str(mode_raw).strip().lower()
        if mode_key in cls._SIMPLER_PLAYBACK_MAP:
            return cls._SIMPLER_PLAYBACK_MAP[mode_key]
        raise ValueError(f"Invalid Simpler playback_mode {mode_raw!r}; expected Classic, 1-Shot, or Slicing")

    def live12_simpler_control(
        self,
        track_index: int,
        device_index: int,
        action: str,
        params: Optional[dict] = None,
        playback_mode: Optional[Union[str, int]] = None,
        sensitivity: Optional[float] = None,
    ) -> Dict[str, Any]:
        valid_actions = ("get_state", "set_playback_mode", "slice", "slice_to_drum_rack", "replace_sample")
        act = str(action).strip().lower()
        if act not in valid_actions:
            raise ValueError(f"Unsupported Simpler action {action!r}; must be one of {valid_actions}")

        t_idx, d_idx = self._validate_device_indices(track_index, device_index)
        s = self.song()
        dev = s.tracks[t_idx].devices[d_idx] if s else None

        eff_mode = playback_mode if playback_mode is not None else (params.get("playback_mode") if params else None)
        eff_sens = sensitivity if sensitivity is not None else (params.get("sensitivity") if params else None)

        if not hasattr(self, "_simpler_state"):
            self._simpler_state: Dict[Tuple[int, int], Dict[str, Any]] = {}
        st = self._simpler_state.setdefault((t_idx, d_idx), {
            "playback_mode": "Classic",
            "slices": [0.0, 0.25, 0.5, 0.75, 1.0],
            "sample_path": "",
        })

        if dev is not None:
            if not (
                hasattr(dev, "playback_mode")
                or getattr(dev, "class_name", "") == "OriginalSimpler"
                or getattr(dev, "class_display_name", "") == "Simpler"
            ):
                raise ValueError(f"Device '{getattr(dev, 'name', d_idx)}' is not a Simpler device")

            sample_obj = getattr(dev, "sample", None)
            if act == "get_state":
                raw_pm = getattr(dev, "playback_mode", None)
                if raw_pm is not None:
                    try:
                        pb_mode = self._SIMPLER_PLAYBACK_NAMES.get(int(raw_pm), str(raw_pm))
                    except (TypeError, ValueError):
                        pb_mode = str(raw_pm)
                else:
                    pb_mode = st["playback_mode"]
                    for p in getattr(dev, "parameters", ()) or ():
                        if "mode" in p.name.lower() or "playback" in p.name.lower():
                            pb_mode = str(p.str_for_value(p.value) if hasattr(p, "str_for_value") else p.value)
                            break
                slices = getattr(sample_obj, "slices", ()) or ()
                s_path = str(getattr(sample_obj, "file_path", "") or "")
                res: Dict[str, Any] = {
                    "status": "success",
                    "track_index": t_idx,
                    "device_index": d_idx,
                    "playback_mode": pb_mode,
                    "slices_count": len(slices),
                    "sample_path": s_path,
                }
                if sample_obj is not None and hasattr(sample_obj, "slicing_sensitivity"):
                    res["slicing_sensitivity"] = float(sample_obj.slicing_sensitivity)
                return res

            elif act == "set_playback_mode":
                mode_raw = eff_mode if eff_mode is not None else "Classic"
                pm_int = self._parse_simpler_playback_mode(mode_raw)
                canonical_mode = self._SIMPLER_PLAYBACK_NAMES[pm_int]
                if hasattr(dev, "playback_mode"):
                    dev.playback_mode = pm_int
                else:
                    matched_p = None
                    for p in getattr(dev, "parameters", ()) or ():
                        if "mode" in p.name.lower() or "playback" in p.name.lower():
                            matched_p = p
                            break
                    if matched_p is None:
                        raise RuntimeError("Device does not expose Simpler playback_mode")
                    if getattr(matched_p, "is_quantized", False):
                        try:
                            matched_p.value = self._coerce_device_param_value(matched_p, canonical_mode)
                        except ValueError:
                            matched_p.value = float(pm_int)
                    else:
                        matched_p.value = float(pm_int)
                st["playback_mode"] = canonical_mode
                return {
                    "status": "success",
                    "track_index": t_idx,
                    "device_index": d_idx,
                    "playback_mode": canonical_mode,
                }

            elif act == "slice":
                if hasattr(dev, "playback_mode"):
                    dev.playback_mode = 2
                if eff_sens is not None:
                    sens_norm = self._normalize_simpler_sensitivity(eff_sens)
                    if sample_obj is None or not hasattr(sample_obj, "slicing_sensitivity"):
                        raise RuntimeError("Simpler sample does not expose slicing_sensitivity")
                    sample_obj.slicing_sensitivity = sens_norm
                if params and "slicing_style" in params:
                    raw_style = params["slicing_style"]
                    if isinstance(raw_style, bool):
                        raise ValueError(f"Invalid Simpler slicing_style {raw_style!r}")
                    style_key = str(raw_style).strip().lower()
                    if style_key not in self._SIMPLER_SLICING_STYLES:
                        raise ValueError(
                            f"Invalid Simpler slicing_style {raw_style!r}; expected transient, beat, region, or manual"
                        )
                    if sample_obj is not None and hasattr(sample_obj, "slicing_style"):
                        sample_obj.slicing_style = self._SIMPLER_SLICING_STYLES[style_key]
                if params and "beat_division" in params:
                    raw_div = params["beat_division"]
                    if isinstance(raw_div, bool):
                        raise ValueError(f"Invalid Simpler beat_division {raw_div!r}")
                    div_key = str(raw_div).strip().lower()
                    if div_key not in self._SIMPLER_BEAT_DIVISIONS:
                        raise ValueError(
                            f"Invalid Simpler beat_division {raw_div!r}; expected 1/32..1 Bar or 0..8"
                        )
                    if sample_obj is not None and hasattr(sample_obj, "slicing_beat_division"):
                        sample_obj.slicing_beat_division = self._SIMPLER_BEAT_DIVISIONS[div_key]
                slices = getattr(sample_obj, "slices", None) if sample_obj else None
                slices_count = len(slices) if slices is not None else 0
                st["playback_mode"] = "Slicing"
                return {
                    "status": "sliced",
                    "track_index": t_idx,
                    "device_index": d_idx,
                    "playback_mode": "Slicing",
                    "slices_count": slices_count,
                }

            elif act == "slice_to_drum_rack":
                if (
                    Live is not None
                    and hasattr(Live, "Conversions")
                    and hasattr(Live.Conversions, "sliced_simpler_to_drum_rack")
                ):
                    Live.Conversions.sliced_simpler_to_drum_rack(s, dev)
                    return {
                        "status": "success",
                        "action": "slice_to_drum_rack",
                        "track_index": t_idx,
                        "device_index": d_idx,
                    }
                if hasattr(dev, "slice_to_drum_rack"):
                    dev.slice_to_drum_rack()
                    return {
                        "status": "success",
                        "action": "slice_to_drum_rack",
                        "track_index": t_idx,
                        "device_index": d_idx,
                    }
                raise NotImplementedError(
                    "slice_to_drum_rack requires Live.Conversions.sliced_simpler_to_drum_rack; use Simpler Slicing mode via action='slice' instead"
                )

            elif act == "replace_sample":
                sample_path = str(params.get("sample_path", "")) if params else ""
                if not sample_path:
                    raise ValueError("params['sample_path'] is required for replace_sample")
                if not hasattr(dev, "replace_sample"):
                    raise RuntimeError("SimplerDevice does not expose replace_sample in this environment")
                dev.replace_sample(sample_path)
                st["sample_path"] = sample_path
                actual_path = str(getattr(getattr(dev, "sample", None), "file_path", sample_path) or sample_path)
                return {
                    "status": "sample_replaced",
                    "track_index": t_idx,
                    "device_index": d_idx,
                    "path": actual_path,
                    "sample_path": actual_path,
                }

        # Offline mock path (s is None)
        if act == "get_state":
            return {
                "status": "success",
                "track_index": t_idx,
                "device_index": d_idx,
                "playback_mode": st["playback_mode"],
                "slices_count": len(st["slices"]),
                "sample_path": st["sample_path"],
            }
        elif act == "set_playback_mode":
            mode_raw = eff_mode if eff_mode is not None else "Classic"
            pm_int = self._parse_simpler_playback_mode(mode_raw)
            canonical_mode = self._SIMPLER_PLAYBACK_NAMES[pm_int]
            st["playback_mode"] = canonical_mode
            return {"status": "success", "playback_mode": canonical_mode}
        elif act == "slice":
            if eff_sens is not None:
                self._normalize_simpler_sensitivity(eff_sens)
            if params and "slicing_style" in params:
                raw_style = params["slicing_style"]
                if isinstance(raw_style, bool) or str(raw_style).strip().lower() not in self._SIMPLER_SLICING_STYLES:
                    raise ValueError(f"Invalid Simpler slicing_style {raw_style!r}")
            if params and "beat_division" in params:
                raw_div = params["beat_division"]
                if isinstance(raw_div, bool) or str(raw_div).strip().lower() not in self._SIMPLER_BEAT_DIVISIONS:
                    raise ValueError(f"Invalid Simpler beat_division {raw_div!r}")
            st["playback_mode"] = "Slicing"
            return {"status": "sliced", "playback_mode": "Slicing", "slices_count": len(st["slices"])}
        elif act == "slice_to_drum_rack":
            return {
                "status": "success",
                "action": "slice_to_drum_rack",
                "slices_count": len(st["slices"]),
            }
        else:
            sample_path = str(params.get("sample_path", "")) if params else ""
            if not sample_path:
                raise ValueError("params['sample_path'] is required for replace_sample")
            st["sample_path"] = sample_path
            return {"status": "sample_replaced", "path": sample_path}

    def live12_meld_control(
        self,
        track_index: int,
        device_index: int,
        engine_params: dict,
    ) -> Dict[str, Any]:
        t_idx, d_idx, updated, unmatched = self._mutate_flagship_device_params(track_index, device_index, engine_params)
        return {
            "status": "success",
            "track_index": t_idx,
            "device_index": d_idx,
            "meld_params_updated": len(updated),
            "parameters": updated,
            "unmatched_params": unmatched,
        }

    def live12_roar_control(
        self,
        track_index: int,
        device_index: int,
        stage_params: dict,
    ) -> Dict[str, Any]:
        t_idx, d_idx, updated, unmatched = self._mutate_flagship_device_params(track_index, device_index, stage_params)
        return {
            "status": "success",
            "track_index": t_idx,
            "device_index": d_idx,
            "roar_stages_updated": len(updated),
            "parameters": updated,
            "unmatched_params": unmatched,
        }

    def live12_drift_control(
        self,
        track_index: int,
        device_index: int,
        voice_params: dict,
    ) -> Dict[str, Any]:
        t_idx, d_idx, updated, unmatched = self._mutate_flagship_device_params(track_index, device_index, voice_params)
        return {
            "status": "success",
            "track_index": t_idx,
            "device_index": d_idx,
            "drift_voice_updated": len(updated),
            "parameters": updated,
            "unmatched_params": unmatched,
        }

    def live12_browser_preview(
        self,
        action: str,
        browser_item_uri: Optional[str] = None,
    ) -> Dict[str, Any]:
        valid_actions = ("preview", "stop", "hotswap_status")
        if action not in valid_actions:
            raise ValueError(f"Invalid browser preview action '{action}', must be one of {valid_actions}")

        app = self.application()
        browser = getattr(app, "browser", None) if app else None
        res: Dict[str, Any] = {"status": "success", "action": action}

        if action == "preview":
            if not browser_item_uri:
                raise ValueError("browser_item_uri is required for action='preview'")
            res["preview_active"] = True
            res["browser_item_uri"] = browser_item_uri
            if browser and hasattr(browser, "preview_item"):
                item = (
                    browser_item_uri
                    if hasattr(browser_item_uri, "is_loadable")
                    else self._find_browser_item(browser, str(browser_item_uri))
                )
                if item is None:
                    raise ValueError(f"Browser item '{browser_item_uri}' not found for preview")
                browser.preview_item(item)
        elif action == "stop":
            res["preview_active"] = False
            if browser and hasattr(browser, "stop_preview"):
                browser.stop_preview()
        elif action == "hotswap_status":
            target = getattr(browser, "hotswap_target", None) if browser else None
            res["hotswap_active"] = (target is not None)
            res["target"] = str(target) if target else None

        return res

    def live12_rack_macro_config(
        self,
        track_index: int,
        device_index: int,
        action: str,
        count: Optional[int] = None,
    ) -> Dict[str, Any]:
        valid_actions = ("get_config", "set_count", "add_macro", "remove_macro", "randomize")
        if action not in valid_actions:
            raise ValueError(f"Invalid rack macro action '{action}', must be one of {valid_actions}")

        t_idx, d_idx = self._validate_device_indices(track_index, device_index)
        s = self.song()
        dev = s.tracks[t_idx].devices[d_idx] if s else None
        if dev is not None and hasattr(dev, "can_have_chains") and not getattr(dev, "can_have_chains", False):
            raise ValueError(f"Device '{getattr(dev, 'name', d_idx)}' is not a Rack device")

        res: Dict[str, Any] = {
            "status": "success",
            "action": action,
            "track_index": t_idx,
            "device_index": d_idx,
        }

        if action == "get_config":
            vmc = int(getattr(dev, "visible_macro_count", 8)) if dev else 8
            chains_cnt = len(getattr(dev, "chains", [])) if dev and hasattr(dev, "chains") else 0
            ret_cnt = len(getattr(dev, "return_chains", [])) if dev and hasattr(dev, "return_chains") else 0
            res["visible_macro_count"] = vmc
            res["chains_count"] = chains_cnt
            res["return_chains_count"] = ret_cnt
        elif action == "set_count":
            cnt = int(count if count is not None else 8)
            if cnt < 1 or cnt > 16:
                raise ValueError("Macro count must be between 1 and 16")
            if dev is not None:
                if hasattr(dev, "add_macro") and hasattr(dev, "remove_macro") and hasattr(dev, "visible_macro_count"):
                    try:
                        dev.visible_macro_count = cnt
                    except (AttributeError, RuntimeError):
                        for _ in range(16):
                            curr = int(dev.visible_macro_count)
                            if curr < cnt:
                                dev.add_macro()
                            elif curr > cnt:
                                dev.remove_macro()
                            else:
                                break
                elif hasattr(dev, "visible_macro_count"):
                    dev.visible_macro_count = cnt
                else:
                    raise RuntimeError("Rack device does not expose visible_macro_count")
                res["visible_macro_count"] = int(getattr(dev, "visible_macro_count", cnt))
            else:
                res["visible_macro_count"] = cnt
        elif action == "add_macro":
            if dev is not None:
                if hasattr(dev, "add_macro"):
                    dev.add_macro()
                elif hasattr(dev, "visible_macro_count"):
                    dev.visible_macro_count = min(16, int(dev.visible_macro_count) + 1)
                else:
                    raise RuntimeError("Rack device does not support adding macros")
                res["visible_macro_count"] = int(getattr(dev, "visible_macro_count", 9))
            else:
                res["visible_macro_count"] = 9
        elif action == "remove_macro":
            if dev is not None:
                if hasattr(dev, "remove_macro"):
                    dev.remove_macro()
                elif hasattr(dev, "visible_macro_count"):
                    dev.visible_macro_count = max(1, int(dev.visible_macro_count) - 1)
                else:
                    raise RuntimeError("Rack device does not support removing macros")
                res["visible_macro_count"] = int(getattr(dev, "visible_macro_count", 7))
            else:
                res["visible_macro_count"] = 7
        elif action == "randomize":
            if dev is not None:
                if not hasattr(dev, "randomize_macros"):
                    raise RuntimeError("Rack device does not expose randomize_macros")
                dev.randomize_macros()
            res["randomized"] = True

        return res

    def live12_drum_pad_control(
        self,
        track_index: int,
        device_index: int,
        action: str,
        pad_note: Optional[int] = None,
        target_note: Optional[int] = None,
        state: Optional[bool] = None,
    ) -> Dict[str, Any]:
        valid_actions = ("inspect_pads", "mute_pad", "solo_pad", "copy_pad", "delete_chains")
        if action not in valid_actions:
            raise ValueError(f"Invalid drum pad action '{action}', must be one of {valid_actions}")

        t_idx, d_idx = self._validate_device_indices(track_index, device_index)
        s = self.song()
        dev = s.tracks[t_idx].devices[d_idx] if s else None

        res: Dict[str, Any] = {
            "status": "success",
            "action": action,
            "track_index": t_idx,
            "device_index": d_idx,
        }

        if dev is not None:
            if hasattr(dev, "can_have_drum_pads") and not dev.can_have_drum_pads:
                raise ValueError(f"Device '{getattr(dev, 'name', d_idx)}' is not a Drum Rack")
            if not hasattr(dev, "drum_pads"):
                raise ValueError(f"Device '{getattr(dev, 'name', d_idx)}' is not a Drum Rack")
        drum_pads = list(getattr(dev, "drum_pads", []) or []) if dev is not None else []

        def _require_pad(note_val: Optional[int], label: str = "pad_note") -> int:
            if note_val is None:
                raise ValueError(f"{label} is required for {action}")
            pn = int(note_val)
            if not (0 <= pn <= 127):
                raise IndexError(f"{label} {pn} out of MIDI range [0, 127]")
            if dev is not None:
                if not drum_pads or pn >= len(drum_pads):
                    raise IndexError(f"{label} {pn} out of Drum Rack range (0..{len(drum_pads) - 1})")
            return pn

        if action == "inspect_pads":
            active_pads = []
            for i, p in enumerate(drum_pads):
                chains = getattr(p, "chains", [])
                if chains or getattr(p, "name", ""):
                    active_pads.append({
                        "note": int(getattr(p, "note", i)),
                        "name": str(getattr(p, "name", f"Pad {i}")),
                        "mute": bool(getattr(p, "mute", False)),
                        "solo": bool(getattr(p, "solo", False)),
                        "chains_count": len(chains),
                    })
            res["pads"] = active_pads
            res["total_pads_count"] = len(drum_pads) if dev is not None else 128

        elif action == "mute_pad":
            pn = _require_pad(pad_note)
            st = bool(state if state is not None else True)
            if dev is not None:
                drum_pads[pn].mute = st
            res["pad_note"] = pn
            res["mute"] = st

        elif action == "solo_pad":
            pn = _require_pad(pad_note)
            st = bool(state if state is not None else True)
            if dev is not None:
                drum_pads[pn].solo = st
            res["pad_note"] = pn
            res["solo"] = st

        elif action == "copy_pad":
            src = _require_pad(pad_note, "pad_note")
            dst = _require_pad(target_note, "target_note")
            if dev is not None:
                if not hasattr(dev, "copy_pad"):
                    raise RuntimeError("Drum Rack device does not expose copy_pad")
                dev.copy_pad(src, dst)
            res["source_note"] = src
            res["target_note"] = dst

        elif action == "delete_chains":
            pn = _require_pad(pad_note)
            if dev is not None:
                p = drum_pads[pn]
                if not hasattr(p, "delete_all_chains"):
                    raise RuntimeError("DrumPad object does not expose delete_all_chains")
                p.delete_all_chains()
            res["pad_note"] = pn
            res["chains_deleted"] = True

        return res

    def live12_cc_control(
        self,
        track_index: int,
        device_index: int,
        action: str,
        cc_number: Optional[int] = None,
        value: Optional[int] = None,
        channel: int = 1,
    ) -> Dict[str, Any]:
        valid_actions = ("set_cc", "get_mappings")
        if action not in valid_actions:
            raise ValueError(f"Invalid CC Control action '{action}', must be one of {valid_actions}")

        t_idx, d_idx = self._validate_device_indices(track_index, device_index)
        s = self.song()
        dev = s.tracks[t_idx].devices[d_idx] if s else None

        res: Dict[str, Any] = {
            "status": "success",
            "action": action,
            "track_index": t_idx,
            "device_index": d_idx,
        }

        if action == "set_cc":
            if cc_number is None or value is None:
                raise ValueError("cc_number and value are required for set_cc")
            cc = int(cc_number)
            val = int(value)
            ch = int(channel)
            if not (0 <= cc <= 127):
                raise ValueError("cc_number must be between 0 and 127")
            if not (0 <= val <= 127):
                raise ValueError("value must be between 0 and 127")
            if not (1 <= ch <= 16):
                raise ValueError("channel must be between 1 and 16")
            res["cc_number"] = cc
            res["value"] = val
            res["channel"] = ch
            if dev is not None:
                params = list(getattr(dev, "parameters", ()) or ())
                # Strict channel parameter matching: never clobber 'Channel Pressure'
                for p in params:
                    p_name_clean = re.sub(r"[^a-z0-9]+", " ", str(getattr(p, "name", "")).lower()).strip()
                    if p_name_clean in ("channel", "midi channel", "ch") and "pressure" not in p_name_clean:
                        p_min = float(getattr(p, "min", 1.0))
                        p_max = float(getattr(p, "max", 16.0))
                        if getattr(p, "is_quantized", False) and hasattr(p, "value_items"):
                            items_l = [str(it).strip().lower() for it in (getattr(p, "value_items", ()) or ())]
                            if str(ch) in items_l:
                                p.value = max(p_min, min(p_max, p_min + float(items_l.index(str(ch)))))
                                break
                        if p_min == 0.0 and p_max <= 15.0:
                            ch_val = float(ch - 1)
                        elif p_min <= float(ch) <= p_max:
                            ch_val = float(ch)
                        else:
                            ch_val = p_min + float(ch - 1)
                        p.value = max(p_min, min(p_max, ch_val))
                        break

                def _match_float_slot_param(slot_idx: int) -> Optional[Any]:
                    slot_pat = re.compile(
                        rf"(?:custom\s*float|float\s*target|float|custom)\s*0*{slot_idx}\b",
                        re.IGNORECASE,
                    )
                    for p_cand in params:
                        if slot_pat.search(str(getattr(p_cand, "name", ""))):
                            return p_cand
                    return None

                def _resolve_cc_list_index(raw_list: List[Any], target_cc: int) -> int:
                    if not raw_list:
                        return target_cc
                    item_pat = re.compile(rf"^(?:cc\s*)?0*{target_cc}(?:\b|\s*\(|$)", re.IGNORECASE)
                    for idx, entry in enumerate(raw_list):
                        if item_pat.match(str(entry).strip()):
                            return idx
                    if 0 <= target_cc < len(raw_list):
                        return target_cc
                    raise ValueError(f"CC {target_cc} not available in CcControlDevice target list")

                matched_p = None
                matched_slot: Optional[int] = None

                # 1. Check existing CcControlDevice LOM custom_float_target_0..11 assignments
                for slot_i in range(12):
                    attr_name = f"custom_float_target_{slot_i}"
                    if not hasattr(dev, attr_name):
                        continue
                    cur_target = getattr(dev, attr_name)
                    list_vals = list(getattr(dev, f"{attr_name}_list", ()) or ())
                    cur_is_cc = False
                    try:
                        if int(cur_target) == cc:
                            cur_is_cc = True
                        elif list_vals and 0 <= int(cur_target) < len(list_vals):
                            lbl = str(list_vals[int(cur_target)]).strip()
                            if re.match(rf"^(?:cc\s*)?0*{cc}(?:\b|\s*\(|$)", lbl, re.IGNORECASE):
                                cur_is_cc = True
                    except (TypeError, ValueError):
                        pass
                    if cur_is_cc:
                        matched_slot = slot_i
                        matched_p = _match_float_slot_param(slot_i)
                        if matched_p is not None:
                            break

                # 2. Direct parameter name lookup (e.g. 'CC 74' or 'Mod Wheel')
                if matched_p is None:
                    cc_pattern = re.compile(rf"\bcc\s*0*{cc}\b", re.IGNORECASE)
                    for p in params:
                        p_name = str(getattr(p, "name", ""))
                        if cc_pattern.search(p_name):
                            matched_p = p
                            break
                if matched_p is None and cc == 1:
                    for p in params:
                        p_name_l = str(getattr(p, "name", "")).lower()
                        if "mod wheel" in p_name_l or "modulation" in p_name_l:
                            matched_p = p
                            break

                # 3. Assign a custom_float_target slot if CcControlDevice exposes them
                if matched_p is None and matched_slot is None:
                    avail_slots = [i for i in range(12) if hasattr(dev, f"custom_float_target_{i}")]
                    if avail_slots:
                        chosen_slot = avail_slots[0]
                        for slot_i in avail_slots:
                            cur_val = getattr(dev, f"custom_float_target_{slot_i}")
                            if cur_val in (-1, 0, None):
                                chosen_slot = slot_i
                                break
                        attr_name = f"custom_float_target_{chosen_slot}"
                        list_vals = list(getattr(dev, f"{attr_name}_list", ()) or ())
                        setattr(dev, attr_name, _resolve_cc_list_index(list_vals, cc))
                        matched_slot = chosen_slot
                        matched_p = _match_float_slot_param(chosen_slot)

                if matched_p is None and matched_slot is None:
                    raise ValueError(
                        f"No parameter matching CC {cc} found on device '{getattr(dev, 'name', d_idx)}'"
                    )

                if matched_p is not None:
                    p_min = float(getattr(matched_p, "min", 0.0))
                    p_max = float(getattr(matched_p, "max", 1.0))
                    matched_p.value = p_min + (val / 127.0) * (p_max - p_min)
                    res["parameter_name"] = str(getattr(matched_p, "name", ""))
                    res["parameter_value"] = float(matched_p.value)
                if matched_slot is not None:
                    res["custom_float_slot"] = matched_slot
                if hasattr(dev, "resend") and callable(dev.resend):
                    dev.resend()
                    res["resent"] = True

        elif action == "get_mappings":
            mappings = []
            if dev is not None and hasattr(dev, "parameters"):
                for i, p in enumerate(dev.parameters):
                    p_min = float(getattr(p, "min", 0.0))
                    p_max = float(getattr(p, "max", 1.0))
                    p_val = float(getattr(p, "value", 0.0))
                    mappings.append({
                        "index": i,
                        "name": str(getattr(p, "name", f"Param {i}")),
                        "value": p_val,
                        "min": p_min,
                        "max": p_max,
                        "normalized_value": (p_val - p_min) / (p_max - p_min) if p_max > p_min else 0.0,
                    })
            res["mappings"] = mappings
            if dev is not None:
                custom_targets = []
                for slot_i in range(12):
                    attr_name = f"custom_float_target_{slot_i}"
                    if hasattr(dev, attr_name):
                        raw_t = getattr(dev, attr_name)
                        list_vals = list(getattr(dev, f"{attr_name}_list", ()) or ())
                        entry: Dict[str, Any] = {"slot": slot_i, "target": raw_t}
                        try:
                            idx_i = int(raw_t)
                            if list_vals and 0 <= idx_i < len(list_vals):
                                entry["target_label"] = str(list_vals[idx_i])
                        except (TypeError, ValueError):
                            pass
                        custom_targets.append(entry)
                if custom_targets:
                    res["custom_targets"] = custom_targets

        return res

    # -------------------------------------------------------------------------
    # Domain 5: View, Native Dialogs & OS-Level Actions
    # -------------------------------------------------------------------------

    def live12_view_switch(self, view_name: str) -> Dict[str, Any]:
        if view_name not in VALID_VIEW_NAMES:
            raise ValueError(f"Invalid view name: '{view_name}'. Must be one of {VALID_VIEW_NAMES}")
        app = self.application()
        if app and hasattr(app, "view"):
            if view_name in ("Session", "Arranger"):
                app.view.show_view(view_name)
            else:
                app.view.focus_view(view_name)
        return {"current_view": view_name, "active_view": view_name}

    def live12_view_select(
        self,
        track_index: Optional[int] = None,
        scene_index: Optional[int] = None,
        clip_slot: Optional[List[int]] = None,
        device_index: Optional[int] = None,
    ) -> Dict[str, Any]:
        s = self.song()
        if s and hasattr(s, "view"):
            if track_index is not None:
                t_idx = int(track_index)
                if not (0 <= t_idx < len(s.tracks)):
                    raise IndexError(f"Track index {t_idx} out of range")
                s.view.selected_track = s.tracks[t_idx]
            if scene_index is not None:
                s_idx = int(scene_index)
                if not (0 <= s_idx < len(s.scenes)):
                    raise IndexError(f"Scene index {s_idx} out of range")
                s.view.selected_scene = s.scenes[s_idx]
            if clip_slot is not None:
                if not isinstance(clip_slot, (list, tuple)) or len(clip_slot) != 2:
                    raise ValueError("clip_slot must be a [track_index, scene_index] pair")
                cs_t = int(clip_slot[0])
                cs_s = int(clip_slot[1])
                if not (0 <= cs_t < len(s.tracks)):
                    raise IndexError(f"clip_slot track index {cs_t} out of range")
                tr = s.tracks[cs_t]
                if not (0 <= cs_s < len(tr.clip_slots)):
                    raise IndexError(f"clip_slot scene index {cs_s} out of range")
                if hasattr(s.view, "highlighted_clip_slot"):
                    s.view.highlighted_clip_slot = tr.clip_slots[cs_s]
            if device_index is not None:
                d_idx = int(device_index)
                if track_index is not None:
                    tr = s.tracks[int(track_index)]
                else:
                    tr = getattr(s.view, "selected_track", None)
                    if tr is None and s.tracks:
                        tr = s.tracks[0]
                if tr is None or not (0 <= d_idx < len(tr.devices)):
                    raise IndexError(f"Device index {d_idx} out of range")
                if hasattr(s.view, "select_device"):
                    s.view.select_device(tr.devices[d_idx])
        return {
            "selected": True,
            "track_index": track_index,
            "scene_index": scene_index,
            "selected_track": track_index,
            "selected_scene": scene_index,
            "selected_clip_slot": clip_slot,
            "selected_device": device_index,
        }

    def live12_dialog_inspect(self) -> Dict[str, Any]:
        app = self.application()
        count = getattr(app, "open_dialog_count", 0) if app else 0
        msg = getattr(app, "current_dialog_message", "") if app else ""
        btn_count = getattr(app, "current_dialog_button_count", 0) if app else 0
        return {
            "open_dialog_count": count,
            "current_dialog_message": msg,
            "current_dialog_button_count": btn_count,
            "has_open_dialog": count > 0,
        }

    def live12_dialog_press(self, button_index: int) -> Dict[str, Any]:
        btn = int(button_index)
        app = self.application()
        count = getattr(app, "open_dialog_count", 0) if app else 0
        if count == 0:
            return {
                "status": "no_open_dialogs",
                "open_dialog_count": 0,
                "button_index": btn,
                "pressed_button_index": btn,
            }

        btn_count = getattr(app, "current_dialog_button_count", 0) if app else 0
        if btn < 0 or (btn_count and btn >= int(btn_count)):
            raise IndexError(f"Dialog button index {btn} out of range (0..{int(btn_count) - 1})")

        msg = getattr(app, "current_dialog_message", "") if app else ""
        if app and hasattr(app, "press_current_dialog_button"):
            try:
                app.press_current_dialog_button(btn)
            except RuntimeError as e:
                new_count = getattr(app, "open_dialog_count", 0) if app else 0
                if new_count == 0:
                    return {
                        "status": "no_open_dialogs",
                        "open_dialog_count": 0,
                        "button_index": btn,
                        "pressed_button_index": btn,
                    }
                if any(tok in str(e).lower() for tok in ("index", "range", "button")):
                    raise IndexError(f"Invalid dialog button index {btn}: {e}") from e
                raise

        new_count = getattr(app, "open_dialog_count", 0) if app else 0
        return {
            "status": "button_pressed",
            "button_index": btn,
            "pressed_button_index": btn,
            "dismissed_dialog": msg,
            "open_dialog_count": new_count,
        }

    def live12_os_save_set(
        self,
        destination_path: str,
        overwrite: bool = False,
        timeout_sec: float = 30.0,
    ) -> Dict[str, Any]:
        if self.song() is not None:
            raise NotImplementedError(
                "OS Save Set dialog cannot be automated inside Live's Python ControlSurface; execute via McpServer/dialogs.py UI driver"
            )
        parent = os.path.dirname(destination_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        return {"saved": True, "path": destination_path, "overwrite": bool(overwrite)}

    def live12_os_open_set(
        self,
        als_path: str,
        discard_unsaved: bool = False,
        timeout_sec: float = 30.0,
    ) -> Dict[str, Any]:
        if self.song() is not None:
            raise NotImplementedError(
                "OS Open Set dialog cannot be automated inside Live's Python ControlSurface; execute via McpServer/dialogs.py UI driver"
            )
        return {"opened": True, "path": als_path, "discard_unsaved": bool(discard_unsaved)}

    def live12_os_export_audio(
        self,
        destination_wav_path: str,
        render_settings: Optional[dict] = None,
        overwrite: bool = False,
        timeout_sec: float = 120.0,
    ) -> Dict[str, Any]:
        if self.song() is not None:
            raise NotImplementedError(
                "OS Audio Export dialog cannot be automated inside Live's Python ControlSurface; execute via McpServer/dialogs.py UI driver"
            )
        parent = os.path.dirname(destination_wav_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        return {"exported": True, "destination": destination_wav_path, "overwrite": bool(overwrite)}

    def close_open_undo_steps(self) -> int:
        """Closes any unbalanced open Live undo steps on disconnect or teardown."""
        closed = 0
        s = self.song()
        while getattr(self, "_undo_depth", 0) > 0:
            self._undo_depth -= 1
            if s and hasattr(s, "end_undo_step"):
                try:
                    s.end_undo_step()
                except RuntimeError:
                    break
            closed += 1
        return closed

    def live12_undo_redo(self, action: str) -> Dict[str, Any]:
        valid_actions = ("undo", "redo", "status", "begin_step", "end_step")
        if action not in valid_actions:
            raise ValueError(f"Invalid undo action '{action}', must be one of {valid_actions}")

        s = self.song()
        res: Dict[str, Any] = {"status": "success", "action": action, "undo_depth": self._undo_depth}

        if action == "undo":
            if s:
                if getattr(s, "can_undo", False) and hasattr(s, "undo"):
                    s.undo()
                    res["undone"] = True
                else:
                    res["undone"] = False
                    res["status"] = "nothing_to_undo"
            else:
                res["undone"] = True
        elif action == "redo":
            if s:
                if getattr(s, "can_redo", False) and hasattr(s, "redo"):
                    s.redo()
                    res["redone"] = True
                else:
                    res["redone"] = False
                    res["status"] = "nothing_to_redo"
            else:
                res["redone"] = True
        elif action == "status":
            can_undo = bool(getattr(s, "can_undo", True)) if s else True
            can_redo = bool(getattr(s, "can_redo", False)) if s else False
            res["can_undo"] = can_undo
            res["can_redo"] = can_redo
        elif action == "begin_step":
            if self._undo_depth >= MAX_UNDO_DEPTH:
                raise RuntimeError(f"Maximum undo step depth ({MAX_UNDO_DEPTH}) reached")
            if s and hasattr(s, "begin_undo_step"):
                s.begin_undo_step()
            self._undo_depth += 1
            res["step_active"] = True
            res["undo_depth"] = self._undo_depth
        elif action == "end_step":
            if self._undo_depth <= 0:
                raise RuntimeError("No open undo step to end")
            if s and hasattr(s, "end_undo_step"):
                s.end_undo_step()
            self._undo_depth -= 1
            res["step_active"] = self._undo_depth > 0
            res["undo_depth"] = self._undo_depth

        return res

    # -------------------------------------------------------------------------
    # Domain 6: Universal LOM Escape Hatch
    # -------------------------------------------------------------------------

    def live12_lom_inspect(self, target_path: str) -> Dict[str, Any]:
        return lom_inspect(self.root_getter, target_path)

    def live12_lom_get(self, target_path: str, property_name: str) -> Dict[str, Any]:
        return lom_get(self.root_getter, target_path, property_name)

    def live12_lom_set(self, target_path: str, property_name: str, value: Any) -> Dict[str, Any]:
        return lom_set(self.root_getter, target_path, property_name, value)

    def live12_lom_call(
        self,
        target_path: str,
        method_name: str,
        args: Optional[list] = None,
        kwargs: Optional[dict] = None,
    ) -> Dict[str, Any]:
        return lom_call(self.root_getter, target_path, method_name, args, kwargs)

    def live12_bridge_reload(self, reset_state: bool = False) -> Dict[str, Any]:
        """
        Hot-reloads the Live12Bridge modules (reflection, handlers) in-memory
        and updates the active handlers instance on the ControlSurface.
        """
        import importlib
        from . import reflection as reflection_mod
        from . import handlers as handlers_mod
        importlib.reload(reflection_mod)
        importlib.reload(handlers_mod)
        new_handlers = handlers_mod.BridgeHandlers(self.cs)
        if not reset_state:
            for attr in (
                "_undo_depths",
                "_current_tuning_system",
                "_top_device_cache",
                "_wavetable_matrices",
                "_simpler_state",
            ):
                if hasattr(self, attr):
                    setattr(new_handlers, attr, getattr(self, attr))
        if hasattr(self.cs, "_handlers"):
            self.cs._handlers = new_handlers
        return {
            "status": "reloaded",
            "message": "Live12Bridge modules reloaded successfully",
            "reset_state": bool(reset_state),
            "handlers_count": len([m for m in dir(new_handlers) if m.startswith("live12_")]),
        }


def normalize_method_name(name: str) -> str:
    """Normalizes method names to canonical live12_* handler form."""
    norm = name.strip().replace(".", "_")
    if not norm.startswith("live12_"):
        norm = f"live12_{norm}"
    return norm


def dispatch_tool_call(handlers: BridgeHandlers, method_name: str, params: Dict[str, Any]) -> Any:
    """
    Finds and invokes the matching structured public live12_* handler or reflection method.
    """
    raw_name = str(method_name or "").strip()
    if raw_name.startswith("_") or raw_name.startswith("live12__"):
        raise AttributeError(f"Private method '{method_name}' cannot be dispatched")
    canonical_name = normalize_method_name(raw_name)
    if not canonical_name.startswith("live12_") or canonical_name.startswith("live12__"):
        raise AttributeError(f"Method '{method_name}' is not a public live12_* handler")
    method = getattr(handlers, canonical_name, None)
    if method and callable(method):
        call_params = {} if params is None else params
        if not isinstance(call_params, dict):
            raise ValueError("Tool call params must be a JSON object")
        return method(**call_params)

    raise AttributeError(f"Method '{method_name}' (canonical: '{canonical_name}') not found in BridgeHandlers")
