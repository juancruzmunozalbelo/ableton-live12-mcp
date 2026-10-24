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
    os.makedirs(folder_path, exist_ok=True)

    if not is_macos():
        raise UnsupportedPlatformError(
            f"macOS UI Automation requires Darwin; current system is '{platform.system()}'."
        )

    applescript = '''
    on run argv
        set targetFolder to item 1 of argv
        set targetFile to item 2 of argv

        tell application "System Events"
            set liveProc to (first process whose bundle identifier is "com.ableton.live" or name is "Live")
            tell liveProc
                set frontmost to true
                delay 0.2

                -- Trigger Save Live Set As... (Shift+Cmd+S)
                keystroke "s" using {command down, shift down}
                delay 0.4

                -- Wait for sheet or Save dialog window
                set saveWindow to missing value
                repeat 30 times
                    if (count of windows) > 1 then
                        set saveWindow to window 1
                        exit repeat
                    end if
                    try
                        if (count of sheets of window 1) > 0 then
                            set saveWindow to sheet 1 of window 1
                            exit repeat
                        end if
                    end try
                    delay 0.1
                end repeat

                if saveWindow is missing value then
                    -- Fallback: menu click
                    try
                        click menu item "Save Live Set As..." of menu "File" of menu bar 1
                    end try
                    delay 0.5
                    if (count of windows) > 1 then
                        set saveWindow to window 1
                    else
                        try
                            if (count of sheets of window 1) > 0 then
                                set saveWindow to sheet 1 of window 1
                            else
                                set saveWindow to window 1
                            end if
                        on error
                            try
                                set saveWindow to window 1
                            end try
                        end try
                    end if
                end if

                -- Open Go To Folder sheet via Cmd+Shift+G
                keystroke "g" using {command down, shift down}
                delay 0.4

                -- Populate Go To folder
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

                -- Set filename in Save As text field
                try
                    set value of text field 1 of saveWindow to targetFile
                end try
                delay 0.2

                -- Click Save
                try
                    click button "Save" of saveWindow
                on error
                    try
                        click button "Guardar" of saveWindow
                    on error
                        keystroke return
                    end try
                end try
                delay 0.4

                -- Handle overwrite confirmation if file exists
                if (count of sheets of saveWindow) > 0 then
                    try
                        click button "Replace" of sheet 1 of saveWindow
                    on error
                        try
                            click button "Reemplazar" of sheet 1 of saveWindow
                        on error
                            keystroke return
                        end try
                    end try
                end if
            end tell
        end tell
        return "triggered"
    end run
    '''

    initial_mtime = None
    if os.path.exists(abs_path) and os.path.isfile(abs_path):
        try:
            initial_mtime = os.path.getmtime(abs_path)
        except OSError:
            initial_mtime = None

    run_applescript(applescript, [folder_path, file_name], timeout_sec=timeout_sec)

    # Poll for file creation
    start_time = time.time()
    file_ready = False
    while time.time() - start_time < timeout_sec:
        if os.path.exists(abs_path) and os.path.isfile(abs_path):
            try:
                curr_size = os.path.getsize(abs_path)
                curr_mtime = os.path.getmtime(abs_path)
                if curr_size > 0:
                    if initial_mtime is None or curr_mtime > initial_mtime:
                        file_ready = True
                        break
            except OSError:
                pass
        time.sleep(DEFAULT_POLL_INTERVAL)

    elapsed = time.time() - start_time
    if not file_ready:
        raise TimeoutExpiredError(
            f"Save command dispatched but file '{abs_path}' was not verified after {timeout_sec}s."
        )

    return {
        "status": "success",
        "saved": True,
        "path": abs_path,
        "saved_path": abs_path,
        "exists": True,
        "file_size_bytes": os.path.getsize(abs_path),
        "duration_sec": round(elapsed, 3),
    }


def open_set(
    als_path: str,
    timeout_sec: float = DEFAULT_OPEN_TIMEOUT,
    discard_unsaved: bool = True,
) -> Dict[str, Any]:
    """
    Opens an Ableton Live Set (.als) using macOS launch services (/usr/bin/open).
    """
    abs_path = validate_als_open_path(als_path)

    if not is_macos():
        raise UnsupportedPlatformError(
            f"macOS UI Automation requires Darwin; current system is '{platform.system()}'."
        )

    # Primary: open via explicit /Applications bundle path to prevent LaunchServices from launching DMG/translocated copies
    app_target = DEFAULT_APP_PATH if os.path.exists(DEFAULT_APP_PATH) else BUNDLE_ID
    flag = "-a" if os.path.exists(DEFAULT_APP_PATH) else "-b"
    cmd = ["/usr/bin/open", flag, app_target, abs_path]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec)
        if proc.returncode == 0:
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

    return {
        "status": "success",
        "opened": True,
        "path": abs_path,
        "als_path": abs_path,
        "opened_set": abs_path,
        "method": "open_applescript",
    }


def export_audio(
    destination_wav_path: str,
    render_settings: Optional[dict] = None,
    timeout_sec: float = DEFAULT_EXPORT_TIMEOUT,
) -> Dict[str, Any]:
    """
    Triggers 'File > Export Audio/Video...' (Shift+Cmd+R), drives the render dialog,
    enters the destination path in Cocoa NSSavePanel, and verifies the rendered WAV header.
    """
    abs_path = validate_wav_export_path(destination_wav_path)
    folder_path = os.path.dirname(abs_path)
    file_name = os.path.basename(abs_path)
    os.makedirs(folder_path, exist_ok=True)

    if not is_macos():
        raise UnsupportedPlatformError(
            f"macOS UI Automation requires Darwin; current system is '{platform.system()}'."
        )

    applescript = '''
    on run argv
        set targetFolder to item 1 of argv
        set targetFile to item 2 of argv

        tell application "System Events"
            set liveProc to (first process whose bundle identifier is "com.ableton.live" or name is "Live")
            tell liveProc
                set frontmost to true
                delay 0.2

                -- Keystroke Shift+Cmd+R (Export Audio/Video...)
                keystroke "r" using {command down, shift down}
                delay 0.5

                -- Wait for Export dialog window
                set exportDlg to missing value
                repeat 30 times
                    if (count of windows) > 1 then
                        exit repeat
                    end if
                    try
                        if (count of sheets of window 1) > 0 then
                            exit repeat
                        end if
                    end try
                    delay 0.1
                end repeat

                -- Press Return to trigger Export button in settings dialog
                keystroke return
                delay 0.5

                -- Wait for Cocoa NSSavePanel
                set saveWindow to missing value
                repeat 30 times
                    if (count of windows) > 1 then
                        set saveWindow to window 1
                        exit repeat
                    end if
                    try
                        if (count of sheets of window 1) > 0 then
                            set saveWindow to sheet 1 of window 1
                            exit repeat
                        end if
                    end try
                    delay 0.1
                end repeat

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
                try
                    click button "Save" of saveWindow
                on error
                    try
                        click button "Guardar" of saveWindow
                    on error
                        keystroke return
                    end try
                end try
                delay 0.4

                -- Handle overwrite confirmation if exists
                if (count of sheets of saveWindow) > 0 then
                    try
                        click button "Replace" of sheet 1 of saveWindow
                    on error
                        try
                            click button "Reemplazar" of sheet 1 of saveWindow
                        on error
                            keystroke return
                        end try
                    end try
                end if
            end tell
        end tell
        return "triggered"
    end run
    '''

    initial_mtime = None
    if os.path.exists(abs_path) and os.path.isfile(abs_path):
        try:
            initial_mtime = os.path.getmtime(abs_path)
        except OSError:
            initial_mtime = None

    run_applescript(applescript, [folder_path, file_name], timeout_sec=timeout_sec)

    # Poll for rendered WAV file and verify RIFF header
    start_time = time.time()
    valid_wave = False
    while time.time() - start_time < timeout_sec:
        if os.path.exists(abs_path) and os.path.isfile(abs_path):
            try:
                curr_mtime = os.path.getmtime(abs_path)
                if initial_mtime is None or curr_mtime > initial_mtime:
                    size = os.path.getsize(abs_path)
                    if size >= 44:
                        # Wait brief moment to confirm file handle closed
                        time.sleep(0.1)
                        try:
                            with open(abs_path, "rb") as f:
                                header = f.read(12)
                                if header[:4] == b"RIFF" and header[8:12] == b"WAVE":
                                    valid_wave = True
                                    break
                        except OSError:
                            pass
            except OSError:
                pass
        time.sleep(DEFAULT_POLL_INTERVAL)

    elapsed = time.time() - start_time
    if not valid_wave:
        raise TimeoutExpiredError(
            f"Export triggered but valid WAV file '{abs_path}' was not detected within {timeout_sec}s."
        )

    return {
        "status": "success",
        "exported": True,
        "destination": abs_path,
        "destination_wav_path": abs_path,
        "file_size_bytes": os.path.getsize(abs_path),
        "valid_riff": True,
        "duration_sec": round(elapsed, 3),
    }


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
    on run argv
        set btnTarget to item 1 of argv
        tell application "System Events"
            set liveProc to (first process whose bundle identifier is "com.ableton.live" or name is "Live")
            tell liveProc
                if (count of sheets of window 1) > 0 then
                    set targetSheet to sheet 1 of window 1
                    try
                        click button btnTarget of targetSheet
                        return "clicked_title"
                    on error
                        -- Fallback to numeric button index
                        try
                            set btnIdx to (btnTarget as integer) + 1
                            click button btnIdx of targetSheet
                            return "clicked_index"
                        on error
                            keystroke return
                            return "pressed_return"
                        end try
                    end try
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
