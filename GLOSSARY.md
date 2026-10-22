# Ableton Live 12 MCP Domain Glossary

Canonical domain terminology for **Ableton Live 12 MCP** (`ableton-live12-mcp`), the production-grade Model Context Protocol server and in-process Control Surface bridge for **Ableton Live 12.4.6 Suite**.

---

## 1. Remote Script & Bridge Architecture

- **Control Surface (`Live12Bridge`)**: In-process Python package located in `/Users/juancruz/Music/Ableton/User Library/Remote Scripts/Live12Bridge/` loaded dynamically by Ableton Live 12 on startup via `create_instance(c_instance)`. Bridges internal C++ Boost.Python objects to external clients via local TCP loopback.
- **Main-Thread Scheduler (`Live.Base.Timer`)**: 5ms periodic callback running on Ableton's main GUI thread. Safely drains the incoming RPC command queue without stalling GUI redraws or causing race conditions in un-synchronized C++ Boost.Python structures.
- **Pointer Safety (`liveobj_valid`)**: C++ pointer validation utility verifying that a Boost.Python LOM object is still valid in memory and has not been deallocated by user deletion or track reorganization in Live.
- **Dynamic Reflection Engine (`reflection.py`)**: Traversal and introspection system enabling recursive property inspection, attribute read/write, and dynamic method execution across all 49 Live Object Model classes.
- **Local Loopback IPC (`127.0.0.1:11246`)**: High-speed, localhost-only TCP socket interface connecting the out-of-process MCP server to the in-process `Live12Bridge` control surface.

---

## 2. Live 12 Music & LOM Domains

- **Extended MIDI Note Specification (`MidiNoteSpecification`)**: Live 12 note structure supporting:
  - `pitch`: MIDI pitch number (0–127).
  - `start_time`: Note start position in arrangement/clip beats.
  - `duration`: Note duration in beats.
  - `velocity`: Note velocity (1–127).
  - `velocity_deviation`: Bipolar velocity randomness range (±0 to 127).
  - `probability`: Trigger probability (0.0 to 1.0) determining chance of playback.
  - `release_velocity`: Note-off release velocity (0–127).
  - `mute`: Per-note mute flag.
- **Take Lanes & Comping (`Live.TakeLane`)**: Arrangement take lanes supporting multiple audio or MIDI passes, persistent user metadata (`get_data`/`set_data`), and comp region selection (`Live.TakeLane.TakeLane.comp_region`).
- **Scale Information (`Song.scale_information`)**: Global musical scale system exposing root note (0–11) and scale intervals across 35+ modes (Major, Minor, Dorian, Phrygian, Lydian, Mixolydian, Locrian, etc.).
- **Microtonal Tuning Systems (`Live.TuningSystem`)**: Live 12 `.ascl` microtonal tuning format support with pitch cent offsets, custom reference frequencies, and microtonal octave mappings.
- **Groove Pool & Swing (`Live.GroovePool`)**: Real-time timing and velocity quantization template engine (`Live.Groove.Groove`) controlling groove base, timing amount, velocity amount, quantization amount, and random jitter.
- **Arrangement Locator Cue Points (`Live.Song.CuePoint`)**: Arrangement markers enabling immediate transport jumping, section demarcation (Intro, Verse, Chorus, Outro), and arrangement navigation.
- **Specialized Live 12 Devices**:
  - `Meld`: Bi-timbral macro-oscillator synthesizer featuring 12 macro sound algorithms, dual filters with scale-quantized resonance, and extensive modulation.
  - `Roar`: Multi-stage saturator and waveshaper with feedback matrix, 3-stage routing (Single, Serial, Parallel, Multi-band, Mid/Side, Feedback), and envelope follower.
  - `Drift`: MPE-capable subtractive synthesizer featuring analog oscillator pitch drift, variable stereo width, and vintage filtering.
  - `Wavetable`: Dual-wavetable synth with 2D modulation matrix, cyclic wave morphing, and dual analog-modeled filters.
  - `Simpler`: 3 playback modes (`Classic`, `One-Shot`, `Slicing`) with slice-to-Drum-Rack workflows.
  - `Drum Rack & DrumPad (`Live.DrumPad`)`: 128-pad percussion matrix with choke groups, chain routing, and pad-to-pad cloning (`copy_pad`).
  - `CC Control (`Live.CcControlDevice`)`: Live 12 MIDI utility device providing hardware CC automation, mapping, and continuous controller parameter dispatching.

---

## 3. Protocol & Tooling

- **Model Context Protocol (MCP)**: Anthropic open standard for tool discovery and invocation via JSON-RPC 2.0 stdio framing.
- **Antigravity (`agy`)**: Autonomous command-line interface and multi-agent coordination orchestrator driving AI music production workflows.
- **75 MCP Tools Catalog**: The complete suite of tools bridging all 20 chapters of the Ableton Live 12 Suite Manual into standard JSON-RPC tool declarations.
- **Sandboxed Test Harness (`SandboxedLiveHarness`)**: Python testing framework providing automated switching between live Ableton Live 12 instances and the offline `MockAbletonBridge`.
