"""
Ableton Live 12 MCP - macOS OS Automation & Hybrid Dialog Engine
===============================================================
Handles OS-level UI automation outside the Live Object Model:
- File > Save Live Set As... (Shift+Cmd+S -> Cocoa NSSavePanel -> Cmd+Shift+G goto sheet -> Save)
- File > Open Live Set... (/usr/bin/open -b com.ableton.live)
- File > Export Audio/Video... (Shift+Cmd+R -> modal render config -> NSSavePanel -> WAV bounce verification)
- Native macOS Cocoa modal dialog inspection and dismissal
- Accessibility permissions verification and actionable diagnostics
"""

from __future__ import annotations

import logging
import os
import platform
import subprocess
import time
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("ableton_live12_mcp.dialogs")

DEFAULT_APP_NAME = "Ableton Live 12 Suite"
DEFAULT_APP_PATH = "/Applications/Ableton Live 12 Suite.app"
BUNDLE_ID = "com.ableton.live"
DEFAULT_POLL_INTERVAL = 0.1  # 100ms
DEFAULT_SAVE_TIMEOUT = 10.0
DEFAULT_OPEN_TIMEOUT = 10.0
DEFAULT_EXPORT_TIMEOUT = 30.0


# ==============================================================================
# Error Classes & Return Envelopes
# ==============================================================================

class DialogError(Exception):
    """Base error for dialog and OS automation failures."""
    code: int = -32000

    def __init__(self, message: str, code: Optional[int] = None):
        super().__init__(message)
        if code is not None:
            self.code = code
        self.message = message


class AccessibilityPermissionError(DialogError):
    """Raised when macOS Accessibility permission is missing (-32001)."""
    code = -32001


class UnsupportedPlatformError(DialogError):
    """Raised when OS automation is attempted on non-macOS systems (-32002)."""
    code = -32002


class TimeoutExpiredError(subprocess.TimeoutExpired, DialogError):
    """Raised when an OS dialog or verification times out (-32003)."""
    code = -32003

    def __init__(
        self,
        message: str,
        cmd: Optional[Any] = None,
        timeout: Optional[float] = None,
        output: Optional[Any] = None,
        stderr: Optional[Any] = None,
    ):
        self.code = -32003
        self.message = message
        subprocess.TimeoutExpired.__init__(
            self,
            cmd=cmd or ["osascript"],
            timeout=timeout if timeout is not None else 0.0,
            output=output,
            stderr=stderr,
        )

    def __str__(self) -> str:
        return self.message


class ApplicationNotRunningError(DialogError):
    """Raised when Ableton Live 12 process is not running (-32004)."""
    code = -32004


ApplicationNotRunning = ApplicationNotRunningError


class ValidationError(DialogError, ValueError):
    """Raised when path or argument validation fails (-32602)."""
    code = -32602


# ==============================================================================
# Path Validation Helpers
# ==============================================================================

def validate_als_save_path(path: str) -> str:
    """Validates and normalizes target path for saving a Live Set (.als)."""
    if not path or not isinstance(path, str) or not path.strip():
        raise ValidationError("destination_path must be a non-empty string")
    if "\x00" in path:
        raise ValidationError("destination_path cannot contain null bytes")
    abs_path = os.path.abspath(os.path.expanduser(path.strip()))
    if os.path.isdir(abs_path):
        raise ValidationError(f"Target path '{abs_path}' already exists as a directory.")
    if not abs_path.lower().endswith(".als"):
        raise ValidationError(f"Invalid path '{path}': Ableton Live Set must end with '.als'")
    return abs_path


def validate_als_open_path(path: str) -> str:
    """Validates and normalizes source path for opening an existing Live Set (.als)."""
    if not path or not isinstance(path, str) or not path.strip():
        raise ValidationError("als_path must be a non-empty string")
    if "\x00" in path:
        raise ValidationError("als_path cannot contain null bytes")
    abs_path = os.path.abspath(os.path.expanduser(path.strip()))
    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"Target Live Set file '{abs_path}' does not exist on disk.")
    if os.path.isdir(abs_path) or not os.path.isfile(abs_path):
        raise ValidationError(f"Target Live Set '{abs_path}' is a directory, not a valid .als file.")
    if not abs_path.lower().endswith(".als"):
        raise ValidationError(f"Target file '{abs_path}' must have '.als' extension.")
    return abs_path


def validate_wav_export_path(path: str) -> str:
    """Validates and normalizes destination path for audio rendering (.wav)."""
    if not path or not isinstance(path, str) or not path.strip():
        raise ValidationError("destination_wav_path must be a non-empty string")
    if "\x00" in path:
        raise ValidationError("destination_wav_path cannot contain null bytes")
    abs_path = os.path.abspath(os.path.expanduser(path.strip()))
    if os.path.isdir(abs_path):
        raise ValidationError(f"Target path '{abs_path}' already exists as a directory.")
    if not (abs_path.lower().endswith(".wav") or abs_path.lower().endswith(".wave")):
        raise ValidationError(f"Invalid export path '{path}': must have '.wav' extension")
    return abs_path


# ==============================================================================
# Environment & Diagnostic Helpers
# ==============================================================================

def is_macos() -> bool:
    """Returns True if running on macOS (Darwin)."""
    return platform.system() == "Darwin"


def get_accessibility_permission_status() -> Tuple[bool, Optional[str]]:
    """Probes macOS System Events authorization without crashing."""
    if not is_macos():
        return False, f"macOS (Darwin) required; current OS is '{platform.system()}'."

    script = 'tell application "System Events" to get name of current user'
    try:
        proc = subprocess.run(
            ["osascript", "-"],
            input=script,
            capture_output=True,
            text=True,
            timeout=3.0,
        )
        if proc.returncode == 0:
            return True, None

        err = proc.stderr.strip()
        if "-1743" in err or "not authorized" in err.lower() or "assistive" in err.lower():
            return False, (
                "macOS Accessibility permission not granted for System Events (-1743). "
                "Please enable Accessibility for Terminal/Python/Antigravity in "
                "System Settings > Privacy & Security > Accessibility."
            )
        return False, f"Accessibility check returned error: {err}"
    except subprocess.TimeoutExpired:
        return False, "Accessibility check timed out after 3.0s."
    except Exception as e:
        return False, f"Accessibility check exception: {str(e)}"


def check_accessibility_permissions() -> bool:
    """Returns True if the process has macOS Accessibility permissions for System Events."""
    ok, _ = get_accessibility_permission_status()
    return ok


def get_live_running_status() -> Tuple[bool, Optional[str]]:
    """Checks whether Ableton Live 12 process is currently running."""
    if not is_macos():
        return False, "macOS (Darwin) required."

    try:
        proc = subprocess.run(["pgrep", "-ix", "Live"], capture_output=True, text=True, timeout=2.0)
        if proc.returncode == 0:
            return True, None
    except Exception:
        pass

    script = f'''
    tell application "System Events"
        return count of (processes whose bundle identifier is "{BUNDLE_ID}" or name is "Live")
    end tell
    '''
    try:
        proc = subprocess.run(
            ["osascript", "-"],
            input=script,
            capture_output=True,
            text=True,
            timeout=3.0,
        )
        if proc.returncode == 0:
            out = proc.stdout.strip()
            try:
                count = int(out or "0")
                if count > 0:
                    return True, None
                return False, f"Ableton Live 12 ('{BUNDLE_ID}') is not running."
            except ValueError:
                return True, None
        return False, f"Failed to query running processes: {proc.stderr.strip()}"
    except Exception as e:
        return False, f"Process query error: {str(e)}"


def is_live_running() -> bool:
    """Returns True if Ableton Live 12 process is running."""
    ok, _ = get_live_running_status()
    return ok


# ==============================================================================
# Subprocess / AppleScript Execution Engine
# ==============================================================================

def run_applescript(
    script: str,
    args: Optional[List[str]] = None,
    timeout_sec: float = 10.0,
) -> Tuple[bool, str, str]:
    """
    Executes an AppleScript with parameters passed safely via argv ($@).
    Uses 'osascript - "$@"' with 'on run argv' to prevent quotation injection.
    """
    if not is_macos():
        raise UnsupportedPlatformError(f"macOS (Darwin) required; current system is '{platform.system()}'.")

    cmd = ["osascript", "-"]
    if args:
        cmd.extend(args)

    try:
        proc = subprocess.run(
            cmd,
            input=script,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired as e:
        raise TimeoutExpiredError(
            f"AppleScript execution timed out after {timeout_sec}s.",
            cmd=e.cmd,
            timeout=e.timeout,
        ) from e

    if proc.returncode != 0:
        err = proc.stderr.strip()
        if "-1743" in err or "not authorized" in err.lower() or "assistive" in err.lower():
            raise AccessibilityPermissionError(
                f"macOS Accessibility permission not granted for System Events (-1743): {err}"
            )
        if "-2741" in err or "syntax error" in err.lower():
            raise DialogError(f"AppleScript syntax error (-2741): {err}")
        if "not running" in err.lower():
            raise ApplicationNotRunningError(f"Ableton Live process not running: {err}")
        raise DialogError(f"AppleScript execution error: {err}")

    return True, proc.stdout.strip(), proc.stderr.strip()


# ==============================================================================
# Core OS Automation Operations
# ==============================================================================

def save_set(
    destination_path: str,
    timeout_sec: float = DEFAULT_SAVE_TIMEOUT,
    overwrite: bool = True,
) -> Dict[str, Any]:
    """
    Triggers 'Save Live Set As...' in Ableton Live 12 and saves the project file to destination_path.
    Interacts with the Cocoa NSSavePanel sheet using Cmd+Shift+G and verifies file creation.
    """
    abs_path = validate_als_save_path(destination_path)
    folder_path = os.path.dirname(abs_path)
    file_name = os.path.basename(abs_path)
    stem = os.path.splitext(file_name)[0]
    project_als_path = os.path.join(folder_path, f"{stem} Project", f"{stem}.als")

    if not overwrite:
        if os.path.exists(abs_path) or os.path.exists(project_als_path):
            raise ValidationError(
                f"Target Live Set already exists and overwrite=False: '{abs_path}'"
            )

    if not is_macos():
        raise UnsupportedPlatformError(
            f"macOS UI Automation requires Darwin; current system is '{platform.system()}'."
        )

    os.makedirs(folder_path, exist_ok=True)

    applescript = '''
    on findSaveDialog(liveProc)
        tell application "System Events"
            tell liveProc
                repeat with w in windows
                    try
                        repeat with s in sheets of w
                            try
                                if (exists button "Save" of s) or (exists button "Guardar" of s) or (exists button "Enregistrer" of s) or (exists button "Sichern" of s) or (exists text field 1 of s) then
                                    return s
                                end if
                            end try
                        end repeat
                    end try
                    try
                        set wSubrole to ""
                        try
                            set wSubrole to (value of attribute "AXSubrole" of w as string)
                        end try
                        if wSubrole is "AXDialog" then
                            if (exists button "Save" of w) or (exists button "Guardar" of w) or (exists button "Enregistrer" of w) or (exists button "Sichern" of w) then
                                return w
                            end if
                        end if
                    end try
                end repeat
            end tell
        end tell
        return missing value
    end findSaveDialog

    on triggerSaveAsMenu(liveProc)
        tell application "System Events"
            tell liveProc
                set menuLabels to {{"File", "Save Live Set As..."}, {"Archivo", "Guardar Live Set como..."}, {"Fichier", "Enregistrer le Set Live sous..."}, {"Ablage", "Live-Set sichern unter..."}}
                repeat with pairItem in menuLabels
                    set mName to item 1 of pairItem
                    set miName to item 2 of pairItem
                    try
                        click menu item miName of menu mName of menu bar 1
                        return true
                    end try
                end repeat
                try
                    set fileMenu to menu 1 of menu bar item 2 of menu bar 1
                    repeat with mi in menu items of fileMenu
                        try
                            set miTitle to (name of mi as string)
                            if (miTitle contains "Save" and miTitle contains "As") or (miTitle contains "Guardar" and miTitle contains "como") or (miTitle contains "sichern unter") or (miTitle contains "Enregistrer" and miTitle contains "sous") then
                                click mi
                                return true
                            end if
                        end try
                    end repeat
                end try
            end tell
        end tell
        return false
    end triggerSaveAsMenu

    on run argv
        set targetFolder to item 1 of argv
        set targetFile to item 2 of argv
        set allowOverwrite to item 3 of argv

        tell application "System Events"
            set liveProc to (first process whose bundle identifier is "com.ableton.live" or name is "Live")
            tell liveProc
                set frontmost to true
                delay 0.2

                -- Trigger Save Live Set As... (Shift+Cmd+S)
                keystroke "s" using {command down, shift down}
                delay 0.4

                -- Wait for real Cocoa Save sheet or Save dialog (never blindly target window 1)
                set saveWindow to my findSaveDialog(liveProc)
                repeat 30 times
                    if saveWindow is not missing value then exit repeat
                    delay 0.1
                    set saveWindow to my findSaveDialog(liveProc)
                end repeat

                if saveWindow is missing value then
                    my triggerSaveAsMenu(liveProc)
                    delay 0.5
                    set saveWindow to my findSaveDialog(liveProc)
                end if

                if saveWindow is missing value then
                    error "Save Live Set As dialog did not open."
                end if

                -- Open Go To Folder sheet via Cmd+Shift+G
                keystroke "g" using {command down, shift down}
                delay 0.4

                -- Populate Go To folder inside the sheet
                if (count of sheets of saveWindow) > 0 then
                    set gotoSheet to sheet 1 of saveWindow
                    set value of text field 1 of gotoSheet to targetFolder
                    delay 0.1
                    try
                        click button "Go" of gotoSheet
                    on error
                        try
                            click button "Ir" of gotoSheet
                        on error
                            try
                                click button "Aller" of gotoSheet
                            on error
                                keystroke return
                            end try
                        end try
                    end try
                    delay 0.3
                end if

                -- Set filename in verified Save As dialog
                try
                    set value of text field 1 of saveWindow to targetFile
                end try
                delay 0.2

                -- Click Save button explicitly (no blind keystroke return on Live main window)
                set clickedSave to false
                repeat with saveBtnName in {"Save", "Guardar", "Enregistrer", "Sichern"}
                    try
                        click button (contents of saveBtnName) of saveWindow
                        set clickedSave to true
                        exit repeat
                    end try
                end repeat
                if not clickedSave then
                    try
                        click (first button of saveWindow whose value of attribute "AXDefault" is true)
                        set clickedSave to true
                    end try
                end if
                if not clickedSave then
                    error "Could not locate Save button in Cocoa Save dialog."
                end if
                delay 0.4

                -- Handle overwrite confirmation sheet if file exists
                if (count of sheets of saveWindow) > 0 then
                    if allowOverwrite is "0" then
                        try
                            click button "Cancel" of sheet 1 of saveWindow
                        on error
                            try
                                click button "Cancelar" of sheet 1 of saveWindow
                            on error
                                key code 53
                            end try
                        end try
                        error "Save aborted: target exists and overwrite=False."
                    end if
                    set clickedReplace to false
                    repeat with repBtnName in {"Replace", "Reemplazar", "Remplacer", "Ersetzen"}
                        try
                            click button (contents of repBtnName) of sheet 1 of saveWindow
                            set clickedReplace to true
                            exit repeat
                        end try
                    end repeat
                    if not clickedReplace then
                        try
                            click (first button of (sheet 1 of saveWindow) whose value of attribute "AXDefault" is true)
                        end try
                    end if
                end if
            end tell
        end tell
        return "triggered"
    end run
    '''

    def _get_mtime_ns(path: str) -> Optional[int]:
        if os.path.exists(path) and os.path.isfile(path):
            try:
                return os.stat(path).st_mtime_ns
            except OSError:
                return None
        return None

    initial_mtime_ns = _get_mtime_ns(abs_path)
    initial_proj_mtime_ns = _get_mtime_ns(project_als_path)

    run_applescript(
        applescript,
        [folder_path, file_name, "1" if overwrite else "0"],
        timeout_sec=timeout_sec,
    )

    # Poll for file creation at abs_path OR <Parent>/<Stem> Project/<Stem>.als
    start_time = time.time()
    verified_path: Optional[str] = None
    candidates = [
        (abs_path, initial_mtime_ns),
        (project_als_path, initial_proj_mtime_ns),
    ]
    while time.time() - start_time < timeout_sec:
        for cand_path, init_ns in candidates:
            if os.path.exists(cand_path) and os.path.isfile(cand_path):
                try:
                    st = os.stat(cand_path)
                    if st.st_size > 0 and (init_ns is None or st.st_mtime_ns > init_ns):
                        verified_path = cand_path
                        break
                except OSError:
                    pass
        if verified_path is not None:
            break
        time.sleep(DEFAULT_POLL_INTERVAL)

    elapsed = time.time() - start_time
    if not verified_path:
        raise TimeoutExpiredError(
            f"Save command dispatched but file '{abs_path}' was not verified after {timeout_sec}s."
        )

    return {
        "status": "success",
        "saved": True,
        "path": verified_path,
        "saved_path": verified_path,
        "exists": True,
        "file_size_bytes": os.path.getsize(verified_path),
        "duration_sec": round(elapsed, 3),
    }


def open_set(
    als_path: str,
    timeout_sec: float = DEFAULT_OPEN_TIMEOUT,
    discard_unsaved: bool = True,
) -> Dict[str, Any]:
    """
    Opens an Ableton Live Set (.als) using macOS launch services (/usr/bin/open),
    checking for and handling 'Save changes' prompts according to discard_unsaved.
    """
    abs_path = validate_als_open_path(als_path)

    if not is_macos():
        raise UnsupportedPlatformError(
            f"macOS UI Automation requires Darwin; current system is '{platform.system()}'."
        )

    def _check_and_handle_unsaved_prompt() -> None:
        prompt_script = '''
        on findUnsavedButtons(containerObj)
            tell application "System Events"
                repeat with bName in {"Don't Save", "No guardar", "Nicht sichern", "Ne pas enregistrer", "Discard"}
                    try
                        if exists button (contents of bName) of containerObj then
                            return button (contents of bName) of containerObj
                        end if
                    end try
                end repeat
            end tell
            return missing value
        end findUnsavedButtons

        on run argv
            set shouldDiscard to item 1 of argv
            tell application "System Events"
                if not (exists (first process whose bundle identifier is "com.ableton.live" or name is "Live")) then
                    return "ok"
                end if
                set liveProc to (first process whose bundle identifier is "com.ableton.live" or name is "Live")
                tell liveProc
                    repeat 5 times
                        repeat with w in windows
                            repeat with s in sheets of w
                                set dontSaveBtn to my findUnsavedButtons(s)
                                if dontSaveBtn is not missing value then
                                    if shouldDiscard is "1" then
                                        click dontSaveBtn
                                        delay 0.3
                                        return "discarded_unsaved"
                                    else
                                        return "blocked_unsaved"
                                    end if
                                end if
                            end repeat
                            try
                                if (value of attribute "AXSubrole" of w as string) is "AXDialog" then
                                    set dontSaveBtn to my findUnsavedButtons(w)
                                    if dontSaveBtn is not missing value then
                                        if shouldDiscard is "1" then
                                            click dontSaveBtn
                                            delay 0.3
                                            return "discarded_unsaved"
                                        else
                                            return "blocked_unsaved"
                                        end if
                                    end if
                                end if
                            end try
                        end repeat
                        delay 0.05
                    end repeat
                end tell
            end tell
            return "ok"
        end run
        '''
        ok, stdout, _ = run_applescript(
            prompt_script,
            ["1" if discard_unsaved else "0"],
            timeout_sec=min(timeout_sec, 5.0),
        )
        if ok and stdout == "blocked_unsaved":
            raise DialogError(
                "Live is blocked on an unsaved changes prompt ('Save changes?'); "
                "save current set or pass discard_unsaved=True."
            )

    # Primary: open via explicit /Applications bundle path to prevent LaunchServices from launching DMG/translocated copies
    app_target = DEFAULT_APP_PATH if os.path.exists(DEFAULT_APP_PATH) else BUNDLE_ID
    flag = "-a" if os.path.exists(DEFAULT_APP_PATH) else "-b"
    cmd = ["/usr/bin/open", flag, app_target, abs_path]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec)
        if proc.returncode == 0:
            _check_and_handle_unsaved_prompt()
            return {
                "status": "success",
                "opened": True,
                "path": abs_path,
                "als_path": abs_path,
                "opened_set": abs_path,
                "method": "open_bundle_id",
            }
    except subprocess.TimeoutExpired as e:
        raise TimeoutExpiredError(
            f"Timeout after {timeout_sec}s opening '{abs_path}' via bundle ID.",
            cmd=e.cmd,
            timeout=e.timeout,
        ) from e

    # Fallback: open via application name
    try:
        proc_app = subprocess.run(
            ["/usr/bin/open", "-a", DEFAULT_APP_NAME, abs_path],
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
        if proc_app.returncode == 0:
            _check_and_handle_unsaved_prompt()
            return {
                "status": "success",
                "opened": True,
                "path": abs_path,
                "als_path": abs_path,
                "opened_set": abs_path,
                "method": "open_app_name",
            }
    except subprocess.TimeoutExpired as e:
        raise TimeoutExpiredError(
            f"Timeout after {timeout_sec}s opening '{abs_path}' via app name.",
            cmd=e.cmd,
            timeout=e.timeout,
        ) from e
    except DialogError:
        raise
    except Exception as e:
        logger.warning(f"open -a fallback failed: {e}")

    # Final fallback: AppleScript
    script = '''
    on run argv
        set targetAls to item 1 of argv
        tell application "Ableton Live 12 Suite"
            open POSIX file targetAls
            activate
        end tell
    end run
    '''
    run_applescript(script, [abs_path], timeout_sec=timeout_sec)
    _check_and_handle_unsaved_prompt()

    return {
        "status": "success",
        "opened": True,
        "path": abs_path,
        "als_path": abs_path,
        "opened_set": abs_path,
        "method": "open_applescript",
    }


_VALID_RENDER_SAMPLE_RATES = {22050, 44100, 48000, 88200, 96000}
_VALID_RENDER_BIT_DEPTHS = {16, 24, 32}
_SUPPORTED_RENDER_KEYS = {
    "sample_rate",
    "bit_depth",
    "dither_type",
    "render_start",
    "render_length",
    "normalize",
    "rendered_track",
}


def _validate_render_settings(render_settings: Optional[dict]) -> Dict[str, Any]:
    """Validates render_settings dictionary for export_audio."""
    if render_settings is None:
        return {}
    if not isinstance(render_settings, dict):
        raise ValidationError(f"render_settings must be an object, got {type(render_settings).__name__}")

    unknown = set(render_settings.keys()) - _SUPPORTED_RENDER_KEYS
    if unknown:
        raise ValidationError(
            f"Unsupported render_settings key(s): {sorted(unknown)}. "
            f"Supported keys: {sorted(_SUPPORTED_RENDER_KEYS)}"
        )

    validated: Dict[str, Any] = {}
    if "sample_rate" in render_settings:
        sr = render_settings["sample_rate"]
        if isinstance(sr, bool) or not isinstance(sr, (int, float)) or int(sr) != sr or int(sr) not in _VALID_RENDER_SAMPLE_RATES:
            raise ValidationError(f"Invalid sample_rate {sr!r}; expected one of {sorted(_VALID_RENDER_SAMPLE_RATES)}")
        validated["sample_rate"] = int(sr)
    if "bit_depth" in render_settings:
        bd = render_settings["bit_depth"]
        if isinstance(bd, bool) or not isinstance(bd, int) or bd not in _VALID_RENDER_BIT_DEPTHS:
            raise ValidationError(f"Invalid bit_depth {bd!r}; expected one of {sorted(_VALID_RENDER_BIT_DEPTHS)}")
        validated["bit_depth"] = bd
    if "render_start" in render_settings:
        rs = render_settings["render_start"]
        if isinstance(rs, bool) or not isinstance(rs, (int, float)) or float(rs) < 0.0:
            raise ValidationError(f"Invalid render_start {rs!r}; must be non-negative number")
        validated["render_start"] = float(rs)
    if "render_length" in render_settings:
        rl = render_settings["render_length"]
        if isinstance(rl, bool) or not isinstance(rl, (int, float)) or float(rl) <= 0.0:
            raise ValidationError(f"Invalid render_length {rl!r}; must be positive number")
        validated["render_length"] = float(rl)
    if "dither_type" in render_settings:
        dt = render_settings["dither_type"]
        if not isinstance(dt, str) or not dt.strip():
            raise ValidationError("dither_type must be a non-empty string")
        validated["dither_type"] = dt
    if "normalize" in render_settings:
        nm = render_settings["normalize"]
        if not isinstance(nm, bool):
            raise ValidationError("normalize must be a boolean")
        validated["normalize"] = nm
    if "rendered_track" in render_settings:
        rt = render_settings["rendered_track"]
        if not isinstance(rt, str) or not rt.strip():
            raise ValidationError("rendered_track must be a non-empty string")
        validated["rendered_track"] = rt
    return validated


def _has_valid_audio_header(header: bytes) -> Tuple[bool, str]:
    """Checks for valid RIFF/WAVE or FORM/AIFF(AIFC) 12-byte container header."""
    if len(header) < 12:
        return False, ""
    if header[:4] == b"RIFF" and header[8:12] == b"WAVE":
        return True, "riff_wave"
    if header[:4] == b"FORM" and header[8:12] in (b"AIFF", b"AIFC"):
        return True, "form_aiff"
    return False, ""


def export_audio(
    destination_wav_path: str,
    render_settings: Optional[dict] = None,
    timeout_sec: float = DEFAULT_EXPORT_TIMEOUT,
) -> Dict[str, Any]:
    """
    Triggers 'File > Export Audio/Video...' (Shift+Cmd+R), drives the render dialog,
    enters the destination path in Cocoa NSSavePanel, waits for export completion,
    and verifies the rendered WAV/AIFF header and file stability.
    """
    abs_path = validate_wav_export_path(destination_wav_path)
    validated_settings = _validate_render_settings(render_settings)
    folder_path = os.path.dirname(abs_path)
    file_name = os.path.basename(abs_path)

    if not is_macos():
        raise UnsupportedPlatformError(
            f"macOS UI Automation requires Darwin; current system is '{platform.system()}'."
        )

    os.makedirs(folder_path, exist_ok=True)

    applescript = '''
    on findSaveDialog(liveProc)
        tell application "System Events"
            tell liveProc
                repeat with w in windows
                    try
                        repeat with s in sheets of w
                            try
                                if (exists button "Save" of s) or (exists button "Guardar" of s) or (exists button "Enregistrer" of s) or (exists button "Sichern" of s) then
                                    return s
                                end if
                            end try
                        end repeat
                    end try
                    try
                        if (value of attribute "AXSubrole" of w as string) is "AXDialog" then
                            if (exists button "Save" of w) or (exists button "Guardar" of w) then
                                return w
                            end if
                        end if
                    end try
                end repeat
            end tell
        end tell
        return missing value
    end findSaveDialog

    on hasExportDialogOrProgress(liveProc)
        tell application "System Events"
            tell liveProc
                repeat with w in windows
                    try
                        if (count of sheets of w) > 0 then
                            return true
                        end if
                    end try
                    try
                        set wName to (name of w as string)
                        if wName contains "Export" or wName contains "Render" or wName contains "Progress" or wName contains "Exportar" then
                            return true
                        end if
                    end try
                    try
                        if (value of attribute "AXSubrole" of w as string) is "AXDialog" then
                            return true
                        end if
                    end try
                end repeat
            end tell
        end tell
        return false
    end hasExportDialogOrProgress

    on run argv
        set targetFolder to item 1 of argv
        set targetFile to item 2 of argv
        set renderStartArg to item 3 of argv
        set renderLengthArg to item 4 of argv
        set maxProgressPolls to (item 5 of argv) as integer

        tell application "System Events"
            set liveProc to (first process whose bundle identifier is "com.ableton.live" or name is "Live")
            tell liveProc
                set frontmost to true
                delay 0.2

                -- Keystroke Shift+Cmd+R (Export Audio/Video...)
                keystroke "r" using {command down, shift down}
                delay 0.5

                -- Wait for Export settings dialog
                repeat 30 times
                    if my hasExportDialogOrProgress(liveProc) then exit repeat
                    delay 0.1
                end repeat

                -- Apply optional render_start / render_length fields when available
                if renderStartArg is not "" or renderLengthArg is not "" then
                    try
                        set frontWin to window 1
                        if renderStartArg is not "" then
                            try
                                set value of text field 1 of frontWin to renderStartArg
                            end try
                        end if
                        if renderLengthArg is not "" then
                            try
                                set value of text field 2 of frontWin to renderLengthArg
                            end try
                        end if
                    end try
                end if

                -- Trigger Export button in settings dialog
                set clickedExport to false
                repeat with w in windows
                    repeat with btnName in {"Export", "Exportar", "Exporter", "Exportieren"}
                        try
                            click button (contents of btnName) of w
                            set clickedExport to true
                            exit repeat
                        end try
                    end repeat
                    if clickedExport then exit repeat
                end repeat
                if not clickedExport then
                    keystroke return
                end if
                delay 0.5

                -- Wait for Cocoa NSSavePanel
                set saveWindow to my findSaveDialog(liveProc)
                repeat 30 times
                    if saveWindow is not missing value then exit repeat
                    delay 0.1
                    set saveWindow to my findSaveDialog(liveProc)
                end repeat

                if saveWindow is missing value then
                    error "Export NSSavePanel dialog did not open."
                end if

                -- Open Go To Folder sheet via Cmd+Shift+G
                keystroke "g" using {command down, shift down}
                delay 0.4

                if (count of sheets of saveWindow) > 0 then
                    set gotoSheet to sheet 1 of saveWindow
                    set value of text field 1 of gotoSheet to targetFolder
                    delay 0.1
                    try
                        click button "Go" of gotoSheet
                    on error
                        try
                            click button "Ir" of gotoSheet
                        on error
                            keystroke return
                        end try
                    end try
                    delay 0.3
                end if

                -- Set filename in Save dialog
                try
                    set value of text field 1 of saveWindow to targetFile
                end try
                delay 0.2

                -- Click Save
                set clickedSave to false
                repeat with saveBtnName in {"Save", "Guardar", "Enregistrer", "Sichern"}
                    try
                        click button (contents of saveBtnName) of saveWindow
                        set clickedSave to true
                        exit repeat
                    end try
                end repeat
                if not clickedSave then
                    try
                        click (first button of saveWindow whose value of attribute "AXDefault" is true)
                    end try
                end if
                delay 0.4

                -- Handle overwrite confirmation if exists
                if (count of sheets of saveWindow) > 0 then
                    repeat with repBtnName in {"Replace", "Reemplazar", "Remplacer", "Ersetzen"}
                        try
                            click button (contents of repBtnName) of sheet 1 of saveWindow
                            exit repeat
                        end try
                    end repeat
                end if

                -- Wait for Ableton Export progress dialog/sheet to close before returning
                repeat maxProgressPolls times
                    if not my hasExportDialogOrProgress(liveProc) then exit repeat
                    delay 0.2
                end repeat
            end tell
        end tell
        return "triggered"
    end run
    '''

    initial_mtime_ns: Optional[int] = None
    if os.path.exists(abs_path) and os.path.isfile(abs_path):
        try:
            initial_mtime_ns = os.stat(abs_path).st_mtime_ns
        except OSError:
            initial_mtime_ns = None

    render_start_str = str(validated_settings["render_start"]) if "render_start" in validated_settings else ""
    render_length_str = str(validated_settings["render_length"]) if "render_length" in validated_settings else ""
    max_progress_polls = str(max(1, int(max(1.0, timeout_sec - 2.0) / 0.2)))

    run_applescript(
        applescript,
        [folder_path, file_name, render_start_str, render_length_str, max_progress_polls],
        timeout_sec=timeout_sec,
    )

    # Poll for rendered WAV/AIFF file: require valid RIFF/WAVE (or FORM/AIFF) header (size >= 44)
    # AND file stability ((size, mtime_ns) unchanged across 3 consecutive polls over >= 0.5s window).
    start_time = time.time()
    poll_interval = min(0.18, max(0.05, timeout_sec / 12.0))
    min_stable_window = min(0.5, max(0.2, timeout_sec * 0.2))
    last_fingerprint: Optional[Tuple[int, int]] = None
    stable_polls = 0
    stable_since: Optional[float] = None
    valid_header_kind = ""
    verified_size = 0

    while time.time() - start_time < timeout_sec:
        if os.path.exists(abs_path) and os.path.isfile(abs_path):
            try:
                st = os.stat(abs_path)
                if (initial_mtime_ns is None or st.st_mtime_ns > initial_mtime_ns) and st.st_size >= 44:
                    with open(abs_path, "rb") as f:
                        header = f.read(12)
                    ok_hdr, hdr_kind = _has_valid_audio_header(header)
                    if ok_hdr:
                        fp = (st.st_size, st.st_mtime_ns)
                        if fp == last_fingerprint:
                            stable_polls += 1
                        else:
                            last_fingerprint = fp
                            stable_polls = 1
                            stable_since = time.monotonic()

                        if stable_polls >= 3 and stable_since is not None:
                            if (time.monotonic() - stable_since) >= min_stable_window:
                                valid_header_kind = hdr_kind
                                verified_size = st.st_size
                                break
                    else:
                        last_fingerprint = None
                        stable_polls = 0
                        stable_since = None
            except OSError:
                last_fingerprint = None
                stable_polls = 0
                stable_since = None
        time.sleep(poll_interval)

    elapsed = time.time() - start_time
    if not valid_header_kind:
        raise TimeoutExpiredError(
            f"Export triggered but valid stabilized WAV/AIFF file '{abs_path}' was not detected within {timeout_sec}s."
        )

    result: Dict[str, Any] = {
        "status": "success",
        "exported": True,
        "destination": abs_path,
        "destination_wav_path": abs_path,
        "file_size_bytes": verified_size,
        "valid_riff": valid_header_kind == "riff_wave",
        "header_format": valid_header_kind,
        "duration_sec": round(elapsed, 3),
    }
    if validated_settings:
        result["render_settings"] = validated_settings
    return result


# ==============================================================================
# Modal Sheet Inspection & Dismissal
# ==============================================================================

def split_dialog_titles(stdout: str) -> List[str]:
    """Splits dialog titles safely using newline delimiters to prevent corrupting titles with commas."""
    if not stdout:
        return []
    if "\n" in stdout:
        return [t.strip() for t in stdout.split("\n") if t.strip()]
    stripped = stdout.strip()
    return [stripped] if stripped else []


def inspect_os_dialogs() -> Dict[str, Any]:
    """Inspects frontmost modal sheets and alert dialogs open in Ableton Live 12."""
    if not is_macos():
        return {"open_sheet_count": 0, "dialog_titles": []}

    script = '''
    tell application "System Events"
        set liveProc to (first process whose bundle identifier is "com.ableton.live" or name is "Live")
        tell liveProc
            set sheetList to {}
            repeat with w in windows
                repeat with s in sheets of w
                    set end of sheetList to (title of s as string)
                end repeat
            end repeat
            set AppleScript's text item delimiters to linefeed
            return sheetList as text
        end tell
    end tell
    '''
    try:
        success, stdout, stderr = run_applescript(script, timeout_sec=3.0)
    except Exception as e:
        return {"open_sheet_count": 0, "dialog_titles": [], "error": str(e)}

    titles = split_dialog_titles(stdout) if stdout else []
    return {
        "open_sheet_count": len(titles),
        "dialog_titles": titles,
    }


def dismiss_os_dialog(
    button_title_or_index: Union[str, int] = 0,
) -> Dict[str, Any]:
    """Dismisses the active modal sheet or alert window in Ableton Live 12."""
    if not is_macos():
        return {"dismissed": False, "reason": "Unsupported platform"}

    btn_arg = str(button_title_or_index)
    script = '''
    on tryClickTarget(containerObj, btnTarget)
        tell application "System Events"
            try
                click button btnTarget of containerObj
                return "clicked_title"
            end try
            if btnTarget is "Cancel" or btnTarget is "cancel" or btnTarget is "Cancelar" or btnTarget is "cancelar" then
                repeat with aliasBtn in {"Cancel", "Cancelar", "Annuler", "Abbrechen"}
                    try
                        click button (contents of aliasBtn) of containerObj
                        return "clicked_title"
                    end try
                end repeat
            end if
            try
                set btnIdx to (btnTarget as integer) + 1
                click button btnIdx of containerObj
                return "clicked_index"
            end try
        end tell
        return ""
    end tryClickTarget

    on run argv
        set btnTarget to item 1 of argv
        tell application "System Events"
            set liveProc to (first process whose bundle identifier is "com.ableton.live" or name is "Live")
            tell liveProc
                set hadDialog to false
                repeat with w in windows
                    if (count of sheets of w) > 0 then
                        set hadDialog to true
                        set targetSheet to sheet 1 of w
                        set res to my tryClickTarget(targetSheet, btnTarget)
                        if res is not "" then return res
                    end if
                    try
                        if (value of attribute "AXSubrole" of w as string) is "AXDialog" then
                            set hadDialog to true
                            set res to my tryClickTarget(w, btnTarget)
                            if res is not "" then return res
                        end if
                    end try
                end repeat
                if hadDialog then
                    key code 53
                    return "pressed_escape"
                end if
            end tell
        end tell
        return "none"
    end run
    '''
    try:
        success, stdout, stderr = run_applescript(script, [btn_arg], timeout_sec=3.0)
        return {
            "dismissed": success and stdout != "none",
            "action": stdout,
            "error": stderr if not success else None,
        }
    except Exception as e:
        return {
            "dismissed": False,
            "action": "error",
            "error": str(e),
        }
