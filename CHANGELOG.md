# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-10-24

### Added
- **`live12_clip_delete_arrangement`**: removes Arrangement View clips by position on a track
  (`live12_clip_delete` only handled Session View slots).
- **`live12_track_set_properties` / `live12_scene_set_properties` palette support**: new
  `color_index` (Live 12 palette slot, 0-69) and `color_rgb` parameters.
- **`skills/ableton-techno-producer`**: model-invoked skill with three reference playbooks
  (Space 92 *Gravity* psy-tech, Joris Voorn *Acid Flow / Trip to Galaxy*, techno theory +
  pre-mix & master bus) for producing through this MCP server.
- **`masterclasses/`**: Space 92 and Joris Voorn live builds, the grid organizer with
  colour-coded sections and an interactive HTML arrangement map.
- **`docs/TROUBLESHOOTING.md`**: live-set safety, bridge CPU, CoreAudio device issues and
  GUI automation recipes.
- **`scripts/inspect_live_set.py` / `scripts/measure_track_levels.py`**: live set snapshot and
  per-track level metering utilities.

### Fixed
- **Track/scene colours now reach the GUI**: `live12_track_set_properties(color=...)` used to
  assign the raw integer to Live's packed-RGB `color` property, which left every track on
  the default palette slot 69. The value is now written to `color_index` (palette) or an
  explicit RGB tuple.
- **Bridge CPU usage**: the `Live.Base.Timer` ran at a 5 ms interval and kept Ableton's main
  thread permanently scheduled (~60 % of a core). The interval is now 20 ms and configurable
  through `LIVE12_BRIDGE_TIMER_MS`.
- **Crash-recovery safe restarts**: `live12_os_open_set` now restores a saved set through the
  native open panel, so a restarted Live can reload the production set without losing state.

## [1.0.0] - 2026-10-22

### Added
- **Complete LOM Surface Discovery**: Reverse-engineered Boost.Python LOM catalog (`docs/lom_surface_12_4_6.json`) covering 184 types, 49 LOM classes, 43 MxD reflection classes, and 2,701 binary tokens extracted directly from Ableton Live 12.4.6 Suite.
- **Human-Readable LOM Reference**: Comprehensive documentation (`docs/LOM_REFERENCE.md`) detailing properties, methods, and listener events across all 49 LOM classes.
- **Ableton Live 12 Manual 20-Chapter Matrix**: Full alignment document (`docs/ABLETON_12_MANUAL_COVERAGE.md`) mapping every manual domain to corresponding MCP tools, LOM classes, and test suites.
- **In-Process `Live12Bridge` Control Surface**: Native MIDI Remote Script executing inside Ableton Live 12 Suite with a 5ms `Live.Base.Timer` main-thread queue and `liveobj_valid` pointer safety protection.
- **Full-Coverage MCP Server (75 Tools)**: High-performance, zero-pip-dependency stdio JSON-RPC 2.0 server providing 75 dedicated tools covering all 20 chapters of the Ableton Live 12 Manual:
  - Transport, tempo, time signatures, loop, punch, metronome, and MIDI capture.
  - Track hierarchy, grouping, take lanes, comping regions, and input/output routing.
  - Session clips, arrangement clip duplication, warp modes, and warp markers.
  - Live 12 extended MIDI note editing with per-note probability, velocity deviation, and release velocity.
  - Algorithmic MIDI transformations (Euclidean rhythm generator, humanize jitter, velocity ramps, scale pitch snapping).
  - Clip automation envelopes, breakpoint stepping, envelope clearing, and automation re-enable.
  - Groove Pool inspection, global groove amount, and clip groove template assignment.
  - Global scale modes (35+ scales) and microtonal `.ascl` tuning system loading.
  - Browser search, audio audition preview, and hotswap monitoring.
  - Rack devices, visible macro knobs (1–16), macro variations, and macro randomization.
  - Drum Rack 128-pad control, pad mute/solo, and pad copying (`copy_pad`).
  - Flagship Live 12 devices: Meld bi-timbral macro synth, Roar multi-stage saturator, Drift subtractive synth, Wavetable modulation matrix, and CC Control.
  - Native application dialog automation and AppleScript audio export (`dialogs.py`).
  - Session undo/redo operations and transactional undo step demarcations.
- **Offline & Live Test Harness**: Comprehensive test infrastructure (`tests/harness.py`) with `MockAbletonBridge` supporting seamless switching between offline mocking and live GUI verification.
- **Automated Verification Suites**: Multi-tier test suites verifying feature isolation, boundary conditions, combinatorial workflows, and 20-chapter end-to-end integration.
- **Interactive Dark Luxury GitHub Pages Site**: Complete, responsive, self-contained documentation site (`docs/index.html`) featuring:
  - Embedded video and audio players for studio showcase playback.
  - Interactive searchable and filterable catalog for all 75 MCP tools.
  - Interactive LOM class explorer inspecting all 49 reverse-engineered classes.
  - Copy-paste Antigravity (`agy`) prompt recipes for automated music production.
- **Multimedia Showcase Assets**: High-aesthetic vector architecture diagram (`assets/architecture.svg`), animated SVG terminal recording (`assets/terminal_demo.svg`), synthesized 8-bar Melodic Techno demo track (`assets/showcase_demo.wav`), session manifest (`assets/showcase_session_manifest.json`), and studio overview video/GIF (`assets/demo_overview.mp4`, `assets/demo_overview.gif`).
- **CI/CD Automation**: GitHub Actions workflows for multi-Python bytecode compilation, schema validation, test execution (`.github/workflows/ci.yml`), and automated GitHub Pages deployment (`.github/workflows/pages.yml`).
- **Open-Source Governance Suite**: Dual MIT and Apache-2.0 licensing, clean-room legal notices (DMCA 1201(f) & EU 2009/24/EC), trademark disclaimers, security threat model (`SECURITY.md`), and Contributor Covenant v2.1 (`CODE_OF_CONDUCT.md`).
