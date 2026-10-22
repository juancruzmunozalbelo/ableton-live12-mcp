# Ableton Live 12 Manual Coverage Matrix

**Ableton Live 12 MCP (`ableton-live12-mcp`)** implements end-to-end programmatic coverage for **all 20 functional domains** of the *Ableton Live 12 Suite Manual*.

This document details the architectural alignment between the 20 manual chapters, the 75 dedicated Model Context Protocol (MCP) tools, the underlying Live Object Model (LOM) C++ Boost.Python classes and methods, and the automated verification suites.

---

## Executive Summary & Tool Distribution

- **Total Manual Chapters Covered**: 20 / 20 (100%)
- **Total Dedicated MCP Tools**: 75
- **Underlying Reverse-Engineered LOM Classes**: 49
- **Core Test Suite**: `tests/test_ableton12_manual_20_chapters.py` (20 chapter test classes)

| # | Manual Chapter Title | Dedicated MCP Tools | LOM Classes & Surface | Test Coverage |
|:---:|:---|:---:|:---|:---|
| **1** | Arrangement View, Time Signatures & Locator Cue Points | 10 | `Song`, `CuePoint`, `Track` | `TestChapter01ArrangementAndCuePoints` |
| **2** | Session View, Scenes & Clip Slots | 8 | `Scene`, `ClipSlot`, `Song` | `TestChapter02SessionViewAndScenes` |
| **3** | Track Hierarchy, Grouping & Performance Impact | 6 | `Song`, `Track` | `TestChapter03TrackHierarchyAndGrouping` |
| **4** | Audio Routing, Sidechain & I/O Channels | 2 | `Track` (I/O routings) | `TestChapter04AudioRoutingAndSidechain` |
| **5** | Take Lanes & Arrangement Comping | 3 | `Track`, `TakeLane` | `TestChapter05TakeLanesAndComping` |
| **6** | Audio Clips, Warping & Sample Properties | 3 | `Clip`, `Sample` | `TestChapter06AudioClipsAndWarping` |
| **7** | Live 12 MIDI Note Editing & Extended Spec | 4 | `Clip`, `MidiNoteSpecification` | `TestChapter07MidiNoteEditingExtended` |
| **8** | Live 12 MIDI Transformations & Algorithmic Tools | 2 | `Clip`, `Song` | `TestChapter08MidiTransformationsAndQuantization` |
| **9** | Clip Envelopes, Automation & Modulation | 1 | `Clip`, `DeviceParameter` | `TestChapter09ClipEnvelopesAndAutomation` |
| **10** | Groove Pool & Swing | 1 | `Song`, `GroovePool`, `Groove`, `Clip` | `TestChapter10GroovePoolAndSwing` |
| **11** | Live 12 Scales & Microtonal Tuning Systems | 3 | `Song`, `TuningSystem` | `TestChapter11ScalesAndMicrotonalTuning` |
| **12** | Browser, Content Categories, Preview & Hotswap | 3 | `Application`, `Browser`, `BrowserItem` | `TestChapter12BrowserPreviewAndHotswap` |
| **13** | Device Chains, Racks & Macro Controls | 7 | `RackDevice`, `Device`, `DeviceParameter` | `TestChapter13DeviceChainsAndRacks` |
| **14** | Drum Racks & Drum Pads | 2 | `RackDevice`, `DrumPad` | `TestChapter14DrumRacksAndDrumPads` |
| **15** | Simpler & Slicing Workflows | 1 | `SimplerDevice`, `Sample` | `TestChapter15SimplerAndSlicing` |
| **16** | Wavetable & Modulation Matrix | 1 | `WavetableDevice` | `TestChapter16WavetableModulationMatrix` |
| **17** | Live 12 Flagship Devices (Meld, Roar, Drift, CC Control) | 4 | `MeldDevice`, `RoarDevice`, `DriftDevice`, `CcControlDevice` | `TestChapter17FlagshipDevicesMeldRoarDriftCC` |
| **18** | Mixer, Sends, Returns & Crossfader | 1 | `MixerDevice`, `Track` | `TestChapter18MixerSendsReturnsCrossfader` |
| **19** | Ableton Link, Tempo Follower & MIDI Capture | 3 | `Song` (Link, Follower, Tap, Nudge, Capture) | `TestChapter19LinkTempoFollowerCaptureMidi` |
| **20** | Views, Native Dialogs, Undo/Redo & LOM Introspection | 12 | `Application.View`, `Song.View`, `Song` (Undo/Redo), `reflection.py` | `TestChapter20ViewsDialogsUndoAndLom` |

---

## Chapter-by-Chapter Technical Breakdown

### Chapter 1: Arrangement View, Time Signature Changes & Locator Cue Points

- **Manual Scope**: Linear arrangement timeline, punch in/out recording, arrangement loop boundaries, tempo automation, signature changes, and locator cue points.
- **Dedicated MCP Tools (10)**:
  - `live12_transport_play`: Starts playback at song position.
  - `live12_transport_stop`: Halts transport.
  - `live12_transport_record`: Toggles session or arrangement record mode.
  - `live12_transport_set_tempo`: Sets song tempo in BPM [20.0..999.0].
  - `live12_transport_set_time_signature`: Sets global time signature numerator and denominator.
  - `live12_transport_set_loop`: Configures arrangement loop active state, start time, and loop length.
  - `live12_transport_set_punch`: Toggles punch-in and punch-out arrangement recording.
  - `live12_transport_set_overdub`: Toggles arrangement overdub and MIDI capture overdubbing.
  - `live12_cue_point_control`: Manages arrangement locators (create, delete, list, jump to cue).
  - `live12_clip_duplicate_to_arrangement`: Duplicates session clips into exact arrangement timeline positions.
- **LOM Classes & Methods**:
  - `Live.Song.Song`: `cue_points`, `set_or_delete_cue()`, `jump_to_next_cue()`, `jump_to_prev_cue()`, `loop`, `loop_start`, `loop_length`, `punch_in`, `punch_out`, `record_mode`, `tempo`, `signature_numerator`, `signature_denominator`.
  - `Live.Song.CuePoint`: `name`, `time`, `jump()`.
  - `Live.Track.Track`: `duplicate_clip_to_arrangement(clip, time)`.
- **Test Verification**: `TestChapter01ArrangementAndCuePoints` in `tests/test_ableton12_manual_20_chapters.py`.

---

### Chapter 2: Session View, Scenes & Clip Slots

- **Manual Scope**: Non-linear clip triggering, scene launching, tempo-assigned scenes, time-signature-assigned scenes, and clip slot states.
- **Dedicated MCP Tools (8)**:
  - `live12_scene_create`: Inserts a new scene at index.
  - `live12_scene_fire`: Fires all clip slots in a scene.
  - `live12_scene_set_properties`: Configures scene name, color, scene-triggered tempo, and scene-triggered time signature.
  - `live12_clip_create`: Creates a blank MIDI clip on a designated slot.
  - `live12_clip_delete`: Deletes a clip from a slot.
  - `live12_clip_fire`: Triggers playback of a specific session clip.
  - `live12_clip_stop`: Stops clip playback on a designated track.
  - `live12_clip_duplicate_to_arrangement`: Bridges session clips to the arrangement timeline.
- **LOM Classes & Methods**:
  - `Live.Scene.Scene`: `fire()`, `name`, `color`, `tempo`, `tempo_enabled`, `time_signature_numerator`, `time_signature_denominator`, `time_signature_enabled`.
  - `Live.ClipSlot.ClipSlot`: `fire()`, `stop()`, `has_clip`, `clip`, `is_playing`, `is_triggered`.
  - `Live.Song.Song`: `create_scene(index)`, `duplicate_scene(index)`, `scenes`.
- **Test Verification**: `TestChapter02SessionViewAndScenes` in `tests/test_ableton12_manual_20_chapters.py`.

---

### Chapter 3: Track Hierarchy, Grouping, Folding & Performance Impact

- **Manual Scope**: Audio and MIDI tracks, return tracks, master track, group tracks, track folding, muting, soloing, and CPU performance management.
- **Dedicated MCP Tools (6)**:
  - `live12_track_create`: Creates MIDI, Audio, or Return tracks.
  - `live12_track_delete`: Deletes a track by index.
  - `live12_track_duplicate`: Clones a track with all devices and clips.
  - `live12_track_set_properties`: Sets track name, color, mute, solo, and arm.
  - `live12_track_group`: Groups multiple tracks into a composite group track.
  - `live12_track_ungroup`: Dissolves a track group back into top-level tracks.
- **LOM Classes & Methods**:
  - `Live.Song.Song`: `create_midi_track()`, `create_audio_track()`, `create_return_track()`, `delete_track()`, `duplicate_track()`, `tracks`, `return_tracks`, `master_track`.
  - `Live.Track.Track`: `name`, `color`, `mute`, `solo`, `arm`, `is_foldable`, `fold_state`, `group_track`, `is_grouped`.
- **Test Verification**: `TestChapter03TrackHierarchyAndGrouping` in `tests/test_ableton12_manual_20_chapters.py`.

---

### Chapter 4: Audio Routing, Sidechain & I/O Channels

- **Manual Scope**: External audio inputs/outputs, track-to-track audio routing, sidechain routing, MIDI sub-channel routing, and monitoring states (In, Auto, Off).
- **Dedicated MCP Tools (2)**:
  - `live12_routing_get`: Inspects active routing configurations and queries available input/output types and channels.
  - `live12_routing_set`: Sets input/output routing type, channel, and monitoring state.
- **LOM Classes & Methods**:
  - `Live.Track.Track`: `input_routing_type`, `input_routing_channel`, `output_routing_type`, `output_routing_channel`, `available_input_routing_types`, `available_input_routing_channels`, `available_output_routing_types`, `available_output_routing_channels`, `current_monitoring_state`.
- **Test Verification**: `TestChapter04AudioRoutingAndSidechain` in `tests/test_ableton12_manual_20_chapters.py`.

---

### Chapter 5: Take Lanes & Arrangement Comping

- **Manual Scope**: Audio and MIDI take lanes, recording multiple passes, comping best regions into the master lane, and auditioning take lanes.
- **Dedicated MCP Tools (3)**:
  - `live12_take_lane_create`: Creates a new take lane on an arrangement track.
  - `live12_take_lane_list`: Queries all take lanes, clip presence, and custom metadata.
  - `live12_take_lane_comp_region`: Comps a beat time window from a take lane into the track's main arrangement clip.
- **LOM Classes & Methods**:
  - `Live.Track.Track`: `take_lanes`, `create_take_lane()`.
  - `Live.TakeLane.TakeLane`: `name`, `comp_region()`, `get_data()`, `set_data()`.
- **Test Verification**: `TestChapter05TakeLanesAndComping` in `tests/test_ableton12_manual_20_chapters.py`.

---

### Chapter 6: Audio Clips, Warping, Warp Markers & Sample Properties

- **Manual Scope**: Audio sample properties, time-stretching, warping modes (Beats, Tones, Texture, Re-Pitch, Complex, Complex Pro), and warp markers.
- **Dedicated MCP Tools (3)**:
  - `live12_audio_clip_set_warp`: Enables/disables warping, sets warp mode, pitch transposition, and clip gain.
  - `live12_audio_clip_add_warp_marker`: Injects sample-to-beat warp markers for surgical timing alignment.
  - `live12_clip_set_properties`: Configures clip loop boundaries, start/end markers, and clip names.
- **LOM Classes & Methods**:
  - `Live.Clip.Clip`: `warping`, `warp_mode`, `warp_markers`, `sample`, `pitch_coarse`, `pitch_fine`, `gain`, `gain_display_degree`, `file_path`, `sample_length`.
- **Test Verification**: `TestChapter06AudioClipsAndWarping` in `tests/test_ableton12_manual_20_chapters.py`.

---

### Chapter 7: Live 12 MIDI Note Editing & Extended Specification

- **Manual Scope**: MIDI clip note generation, probability (0.0–1.0), velocity deviation (± spread), release velocity, note mute, and note deletion.
- **Dedicated MCP Tools (4)**:
  - `live12_clip_add_notes`: Injects MIDI notes with Live 12 extended probability and velocity deviation parameters.
  - `live12_clip_get_notes`: Reads all note events in a clip with extended parameters.
  - `live12_clip_modify_notes`: Updates existing notes by note ID or pitch/time coordinate.
  - `live12_clip_remove_notes`: Removes notes by exact ID or time/pitch window.
- **LOM Classes & Methods**:
  - `Live.Clip.Clip`: `add_new_notes()`, `get_notes_extended()`, `apply_note_modifications()`, `remove_notes_extended()`, `remove_notes_by_id()`, `duplicate_notes_by_id()`.
  - `Live.Clip.MidiNoteSpecification`: `pitch`, `start_time`, `duration`, `velocity`, `velocity_deviation`, `probability`, `release_velocity`, `mute`.
- **Test Verification**: `TestChapter07MidiNoteEditingExtended` in `tests/test_ableton12_manual_20_chapters.py`.

---

### Chapter 8: Live 12 MIDI Transformations, Quantization & Pitch/Scale Tools

- **Manual Scope**: Algorithmic MIDI tools, Euclidean rhythms, humanization jitter, velocity ramps, and scale pitch quantization.
- **Dedicated MCP Tools (2)**:
  - `live12_clip_quantize`: Quantizes note start times and lengths to musical grid increments (1/4, 1/8, 1/16, 1/32).
  - `live12_clip_transform_midi`: Executes algorithmic transformations: Bjorklund Euclidean distribution, humanize timing/velocity jitter, linear velocity ramps, and fit-to-scale snapping.
- **LOM Classes & Methods**:
  - `Live.Clip.Clip`: `quantize()`, `quantize_pitch()`, algorithmic transformation pipeline via `get_notes_extended` and `apply_note_modifications`.
  - `Live.Song.Song`: `scale_information`.
- **Test Verification**: `TestChapter08MidiTransformationsAndQuantization` in `tests/test_ableton12_manual_20_chapters.py`.

---

### Chapter 9: Clip Envelopes, Automation & Modulation

- **Manual Scope**: Parameter automation within clips, breakpoint envelope creation, clearing parameter automation, and re-enabling manual automation override.
- **Dedicated MCP Tools (1)**:
  - `live12_clip_envelope_control`: Sets breakpoint values, inspects envelope existence, clears individual or all envelopes, and re-enables automation.
- **LOM Classes & Methods**:
  - `Live.Clip.Clip`: `clear_envelope()`, `clear_all_envelopes()`, `has_envelopes`.
  - `Live.DeviceParameter.DeviceParameter`: `value`, `automation_state`, `re_enable_automation()`.
- **Test Verification**: `TestChapter09ClipEnvelopesAndAutomation` in `tests/test_ableton12_manual_20_chapters.py`.

---

### Chapter 10: Groove Pool & Swing

- **Manual Scope**: Groove template management, global song groove intensity, assigning swing/grooves to audio and MIDI clips, and groove timing extraction.
- **Dedicated MCP Tools (1)**:
  - `live12_groove_pool_control`: Queries groove pool templates, sets global song groove amount, assigns grooves to clips, and detaches grooves.
- **LOM Classes & Methods**:
  - `Live.Song.Song`: `groove_pool`, `groove_amount`.
  - `Live.GroovePool.GroovePool`: `grooves`.
  - `Live.Groove.Groove`: `name`, `base`, `timing_amount`, `velocity_amount`, `quantization_amount`, `random_amount`.
  - `Live.Clip.Clip`: `groove`, `has_groove`.
- **Test Verification**: `TestChapter10GroovePoolAndSwing` in `tests/test_ableton12_manual_20_chapters.py`.

---

### Chapter 11: Live 12 Scales & Microtonal Tuning Systems

- **Manual Scope**: Global song scale modes (35+ scales), root note assignment, microtonal tuning systems (`.ascl`), and microtonal reference frequencies.
- **Dedicated MCP Tools (3)**:
  - `live12_song_set_scale`: Sets global musical scale (e.g. Minor, Major, Dorian, Phrygian) and root note (0–11).
  - `live12_song_set_tuning_system`: Loads microtonal tuning files (`.ascl`) with pitch cent offsets.
  - `live12_song_get_state`: Inspects complete musical context (tempo, scale, tuning, signature).
- **LOM Classes & Methods**:
  - `Live.Song.Song`: `scale_name`, `root_note`, `scale_mode`, `tuning_system`.
  - `Live.TuningSystem.TuningSystem`: `name`, `scale_degrees`, `reference_pitch`, `cent_offsets`.
- **Test Verification**: `TestChapter11ScalesAndMicrotonalTuning` in `tests/test_ableton12_manual_20_chapters.py`.

---

### Chapter 12: Browser, Content Categories, Preview & Hotswap

- **Manual Scope**: Searching core library, packs, and user presets, audio preview auditioning, loading devices/samples into tracks or drum pads, and hotswap targets.
- **Dedicated MCP Tools (3)**:
  - `live12_browser_search`: Searches browser categories by query and category filter.
  - `live12_browser_load_item`: Instantiates browser items onto tracks or drum pads via URI.
  - `live12_browser_preview`: Auditions items via audio preview engine and queries active hotswap state.
- **LOM Classes & Methods**:
  - `Live.Application.Application`: `browser`.
  - `Live.Browser.Browser`: `preview_item()`, `stop_preview()`, `relation_to_hotswap_target()`, `hotswap_target`, `loads_into_drum_rack`.
- **Test Verification**: `TestChapter12BrowserPreviewAndHotswap` in `tests/test_ableton12_manual_20_chapters.py`.

---

### Chapter 13: Device Chains, Racks, Macro Controls & Macro Variations

- **Manual Scope**: Instrument and effect racks, parallel chains, dynamic macro knob counts (1–16), macro snapshots/variations, and parameter randomizations.
- **Dedicated MCP Tools (7)**:
  - `live12_device_list`: Enumerates all devices on a track.
  - `live12_device_get_parameters`: Inspects device parameters, names, ranges, and current values.
  - `live12_device_set_parameter`: Adjusts parameter value by name or index.
  - `live12_device_toggle`: Enables or disables a device bypass state.
  - `live12_rack_macro_control`: Sets macro knob values (macros 0–15).
  - `live12_rack_variation_control`: Stores, recalls, or deletes macro variation snapshots.
  - `live12_rack_macro_config`: Configures visible macro counts (1–16), increments/decrements macros, and randomizes macro values.
- **LOM Classes & Methods**:
  - `Live.RackDevice.RackDevice`: `macros`, `visible_macro_count`, `add_macro()`, `remove_macro()`, `randomize_macros()`, `variations`, `store_variation()`, `recall_variation()`, `chains`, `return_chains`.
  - `Live.Device.Device`: `name`, `class_name`, `type`, `is_active`, `parameters`.
- **Test Verification**: `TestChapter13DeviceChainsAndRacks` in `tests/test_ableton12_manual_20_chapters.py`.

---

### Chapter 14: Drum Racks & Drum Pads

- **Manual Scope**: 128-pad drum racks, pad sample loading, pad muting/soloing, cloning pads to new notes, and pad chain cleanup.
- **Dedicated MCP Tools (2)**:
  - `live12_drum_pad_control`: Queries pad status, sets pad mute/solo, clones pad chains (`copy_pad`), and deletes chains.
  - `live12_browser_load_item`: Directly populates drum pads via `drum_pad_index`.
- **LOM Classes & Methods**:
  - `Live.RackDevice.RackDevice`: `drum_pads`, `copy_pad(source_note, target_note)`.
  - `Live.DrumPad.DrumPad`: `name`, `note`, `mute`, `solo`, `chains`, `delete_all_chains()`.
- **Test Verification**: `TestChapter14DrumRacksAndDrumPads` in `tests/test_ableton12_manual_20_chapters.py`.

---

### Chapter 15: Simpler & Slicing Workflows

- **Manual Scope**: Live's integrated sampling instrument, Classic/One-Shot/Slicing modes, slice sensitivity, and slice-to-Drum-Rack conversion.
- **Dedicated MCP Tools (1)**:
  - `live12_simpler_control`: Converts Simpler slice points to Drum Rack pads and manages sample replacement.
- **LOM Classes & Methods**:
  - `Live.SimplerDevice.SimplerDevice`: `playback_mode`, `sample`, `slicing_playback_mode`, `slice_to_drum_rack()`, `multi_sample_mode`.
- **Test Verification**: `TestChapter15SimplerAndSlicing` in `tests/test_ableton12_manual_20_chapters.py`.

---

### Chapter 16: Wavetable & Modulation Matrix

- **Manual Scope**: Dual morphing wavetable synth, 2D modulation matrix, LFOs, envelopes, and modulation depth assignment.
- **Dedicated MCP Tools (1)**:
  - `live12_wavetable_modulation_matrix`: Sets source-target routing, modulation depths, queries active routings, and clears matrix connections.
- **LOM Classes & Methods**:
  - `Live.WavetableDevice.WavetableDevice`: `modulation_matrix`, `filter_routing`, `oscillator_1`, `oscillator_2`, `lfo_1`, `lfo_2`.
- **Test Verification**: `TestChapter16WavetableModulationMatrix` in `tests/test_ableton12_manual_20_chapters.py`.

---

### Chapter 17: Live 12 Flagship Devices (Meld, Roar, Drift, CC Control)

- **Manual Scope**: Live 12's signature instruments and effects: Meld bi-timbral macro synth, Roar multi-stage saturator, Drift subtractive synth, and CC Control utility device.
- **Dedicated MCP Tools (4)**:
  - `live12_meld_control`: Configures dual macro-oscillator engines (A & B) and scale resonators.
  - `live12_roar_control`: Configures multi-stage saturation routing (Single, Serial, Parallel, Multi-band, Mid/Side, Feedback) and drive.
  - `live12_drift_control`: Adjusts analog oscillator drift, filter character, and stereo width.
  - `live12_cc_control`: Maps continuous controller numbers and sends MIDI CC values [0..127].
- **LOM Classes & Methods**:
  - `Live.MeldDevice.MeldDevice`, `Live.RoarDevice.RoarDevice`, `Live.DriftDevice.DriftDevice`, `Live.CcControlDevice.CcControlDevice`.
- **Test Verification**: `TestChapter17FlagshipDevicesMeldRoarDriftCC` in `tests/test_ableton12_manual_20_chapters.py`.

---

### Chapter 18: Mixer, Sends, Returns, Crossfader & Cue Volume

- **Manual Scope**: Channel strip mixing, auxiliary send levels, stereo panning, A/B crossfader assignments, crossfader curve, and cue monitoring volume.
- **Dedicated MCP Tools (1)**:
  - `live12_mixer_set`: Configures track volume, stereo pan, auxiliary send levels, and crossfader assignment.
- **LOM Classes & Methods**:
  - `Live.MixerDevice.MixerDevice`: `volume`, `panning`, `sends`, `crossfader`, `crossfade_assign`, `cue_volume`, `track_activator`.
- **Test Verification**: `TestChapter18MixerSendsReturnsCrossfader` in `tests/test_ableton12_manual_20_chapters.py`.

---

### Chapter 19: Ableton Link, Tempo Follower, Count-In & Capture MIDI

- **Manual Scope**: Network tempo synchronization via Ableton Link, live tempo following, metronome count-in, tap tempo, tempo nudging, and retrospective MIDI capture.
- **Dedicated MCP Tools (3)**:
  - `live12_tempo_sync_control`: Controls Ableton Link toggle, tempo follower toggle, tap tempo execution, and tempo nudging up/down.
  - `live12_song_capture_midi`: Retrospectively captures recently played MIDI notes into new clips without pre-recording.
  - `live12_transport_set_metronome`: Enables/disables metronome click and configures count-in duration.
- **LOM Classes & Methods**:
  - `Live.Song.Song`: `is_ableton_link_enabled`, `tempo_follower_enabled`, `tap_tempo()`, `nudge_up()`, `nudge_down()`, `capture_midi()`, `metronome`, `count_in_duration`.
- **Test Verification**: `TestChapter19LinkTempoFollowerCaptureMidi` in `tests/test_ableton12_manual_20_chapters.py`.

---

### Chapter 20: Application Views, Native Dialogs, Undo/Redo & OS Project/Export Actions

- **Manual Scope**: GUI view switching, clip/device detail navigation, native Cocoa save/export dialogs, undo/redo transactions, project persistence, and full dynamic LOM inspection.
- **Dedicated MCP Tools (12)**:
  - `live12_view_switch`: Toggles between Session View and Arrangement View, opens Clip or Device detail views.
  - `live12_view_select`: Programmatically selects tracks, scenes, clip slots, or devices in the GUI.
  - `live12_dialog_inspect`: Checks status of open macOS dialogs (e.g. Save, Missing Files).
  - `live12_dialog_press`: Interacts with native dialog buttons ("Save", "Don't Save", "Cancel").
  - `live12_undo_redo`: Executes undo/redo operations and demarcates transactional undo steps.
  - `live12_os_save_set`: Saves the current Live set (`.als`) to disk.
  - `live12_os_open_set`: Loads an `.als` project file via AppleScript System Events.
  - `live12_os_export_audio`: Triggers audio bounce export dialog and executes render.
  - `live12_lom_inspect`: Introspects properties, methods, and child objects of any Live Object Model path.
  - `live12_lom_get`: Dynamically retrieves property values from any LOM object.
  - `live12_lom_set`: Dynamically sets property values on any LOM object.
  - `live12_lom_call`: Dynamically invokes arbitrary Boost.Python methods on any LOM object.
- **LOM Classes & Methods**:
  - `Live.Application.Application.View`, `Live.Song.Song.View`.
  - `Live.Song.Song`: `undo()`, `redo()`, `can_undo`, `can_redo`, `begin_undo_step()`, `end_undo_step()`.
  - Native Cocoa dialog bridge (`dialogs.py`).
  - Dynamic reflection engine (`reflection.py`).
- **Test Verification**: `TestChapter20ViewsDialogsUndoAndLom` in `tests/test_ableton12_manual_20_chapters.py`.
