# Space 92 (*Gravity*) & Peak-Time Psy-Tech Playbook

Reference recipe for building Space 92 style Peak-Time / Rolling Psy-Tech tracks in Ableton Live 12 Suite (`136.0–138.0 BPM`, `Phrygian` mode).

## 1. Signature Sonic DNA

1. **The `K-B-B-B` Rolling 16th Sub-Bass Engine (Psy-Trance Inheritance):**
   - Unlike muddy warehouse rumble techno, Space 92 uses a surgical 16th-note rolling bassline where step `0.00` of every beat is silent (occupied by the Kick transient) and steps `0.25`, `0.50`, and `0.75` fire tight, percussive sub-bass pulses:
     - `0.25` (first 16th after Kick): `velocity = 82`, `duration = 0.20` (ghost recovery note, simulates sidechain ducking).
     - `0.50` (`&` offbeat): `velocity = 122`, `duration = 0.22` (primary offbeat bounce).
     - `0.75` (fourth 16th): `velocity = 108`, `duration = 0.22` (forward propulsion into the next Kick).
   - **Ableton Device Chain (`Operator`):**
     - Load `Operator` + `Saturator` + `Compressor`.
     - Set Oscillator A to Saw/Square hybrid with steep 24 dB Low-Pass Filter (`Filter Freq = 0.26` / `~185 Hz`, `Filter Res = 0.22`, zero sustain tail so every 16th note stops cleanly before the next).
     - Keep sub fundamental locked to root (`G1 = MIDI 43` at `49.0 Hz` or `F1 = MIDI 41` at `43.65 Hz`), stepping up to `b2` (`Ab1 = MIDI 44`) on beat 15 of every 16-beat phrase for Phrygian tension.

2. **Dual Low-End Layering (Sub `K-B-B-B` + High-Passed Techno Texture Rumble):**
   - Layer a warehouse rumble audio loop underneath the `K-B-B-B` MIDI sub, but **high-pass the rumble at `125 Hz` and low-pass at `360 Hz`** (`fader = -9.0 dB`).
   - Result: `45–115 Hz` stays 100% phase-clean (`Kick` + `K-B-B-B`), while `125–360 Hz` provides the dark cavern room texture.

3. **The *Gravity* / *Dominator* Octave Hoover Anthem (`Wavetable`):**
   - Load `Wavetable` → `EQ Eight` (HPF `210 Hz`) → `Chorus-Ensemble` → `Reverb`.
   - Set Oscillator 1 & 2 to Detuned Sawtooths + Sub Oscillator + heavy Unison (`param 89 = 0.78`, `voices = 0.42`).
   - Program MIDI phrases in **stacked octaves** (`G3 + G4`, rising to `D4 + D5` and `Eb4 + Eb5`, resolving down the Phrygian scale `Bb3 → Ab3 → G3`).
   - Automate `Filter 1 Freq` (`param 26`) from `0.45` (Breakdown reveal) up to `0.96` (Pre-Drop Climax).

4. **The 4-Beat Pre-Drop Vacuum (Bar 48 / `beats 188.0..192.0`):**
   - Cut all drums, risers, snare rolls, and synths dead on `beat 188.0`.
   - Leave 4 beats (`1.74 seconds` at `138 BPM`) of stark space before slamming the full `Kick + K-B-B-B + Hoover + Sub Impact` at `beat 192.0`.

## 2. Reference Script in Repo
- Executable builder: [`/Users/juancruz/ableton-live12-mcp/masterclasses/scripts/build_space92_gravity_psytech.py`](file:///Users/juancruz/ableton-live12-mcp/masterclasses/scripts/build_space92_gravity_psytech.py)
