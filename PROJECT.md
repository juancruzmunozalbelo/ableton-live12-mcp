# Project: Ableton Live 12.4.6 LOM REA & Full-Coverage MCP Server

## Architecture
The system consists of three primary layers and an automated testing track:

```
+-------------------------------------------------------------+
|                      Antigravity CLI                        |
|                           (agy)                             |
+------------------------------+------------------------------+
                               | stdio JSON-RPC 2.0
                               v
+-------------------------------------------------------------+
|               Ableton Live 12 MCP Server                    |
|             (Pure Python stdlib, 61 tools)                  |
|  - Transport / Song / Arrangement                           |
|  - Tracks / TakeLanes / Scenes / Routing                    |
|  - Clips / Extended MIDI Notes / Audio Warping              |
|  - Browser / Devices / Meld / Roar / Drift / Racks          |
|  - View / In-LOM Dialogs / AppleScript OS Automation        |
|  - Universal LOM Escape Hatch (inspect, get, set, call)     |
+------------------------------+------------------------------+
                               | Loopback TCP (127.0.0.1:11246)
                               | NDJSON RPC / Discovery File
                               v
+-------------------------------------------------------------+
|      Live 12 Control Surface Bridge (Remote Script)         |
|  (/Users/juancruz/Music/Ableton/User Library/Remote Scripts)|
|  - create_instance(c_instance)                              |
|  - Live.Base.Timer (5ms main-thread scheduler)              |
|  - Dynamic Reflection Engine (_MxDCore style)               |
|  - liveobj_valid pointer safety                             |
|  - C++ Boost.Python bindings interface                      |
+------------------------------+------------------------------+
                               | Direct In-Process C++ Bindings
                               v
+-------------------------------------------------------------+
|               Ableton Live 12.4.6 Suite Engine              |
|              (/Applications/Ableton Live 12 Suite.app)      |
+-------------------------------------------------------------+
```

## Code Layout
```
/Users/juancruz/ableton-live12-mcp/
├── docs/
│   ├── lom_surface_12_4_6.json           # Machine-readable Boost.Python catalog
│   └── LOM_REFERENCE.md                 # Human-readable LOM reference guide
├── src/
│   ├── ableton_live12_mcp/              # MCP Server package (Python 3.11 stdlib)
│   │   ├── __init__.py
│   │   ├── __main__.py
│   │   ├── server.py                    # MCP stdio JSON-RPC 2.0 server
│   │   ├── client.py                    # TCP client to Remote Script bridge
│   │   ├── dialogs.py                   # Hybrid dialog engine (LOM + osascript)
│   │   ├── models.py                    # Extended MIDI Note, TakeLane, Device models
│   │   └── tools/                       # 6 tool domain modules
│   │       ├── __init__.py
│   │       ├── song_tools.py            # Transport, Song, Arrangement, Scale
│   │       ├── track_tools.py           # Tracks, TakeLanes, Scenes, Routing
│   │       ├── clip_tools.py            # Clips, Extended MIDI notes, Warping
│   │       ├── device_tools.py          # Browser, Devices, Racks, Parameters
│   │       ├── view_tools.py            # View switching, Dialogs, OS automation
│   │       └── lom_tools.py             # Universal LOM escape hatch
│   └── live12_bridge/                   # Source copy of Remote Script
│       ├── __init__.py                  # create_instance entry point
│       ├── bridge.py                    # TCP server & Live.Base.Timer dispatcher
│       └── reflection.py                # Dynamic LOM resolver & serializer
├── tests/                               # 4-Tier Automated Test Suite
│   ├── test_tier1_feature_isolation.py  # Tier 1: Single feature verification
│   ├── test_tier2_boundaries_corners.py # Tier 2: Edge cases and limits
│   ├── test_tier3_pairwise_combos.py    # Tier 3: Cross-subsystem interactions
│   ├── test_tier4_production_flow.py    # Tier 4: Real-world production scenarios
│   └── conftest.py / harness.py         # Live test fixture & __agy_test_* cleanup
└── scripts/
    ├── extract_lom_surface.py           # REA symbol extractor
    ├── register_mcp.py                  # Registers server in Antigravity config
    └── run_live_tests.sh                # End-to-end test runner
```

Remote Script Destination:
`/Users/juancruz/Music/Ableton/User Library/Remote Scripts/Live12Bridge/`

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | REA Symbol & Converter Extraction | Extract 184 Boost.Python classes and methods from Mach-O binary | M1 | ORIGINAL_REQUEST §R1, Survey 1 |
| 2 | Machine-readable LOM Catalog | Generate `docs/lom_surface_12_4_6.json` | M1 | ORIGINAL_REQUEST §R1 |
| 3 | Human-readable LOM Guide | Generate `docs/LOM_REFERENCE.md` | M1 | ORIGINAL_REQUEST §R1 |
| 4 | Remote Script Package Structure | `create_instance(c_instance)` in User Library | M2 | ORIGINAL_REQUEST §R2, Survey 2 |
| 5 | Main-Thread Scheduler | `Live.Base.Timer` 5ms polling + `update_display` secondary drain | M2 | ORIGINAL_REQUEST §R2, Survey 2 |
| 6 | Loopback TCP IPC Server | Socket listener with `/tmp/ableton_live12_bridge.json` discovery | M2 | ORIGINAL_REQUEST §R2, Survey 2 |
| 7 | Dynamic LOM Reflection Engine | `lom_inspect`, `lom_get`, `lom_set`, `lom_call` with pointer validation | M2 | ORIGINAL_REQUEST §R2, Survey 2 |
| 8 | Live 12 Extended MIDI Engine | `MidiNoteSpecification` handling in bridge | M2 | ORIGINAL_REQUEST §R2, Survey 1, 2 |
| 9 | Bridge Logging & Diagnostics | Log to `Log.txt` via `c_instance.log_message()` with stack traces | M2 | ORIGINAL_REQUEST §R2, Survey 2 |
| 10 | MCP stdio JSON-RPC Server | Python 3.11 stdlib MCP protocol implementation | M3 | ORIGINAL_REQUEST §R3, Survey 3 |
| 11 | Domain 1: Transport & Song Tools | Play, stop, record, tempo, signature, cue points, capture MIDI | M3 | ORIGINAL_REQUEST §R3.1 |
| 12 | Domain 1: Scale & Tuning Tools | Project scale, root note, microtonal tuning systems | M3 | ORIGINAL_REQUEST §R3.1 |
| 13 | Domain 2: Track & Routing Tools | Create, delete, arm, solo, mute, volume, pan, routing types/channels | M3 | ORIGINAL_REQUEST §R3.2 |
| 14 | Domain 2: TakeLane Tools | Create take lane, arrangement take lane audio/midi clips, metadata | M3 | ORIGINAL_REQUEST §R3.2 |
| 15 | Domain 2: Scene Tools | Create, fire, duplicate, rename, color scenes | M3 | ORIGINAL_REQUEST §R3.2 |
| 16 | Domain 3: Clip Tools | Create, fire, stop, duplicate, loop points, launch quantization | M3 | ORIGINAL_REQUEST §R3.3 |
| 17 | Domain 3: Live 12 Extended MIDI | Read/write notes with probability, velocity_deviation, release_velocity | M3 | ORIGINAL_REQUEST §R3.3 |
| 18 | Domain 3: Audio Warping Tools | Warp modes, warp markers, pitch shift, clip gain | M3 | ORIGINAL_REQUEST §R3.3 |
| 19 | Domain 4: Browser Navigation Tools | Browse sounds, drums, instruments, effects, packs, plugins | M3 | ORIGINAL_REQUEST §R3.4 |
| 20 | Domain 4: Device & Preset Loading | Load browser item to track, chain, or drum pad | M3 | ORIGINAL_REQUEST §R3.4 |
| 21 | Domain 4: Device Parameter Tools | Read/set device parameters by value or normalized range | M3 | ORIGINAL_REQUEST §R3.4 |
| 22 | Domain 4: Live 12 Specialized Devices | Wavetable mod matrix, Meld, Roar, Drift, Rack macro variations | M3 | ORIGINAL_REQUEST §R3.4 |
| 23 | Domain 5: View Navigation Tools | Switch between Session, Arranger, Detail, Browser, Clip, Device | M3 | ORIGINAL_REQUEST §R3.5 |
| 24 | Domain 5: In-LOM Dialog Tools | `open_dialog_count`, `current_dialog_message`, `press_current_dialog_button` | M4 | ORIGINAL_REQUEST §R3.5, Survey 1, 3 |
| 25 | Domain 5: OS AppleScript Automation | Cocoa NSSavePanel dialogs (Save Set, Audio Export, Open ALS) | M4 | ORIGINAL_REQUEST §R3.5, Survey 3 |
| 26 | Domain 6: Universal LOM Escape Hatch | Dynamic `lom_inspect`, `lom_get`, `lom_set`, `lom_call` MCP tools | M3 | ORIGINAL_REQUEST §R3.6 |
| 27 | Antigravity Registration Script | Automated setup in `~/.gemini/config/mcp_config.json` | M3 | ORIGINAL_REQUEST §R3 |
| 28 | Test Infra & Sandboxed Harness | `__agy_test_*` isolation, mutation assertions, guaranteed teardown | Test Track | ORIGINAL_REQUEST §R4, Survey 3 |
| 29 | Tier 1 Tests: Feature Isolation | >=5 isolated tests per feature group | Test Track | Project Pattern, Survey 3 |
| 30 | Tier 2 Tests: Boundaries & Corners | Empty clips, limits, invalid inputs, edge cases | Test Track | Project Pattern, Survey 3 |
| 31 | Tier 3 Tests: Pairwise Interactions | Cross-subsystem workflows (e.g. track+device+clip) | Test Track | Project Pattern, Survey 3 |
| 32 | Tier 4 Tests: Real-World Scenarios | Complete end-to-end production song construction | Test Track | Project Pattern, Survey 3 |
| 33 | E2E Live Verification Run | Execute test suite against live running Ableton 12.4.6 | M5 | ORIGINAL_REQUEST §R4 |
| 34 | Tier 5 Adversarial Hardening | Coverage audit and edge-case stress testing | M5 (Phase 2) | Project Pattern |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | LOM REA & Documentation Surface | Extract C++ Boost.Python symbols, generate `docs/lom_surface_12_4_6.json` and `docs/LOM_REFERENCE.md` | Survey complete | DONE |
| M2 | Control Surface Bridge (`Live12Bridge`) | Build & install Remote Script in User Library, `Live.Base.Timer` dispatch, TCP IPC, dynamic LOM engine | M1 interface specs | DONE |
| M3 | MCP Server Core & Tool Suite | Pure Python stdlib MCP server (61 tools across 6 domains), Antigravity config registration | M2 | DONE |
| M4 | OS Automation & Hybrid Dialog Engine | In-LOM dialog inspector + AppleScript/System Events for native sheets | M3 | DONE |
| M5 | Initial Live Verification & Hardening | 100% E2E test pass on live Ableton 12.4.6; Tier 5 adversarial hardening | M1, M2, M3, M4, Test Track | DONE |
| M6 | 20-Domain Manual Audit & Spec | Map 20 manual chapters, identify gaps, specify 14 new dedicated MCP tools | M5 | DONE |
| M7 | Core Bridge & MCP Tool Expansion | Implement 14 new tools (75 total), update LOM bridge handlers and mock harness | M6 | DONE |
| M8 | 20-Chapter Manual E2E Test Suite | Automated test suite covering all 20 chapters, 100% mock & live suite pass | M7 | DONE |
| M9 | Multimedia Asset Production | Generate demo video, animated GIF, vector diagrams, showcase audio & manifest | M8 | DONE |
| M10 | Governance, Interactive Docs & Release | Clean-room dual licensing, docs site, GitHub Pages, CI green across Py3.11-3.13 | M9 | DONE |
| M11 | Live Hardening, Masterclasses & Producer Skill | Palette-color fix (`color_index`), `live12_clip_delete_arrangement`, bridge timer CPU fix, Space 92 / Joris Voorn builds, grid organizer + HTML map, `ableton-techno-producer` skill, troubleshooting docs | M10 | DONE |

## Parallel Track: E2E Testing Track
- **Owner**: E2E Testing Orchestrator
- **Scope**: Requirement-driven 4-tier test suite (`TEST_INFRA.md`, `tests/test_tier*.py`, runner script).
- **Deliverable**: Publishes `TEST_READY.md` when test suite is fully implemented.
- **Status**: DONE (TEST_READY.md published, 76/76 tests passing)

## Interface Contracts

### 1. Remote Script Bridge ↔ MCP Server
- **Transport**: TCP loopback (`127.0.0.1:11246` default, auto-fallback with discovery file `/tmp/ableton_live12_bridge.json`).
- **Framing**: Newline-delimited JSON-RPC 2.0.
- **Request Format**:
  ```json
  {"jsonrpc": "2.0", "id": 1, "method": "lom_call", "params": {"path": "live_set.tracks.0.clip_slots.0.clip", "method": "add_new_notes", "args": [[{"pitch": 60, "start_time": 0.0, "duration": 1.0, "velocity": 100.0, "probability": 0.8}]]}}
  ```
- **Response Format**:
  ```json
  {"jsonrpc": "2.0", "id": 1, "result": {"success": true, "note_ids": [101]}}
  ```
- **Error Format**:
  ```json
  {"jsonrpc": "2.0", "id": 1, "error": {"code": -32000, "message": "IndexError: track index 99 out of range", "data": {"traceback": "..."}}}
  ```

### 2. MCP Server ↔ Antigravity (`agy`)
- **Transport**: Standard I/O (stdin/stdout) JSON-RPC 2.0.
- **Protocol**: Model Context Protocol (protocol version: `2024-11-05`).
- **Tools**: 61 tools with JSON Schema Draft-07 parameter definitions.
- **Registration**: Registered in `/Users/juancruz/.gemini/config/mcp_config.json`:
  ```json
  "ableton-live12": {
    "command": "/Users/juancruz/.local/share/uv/python/cpython-3.11-macos-aarch64-none/bin/python3.11",
    "args": ["-m", "ableton_live12_mcp"],
    "cwd": "/Users/juancruz/ableton-live12-mcp"
  }
  ```

### 3. Test Harness ↔ Live Environment
- **Sandboxing**: All created tracks and clips prefixed with `__agy_test_<run_id>_*`.
- **Teardown**: Safe cleanup in `finally` blocks ensuring zero residual test data.
- **Mutation Verification**: Mandatory read-back assertion following every set/create operation.
