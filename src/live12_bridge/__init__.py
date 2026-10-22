"""
Live 12 Bridge - Remote Script Entry Point
==========================================
Ableton Live 12 Control Surface entry point and capability declarations.
"""

from __future__ import annotations

from typing import Any, Dict

from .bridge import Live12Bridge, Live12ControlSurface
from .handlers import BridgeHandlers
from .reflection import (
    liveobj_valid,
    lom_call,
    lom_get,
    lom_inspect,
    lom_set,
    midi_note_to_dict,
    dict_to_midi_note_spec,
)


def create_instance(c_instance: Any) -> Live12ControlSurface:
    """
    Mandatory factory function called by Ableton Live C++ core on script initialization.
    """
    return Live12ControlSurface(c_instance)


def get_capabilities() -> Dict[str, Any]:
    """
    Optional capability flags for Ableton Live Control Surface manager.
    """
    return {
        "AUTO_LOAD_KEY": True,
        "PORTS_KEY": [],
        "SCRIPT": "Live12Bridge",
    }


__all__ = [
    "create_instance",
    "get_capabilities",
    "Live12ControlSurface",
    "Live12Bridge",
    "BridgeHandlers",
    "liveobj_valid",
    "lom_inspect",
    "lom_get",
    "lom_set",
    "lom_call",
    "midi_note_to_dict",
    "dict_to_midi_note_spec",
]
