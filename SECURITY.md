# Security Policy

## Supported Versions

We actively maintain and provide security patches for the following versions of **Ableton Live 12 MCP**:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0.0 | :x:                |

---

## Reporting a Vulnerability

If you discover a security vulnerability within Ableton Live 12 MCP, please report it privately rather than opening a public issue on GitHub.

- **Email**: Send vulnerability reports directly to **juancruzmunozalbelo@gmail.com**.
- **Subject**: `[SECURITY VULNERABILITY] Ableton Live 12 MCP: <Short Description>`
- **Include**:
  - A description of the vulnerability and affected module(s).
  - Step-by-step instructions or proof-of-concept code to reproduce the issue.
  - Expected impact, potential attack vectors, and any proposed fixes.

We will acknowledge receipt within 48 hours and coordinate a coordinated disclosure timeline and fix release.

---

## Threat Model & Security Architecture

Ableton Live 12 MCP operates as a local Model Context Protocol server communicating with an in-process Remote Script inside Ableton Live 12 Suite. Our threat model focuses on four key trust boundaries:

### 1. Loopback TCP IPC (`127.0.0.1`)
- The internal TCP server in `src/live12_bridge/` binds exclusively to the local IPv4 loopback interface (`127.0.0.1`). It never binds to `0.0.0.0` or listens on external network interfaces.
- Port discovery is stored in `/tmp/ableton_live12_bridge.json` with standard POSIX file permissions.

### 2. stdio JSON-RPC 2.0 Boundary
- The external MCP interface operates exclusively over standard input/output (`stdio`) JSON-RPC 2.0 under the execution context of the invoking agent (e.g. Antigravity `agy`), preventing remote network exploitation.

### 3. Pointer Safety & Memory Protection
- Ableton Live's internal Boost.Python objects can become dangling if tracks or clips are deleted in the GUI.
- The dynamic reflection engine in `src/live12_bridge/reflection.py` strictly validates object pointers using `liveobj_valid(obj)` before invoking any attribute or method, preventing C++ access violations or application crashes.

### 4. AppleScript OS Automation (`dialogs.py`)
- OS-level dialog interactions (`osascript` / System Events) are strictly scoped to the `Ableton Live 12 Suite` process name and standard Cocoa `NSSavePanel` file paths, preventing arbitrary shell command execution.
