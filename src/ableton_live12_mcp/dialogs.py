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
import math
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
    """Probes macOS System Events UI scripting authorization without crashing."""
    if not is_macos():
        return False, f"macOS (Darwin) required; current OS is '{platform.system()}'."

    script = 'tell application "System Events" to get UI elements enabled'
    try:
        proc = subprocess.run(
            ["osascript", "-"],
            input=script,
            capture_output=True,
            text=True,
            timeout=3.0,
        )
        if proc.returncode == 0:
            out = proc.stdout.strip().lower()
            if out == "true":
                return True, None
            if out == "false":
                return False, (
                    "macOS Accessibility UI scripting is disabled ('UI elements enabled' returned false). "
                    "Please enable Accessibility for Terminal/Python/Antigravity in "
                    "System Settings > Privacy & Security > Accessibility."
                )
            return False, f"Unexpected Accessibility check output: {proc.stdout.strip()!r}"

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
        proc = subprocess.run(["pgrep", "-x", "Live"], capture_output=True, text=True, timeout=2.0)
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
                return False, f"Unexpected process count output from System Events: {out!r}"
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
        if "-1719" in err or "can't get process" in err.lower() or "not running" in err.lower():
            raise ApplicationNotRunningError(f"Ableton Live process not running: {err}")
        raise DialogError(f"AppleScript execution error: {err}")

    return True, proc.stdout.strip(), proc.stderr.strip()


# ==============================================================================
# Core OS Automation Operations
# ==============================================================================

_APPLESCRIPT_SAVE_PANEL_HELPERS = '''
    on hasSaveButton(containerObj)
        tell application "System Events"
            try
                return (exists button "Save" of containerObj) or (exists button "Guardar" of containerObj) or (exists button "Enregistrer" of containerObj) or (exists button "Sichern" of containerObj)
            end try
        end tell
        return false
    end hasSaveButton

    on findSaveDialog(liveProc)
        tell application "System Events"
            tell liveProc
                repeat with w in windows
                    try
                        repeat with s in sheets of w
                            if my hasSaveButton(s) then
                                return s
                            end if
                        end repeat
                    end try
                    try
                        set wSubrole to ""
                        try
                            set wSubrole to (value of attribute "AXSubrole" of w as string)
                        end try
                        if wSubrole is "AXDialog" then
                            if my hasSaveButton(w) then
                                return w
                            end if
                        end if
                    end try
                end repeat
            end tell
        end tell
        return missing value
    end findSaveDialog

    on findTextInput(containerObj)
        tell application "System Events"
            try
                if exists text field 1 of containerObj then return text field 1 of containerObj
            end try
            try
                if exists combo box 1 of containerObj then return combo box 1 of containerObj
            end try
            try
                repeat with g in groups of containerObj
                    try
                        if exists text field 1 of g then return text field 1 of g
                    end try
                    try
                        if exists combo box 1 of g then return combo box 1 of g
                    end try
                end repeat
            end try
            try
                repeat with sa in scroll areas of containerObj
                    try
                        if exists text field 1 of sa then return text field 1 of sa
                    end try
                end repeat
            end try
        end tell
        return missing value
    end findTextInput

    on confirmGotoContainer(gotoContainer)
        tell application "System Events"
            repeat with goName in {"Go", "Ir", "Aller", "Öffnen"}
                try
                    if exists button (contents of goName) of gotoContainer then
                        click button (contents of goName) of gotoContainer
                        return true
                    end if
                end try
            end repeat
            keystroke return
            return true
        end tell
    end confirmGotoContainer

    on setGotoFolderPath(liveProc, saveWindow, targetFolder)
        tell application "System Events"
            tell liveProc
                repeat 15 times
                    try
                        if (count of sheets of saveWindow) > 0 then
                            set cand to sheet 1 of saveWindow
                            if not my hasSaveButton(cand) then
                                set fld to my findTextInput(cand)
                                if fld is not missing value then
                                    set value of fld to targetFolder
                                    delay 0.1
                                    my confirmGotoContainer(cand)
                                    delay 0.3
                                    return true
                                end if
                            end if
                        end if
                    end try

                    try
                        if (count of windows) > 0 and (count of sheets of window 1) > 0 then
                            set cand to sheet 1 of window 1
                            if not my hasSaveButton(cand) then
                                set fld to my findTextInput(cand)
                                if fld is not missing value then
                                    set value of fld to targetFolder
                                    delay 0.1
                                    my confirmGotoContainer(cand)
                                    delay 0.3
                                    return true
                                end if
                            end if
                        end if
                    end try

                    try
                        repeat with p in popovers of saveWindow
                            set fld to my findTextInput(p)
                            if fld is not missing value then
                                set value of fld to targetFolder
                                delay 0.1
                                my confirmGotoContainer(p)
                                delay 0.3
                                return true
                            end if
                        end repeat
                    end try

                    try
                        if (count of windows) > 0 then
                            repeat with p in popovers of window 1
                                set fld to my findTextInput(p)
                                if fld is not missing value then
                                    set value of fld to targetFolder
                                    delay 0.1
                                    my confirmGotoContainer(p)
                                    delay 0.3
                                    return true
                                end if
                            end repeat
                        end if
                    end try

                    try
                        repeat with w in windows
                            set wSub to ""
                            try
                                set wSub to (value of attribute "AXSubrole" of w as string)
                            end try
                            if wSub is "AXDialog" or wSub is "AXPopover" or wSub is "AXFloatingWindow" then
                                if not my hasSaveButton(w) then
                                    set fld to my findTextInput(w)
                                    if fld is not missing value then
                                        set value of fld to targetFolder
                                        delay 0.1
                                        my confirmGotoContainer(w)
                                        delay 0.3
                                        return true
                                    end if
                                    try
                                        repeat with p in popovers of w
                                            set fld2 to my findTextInput(p)
                                            if fld2 is not missing value then
                                                set value of fld2 to targetFolder
                                                delay 0.1
                                                my confirmGotoContainer(p)
                                                delay 0.3
                                                return true
                                            end if
                                        end repeat
                                    end try
                                end if
                            end if
                        end repeat
                    end try

                    delay 0.1
                end repeat
            end tell
        end tell
        error "Go To Folder dialog or path field could not be targeted after Cmd+Shift+G."
    end setGotoFolderPath

    on clickSaveInDialog(saveWindow)
        tell application "System Events"
            repeat with saveBtnName in {"Save", "Guardar", "Enregistrer", "Sichern"}
                try
                    click button (contents of saveBtnName) of saveWindow
                    return true
                end try
            end repeat
            try
                set defaultBtn to value of attribute "AXDefaultButton" of saveWindow
                if defaultBtn is not missing value then
                    click defaultBtn
                    return true
                end if
            end try
        end tell
        return false
    end clickSaveInDialog
'''


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

    applescript = _APPLESCRIPT_SAVE_PANEL_HELPERS + '''
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

                -- Open Go To Folder sheet/popover via Cmd+Shift+G and set targetFolder explicitly
                keystroke "g" using {command down, shift down}
                delay 0.3
                my setGotoFolderPath(liveProc, saveWindow, targetFolder)

                -- Set filename in verified Save As dialog (never swallow failure)
                set value of text field 1 of saveWindow to targetFile
                delay 0.2

                -- Click Save button explicitly
                if not my clickSaveInDialog(saveWindow) then
                    error "Could not locate Save button in Cocoa Save dialog."
                end if
                delay 0.4

                -- Handle overwrite confirmation sheet if file exists
                set hasOverwriteSheet to false
                try
                    if (count of sheets of saveWindow) > 0 then
                        set hasOverwriteSheet to true
                    end if
                end try
                if hasOverwriteSheet then
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
                            set repSheet to sheet 1 of saveWindow
                            set defaultRepBtn to value of attribute "AXDefaultButton" of repSheet
                            if defaultRepBtn is not missing value then
                                click defaultRepBtn
                            end if
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

    op_start = time.monotonic()
    deadline = op_start + max(0.0, float(timeout_sec))

    run_applescript(
        applescript,
        [folder_path, file_name, "1" if overwrite else "0"],
        timeout_sec=max(0.05, deadline - time.monotonic()),
    )

    # Poll for file creation at abs_path OR <Parent>/<Stem> Project/<Stem>.als
    verified_path: Optional[str] = None
    candidates = [
        (abs_path, initial_mtime_ns),
        (project_als_path, initial_proj_mtime_ns),
    ]
    while True:
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
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(DEFAULT_POLL_INTERVAL, remaining))

    elapsed = time.monotonic() - op_start
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

    op_start = time.monotonic()
    deadline = op_start + max(0.0, float(timeout_sec))

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
                    repeat 20 times
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
                        delay 0.1
                    end repeat
                end tell
            end tell
            return "ok"
        end run
        '''
        rem = max(0.1, min(5.0, deadline - time.monotonic()))
        ok, stdout, _ = run_applescript(
            prompt_script,
            ["1" if discard_unsaved else "0"],
            timeout_sec=rem,
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
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=max(0.05, deadline - time.monotonic()))
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
            timeout=max(0.05, deadline - time.monotonic()),
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

    # Final fallback: AppleScript using bundle id
    script = '''
    on run argv
        set targetAls to item 1 of argv
        tell application id "com.ableton.live"
            open POSIX file targetAls
            activate
        end tell
    end run
    '''
    run_applescript(script, [abs_path], timeout_sec=max(0.05, deadline - time.monotonic()))
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
_UI_INACCESSIBLE_RENDER_KEYS = frozenset({
    "sample_rate",
    "bit_depth",
    "dither_type",
    "normalize",
    "rendered_track",
})
_UI_ATTEMPTED_RENDER_KEYS = frozenset({
    "render_start",
    "render_length",
})


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
        if (
            isinstance(sr, bool)
            or not isinstance(sr, (int, float))
            or not math.isfinite(float(sr))
            or int(sr) != sr
            or int(sr) not in _VALID_RENDER_SAMPLE_RATES
        ):
            raise ValidationError(f"Invalid sample_rate {sr!r}; expected one of {sorted(_VALID_RENDER_SAMPLE_RATES)}")
        validated["sample_rate"] = int(sr)
    if "bit_depth" in render_settings:
        bd = render_settings["bit_depth"]
        if isinstance(bd, bool) or not isinstance(bd, int) or bd not in _VALID_RENDER_BIT_DEPTHS:
            raise ValidationError(f"Invalid bit_depth {bd!r}; expected one of {sorted(_VALID_RENDER_BIT_DEPTHS)}")
        validated["bit_depth"] = bd
    if "render_start" in render_settings:
        rs = render_settings["render_start"]
        if (
            isinstance(rs, bool)
            or not isinstance(rs, (int, float))
            or not math.isfinite(float(rs))
            or float(rs) < 0.0
        ):
            raise ValidationError(f"Invalid render_start {rs!r}; must be non-negative finite number")
        validated["render_start"] = float(rs)
    if "render_length" in render_settings:
        rl = render_settings["render_length"]
        if (
            isinstance(rl, bool)
            or not isinstance(rl, (int, float))
            or not math.isfinite(float(rl))
            or float(rl) <= 0.0
        ):
            raise ValidationError(f"Invalid render_length {rl!r}; must be positive finite number")
        validated["render_length"] = float(rl)
    if "dither_type" in render_settings:
        dt = render_settings["dither_type"]
        if not isinstance(dt, str) or not dt.strip() or "\x00" in dt:
            raise ValidationError("dither_type must be a non-empty string")
        validated["dither_type"] = dt
    if "normalize" in render_settings:
        nm = render_settings["normalize"]
        if not isinstance(nm, bool):
            raise ValidationError("normalize must be a boolean")
        validated["normalize"] = nm
    if "rendered_track" in render_settings:
        rt = render_settings["rendered_track"]
        if not isinstance(rt, str) or not rt.strip() or "\x00" in rt:
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

    applescript = _APPLESCRIPT_SAVE_PANEL_HELPERS + '''
    on isExportTitle(titleStr)
        if titleStr is missing value then return false
        set t to (titleStr as string)
        return (t contains "Export") or (t contains "Render") or (t contains "Progress") or (t contains "Exportar") or (t contains "Exporter") or (t contains "Exportieren") or (t contains "Rendering")
    end isExportTitle

    on hasExportButtons(containerObj)
        tell application "System Events"
            repeat with bName in {"Export", "Exportar", "Exporter", "Exportieren"}
                try
                    if exists button (contents of bName) of containerObj then return true
                end try
            end repeat
        end tell
        return false
    end hasExportButtons

    on hasExportDialogOrProgress(liveProc)
        tell application "System Events"
            tell liveProc
                repeat with w in windows
                    try
                        repeat with s in sheets of w
                            if my hasSaveButton(s) or my hasExportButtons(s) then return true
                            try
                                if exists progress indicator 1 of s then return true
                            end try
                            try
                                set sTitle to title of s
                                if my isExportTitle(sTitle) then return true
                            end try
                        end repeat
                    end try
                    set wName to ""
                    try
                        set rawName to name of w
                        if rawName is not missing value then set wName to (rawName as string)
                    end try
                    if my isExportTitle(wName) then
                        return true
                    end if
                    try
                        if (value of attribute "AXSubrole" of w as string) is "AXDialog" then
                            if my hasExportButtons(w) or my hasSaveButton(w) then
                                return true
                            end if
                            try
                                if exists progress indicator 1 of w then return true
                            end try
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

        set appliedList to {}

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
                    set exportWin to missing value
                    repeat with w in windows
                        if my hasExportButtons(w) then
                            set exportWin to w
                            exit repeat
                        end if
                    end repeat
                    if exportWin is missing value then
                        try
                            set exportWin to window 1
                        end try
                    end if
                    if exportWin is not missing value then
                        if renderStartArg is not "" then
                            try
                                set value of text field 1 of exportWin to renderStartArg
                                set end of appliedList to "render_start"
                            end try
                        end if
                        if renderLengthArg is not "" then
                            try
                                set value of text field 2 of exportWin to renderLengthArg
                                set end of appliedList to "render_length"
                            end try
                        end if
                    end if
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

                -- Open Go To Folder sheet/popover via Cmd+Shift+G and set targetFolder explicitly
                keystroke "g" using {command down, shift down}
                delay 0.3
                my setGotoFolderPath(liveProc, saveWindow, targetFolder)

                -- Set filename in Save dialog (never swallow failure)
                set value of text field 1 of saveWindow to targetFile
                delay 0.2

                -- Click Save
                if not my clickSaveInDialog(saveWindow) then
                    error "Could not locate Save button in Export NSSavePanel dialog."
                end if
                delay 0.4

                -- Handle overwrite confirmation if exists
                set hasOverwriteSheet to false
                try
                    if (count of sheets of saveWindow) > 0 then
                        set hasOverwriteSheet to true
                    end if
                end try
                if hasOverwriteSheet then
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
                            set repSheet to sheet 1 of saveWindow
                            set defaultRepBtn to value of attribute "AXDefaultButton" of repSheet
                            if defaultRepBtn is not missing value then
                                click defaultRepBtn
                            end if
                        end try
                    end if
                end if

                -- Wait for Ableton Export progress dialog/sheet to close before returning
                repeat maxProgressPolls times
                    if not my hasExportDialogOrProgress(liveProc) then exit repeat
                    delay 0.2
                end repeat
            end tell
        end tell
        set AppleScript's text item delimiters to ","
        return "triggered|applied=" & (appliedList as text)
    end run
    '''

    initial_mtime_ns: Optional[int] = None
    if os.path.exists(abs_path) and os.path.isfile(abs_path):
        try:
            initial_mtime_ns = os.stat(abs_path).st_mtime_ns
        except OSError:
            initial_mtime_ns = None

    op_start = time.monotonic()
    deadline = op_start + max(0.0, float(timeout_sec))

    remaining_for_script = max(0.05, deadline - time.monotonic())
    post_poll_reserve = min(2.0, remaining_for_script * 0.35)
    script_setup_budget = min(2.5, remaining_for_script * 0.4)
    progress_budget = max(0.0, remaining_for_script - post_poll_reserve - script_setup_budget)
    max_progress_polls = str(max(0, int(progress_budget / 0.2)))

    render_start_str = str(validated_settings["render_start"]) if "render_start" in validated_settings else ""
    render_length_str = str(validated_settings["render_length"]) if "render_length" in validated_settings else ""

    _, script_stdout, _ = run_applescript(
        applescript,
        [folder_path, file_name, render_start_str, render_length_str, max_progress_polls],
        timeout_sec=remaining_for_script,
    )

    # Poll for rendered WAV/AIFF file: require valid RIFF/WAVE (or FORM/AIFF) header (size >= 44)
    # AND file stability ((size, mtime_ns) unchanged across 3 consecutive polls over >= min_stable_window).
    min_stable_window = min(0.5, max(0.0, float(timeout_sec) * 0.25))
    poll_interval = min(0.18, max(0.005, min(float(timeout_sec) / 12.0, max(0.005, min_stable_window / 3.0))))
    last_fingerprint: Optional[Tuple[int, int]] = None
    stable_polls = 0
    stable_since: Optional[float] = None
    valid_header_kind = ""
    verified_size = 0

    while True:
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
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(poll_interval, remaining))

    elapsed = time.monotonic() - op_start
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
        applied_render_settings: Dict[str, Any] = {}
        unapplied_render_settings: Dict[str, Any] = {}

        if "|applied=" in script_stdout:
            applied_raw = script_stdout.split("|applied=", 1)[1].strip()
            confirmed_ui_keys = {k.strip() for k in applied_raw.split(",") if k.strip()}
        else:
            confirmed_ui_keys = set(_UI_ATTEMPTED_RENDER_KEYS)

        for k, v in validated_settings.items():
            if k in _UI_INACCESSIBLE_RENDER_KEYS:
                unapplied_render_settings[k] = v
            elif k in confirmed_ui_keys:
                applied_render_settings[k] = v
            else:
                unapplied_render_settings[k] = v

        result["applied_render_settings"] = applied_render_settings
        result["unapplied_render_settings"] = unapplied_render_settings
        if unapplied_render_settings:
            result["warning"] = (
                "Ableton Live's Export Audio/Video dialog uses a custom UI that does not expose "
                "Cocoa Accessibility controls for sample_rate, bit_depth, dither_type, normalize, "
                "or rendered_track. Unapplied settings: "
                f"{sorted(unapplied_render_settings.keys())}; Live used its current dialog settings."
            )
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
            set sheetCount to 0
            set sheetList to {}
            repeat with w in windows
                try
                    repeat with s in sheets of w
                        set sheetCount to sheetCount + 1
                        set sTitle to ""
                        try
                            set rawST to title of s
                            if rawST is not missing value then set sTitle to (rawST as string)
                        end try
                        if sTitle is "" then
                            try
                                set rawSN to name of s
                                if rawSN is not missing value then set sTitle to (rawSN as string)
                            end try
                        end if
                        if sTitle is not "" then set end of sheetList to sTitle
                    end repeat
                end try
                try
                    if (value of attribute "AXSubrole" of w as string) is "AXDialog" then
                        set sheetCount to sheetCount + 1
                        set wTitle to ""
                        try
                            set rawWT to title of w
                            if rawWT is not missing value then set wTitle to (rawWT as string)
                        end try
                        if wTitle is "" then
                            try
                                set rawWN to name of w
                                if rawWN is not missing value then set wTitle to (rawWN as string)
                            end try
                        end if
                        if wTitle is not "" then set end of sheetList to wTitle
                    end if
                end try
            end repeat
            set AppleScript's text item delimiters to linefeed
            return (sheetCount as string) & linefeed & (sheetList as text)
        end tell
    end tell
    '''
    try:
        success, stdout, stderr = run_applescript(script, timeout_sec=3.0)
    except Exception as e:
        return {"open_sheet_count": 0, "dialog_titles": [], "error": str(e)}

    if not stdout:
        return {"open_sheet_count": 0, "dialog_titles": []}

    parts = stdout.split("\n", 1)
    if parts[0].strip().isdigit():
        open_sheet_count = int(parts[0].strip())
        titles = split_dialog_titles(parts[1]) if len(parts) > 1 else []
    else:
        titles = split_dialog_titles(stdout)
        open_sheet_count = len(titles)

    return {
        "open_sheet_count": open_sheet_count,
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
                    set frontmost to true
                    delay 0.1
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
