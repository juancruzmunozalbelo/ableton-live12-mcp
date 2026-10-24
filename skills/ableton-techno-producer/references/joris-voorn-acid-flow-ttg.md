# Joris Voorn (*Acid Flow / Trip to Galaxy Edit*) Playbook

Reference recipe for building hypnotic Dutch Festival Acid Techno (Joris Voorn *Acid Flow* / Awakenings *Trip to Galaxy Edit*) combined with a modern Peak-Time chassis in Ableton Live 12 Suite.

## 1. Signature Sonic DNA

1. **The Dual TB-303 Acid Engine (`Analog` / `Drift`):**
   - Instead of relying on a single static lead, Joris Voorn's *Acid Flow* creates movement through **two interlocking TB-303 lines** with independent filter characters and loop lengths:
   - **Track 04 — Main TB-303 Lead (16-Step `G Phrygian` Motif):**
     - Device chain: `Analog` → `EQ Eight` (HPF `135 Hz`) → `Overdrive` (gentle mid bite: `Drive=0.28, Tone=0.52, Dry/Wet=0.22`) → `Delay` (Ping-Pong `Dry/Wet=0.18`).
     - Notes: Continuous 1/16th pattern anchoring on root `G2 (MIDI 55)` and `G1 (MIDI 43)`, jumping to octave `G3 (MIDI 67)`, Phrygian `Ab2 (MIDI 56)`, `Bb2 (MIDI 58)`, `D3 (MIDI 62)`, and `Eb3 (MIDI 63)`.
     - **Accents & Slides:** Program accented steps (`velocity = 124–127`) and overlapping legato durations (`duration = 0.32` on a `0.25` grid) so the filter envelope glides between pitches like a hardware Roland TB-303.
     - **Clip Filter Envelopes Across the Arrangement:**
       - `Intro (0..64)`: `F1 Freq` sweeps `0.25 → 0.42`, `Reso = 0.62` (deep subterranean bubbling).
       - `TTG Groove (64..128)`: `F1 Freq` sweeps `0.42 → 0.68`, `Reso = 0.74`.
       - `Breakdown Meltdown (128..176)`: `F1 Freq` sweeps `0.38 → 0.88`, `Reso = 0.82`.
       - `Pre-Drop Acid Scream (176..188)`: `F1 Freq` sweeps `0.82 → 0.95`, `Reso = 0.88` (stops dead at `188.0`).
       - `Peak Drop (192..256)`: `F1 Freq` sweeps `0.72 → 0.92`, `Reso = 0.80`.
   - **Track 05 — Counter TB-303 (`5/16` Polyrhythm + `MS-20` Filter):**
     - Device chain: `Drift` → `EQ Eight` (HPF `165 Hz`) → `Auto Filter` (`Filter Type = LP`, `Slope = 24 dB`, `Circuit = MS-20 / 2.0`, `Drive = 3.5 dB`, `Resonance = 0.52`, `LFO Amount = 0.28`).
     - Notes: A **5-sixteenth-note motif** (`5 * 0.25 = 1.25 beats`) repeated across the 16-beat bar (`step = idx * 0.25`, `m = motif[idx % 5]`). Because `5` does not divide `16` evenly, the accent shifts against the `4/4` Kick on every single bar.
     - Keep fader at `-8.5 dB` and pan at `+0.18` (`pan = -0.12` on Main 303) for wide stereo separation.

2. **Authentic TR-909 Cymbal Architecture (`Open Hat` + `Acid Ride`):**
   - **Track 09 — 909 Offbeat Open Hat (`&`):**
     - Sample source: `/Applications/Ableton Live 12 Suite.app/Contents/App-Resources/Core Library/Samples/Drums/Hihat/Hihat Open 909.aif`.
     - Render a sample-accurate 16-beat loop placing the 909 Open Hat on every `&` (`(b + 0.5) * beat_frames`), filtered `480 Hz – 8500 Hz` with exponential decay (`fade_exp = 1.6`, `gain = 0.18`, track fader `-10.5 dB`) so it glides smoothly without harshness.
   - **Track 10 — 909 Acid Ride (Climax Layer):**
     - Sample source: `/Applications/Ableton Live 12 Suite.app/Contents/App-Resources/Core Library/Samples/Drums/Ride/Ride 909.aif`.
     - Render 16th-note ride hits on steps `0.25 (vel 0.45)`, `0.50 (vel 1.0)`, `0.75 (vel 0.72)` of each beat (leaving `0.00` ducked for the Kick), `gain = 0.16`, track fader `-10.0 dB`.
     - Hold back the 909 Ride until **Bar 25 (`beat 96.0`)** and **Drop Part 2 (Bar 57 / `beat 224.0`)** so the second half of the Drop surges in energy.

## 2. Reference Script in Repo
- Executable builder: [`/Users/juancruz/ableton-live12-mcp/masterclasses/scripts/build_joris_acid_flow_ttg.py`](file:///Users/juancruz/ableton-live12-mcp/masterclasses/scripts/build_joris_acid_flow_ttg.py)
