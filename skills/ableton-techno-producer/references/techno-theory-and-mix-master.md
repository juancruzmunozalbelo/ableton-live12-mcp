# Peak-Time & Acid Techno Theory, Pre-Mix & Master Bus Reference

## 1. Scale & Club Sub Physics (`G Phrygian` vs `F Phrygian`)

- **Club Sub Sweet Spot (`43 Hz – 52 Hz`):**
  - `F1 = 43.65 Hz` (MIDI `41`) and `G1 = 49.00 Hz` (MIDI `43`) hit the exact resonant peak of festival bass arrays (Funktion-One / L-Acoustics).
- **The Phrygian Mode (Dark Hypnotic Tension):**
  - Unlike Natural Minor (whole step between degree 1 and 2), **Phrygian** places a **semitone (`b2`)** right above the root:
    - **G Phrygian:** `G (root) – Ab (b2) – Bb (b3) – C (4) – D (5) – Eb (b6) – F (b7)`.
    - **F Phrygian:** `F (root) – Gb (b2) – Ab (b3) – Bb (4) – C (5) – Db (b6) – Eb (b7)`.
  - **The Golden Interval Rule:** Anchor 80% of the sub-bass and 303 notes on the **Root (`1`)**, **Octave (`8`)**, and **Fifth (`5`)**, and use the **Flat Second (`b2`)** (`Ab` in G Phrygian) at the end of 4-bar and 8-bar phrases to create dark magnetic pull back to the root.

---

## 2. Vertical Frequency Allocation & Pre-Mix Gain Staging

Never let two tracks fight for the same frequency band. Apply an `EQ Eight` high-pass cut on every track above the Kick and Sub:

- **Band 1 — Sub Foundation (`30 – 115 Hz`, Strictly Mono):**
  - `01 [LOW] KICK`: `0.0 dB` (Fundamental `49 Hz` in `G1`).
  - `02 [LOW] PSY K-B-B-B SUB`: `-3.5 dB` (Plays only on steps `0.25, 0.50, 0.75` between Kick hits; LPF `185 Hz`).
  - `07 [BASS PAD] DARK REESE DRONE`: `-4.5 dB` (Plays **only** during the Breakdown `beats 128..188` when the Kick & K-B-B-B are silent; LPF `280 Hz`).
- **Band 2 — Low-Mid Cavern Body (`125 – 350 Hz`):**
  - `03 [LOW] TECHNO RUMBLE`: `-9.0 dB` (`HPF 125 Hz`, `LPF 360 Hz` so it never muddies the `49 Hz` sub).
- **Band 3 — Acid & Mid Presence (`160 Hz – 4.5 kHz`):**
  - `04 [ACID] TB-303 MAIN LEAD`: `-2.5 dB`, `pan = -0.12`, `HPF 135 Hz`.
  - `05 [ACID] TB-303 COUNTER 5/16`: `-8.5 dB`, `pan = +0.18`, `HPF 165 Hz`, `MS-20 Drive = 3.5 dB`.
  - `06 [SYNTH] SPACE92 HOOVER ANTHEM`: `-3.2 dB`, wide unison, `HPF 210 Hz`.
  - `13 [ATMOS] TUNED VOCAL PAD (G3)`: `-5.0 dB`, `HPF 220 Hz`.
- **Band 4 — High-Mid Groove & Transients (`400 Hz – 8.5 kHz`):**
  - `11 [DRUMS] CLAP & GROOVE STORM`: `-8.5 dB`, `HPF 220 Hz`.
  - `12 [BUILD] RISER & SNARE ROLL`: `-7.5 dB`, `HPF 210 Hz`, `LPF 7.0 kHz`.
- **Band 5 — Silky Air & Cymbals (`4.5 – 16 kHz`):**
  - `08 [DRUMS] 909 CLOSED HATS`: `-9.5 dB`, `HPF 380 Hz`.
  - `09 [DRUMS] 909 OPEN HAT (&)`: `-10.5 dB`, `HPF 450 Hz`, `LPF 8.5 kHz`.
  - `10 [DRUMS] 909 ACID RIDE`: `-10.0 dB`, `HPF 550 Hz`, `LPF 8.2 kHz`.

---

## 3. Return Buses & Master Bus Chain

- **Return A — `A-DARK CLUB HALL REVERB`:**
  - `Reverb` (`Decay = 0.62`, `Dry/Wet = 1.0`) → `EQ Eight` (`HPF 250 Hz` so reverb tails never muddy the sub).
- **Return B — `B-303 PING-PONG DELAY`:**
  - `Delay` (`Feedback = 0.45`, `Dry/Wet = 1.0`) → `EQ Eight` (`HPF 300 Hz`).
- **Master Track Chain:**
  1. `EQ Eight`: `48 dB/oct` brickwall high-pass cut at `30 Hz` (removes DC offset and subsonic rumble) + `+1.2 dB` high-shelf air boost at `10 kHz`.
  2. `Glue Compressor`: Slow attack (`30 ms`) to let Kick transients punch through, fast auto release, `Threshold = -4.5 dB`, `Makeup = +2.2 dB`, `Dry/Wet = 75%`.
  3. `Saturator`: `+1.8 dB` drive (`Dry/Wet = 35%`) for analog harmonic density.
  4. `Limiter`: `+2.5 dB` gain into `-0.3 dB` true-peak ceiling.
