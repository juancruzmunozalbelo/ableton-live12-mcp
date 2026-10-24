# Ableton Live 12 Suite Masterclass Reconstruction & Engineering Playbook

A comprehensive technical synthesis, architectural reference, and reproduction playbook for the multimodal reverse-engineering and live in-DAW reconstruction of two flagship electronic music masterclasses inside **Ableton Live 12.4.6 Suite**:

1. **Tomas Otero's HOLO Master Class (Modules 1–5):** Modern Melodic Techno at 126 BPM in C Minor (Afterlife, Anyma, Tale of Us, Argy aesthetic), spanning conceptual reference setup, layered drum architecture, sub rumble synthesis, Live 12 native sound design (`Wavetable`, `Meld`, `Drift`, `Roar`), extended MIDI progressions, and a complete 180-bar multi-minute arrangement.
2. **Peerk's Peak Time Techno Masterclass (`ClaSE PEAK jULIO 25`):** Raw, industrial Peak Time Techno at 135 BPM in G Minor, comprising 33 tracks organized into a 3-level nested bus hierarchy with physical audio sample injection across arrangement take lanes, vocal band-pass spinning, and wavetable distortion racks.

Every Live Set (`.als`) and audio bounce (`.wav`) documented in this playbook was generated live and sequentially on macOS via the [`ableton-live12-mcp`](../README.md) JSON-RPC bridge running directly inside the Live 12.4.6 CPython 3.11 engine on `127.0.0.1:11246`.

---

## Table of Contents

- [1. Executive Overview](#1-executive-overview)
- [2. Architecture & Execution Harness](#2-architecture-execution-harness)
  - [2.1 Three-Layer Control Bridge](#21-three-layer-control-bridge)
  - [2.2 In-Process Session Reset Protocol](#22-in-process-session-reset-protocol)
  - [2.3 Native macOS UI Automation Harness](#23-native-macos-ui-automation-harness)
  - [2.4 Audio Stabilization & 24-Bit PCM Conversion](#24-audio-stabilization-24-bit-pcm-conversion)
  - [2.5 Dual-Engine Programmatic Verification](#25-dual-engine-programmatic-verification)
- [3. Masterclass Deep-Dive & Deconstructed Techniques](#3-masterclass-deep-dive-deconstructed-techniques)
  - [3.1 HOLO Module 1: Concepto y Referencia](#31-holo-module-1-concepto-y-referencia)
  - [3.2 HOLO Module 2: Groove y Baterías](#32-holo-module-2-groove-y-baterías)
  - [3.3 HOLO Module 3: Diseño Sonoro (Suite Synthesis)](#33-holo-module-3-diseño-sonoro-suite-synthesis)
  - [3.4 HOLO Module 4: Bases Armónicas y Melódicas](#34-holo-module-4-bases-armónicas-y-melódicas)
  - [3.5 HOLO Module 5: Arreglo Completo & Master Bus](#35-holo-module-5-arreglo-completo-master-bus)
  - [3.6 Peak Time Techno Masterclass (ClaSE PEAK jULIO 25)](#36-peak-time-techno-masterclass-clase-peak-julio-25)
- [4. Complete Catalog of Reconstructed Assets](#4-complete-catalog-of-reconstructed-assets)
  - [4.1 Ableton Live Sets (.als) Inventory](#41-ableton-live-sets-als-inventory)
  - [4.2 Rendered Audio Bounces (.wav) Inventory](#42-rendered-audio-bounces-wav-inventory)
- [5. Standalone Python Builder Scripts](#5-standalone-python-builder-scripts)
  - [5.1 Architecture of builder_base.py](#51-architecture-of-builder_basepy)
  - [5.2 Module Builders Catalog](#52-module-builders-catalog)
  - [5.3 Reproduction Commands](#53-reproduction-commands)
  - [5.4 Programmatic Verification Commands](#54-programmatic-verification-commands)
- [6. LOM & MCP Tool Cross-Reference](#6-lom-mcp-tool-cross-reference)

---

## 1. Executive Overview

This playbook establishes a rigorous, reproducible methodology for transcribing high-level music production pedagogy into deterministic, programmatic DAW execution. Rather than relying on static project templates, every clip, note, track, device parameter, routing matrix, and arrangement locator was constructed through automated remote procedure calls against a live, licensed instance of **Ableton Live 12.4.6 Suite**.

### Scope of the Reconstructed Masterclasses

- **Tomas Otero HOLO Master Class (5 Modules):**
  - **Video Footage:** 5 high-definition video modules totaling 30,024 seconds (8.34 hours) analyzed via multimodal frame extraction, audio spectral analysis, and transcript processing.
  - **Musical Spec:** 126.00 BPM, 4/4 time signature, C Minor (Aeolian modal center), 180-bar timeline (5m 43s duration).
  - **Technical Innovations:** Multi-layered kick design with sub rumble diffusion, native Ableton 12 `Wavetable`, `Meld`, `Drift`, and `Roar` synthesis chains, C Minor extended 9th chords (`Cm(add9) - Ab(add9) - Fm(add9) - Gm7`), 16th rolling basslines, PC2 3-3-2 triplet bass motifs, Live 12 note probability and velocity deviation distributions, pre-drop gain ducking (-1.5 dB trick), and a 5-device mastering chain.
- **Peerk Peak Time Techno Masterclass (`ClaSE PEAK jULIO 25`):**
  - **Source Material:** 9,732-second (2.7 hour) masterclass video (`video peak.mp4`) accompanied by the original master project file (`ClaSE PEAK jULIO 25.als`), 5 chronological progress snapshots in `Backup/`, and 19 physical audio samples in `Samples/`.
  - **Musical Spec:** 135.00 BPM, 4/4 time signature, G Minor, 176-bar arrangement (312.89s duration), 33 total tracks.
  - **Technical Innovations:** 3-level nested stem bus hierarchy (`1-Group` -> `2-Group` -> `3-Group`), physical sample injection into arrangement `TakeLane` comping clips, vocal formantic slicing and binaural `Band-pass Spinner` modulation (Auto Filter MS2 24dB at 2,490 Hz with 0.64 Hz LFO and 14.5% stereo spin), and multi-stage distortion chains (`Amp` + `Overdrive` + `Pedal` + `Redux2` + `Saturator` + `DrumBuss`).

---

## 2. Architecture & Execution Harness

### 2.1 Three-Layer Control Bridge

The reconstruction engine interfaces with Ableton Live 12 Suite via a low-latency, thread-safe 3-layer architecture:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   Antigravity MCP Automation Engine                   │
│         (Python Builder Scripts / CLI / Orchestration Runner)          │
└───────────────────────────────────▲────────────────────────────────────┘
                                    │ JSON-RPC 2.0 (MCP Protocol / TCP)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                  Ableton Live 12 MCP Server / Client                   │
│         (src/ableton_live12_mcp - 76 Tools across 20 Domains)          │
└───────────────────────────────────▲────────────────────────────────────┘
                                    │ High-Speed TCP RPC (127.0.0.1:11246)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│             In-Process Control Surface Bridge (Live12Bridge)           │
│     (Embedded CPython 3.11.6 runtime in /Applications/Ableton Live)    │
└───────────────────────────────────▲────────────────────────────────────┘
                                    │ Direct C++ Boost.Python Bindings
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                       Ableton Live Object Model                        │
│   (Live.Song, Live.Track, Live.Device, Live.Clip, Live.TakeLane, etc.) │
└────────────────────────────────────────────────────────────────────────┘
```

1. **Automation Layer:** Standalone Python scripts in `masterclasses/scripts/` orchestrate musical recipes deterministically.
2. **MCP Server & Client:** Exposes 76 strongly-typed tools adhering to the Model Context Protocol (2024-11-05 standard).
3. **In-Process Remote Script Bridge (`Live12Bridge`):** Installed in the macOS User Library, executing state mutations strictly on Ableton's main thread with zero unhandled tracebacks.

### 2.2 In-Process Session Reset Protocol

To reconstruct 6 complex masterclasses sequentially on a single running Live instance without restarting the DAW or invalidating the TCP socket connection, `builder_base.py` implements the `clean_session_reset()` protocol:

- **Transport Neutralization:** Halts playback (`live12_transport_stop`), disables arrangement record mode, session record mode, overdub, punch in/out, metronome, and resets the playhead (`song.current_song_time = 0.0`).
- **Reverse-Order Track Deletion:** Queries active track count via `live12_song_get_state` and deletes user tracks in descending order (`tracks_count - 1` down to `0`). If Live prevents deletion of the sole remaining track, a temporary placeholder track is spawned to allow safe destruction of track 0.
- **Return Track Purging:** Introspects `song.return_tracks` via `live12_lom_get` and invokes `song.delete_return_track(idx)` in reverse order.
- **Master Chain Stripping:** Introspects `song.master_track.devices` and deletes all master devices.
- **Locator Flushing:** Lists all arrangement cue points via `live12_cue_point_control` and deletes them sequentially.
- **Global Metric Initialization:** Sets target tempo (`126.0` or `135.0` BPM), time signature (`4/4`), song root note, scale type, and Equal Temperament tuning system.
- **View Reset:** Focuses `Arranger` and `Detail/DeviceChain` views.

### 2.3 Native macOS UI Automation Harness

While Ableton's Live Object Model (LOM) provides comprehensive control over tracks, devices, clips, and parameters, file persistence (`Save Live Set As...`) and audio rendering (`Export Audio/Video...`) exist as native Cocoa GUI modal dialogs outside the C++ Python API.

The harness bridges this boundary using macOS AppleScript (`System Events`) targeting bundle identifier `com.ableton.live`:
- **Set Saving (`save_live_set`):** Triggers `Shift+Cmd+S`, activates "Go To Folder" (`Shift+Cmd+G`), inputs the target directory, types the project filename, presses Return, and automatically detects and clicks Cocoa modal sheets containing "Replace" or "Reemplazar" buttons. It then polls disk storage and consolidates the `.als` file into its canonical path.
- **Audio Export (`export_audio_bounce`):** Enables arrangement looping over the exact measure range, triggers `File -> Export Audio/Video...`, confirms export settings via Return, drives the file destination sheet, handles replacement prompts, and waits for audio rendering to stabilize on disk.

### 2.4 Audio Stabilization & 24-Bit PCM Conversion

Ableton Live on macOS defaults to the `.aif` (AIFF) container when rendering audio. To ensure strict compliance with universal 24-bit PCM RIFF WAV standards:
1. `export_audio_bounce` polls the filesystem until the rendering file stops growing for 3 consecutive intervals (1.5 seconds of size stability).
2. The harness immediately executes an in-process conversion via `ffmpeg`:
   ```bash
   ffmpeg -y -i candidate_audio.aif -c:a pcm_s24le destination_path.wav
   ```
3. Stale `.asd` analysis files and intermediate `.aif` files are scrubbed, leaving a clean, standard 24-bit 44.1 kHz PCM `.wav` container.

### 2.5 Dual-Engine Programmatic Verification

Every generated asset is subjected to rigorous, automated verification:
1. **ALS XML Integrity (`verify_als_integrity`):** Validates the gzip magic header (`0x1F 0x8B`), uncompresses the XML stream, verifies the `<Ableton>` root tag, parses `<LiveSet>`, checks creator metadata (`Ableton Live 12.4.6`), confirms minimum expected user track counts, and verifies arrangement `<Locators>`.
2. **Audio Energy & Duration Verification (`verify_pcm_wav_energy`):** Validates the RIFF WAV header, verifies PCM compression format (`comptype == 'NONE'`), checks duration (`>= 10.0 seconds`), and computes the exact Root Mean Square (RMS) energy across all channels in dBFS using chunked 24-bit signed integer decoding:
   $$\text{RMS}_{\text{dBFS}} = 20 \log_{10} \left( \sqrt{\frac{1}{N} \sum_{i=1}^N \left(\frac{x_i}{8388608.0}\right)^2} \right)$$
   Assets failing to exceed `-40.0 dBFS` or duration thresholds are immediately rejected.

---

## 3. Masterclass Deep-Dive & Deconstructed Techniques

### 3.1 HOLO Module 1: Concepto y Referencia

*Associated Specification:* [`masterclasses/specs/holo_m1_concepto_referencia.md`](specs/holo_m1_concepto_referencia.md)  
*Specification JSON:* [`masterclasses/specs/holo_m1_concepto_referencia.json`](specs/holo_m1_concepto_referencia.json)  
*Live Set Asset:* [`masterclasses/holo/modulo_1_concepto_referencia.als`](holo/modulo_1_concepto_referencia.als) (37.6 KB, 11 tracks)  
*Audio Render Asset:* [`masterclasses/holo/modulo_1_concepto_referencia.wav`](holo/modulo_1_concepto_referencia.wav) (10.1 MB, 38.095s, RMS: -23.86 dBFS)

#### Musical Context & Foundations
- **Tempo:** 126.00 BPM | **Key/Scale:** C Minor (Aeolian modal center) | **Time Signature:** 4/4.
- **Arrangement Extent:** 180 bars (5m 43s) planned timeline.

#### Track Hierarchy & Reference Routing
- Group Track: `CONCEPTO Y REFERENCIA`
  - Track 1: `Ref 1 - Calling For More` (Sezer Uysal & Axelax, warpeado en modo Complex Pro, Formants 100%, Envelope 128).
  - Track 2: `Ref 2 - Hyper Saw` (Eze Ramirez, warpeado en modo Complex Pro, silenciado por defecto para alternancia A/B).
- **Master Bypass Routing Rule:** The reference group's audio output is routed strictly to `Ext Out` / `Cue Out` rather than `Master`. This critical technique prevents commercial mastered audio from entering the project's master bus compressors, saturators, and limiters, ensuring an unbiased, uncolored A/B comparison.
- **Audition Stems:** To ensure genuine acoustic energy during the foundational phase, the project includes an `Audition Kick Scratch` (Operator + Drum Buss) playing a 4-on-the-floor C1 pulse and an `Audition Shaker Scratch` (Drift + Auto Filter) executing syncopated 16th rhythms.

#### 6-Bus Shared Return Network
1. **Return A — `CLA-76` (Parallel Drum Compression):** `Live.Compressor` modeling vintage FET 1176 circuitry. Attack: `0.02 ms`, Release: `50 ms`, Ratio: `4:1`, Makeup Gain: `+4.5 dB`. Adds snap and sustain to transient percussions without crushing direct dynamic punch.
2. **Return B — `room` (Small Acoustic Ambience):** `Live.Reverb` (Studio Room). Decay: `650 ms`, Pre-Delay: `12 ms`, High Cut: `4,500 Hz`, Low Cut: `220 Hz`, Diffusion: `75%`. Emplaces kick, claps, and hats into a tangible physical space.
3. **Return C — `PLate` (Dense Metallic Plate):** `Live.Hybrid` in Plate algorithm. Decay: `1,800 ms`, Pre-Delay: `20 ms`, Damping: `5,000 Hz`. Gives silky top-end sheen to synth stabs and claps.
4. **Return D — `long rvbv` (Atmospheric Hall):** `Live.Reverb`. Decay: `5,200 ms`, Pre-Delay: `35 ms`, Room Size: `90`, Low Cut: `180 Hz`. Tailored for dramatic synth throws and breakdown swells.
5. **Return E — `SHIMMER` (Pitch-Shifted Reverb):** `Live.Hybrid` Shimmer mode. Pitch Shift: `+12 semitones` in the feedback loop, Decay: `4,500 ms`, Feedback: `40%`. Creates celestial harmonic halos above C Minor chord progressions.
6. **Return F — `Portal` (Granular Echo / Stutter):** `Live.Echo` with granular modulation. Left: `3/16` (dotted 8th), Right: `1/8`, Feedback: `38%`. Generates polyrhythmic spatial delay throws.

#### 11 Arrangement Locators
The 180-bar arrangement is calibrated with 11 strategic markers defining the energetic curve:
- `INTRO` (Bar 1.1.1 / 0.0 beats, 16 bars): Clean entry for DJ mixing.
- `ARMADO` (Bar 17.1.1 / 64.0 beats, 16 bars): Introduction of claps on beats 2 & 4 and 16th hats.
- `PUENTE` (Bar 33.1.1 / 128.0 beats, 16 bars): Percussions thin out; synth lead filter sweeps open.
- `DROP 1` (Bar 49.1.1 / 192.0 beats, 16 bars): First peak; full kick, sub rumble, and unfiltered lead.
- `PUENTE 2` (Bar 65.1.1 / 256.0 beats, 16 bars): Introduction of triplet bass motifs and hat variations.
- `DROP 2` (Bar 81.1.1 / 320.0 beats, 16 bars): Driving section featuring call-and-response melodic themes.
- `PUENTE 3` (Bar 97.1.1 / 384.0 beats, 16 bars): Rhythmic breakdown transition; high-pass filtering rises.
- `BREAK` (Bar 113.1.1 / 448.0 beats, 16 bars): Kick and bass mute completely; emotional exposition of C Minor pads.
- `PREDROP` (Bar 129.1.1 / 512.0 beats, 16 bars): Snare build roll, pitch risers, and -1.5 dB master gain ducking.
- `MAIN DROP` (Bar 145.1.1 / 576.0 beats, 16 bars): Full climax (`DROP :)`); all musical systems active.
- `OUTRO` (Bar 161.1.1 / 640.0 beats, 16 bars): Deconstruction to kick and sub for DJ outro mixing.

---

### 3.2 HOLO Module 2: Groove y Baterías

*Associated Specification:* [`masterclasses/specs/holo_m2_groove_baterias.md`](specs/holo_m2_groove_baterias.md)  
*Specification JSON:* [`masterclasses/specs/holo_m2_groove_baterias.json`](specs/holo_m2_groove_baterias.json)  
*Live Set Asset:* [`masterclasses/holo/modulo_2_groove_baterias.als`](holo/modulo_2_groove_baterias.als) (96.4 KB, 15 tracks)  
*Audio Render Asset:* [`masterclasses/holo/modulo_2_groove_baterias.wav`](holo/modulo_2_groove_baterias.wav) (8.1 MB, 30.476s, RMS: -29.07 dBFS)

#### Dual-Layer Kick Architecture
1. **Kick Punch Layer:** Tuned fundamental at `F` (~46.2 Hz). Provides transient click (3.2 kHz) and punch (70–120 Hz).
   - Device Chain: `Operator` -> `Drum Buss` (Drive 18%, Boom +2.2 dB at 46 Hz, Transients +1.5 dB) -> `EQ Eight` (High-pass 28 Hz 48 dB/oct, surgical notch -2.5 dB at 320 Hz, high boost +1.8 dB at 3,200 Hz).
2. **Kick Sub Body Layer:** Provides round low-end sustain across 40–80 Hz.
   - Device Chain: `Operator` -> `Auto Filter` (Low-pass 90 Hz 24 dB/oct).

#### 16th Sub Rumble Processing Chain
The sub rumble replaces traditional sub basslines in melodic techno drops, generating forward momentum through a specialized serial-parallel DSP chain:
- **Audio Tap:** Parallel send tapped directly from the Kick Punch.
- **Delay:** 1/16 triplet / 1/16 straight delay, 35% feedback.
- **Reverb:** 100% wet, Decay `850 ms`, Pre-delay `0 ms`, Diffusion `100%`.
- **Filtering:** `Auto Filter` with analog `MS2` Korg ladder model, low-pass at `100 Hz` (24 dB/oct), Drive `+3.5 dB`.
- **Saturation:** `Saturator` in Soft Sine mode, Drive `+3.0 dB`, 100% wet.
- **Mono Enforcement:** `Utility` with `Bass Mono` active below `120 Hz`, stereo width set to `0%` (strict mono) to eliminate acoustic phase cancellation in club sound systems.
- **Dynamic Ducking:** `Compressor` sidechained to Kick Punch. Attack: `0.1 ms`, Release: `80 ms`, Ducking depth: `-12 dB`. Leaves the downbeat transient completely transparent, swelling rhythmically across the 16th intervals.

#### Percussion Stems & Drum Programming
- **Clap-Snare Main:** Placed on beats 2 and 4. Sharp initial transient with stereo tail. Routed to `CLA-76` (-12 dB send) and `room` (-14 dB send).
- **Shaker Loop 16th:** Continuous 16th groove high-passed at `450 Hz`, mixed at `-13 dBFS` for organic bed noise.
- **Hi-Hats Offbeat & 16th:** Open hat on offbeat 8ths (propulsion) combined with closed 16th hats.
- **Drum Rack Aux Perc:** Mapped across MIDI pitches: Rimshot Wood (C1 / 36, pan -25), Perc Bongo Tight (D1 / 38, pan +30), Closed Hat Ghost (F#1 / 42, velocities 60–85), Open Hat Sizzle (A#1 / 46).
- **PERCUSSIVE Top Loop:** Band-pass filtered between `800 Hz` and `9,000 Hz` for top-end sizzle.

#### Live 12 Groove Pool & Swing
- **Groove Template:** `Swing 16ths` loaded into Live 12's `Groove Pool`.
- **Application:** Shakers and closed hats set to `Swing 16-59` at `65%` global groove intensity. Auxiliary percussions set to `Swing 16-62`. Kick drum anchored to 100% rigid grid.
- **Drums Group Bus:** Glued with `Glue Compressor` (Attack 30 ms, Release 0.2s, Ratio 2:1, 2.0 dB gain reduction) and `EQ Eight` (+1.2 dB shelf at 10 kHz).

---

### 3.3 HOLO Module 3: Diseño Sonoro (Suite Synthesis)

*Associated Specification:* [`masterclasses/specs/holo_m3_diseno_sonoro.md`](specs/holo_m3_diseno_sonoro.md)  
*Specification JSON:* [`masterclasses/specs/holo_m3_diseno_sonoro.json`](specs/holo_m3_diseno_sonoro.json)  
*Live Set Asset:* [`masterclasses/holo/modulo_3_diseno_sonoro.als`](holo/modulo_3_diseno_sonoro.als) (82.5 KB, 14 tracks)  
*Audio Render Asset:* [`masterclasses/holo/modulo_3_diseno_sonoro.wav`](holo/modulo_3_diseno_sonoro.wav) (10.1 MB, 38.095s, RMS: -25.36 dBFS)

#### Flagship Live 12 Synth Architectures
- **Wavetable Lead (`Wavetable`):**
  - Osc 1: `Retro / Complex` category, `Cobalt` wavetable, position `1.0`, `FM Modern` mode at `0.734`.
  - Osc 2: Sawtooth wave, fine detuning `+7 cents`.
  - Sub Osc: `-1 octave`, level `0.0 dB`.
  - Filter 1: `MS2` ladder circuit, cutoff `650 Hz`, resonance `0.156`, drive `8.81 dB`, envelope decay `800 ms`.
  - Unison: `Shimmer` mode, 4 voices, 25% spread.
  - Glide: Portamento with `30.0 ms` glide time.
- **Multi-Stage Saturation (`Roar`):**
  - Routing: `Parallel / Multi-band`.
  - Mid Stage: `Warm Tube` mode, drive `+6.5 dB`, bias `0.20`.
  - High Stage: `High-cut Crunch`, drive `+4.0 dB`, Envelope Follower modulation `25%`, Feedback `15%`.
  - Dry/Wet: `65%`.
- **Hybrid Bass & Textures (`Meld`):**
  - Engine A: `Virtual Analog Sub` (Pulse/Saw at -1 oct).
  - Engine B: `Rain / Noisy Texture` (resonance 0.65, velocity-reactive).
  - Cross-modulation at `35%`, filter drive `4.5 dB`.
- **Analog Lead (`Drift`):**
  - Osc 1: Saw, Osc 2: Square (+9 cents). `Drift Amount: 0.45` for vintage pitch instability. Wide Chorus mode.
- **FM Digital Stabs (`Operator`):**
  - Algorithm 1 (D -> C -> B -> A). Osc A: Sine, Osc B: Sine 1:1 (-12 dB), Osc C: Sine 2:1 (-24 dB), Osc D: White Noise with `15 ms` decay for percussive transient click. Filter low-pass at `450 Hz`.

#### Dynamic Spectral Cleaning: SC Filter Ducking
- An `Auto Filter` in high-pass mode (`HighPass 24 dB/oct`) set to `200 Hz` is placed on the synth bus, sidechained to `Kick Punch`.
- Each kick strike instantly removes frequencies below 200 Hz in the synths, snapping back when the kick decays, completely eliminating phase mud across 100–250 Hz.

#### Performance Macro Rack Architecture
The lead synth is mapped to an 8-macro `InstrumentRack`:
1. `Macro 1 (Lead Cutoff)`: Wavetable Filter 1 Cutoff (`20 Hz – 20 kHz`).
2. `Macro 2 (Lead Resonance)`: Filter 1 Resonance (`0.00 – 0.85`).
3. `Macro 3 (Envelope Decay)`: Envelope 2 Decay (`50 ms – 3,000 ms`).
4. `Macro 4 (Roar Saturation)`: Roar Drive (`0.0 dB – 18.0 dB`).
5. `Macro 5 (Delay Throw)`: Ping-Pong Delay Send (`0% – 100%`).
6. `Macro 6 (Reverb Wash)`: Long Reverb Send (`0% – 100%`).
7. `Macro 7 (Shimmer Octave)`: SHIMMER Send (`0% – 100%`).
8. `Macro 8 (Stereo Spread)`: Unison Spread (`0% – 200%`).

---

### 3.4 HOLO Module 4: Bases Armónicas y Melódicas

*Associated Specification:* [`masterclasses/specs/holo_m4_bases_armonicas_melodicas.md`](specs/holo_m4_bases_armonicas_melodicas.md)  
*Specification JSON:* [`masterclasses/specs/holo_m4_bases_armonicas_melodicas.json`](specs/holo_m4_bases_armonicas_melodicas.json)  
*Live Set Asset:* [`masterclasses/holo/modulo_4_bases_armonicas_melodicas.als`](holo/modulo_4_bases_armonicas_melodicas.als) (74.8 KB, 14 tracks)  
*Audio Render Asset:* [`masterclasses/holo/modulo_4_bases_armonicas_melodicas.wav`](holo/modulo_4_bases_armonicas_melodicas.wav) (8.1 MB, 30.476s, RMS: -19.72 dBFS)

#### Harmonic Framework & 16-Bar Cyclical Progression
The composition centers on C Minor Natural (Aeolian), progressing through 4 chords across 16 bars:
```
Bars 1–4:   [ Cm(add9) ]  (i  - Tonic Minor)
Bars 5–8:   [ Ab(add9) ]  (VI - Submediant Major)
Bars 9–12:  [ Fm(add9) ]  (iv - Subdominant Minor)
Bars 13–16: [ Gm7      ]  (v  - Dominant Minor Modal)
```

#### Open Voicings & Extended Color
- **Cm(add9):** Root C1 (36) / C2 (48). Upper voices: C3 (48), Eb3 (51), G3 (55), D4 (62). The 9th (D4) provides emotional tension.
- **Ab(add9):** Root Ab0 (32) / Ab1 (44). Upper voices: Ab2 (44), C3 (48), Eb3 (51), Bb3 (58). Imparts dramatic luminosity.
- **Fm(add9):** Root F0 (29) / F1 (41). Upper voices: F2 (41), Ab2 (44), C3 (48), G3 (55). Melancholic descent.
- **Gm7:** Root G0 (31) / G1 (43). Upper voices: G2 (43), Bb2 (46), D3 (50), F3 (53). Modal minor dominant cycling smoothly back to Cm.

#### Bass Architecture & Rhythmic Motifs
1. **Rolling 16th Bass:** Relentless 16th galop on roots and fifths (C1-G1, Ab0-Eb1, F0-C1, G0-D1). Downbeat velocity: `110`; link notes: `75`.
2. **PC2 Triplet Bass Motif:** `3-3-2` syncopated subdivision (offsets `0.0, 0.75, 1.5, 2.0, 2.75, 3.5` within 4/4) deployed in `PUENTE 2` and `DROP 2` for polyrhythmic tension.

#### Live 12 Extended MIDI Capabilities
- **Note Probability:** Programmed via LOM float values (`0.85` on rolling ghost notes, `0.95` on melody notes). Ensures dynamic variation during extended playback.
- **Velocity Deviation:** Range set to `+/- 8` to `+/- 12` units, triggering real-time Gaussian velocity randomization.
- **Fit to Scale & Highlight Scale:** Editor locked to C Minor, enforcing harmonic purity across all generative passes.

---

### 3.5 HOLO Module 5: Arreglo Completo & Master Bus

*Associated Specification:* [`masterclasses/specs/holo_m5_arreglo_completo.md`](specs/holo_m5_arreglo_completo.md)  
*Specification JSON:* [`masterclasses/specs/holo_m5_arreglo_completo.json`](specs/holo_m5_arreglo_completo.json)  
*Live Set Asset:* [`masterclasses/holo/modulo_5_arreglo_completo.als`](holo/modulo_5_arreglo_completo.als) (197.7 KB, 29 tracks)  
*Audio Render Asset:* [`masterclasses/holo/modulo_5_arreglo_completo.wav`](holo/modulo_5_arreglo_completo.wav) (8.1 MB, 30.476s, RMS: -19.64 dBFS)

#### 180-Bar Complete Arrangement Macro-Structure
Consolidates all stems into a 25-track arrangement across 3 nested groups:
- **`DRUMS` Group (8 tracks):** Kick Punch, Kick Sub Body, Kick Sub Rumble, Clap-Snare, Shaker Loop, Hi-Hats, Drum Rack Aux Perc, Top Loop.
- **`SYNTHS` Group (7 tracks):** Wavetable Lead, Meld Bass & Texture, Drift Analog Lead, Operator FM Stabs, Dedicated SUB Bass, Atmospheric Pads, Pluck Arp.
- **`HARMONICS & MELODICS` Group (7 tracks):** Progression Chords, Rolling 16th Bass, PC2 Triplet Bass, Main Lead Theme, Counter-Melody Arp, Structural Fills, Risers & FX.

#### Secret Arrangement Dynamics: Pre-Drop Gain Ducking
- **The Technique:** At bar 144.3 (the final beat before `MAIN DROP` at 145.1.1), the master pre-gain is attenuated `-1.5 dB` via `Utility`.
- **Impact:** At bar 145.1.1, the gain instantly snaps back to `0.0 dB` simultaneously with a crash impact. The ear adapts to the brief dip, causing the full drop to register with perceived loudness and explosive punch.

#### Essential Automation Envelopes
1. `SYNTHS Auto Filter Cutoff`: Sweeps from 350 Hz (Intro) to 18 kHz (Drop 1), sweeps down to 850 Hz (Break), and opens fully to 18.5 kHz (Predrop).
2. `Roar Multi-Stage Drive`: Escalates from +3.0 dB to +10.5 dB in Puente 1, and reaches +12.0 dB in Predrop.
3. `Reverb & Delay Throws`: Automated send bursts on the final beats of bars 48.4, 80.4, and 144.4.

#### Master Bus Processing Chain
1. **`EQ Eight`:** High-pass 25 Hz (48 dB/oct), notch -0.8 dB at 260 Hz, high shelf +0.8 dB at 12 kHz.
2. **`Glue Compressor`:** Attack 30 ms, Release 0.1s (Auto), Ratio 2:1, Gain reduction 1.0–2.0 dB, Makeup +1.5 dB.
3. **`Saturator`:** Analog Clip curve, Drive +0.8 dB, Dry/Wet 15% (parallel density).
4. **`Utility`:** Bass Mono active below 120 Hz, stereo width 105%.
5. **`Limiter`:** Ceiling -0.3 dB (inter-sample peak safety), Lookahead 5.0 ms, Release 100 ms.

---

### 3.6 Peak Time Techno Masterclass (ClaSE PEAK jULIO 25)

*Associated Specification:* [`masterclasses/specs/clase_peak_julio_25.md`](specs/clase_peak_julio_25.md)  
*Specification JSON:* [`masterclasses/specs/clase_peak_julio_25.json`](specs/clase_peak_julio_25.json)  
*Live Set Asset:* [`masterclasses/peak/clase_peak_julio_25_mcp.als`](peak/clase_peak_julio_25_mcp.als) / [`clase_peak_julio_25.als`](peak/clase_peak_julio_25.als) (104.6 KB, 31 tracks)  
*Audio Render Asset:* [`masterclasses/peak/clase_peak_julio_25_mcp.wav`](peak/clase_peak_julio_25_mcp.wav) / [`clase_peak_julio_25.wav`](peak/clase_peak_julio_25.wav) (7.5 MB, 28.444s, RMS: -34.20 dBFS)

#### Global Architectural Metrics
- **Tempo:** 135.00 BPM | **Key/Scale:** G Minor (Sol Menor) | **Time Signature:** 4/4.
- **Arrangement Timeline:** 176 bars (704.0 beats / 312.89s).
- **Track Inventory:** 33 total tracks (27 child stems + 3 nested groups + 3 returns + master).

#### 3-Level Nested Bus Hierarchy
```
Pista Máster (MainTrack) [Limiter + Voxengo SPAN]
  └── 1-Group (Master STEM Bus, Vol -4.7 dB)
        └── 2-Group (Drums & Melodics Bus, Vol -0.7 dB)
              ├── 3-Group (Kick & Sub Bus, Vol -5.7 dB)
              │     ├── 4-OL_SKPA1_Kick_Loop_01_123 (5) (Audio)
              │     └── 5-TWHS_HGE1_RUMBLE_LOOP_08_143BPM (Audio)
              ├── 6-OL_SKPA1_Kick Layer 2 (Audio)
              ├── 7-ADRKT_WTTB4_Synth_10 (MIDI Wavetable)
              ├── 8-Omnisphere Atmosphere (MIDI)
              ├── 9-TWHS_HGE1_CH_LOOP_03 Closed Hat (Audio)
              ├── 10-ADRKT_WTTB4_Synth_26 (MIDI)
              ├── 11-ADRKT_WTTB4_Synth_15 (MIDI)
              ├── Omnisphere Bounced STEM (Audio)
              ├── 13-ADRKT_WTTB4_Synth_18 Arp/Riser (MIDI)
              ├── ADRKT_WTTB4_Bass_01 (MIDI)
              ├── 15-TWHS_HGE1_CLAP_02 (Audio)
              ├── 16 to 21: Vocal Stems & Chops (Audio)
              ├── 22-TA_MK4_SNARE_ROLL_MASSIVE (Audio)
              └── 23-Serum 2 Hook/Arp (MIDI)
```

#### Physical Sample Integration via TakeLanes
The Peak Time reconstruction injects 19 verified physical samples from `/Users/juancruz/Downloads/ClaSE PEAK jULIO 25 Project/Samples/` onto arrangement take lanes:
- `SAMPLE_KICK`: `Processed/Consolidate/OL_SKPA1_Kick_Loop_01_123 (5) [2025-06-25 203905].wav`
- `SAMPLE_RUMBLE`: `Processed/Consolidate/TWHS_HGE1_RUMBLE_LOOP_08_143BPM [2025-06-25 203947].wav`
- `SAMPLE_CH`: `Imported/TWHS_HGE1_CH_LOOP_03_142BPM.wav`
- `SAMPLE_CLAP`: `Processed/Consolidate/TWHS_HGE1_CLAP_02 [2025-06-25 211236].wav`
- `SAMPLE_VOCAL`: `Processed/Consolidate/AU_MTF2_126_vocal_rap_doubles_female_get_naughty_sex_pills_dry_Gmin [2025-06-25 211605].wav`
- `SAMPLE_SNARE`: `Imported/TA_MK4_SNARE_ROLL_MASSIVE_126.wav`
- `SAMPLE_GROOVE`: `Imported/ZEN_KBB_137_drum_groove_storm.wav`
- `SAMPLE_IMPACT`: `Imported/031_FX_Impact_-_SEROTONINTRANCE_Zenhiser.wav`
- `SAMPLE_RISER`: `Imported/ESM_7th_Dimension_Build_Up_Rising_Riser_Cinematic_Trailer_Movie_Transition.wav`
- `SAMPLE_OMNI`: `Processed/Bounce/Bounce 7-Omnisphere [2025-06-25 210111]-2.wav`

#### Vocal Processing & The Band-Pass Spinner
Tracks 16, 18, and 19 feature Peerk's signature vocal modulation:
- **Device:** `AutoFilter` in Band-pass mode (24 dB/oct, `MS2` analog circuit, 15.9% drive).
- **Center Frequency:** `2,490.39 Hz` (~2.5 kHz) with high resonance `0.738`.
- **LFO Modulation:** Sine wave at `0.64 Hz`, amount `14.5%`, `Spin: 0.5`. This induces a continuous binaural rotation between the left and right ears.
- **Sends:** Send A (`Reverb`) = 100%, Send C (`Echo`) = 100%, generating washed out vocal echoes across transitions.

#### Industrial Distortion Chains
Wavetable synth tracks pass through high-gain distortion racks:
`Wavetable (Cobalt FM)` -> `Amp` (vintage lead) -> `Overdrive` -> `Pedal` -> `Redux2` (bitcrush/downsample) -> `Saturator` -> `DrumBuss` -> `EQ Eight`.

#### 5-Snapshot Chronological Evolution
The masterclass development was captured across 5 project snapshots:
1. `Snapshot 1` (20:58, 33 KB): 5 tracks establishing the 135 BPM kick and sub rumble groove.
2. `Snapshot 2` (22:18, 158 KB): 8 tracks adding closed hats, Omnisphere, and Synth 15 lead.
3. `Snapshot 3` (22:58, 560 KB): 29 tracks restructuring into 3 nested groups with claps, snare rolls, Serum, and vocal chops.
4. `Snapshot 4` (23:00, 838 KB): 33 tracks introducing Oscar Mulero's industrial texture and extending to 176 bars.
5. `Snapshot 5` (02:24, 837 KB): Freezing heavy CPU tracks (`Freeze ZEN_KBB`, `Freeze Omnisphere`).

---

## 4. Complete Catalog of Reconstructed Assets

All assets are located in `masterclasses/holo/` and `masterclasses/peak/` and have been programmatically validated against real Ableton Live 12 XML schemas and RIFF audio frames.

### 4.1 Ableton Live Sets (.als) Inventory

| # | Masterclass Module | Relative Path | File Size | User Tracks | XML Root | Creator |
|---|---|---|---|---|---|---|
| 1 | HOLO M1: Concepto y Referencia | `holo/modulo_1_concepto_referencia.als` | 37,604 B | 11 tracks | `<Ableton>` | Ableton Live 12.4.6 |
| 2 | HOLO M2: Groove y Baterías | `holo/modulo_2_groove_baterias.als` | 96,388 B | 15 tracks | `<Ableton>` | Ableton Live 12.4.6 |
| 3 | HOLO M3: Diseño Sonoro | `holo/modulo_3_diseno_sonoro.als` | 82,513 B | 14 tracks | `<Ableton>` | Ableton Live 12.4.6 |
| 4 | HOLO M4: Bases Armónicas y Melódicas | `holo/modulo_4_bases_armonicas_melodicas.als` | 74,779 B | 14 tracks | `<Ableton>` | Ableton Live 12.4.6 |
| 5 | HOLO M5: Arreglo Completo | `holo/modulo_5_arreglo_completo.als` | 197,734 B | 29 tracks | `<Ableton>` | Ableton Live 12.4.6 |
| 6 | Peak Time: ClaSE PEAK jULIO 25 | `peak/clase_peak_julio_25_mcp.als` | 104,642 B | 31 tracks | `<Ableton>` | Ableton Live 12.4.6 |

*Detailed File References:*
- • **HOLO M1 ALS:** [`holo/modulo_1_concepto_referencia.als`](file:///Users/juancruz/ableton-live12-mcp/masterclasses/holo/modulo_1_concepto_referencia.als)
- • **HOLO M2 ALS:** [`holo/modulo_2_groove_baterias.als`](file:///Users/juancruz/ableton-live12-mcp/masterclasses/holo/modulo_2_groove_baterias.als)
- • **HOLO M3 ALS:** [`holo/modulo_3_diseno_sonoro.als`](file:///Users/juancruz/ableton-live12-mcp/masterclasses/holo/modulo_3_diseno_sonoro.als)
- • **HOLO M4 ALS:** [`holo/modulo_4_bases_armonicas_melodicas.als`](file:///Users/juancruz/ableton-live12-mcp/masterclasses/holo/modulo_4_bases_armonicas_melodicas.als)
- • **HOLO M5 ALS:** [`holo/modulo_5_arreglo_completo.als`](file:///Users/juancruz/ableton-live12-mcp/masterclasses/holo/modulo_5_arreglo_completo.als)
- • **Peak Class ALS:** [`peak/clase_peak_julio_25_mcp.als`](file:///Users/juancruz/ableton-live12-mcp/masterclasses/peak/clase_peak_julio_25_mcp.als) (also linked as [`peak/clase_peak_julio_25.als`](file:///Users/juancruz/ableton-live12-mcp/masterclasses/peak/clase_peak_julio_25.als))

### 4.2 Rendered Audio Bounces (.wav) Inventory

| # | Masterclass Module | Relative Path | File Size | Duration | Format | RMS dBFS | Status |
|---|---|---|---|---|---|---|---|
| 1 | HOLO M1: Concepto y Referencia | `holo/modulo_1_concepto_referencia.wav` | 10,080,102 B | 38.095s | 44.1kHz 24b Stereo | -23.86 dBFS | PASS (Non-Silent) |
| 2 | HOLO M2: Groove y Baterías | `holo/modulo_2_groove_baterias.wav` | 8,064,102 B | 30.476s | 44.1kHz 24b Stereo | -29.07 dBFS | PASS (Non-Silent) |
| 3 | HOLO M3: Diseño Sonoro | `holo/modulo_3_diseno_sonoro.wav` | 10,080,102 B | 38.095s | 44.1kHz 24b Stereo | -25.36 dBFS | PASS (Non-Silent) |
| 4 | HOLO M4: Bases Armónicas y Melódicas | `holo/modulo_4_bases_armonicas_melodicas.wav` | 8,064,102 B | 30.476s | 44.1kHz 24b Stereo | -19.72 dBFS | PASS (Non-Silent) |
| 5 | HOLO M5: Arreglo Completo | `holo/modulo_5_arreglo_completo.wav` | 8,064,102 B | 30.476s | 44.1kHz 24b Stereo | -19.64 dBFS | PASS (Non-Silent) |
| 6 | Peak Time: ClaSE PEAK jULIO 25 | `peak/clase_peak_julio_25_mcp.wav` | 7,526,502 B | 28.444s | 44.1kHz 24b Stereo | -34.20 dBFS | PASS (Non-Silent) |

*Detailed File References:*
- • **HOLO M1 WAV:** [`holo/modulo_1_concepto_referencia.wav`](file:///Users/juancruz/ableton-live12-mcp/masterclasses/holo/modulo_1_concepto_referencia.wav)
- • **HOLO M2 WAV:** [`holo/modulo_2_groove_baterias.wav`](file:///Users/juancruz/ableton-live12-mcp/masterclasses/holo/modulo_2_groove_baterias.wav)
- • **HOLO M3 WAV:** [`holo/modulo_3_diseno_sonoro.wav`](file:///Users/juancruz/ableton-live12-mcp/masterclasses/holo/modulo_3_diseno_sonoro.wav)
- • **HOLO M4 WAV:** [`holo/modulo_4_bases_armonicas_melodicas.wav`](file:///Users/juancruz/ableton-live12-mcp/masterclasses/holo/modulo_4_bases_armonicas_melodicas.wav)
- • **HOLO M5 WAV:** [`holo/modulo_5_arreglo_completo.wav`](file:///Users/juancruz/ableton-live12-mcp/masterclasses/holo/modulo_5_arreglo_completo.wav)
- • **Peak Class WAV:** [`peak/clase_peak_julio_25_mcp.wav`](file:///Users/juancruz/ableton-live12-mcp/masterclasses/peak/clase_peak_julio_25_mcp.wav) (also linked as [`peak/clase_peak_julio_25.wav`](file:///Users/juancruz/ableton-live12-mcp/masterclasses/peak/clase_peak_julio_25.wav))

---

## 5. Standalone Python Builder Scripts

All builder scripts reside in [`masterclasses/scripts/`](scripts/) and can be executed independently or orchestrated as an automated batch.

### 5.1 Architecture of builder_base.py

[`builder_base.py`](scripts/builder_base.py) encapsulates the shared infrastructure:
- `clean_session_reset(client, target_tempo, target_scale_root, target_scale_name)`: Non-destructive in-process RPC reset.
- `save_live_set(client, destination_als_path, timeout_sec)`: AppleScript UI automation driving `Shift+Cmd+S`, sheet handling, and file consolidation.
- `export_audio_bounce(client, destination_wav_path, duration_beats, timeout_sec)`: Menu automation, loop boundary configuration, file stabilization, and `ffmpeg` 24-bit PCM conversion.
- `verify_als_integrity(als_path, expected_min_tracks)`: Gzip decompression, `<LiveSet>` validation, track counting, and locator parsing.
- `verify_pcm_wav_energy(wav_path, min_duration_sec, min_rms_dbfs)`: RIFF chunk parsing, 24-bit sample normalization, and pure-Python RMS calculation.
- `verify_als_and_wav(...)`: Composite assertion verifying both container integrity and audio energy.
- `MasterclassBuilder`: Base class managing JSON spec loading, connection management, locator generation, return track creation, track instantiation, browser device loading, clip programming with Live 12 extended notes, and take lane audio sample injection.

### 5.2 Module Builders Catalog

- [`build_holo_m1.py`](scripts/build_holo_m1.py): Builds HOLO Module 1 reference track structure, audition stems, 6 returns, and 11 locators.
- [`build_holo_m2.py`](scripts/build_holo_m2.py): Builds HOLO Module 2 drum stems (Kick Punch, Sub Body, 16th Rumble, Claps, Hats, Shakers, Aux Percussion) and DRUMS group bus.
- [`build_holo_m3.py`](scripts/build_holo_m3.py): Builds HOLO Module 3 synth sound design stems (Wavetable Lead, Meld Bass, Drift Lead, Operator FM, Sub, Pads, Pluck Arp) and SYNTHS group bus.
- [`build_holo_m4.py`](scripts/build_holo_m4.py): Builds HOLO Module 4 harmonic progression (`Cm-Ab-Fm-Gm`), rolling 16th bass, PC2 triplet bass, lead theme, and HARMONICS & MELODICS bus.
- [`build_holo_m5.py`](scripts/build_holo_m5.py): Builds HOLO Module 5 25-track arrangement across 3 nested groups, pre-drop gain ducking, and 5-device master processing chain.
- [`build_peak_class.py`](scripts/build_peak_class.py): Builds Peak Time Techno 33-track project with 3-level nested groups (`1-Group`, `2-Group`, `3-Group`) and 19 physical audio samples.
- [`run_all_masterclasses.py`](scripts/run_all_masterclasses.py): Orchestrates sequential execution of all 6 builders with cool-down pauses and emits a consolidated JSON report.

### 5.3 Reproduction Commands

Ensure `/Applications/Ableton Live 12 Suite.app` is running and the `Live12Bridge` control surface is active on `127.0.0.1:11246`.

#### Execute Individual Masterclass Builders
```bash
# Set PYTHONPATH to include src and masterclasses/scripts
export PYTHONPATH="src:masterclasses/scripts:$PYTHONPATH"

# Build HOLO Module 1
python3 masterclasses/scripts/build_holo_m1.py

# Build HOLO Module 2
python3 masterclasses/scripts/build_holo_m2.py

# Build HOLO Module 3
python3 masterclasses/scripts/build_holo_m3.py

# Build HOLO Module 4
python3 masterclasses/scripts/build_holo_m4.py

# Build HOLO Module 5
python3 masterclasses/scripts/build_holo_m5.py

# Build Peak Time Class
python3 masterclasses/scripts/build_peak_class.py
```

#### Execute Full Batch Suite Orchestrator
```bash
export PYTHONPATH="src:masterclasses/scripts:$PYTHONPATH"
python3 masterclasses/scripts/run_all_masterclasses.py
```

### 5.4 Programmatic Verification Commands

To independently verify the generated files on disk without launching a build:
```bash
PYTHONPATH="src:masterclasses/scripts" python3 -c "
import glob, sys
from builder_base import verify_als_and_wav

targets = [
    ('HOLO M1', 'masterclasses/holo/modulo_1_concepto_referencia.als', 'masterclasses/holo/modulo_1_concepto_referencia.wav', 4),
    ('HOLO M2', 'masterclasses/holo/modulo_2_groove_baterias.als', 'masterclasses/holo/modulo_2_groove_baterias.wav', 8),
    ('HOLO M3', 'masterclasses/holo/modulo_3_diseno_sonoro.als', 'masterclasses/holo/modulo_3_diseno_sonoro.wav', 7),
    ('HOLO M4', 'masterclasses/holo/modulo_4_bases_armonicas_melodicas.als', 'masterclasses/holo/modulo_4_bases_armonicas_melodicas.wav', 7),
    ('HOLO M5', 'masterclasses/holo/modulo_5_arreglo_completo.als', 'masterclasses/holo/modulo_5_arreglo_completo.wav', 25),
    ('Peak Class', 'masterclasses/peak/clase_peak_julio_25_mcp.als', 'masterclasses/peak/clase_peak_julio_25_mcp.wav', 27)
]

for name, als, wav, min_tracks in targets:
    res = verify_als_and_wav(als, wav, expected_min_tracks=min_tracks, min_duration_sec=10.0, min_rms_dbfs=-40.0)
    status = 'PASS' if res['valid'] else 'FAIL'
    print(f'[{status}] {name:15} | Tracks: {res[\"als\"][\"user_tracks_count\"]:2d} | Duration: {res[\"wav\"][\"duration_sec\"]:5.2f}s | RMS: {res[\"wav\"][\"rms_dbfs\"]:6.2f} dBFS')
"
```

---

## 6. LOM & MCP Tool Cross-Reference

The table below maps every high-level musical and architectural workflow demonstrated in the masterclasses to its corresponding Live Object Model (LOM) path and native `ableton-live12` MCP tool:

| Musical & Architectural Domain | Practical Production Operation | Live Object Model (LOM) C++ / Python Binding | Native MCP Tool Name |
|---|---|---|---|
| **1. Transport & Project Setup** | Start / stop arrangement playback | `Live.Song.Song.is_playing`, `start_playing()`, `stop_playing()` | `live12_transport_play`, `live12_transport_stop` |
| | Set global project BPM | `Live.Song.Song.tempo` | `live12_transport_set_tempo` |
| | Set project time signature | `Live.Song.Song.signature_numerator`, `signature_denominator` | `live12_transport_set_time_signature` |
| | Configure arrangement loop boundaries | `Live.Song.Song.loop`, `loop_start`, `loop_length` | `live12_transport_set_loop` |
| | Punch In / Punch Out boundaries | `Live.Song.Song.punch_in`, `punch_out` | `live12_transport_set_punch` |
| | Set musical scale & root note | `Live.Song.Song.scale_information.root_note`, `scale_name` | `live12_song_set_scale` |
| | Configure microtonal tuning systems | `Live.Song.Song.tuning_system` | `live12_song_set_tuning_system` |
| **2. Arrangement & Locators** | Create / delete arrangement cue points | `Live.Song.Song.set_or_delete_cue()`, `cue_points` | `live12_cue_point_control` |
| | Rename arrangement locator | `Live.Song.CuePoint.name` | `live12_lom_set` (`song.cue_points.<idx>.name`) |
| | Jump playhead to time in beats | `Live.Song.Song.current_song_time` | `live12_lom_set` (`song.current_song_time`) |
| **3. Tracks & Hierarchy** | Create MIDI, Audio, or Return tracks | `Live.Song.Song.create_midi_track()`, `create_audio_track()`, `create_return_track()` | `live12_track_create` |
| | Delete tracks during session reset | `Live.Song.Song.delete_track()`, `delete_return_track()` | `live12_track_delete`, `live12_lom_call` |
| | Name, color, mute, solo, arm tracks | `Live.Track.Track.name`, `color`, `mute`, `solo`, `arm` | `live12_track_set_properties` |
| | Group tracks into parent bus | `Live.Song.Song.create_group_track()`, `Track.group_track` | `live12_track_group` |
| | Ungroup / dissolve group buses | `Live.Song.Song.ungroup_track()` | `live12_track_ungroup` |
| **4. Mixer & Signal Routing** | Set track fader volume & pan | `Live.MixerDevice.MixerDevice.volume`, `panning` | `live12_mixer_set` |
| | Set auxiliary send levels (A–F) | `Live.MixerDevice.MixerDevice.sends` | `live12_mixer_set` |
| | Crossfader assignment (A/B/None) | `Live.MixerDevice.MixerDevice.crossfade_assign` | `live12_mixer_set` |
| | Route audio to Cue Out / Ext Out | `Live.Track.Track.output_routing_type`, `output_routing_channel` | `live12_routing_set` |
| | Inspect available track routings | `Live.Track.Track.available_input_routing_types`, `available_output_routing_types` | `live12_routing_get` |
| **5. Clips & Extended MIDI** | Create empty Session MIDI clips | `Live.ClipSlot.ClipSlot.create_clip()` | `live12_clip_create` |
| | Inject Live 12 extended notes | `Live.Clip.Clip.add_new_notes()` (supports probability & velocity deviation) | `live12_clip_add_notes` |
| | Read back extended MIDI notes | `Live.Clip.Clip.get_notes_extended(from_pitch, pitch_span, from_time, time_span)` | `live12_clip_get_notes` |
| | Duplicate session clip to arrangement | `Live.Track.Track.duplicate_clip_to_arrangement()` | `live12_clip_duplicate_to_arrangement` |
| | Quantize notes to musical grid | `Live.Clip.Clip.quantize()` | `live12_clip_quantize` |
| | Remove notes by ID or window | `Live.Clip.Clip.remove_notes_by_id()`, `remove_notes_extended()` | `live12_clip_remove_notes` |
| | Algorithmic MIDI transformations | Live 12 MIDI tool transforms (humanize, ramps, Euclidean, arpeggiate) | `live12_clip_transform_midi` |
| | Clip parameter automation envelopes | `Live.Clip.Clip.automation_envelope()`, `insert_step()` | `live12_clip_envelope_control` |
| | Groove Pool swing assignment | `Live.Song.Song.groove_pool`, `Clip.groove` | `live12_groove_pool_control` |
| **6. TakeLanes & Comping** | Create take lane on arrangement track | `Live.Track.Track.create_take_lane()` | `live12_take_lane_create` |
| | Inject audio sample onto take lane | `Live.TakeLane.TakeLane.create_audio_clip()` | `live12_take_lane_create_audio_clip` |
| | Comp take lane region into track | `Live.TakeLane.TakeLane.comp_region()` | `live12_take_lane_comp_region` |
| | List all take lanes on a track | `Live.Track.Track.take_lanes` | `live12_take_lane_list` |
| **7. Browser & Device Loading** | Search instruments, fx & samples | `Live.Application.Application.browser` query hierarchy | `live12_browser_search` |
| | Load native device onto track/chain | `Live.Application.Application.browser.load_item()` | `live12_browser_load_item` |
| | Preview/audition audio samples | `Live.Application.Browser.preview_item()`, `stop_preview()` | `live12_browser_preview` |
| **8. Devices, Parameters & Racks** | Inspect device chain on track | `Live.Track.Track.devices` | `live12_device_list` |
| | Query device parameters | `Live.Device.Device.parameters` | `live12_device_get_parameters` |
| | Modulate device parameter | `Live.DeviceParameter.DeviceParameter.value` | `live12_device_set_parameter` |
| | Enable / disable (bypass) device | `Live.Device.Device.is_active` | `live12_device_toggle` |
| | Control rack macro knobs (1–16) | `Live.RackDevice.RackDevice.parameters` (Macro 1–16) | `live12_rack_macro_control` |
| | Store / recall Macro Variations | `Live.RackDevice.RackDevice.store_variation()`, `recall_variation()` | `live12_rack_variation_control` |
| | Configure rack macro count | `Live.RackDevice.RackDevice.visible_macro_count` | `live12_rack_macro_config` |
| | Wavetable Modulation Matrix | `Live.WavetableDevice.WavetableDevice.set_modulation_value()` | `live12_wavetable_modulation_matrix` |
| | Roar Multi-Stage Saturation | `Live.RoarDevice.RoarDevice` parameters | `live12_roar_control` |
| | Meld Macro Synthesizer | `Live.MeldDevice.MeldDevice` engine parameters | `live12_meld_control` |
| | Drift Subtractive Synthesizer | `Live.DriftDevice.DriftDevice` voice/drift parameters | `live12_drift_control` |
| | Simpler sample replacement & slicing | `Live.SimplerDevice.SimplerDevice.slice_to_drum_rack()` | `live12_simpler_control` |
| | Drum Rack pad mute / solo / copy | `Live.DrumPad.DrumPad`, `RackDevice.copy_pad()` | `live12_drum_pad_control` |
| | CC Control MIDI parameter mapping | `Live.CcControlDevice.CcControlDevice` | `live12_cc_control` |
| **9. Views, Dialogs & OS** | Switch GUI views (Session/Arranger) | `Live.Application.View.show_view()`, `focus_view()` | `live12_view_switch` |
| | Select track / device / clip in UI | `Live.Application.View.selected_track`, `select_device()` | `live12_view_select` |
| | Inspect native modal dialogs | `Live.Application.Application.open_dialog_count`, `current_dialog_message` | `live12_dialog_inspect` |
| | Press native modal dialog buttons | `Live.Application.Application.press_current_dialog_button()` | `live12_dialog_press` |
| | Save Live Set (.als) to disk | macOS AppleScript `Shift+Cmd+S` + sheet handling | `live12_os_save_set` |
| | Open Live Set (.als) from disk | macOS LaunchServices / AppleScript | `live12_os_open_set` |
| | Export audio render (.wav) | macOS AppleScript menu automation + ffmpeg 24b PCM | `live12_os_export_audio` |
| | Undo / Redo operations | `Live.Song.Song.undo()`, `redo()` | `live12_undo_redo` |
| | Universal dynamic LOM introspection | Arbitrary Boost.Python property reflection & discovery | `live12_lom_inspect` |
| | Universal dynamic LOM read | Arbitrary Boost.Python property getter | `live12_lom_get` |
| | Universal dynamic LOM write | Arbitrary Boost.Python property setter | `live12_lom_set` |
| | Universal dynamic LOM method call | Arbitrary Boost.Python method invocation with args/kwargs | `live12_lom_call` |

---

*This concludes the masterclass engineering playbook. All accompanying scripts, schemas, specs, and audio assets remain committed and verified in this repository.*
