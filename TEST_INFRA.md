# Ableton Live 12 MCP: Test Infrastructure & Verification Architecture

## 1. Overview & Test Philosophy

This document defines the comprehensive test philosophy, architecture, sandboxing rules, and feature verification matrix for the **Ableton Live 12.4.6 Suite Model Context Protocol (MCP) Server and Remote Script Bridge**.

### 1.1 Core Principles

1. **Opaque-Box Requirement-Driven Verification**:
   Tests treat the MCP server and Ableton Remote Script bridge as an integrated system, testing strictly against published interface contracts, JSON-RPC 2.0 protocols, and LOM behavioral specifications defined in `ORIGINAL_REQUEST.md` and `PROJECT.md`.
2. **Strict Non-Destructive Sandboxing**:
   All tests operating against a running Ableton Live 12 instance must never alter, corrupt, or delete user tracks, scenes, or settings. All test resources are isolated using unique session identifiers (`__agy_test_<run_id>_*`) and guaranteed teardown in `finally` blocks.
3. **Mandatory Read-Back Mutation Verification**:
   No mutation (creating tracks, loading devices, inserting extended MIDI notes, setting parameters, or switching views) is considered successful based solely on the server returning an HTTP/RPC `200 OK`. Every mutation must be immediately followed by a read-back inspection asserting that the Live engine state matches the intended modification within floating-point tolerance.
4. **Dual-Mode Execution (Live DAW vs. Offline Mock Fallback)**:
   The test harness features transparent dual-mode execution. When Ableton Live 12.4.6 is running with the `Live12Bridge` control surface active, tests execute against the live C++ DAW engine. When Live is not running (e.g., in CI or unit test runs), the harness seamlessly activates an in-memory `MockAbletonBridge` that accurately simulates Ableton Live 12.4.6 LOM behavior, ensuring 100% test reproducibility anywhere.
5. **Adversarial & Boundary Rigor**:
   Tests explicitly stress out-of-bounds parameters, invalid indices, extreme durations, boundary tempos (20.0 to 999.0 BPM), probability extremes (0.0 to 1.0), and malformed payloads, asserting clean error reporting without server or bridge crashes.

---

## 2. Requirement Mapping Matrix (ORIGINAL_REQUEST.md & PROJECT.md)

Every requirement specified in `ORIGINAL_REQUEST.md` (R1–R4) and the 6 functional domains in `PROJECT.md` is mapped to an authoritative test suite and specific test functions.

| Requirement ID | Domain / Capability | Authoritative Test File | Key Test Cases |
|---|---|---|---|
| **R1** | LOM Surface Catalog & REA Symbols | `tests/test_tier1_feature_isolation.py` | `test_domain6_lom_surface_inspection`, `test_domain6_lom_type_reflection` |
| **R2** | In-Process Remote Script Bridge & IPC | `tests/test_tier1_feature_isolation.py`, `tests/test_tier2_boundaries_corners.py` | `test_bridge_ping_health`, `test_bridge_timeout_resilience`, `test_main_thread_scheduling` |
| **R3.1** | Domain 1: Transport, Song & Arrangement | `tests/test_tier1_feature_isolation.py`, `tests/test_tier2_boundaries_corners.py` | `test_transport_play_stop_record`, `test_tempo_bounds_clamp`, `test_scale_and_tuning_systems`, `test_loop_punch_overdub` |
| **R3.2** | Domain 2: Tracks, TakeLanes, Scenes & Routing | `tests/test_tier1_feature_isolation.py`, `tests/test_tier2_boundaries_corners.py`, `tests/test_tier3_pairwise_combos.py` | `test_track_creation_and_properties`, `test_takelane_comping`, `test_scene_fire_and_duplicate`, `test_mixer_and_send_routing` |
| **R3.3** | Domain 3: Clips, Extended MIDI & Audio Warping | `tests/test_tier1_feature_isolation.py`, `tests/test_tier2_boundaries_corners.py`, `tests/test_tier3_pairwise_combos.py` | `test_extended_midi_notes_crud`, `test_probability_velocity_deviation`, `test_quantize_and_loop_markers`, `test_audio_warp_modes_and_markers` |
| **R3.4** | Domain 4: Browser, Devices, Racks & Parameters | `tests/test_tier1_feature_isolation.py`, `tests/test_tier3_pairwise_combos.py` | `test_browser_search_and_load`, `test_device_parameter_get_set`, `test_specialized_devices_drift_roar_meld_wavetable`, `test_rack_macro_and_variations` |
| **R3.5** | Domain 5: View, Dialogs & OS-Level Actions | `tests/test_tier1_feature_isolation.py`, `tests/test_tier3_pairwise_combos.py`, `tests/test_tier4_production_flow.py` | `test_view_switching_and_selection`, `test_in_lom_dialog_inspection_and_press`, `test_os_save_open_export` |
| **R3.6** | Domain 6: Universal LOM Escape Hatch | `tests/test_tier1_feature_isolation.py`, `tests/test_tier2_boundaries_corners.py`, `tests/test_tier4_production_flow.py` | `test_lom_inspect_path`, `test_lom_get_property`, `test_lom_set_property`, `test_lom_call_method`, `test_lom_invalid_path_error` |
| **R4** | End-to-End Automated Song Construction | `tests/test_tier4_production_flow.py`, `scripts/run_live_tests.sh` | `test_complete_edm_production_flow`, `test_ambient_generative_composition_flow` |

---

## 3. Four-Tier Test Architecture

The test suite is structured into 4 hierarchical testing tiers:

```
+-------------------------------------------------------------+
|               Tier 4: Production Workflows                  |
|  - Real-world multi-track composition & arrangement         |
|  - Microtonal tuning + Live 12 generative MIDI              |
|  - Full stem and audio export automation                   |
+------------------------------+------------------------------+
                               |
+------------------------------+------------------------------+
|           Tier 3: Pairwise Subsystem Interactions           |
|  - Track creation + Device load + Clip insert + Modulation  |
|  - Return track + Bus routing + Volume/Pan/Send automation   |
|  - View switching + Clip/Device UI selection synchronization|
+------------------------------+------------------------------+
                               |
+------------------------------+------------------------------+
|           Tier 2: Boundaries, Corners & Resilience          |
|  - Parameter extremes (BPM < 20 or > 999, Pitch < 0 or > 127)|
|  - Invalid indices (-1, 9999), empty clips, 0-length notes  |
|  - Offline bridge disconnection & error frame formatting    |
+------------------------------+------------------------------+
                               |
+------------------------------+------------------------------+
|             Tier 1: Feature & Protocol Isolation            |
|  - JSON-RPC 2.0 stdio framing & Draft-07 schema compliance  |
|  - 61 Atomic tool execution tests (>= 5 per domain)         |
|  - Read-back verification of state mutations                |
+-------------------------------------------------------------+
```

### 3.1 Tier 1: Feature Isolation (`tests/test_tier1_feature_isolation.py`)
- Exercises every tool domain in atomic isolation.
- Validates input parameter acceptance, JSON-RPC response formatting, and mutation execution.
- Contains >= 5 dedicated tests for each of the 6 functional domains (minimum 30 tests).
- Every test modifies only sandboxed objects and validates state mutation via read-back.

### 3.2 Tier 2: Boundaries & Corners (`tests/test_tier2_boundaries_corners.py`)
- Validates defensive bounds and error envelopes.
- Tempo clamping (rejection/clamping outside 20.0–999.0 BPM).
- Note pitch boundaries (0 and 127 valid; -1, 128 rejected with informative error).
- Probability boundaries (0.0 and 1.0 valid; -0.1, 1.5 rejected).
- Velocity deviation boundaries (-127 to +127).
- Invalid track/slot/device indices returning structured JSON error objects (`isError: true`) rather than throwing unhandled exceptions.
- Empty clips, clips with maximum length (e.g. 65536 beats), empty note lists, and concurrent requests.

### 3.3 Tier 3: Pairwise Combinations (`tests/test_tier3_pairwise_combos.py`)
- Cross-domain integration verifying that components interact correctly:
  1. **Track + Instrument + Clip + Extended MIDI**: Create track, search and load synth (Drift), create clip, write polyphonic chord with probability/velocity deviation, verify notes and playback.
  2. **Track + Audio Effect Rack + Macro Modulation**: Create track, load effect rack, map macros, adjust macro values, verify parameter changes.
  3. **Multi-Track + Return Bus + Mixer Routing**: Create instrument track and return track, configure send amounts, set master/track panning and volume.
  4. **View Switching + Entity Selection**: Switch between Session/Arranger/Clip views, select tracks and clips, verify UI state synchronization.
  5. **TakeLane Comping + Arrangement Clips**: Create take lanes, record/add clips to lanes, comp region to main arrangement lane.

### 3.4 Tier 4: Real-World Production Flow (`tests/test_tier4_production_flow.py`)
- Real-world multi-track composition and production pipeline:
  1. Configure project global scale (e.g. D Minor) and microtonal tuning.
  2. Set master tempo (124.0 BPM) and arrangement loop.
  3. Track 1: Drums (Drum Rack, 4-bar kick/snare pattern).
  4. Track 2: Bass (Drift synth, 16th-note sub bass with velocity deviation).
  5. Track 3: Lead/Arp (Wavetable with modulation matrix).
  6. Return Track A: Reverb.
  7. Route sends, balance mixer gains, fire scenes, inspect telemetry during playback.
  8. Save Set / Export verification.

---

## 4. Sandboxing & Lifecycle Management

### 4.1 Resource Naming Scheme
All temporary tracks, scenes, and clips created during test runs are named with the deterministic prefix:
```
__agy_test_<run_id>_<entity_type>_<descriptor>
```
Where:
- `<run_id>` is a timestamped random token (e.g., `20261021_224500_a1b2c3`).
- `<entity_type>` is `track`, `scene`, `clip`, or `lane`.
- `<descriptor>` indicates the specific test (e.g., `drum_rack`, `bass_drift`).

### 4.2 Teardown Guarantees
The test harness ensures zero residue in the Live environment:
1. `Live12TestSession` registers every created entity.
2. In `session.teardown()`, executed in Pytest fixture teardown or `finally` blocks:
   - Stops the transport (`live12_transport_stop()`).
   - Resets tempo to 120.0 BPM.
   - Resets project scale and time signature to standard (4/4, C Major).
   - Iterates through all tracks in the song, identifying and deleting any track starting with `__agy_test_` in reverse order (to maintain index stability).
   - Deletes all scenes starting with `__agy_test_`.
   - Clears test audio exports from `/tmp/__agy_test_*`.

---

## 5. Dual-Mode Harness Architecture (`tests/harness.py`)

### 5.1 Mode Selection Logic
1. If environment variable `ABLETON_TEST_MODE=mock` is set, the harness forces mock mode.
2. If `ABLETON_TEST_MODE=live` is set, the harness requires a live bridge or fails immediately.
3. If unset (default auto-detection):
   - The harness inspects `/tmp/ableton_live12_bridge.json` or attempts TCP connection to `127.0.0.1:11246` (and fallback `127.0.0.1:9888`).
   - Sends a `ping` RPC request with a 250ms timeout.
   - If connected and acknowledged, mode is `LIVE`.
   - If unreachable, logs a notice to `stderr` and switches seamlessly to `MOCK` mode.

### 5.2 Mock Engine Capabilities
`MockAbletonBridge` in `tests/harness.py` contains a complete in-memory model of Live 12.4.6:
- `MockSong`: Manages tempo, time signature, scale information, tuning systems, transport playback, loop markers, cue points, and tracks collection.
- `MockTrack`: Manages track types (audio, midi, return), volume, pan, sends, mute, solo, arm, routing, devices, clip slots, and take lanes.
- `MockClip`: Stores Live 12 extended MIDI notes (`pitch`, `start_time`, `duration`, `velocity`, `velocity_deviation`, `release_velocity`, `probability`, `mute`, `note_id`), audio warp settings, loop points.
- `MockDevice`: Simulates Meld, Roar, Drift, Wavetable, Simpler, Racks, with parameters, macro controls, and variations.
- `MockBrowser`: Provides simulated search across standard Ableton 12 core library items.
- `MockView`: Tracks active view mode and UI selections.
- `MockLomResolver`: Simulates dynamic path reflection (`live_app.song.tracks[0].clip_slots[0].clip.get_notes_extended()`).

---

## 6. Test Runner & CLI Tooling (`scripts/run_live_tests.sh`)

The test suite is executable via `scripts/run_live_tests.sh` or standard `pytest`:

```bash
# Run all tiers in auto-detect mode (live if running, mock otherwise)
./scripts/run_live_tests.sh

# Force mock mode for CI/local verification
./scripts/run_live_tests.sh --mock

# Force live mode against running Ableton Live 12
./scripts/run_live_tests.sh --live

# Run a specific tier
./scripts/run_live_tests.sh --tier tier1
```

---

## 7. Coverage & Success Criteria

1. **Protocol Compliance**: 100% adherence to MCP stdio JSON-RPC 2.0 framing and error reporting.
2. **Domain Coverage**: All 6 functional domains and all 61 tools covered by atomic and integration tests.
3. **Test Volume**:
   - Tier 1: >= 30 isolated tests (>= 5 per domain).
   - Tier 2: >= 30 boundary & corner tests (>= 5 per domain).
   - Tier 3: >= 5 pairwise integration suites.
   - Tier 4: >= 2 production workflows (EDM and Generative Ambient).
   - Total: >= 67 executable, authentic tests.
4. **Assertion Integrity**: Every mutating test performs read-back verification against the engine state. Zero dummy assertions.
