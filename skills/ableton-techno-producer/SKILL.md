---
name: ableton-techno-producer
description: Produce, arrange, mix, master, and color-code Peak-Time Techno, Acid Techno (Joris Voorn / Trip to Galaxy), and Psy-Tech (Space 92 / Gravity) tracks inside Ableton Live 12 Suite via the ableton-live12 MCP server. Use when building tracks, programming TB-303 acid lines, rolling K-B-B-B basslines, organizing the Ableton Arrangement grid with colors/names, or generating interactive HTML studio arrangement maps.
---

# Ableton Live 12 Techno Producer (`ableton-live12` MCP)

End-to-end production, arrangement, surgical pre-mixing, mastering, and visual grid organization for Ableton Live 12.4.6 Suite via `Live12Client` (`127.0.0.1:11246`).

## Reference Playbooks (Load by Branch)

- **Space 92 (*Gravity*) & Rolling Psy-Tech branch** → read [`references/space92-peak-psytech.md`](references/space92-peak-psytech.md) for the `K-B-B-B` rolling sub-bass engine, `Dominator Hoover` supersaw lead, and 4-beat `Pre-Drop Silence`.
- **Joris Voorn (*Acid Flow / Trip to Galaxy*) & Dual TB-303 branch** → read [`references/joris-voorn-acid-flow-ttg.md`](references/joris-voorn-acid-flow-ttg.md) for the Dual TB-303 (`16/16` Lead + `5/16` Polyrhythm) filter-sweep engine, TR-909 Offbeat Open Hat (`&`), and 909 Acid Ride climax.
- **Music Theory, Frequency Allocation, Pre-Mix & Master Bus branch** → read [`references/techno-theory-and-mix-master.md`](references/techno-theory-and-mix-master.md) for the Phrygian `b2` tension formula, 5-layer vertical EQ spectrum, Breakdown Sub-Floor (`Dark Reese Drone`), and Master Bus chain.

---

## Non-Negotiable MCP & Audio Engineering Invariants

Every Ableton Live 12 session built or modified through `ableton-live12` must obey these 6 execution rules:

### 1. Main Arrangement Lane Injection (Zero TakeLanes Clutter)
Place every clip directly onto the main track lane (`song.tracks.{idx}.arrangement_clips`) so waveforms and MIDI notes are immediately visible in Arrangement View without expanding `TakeLanes`:
- **Audio Clips on Arrangement:**
  ```python
  c.call("live12_lom_call", {
      "target_path": f"song.tracks.{track_idx}",
      "method_name": "create_audio_clip",
      "args": [sample_path, float(start_beat)],
  })
  ```
- **MIDI Clips on Arrangement (with Filter Envelopes):**
  1. Create the MIDI clip in Session slot (`live12_clip_create`), add notes (`live12_clip_add_notes`), and write device parameter envelopes (`live12_clip_envelope_control` with `insert_step`) while in the Session slot.
  2. Resolve the Session clip object and duplicate it onto the main Arrangement track at each target beat:
     ```python
     clip_ref = c.call("live12_lom_get", {
         "target_path": f"song.tracks.{track_idx}.clip_slots.{slot_idx}",
         "property_name": "clip",
     })["value"]
     for pos in arrangement_positions:
         c.call("live12_lom_call", {
             "target_path": f"song.tracks.{track_idx}",
             "method_name": "duplicate_clip_to_arrangement",
             "args": [clip_ref["lom_id"], float(pos)],
         })
     ```

### 2. Sample-Accurate Multi-Beat Audio Loops (Never Use `ffmpeg adelay` on Stereo Loops)
In `ffmpeg`, `adelay=d0|d1|d2...` delays individual channels (`L`, `R`) rather than repeating a one-shot across 16 beats on a stereo file. Always construct 16-beat (4-bar) drum and rumble loops using Python standard library `array('h')` + `wave` frame placement:
```python
sr = 44100
beat_frames = int(round((60.0 / bpm) * sr))  # e.g., 19,174 frames at 138.0 BPM
bar4_frames = beat_frames * 16               # 306,784 frames per 4-bar block
```
Place one-shots on exact frame boundaries (`b * beat_frames` for downbeats, `int((b + 0.5) * beat_frames)` for `&` offbeats) with exponential decay envelopes and conservative headroom (`gain <= 0.20` for 909 hats/rides, `gain <= 0.45` for rumbles).

### 3. Unified Harmonic Tuning Across Audio Samples & MIDI
Never mix untuned audio samples (e.g., a Kick in `G1 = 49 Hz` or a Vocal Pad in `C4`) with MIDI notes in a conflicting key (e.g., `F Phrygian`).
- Before writing MIDI notes, inspect the fundamental frequency of the Kick and tonal samples.
- Align `live12_song_set_scale` (`root_note`, `scale_name="Phrygian"`) with the Kick fundamental (`root_note=7` for `G Phrygian`, `root_note=5` for `F Phrygian`), and pitch-shift any tonal audio pad/vocal (`asetrate` + `aresample=44100`) to the exact root or 5th of the project scale.

### 4. Breakdown Sub-Floor & 4-Beat Pre-Drop Silence
- **Breakdown Sub-Floor:** Whenever the Kick drops out during the main Breakdown (e.g., Bars 33–47 / `beats 128..188`), insert a low-passed `Dark Reese Drone` (`Wavetable` saw unison low-passed at `~280 Hz` playing root `G1 + G2 + D3`) so the club floor never loses physical weight while the `TB-303` and `Hoover` sweep upward.
- **Pre-Drop Silence (Bar 48 / `beats 188..192`):** Cut all melodic, bass, and drum build clips dead on `beat 188.0` (use shortened 12-beat climax clips at `176.0..188.0` and trim the Snare Roll to end at `188.0`). Leave `188.0..192.0` clear for a single dry/delayed vocal hook or sub vacuum before firing the `Peak Drop` at `192.0`.

### 5. Grid Color-Coding & Clip Naming Standard
After placing clips on the Arrangement timeline, iterate through `song.tracks.{t}.arrangement_clips.{c}` and set both `name` (prefixed with `[INTRO]`, `[TTG]`, `[BREAK]`, `[CLIMAX]`, `[DROP 1]`, `[DROP 2]`) and `color_index`:
- **Red (`14`, `15`, `16`):** `[LOW]` Kick, `K-B-B-B` Sub Bass, High-Passed Techno Rumble.
- **Orange / Acid Amber / Lime (`17`, `18`, `19`, `52`):** `[ACID]` Dual TB-303 tracks (shift clip `color_index` from `16` closed → `18` opening → `17` meltdown → `14` scream → `52` neon drop).
- **Magenta / Purple (`60`, `49`):** `[SYNTH]` Space 92 Hoover Anthem & Dark Reese Breakdown Floor.
- **Cyan / Blue (`10`, `12`, `13`, `11`):** `[DRUMS]` 909 Closed Hats, 909 Offbeat Open Hat, 909 Acid Ride Climax, Peak Clap & Groove Storm.
- **Emerald / Lime / Coral (`55`, `58`, `69`):** `[BUILD / ATMOS / FX]` Riser & Snare Roll, Tuned Vocal Pad, Sub Impact Explosion.

### 6. Interactive HTML Arrangement & Mix Blueprint
Pair every full-track build with a self-contained Dark Studio HTML Arrangement Map (`masterclasses/peak/*_arrangement_map.html`) synced from the live Ableton LOM state (`tracks`, `arrangement_clips`, `cue_points`, EQ high-pass cuts, and dB fader levels) using [`organize_grid_and_export_html.py`](file:///Users/juancruz/ableton-live12-mcp/masterclasses/scripts/organize_grid_and_export_html.py).
