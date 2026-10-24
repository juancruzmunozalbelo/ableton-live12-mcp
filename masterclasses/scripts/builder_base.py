"""
Ableton Live 12 MCP - Masterclass Reconstructive Builder Base
============================================================
Shared infrastructure for building Ableton Live 12 sets via MCP RPC on 127.0.0.1:11246,
including in-process session reset, set saving, audio rendering, and integrity verification.
"""

from __future__ import annotations

import gzip
import json
import logging
import math
import os
import shutil
import subprocess
import time
import wave
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple, Union

from ableton_live12_mcp.client import Live12Client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("masterclass.builder_base")


# ==============================================================================
# In-Process Session Reset Sequence
# ==============================================================================

def clean_session_reset(
    client: Live12Client,
    target_tempo: float = 126.0,
    target_scale_root: int = 0,
    target_scale_name: str = "Minor",
) -> Dict[str, Any]:
    """
    Executes a complete, non-destructive session reset over RPC on 127.0.0.1:11246.
    Cleans all user tracks, return tracks, master devices, locators, and resets global properties.
    Does NOT restart Live or invoke GUI New Live Set (Cmd+N).
    """
    logger.info("Executing clean session reset via RPC...")

    # 1. Neutralize Transport & Playhead
    client.call_tool("live12_transport_stop")
    try:
        client.call_tool("live12_lom_set", {"target_path": "song", "property_name": "record_mode", "value": False})
        client.call_tool("live12_lom_set", {"target_path": "song", "property_name": "session_record", "value": False})
        client.call_tool("live12_lom_set", {"target_path": "song", "property_name": "current_song_time", "value": 0.0})
    except Exception as e:
        logger.debug("Minor exception resetting playhead/record properties: %s", e)

    client.call_tool("live12_transport_set_loop", {"enabled": False, "start": 0.0, "length": 4.0})
    client.call_tool("live12_transport_set_punch", {"punch_in": False, "punch_out": False})
    client.call_tool("live12_transport_set_metronome", {"enabled": False})
    client.call_tool("live12_transport_set_overdub", {"overdub": False})

    # 2. Delete All User Tracks in Reverse Order
    while True:
        state = client.call_tool("live12_song_get_state")
        tracks_count = state.get("tracks_count", 0)
        if tracks_count <= 0:
            break
        if tracks_count == 1:
            try:
                client.call_tool("live12_track_delete", {"track_index": 0})
            except Exception:
                # If Live protects the last track, create a temporary track and delete track 0
                try:
                    client.call_tool("live12_track_create", {"type": "midi", "index": -1})
                    client.call_tool("live12_track_delete", {"track_index": 0})
                except Exception:
                    pass
            break
        client.call_tool("live12_track_delete", {"track_index": tracks_count - 1})

    # 3. Delete All Return Tracks in Reverse Order
    try:
        ret_res = client.call_tool("live12_lom_get", {"target_path": "song", "property_name": "return_tracks"})
        return_tracks = ret_res.get("value", []) if isinstance(ret_res, dict) or hasattr(ret_res, "get") else []
        for idx in range(len(return_tracks) - 1, -1, -1):
            try:
                client.call_tool("live12_lom_call", {
                    "target_path": "song",
                    "method_name": "delete_return_track",
                    "args": [idx],
                })
            except Exception as e:
                logger.debug("Could not delete return track %d: %s", idx, e)
    except Exception as e:
        logger.debug("Could not inspect return tracks during reset: %s", e)

    # 4. Clean Master Track Devices
    try:
        master_devs_res = client.call_tool("live12_lom_get", {"target_path": "song.master_track", "property_name": "devices"})
        m_devs = master_devs_res.get("value", []) if isinstance(master_devs_res, dict) or hasattr(master_devs_res, "get") else []
        for idx in range(len(m_devs) - 1, -1, -1):
            try:
                client.call_tool("live12_lom_call", {
                    "target_path": "song.master_track",
                    "method_name": "delete_device",
                    "args": [idx],
                })
            except Exception as e:
                logger.debug("Could not delete master device %d: %s", idx, e)
    except Exception as e:
        logger.debug("Could not inspect master devices during reset: %s", e)

    # 5. Clear All Arrangement Locators (Cue Points)
    try:
        cues_res = client.call_tool("live12_cue_point_control", {"action": "list"})
        cps = cues_res.get("cue_points", []) if isinstance(cues_res, dict) or hasattr(cues_res, "get") else []
        for idx in range(len(cps) - 1, -1, -1):
            client.call_tool("live12_cue_point_control", {"action": "delete", "cue_index": idx})
    except Exception as e:
        logger.debug("Could not clear cues: %s", e)

    # 6. Reset Global Song & Musical Parameters
    client.call_tool("live12_transport_set_tempo", {"tempo": float(target_tempo)})
    client.call_tool("live12_transport_set_time_signature", {"numerator": 4, "denominator": 4})
    client.call_tool("live12_song_set_scale", {"root_note": int(target_scale_root), "scale_name": str(target_scale_name)})
    try:
        client.call_tool("live12_song_set_tuning_system", {"tuning_name": "Equal Temperament"})
    except Exception:
        pass

    # 7. Reset View
    try:
        client.call_tool("live12_view_switch", {"view": "Arranger"})
        client.call_tool("live12_view_switch", {"view": "Detail/DeviceChain"})
    except Exception:
        pass

    final_state = client.call_tool("live12_song_get_state")
    logger.info("Session reset complete. Clean state: %s", final_state.raw)
    return final_state.raw


# ==============================================================================
# Set Saving & Audio Export Helpers
# ==============================================================================

def save_live_set(client: Live12Client, destination_als_path: str, timeout_sec: float = 25.0) -> Dict[str, Any]:
    """
    Saves the current live set to destination_als_path via AppleScript UI automation
    and locates/consolidates the resulting .als on disk.
    """
    abs_path = os.path.abspath(os.path.expanduser(destination_als_path))
    folder_path = os.path.dirname(abs_path)
    file_name = os.path.basename(abs_path)
    base_name = os.path.splitext(file_name)[0]
    os.makedirs(folder_path, exist_ok=True)

    logger.info("Saving Live Set to: %s...", abs_path)
    client.call_tool("live12_transport_stop")
    time.sleep(0.3)

    script = f'''
    set targetFolder to "{folder_path}"
    set targetFile to "{base_name}"

    tell application "System Events"
        set liveProc to (first process whose bundle identifier is "com.ableton.live")
        set frontmost of liveProc to true
        delay 0.3

        -- Trigger Save Live Set As... (Shift+Cmd+S)
        keystroke "s" using {{command down, shift down}}
        delay 0.6

        -- Open Go To Folder
        keystroke "g" using {{command down, shift down}}
        delay 0.5

        -- Type targetFolder and confirm
        keystroke targetFolder
        delay 0.2
        keystroke return
        delay 0.5

        -- Type targetFile and confirm
        keystroke targetFile
        delay 0.3
        keystroke return
        delay 0.5

        -- Replace if asked
        delay 0.4
        tell liveProc
            repeat with w in windows
                if exists sheet 1 of w then
                    tell sheet 1 of w
                        if exists button "Replace" then
                            click button "Replace"
                        else if exists button "Reemplazar" then
                            click button "Reemplazar"
                        end if
                    end tell
                end if
            end repeat
        end tell
    end tell
    return "done"
    '''
    subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=timeout_sec)

    # Poll for file creation either directly at abs_path or within any Project directory
    start_time = time.time()
    found_als: Optional[str] = None
    project_dir = os.path.join(folder_path, f"{base_name} Project")
    project_als = os.path.join(project_dir, f"{base_name}.als")

    while time.time() - start_time < timeout_sec:
        if os.path.exists(abs_path) and os.path.getsize(abs_path) > 1024:
            found_als = abs_path
            break
        if os.path.exists(project_als) and os.path.getsize(project_als) > 1024:
            shutil.copy2(project_als, abs_path)
            found_als = abs_path
            break

        # Search recursively for any recently created .als in folder_path
        for root_dir, _, files in os.walk(folder_path):
            for f in files:
                if f.endswith(".als") and base_name in f:
                    candidate = os.path.join(root_dir, f)
                    if os.path.getsize(candidate) > 1024:
                        shutil.copy2(candidate, abs_path)
                        found_als = abs_path
                        break
            if found_als:
                break
        if found_als:
            break
        time.sleep(0.4)

    if not found_als or not os.path.exists(found_als):
        raise TimeoutError(f"Failed to verify saved Live Set at '{abs_path}' after {timeout_sec}s")

    file_size = os.path.getsize(found_als)
    logger.info("Live Set successfully saved and consolidated at %s (%d bytes)", found_als, file_size)
    return {"saved": True, "path": found_als, "size_bytes": file_size}


def export_audio_bounce(
    client: Live12Client,
    destination_wav_path: str,
    duration_beats: float = 64.0,
    timeout_sec: float = 60.0,
) -> Dict[str, Any]:
    """
    Exports audio bounce for the specified arrangement duration.
    Configures arrangement loop, triggers Export Audio/Video, drives Cocoa Save panel,
    stabilizes the output, and converts to 24-bit PCM WAV if exported as AIFF.
    """
    abs_path = os.path.abspath(os.path.expanduser(destination_wav_path))
    folder_path = os.path.dirname(abs_path)
    file_name = os.path.basename(abs_path)
    base_name = os.path.splitext(file_name)[0]
    os.makedirs(folder_path, exist_ok=True)
    aif_path = os.path.join(folder_path, f"{base_name}.aif")
    wav_aif_path = os.path.join(folder_path, f"{file_name}.aif")

    # 1. Clean stale audio and asd files for base_name
    for f in os.listdir(folder_path):
        if base_name in f and (f.endswith(".aif") or f.endswith(".wav") or f.endswith(".asd")):
            try:
                os.remove(os.path.join(folder_path, f))
            except Exception:
                pass

    # 2. Configure arrangement loop boundaries
    logger.info("Configuring export arrangement loop (start: 0.0, length: %.1f beats)...", duration_beats)
    client.call_tool("live12_transport_stop")
    client.call_tool("live12_transport_set_loop", {
        "enabled": True,
        "start": 0.0,
        "length": float(duration_beats),
    })
    time.sleep(0.3)

    # 3. Trigger Export Audio via AppleScript menu click and dialog automation
    logger.info("Triggering Export Audio/Video menu item in Ableton Live...")
    script = f'''
    set targetFolder to "{folder_path}"
    set targetFile to "{base_name}"

    tell application "System Events"
        set liveProc to (first process whose bundle identifier is "com.ableton.live")
        set frontmost of liveProc to true
        delay 0.2

        -- Click Export Audio/Video... from File menu
        tell liveProc
            click menu item "Export Audio/Video..." of menu "File" of menu bar 1
        end tell
        delay 0.6

        -- Confirm export settings by pressing Return
        keystroke return
        delay 0.8

        -- Open Go To Folder
        keystroke "g" using {{command down, shift down}}
        delay 0.5
        keystroke targetFolder
        delay 0.2
        keystroke return
        delay 0.5

        -- Type targetFile and confirm
        keystroke targetFile
        delay 0.3
        keystroke return
        delay 0.5

        -- Replace if prompted
        delay 0.4
        tell liveProc
            repeat with w in windows
                if exists sheet 1 of w then
                    tell sheet 1 of w
                        if exists button "Replace" then
                            click button "Replace"
                        else if exists button "Reemplazar" then
                            click button "Reemplazar"
                        end if
                    end tell
                end if
            end repeat
        end tell
    end tell
    return "done"
    '''
    subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=timeout_sec)

    # 4. Wait for audio rendering to stabilize on disk
    logger.info("Waiting for audio bounce completion and file stabilization...")
    start_time = time.time()
    candidate_audio: Optional[str] = None
    last_size = -1
    stable_count = 0

    while time.time() - start_time < timeout_sec:
        # Check all possible candidate files Live may write (.wav, .aif, .wav.aif, or any audio in folder)
        for cand in [abs_path, aif_path, wav_aif_path]:
            if os.path.exists(cand) and os.path.getsize(cand) > 65536:
                curr_size = os.path.getsize(cand)
                if curr_size == last_size:
                    stable_count += 1
                else:
                    stable_count = 0
                    last_size = curr_size

                if stable_count >= 3:
                    candidate_audio = cand
                    break
        if candidate_audio:
            break

        # Also search folder for any audio starting with base_name
        for f in os.listdir(folder_path):
            if (f.endswith(".wav") or f.endswith(".aif") or f.endswith(".aiff")) and base_name in f:
                cand = os.path.join(folder_path, f)
                if os.path.getsize(cand) > 65536:
                    curr_size = os.path.getsize(cand)
                    if curr_size == last_size:
                        stable_count += 1
                    else:
                        stable_count = 0
                        last_size = curr_size
                    if stable_count >= 3:
                        candidate_audio = cand
                        break
        if candidate_audio:
            break
        time.sleep(0.5)

    if not candidate_audio:
        raise TimeoutError(f"Audio export failed: no stabilized audio file found at '{abs_path}' within {timeout_sec}s")

    # 5. Convert to standardized 24-bit PCM WAV if needed
    if candidate_audio != abs_path or not candidate_audio.endswith(".wav"):
        logger.info("Standardizing exported audio %s -> %s via ffmpeg...", candidate_audio, abs_path)
        subprocess.run(
            ["ffmpeg", "-y", "-i", candidate_audio, "-c:a", "pcm_s24le", abs_path],
            check=True,
            capture_output=True,
        )

    file_size = os.path.getsize(abs_path)
    logger.info("Audio bounce successfully generated at %s (%d bytes)", abs_path, file_size)
    return {"exported": True, "path": abs_path, "size_bytes": file_size}


# ==============================================================================
# Verification Engines
# ==============================================================================

def verify_als_integrity(als_path: str, expected_min_tracks: int = 1) -> Dict[str, Any]:
    """
    Decompresses and parses an Ableton Live Set (.als) XML to verify integrity,
    creator version, tracks count, and locators.
    """
    abs_path = os.path.abspath(os.path.expanduser(als_path))
    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"ALS file does not exist: {abs_path}")

    file_size = os.path.getsize(abs_path)
    if file_size < 1000:
        raise ValueError(f"ALS file is too small ({file_size} bytes): {abs_path}")

    with open(abs_path, "rb") as f:
        magic = f.read(2)
        if magic != b"\x1f\x8b":
            raise ValueError(f"File {abs_path} is not a valid gzip container (magic {magic!r})")

    with gzip.open(abs_path, "rb") as gz:
        xml_bytes = gz.read()

    root = ET.fromstring(xml_bytes)
    if root.tag != "Ableton":
        raise ValueError(f"Expected root tag <Ableton>, got <{root.tag}> in {abs_path}")

    live_set = root.find("LiveSet")
    if live_set is None:
        raise ValueError(f"Missing <LiveSet> in {abs_path}")

    tracks_elem = live_set.find("Tracks")
    tracks = list(tracks_elem) if tracks_elem is not None else []
    if len(tracks) < expected_min_tracks:
        raise ValueError(f"Expected at least {expected_min_tracks} tracks, found {len(tracks)}")

    locators_elem = live_set.find("Locators")
    locators = []
    if locators_elem is not None:
        for loc in locators_elem.findall("Locator"):
            name_elem = loc.find("Name")
            name = name_elem.attrib.get("Value", "") if name_elem is not None else ""
            time_elem = loc.find("Time")
            t = float(time_elem.attrib.get("Value", 0.0)) if time_elem is not None else 0.0
            locators.append({"name": name, "time": t})

    return {
        "verified": True,
        "path": abs_path,
        "file_size_bytes": file_size,
        "creator": root.attrib.get("Creator", "Unknown"),
        "major_version": root.attrib.get("MajorVersion"),
        "minor_version": root.attrib.get("MinorVersion"),
        "user_tracks_count": len(tracks),
        "locators_count": len(locators),
        "locators": locators,
    }


def verify_pcm_wav_energy(
    wav_path: str,
    min_duration_sec: float = 10.0,
    min_rms_dbfs: float = -40.0,
) -> Dict[str, Any]:
    """
    Verifies that a WAV file has valid RIFF headers, valid PCM audio data,
    duration >= min_duration_sec, and non-zero RMS energy > min_rms_dbfs.
    """
    abs_path = os.path.abspath(os.path.expanduser(wav_path))
    if not os.path.exists(abs_path):
        return {"valid": False, "error": f"WAV file does not exist: {abs_path}"}

    file_size = os.path.getsize(abs_path)
    if file_size < 44:
        return {"valid": False, "error": f"File size ({file_size} bytes) smaller than RIFF header"}

    with wave.open(abs_path, "rb") as wf:
        channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()
        nframes = wf.getnframes()
        comptype = wf.getcomptype()

        if comptype != "NONE":
            return {"valid": False, "error": f"Unsupported compression: {comptype}"}

        if nframes == 0 or framerate == 0:
            return {"valid": False, "error": "WAV file contains 0 audio frames"}

        duration_sec = nframes / float(framerate)

        # Chunked pure-python RMS calculation
        sum_sq = 0.0
        total_samples = 0
        chunk_frames = 16384
        while True:
            raw = wf.readframes(chunk_frames)
            if not raw:
                break
            n_samples = len(raw) // sampwidth
            total_samples += n_samples
            if sampwidth == 2:  # 16-bit PCM
                import struct
                shorts = struct.unpack(f"<{n_samples}h", raw)
                for s in shorts:
                    norm = s / 32768.0
                    sum_sq += norm * norm
            elif sampwidth == 3:  # 24-bit PCM
                for i in range(0, len(raw), 3):
                    val = int.from_bytes(raw[i:i+3], byteorder="little", signed=True)
                    norm = val / 8388608.0
                    sum_sq += norm * norm
            elif sampwidth == 4:  # 32-bit float or PCM
                import struct
                floats = struct.unpack(f"<{n_samples}f", raw)
                for f in floats:
                    sum_sq += f * f

        mean_sq = sum_sq / max(1, total_samples)
        rms = math.sqrt(mean_sq)
        rms_dbfs = 20.0 * math.log10(rms) if rms > 1e-9 else float("-inf")

        is_non_zero = rms_dbfs > min_rms_dbfs
        duration_ok = duration_sec >= min_duration_sec

        return {
            "valid": is_non_zero and duration_ok,
            "path": abs_path,
            "channels": channels,
            "sample_rate": framerate,
            "bit_depth": sampwidth * 8,
            "duration_sec": round(duration_sec, 3),
            "rms": rms,
            "rms_dbfs": round(rms_dbfs, 2),
            "is_silent": rms < 1e-5,
            "meets_rms_threshold": is_non_zero,
            "meets_duration_threshold": duration_ok,
        }


def verify_als_and_wav(
    als_path: str,
    wav_path: str,
    expected_min_tracks: int = 1,
    min_duration_sec: float = 10.0,
    min_rms_dbfs: float = -40.0,
) -> Dict[str, Any]:
    """Combines ALS XML and WAV audio verifications."""
    als_res = verify_als_integrity(als_path, expected_min_tracks=expected_min_tracks)
    wav_res = verify_pcm_wav_energy(wav_path, min_duration_sec=min_duration_sec, min_rms_dbfs=min_rms_dbfs)
    overall_valid = als_res.get("verified", False) and wav_res.get("valid", False)
    return {
        "valid": overall_valid,
        "als": als_res,
        "wav": wav_res,
    }


# ==============================================================================
# Reusable Masterclass Builder Base Class
# ==============================================================================

class MasterclassBuilder:
    """
    Base builder class for sequential Ableton Live 12 Masterclass reconstruction.
    """

    def __init__(self, spec_path: str, als_dest: str, wav_dest: str):
        self.spec_path = os.path.abspath(os.path.expanduser(spec_path))
        self.als_dest = os.path.abspath(os.path.expanduser(als_dest))
        self.wav_dest = os.path.abspath(os.path.expanduser(wav_dest))
        self.spec = self.load_spec()
        self.client = Live12Client()
        self.track_indices: Dict[str, int] = {}

    def load_spec(self) -> Dict[str, Any]:
        with open(self.spec_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def connect(self) -> None:
        logger.info("Connecting to Ableton Live 12 bridge on 127.0.0.1:11246...")
        if not self.client.is_reachable():
            raise ConnectionError("Live 12 Bridge unreachable on 127.0.0.1:11246. Is Ableton Live 12 Suite running?")
        logger.info("Successfully connected to Live 12 bridge.")

    def reset_session(self) -> None:
        tempo = float(self.spec.get("tempo", 126.0))
        scale = self.spec.get("scale", {})
        root_name = scale.get("root_note", "C")
        root_map = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}
        root_idx = root_map.get(root_name, 0)
        scale_name = scale.get("name", "Minor")
        clean_session_reset(self.client, target_tempo=tempo, target_scale_root=root_idx, target_scale_name=scale_name)
        self.track_indices.clear()

    def create_locators(self) -> None:
        locators = self.spec.get("locators", [])
        logger.info("Programming %d arrangement locators...", len(locators))
        for loc in locators:
            time_beats = float(loc.get("time_beats", (loc.get("time_bars", 1.0) - 1.0) * 4.0))
            name = loc.get("name", "CUE")

            # Check existing cue points
            cues_res = self.client.call_tool("live12_cue_point_control", {"action": "list"})
            cues = cues_res.get("cue_points", []) if isinstance(cues_res, dict) or hasattr(cues_res, "get") else []
            match_idx = None
            for cp in cues:
                if abs(float(cp.get("time", -999.0)) - time_beats) < 0.2:
                    match_idx = cp.get("index")
                    break

            if match_idx is None:
                self.client.call_tool("live12_lom_set", {"target_path": "song", "property_name": "current_song_time", "value": float(time_beats)})
                time.sleep(0.04)
                self.client.call_tool("live12_lom_call", {"target_path": "song", "method_name": "set_or_delete_cue"})
                time.sleep(0.04)
                cues_res = self.client.call_tool("live12_cue_point_control", {"action": "list"})
                cues = cues_res.get("cue_points", []) if isinstance(cues_res, dict) or hasattr(cues_res, "get") else []
                for cp in cues:
                    if abs(float(cp.get("time", -999.0)) - time_beats) < 0.2:
                        match_idx = cp.get("index")
                        break

            if match_idx is not None:
                try:
                    self.client.call_tool("live12_lom_set", {
                        "target_path": f"song.cue_points.{match_idx}",
                        "property_name": "name",
                        "value": str(name),
                    })
                except Exception as e:
                    logger.debug("Minor notice setting cue name: %s", e)

        # Restore playhead to 0.0
        try:
            self.client.call_tool("live12_lom_set", {"target_path": "song", "property_name": "current_song_time", "value": 0.0})
        except Exception:
            pass

    def create_returns(self) -> None:
        returns = self.spec.get("return_tracks", [])
        if not returns:
            return
        logger.info("Configuring %d return tracks...", len(returns))
        # Query current return tracks
        ret_res = self.client.call_tool("live12_lom_get", {"target_path": "song", "property_name": "return_tracks"})
        curr_count = len(ret_res.get("value", [])) if isinstance(ret_res, dict) or hasattr(ret_res, "get") else 0
        while curr_count < len(returns):
            self.client.call_tool("live12_track_create", {"type": "return", "index": -1})
            curr_count += 1

        # Name return tracks and load devices
        for idx, ret in enumerate(returns):
            ret_name = ret.get("name", f"Return {chr(65+idx)}")
            try:
                self.client.call_tool("live12_lom_set", {
                    "target_path": f"song.return_tracks.{idx}",
                    "property_name": "name",
                    "value": ret_name,
                })
            except Exception as e:
                logger.debug("Failed renaming return track %d: %s", idx, e)

            # Load devices on return track
            devices = ret.get("devices", [])
            for dev in devices:
                dev_name = dev.get("name") or dev.get("device_name")
                if dev_name:
                    self.load_device(idx, dev_name, track_type="return")

    def create_track(
        self,
        name: str,
        track_type: str = "midi",
        color: Optional[int] = None,
        volume_db: Optional[float] = None,
        pan: float = 0.0,
    ) -> int:
        """Creates a track, sets name, volume, and returns its dynamic index."""
        t_type = "audio" if track_type.lower() == "audio" else "midi"
        res = self.client.call_tool("live12_track_create", {"type": t_type, "index": -1})
        t_idx = int(res.get("track_index", 0))

        # Set properties
        props: Dict[str, Any] = {"track_index": t_idx, "name": name}
        if color is not None:
            props["color"] = int(color)
        self.client.call_tool("live12_track_set_properties", props)

        # Set mixer
        if volume_db is not None:
            # Map dB to normalized value: 0 dB ~= 0.85, -6 dB ~= 0.70, -12 dB ~= 0.55
            norm_vol = max(0.0, min(1.0, 0.85 * (10.0 ** (volume_db / 40.0))))
            self.client.call_tool("live12_mixer_set", {"track_index": t_idx, "volume": norm_vol, "pan": float(pan)})

        self.track_indices[name] = t_idx
        return t_idx

    def load_device(self, track_index: int, device_name: str, track_type: str = "regular") -> None:
        """Loads a native Suite instrument or audio effect from the browser."""
        # Clean canonical device name (e.g., 'Compressor (Sidechain)' -> 'Compressor')
        clean_name = device_name.split("(")[0].strip()
        if "simpler" in clean_name.lower():
            clean_name = "Simpler"
        elif "wavetable" in clean_name.lower():
            clean_name = "Wavetable"
        elif "drum buss" in clean_name.lower() or "drumbuss" in clean_name.lower():
            clean_name = "Drum Buss"
        elif "auto filter" in clean_name.lower():
            clean_name = "Auto Filter"
        elif "glue" in clean_name.lower():
            clean_name = "Glue Compressor"
        elif "eq eight" in clean_name.lower():
            clean_name = "EQ Eight"
        elif "reverb" in clean_name.lower():
            clean_name = "Reverb"
        elif "echo" in clean_name.lower():
            clean_name = "Echo"
        elif "delay" in clean_name.lower():
            clean_name = "Delay"
        elif "utility" in clean_name.lower():
            clean_name = "Utility"
        elif "limiter" in clean_name.lower():
            clean_name = "Limiter"
        elif "saturator" in clean_name.lower():
            clean_name = "Saturator"
        elif "roar" in clean_name.lower():
            clean_name = "Roar"
        elif "meld" in clean_name.lower():
            clean_name = "Meld"
        elif "drift" in clean_name.lower():
            clean_name = "Drift"
        elif "operator" in clean_name.lower():
            clean_name = "Operator"

        logger.info("Loading device '%s' (resolved from '%s') on track %d...", clean_name, device_name, track_index)
        self.client.call_tool("live12_browser_load_item", {
            "track_index": track_index,
            "browser_item_uri": clean_name,
            "track_type": track_type,
        })
        time.sleep(0.15)

    def create_clip_with_notes(
        self,
        track_index: int,
        slot_index: int,
        notes: List[Dict[str, Any]],
        length_beats: float = 16.0,
        name: Optional[str] = None,
        duplicate_to_arrangement: bool = True,
        arrangement_start_beat: float = 0.0,
    ) -> None:
        """Creates a session MIDI clip, injects Live 12 extended notes, and optionally duplicates to arrangement."""
        clip_name = name or f"Clip {slot_index + 1}"
        self.client.call_tool("live12_clip_create", {
            "track_index": track_index,
            "slot_index": slot_index,
            "length_beats": float(length_beats),
            "name": clip_name,
        })

        if notes:
            self.client.call_tool("live12_clip_add_notes", {
                "track_index": track_index,
                "slot_index": slot_index,
                "notes": notes,
            })

        if duplicate_to_arrangement:
            self.client.call_tool("live12_clip_duplicate_to_arrangement", {
                "track_index": track_index,
                "slot_index": slot_index,
                "arrangement_time": float(arrangement_start_beat),
            })

    def inject_audio_sample(
        self,
        track_index: int,
        file_path: str,
        start_beat: float,
        length_beats: Optional[float] = None,
        warp_mode: str = "Beats",
    ) -> None:
        """Injects a real audio WAV sample onto an arrangement take lane and comps it."""
        abs_sample = os.path.abspath(os.path.expanduser(file_path))
        if not os.path.exists(abs_sample):
            logger.warning("Sample not found on disk: %s", abs_sample)
            return

        lane_res = self.client.call_tool("live12_take_lane_create", {"track_index": track_index})
        lane_idx = int(lane_res.get("take_lane_index", 0))

        self.client.call_tool("live12_take_lane_create_audio_clip", {
            "track_index": track_index,
            "take_lane_index": lane_idx,
            "file_path": abs_sample,
            "time": float(start_beat),
        })

        if length_beats:
            self.client.call_tool("live12_take_lane_comp_region", {
                "track_index": track_index,
                "take_lane_index": lane_idx,
                "time": float(start_beat),
                "length": float(length_beats),
            })

    def group_tracks(self, track_indices: List[int], group_name: str = "GROUP") -> int:
        """Groups listed track indices and renames the resulting group track."""
        res = self.client.call_tool("live12_track_group", {"track_indices": track_indices})
        grp_idx = int(res.get("group_track_index", min(track_indices)))
        self.client.call_tool("live12_track_set_properties", {"track_index": grp_idx, "name": group_name})
        return grp_idx

    def build(self) -> None:
        """Subclasses implement specific module construction."""
        raise NotImplementedError

    def save_and_export(self, render_duration_beats: float = 64.0) -> None:
        """Saves .als Live Set and exports .wav audio bounce."""
        save_live_set(self.client, self.als_dest, timeout_sec=25.0)
        export_audio_bounce(self.client, self.wav_dest, duration_beats=render_duration_beats, timeout_sec=60.0)

    def verify(self, expected_min_tracks: int = 1, min_duration_sec: float = 10.0) -> Dict[str, Any]:
        """Validates generated .als XML and .wav audio files."""
        return verify_als_and_wav(
            self.als_dest,
            self.wav_dest,
            expected_min_tracks=expected_min_tracks,
            min_duration_sec=min_duration_sec,
            min_rms_dbfs=-40.0,
        )

    def run(self, render_duration_beats: float = 64.0, expected_min_tracks: int = 1) -> Dict[str, Any]:
        """Full end-to-end execution lifecycle."""
        logger.info("=== Starting Masterclass Reconstruction: %s ===", self.spec.get("module_name", os.path.basename(self.als_dest)))
        self.connect()
        self.reset_session()
        self.create_locators()
        self.create_returns()
        self.build()
        self.save_and_export(render_duration_beats=render_duration_beats)
        results = self.verify(expected_min_tracks=expected_min_tracks)
        logger.info("=== Reconstruction Complete. Verification: %s ===", results)
        return results
