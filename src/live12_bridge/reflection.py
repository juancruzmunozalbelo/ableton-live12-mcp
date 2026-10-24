"""
Live 12 Bridge - Dynamic LOM Reflection Engine
=============================================
Provides introspection, path navigation, property getters/setters,
safe method invocation with Live.Base pointer validation (`liveobj_valid`),
and full Live 12 extended MIDI note conversions.
"""

from __future__ import annotations

import inspect
import math
import re
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

try:
    import Live
except ImportError:
    Live = None


# Standard Live 12 MIDI note attributes
MIDI_NOTE_ATTRS = (
    "note_id",
    "pitch",
    "start_time",
    "duration",
    "velocity",
    "mute",
    "probability",
    "velocity_deviation",
    "release_velocity",
)

REQUIRED_MIDI_NOTE_ATTRS = ("pitch", "start_time", "duration")


class MockMidiNoteSpecification:
    """Fallback specification container for environments outside live Ableton engine."""

    def __init__(
        self,
        pitch: int,
        start_time: float,
        duration: float,
        velocity: float = 100.0,
        velocity_deviation: float = 0.0,
        release_velocity: float = 64.0,
        probability: float = 1.0,
        mute: bool = False,
    ):
        self.pitch = int(pitch)
        self.start_time = float(start_time)
        self.duration = float(duration)
        self.velocity = float(velocity)
        self.velocity_deviation = float(velocity_deviation)
        self.release_velocity = float(release_velocity)
        self.probability = float(probability)
        self.mute = bool(mute)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pitch": self.pitch,
            "start_time": self.start_time,
            "duration": self.duration,
            "velocity": self.velocity,
            "velocity_deviation": self.velocity_deviation,
            "release_velocity": self.release_velocity,
            "probability": self.probability,
            "mute": self.mute,
        }


def liveobj_valid(obj: Any) -> bool:
    """
    Validates whether a Boost.Python Live Object Model pointer is still alive.
    Deleted C++ objects raise RuntimeError or ReferenceError on attribute access or equality checks.
    """
    if obj is None:
        return False
    try:
        # Boost.Python objects raise RuntimeError or return False if C++ pointer is deleted
        return bool(obj != None)
    except (RuntimeError, ReferenceError, AttributeError):
        return False


def serialize_lom_value(val: Any, depth: int = 0) -> Any:
    """
    Recursively serializes primitives, collections, and Live objects into JSON-safe types.
    """
    if depth > 5:
        return str(val)

    if val is None or isinstance(val, (bool, int, str)):
        return val

    if isinstance(val, float):
        if math.isnan(val) or math.isinf(val):
            return str(val)
        return val

    if isinstance(val, (list, tuple, set)) or "Vector" in type(val).__name__:
        # For long lists of complex objects, summarize or serialize items
        return [serialize_lom_value(item, depth + 1) for item in val]

    if isinstance(val, dict):
        return {str(k): serialize_lom_value(v, depth + 1) for k, v in val.items()}

    # Check if it has a to_dict method
    if hasattr(val, "to_dict") and callable(val.to_dict):
        try:
            return serialize_lom_value(val.to_dict(), depth + 1)
        except Exception:
            pass

    # Live object or generic Python object
    if liveobj_valid(val):
        info: Dict[str, Any] = {
            "type": type(val).__name__,
        }
        if hasattr(val, "name") and not callable(getattr(val, "name")):
            info["name"] = str(getattr(val, "name"))
        if hasattr(val, "_live_ptr"):
            info["live_ptr"] = getattr(val, "_live_ptr")
        return info

    return str(val)


def midi_note_to_dict(note: Any) -> Dict[str, Any]:
    """
    Converts a Live 12 Live.Clip.MidiNote C++ object or dictionary to a complete note dict.
    """
    if isinstance(note, dict):
        return {
            "note_id": note.get("note_id", 0),
            "pitch": int(note.get("pitch", 60)),
            "start_time": float(note.get("start_time", 0.0)),
            "duration": float(note.get("duration", 1.0)),
            "velocity": float(note.get("velocity", 100.0)),
            "velocity_deviation": float(note.get("velocity_deviation", 0.0)),
            "release_velocity": float(note.get("release_velocity", 64.0)),
            "probability": float(note.get("probability", 1.0)),
            "mute": bool(note.get("mute", False)),
        }

    return {
        "note_id": getattr(note, "note_id", 0),
        "pitch": int(getattr(note, "pitch", 60)),
        "start_time": float(getattr(note, "start_time", 0.0)),
        "duration": float(getattr(note, "duration", 1.0)),
        "velocity": float(getattr(note, "velocity", 100.0)),
        "velocity_deviation": float(getattr(note, "velocity_deviation", 0.0)),
        "release_velocity": float(getattr(note, "release_velocity", 64.0)),
        "probability": float(getattr(note, "probability", 1.0)),
        "mute": bool(getattr(note, "mute", False)),
    }


def dict_to_midi_note_spec(n: Dict[str, Any]) -> Any:
    """
    Instantiates a native Live.Clip.MidiNoteSpecification (or fallback Mock) from dictionary.
    """
    for required in REQUIRED_MIDI_NOTE_ATTRS:
        if required not in n:
            raise ValueError(f"Missing required note specification attribute '{required}'")

    pitch = int(n["pitch"])
    start_time = float(n["start_time"])
    duration = float(n["duration"])
    velocity = float(n.get("velocity", 100.0))
    velocity_deviation = float(n.get("velocity_deviation", 0.0))
    release_velocity = float(n.get("release_velocity", 64.0))
    probability = float(n.get("probability", 1.0))
    mute = bool(n.get("mute", False))

    if Live and hasattr(Live, "Clip") and hasattr(Live.Clip, "MidiNoteSpecification"):
        return Live.Clip.MidiNoteSpecification(
            pitch=pitch,
            start_time=start_time,
            duration=duration,
            velocity=velocity,
            velocity_deviation=velocity_deviation,
            release_velocity=release_velocity,
            probability=probability,
            mute=mute,
        )

    return MockMidiNoteSpecification(
        pitch=pitch,
        start_time=start_time,
        duration=duration,
        velocity=velocity,
        velocity_deviation=velocity_deviation,
        release_velocity=release_velocity,
        probability=probability,
        mute=mute,
    )


def resolve_path(root_getter: Callable[[str], Any], path: str) -> Any:
    """
    Navigates through the Live Object Model hierarchy given a delimited path string.
    Supported delimiters: dot (.), slash (/), or space.
    Examples:
      'live_set.tracks.0.clip_slots.0.clip'
      'live_app.view'
      'live_set/tracks/1/devices/0'
      'tracks 0 devices 0 parameters 1'
    """
    if not path or not path.strip():
        raise ValueError("target_path cannot be empty")

    tokens = [t.strip() for t in re.findall(r'[^.\[\]\s/]+', path.strip()) if t.strip()]
    if not tokens:
        raise ValueError("target_path cannot be empty")

    for token in tokens:
        if token.startswith("_"):
            raise PermissionError(f"Access to private or protected attribute '{token}' is prohibited")

    first = tokens[0].lower()
    if first in ("live_set", "song"):
        obj = root_getter("song")
        tokens = tokens[1:]
    elif first in ("live_app", "app", "application"):
        obj = root_getter("application")
        tokens = tokens[1:]
    elif first in ("control_surfaces", "cs"):
        obj = root_getter("control_surfaces")
        tokens = tokens[1:]
    elif first in ("this_device", "self"):
        obj = root_getter("this_device")
        tokens = tokens[1:]
    else:
        # Default root is song, tokens[0] may be 'tracks', 'scenes', etc.
        obj = root_getter("song")

    current_path = []
    for token in tokens:
        if not liveobj_valid(obj):
            raise RuntimeError(f"Live object at '{'.'.join(current_path)}' is invalid or has been deleted")

        # Check integer indexing
        try:
            idx = int(token)
            is_int = True
        except ValueError:
            is_int = False

        if is_int:
            if isinstance(obj, dict):
                obj = obj[idx]
            elif isinstance(obj, (list, tuple)) or hasattr(obj, "__getitem__"):
                try:
                    c_len = len(obj)
                    if 0 <= idx < c_len:
                        obj = obj[idx]
                    else:
                        raise IndexError(f"Index {idx} out of range for collection of size {c_len}")
                except (TypeError, AttributeError):
                    obj = obj[idx]
            else:
                raise TypeError(f"Cannot index into object of type '{type(obj).__name__}'")
        else:
            if isinstance(obj, dict) and token in obj:
                obj = obj[token]
            elif hasattr(obj, token):
                obj = getattr(obj, token)
            else:
                raise AttributeError(f"'{type(obj).__name__}' object has no attribute '{token}'")

        current_path.append(token)

    return obj


def lom_inspect(root_getter: Callable[[str], Any], target_path: str) -> Dict[str, Any]:
    """
    Introspects an object at target_path in the Live Object Model,
    returning its type, available properties, methods, and docstring.
    """
    obj = resolve_path(root_getter, target_path)

    # Determine type name
    type_obj = type(obj)
    module_name = getattr(type_obj, "__module__", "")
    type_name = getattr(type_obj, "__name__", str(type_obj))
    if module_name and module_name != "builtins":
        full_type = f"{module_name}.{type_name}"
    else:
        full_type = type_name
    if not full_type.startswith("Live.") and any(k in full_type for k in ("Track", "Clip", "Device", "Song", "Scene", "Chain", "Application")):
        full_type = f"Live.{full_type}"

    props = []
    methods = []

    for attr in dir(obj):
        if attr.startswith("_"):
            continue
        try:
            val = getattr(obj, attr)
            if callable(val):
                methods.append(attr)
            else:
                props.append(attr)
        except Exception:
            props.append(attr)

    doc = inspect.getdoc(obj) or getattr(obj, "__doc__", None)

    return {
        "path": target_path,
        "type": full_type,
        "properties": sorted(props),
        "methods": sorted(methods),
        "doc": doc,
    }


def lom_get(root_getter: Callable[[str], Any], target_path: str, property_name: str) -> Dict[str, Any]:
    """
    Reads a property value on the object resolved by target_path.
    """
    if property_name.startswith("_"):
        raise PermissionError(f"Access to private or protected attribute '{property_name}' is prohibited")

    obj = resolve_path(root_getter, target_path)
    if not liveobj_valid(obj):
        raise RuntimeError(f"Target object at '{target_path}' is invalid or deleted")

    if not hasattr(obj, property_name):
        raise AttributeError(f"'{type(obj).__name__}' object has no attribute '{property_name}'")

    val = getattr(obj, property_name)
    serialized = serialize_lom_value(val)
    return {
        "path": target_path,
        "property": property_name,
        "value": serialized,
    }


def lom_set(
    root_getter: Callable[[str], Any],
    target_path: str,
    property_name: str,
    value: Any,
) -> Dict[str, Any]:
    """
    Mutates a property value on the object resolved by target_path.
    """
    if property_name.startswith("_"):
        raise PermissionError(f"Access to private or protected attribute '{property_name}' is prohibited")

    obj = resolve_path(root_getter, target_path)
    if not liveobj_valid(obj):
        raise RuntimeError(f"Target object at '{target_path}' is invalid or deleted")

    if not hasattr(obj, property_name):
        raise AttributeError(f"'{type(obj).__name__}' object has no attribute '{property_name}'")

    # Type coercion when appropriate
    curr_val = getattr(obj, property_name, None)
    assigned_val = value
    if isinstance(curr_val, float) and not isinstance(value, float):
        try:
            assigned_val = float(value)
        except (ValueError, TypeError):
            pass
    elif isinstance(curr_val, int) and not isinstance(curr_val, bool) and not isinstance(value, int):
        try:
            assigned_val = int(value)
        except (ValueError, TypeError):
            pass
    elif isinstance(curr_val, bool) and not isinstance(value, bool):
        assigned_val = bool(value)

    setattr(obj, property_name, assigned_val)
    new_val = getattr(obj, property_name)
    return {
        "path": target_path,
        "property": property_name,
        "new_value": serialize_lom_value(new_val),
    }


def lom_call(
    root_getter: Callable[[str], Any],
    target_path: str,
    method_name: str,
    args: Optional[List[Any]] = None,
    kwargs: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Invokes a method on the object resolved by target_path.
    """
    if method_name.startswith("_"):
        raise PermissionError(f"Access to private or protected attribute '{method_name}' is prohibited")

    obj = resolve_path(root_getter, target_path)
    if not liveobj_valid(obj):
        raise RuntimeError(f"Target object at '{target_path}' is invalid or deleted")

    if not hasattr(obj, method_name):
        raise AttributeError(f"'{type(obj).__name__}' object has no method '{method_name}'")

    method = getattr(obj, method_name)
    call_args = list(args or [])
    call_kwargs = dict(kwargs or {})

    # Specialized conversion for note operations in Live 12
    if method_name == "add_new_notes" and call_args:
        notes_arg = call_args[0]
        if isinstance(notes_arg, (list, tuple)):
            converted_notes = []
            for n in notes_arg:
                if isinstance(n, dict):
                    converted_notes.append(dict_to_midi_note_spec(n))
                else:
                    converted_notes.append(n)
            call_args[0] = tuple(converted_notes)

    result = method(*call_args, **call_kwargs)
    serialized = serialize_lom_value(result)
    if serialized is None:
        serialized = True
    return {
        "path": target_path,
        "method": method_name,
        "result": serialized,
    }
