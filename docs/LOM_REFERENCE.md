# Ableton Live 12.4.6 Suite: Live Object Model (LOM) Reference Guide

> **Authoritative Reference Documentation**  
> **Application:** Ableton Live 12 Suite (12.4.6, build `2026-09-10_0de5c8fa9a`)  
> **Runtime:** Embedded CPython 3.11.6 / Boost.Python Bindings  
> **Mach-O Binary SHA-256:** `5e8832e06fe92d42ceebac4fad153e44422c90923f426dcb05c760c6d80b3949`  
> **Extracted:** `2026-10-21T23:43:37.849138+00:00`  

---

## 1. Architecture & Execution Context

The Ableton Live Object Model (LOM) exposes the C++ real-time audio and sequencing engine to Python via Boost.Python. Live statically embeds CPython 3.11.6 in the main application executable.

```
+----------------------------------------------------------------+
|                External Client (MCP / Remote RPC)              |
+-------------------------------+--------------------------------+
                                | Loopback TCP (127.0.0.1:11246)
                                v
+----------------------------------------------------------------+
|           Live 12 Remote Script (CPython 3.11 Runtime)          |
|  - Socket Listener Thread -> Thread-Safe Request Queue         |
|  - Live.Base.Timer (5ms main-thread scheduler)                 |
+-------------------------------+--------------------------------+
                                | In-Process Main-Thread Calls
                                v
+----------------------------------------------------------------+
|             Ableton Live C++ Engine (AppLive / Boost.Python)   |
+----------------------------------------------------------------+
```

### The Main Thread Invariant
Directly calling mutating LOM methods (`create_midi_track`, `add_new_notes`, parameter value updates) from a background thread causes race conditions or fatal crashes. **All LOM modifications must be dispatched on Ableton's main thread** using `Live.Base.Timer` or `update_display()` callbacks.

### Pointer Validity Safety (`liveobj_valid`)
When objects are deleted by the user or through undo operations, accessing attributes on a dangling pointer raises `RuntimeError: Underlying C/C++ object has been deleted`. Always guard object references before access:
```python
def is_valid_live_object(obj):
    if obj is None:
        return False
    try:
        return bool(obj != None)
    except RuntimeError:
        return False
```

---

## 2. Live Object Model Hierarchy

```
Live.Application (Singleton: Live.Application.get_application())
 ├── View (Live.Application.View)
 ├── Browser (Live.Browser)
 └── Song (Live.Song - Live.Application.get_application().get_document())
      ├── View (Live.Song.View)
      ├── TuningSystem (Live.TuningSystem)
      ├── GroovePool (Live.GroovePool)
      ├── CuePoints (tuple of Live.Song.CuePoint)
      ├── Scenes (tuple of Live.Scene)
      └── Tracks (tuple of Live.Track)
           ├── View (Live.Track.View)
           ├── MixerDevice (Live.MixerDevice)
           ├── TakeLanes (tuple of Live.TakeLane) [Live 12]
           │    └── Clips (tuple of Live.Clip)
           ├── ClipSlots (tuple of Live.ClipSlot)
           │    └── Clip (Live.Clip)
           │         ├── MidiNotes (tuple of Live.Clip.MidiNote) [Live 12]
           │         ├── WarpMarkers (tuple of WarpMarker)
           │         └── Envelopes (tuple of AutomationEnvelope)
           └── Devices (tuple of Live.Device)
                ├── Parameters (tuple of Live.DeviceParameter)
                ├── Chains (tuple of Live.Chain) [RackDevice]
                ├── DrumPads (tuple of Live.DrumPad) [DrumRack]
                └── ModulationMatrix [WavetableDevice]
```

---

## 3. Boost.Python C++ Type Registrations (184 Types)

The native Mach-O binary exports exactly 184 registered types via `boost::python::converter::detail::registered_base<T>::converters`:

### Handles (41)
- `TCcControlDevicePyHandle`
- `TChainPyHandle`
- `TCompressorDevicePyHandle`
- `TDriftDevicePyHandle`
- `TDrumCellDevicePyHandle`
- `TDrumChainPyHandle`
- `TEq8DevicePyHandle`
- `THybridReverbDevicePyHandle`
- `TLooperDevicePyHandle`
- `TMaxDevicePyHandle`
- `TMeldDevicePyHandle`
- `TPluginDevicePyHandle`
- `TPyHandle<AAbstractGroove>`
- `TPyHandle<AAutomation>`
- `TPyHandle<ABranchMixerDevice>`
- `TPyHandle<ABrowserDelegate>`
- `TPyHandle<AClip>`
- `TPyHandle<ACuePoint>`
- `TPyHandle<ADevice>`
- `TPyHandle<ADrumGroupDevicePad>`
- `TPyHandle<AGroovePool>`
- `TPyHandle<AGroupAndClipSlotBase>`
- `TPyHandle<AMultiSamplePart>`
- `TPyHandle<AMxDManagerImpl>`
- `TPyHandle<AMxDRoutable>`
- `TPyHandle<APythonListWrapper>`
- `TPyHandle<ARemoteable>`
- `TPyHandle<AScene>`
- `TPyHandle<ASong>`
- `TPyHandle<ASongApp>`
- `TPyHandle<ATakeLane>`
- `TPyHandle<ATimeableValue>`
- `TPyHandle<ATrackDevice>`
- `TPyHandle<ATuningSystem>`
- `TRackDevicePyHandle`
- `TRoarDevicePyHandle`
- `TShifterDevicePyHandle`
- `TSimplerDevicePyHandle`
- `TTrackPyHandle`
- `TTransmuteDevicePyHandle`
- `TWavetableDevicePyHandle`

### View Data (8)
- `TEq8DevicePyViewData`
- `TPyViewData<AClip>`
- `TPyViewData<ADevice>`
- `TPyViewData<ASong>`
- `TPyViewData<ASongApp>`
- `TPyViewData<ATrack>`
- `TRackDevicePyViewData`
- `TSimplerDevicePyViewData`

### Proxies (4)
- `TFunctionProxyPtr<AFullVelocityModule>`
- `TFunctionProxyPtr<ANoteRepeatModule>`
- `TFunctionProxyPtr<ATimeToMidiModule>`
- `TFunctionProxyPtr<AVelocityLevelsModule>`

### Enums (63)
- `AInstallationConfigData::TVariant`
- `ATimebombAuthorizationPolicy::TAuthorizationUpdateContext`
- `IBrowserApiContentQuery::THotSwapFilterType`
- `NApiHelpers::TEnvelopeEvent`
- `NApiHelpers::TEnvelopeEventControlCoefficients`
- `NApiHelpers::TPitchClassAndOctave`
- `NApiHelpers::TReferencePitch`
- `NApiHelpers::TWarpMarker`
- `NApplicationViewTypes::TViewNavDirection`
- `NAudioToMidi::TAlgorithmType`
- `NCapture::TDestination`
- `NClipApi::TNoteInfo`
- `NEnabled::TState`
- `NEq8Types::TEditMode`
- `NEq8Types::TMode`
- `NGrooveTypes::TGridTypes`
- `NMoveDisplayCpp::TAlignmentHorizontal`
- `NMoveDisplayCpp::TAlignmentVertical`
- `NPythonApplication::TMessageButtons`
- `NPythonApplication::TUnavailableFeature`
- `NPythonBrowser::TPythonBrowserItem`
- `NPythonBrowser::TPythonBrowserItem::TPythonBrowserItemIterator`
- `NPythonClip::TNoteSpecification`
- `NPythonMidiMap::TCCFeedbackRule`
- `NPythonMidiMap::TNoteFeedbackRule`
- `NPythonMidiMap::TPitchBendFeedbackRule`
- `NPythonMixerDeviceCpp::TCrossfadeAssignments`
- `NPythonTrackCpp::TMonitoringStates`
- `NQuantizationTypes::TBeatGridQuantization`
- `NQuantizationTypes::TClipLaunchQuantization`
- `NQuantizationTypes::TLaunchModes`
- `NQuantizationTypes::TLaunchQuantization`
- `NQuantizationTypes::TMidiRecordingQuantization`
- `NRemoteMapperTypes::TControllerMapMode`
- `NRouting::TRoutingTargetChannelLayout`
- `NRoutingApi::TRoutingChannel`
- `NRoutingApi::TRoutingType`
- `NRoutingApi::TRoutingTypeCategory`
- `NSceneOperations::TCaptureMode`
- `NSessionRecordingState::TState`
- `NSimplerTypes::TPlaybackMode`
- `NSimplerTypes::TSlicingBeatGrid`
- `NSimplerTypes::TSlicingPlaybackMode`
- `NSimplerTypes::TSlicingStyle`
- `NSongApi::TBeatTime`
- `NSongApi::TSmptTime`
- `NTimeConversionTypes::TTimeFormat`
- `NTimeableTypes::TLedState`
- `NTrackApi::TDeviceInsertMode`
- `NWarperTypes::TWarpMode`
- `OWarperBeats::TTransientLoopMode`
- `TClipSlotPlayingState`
- `TPanMode`
- `TPush2Visualisation::TVisualisationColor`
- `TPushMessageDescription::TType`
- `ableton::devices::wavetable::FilterRouting`
- `ableton::devices::wavetable::ModulationSource`
- `ableton::devices::wavetable::OscEffectMode`
- `ableton::devices::wavetable::UnisonMode`
- `ableton::devices::wavetable::model::Wavetable::VoiceCount`
- `ableton::devices::wavetable::model::Wavetable::Voicing`
- `ableton::live_library::DeviceType`
- `ableton::live_library::Relation`

### Value Types (3)
- `PythonTimer`
- `TString`
- `TText`

### Primitives (10)
- `bool`
- `char`
- `double`
- `float`
- `int`
- `long`
- `signed char`
- `unsigned char`
- `unsigned int`
- `unsigned long long`

### Weak Ptrs (32)
- `TWeakPtr<AProgressDialog>`
- `TWeakPtr<APythonControlSurfaceProxy>`
- `TWeakPtr<APythonPreferenceEntry>`
- `TWeakPtr<AStartupDialog>`
- `TWeakPtr<ATimeableValue>`
- `TWeakPtr<IPythonRealTimeMapper>`
- `TWeakPtr<LPythonRemote>`
- `TWeakPtr<TCcControlDevicePyHandle>`
- `TWeakPtr<TChainPyHandle>`
- `TWeakPtr<TCompressorDevicePyHandle>`
- `TWeakPtr<TDriftDevicePyHandle>`
- `TWeakPtr<TDrumCellDevicePyHandle>`
- `TWeakPtr<TDrumChainPyHandle>`
- `TWeakPtr<TEq8DevicePyHandle>`
- `TWeakPtr<TEq8DevicePyViewData>`
- `TWeakPtr<THybridReverbDevicePyHandle>`
- `TWeakPtr<TLooperDevicePyHandle>`
- `TWeakPtr<TMaxDevicePyHandle>`
- `TWeakPtr<TMeldDevicePyHandle>`
- `TWeakPtr<TMidiRemoteScript>`
- `TWeakPtr<TPluginDevicePyHandle>`
- `TWeakPtr<TPush2Visualisation>`
- `TWeakPtr<TPyHandleBase>`
- `TWeakPtr<TRackDevicePyHandle>`
- `TWeakPtr<TRackDevicePyViewData>`
- `TWeakPtr<TRoarDevicePyHandle>`
- `TWeakPtr<TShifterDevicePyHandle>`
- `TWeakPtr<TSimplerDevicePyHandle>`
- `TWeakPtr<TSimplerDevicePyViewData>`
- `TWeakPtr<TTrackPyHandle>`
- `TWeakPtr<TTransmuteDevicePyHandle>`
- `TWeakPtr<TWavetableDevicePyHandle>`

### Other (23)
- `AAbstractGroove`
- `AFullVelocityModule`
- `ANoteRepeatModule`
- `AProgressDialog`
- `APythonControlSurfaceProxy`
- `APythonLicensingBridge`
- `APythonPreferenceEntry`
- `AStartupDialog`
- `ATimeToMidiModule`
- `AVelocityLevelsModule`
- `IPythonRealTimeMapper`
- `LPythonRemote`
- `NMoveDisplayCpp::MoveDisplay`
- `TArray<unsigned char>`
- `TControlDescription`
- `TMidiRemoteScript`
- `TProcessObserver::State`
- `TPush2MidiRemoteScript`
- `TPush2Visualisation`
- `TPushMidiRemoteScript`
- `TPyHandleBase`
- `TUnlockStatus`
- `boost::python::api::object`

---

## 4. Core LOM Class Reference

### `Live.Application.Application`
- **C++ Handle:** `TPyHandle<ASongApp>`
- **Canonical Parent:** `None`
- **Docstring:** _This class represents the Live application._

Top-level host application interface providing access to the open document, browser, view system, licensing, CPU meters, and native modal dialog automation.

#### Properties

| Property | Type | Access | Listener | Description |
|---|---|---|---|---|
| `open_dialog_count` | `int` | read-only | Yes | The number of open dialogs in Live. 0 if no dialog is open. |
| `current_dialog_message` | `str` | read-only | Yes | Text of the last dialog that appeared; Empty if all dialogs just disappeared. |
| `current_dialog_button_count` | `int` | read-only | Yes | Number of interactive buttons available on the currently active dialog. |
| `average_process_usage` | `float` | read-only | Yes | Reports Live average CPU processing load (0.0 to 1.0+). |
| `peak_process_usage` | `float` | read-only | Yes | Reports Live peak CPU load. |
| `control_surfaces` | `tuple[ControlSurface | None]` | read-only | No | Const access to a list of control surfaces configured in Preferences. |
| `unavailable_features` | `tuple[UnavailableFeature]` | read-only | No | List of features unavailable due to license tier (Intro/Standard/Suite). |
| `view` | `Live.Application.Application.View` | read-only | No | Returns the application's view component. |
| `browser` | `Live.Browser.Browser` | read-only | No | Returns an interface to the Live asset database browser. |

#### Methods

##### `get_document() -> Live.Song.Song`
Returns the active Live Set document instance.

##### `get_version_string() -> str`
Returns the full version string of Live (e.g. '12.4.6').

##### `get_major_version() -> int`
Returns integer major version (12).

##### `get_minor_version() -> int`
Returns integer minor version (4).

##### `get_bugfix_version() -> int`
Returns integer bugfix version (6).

##### `get_variant() -> str`
Returns Live edition variant ('Suite', 'Standard', 'Intro', 'Lite', 'Trial', 'Beta').

##### `has_option(entry: str) -> bool`
Returns True if entry exists in Options.txt, False otherwise.

##### `press_current_dialog_button(button_index: int) -> None`
Presses a button, by index, on the current open modal dialog.

##### `push_dialog_type(dialog_type: int) -> None`
Pushes dialog type specification.

---

### `Live.Application.Application.View`
- **C++ Handle:** `TPyViewData<ASongApp>`
- **Canonical Parent:** `Live.Application.Application`
- **Docstring:** _This class represents the view aspects of the Live application._

Application view manager for switching main views, toggling browser/hot swap, and inspecting view component visibility.

#### Properties

| Property | Type | Access | Listener | Description |
|---|---|---|---|---|
| `available_main_views` | `tuple[str]` | read-only | No | List of available main view identifiers: ['Session', 'Arranger']. |
| `focused_document_view` | `str` | read-only | Yes | Identifier of the currently focused document view ('Session' or 'Arranger'). |
| `browse_mode` | `bool` | read-only | Yes | True if HotSwap browse mode is active. |

#### Methods

##### `focus_view(identifier: str) -> None`
Focuses and brings view to front ('Session', 'Arranger', 'Detail', 'Detail/Clip', 'Detail/DeviceChain', 'Browser').

##### `show_view(identifier: str) -> None`
Reveals specified view window/component.

##### `hide_view(identifier: str) -> None`
Hides or collapses specified view component.

##### `scroll_view(direction: NavDirection) -> None`
Scrolls focused view (left, right, up, down).

##### `zoom_view(direction: NavDirection) -> None`
Zooms focused view (in, out).

##### `toggle_browse() -> None`
Reveals device chain and toggles hot-swap mode for selected device.

##### `is_view_visible(identifier: str, main_window_only: bool = True) -> bool`
Returns True if specified view identifier is currently visible.

---

### `Live.Song.Song`
- **C++ Handle:** `TPyHandle<ASong>`
- **Canonical Parent:** `Live.Application.Application`
- **Docstring:** _This class represents a Live set._

Central project container governing playback transport, tracks, scenes, arrangement loop, tempo, time signature, project scale, microtonal tuning, and MIDI capture.

#### Properties

| Property | Type | Access | Listener | Description |
|---|---|---|---|---|
| `is_playing` | `bool` | read/write | Yes | Playback state. |
| `tempo` | `float` | read/write | Yes | Song tempo in BPM [20.0, 999.0]. |
| `signature_numerator` | `int` | read/write | Yes | Time signature numerator. |
| `signature_denominator` | `int` | read/write | Yes | Time signature denominator. |
| `current_song_time` | `float` | read/write | Yes | Playhead position in beats. |
| `loop` | `bool` | read/write | Yes | Arrangement loop active state. |
| `loop_start` | `float` | read/write | Yes | Arrangement loop start in beats. |
| `loop_length` | `float` | read/write | Yes | Arrangement loop length in beats. |
| `punch_in` | `bool` | read/write | Yes | Punch-in recording flag at loop start. |
| `punch_out` | `bool` | read/write | Yes | Punch-out recording flag at loop end. |
| `record_mode` | `bool` | read/write | Yes | Global arrangement record status. |
| `session_record` | `bool` | read/write | Yes | Session recording status. |
| `arrangement_overdub` | `bool` | read/write | Yes | Arrangement MIDI overdub status. |
| `back_to_arranger` | `bool` | read/write | Yes | Return playback from Session clips to Arrangement. |
| `scale_mode` | `bool` | read/write | Yes | Enables/disables Live 12 project scale mode. |
| `root_note` | `int` | read/write | Yes | Project root pitch key (0=C, 11=B). |
| `scale_name` | `str` | read/write | Yes | Active scale name (e.g. 'Major', 'Minor', 'Dorian'). |
| `scale_information` | `tuple[int]` | read-only | Yes | Semitone interval offsets from root note. |
| `tuning_system` | `Live.TuningSystem.TuningSystem | None` | read-only | Yes | Currently applied microtonal tuning system. |
| `can_capture_midi` | `bool` | read-only | Yes | True if unrecorded MIDI is in buffer. |
| `can_undo` | `bool` | read-only | Yes | True if undo action is available. |
| `can_redo` | `bool` | read-only | Yes | True if redo action is available. |
| `tracks` | `tuple[Live.Track.Track]` | read-only | Yes | List of audio and MIDI tracks. |
| `visible_tracks` | `tuple[Live.Track.Track]` | read-only | Yes | List of tracks not hidden inside collapsed group tracks. |
| `return_tracks` | `tuple[Live.Track.Track]` | read-only | Yes | Return tracks collection. |
| `master_track` | `Live.Track.Track` | read-only | No | Master track singleton. |
| `scenes` | `tuple[Live.Scene.Scene]` | read-only | Yes | List of scenes. |
| `cue_points` | `tuple[Live.Song.CuePoint]` | read-only | Yes | Arrangement cue point locators. |
| `groove_pool` | `Live.GroovePool.GroovePool` | read-only | No | Project groove library. |
| `metronome` | `bool` | read/write | Yes | Enables/disables the metronome click. |
| `groove_amount` | `float` | read/write | Yes | Global groove pool timing amount applied to song (0.0 to 1.0). |
| `swing_amount` | `float` | read/write | Yes | Global 8th/16th swing intensity percentage. |
| `view` | `Live.Song.Song.View` | read-only | No | Song view controls object. |

#### Methods

##### `start_playing() -> None`
Starts playback at current song time.

##### `stop_playing() -> None`
Stops playback.

##### `continue_playing() -> None`
Resumes playback from playhead position.

##### `stop_all_clips(quantized: bool = True) -> None`
Stops all playing session clips.

##### `jump_by(beats: float) -> None`
Jumps playhead forward/backward by specified beats.

##### `create_audio_track(index: int = -1) -> Live.Track.Track`
Creates new audio track at index.

##### `create_midi_track(index: int = -1) -> Live.Track.Track`
Creates new MIDI track at index.

##### `create_return_track() -> Live.Track.Track`
Creates new return track.

##### `delete_track(index: int) -> None`
Deletes track at index.

##### `duplicate_track(index: int) -> Live.Track.Track`
Duplicates track at index.

##### `create_scene(index: int = -1) -> Live.Scene.Scene`
Creates new scene.

##### `delete_scene(index: int) -> None`
Deletes scene at index.

##### `capture_midi(destination: CaptureDestination = auto) -> None`
Captures unrecorded MIDI buffer into clip.

##### `undo() -> None`
Reverts last undo step.

##### `redo() -> None`
Redoes last reverted step.

##### `begin_undo_step() -> None`
Starts atomic undo transaction block.

##### `end_undo_step() -> None`
Commits atomic undo transaction block.

##### `get_all_scales_ordered() -> tuple[tuple[str, tuple[int]]]`
Returns ordered list of all supported project scales.

##### `tap_tempo() -> None`
Taps tempo following user tap interval timing.

##### `jump_to_next_cue() -> None`
Jumps playhead to the next locator cue point in Arrangement view.

##### `jump_to_prev_cue() -> None`
Jumps playhead to the previous locator cue point in Arrangement view.

##### `set_or_delete_cue() -> None`
Sets a new locator cue point at the current song time, or deletes the cue point if one exists.

##### `duplicate_scene(index: int) -> Live.Scene.Scene`
Duplicates the scene at the specified index.

---

### `Live.Track.Track`
- **C++ Handle:** `TTrackPyHandle`
- **Canonical Parent:** `Live.Song.Song`
- **Docstring:** _This class represents a track in Live. It can be either an Audio track, a MIDI Track, a Return Track, or the Master Track._

Track object containing clip slots, arrangement clips, take lanes, device chains, routing, and mixer controls.

#### Properties

| Property | Type | Access | Listener | Description |
|---|---|---|---|---|
| `name` | `str` | read/write | Yes | Track header display name. |
| `color` | `int` | read/write | Yes | RGB color integer. |
| `color_index` | `int` | read/write | Yes | Color palette index [0..69]. |
| `mute` | `bool` | read/write | Yes | Mute state. |
| `solo` | `bool` | read/write | Yes | Solo state. |
| `arm` | `bool` | read/write | Yes | Record arm state. |
| `can_be_armed` | `bool` | read-only | No | True if track supports recording arm. |
| `has_audio_input` | `bool` | read-only | No | True for audio tracks. |
| `has_audio_output` | `bool` | read-only | No | True if audio signal outputs. |
| `has_midi_input` | `bool` | read-only | No | True for MIDI tracks. |
| `has_midi_output` | `bool` | read-only | No | True if MIDI signal outputs. |
| `is_foldable` | `bool` | read-only | Yes | True for group tracks. |
| `fold_state` | `bool` | read/write | Yes | Folded state of group track. |
| `is_grouped` | `bool` | read-only | No | True if track resides inside a group track. |
| `group_track` | `Live.Track.Track | None` | read-only | No | Containing group track reference. |
| `clip_slots` | `tuple[Live.ClipSlot.ClipSlot]` | read-only | Yes | Session view clip slot cells. |
| `arrangement_clips` | `tuple[Live.Clip.Clip]` | read-only | Yes | Arrangement timeline clips. |
| `take_lanes` | `tuple[Live.TakeLane.TakeLane]` | read-only | Yes | Live 12 arrangement take lanes collection. |
| `devices` | `tuple[Live.Device.Device]` | read-only | Yes | Device chain collection. |
| `mixer_device` | `Live.MixerDevice.MixerDevice` | read-only | No | Volume, pan, and send mixer device. |
| `current_monitoring_state` | `MonitoringStates` | read/write | Yes | Monitoring state (IN, AUTO, OFF). |
| `input_routing_type` | `RoutingType` | read/write | Yes | Current input routing type. |
| `input_routing_channel` | `RoutingChannel` | read/write | Yes | Current input routing channel. |
| `output_routing_type` | `RoutingType` | read/write | Yes | Current output routing type. |
| `output_routing_channel` | `RoutingChannel` | read/write | Yes | Current output routing channel. |

#### Methods

##### `create_take_lane() -> Live.TakeLane.TakeLane`
Creates and returns a new arrangement take lane on this track.

##### `duplicate_clip_slot(slot_index: int) -> int`
Duplicates clip slot to adjacent slot.

##### `delete_clip(clip: Live.Clip.Clip) -> None`
Deletes specified clip from track.

##### `duplicate_clip_to_arrangement(clip: Live.Clip.Clip, destination_time: float) -> Live.Clip.Clip`
Copies clip to arrangement timeline at destination beat.

##### `stop_all_clips(quantized: bool = True) -> None`
Stops all playing clips on this track.

---

### `Live.TakeLane.TakeLane`
- **C++ Handle:** `TPyHandle<ATakeLane>`
- **Canonical Parent:** `Live.Track.Track`
- **Docstring:** _Represents an arrangement take lane on an audio or MIDI track in Live 12._

Live 12 TakeLane API enabling non-destructive comping, programmatic take management, and per-lane clip creation in the Arrangement view.

#### Properties

| Property | Type | Access | Listener | Description |
|---|---|---|---|---|
| `name` | `str` | read/write | Yes | Name of the take lane. |
| `arrangement_clips` | `tuple[Live.Clip.Clip]` | read-only | Yes | Read-only access to the arrangement clips in the take lane. |
| `canonical_parent` | `Live.Track.Track` | read-only | No | Track that owns this take lane. |

#### Methods

##### `create_audio_clip(file_path: str, time: float) -> Live.Clip.Clip`
Creates an audio clip referencing the file at the given path and inserts it into the arrangement at the specified time. Throws an error when called on a non-audio or a frozen track, when the specified time is outside the [0., 1576800.] range, when the track is currently being recorded into, or when the path doesn't point to a valid audio file.

##### `create_midi_clip(time: float, length: float) -> Live.Clip.Clip`
Creates an empty MIDI clip and inserts it into the arrangement at the specified time. Throws an error when called on a non-MIDI track or a frozen track, when the specified time is outside the [0., 1576800.] range, or when the track is currently being recorded into.

##### `get_data(key: str, default: Any = None) -> Any`
Retrieves custom key-value data persistently stored with the take lane in the Live Set.

##### `set_data(key: str, value: Any) -> None`
Persists custom key-value metadata with the take lane into the Live Set.

---

### `Live.ClipSlot.ClipSlot`
- **C++ Handle:** `TPyHandle<AGroupAndClipSlotBase>`
- **Canonical Parent:** `Live.Track.Track`
- **Docstring:** _This class represents an entry in Lives Session view matrix._

Matrix cell in the Session View capable of hosting, triggering, or creating a Session clip.

#### Properties

| Property | Type | Access | Listener | Description |
|---|---|---|---|---|
| `has_clip` | `bool` | read-only | Yes | True if slot contains a clip. |
| `clip` | `Live.Clip.Clip | None` | read-only | Yes | Clip instance reference. |
| `is_group_slot` | `bool` | read-only | No | True if slot resides on a group track. |
| `is_playing` | `bool` | read-only | Yes | True if clip in slot is currently playing. |
| `is_triggered` | `bool` | read-only | Yes | True if clip slot launch is queued. |
| `color` | `int` | read/write | Yes | Slot background color RGB. |
| `color_index` | `int` | read/write | Yes | Color palette index. |

#### Methods

##### `create_clip(length: float) -> None`
Creates an empty MIDI clip of specified beat length in this slot.

##### `create_audio_clip(file_path: str) -> None`
Creates an audio clip referencing file path in this slot.

##### `delete_clip() -> None`
Deletes clip residing in this slot.

##### `duplicate_clip_to(target_slot: Live.ClipSlot.ClipSlot) -> None`
Copies clip to destination slot.

##### `fire() -> None`
Fires clip slot according to launch quantization.

##### `stop() -> None`
Stops playback of clip in this slot.

---

### `Live.Clip.Clip`
- **C++ Handle:** `TPyHandle<AClip>`
- **Canonical Parent:** `Live.Track.Track`
- **Docstring:** _This class represents a Clip in Live. It can be either an Audio Clip or a MIDI Clip, in an Arrangement or the Session, depending on the Track (Slot) it lives in._

Audio and MIDI container supporting Live 12 extended MIDI notes (probability, velocity_deviation, note_id), audio warp markers, pitch transpose, looping, and envelopes.

#### Properties

| Property | Type | Access | Listener | Description |
|---|---|---|---|---|
| `name` | `str` | read/write | Yes | Display label. |
| `color` | `int` | read/write | Yes | RGB color integer. |
| `color_index` | `int` | read/write | Yes | Color palette index [0..69]. |
| `muted` | `bool` | read/write | Yes | Muted / deactivated flag. |
| `is_audio_clip` | `bool` | read-only | No | True for audio clips. |
| `is_midi_clip` | `bool` | read-only | No | True for MIDI clips. |
| `is_session_clip` | `bool` | read-only | No | True for session clips. |
| `is_arrangement_clip` | `bool` | read-only | No | True for arrangement timeline clips. |
| `is_take_lane_clip` | `bool` | read-only | No | Live 12: True if clip resides in a take lane. |
| `start_time` | `float` | read/write | Yes | Timeline start position in beats for Arrangement clips. |
| `end_time` | `float` | read/write | Yes | Clip end marker. |
| `loop_start` | `float` | read/write | Yes | Loop start position. |
| `loop_end` | `float` | read/write | Yes | Loop end position. |
| `looping` | `bool` | read/write | Yes | Looping enabled flag. |
| `pitch_coarse` | `int` | read/write | Yes | Audio clip coarse pitch semitones [-48..48]. |
| `pitch_fine` | `int` | read/write | Yes | Audio clip fine pitch cents [-500..500]. |
| `warp_markers` | `tuple[WarpMarker]` | read-only | Yes | Audio warp marker collection. |
| `warping` | `bool` | read/write | Yes | Enables audio tempo warping (audio clips only). |
| `warp_mode` | `WarpMode` | read/write | Yes | Selected warp mode (beats, tones, texture, repitch, complex, complex_pro, rex). |
| `available_warp_modes` | `tuple[WarpMode]` | read-only | No | Tuple of available warp modes for this audio clip. |
| `gain` | `float` | read/write | Yes | Clip sample gain factor (1.0 = 0 dB). |
| `gain_display_string` | `str` | read-only | Yes | Formatted decibel gain string (e.g. '+3.5 dB'). |
| `file_path` | `str` | read-only | Yes | Absolute filesystem path to referenced audio file (audio clips only). |
| `length` | `float` | read-only | Yes | Total clip length in beats. |
| `position` | `float` | read-only | Yes | Current playback head position in beats. |
| `playing_position` | `float` | read-only | Yes | Real-time playhead position in beats (updated during playback). |
| `is_playing` | `bool` | read-only | Yes | True if the clip is currently actively outputting audio or MIDI. |
| `is_recording` | `bool` | read-only | Yes | True if the clip is actively recording input. |
| `is_overdubbing` | `bool` | read-only | Yes | True if MIDI overdub is actively writing notes to the clip. |
| `is_triggered` | `bool` | read-only | Yes | True if the clip has received a launch trigger and is waiting for quantization. |
| `launch_mode` | `LaunchMode` | read/write | Yes | Launch mode: trigger (0), gate (1), toggle (2), repeat (3). |
| `launch_quantization` | `ClipLaunchQuantization` | read/write | Yes | Clip-level launch quantization setting. |
| `legato` | `bool` | read/write | Yes | Enables legato clip launching. |
| `signature_numerator` | `int` | read/write | Yes | Time signature numerator for this clip. |
| `signature_denominator` | `int` | read/write | Yes | Time signature denominator for this clip. |
| `ram_mode` | `bool` | read/write | Yes | True if sample is loaded entirely into RAM. |
| `sample_length` | `float` | read-only | Yes | Raw audio sample duration in sample frames. |
| `sample_rate` | `float` | read-only | Yes | Audio sample sample rate in Hz. |
| `start_marker` | `float` | read/write | Yes | Sample/clip start marker position in beats. |
| `end_marker` | `float` | read/write | Yes | Sample/clip end marker position in beats. |
| `groove` | `Live.Groove.Groove` | read/write | Yes | The groove object applied to this clip. |
| `has_groove` | `bool` | read-only | Yes | True if a groove is assigned to the clip. |
| `has_envelopes` | `bool` | read-only | Yes | True if the clip contains any parameter automation envelopes. |
| `view` | `Live.Clip.Clip.View` | read-only | No | Clip view object. |

#### Methods

##### `get_notes_extended(from_pitch: int, pitch_span: int, from_time: float, time_span: float) -> tuple[Live.Clip.MidiNote]`
Returns a list of MIDI notes from the given pitch and time range. Each note is represented by a Live.Clip.MidiNote object.

##### `get_selected_notes_extended() -> tuple[Live.Clip.MidiNote]`
Returns a list of all MIDI notes from the clip that are currently selected. Each note is represented by a Live.Clip.MidiNote object.

##### `get_all_notes_extended() -> tuple[Live.Clip.MidiNote]`
Returns a list of all MIDI notes from the clip, regardless of position relative to loop markers.

##### `get_notes_by_id(note_ids: tuple[int]) -> tuple[Live.Clip.MidiNote]`
Return a list of MIDI notes matching the given note IDs.

##### `add_new_notes(notes: iterable[Live.Clip.MidiNoteSpecification]) -> None`
Expects a Python iterable holding Live.Clip.MidiNoteSpecification objects to construct new notes in the clip.

##### `apply_note_modifications(notes: iterable[Live.Clip.MidiNote]) -> None`
Expects a list of notes matching note IDs. Modifies existing notes while preserving per-note MPE expressions.

##### `duplicate_notes_by_id(note_ids: tuple[int], destination_time: float = -1.0, transposition_amount: int = 0) -> None`
Duplicates specified note IDs to destination time with semitone transposition.

##### `remove_notes_extended(from_pitch: int, pitch_span: int, from_time: float, time_span: float) -> None`
Delete all notes starting in the given pitch and time range.

##### `remove_notes_by_id(note_ids: tuple[int]) -> None`
Delete all notes matching the given note IDs.

##### `select_all_notes() -> None`
Selects all notes in the clip.

##### `deselect_all_notes() -> None`
Deselects all notes in the clip.

##### `quantize(quantization: int, amount: float) -> None`
Quantizes notes or audio warp markers.

##### `quantize_pitch(pitch: int, quantization: int, amount: float) -> None`
Quantizes notes of a specific pitch.

##### `note_number_to_name(midi_pitch: int) -> str`
Return human-readable name for pitch number, respecting Set scale and tuning system.

##### `add_warp_marker(beat_time: float) -> WarpMarker`
Inserts warp marker at beat position in audio clip.

##### `fire() -> None`
Launches the clip according to its launch quantization.

##### `stop() -> None`
Stops playback of the clip according to track/global launch quantization.

##### `crop() -> None`
Crops the clip to its loop boundaries.

##### `duplicate_loop() -> None`
Duplicates the active loop section and doubles clip length.

##### `clear_all_envelopes() -> None`
Removes all automation envelopes from the clip.

##### `clear_envelope(parameter: Live.DeviceParameter.DeviceParameter) -> None`
Removes the automation envelope for the specified device parameter.

---

### `Live.Clip.MidiNote`
- **C++ Handle:** `NClipApi::TNoteInfo`
- **Canonical Parent:** `Live.Clip.Clip`
- **Docstring:** _An object representing a MIDI Note in Live 12._

Represents an individual MIDI note retrieved from Live 12 extended note queries. Encapsulates note identity, probability, velocity humanization, and release velocity.

#### Properties

| Property | Type | Access | Listener | Description |
|---|---|---|---|---|
| `note_id` | `int` | read-only | No | Unique numerical note ID within originating clip. Required for apply_note_modifications. |
| `pitch` | `int` | read/write | No | MIDI pitch [0..127]. |
| `start_time` | `float` | read/write | No | Note onset beat position. |
| `duration` | `float` | read/write | No | Note duration in beats. |
| `velocity` | `float` | read/write | No | Strike velocity [0.0..127.0]. |
| `velocity_deviation` | `float` | read/write | No | Live 12: Velocity deviation range [-127.0..127.0] for humanization randomization. |
| `release_velocity` | `float` | read/write | No | Release velocity [0.0..127.0]. |
| `probability` | `float` | read/write | No | Live 12: Note triggering probability [0.0..1.0]. |
| `mute` | `bool` | read/write | No | Muted / deactivated note flag. |

---

### `Live.Clip.MidiNoteSpecification`
- **C++ Handle:** `NPythonClip::TNoteSpecification`
- **Canonical Parent:** `Live.Clip.Clip`
- **Docstring:** _An object specifying the data for creating a MIDI note. To be used with the add_new_notes function._

Specification object used to instantiate new notes via Clip.add_new_notes(). Only pitch, start_time, and duration are mandatory.

#### Properties

| Property | Type | Access | Listener | Description |
|---|---|---|---|---|
| `pitch` | `int` | read-only | No | MIDI pitch [0..127] |
| `start_time` | `float` | read-only | No | Onset in beats |
| `duration` | `float` | read-only | No | Duration in beats |
| `velocity` | `float` | read-only | No | Strike velocity [0.0..127.0] |
| `velocity_deviation` | `float` | read-only | No | Velocity deviation [-127.0..127.0] |
| `release_velocity` | `float` | read-only | No | Release velocity [0.0..127.0] |
| `probability` | `float` | read-only | No | Triggering probability [0.0..1.0] |
| `mute` | `bool` | read-only | No | Muted flag |

---

### `Live.TuningSystem.TuningSystem`
- **C++ Handle:** `TPyHandle<ATuningSystem>`
- **Canonical Parent:** `Live.Song.Song`
- **Docstring:** _Represents a Tuning System and its properties in Live 12._

Microtonal tuning system loaded into the Live Set, providing microtonal frequency calculations, step definitions, and cents offsets.

#### Properties

| Property | Type | Access | Listener | Description |
|---|---|---|---|---|
| `name` | `str` | read/write | Yes | Name of currently active tuning system. |
| `number_of_notes_in_pseudo_octave` | `int` | read-only | No | Number of pitch classes per pseudo-octave cycle. |
| `pseudo_octave_in_cents` | `float` | read-only | No | Width of octave cycle in cents (1200.0 for standard 12-TET). |
| `lowest_note` | `PitchClassAndOctave` | read/write | No | Lowest supported note (index_in_octave, octave). |
| `highest_note` | `PitchClassAndOctave` | read/write | No | Highest supported note (index_in_octave, octave). |
| `reference_pitch` | `ReferencePitch` | read/write | No | Tuning anchor (index_in_octave, octave, frequency). |
| `note_tunings` | `tuple[float]` | read/write | Yes | Cents deviation offsets for each step in pseudo-octave. |

---

### `Live.Browser.Browser`
- **C++ Handle:** `TPyHandle<ABrowserDelegate>`
- **Canonical Parent:** `Live.Application.Application`
- **Docstring:** _This class represents the live browser data base._

Sound library and asset database. Exposes categorical root items (sounds, drums, instruments, effects, packs, plugins) and provides item loading and previewing.

#### Properties

| Property | Type | Access | Listener | Description |
|---|---|---|---|---|
| `sounds` | `BrowserItem` | read-only | No | Sounds category root. |
| `drums` | `BrowserItem` | read-only | No | Drums category root. |
| `instruments` | `BrowserItem` | read-only | No | Instruments category root. |
| `audio_effects` | `BrowserItem` | read-only | No | Audio Effects category root. |
| `midi_effects` | `BrowserItem` | read-only | No | MIDI Effects category root. |
| `max_for_live` | `BrowserItem` | read-only | No | Max for Live devices category root. |
| `plugins` | `BrowserItem` | read-only | No | VST2, VST3, AU plugins root. |
| `clips` | `BrowserItem` | read-only | No | Clips root. |
| `samples` | `BrowserItem` | read-only | No | Samples root. |
| `packs` | `BrowserItem` | read-only | No | Installed Ableton Packs root. |
| `user_library` | `BrowserItem` | read-only | No | User Library root. |
| `current_project` | `BrowserItem` | read-only | No | Current Project folder root. |
| `colors` | `tuple[BrowserItem]` | read-only | No | Configured browser color tags. |

#### Methods

##### `load_item(item: BrowserItem) -> None`
Loads browser item into currently selected track, chain, or pad.

##### `preview_item(item: BrowserItem) -> None`
Starts auditioning audio preview of browser item.

##### `stop_preview() -> None`
Halts active browser preview.

##### `full_refresh() -> None`
Forces complete filesystem rescan.

##### `relation_to_hotswap_target(item: BrowserItem) -> Relation`
Evaluates relationship between item and active hotswap device.

---

### `Live.Device.Device`
- **C++ Handle:** `TPyHandle<ADevice>`
- **Canonical Parent:** `Live.Track.Track`
- **Docstring:** _This class represents a MIDI or Audio DSP-Device in Live._

Base DSP device containing parameters, on/off activator, A/B comparison preset slots, and view state.

#### Properties

| Property | Type | Access | Listener | Description |
|---|---|---|---|---|
| `name` | `str` | read/write | Yes | Device instance header name. |
| `class_name` | `str` | read-only | No | Internal C++ device identifier (e.g. 'UltraRandom', 'Roar', 'Drift'). |
| `class_display_name` | `str` | read-only | No | Human-readable device title. |
| `type` | `DeviceType` | read-only | No | audio_effect, midi_effect, or instrument. |
| `is_active` | `bool` | read/write | Yes | Device activator on/off state. |
| `parameters` | `tuple[Live.DeviceParameter.DeviceParameter]` | read-only | Yes | Automatable parameters collection. |
| `can_have_chains` | `bool` | read-only | No | True for Rack devices. |
| `can_have_drum_pads` | `bool` | read-only | No | True for Drum Rack devices. |
| `can_compare_ab` | `bool` | read-only | No | True if device supports A/B preset comparison. |

#### Methods

##### `save_preset_to_compare_ab_slot() -> None`
Stores active parameters to secondary A/B slot.

##### `store_chosen_bank(bank: int) -> None`
Stores parameter bank index.

---

### `Live.DeviceParameter.DeviceParameter`
- **C++ Handle:** `TPyHandle<ATimeableValue>`
- **Canonical Parent:** `Live.Device.Device`
- **Docstring:** _This class represents a (automatable) parameter within a MIDI or Audio DSP-Device._

DSP parameter with automation envelopes, value item strings, gesture demarcation, and listener support.

#### Properties

| Property | Type | Access | Listener | Description |
|---|---|---|---|---|
| `name` | `str` | read-only | Yes | Current parameter name. |
| `original_name` | `str` | read-only | No | Original unmapped parameter name. |
| `value` | `float` | read/write | Yes | Current raw numeric value [min..max]. |
| `display_value` | `str` | read-only | No | Formatted string with units (e.g. '12.0 kHz', '-6.0 dB'). |
| `default_value` | `float` | read-only | No | Factory default value. |
| `min` | `float` | read-only | No | Minimum allowable value. |
| `max` | `float` | read-only | No | Maximum allowable value. |
| `is_quantized` | `bool` | read-only | No | True for discrete stepped parameters. |
| `is_enabled` | `bool` | read-only | Yes | True if parameter is currently active. |
| `value_items` | `tuple[str]` | read-only | No | Enumerated display labels for quantized parameters. |
| `automation_state` | `AutomationState` | read-only | Yes | Automation status (none, playing, overridden). |
| `state` | `ParameterState` | read/write | Yes | Parameter state (enabled, irrelevant, disabled). |

#### Methods

##### `begin_gesture() -> None`
Demarcates beginning of user parameter manipulation for automation recording.

##### `end_gesture() -> None`
Demarcates end of parameter touch/manipulation.

##### `re_enable_automation() -> None`
Re-enables overridden automation for this parameter.

---

### `Live.RackDevice.RackDevice`
- **C++ Handle:** `TRackDevicePyHandle`
- **Canonical Parent:** `Live.Track.Track | Live.Chain.Chain`
- **Docstring:** _Represents an Audio Effect Rack, MIDI Effect Rack, Instrument Rack, or Drum Rack device._

Multi-chain container device supporting macro controls, macro variations, dynamic macro count, and drum pad routing.

#### Properties

| Property | Type | Access | Listener | Description |
|---|---|---|---|---|
| `canonical_parent` | `Live.Track.Track | Live.Chain.Chain` | read-only | No | Track or Chain that owns this device instance. |
| `name` | `str` | read/write | Yes | User-editable display name of this Rack Device device instance. |
| `class_name` | `str` | read-only | No | Internal Ableton class identifier ('RackDevice'). |
| `class_display_name` | `str` | read-only | No | Canonical UI name of the device type ('Rack Device'). |
| `type` | `DeviceType` | read-only | No | Device category (undefined). |
| `is_active` | `bool` | read/write | Yes | Device device-activator (on/off toggle). |
| `parameters` | `tuple[Live.DeviceParameter.DeviceParameter]` | read-only | Yes | Tuple of all controllable automation parameters. |
| `can_have_chains` | `bool` | read-only | No | Whether the device can contain nested chains. |
| `can_have_drum_pads` | `bool` | read-only | No | Whether the device can host drum pads. |
| `latency_in_ms` | `float` | read-only | Yes | Latency introduced by internal processing in milliseconds. |
| `latency_in_samples` | `int` | read-only | Yes | Latency introduced by internal processing in sample units. |
| `view` | `Live.RackDevice.RackDevice.View` | read-only | No | Rack device view object. |
| `chains` | `tuple[Live.Chain.Chain]` | read-only | Yes | Tuple of audio or MIDI chains contained in this rack. |
| `return_chains` | `tuple[Live.Chain.Chain]` | read-only | Yes | Tuple of internal return chains. |
| `drum_pads` | `tuple[Live.DrumPad.DrumPad]` | read-only | Yes | Tuple of all 128 drum pads (present on Drum Racks). |
| `visible_drum_pads` | `tuple[Live.DrumPad.DrumPad]` | read-only | Yes | Tuple of visible drum pads in the drum pad matrix view. |
| `has_drum_pads` | `bool` | read-only | No | True if this rack is a Drum Rack. |
| `has_macro_mappings` | `bool` | read-only | Yes | True if at least one macro is mapped to a downstream parameter. |
| `chain_selector` | `Live.DeviceParameter.DeviceParameter` | read-only | No | Parameter controlling chain selector zone routing. |
| `is_showing_chains` | `bool` | read/write | Yes | Whether the chain list view is visible in the GUI. |
| `can_show_chains` | `bool` | read-only | No | Whether this rack supports chain list view display. |
| `variation_count` | `int` | read-only | Yes | Number of stored macro variations. |
| `selected_variation_index` | `int` | read/write | Yes | Zero-based index of the currently selected macro variation. |
| `visible_macro_count` | `int` | read/write | Yes | Number of visible macro knobs (1 to 16). |

#### Methods

##### `store_variation() -> None`
Stores current macro parameter states as a new macro variation.

##### `recall_selected_variation() -> None`
Recalls macro parameter states from the variation at selected_variation_index.

##### `delete_selected_variation() -> None`
Deletes the macro variation at selected_variation_index.

##### `recall_last_used_variation() -> None`
Recalls the most recently used macro variation.

##### `add_macro() -> None`
Increments visible_macro_count by 1 (up to 16).

##### `remove_macro() -> None`
Decrements visible_macro_count by 1 (down to 1).

##### `randomize_macros() -> None`
Randomizes all mapped macro knob parameter values.

##### `copy_pad(source_pitch: int, destination_pitch: int) -> None`
Copies drum pad configuration and nested devices from source MIDI pitch to destination MIDI pitch.

##### `insert_chain(index: int = -1) -> Live.Chain.Chain`
Inserts a new chain at the specified index (-1 appends to the end).

---

### `Live.WavetableDevice.WavetableDevice`
- **C++ Handle:** `TWavetableDevicePyHandle`
- **Canonical Parent:** `Live.Track.Track`
- **Docstring:** _This class represents a Wavetable device._

Advanced Wavetable synthesizer featuring dual wavetable oscillators, unison modes, and a programmatic modulation matrix API.

#### Properties

| Property | Type | Access | Listener | Description |
|---|---|---|---|---|
| `visible_modulation_target_names` | `tuple[str]` | read-only | Yes | Names of visible modulation targets in matrix. |
| `oscillator_wavetable_categories` | `tuple[str]` | read-only | No | Available wavetable categories. |
| `oscillator_1_wavetables` | `tuple[str]` | read-only | No | Oscillator 1 wavetable names in category. |
| `oscillator_2_wavetables` | `tuple[str]` | read-only | No | Oscillator 2 wavetable names in category. |
| `oscillator_1_wavetable_category` | `str` | read/write | Yes | Oscillator 1 active category. |
| `oscillator_2_wavetable_category` | `str` | read/write | Yes | Oscillator 2 active category. |
| `oscillator_1_wavetable_index` | `int` | read/write | Yes | Oscillator 1 active wavetable index. |
| `oscillator_2_wavetable_index` | `int` | read/write | Yes | Oscillator 2 active wavetable index. |
| `oscillator_1_effect_mode` | `OscEffectMode` | read/write | Yes | Oscillator 1 effect mode (none, fm, classic, modern). |
| `oscillator_2_effect_mode` | `OscEffectMode` | read/write | Yes | Oscillator 2 effect mode. |
| `unison_mode` | `UnisonMode` | read/write | Yes | Unison mode. |
| `unison_voice_count` | `int` | read/write | Yes | Number of unison voices. |
| `filter_routing` | `FilterRouting` | read/write | Yes | Filter routing mode (serial, parallel, split). |

#### Methods

##### `is_parameter_modulatable(parameter: Live.DeviceParameter.DeviceParameter) -> bool`
Returns True if parameter can be modulated.

##### `add_parameter_to_modulation_matrix(parameter: Live.DeviceParameter.DeviceParameter) -> None`
Adds parameter to modulation matrix targets.

##### `get_modulation_value(source: ModulationSource, target_index: int) -> float`
Gets modulation intensity between source and target.

##### `set_modulation_value(source: ModulationSource, target_index: int, value: float) -> None`
Sets modulation amount for source-target connection.

##### `get_modulation_target_parameter_name(target_index: int) -> str`
Retrieves parameter name at target index.

---

### `Live.MeldDevice.MeldDevice`
- **C++ Handle:** `TMeldDevicePyHandle`
- **Canonical Parent:** `Live.Track.Track`
- **Docstring:** _This class represents a Meld device._

Live 12 bi-timbral macro synthesizer featuring dual independent sound engines (Engine A and Engine B), cross-modulation, and extensive macro controls.

#### Properties

| Property | Type | Access | Listener | Description |
|---|---|---|---|---|
| `selected_engine` | `int` | read/write | Yes | Active engine focus (0=Engine A, 1=Engine B). |
| `unison_voices` | `int` | read/write | Yes | Unison voice count [off, 2, 3]. |
| `mono_poly` | `int` | read/write | Yes | Voicing mode (mono, poly). |
| `poly_voices` | `int` | read/write | Yes | Polyphony voice limit [2..12]. |

---

### `Live.RoarDevice.RoarDevice`
- **C++ Handle:** `TRoarDevicePyHandle`
- **Canonical Parent:** `Live.Track.Track`
- **Docstring:** _This class represents a Roar device._

Live 12 multi-stage saturation and coloration audio effect with flexible routing stages and envelope follower auditioning.

#### Properties

| Property | Type | Access | Listener | Description |
|---|---|---|---|---|
| `routing_mode_list` | `tuple[str]` | read-only | No | Available routing topologies: ['Single', 'Serial', 'Parallel', 'Mid/Side', 'Multi-band', 'Feedback']. |
| `routing_mode_index` | `int` | read/write | Yes | Currently active routing mode index. |
| `env_listen` | `bool` | read/write | Yes | Envelope follower audition listen state. |

---

### `Live.DriftDevice.DriftDevice`
- **C++ Handle:** `TDriftDevicePyHandle`
- **Canonical Parent:** `Live.Track.Track | Live.Chain.Chain`
- **Docstring:** _This class represents a Drift device._

Ableton Live 12 Drift analog-subtractive synthesizer device with voice modes, independent stereo filter modulation, and flexible modulation matrix routing.

#### Properties

| Property | Type | Access | Listener | Description |
|---|---|---|---|---|
| `canonical_parent` | `Live.Track.Track | Live.Chain.Chain` | read-only | No | Track or Chain that owns this device instance. |
| `name` | `str` | read/write | Yes | User-editable display name of this Drift device instance. |
| `class_name` | `str` | read-only | No | Internal Ableton class identifier ('Drift'). |
| `class_display_name` | `str` | read-only | No | Canonical UI name of the device type ('Drift'). |
| `type` | `DeviceType` | read-only | No | Device category (instrument). |
| `is_active` | `bool` | read/write | Yes | Device device-activator (on/off toggle). |
| `parameters` | `tuple[Live.DeviceParameter.DeviceParameter]` | read-only | Yes | Tuple of all controllable automation parameters. |
| `can_have_chains` | `bool` | read-only | No | Whether the device can contain nested chains. |
| `can_have_drum_pads` | `bool` | read-only | No | Whether the device can host drum pads. |
| `latency_in_ms` | `float` | read-only | Yes | Latency introduced by internal processing in milliseconds. |
| `latency_in_samples` | `int` | read-only | Yes | Latency introduced by internal processing in sample units. |
| `view` | `Live.Device.Device.View` | read-only | No | GUI view controls for the device. |
| `voice_mode_list` | `list[str]` | read-only | No | Return the voice mode list (Poly, Mono, Stereo, Legato). |
| `voice_mode_index` | `int` | read/write | Yes | Return the voice mode index. |
| `voice_count_list` | `list[str]` | read-only | No | Return the voice count list. |
| `voice_count_index` | `int` | read/write | Yes | Return the voice count index. |
| `mod_matrix_shape_source_list` | `list[str]` | read-only | No | Return the shape mod source list. |
| `mod_matrix_shape_source_index` | `int` | read/write | Yes | Return the shape mod source index. |
| `mod_matrix_lfo_source_list` | `list[str]` | read-only | No | Return the lfo mod source list. |
| `mod_matrix_lfo_source_index` | `int` | read/write | Yes | Return the lfo mod source index. |
| `mod_matrix_filter_source_1_list` | `list[str]` | read-only | No | Return the filter mod source 1 list. |
| `mod_matrix_filter_source_1_index` | `int` | read/write | Yes | Return the filter mod source 1 index. |
| `mod_matrix_filter_source_2_list` | `list[str]` | read-only | No | Return the filter mod source 2 list. |
| `mod_matrix_filter_source_2_index` | `int` | read/write | Yes | Return the filter mod source 2 index. |
| `mod_matrix_pitch_source_1_list` | `list[str]` | read-only | No | Return the pitch mod source 1 list. |
| `mod_matrix_pitch_source_1_index` | `int` | read/write | Yes | Return the pitch mod source 1 index. |
| `mod_matrix_pitch_source_2_list` | `list[str]` | read-only | No | Return the pitch mod source 2 list. |
| `mod_matrix_pitch_source_2_index` | `int` | read/write | Yes | Return the pitch mod source 2 index. |
| `mod_matrix_source_1_list` | `list[str]` | read-only | No | Return the custom mod source 1 list. |
| `mod_matrix_source_1_index` | `int` | read/write | Yes | Return the custom mod source 1 index. |
| `mod_matrix_source_2_list` | `list[str]` | read-only | No | Return the custom mod source 2 list. |
| `mod_matrix_source_2_index` | `int` | read/write | Yes | Return the custom mod source 2 index. |
| `mod_matrix_source_3_list` | `list[str]` | read-only | No | Return the custom mod source 3 list. |
| `mod_matrix_source_3_index` | `int` | read/write | Yes | Return the custom mod source 3 index. |
| `mod_matrix_target_1_list` | `list[str]` | read-only | No | Return the custom mod target 1 list. |
| `mod_matrix_target_1_index` | `int` | read/write | Yes | Return the custom mod target 1 index. |
| `mod_matrix_target_2_list` | `list[str]` | read-only | No | Return the custom mod target 2 list. |
| `mod_matrix_target_2_index` | `int` | read/write | Yes | Return the custom mod target 2 index. |
| `mod_matrix_target_3_list` | `list[str]` | read-only | No | Return the custom mod target 3 list. |
| `mod_matrix_target_3_index` | `int` | read/write | Yes | Return the custom mod target 3 index. |
| `pitch_bend_range` | `int` | read/write | Yes | Return the Pitch Bend Range in semitones. |

---

### `Live.CcControlDevice.CcControlDevice`
- **C++ Handle:** `TCcControlDevicePyHandle`
- **Canonical Parent:** `Live.Track.Track | Live.Chain.Chain`
- **Docstring:** _This class represents a CcControl device._

Ableton Live 12 MIDI effect device for transmitting customizable continuous controllers, program changes, and boolean CC messages to external MIDI hardware and plug-ins.

#### Properties

| Property | Type | Access | Listener | Description |
|---|---|---|---|---|
| `canonical_parent` | `Live.Track.Track | Live.Chain.Chain` | read-only | No | Track or Chain that owns this device instance. |
| `name` | `str` | read/write | Yes | User-editable display name of this CC Control device instance. |
| `class_name` | `str` | read-only | No | Internal Ableton class identifier ('CcControl'). |
| `class_display_name` | `str` | read-only | No | Canonical UI name of the device type ('CC Control'). |
| `type` | `DeviceType` | read-only | No | Device category (midi_effect). |
| `is_active` | `bool` | read/write | Yes | Device device-activator (on/off toggle). |
| `parameters` | `tuple[Live.DeviceParameter.DeviceParameter]` | read-only | Yes | Tuple of all controllable automation parameters. |
| `can_have_chains` | `bool` | read-only | No | Whether the device can contain nested chains. |
| `can_have_drum_pads` | `bool` | read-only | No | Whether the device can host drum pads. |
| `latency_in_ms` | `float` | read-only | Yes | Latency introduced by internal processing in milliseconds. |
| `latency_in_samples` | `int` | read-only | Yes | Latency introduced by internal processing in sample units. |
| `view` | `Live.Device.Device.View` | read-only | No | GUI view controls for the device. |
| `custom_bool_target_list` | `list[str]` | read-only | No | Return the custom bool target list. |
| `custom_bool_target` | `int` | read/write | Yes | Return the custom bool target CC index. |
| `custom_float_target_0_list` | `list[str]` | read-only | No | Return the custom float target 0 list. |
| `custom_float_target_0` | `int` | read/write | Yes | Return the custom float target 0 CC index. |
| `custom_float_target_1_list` | `list[str]` | read-only | No | Return the custom float target 1 list. |
| `custom_float_target_1` | `int` | read/write | Yes | Return the custom float target 1 CC index. |
| `custom_float_target_2_list` | `list[str]` | read-only | No | Return the custom float target 2 list. |
| `custom_float_target_2` | `int` | read/write | Yes | Return the custom float target 2 CC index. |
| `custom_float_target_3_list` | `list[str]` | read-only | No | Return the custom float target 3 list. |
| `custom_float_target_3` | `int` | read/write | Yes | Return the custom float target 3 CC index. |
| `custom_float_target_4_list` | `list[str]` | read-only | No | Return the custom float target 4 list. |
| `custom_float_target_4` | `int` | read/write | Yes | Return the custom float target 4 CC index. |
| `custom_float_target_5_list` | `list[str]` | read-only | No | Return the custom float target 5 list. |
| `custom_float_target_5` | `int` | read/write | Yes | Return the custom float target 5 CC index. |
| `custom_float_target_6_list` | `list[str]` | read-only | No | Return the custom float target 6 list. |
| `custom_float_target_6` | `int` | read/write | Yes | Return the custom float target 6 CC index. |
| `custom_float_target_7_list` | `list[str]` | read-only | No | Return the custom float target 7 list. |
| `custom_float_target_7` | `int` | read/write | Yes | Return the custom float target 7 CC index. |
| `custom_float_target_8_list` | `list[str]` | read-only | No | Return the custom float target 8 list. |
| `custom_float_target_8` | `int` | read/write | Yes | Return the custom float target 8 CC index. |
| `custom_float_target_9_list` | `list[str]` | read-only | No | Return the custom float target 9 list. |
| `custom_float_target_9` | `int` | read/write | Yes | Return the custom float target 9 CC index. |
| `custom_float_target_10_list` | `list[str]` | read-only | No | Return the custom float target 10 list. |
| `custom_float_target_10` | `int` | read/write | Yes | Return the custom float target 10 CC index. |
| `custom_float_target_11_list` | `list[str]` | read-only | No | Return the custom float target 11 list. |
| `custom_float_target_11` | `int` | read/write | Yes | Return the custom float target 11 CC index. |

#### Methods

##### `resend() -> None`
Resend all CC values to output.

---

### `Live.SimplerDevice.SimplerDevice`
- **C++ Handle:** `TSimplerDevicePyHandle`
- **Canonical Parent:** `Live.Track.Track | Live.Chain.Chain`
- **Docstring:** _This class represents a Simpler device in Live._

Ableton Simpler sampling instrument device, supporting sample replacement, playback slicing, warping, and multi-sample parts.

#### Properties

| Property | Type | Access | Listener | Description |
|---|---|---|---|---|
| `canonical_parent` | `Live.Track.Track | Live.Chain.Chain` | read-only | No | Track or Chain that owns this device instance. |
| `name` | `str` | read/write | Yes | User-editable display name of this Simpler device instance. |
| `class_name` | `str` | read-only | No | Internal Ableton class identifier ('OriginalSimpler'). |
| `class_display_name` | `str` | read-only | No | Canonical UI name of the device type ('Simpler'). |
| `type` | `DeviceType` | read-only | No | Device category (instrument). |
| `is_active` | `bool` | read/write | Yes | Device device-activator (on/off toggle). |
| `parameters` | `tuple[Live.DeviceParameter.DeviceParameter]` | read-only | Yes | Tuple of all controllable automation parameters. |
| `can_have_chains` | `bool` | read-only | No | Whether the device can contain nested chains. |
| `can_have_drum_pads` | `bool` | read-only | No | Whether the device can host drum pads. |
| `latency_in_ms` | `float` | read-only | Yes | Latency introduced by internal processing in milliseconds. |
| `latency_in_samples` | `int` | read-only | Yes | Latency introduced by internal processing in sample units. |
| `view` | `Live.SimplerDevice.SimplerDevice.View` | read-only | No | Simpler device view object. |
| `sample` | `Live.Sample.Sample` | read-only | Yes | Reference to the loaded sample object. |
| `playback_mode` | `PlaybackMode` | read/write | Yes | PlaybackMode: Classic (0), One-Shot (1), Slicing (2). |
| `playing_position` | `float` | read-only | Yes | Current playback position within the sample in seconds. |
| `playing_position_enabled` | `bool` | read/write | Yes | Enables real-time tracking of playing position. |
| `pad_slicing` | `bool` | read/write | Yes | Enables manual pad slicing mode. |
| `multi_sample_mode` | `bool` | read-only | Yes | Whether Simpler is in multi-sample mode. |
| `slicing_playback_mode` | `int` | read/write | Yes | Playback mode for slices: Mono (0), Poly (1), Through (2). |
| `voices` | `int` | read/write | Yes | Maximum voice polyphony. |
| `retrigger` | `bool` | read/write | Yes | Retrigger sample playback on note on. |
| `can_warp_as` | `bool` | read-only | Yes | Whether warp_as can currently be executed on the loaded sample. |
| `can_warp_double` | `bool` | read-only | Yes | Whether warp_double can currently be executed on the loaded sample. |
| `can_warp_half` | `bool` | read-only | Yes | Whether warp_half can currently be executed on the loaded sample. |

#### Methods

##### `replace_sample(file_path: str) -> None`
Replaces the loaded samples with the one at the provided path.

##### `crop() -> None`
Crops the loaded sample to the current start and end marker bounds.

##### `reverse() -> None`
Reverses the audio sample in memory.

##### `guess_playback_length() -> None`
Analyzes the sample and guesses the optimal playback length.

##### `warp_as(length: float) -> None`
Warps the sample to a specified target length in beats.

##### `warp_double() -> None`
Doubles the warp tempo (halves playback speed).

##### `warp_half() -> None`
Halves the warp tempo (doubles playback speed).

---

### `Live.Chain.Chain`
- **C++ Handle:** `TChainPyHandle`
- **Canonical Parent:** `Live.RackDevice.RackDevice`
- **Docstring:** _This class represents a group device chain in Live._

Individual branch within an Audio, MIDI, or Instrument Rack holding its own sub-device chain and mixer.

#### Properties

| Property | Type | Access | Listener | Description |
|---|---|---|---|---|
| `name` | `str` | read/write | Yes | Chain display name. |
| `color` | `int` | read/write | Yes | Color integer. |
| `devices` | `tuple[Live.Device.Device]` | read-only | Yes | Sub-device chain collection. |
| `mixer_device` | `Live.ChainMixerDevice.ChainMixerDevice` | read-only | No | Chain volume, pan, and send mixer. |

#### Methods

##### `duplicate_device(index: int) -> Live.Device.Device`
Duplicates device at index.

##### `delete_device(index: int) -> None`
Deletes device at index.

---

### `Live.DrumPad.DrumPad`
- **C++ Handle:** `TPyHandle<ADrumGroupDevicePad>`
- **Canonical Parent:** `Live.RackDevice.RackDevice`
- **Docstring:** _This class represents a drum group device pad in Live._

Individual pad in a Drum Rack assigned to a MIDI note [0..127].

#### Properties

| Property | Type | Access | Listener | Description |
|---|---|---|---|---|
| `name` | `str` | read/write | Yes | Pad header label. |
| `note` | `int` | read-only | No | Assigned MIDI note number [0..127]. |
| `mute` | `bool` | read/write | Yes | Pad mute status. |
| `solo` | `bool` | read/write | Yes | Pad solo status. |
| `chains` | `tuple[Live.DrumChain.DrumChain]` | read-only | Yes | Chains triggered by this pad. |

#### Methods

##### `delete_all_chains() -> None`
Deletes all chains associated with this pad.

---

### `Live.Scene.Scene`
- **C++ Handle:** `TPyHandle<AScene>`
- **Canonical Parent:** `Live.Song.Song`
- **Docstring:** _This class represents an series of ClipSlots in Lives Sessionview matrix._

Horizontal row across all tracks in the Session View, capable of launching all clips simultaneously.

#### Properties

| Property | Type | Access | Listener | Description |
|---|---|---|---|---|
| `name` | `str` | read/write | Yes | Scene label. |
| `color` | `int` | read/write | Yes | RGB color integer. |
| `clip_slots` | `tuple[Live.ClipSlot.ClipSlot]` | read-only | No | Clip slots comprising this scene. |
| `tempo` | `float` | read/write | No | Tempo override in BPM if defined. |
| `time_signature_numerator` | `int` | read/write | Yes | Scene time signature numerator. |
| `time_signature_denominator` | `int` | read/write | Yes | Scene time signature denominator. |
| `time_signature_enabled` | `bool` | read/write | Yes | True if scene launch overrides project time signature. |
| `tempo_enabled` | `bool` | read/write | Yes | True if scene launch overrides project tempo. |

#### Methods

##### `fire() -> None`
Fires scene according to launch quantization.

##### `fire_as_selected() -> None`
Selects scene and fires.

---

### `Live.Base.Timer`
- **C++ Handle:** `PythonTimer`
- **Canonical Parent:** `None`
- **Docstring:** _A timer that will trigger a callback after a certain inverval. The timer can be repeated and will trigger the callback every interval. Errors in the callback will stop the timer._

High-frequency C++ timer embedded in Live's main event loop. Crucial for scheduling asynchronous RPC bridge queue dispatches at 5ms intervals on the main thread.

#### Properties

| Property | Type | Access | Listener | Description |
|---|---|---|---|---|
| `interval` | `int` | read/write | No | Timer interval in milliseconds. |
| `repeat` | `bool` | read/write | No | Whether timer repeats periodically. |
| `running` | `bool` | read-only | No | Whether timer is actively running. |

#### Methods

##### `start() -> None`
Starts timer execution.

##### `stop() -> None`
Stops timer execution.

##### `restart() -> None`
Restarts timer from zero elapsed time.

---

### `Live.SpectralResonatorDevice.SpectralResonatorDevice`
- **C++ Handle:** `TPyHandle<ATrackDevice>`
- **Canonical Parent:** `Live.Track.Track | Live.Chain.Chain`
- **Docstring:** _This class represents a Spectral Resonator device._

Live 12 Spectral Resonator audio effect device with spectral processing, polyphonic MIDI sidechain resonator modes, and tuning controls.

#### Properties

| Property | Type | Access | Listener | Description |
|---|---|---|---|---|
| `canonical_parent` | `Live.Track.Track | Live.Chain.Chain` | read-only | No | Track or Chain that owns this device instance. |
| `name` | `str` | read/write | Yes | User-editable display name of this Spectral Resonator device instance. |
| `class_name` | `str` | read-only | No | Internal Ableton class identifier ('SpectralResonator'). |
| `class_display_name` | `str` | read-only | No | Canonical UI name of the device type ('Spectral Resonator'). |
| `type` | `DeviceType` | read-only | No | Device category (audio_effect). |
| `is_active` | `bool` | read/write | Yes | Device device-activator (on/off toggle). |
| `parameters` | `tuple[Live.DeviceParameter.DeviceParameter]` | read-only | Yes | Tuple of all controllable automation parameters. |
| `can_have_chains` | `bool` | read-only | No | Whether the device can contain nested chains. |
| `can_have_drum_pads` | `bool` | read-only | No | Whether the device can host drum pads. |
| `latency_in_ms` | `float` | read-only | Yes | Latency introduced by internal processing in milliseconds. |
| `latency_in_samples` | `int` | read-only | Yes | Latency introduced by internal processing in sample units. |
| `view` | `Live.Device.Device.View` | read-only | No | GUI view controls for the device. |
| `frequency_dial_mode_list` | `list[str]` | read-only | No | Return the current frequency dial mode list (e.g. ['hz', 'note']). |
| `frequency_dial_mode` | `int` | read/write | Yes | Return the current frequency dial mode index. |
| `midi_gate_list` | `list[str]` | read-only | No | Return the current midi gate list. |
| `midi_gate` | `int` | read/write | Yes | Return the current midi gate index. |
| `mod_mode_list` | `list[str]` | read-only | No | Return the current mod mode list (e.g. ['chorus', 'wander', 'granular']). |
| `mod_mode` | `int` | read/write | Yes | Return the current mod mode index. |
| `mono_poly_list` | `list[str]` | read-only | No | Return the current mono poly mode list (e.g. ['mono', 'poly']). |
| `mono_poly` | `int` | read/write | Yes | Return the current mono poly mode index. |
| `pitch_mode` | `int` | read/write | Yes | Return the current pitch bend range setting. |
| `pitch_bend_range` | `int` | read/write | Yes | Pitch bend range in semitones. |
| `polyphony` | `int` | read/write | Yes | Return the current polyphony. |

---

### `Live.MixerDevice.MixerDevice`
- **C++ Handle:** `TPyHandle<ABranchMixerDevice>`
- **Canonical Parent:** `Live.Track.Track`
- **Docstring:** _This class represents a Mixer Device in Live, which gives you access to the Volume and Panning properties of a Track._

Mixer component governing track volume, stereo balance panning, send return amounts, crossfader assignment, and monitoring split.

#### Properties

| Property | Type | Access | Listener | Description |
|---|---|---|---|---|
| `volume` | `Live.DeviceParameter.DeviceParameter` | read-only | No | Track volume parameter. |
| `panning` | `Live.DeviceParameter.DeviceParameter` | read-only | No | Track stereo pan parameter. |
| `sends` | `tuple[Live.DeviceParameter.DeviceParameter]` | read-only | No | Collection of auxiliary send parameters. |
| `crossfader` | `Live.DeviceParameter.DeviceParameter` | read-only | No | Master crossfader parameter (on Master track). |
| `cue_volume` | `Live.DeviceParameter.DeviceParameter` | read-only | No | Cue audition volume parameter. |
| `crossfade_assign` | `CrossfadeAssignments` | read/write | Yes | Crossfader assignment (A, NONE, B). |
| `left_split_stereo` | `Live.DeviceParameter.DeviceParameter` | read-only | No | Split stereo left pan parameter. |
| `right_split_stereo` | `Live.DeviceParameter.DeviceParameter` | read-only | No | Split stereo right pan parameter. |
| `track_activator` | `Live.DeviceParameter.DeviceParameter` | read-only | No | Track mute/unmute activator parameter. |

---

### `Live.GroovePool.GroovePool`
- **C++ Handle:** `TPyHandle<AGroovePool>`
- **Canonical Parent:** `Live.Song.Song`
- **Docstring:** _This class represents the groove pool in Live._

Project-wide repository containing timing and velocity swing templates applicable to clips.

#### Properties

| Property | Type | Access | Listener | Description |
|---|---|---|---|---|
| `grooves` | `tuple[Live.Groove.Groove]` | read-only | Yes | Collection of grooves loaded into the pool. |

---

### `Live.Sample.Sample`
- **C++ Handle:** `TPyHandle<AMultiSamplePart>`
- **Canonical Parent:** `Live.SimplerDevice.SimplerDevice`
- **Docstring:** _This class represents a sample file loaded into a Simpler instance._

Underlying audio waveform asset loaded in Simpler, providing sample bounds, warping, transient detection markers, and slicing.

#### Properties

| Property | Type | Access | Listener | Description |
|---|---|---|---|---|
| `file_path` | `str` | read-only | Yes | Filesystem path to source audio sample. |
| `length` | `float` | read-only | No | Sample length in samples. |
| `sample_rate` | `float` | read-only | No | Audio sample rate in Hz (e.g. 44100.0, 48000.0). |
| `gain` | `float` | read/write | Yes | Sample playback gain factor. |
| `slicing_sensitivity` | `float` | read/write | Yes | Transient detector threshold sensitivity [0.0..100.0]. |
| `slices` | `tuple[float]` | read-only | Yes | Sample slice boundary markers in samples. |
| `warping` | `bool` | read/write | Yes | Whether sample warping engine is active. |
| `warp_mode` | `WarpMode` | read/write | Yes | Active time-stretching warp algorithm. |
| `slicing_style` | `SlicingStyle` | read/write | Yes | Slicing algorithm: transient (0), beat (1), region (2), manual (3). |
| `slicing_beat_grid` | `SlicingBeatGrid` | read/write | Yes | Beat division grid used when slicing_style is beat. |
| `slicing_region_count` | `int` | read/write | Yes | Number of equal divisions when slicing_style is region. |
| `slicing_beat_division` | `SlicingBeatDivision` | read/write | Yes | Grid resolution when slicing by beat division. |

#### Methods

##### `clear_slices() -> None`
Clears all transient slice markers.

##### `insert_slice(sample_time: float) -> None`
Inserts manual slice marker at sample index.

##### `move_slice(old_sample_time: float, new_sample_time: float) -> None`
Moves slice marker position.

---

### `Live.MaxDevice.MaxDevice`
- **C++ Handle:** `TMaxDevicePyHandle`
- **Canonical Parent:** `Live.Track.Track`
- **Docstring:** _This class represents a Max for Live device._

Max for Live interactive patch container with dynamic parameter mapping and direct LOM integration.

#### Properties

| Property | Type | Access | Listener | Description |
|---|---|---|---|---|
| `audio_inputs` | `tuple[DeviceIO]` | read-only | No | Configured audio input routing buses. |
| `audio_outputs` | `tuple[DeviceIO]` | read-only | No | Configured audio output routing buses. |
| `midi_inputs` | `tuple[DeviceIO]` | read-only | No | Configured MIDI input routing buses. |
| `midi_outputs` | `tuple[DeviceIO]` | read-only | No | Configured MIDI output routing buses. |
| `parameters` | `tuple[Live.DeviceParameter.DeviceParameter]` | read-only | Yes | Max patch exposed automatable parameters. |

#### Methods

##### `get_bank_count() -> int`
Returns number of configured parameter banks.

##### `get_bank_name(bank_index: int) -> str`
Returns name of parameter bank at index.

##### `get_bank_parameters(bank_index: int) -> tuple[Live.DeviceParameter.DeviceParameter]`
Returns parameters assigned to bank.

---

### `Live.Browser.BrowserItem`
- **C++ Handle:** `NPythonBrowser::TPythonBrowserItem`
- **Canonical Parent:** `Live.Browser.Browser | Live.Browser.BrowserItem`
- **Docstring:** _This class represents an item of the browser hierarchy._

Represents a leaf node or folder container in Ableton Live's unified database browser, allowing programmatic traversal and loading of devices, presets, samples, and packs.

#### Properties

| Property | Type | Access | Listener | Description |
|---|---|---|---|---|
| `name` | `str` | read-only | No | Const access to the canonical display name of this browser item. |
| `source` | `str` | read-only | No | Specifies where the item comes from (e.g. Core Library, Live pack, User Library). |
| `uri` | `str` | read-only | No | The uri describes a unique identifier for a browser item used for loading. |
| `is_folder` | `bool` | read-only | No | Indicates if the browser item represents a folder containing children. |
| `is_device` | `bool` | read-only | No | Indicates if the browser item represents a device or plugin. |
| `is_loadable` | `bool` | read-only | No | True if item can be loaded via the Browser's 'load_item' method. |
| `is_selected` | `bool` | read-only | No | True if the item is ancestor of or the actual current UI selection. |
| `children` | `tuple[Live.Browser.BrowserItem]` | read-only | No | Const access to the descendant child items of this browser item. |
| `iter_children` | `Any` | read-only | No | Const iterable access to the descendants of this browser item. |

---

### `Live.Song.Song.View`
- **C++ Handle:** `TPyViewData<ASong>`
- **Canonical Parent:** `Live.Song.Song`
- **Docstring:** _Represents the view state and UI selection of the current Live document._

Provides control over UI selections, current focus, and detail views in the main Ableton Live window.

#### Properties

| Property | Type | Access | Listener | Description |
|---|---|---|---|---|
| `canonical_parent` | `Live.Song.Song` | read-only | No | Song instance owning this view. |
| `selected_track` | `Live.Track.Track` | read/write | Yes | Currently selected track in the UI. |
| `selected_scene` | `Live.Scene.Scene` | read/write | Yes | Currently selected scene in the UI. |
| `selected_chain` | `Live.Chain.Chain` | read/write | Yes | Currently selected device chain. |
| `selected_parameter` | `Live.DeviceParameter.DeviceParameter` | read/write | Yes | Currently focused device parameter. |
| `highlighted_clip_slot` | `Live.ClipSlot.ClipSlot` | read/write | Yes | Currently focused Session clip slot. |
| `detail_clip` | `Live.Clip.Clip` | read-only | Yes | Clip currently displayed in the Detail view. |
| `draw_mode` | `bool` | read/write | Yes | Whether automation pencil / draw mode is active. |
| `follow_song` | `bool` | read/write | Yes | Whether Arrangement view follows the playhead. |

#### Methods

##### `select_device(device: Live.Device.Device) -> None`
Selects and focuses the specified device in the Detail Device Chain view.

---

### `Live.Track.Track.View`
- **C++ Handle:** `TPyViewData<ATrack>`
- **Canonical Parent:** `Live.Track.Track`
- **Docstring:** _Represents the view state of a specific Track._

Controls track collapse state, device insertion modes, and device selection on this track.

#### Properties

| Property | Type | Access | Listener | Description |
|---|---|---|---|---|
| `canonical_parent` | `Live.Track.Track` | read-only | No | Track owning this view. |
| `is_collapsed` | `bool` | read/write | Yes | Whether track height is collapsed in Arrangement view. |
| `device_insert_mode` | `DeviceInsertMode` | read/write | Yes | Insertion mode: selected_left (0), selected_right (1), default (2). |
| `selected_device` | `Live.Device.Device` | read/write | Yes | Currently selected device on this track. |

#### Methods

##### `select_instrument() -> None`
Selects and focuses the primary instrument device on this track.

---

### `Live.Clip.Clip.View`
- **C++ Handle:** `TPyViewData<AClip>`
- **Canonical Parent:** `Live.Clip.Clip`
- **Docstring:** _Represents the view state of a Clip in the Detail Clip view._

Controls clip editor grid quantization, triplet modes, envelope parameter selection, and loop zooming.

#### Properties

| Property | Type | Access | Listener | Description |
|---|---|---|---|---|
| `canonical_parent` | `Live.Clip.Clip` | read-only | No | Clip owning this view. |
| `grid_quantization` | `GridQuantization` | read/write | Yes | Clip detail grid division setting. |
| `grid_is_triplet` | `bool` | read/write | Yes | Whether grid is set to triplet divisions. |

#### Methods

##### `show_envelope() -> None`
Displays the clip envelope editor panel.

##### `hide_envelope() -> None`
Hides the clip envelope editor panel.

##### `select_envelope_parameter(parameter: Live.DeviceParameter.DeviceParameter) -> None`
Focuses the envelope view on the specified device parameter.

##### `show_loop() -> None`
Zooms the clip view to display the full active loop region.

---

### `Live.Device.Device.View`
- **C++ Handle:** `TPyViewData<ADevice>`
- **Canonical Parent:** `Live.Device.Device`
- **Docstring:** _Represents the GUI view state of an Ableton device._

Controls device display state and GUI expansion in the Detail Device Chain view.

#### Properties

| Property | Type | Access | Listener | Description |
|---|---|---|---|---|
| `canonical_parent` | `Live.Device.Device` | read-only | No | Device instance owning this view. |
| `is_collapsed` | `bool` | read/write | Yes | Whether the device display panel is collapsed in the chain. |

---

### `Live.RackDevice.RackDevice.View`
- **C++ Handle:** `TRackDevicePyViewData`
- **Canonical Parent:** `Live.RackDevice.RackDevice`
- **Docstring:** _Represents the view state of a RackDevice._

Controls rack chain visibility, drum pad scroll offset, and selected chain/pad in the rack GUI.

#### Properties

| Property | Type | Access | Listener | Description |
|---|---|---|---|---|
| `canonical_parent` | `Live.RackDevice.RackDevice` | read-only | No | Rack device owning this view. |
| `is_collapsed` | `bool` | read/write | Yes | Whether the rack device display is collapsed. |
| `is_showing_chain_devices` | `bool` | read/write | Yes | Whether devices inside the selected chain are visible. |
| `selected_chain` | `Live.Chain.Chain` | read/write | Yes | Currently selected chain in the rack. |
| `selected_drum_pad` | `Live.DrumPad.DrumPad` | read/write | Yes | Currently selected drum pad (if Drum Rack). |
| `drum_pads_scroll_position` | `int` | read/write | Yes | Vertical scroll row position of the drum pad grid. |

---

### `Live.SimplerDevice.SimplerDevice.View`
- **C++ Handle:** `TSimplerDevicePyViewData`
- **Canonical Parent:** `Live.SimplerDevice.SimplerDevice`
- **Docstring:** _Represents the view state of a Simpler device._

Controls Simpler waveform zoom, collapse state, and selected slice index.

#### Properties

| Property | Type | Access | Listener | Description |
|---|---|---|---|---|
| `canonical_parent` | `Live.SimplerDevice.SimplerDevice` | read-only | No | Simpler device owning this view. |
| `is_collapsed` | `bool` | read/write | Yes | Whether Simpler UI is collapsed. |
| `selected_slice` | `int` | read/write | Yes | Index of the currently selected waveform slice. |

---

### `Live.Eq8Device.Eq8Device.View`
- **C++ Handle:** `TEq8DevicePyViewData`
- **Canonical Parent:** `Live.Eq8Device.Eq8Device`
- **Docstring:** _Represents the view state of an EQ Eight device._

Controls EQ Eight band selection and display collapse in the Device Chain view.

#### Properties

| Property | Type | Access | Listener | Description |
|---|---|---|---|---|
| `canonical_parent` | `Live.Eq8Device.Eq8Device` | read-only | No | EQ Eight device owning this view. |
| `is_collapsed` | `bool` | read/write | Yes | Whether EQ Eight UI is collapsed. |
| `selected_band` | `int` | read/write | Yes | Zero-based index of the currently selected filter band (0-7). |

---

### `Live.ShifterDevice.ShifterDevice`
- **C++ Handle:** `TShifterDevicePyHandle`
- **Canonical Parent:** `Live.Track.Track | Live.Chain.Chain`
- **Docstring:** _This class represents a Shifter device in Live._

Live 12 frequency shifter and pitch shifter audio effect device with multi-mode pitch, frequency, and ring modulation algorithms.

#### Properties

| Property | Type | Access | Listener | Description |
|---|---|---|---|---|
| `canonical_parent` | `Live.Track.Track | Live.Chain.Chain` | read-only | No | Track or Chain that owns this device instance. |
| `name` | `str` | read/write | Yes | User-editable display name of this Shifter device instance. |
| `class_name` | `str` | read-only | No | Internal Ableton class identifier ('Shifter'). |
| `class_display_name` | `str` | read-only | No | Canonical UI name of the device type ('Shifter'). |
| `type` | `DeviceType` | read-only | No | Device category (audio_effect). |
| `is_active` | `bool` | read/write | Yes | Device device-activator (on/off toggle). |
| `parameters` | `tuple[Live.DeviceParameter.DeviceParameter]` | read-only | Yes | Tuple of all controllable automation parameters. |
| `can_have_chains` | `bool` | read-only | No | Whether the device can contain nested chains. |
| `can_have_drum_pads` | `bool` | read-only | No | Whether the device can host drum pads. |
| `latency_in_ms` | `float` | read-only | Yes | Latency introduced by internal processing in milliseconds. |
| `latency_in_samples` | `int` | read-only | Yes | Latency introduced by internal processing in sample units. |
| `view` | `Live.Device.Device.View` | read-only | No | GUI view controls for the device. |
| `pitch_bend_range` | `int` | read/write | Yes | Pitch bend range in semitones. |
| `pitch_mode_index` | `int` | read/write | Yes | Selected mode index (Pitch, Frequency, Ring Mod). |

---

### `Live.CompressorDevice.CompressorDevice`
- **C++ Handle:** `TCompressorDevicePyHandle`
- **Canonical Parent:** `Live.Track.Track | Live.Chain.Chain`
- **Docstring:** _This class represents a Compressor device in Live._

Ableton Compressor audio effect device supporting variable sidechain input routing and gain reduction processing.

#### Properties

| Property | Type | Access | Listener | Description |
|---|---|---|---|---|
| `canonical_parent` | `Live.Track.Track | Live.Chain.Chain` | read-only | No | Track or Chain that owns this device instance. |
| `name` | `str` | read/write | Yes | User-editable display name of this Compressor device instance. |
| `class_name` | `str` | read-only | No | Internal Ableton class identifier ('Compressor2'). |
| `class_display_name` | `str` | read-only | No | Canonical UI name of the device type ('Compressor'). |
| `type` | `DeviceType` | read-only | No | Device category (audio_effect). |
| `is_active` | `bool` | read/write | Yes | Device device-activator (on/off toggle). |
| `parameters` | `tuple[Live.DeviceParameter.DeviceParameter]` | read-only | Yes | Tuple of all controllable automation parameters. |
| `can_have_chains` | `bool` | read-only | No | Whether the device can contain nested chains. |
| `can_have_drum_pads` | `bool` | read-only | No | Whether the device can host drum pads. |
| `latency_in_ms` | `float` | read-only | Yes | Latency introduced by internal processing in milliseconds. |
| `latency_in_samples` | `int` | read-only | Yes | Latency introduced by internal processing in sample units. |
| `view` | `Live.Device.Device.View` | read-only | No | GUI view controls for the device. |
| `available_input_routing_channels` | `tuple[str]` | read-only | Yes | Available sidechain input channels. |
| `available_input_routing_types` | `tuple[str]` | read-only | Yes | Available sidechain input routing source types. |
| `input_routing_channel` | `str` | read/write | Yes | Currently selected sidechain routing channel. |
| `input_routing_type` | `str` | read/write | Yes | Currently selected sidechain routing type. |

---

### `Live.HybridReverbDevice.HybridReverbDevice`
- **C++ Handle:** `THybridReverbDevicePyHandle`
- **Canonical Parent:** `Live.Track.Track | Live.Chain.Chain`
- **Docstring:** _This class represents a Hybrid Reverb device in Live._

Convolution and algorithmic hybrid reverberation device with impulse response file browsing and time-shaping controls.

#### Properties

| Property | Type | Access | Listener | Description |
|---|---|---|---|---|
| `canonical_parent` | `Live.Track.Track | Live.Chain.Chain` | read-only | No | Track or Chain that owns this device instance. |
| `name` | `str` | read/write | Yes | User-editable display name of this Hybrid Reverb device instance. |
| `class_name` | `str` | read-only | No | Internal Ableton class identifier ('HybridReverb'). |
| `class_display_name` | `str` | read-only | No | Canonical UI name of the device type ('Hybrid Reverb'). |
| `type` | `DeviceType` | read-only | No | Device category (audio_effect). |
| `is_active` | `bool` | read/write | Yes | Device device-activator (on/off toggle). |
| `parameters` | `tuple[Live.DeviceParameter.DeviceParameter]` | read-only | Yes | Tuple of all controllable automation parameters. |
| `can_have_chains` | `bool` | read-only | No | Whether the device can contain nested chains. |
| `can_have_drum_pads` | `bool` | read-only | No | Whether the device can host drum pads. |
| `latency_in_ms` | `float` | read-only | Yes | Latency introduced by internal processing in milliseconds. |
| `latency_in_samples` | `int` | read-only | Yes | Latency introduced by internal processing in sample units. |
| `view` | `Live.Device.Device.View` | read-only | No | GUI view controls for the device. |
| `ir_attack_time` | `float` | read/write | Yes | Impulse response envelope attack time in ms. |
| `ir_decay_time` | `float` | read/write | Yes | Impulse response envelope decay time in ms. |
| `ir_size_factor` | `float` | read/write | Yes | Impulse response duration scaling factor. |
| `ir_time_shaping_on` | `bool` | read/write | Yes | Whether impulse response time-shaping EQ/envelope is enabled. |
| `ir_category_list` | `list[str]` | read-only | No | List of available impulse response categories. |
| `ir_category_index` | `int` | read/write | Yes | Selected impulse response category index. |
| `ir_file_list` | `list[str]` | read-only | No | List of available impulse response files in current category. |
| `ir_file_index` | `int` | read/write | Yes | Selected impulse response file index. |

---

### `Live.LooperDevice.LooperDevice`
- **C++ Handle:** `TLooperDevicePyHandle`
- **Canonical Parent:** `Live.Track.Track | Live.Chain.Chain`
- **Docstring:** _This class represents a Looper device in Live._

Real-time audio looper device supporting overdubbing, reverse, speed modification, and direct export to Session clip slots.

#### Properties

| Property | Type | Access | Listener | Description |
|---|---|---|---|---|
| `canonical_parent` | `Live.Track.Track | Live.Chain.Chain` | read-only | No | Track or Chain that owns this device instance. |
| `name` | `str` | read/write | Yes | User-editable display name of this Looper device instance. |
| `class_name` | `str` | read-only | No | Internal Ableton class identifier ('Looper'). |
| `class_display_name` | `str` | read-only | No | Canonical UI name of the device type ('Looper'). |
| `type` | `DeviceType` | read-only | No | Device category (audio_effect). |
| `is_active` | `bool` | read/write | Yes | Device device-activator (on/off toggle). |
| `parameters` | `tuple[Live.DeviceParameter.DeviceParameter]` | read-only | Yes | Tuple of all controllable automation parameters. |
| `can_have_chains` | `bool` | read-only | No | Whether the device can contain nested chains. |
| `can_have_drum_pads` | `bool` | read-only | No | Whether the device can host drum pads. |
| `latency_in_ms` | `float` | read-only | Yes | Latency introduced by internal processing in milliseconds. |
| `latency_in_samples` | `int` | read-only | Yes | Latency introduced by internal processing in sample units. |
| `view` | `Live.Device.Device.View` | read-only | No | GUI view controls for the device. |
| `loop_length` | `float` | read-only | Yes | Current loop length in beats. |
| `tempo` | `float` | read-only | Yes | Detected loop tempo in BPM. |
| `record_length_list` | `list[str]` | read-only | No | List of quantized loop recording length options (1 bar, 2 bars, etc.). |
| `record_length_index` | `int` | read/write | Yes | Index of selected recording length quantization. |

#### Methods

##### `clear() -> None`
Clears recorded audio in the buffer.

##### `play() -> None`
Starts loop playback.

##### `record() -> None`
Initiates recording into empty looper or begins overdub.

##### `overdub() -> None`
Engages overdub layer recording.

##### `stop() -> None`
Stops looper playback.

##### `undo() -> None`
Undoes the most recent overdub take.

##### `double_length() -> None`
Doubles the current loop buffer length.

##### `half_length() -> None`
Halves the current loop buffer length.

##### `double_speed() -> None`
Plays loop at double speed (pitch shifted up one octave).

##### `half_speed() -> None`
Plays loop at half speed (pitch shifted down one octave).

##### `export_to_clip_slot(clip_slot: Live.ClipSlot.ClipSlot) -> None`
Exports the recorded loop audio buffer directly into a Session view clip slot.

---

### `Live.Eq8Device.Eq8Device`
- **C++ Handle:** `TEq8DevicePyHandle`
- **Canonical Parent:** `Live.Track.Track | Live.Chain.Chain`
- **Docstring:** _This class represents an EQ Eight device in Live._

Eight-band parametric equalizer device with stereo, left/right, and mid/side processing modes and high-resolution oversampling.

#### Properties

| Property | Type | Access | Listener | Description |
|---|---|---|---|---|
| `canonical_parent` | `Live.Track.Track | Live.Chain.Chain` | read-only | No | Track or Chain that owns this device instance. |
| `name` | `str` | read/write | Yes | User-editable display name of this EQ Eight device instance. |
| `class_name` | `str` | read-only | No | Internal Ableton class identifier ('Eq8'). |
| `class_display_name` | `str` | read-only | No | Canonical UI name of the device type ('EQ Eight'). |
| `type` | `DeviceType` | read-only | No | Device category (audio_effect). |
| `is_active` | `bool` | read/write | Yes | Device device-activator (on/off toggle). |
| `parameters` | `tuple[Live.DeviceParameter.DeviceParameter]` | read-only | Yes | Tuple of all controllable automation parameters. |
| `can_have_chains` | `bool` | read-only | No | Whether the device can contain nested chains. |
| `can_have_drum_pads` | `bool` | read-only | No | Whether the device can host drum pads. |
| `latency_in_ms` | `float` | read-only | Yes | Latency introduced by internal processing in milliseconds. |
| `latency_in_samples` | `int` | read-only | Yes | Latency introduced by internal processing in sample units. |
| `view` | `Live.Eq8Device.Eq8Device.View` | read-only | No | EQ Eight device view object. |
| `edit_mode` | `int` | read/write | Yes | Edit mode: Stereo (0), Left/Right (1), Mid/Side (2). |
| `global_mode` | `int` | read/write | Yes | Global filter processing configuration mode. |
| `oversample` | `bool` | read/write | Yes | Enables 2x oversampling mode for improved high-frequency phase linearity. |

---

### `Live.DrumCellDevice.DrumCellDevice`
- **C++ Handle:** `TDrumCellDevicePyHandle`
- **Canonical Parent:** `Live.DrumChain.DrumChain`
- **Docstring:** _This class represents a Drum Cell instrument device in Live._

Dedicated single-pad drum synthesis instrument module used in Ableton Drum Racks.

#### Properties

| Property | Type | Access | Listener | Description |
|---|---|---|---|---|
| `canonical_parent` | `Live.Track.Track | Live.Chain.Chain` | read-only | No | Track or Chain that owns this device instance. |
| `name` | `str` | read/write | Yes | User-editable display name of this Drum Cell device instance. |
| `class_name` | `str` | read-only | No | Internal Ableton class identifier ('DrumCell'). |
| `class_display_name` | `str` | read-only | No | Canonical UI name of the device type ('Drum Cell'). |
| `type` | `DeviceType` | read-only | No | Device category (instrument). |
| `is_active` | `bool` | read/write | Yes | Device device-activator (on/off toggle). |
| `parameters` | `tuple[Live.DeviceParameter.DeviceParameter]` | read-only | Yes | Tuple of all controllable automation parameters. |
| `can_have_chains` | `bool` | read-only | No | Whether the device can contain nested chains. |
| `can_have_drum_pads` | `bool` | read-only | No | Whether the device can host drum pads. |
| `latency_in_ms` | `float` | read-only | Yes | Latency introduced by internal processing in milliseconds. |
| `latency_in_samples` | `int` | read-only | Yes | Latency introduced by internal processing in sample units. |
| `view` | `Live.Device.Device.View` | read-only | No | GUI view controls for the device. |
| `gain` | `float` | read/write | Yes | Pad output trim gain in dB. |

---

### `Live.PluginDevice.PluginDevice`
- **C++ Handle:** `TPluginDevicePyHandle`
- **Canonical Parent:** `Live.Track.Track | Live.Chain.Chain`
- **Docstring:** _This class represents a third-party VST, VST3, or Audio Unit (AU) plugin in Live._

Third-party audio effect or software instrument plugin host interface, providing preset selection, parameter automation, and custom editor window toggling.

#### Properties

| Property | Type | Access | Listener | Description |
|---|---|---|---|---|
| `canonical_parent` | `Live.Track.Track | Live.Chain.Chain` | read-only | No | Track or Chain that owns this device instance. |
| `name` | `str` | read/write | Yes | User-editable display name of this Plugin device instance. |
| `class_name` | `str` | read-only | No | Internal Ableton class identifier ('PluginDevice'). |
| `class_display_name` | `str` | read-only | No | Canonical UI name of the device type ('Plugin'). |
| `type` | `DeviceType` | read-only | No | Device category (undefined). |
| `is_active` | `bool` | read/write | Yes | Device device-activator (on/off toggle). |
| `parameters` | `tuple[Live.DeviceParameter.DeviceParameter]` | read-only | Yes | Tuple of all controllable automation parameters. |
| `can_have_chains` | `bool` | read-only | No | Whether the device can contain nested chains. |
| `can_have_drum_pads` | `bool` | read-only | No | Whether the device can host drum pads. |
| `latency_in_ms` | `float` | read-only | Yes | Latency introduced by internal processing in milliseconds. |
| `latency_in_samples` | `int` | read-only | Yes | Latency introduced by internal processing in sample units. |
| `view` | `Live.Device.Device.View` | read-only | No | GUI view controls for the device. |
| `is_editor_open` | `bool` | read/write | Yes | Whether the native third-party plugin GUI window is open. |
| `presets` | `tuple[str]` | read-only | Yes | Tuple of factory/user preset names exposed by the plugin. |
| `selected_preset_index` | `int` | read/write | Yes | Zero-based index of the currently active plugin preset. |

---

### `Live.Song.CuePoint`
- **C++ Handle:** `TPyHandle<ACuePoint>`
- **Canonical Parent:** `Live.Song.Song`
- **Docstring:** _Represents an Arrangement locator cue point in Live._

Arrangement timeline locator mark used for transport jumping, section markers, and timeline rehearsal navigation.

#### Properties

| Property | Type | Access | Listener | Description |
|---|---|---|---|---|
| `name` | `str` | read/write | Yes | Name / label of the cue point locator. |
| `time` | `float` | read/write | Yes | Arrangement timeline position in beats. |
| `canonical_parent` | `Live.Song.Song` | read-only | No | Song instance owning this cue point. |

#### Methods

##### `jump() -> None`
Jumps playback transport immediately to this cue point locator's beat position.

---

### `Live.Groove.Groove`
- **C++ Handle:** `TPyHandle<AAbstractGroove>`
- **Canonical Parent:** `Live.GroovePool.GroovePool`
- **Docstring:** _Represents an individual groove preset in the Groove Pool._

Swing, timing, velocity, and randomization groove template applied non-destructively to MIDI and audio clips.

#### Properties

| Property | Type | Access | Listener | Description |
|---|---|---|---|---|
| `name` | `str` | read/write | Yes | Name of the groove preset. |
| `base` | `int` | read/write | Yes | Base groove timing division (e.g. 8th, 16th). |
| `timing_amount` | `float` | read/write | Yes | Amount of timing deviation applied (0.0 to 1.0). |
| `velocity_amount` | `float` | read/write | Yes | Amount of velocity variation applied (0.0 to 1.0). |
| `quantization_amount` | `float` | read/write | Yes | Pre-groove straight quantization intensity (0.0 to 1.0). |
| `random_amount` | `float` | read/write | Yes | Random timing jitter intensity (0.0 to 1.0). |
| `canonical_parent` | `Live.GroovePool.GroovePool` | read-only | No | GroovePool instance owning this groove. |

---

### `Live.DrumChain.DrumChain`
- **C++ Handle:** `TDrumChainPyHandle`
- **Canonical Parent:** `Live.DrumPad.DrumPad`
- **Docstring:** _This class represents a drum group device chain in Live._

Specialized branch chain nested inside a Drum Rack pad, featuring incoming trigger note, outgoing device note, and choke group assignment.

#### Properties

| Property | Type | Access | Listener | Description |
|---|---|---|---|---|
| `canonical_parent` | `Live.DrumPad.DrumPad` | read-only | No | DrumPad instance owning this chain. |
| `name` | `str` | read/write | Yes | Name of the drum chain. |
| `color` | `int` | read/write | Yes | RGB color integer of the drum chain. |
| `color_index` | `int` | read/write | Yes | Live palette color index. |
| `is_auto_colored` | `bool` | read/write | Yes | Whether chain color automatically follows parent pad. |
| `mute` | `bool` | read/write | Yes | Mute state of the drum chain. |
| `solo` | `bool` | read/write | Yes | Solo state of the drum chain. |
| `muted_via_solo` | `bool` | read-only | Yes | True if muted as a consequence of another chain being soloed. |
| `in_note` | `int` | read/write | Yes | Access to the incoming MIDI note that will trigger this chain (0-127). |
| `out_note` | `int` | read/write | Yes | Access to the MIDI note sent to the devices in the chain (0-127). |
| `choke_group` | `int` | read/write | Yes | Access to the chain's choke group setting (0 = off, 1-16). |
| `devices` | `tuple[Live.Device.Device]` | read-only | Yes | Tuple of devices hosted within this chain. |
| `mixer_device` | `Live.ChainMixerDevice.ChainMixerDevice` | read-only | No | Chain mixer device controlling volume, panning, and sends. |
| `has_audio_input` | `bool` | read-only | No | Whether chain receives audio input. |
| `has_audio_output` | `bool` | read-only | No | Whether chain produces audio output. |
| `has_midi_input` | `bool` | read-only | No | Whether chain receives MIDI input. |
| `has_midi_output` | `bool` | read-only | No | Whether chain produces MIDI output. |

#### Methods

##### `insert_device(index: int = -1) -> Live.Device.Device`
Inserts a new device at index into the chain.

##### `delete_device(index: int) -> None`
Deletes the device at index from the chain.

---

### `Live.DeviceIO.DeviceIO`
- **C++ Handle:** `TPyHandle<AMxDRoutable>`
- **Canonical Parent:** `Live.Track.Track | Live.Device.Device`
- **Docstring:** _Represents audio/MIDI input or output routing configuration for tracks and devices._

Exposes available audio/MIDI routing types and channels, allowing programmatic input/output patchbay reconfiguration.

#### Properties

| Property | Type | Access | Listener | Description |
|---|---|---|---|---|
| `canonical_parent` | `Any` | read-only | No | Object owning this routing terminal. |
| `routing_type` | `str` | read/write | Yes | Current routing type string. |
| `routing_channel` | `str` | read/write | Yes | Current routing channel string. |
| `available_routing_types` | `tuple[str]` | read-only | Yes | Tuple of valid routing type options. |
| `available_routing_channels` | `tuple[str]` | read-only | Yes | Tuple of valid routing channel options. |
| `default_external_routing_channel_is_none` | `bool` | read-only | No | True if external routing defaults to no channel. |

---

### `Live.ChainMixerDevice.ChainMixerDevice`
- **C++ Handle:** `TPyHandle<ABranchMixerDevice>`
- **Canonical Parent:** `Live.Chain.Chain | Live.DrumChain.DrumChain`
- **Docstring:** _Represents the mixer section of a Rack chain or Drum Pad chain._

Controls chain volume attenuation, stereo panning, chain mute/activator toggle, and internal rack send bus levels.

#### Properties

| Property | Type | Access | Listener | Description |
|---|---|---|---|---|
| `canonical_parent` | `Live.Chain.Chain` | read-only | No | Chain instance owning this mixer. |
| `volume` | `Live.DeviceParameter.DeviceParameter` | read-only | No | Chain output volume parameter. |
| `panning` | `Live.DeviceParameter.DeviceParameter` | read-only | No | Chain stereo panning parameter. |
| `chain_activator` | `Live.DeviceParameter.DeviceParameter` | read-only | No | Chain on/off speaker activator parameter. |
| `sends` | `tuple[Live.DeviceParameter.DeviceParameter]` | read-only | Yes | Tuple of send parameters routing signal to rack return chains. |

---

## 5. Live 12 Extended Subsystems & Specialized APIs

### 5.1 TakeLane Comping API
In Live 12, arrangement take lanes are exposed via `track.take_lanes` and `track.create_take_lane()`. Each take lane supports programmatic clip creation:
```python
# Create take lane on MIDI track
take_lane = track.create_take_lane()
take_lane.name = 'Vocal Lead Comp 01'

# Insert MIDI clip directly into take lane
clip = take_lane.create_midi_clip(time=0.0, length=4.0)

# Insert Audio clip referencing sample on disk
audio_clip = take_lane.create_audio_clip(file_path='/path/to/take.wav', time=16.0)

# Store persistent metadata with Set save/load
take_lane.set_data('take_rating', 5)
assert take_lane.get_data('take_rating', 0) == 5
```

### 5.2 Extended MIDI Note Model
Live 12 replaces the legacy 5-tuple note format with rich objects (`MidiNote` and `MidiNoteSpecification`).

```python
from Live.Clip import MidiNoteSpecification

# Construct new notes with probability and velocity deviation
notes = [
    MidiNoteSpecification(
        pitch=60,
        start_time=0.0,
        duration=0.5,
        velocity=100.0,
        velocity_deviation=15.0,  # Randomization range
        probability=0.85,         # 85% trigger probability
        release_velocity=64.0,
        mute=False
    ),
    MidiNoteSpecification(pitch=64, start_time=0.5, duration=0.5, probability=0.5)
]
clip.add_new_notes(notes)

# Query existing notes
retrieved_notes = clip.get_notes_extended(from_pitch=0, pitch_span=128, from_time=0.0, time_span=4.0)

# In-place modification preserving per-note MPE expressions
for n in retrieved_notes:
    n.velocity = 115.0
    n.probability = 1.0
clip.apply_note_modifications(retrieved_notes)
```

### 5.3 Microtonal Tuning & Project Scales
Live 12 natively supports microtonal `.ascl` and `.tun` tuning files:
```python
song = Live.Application.get_application().get_document()
print('Scale Mode:', song.scale_mode)
print('Root Note:', song.root_note)  # 0 = C
print('Scale Name:', song.scale_name)
print('Scale Intervals:', song.scale_information)

tuning = song.tuning_system
if tuning:
    print('Tuning System:', tuning.name)
    print('Notes in Pseudo-Octave:', tuning.number_of_notes_in_pseudo_octave)
    print('Pseudo-Octave Cents:', tuning.pseudo_octave_in_cents)
    print('Reference Pitch:', tuning.reference_pitch)
    print('Cents Tunings:', tuning.note_tunings)
```

### 5.4 Native Modal Dialog Automation
In-LOM modal dialog inspection and dismissal via `Live.Application`:
```python
app = Live.Application.get_application()
if app.open_dialog_count > 0:
    msg = app.current_dialog_message
    btn_count = app.current_dialog_button_count
    print(f'Active Dialog ({btn_count} buttons): {msg}')
    # Programmatically press button 0 (OK / Confirm)
    app.press_current_dialog_button(0)
```

### 5.5 Wavetable Modulation Matrix API
Programmatic matrix routing for `Live.WavetableDevice`:
```python
from Live.WavetableDevice import ModulationSource

wavetable = track.devices[0]
targets = wavetable.visible_modulation_target_names
print('Visible targets:', targets)

# Check if filter cutoff is modulatable and set modulation
param = wavetable.parameters[5]  # Filter Cutoff
if wavetable.is_parameter_modulatable(param):
    wavetable.add_parameter_to_modulation_matrix(param)
    # Set LFO 1 -> Cutoff modulation to 0.75
    wavetable.set_modulation_value(ModulationSource.lfo_1, target_index=0, value=0.75)
    current_mod = wavetable.get_modulation_value(ModulationSource.lfo_1, target_index=0)
```

---

## 6. Enums Catalog

### `DeviceType`
`audio_effect, midi_effect, instrument, undefined`

### `PlaybackMode`
`classic, one_shot, slicing`

### `SlicingStyle`
`transient, beat, region, manual`

### `SlicingBeatGrid`
`1/32, 1/24, 1/16, 1/12, 1/8, 1/6, 1/4, 1/2, 1 Bar`

### `SlicingBeatDivision`
`1/32, 1/24, 1/16, 1/12, 1/8, 1/6, 1/4, 1/2, 1 Bar`

### `WarpMode`
`beats, tones, texture, repitch, complex, complex_pro`

### `LaunchMode`
`trigger, gate, toggle, repeat`

### `LaunchQuantization`
`none, 8_bars, 4_bars, 2_bars, 1_bar, half, half_triplet, quarter, quarter_triplet, eighth, eighth_triplet, sixteenth, sixteenth_triplet, thirtysecond`

### `AutomationState`
`none, playing, overridden`

### `ParameterState`
`enabled, irrelevant, disabled`

### `OscEffectMode`
`none, fm, classic, modern`

### `UnisonMode`
`classic, shimmer, ripple`

### `FilterRouting`
`serial, parallel, split`

### `PanMode`
`classic, split_stereo`

### `RoutingChannelLayout`
`mono, stereo`

### `ClipSlotPlayingState`
`stopped, playing, recording`

### `RecordingQuantization`
`none, quarter, eighth, eighth_triplet, eighth_and_triplet, sixteenth, sixteenth_triplet, sixteenth_and_triplet, thirtysecond`

### `ViewIdentifier`
`Session, Arranger, Detail, Detail/Clip, Detail/DeviceChain, Browser`

### `CrossfadeAssign`
`None, A, B`

### `ScaleMode`
`Major, Minor, Dorian, Mixolydian, Lydian, Phrygian, Locrian, Minor_Pentatonic, Major_Pentatonic, Harmonic_Minor, Melodic_Minor, Whole_Tone`

### `CaptureDestination`
`auto, focused_track, selected_clip_slot`

### `DialogButton`
`OK, Cancel, Save, DontSave, Yes, No`

### `AudioFileFormat`
`wav, aif, flac`

### `NoteSpecificationFormat`
`dict, object`

### `SampleSlicingPlaybackMode`
`poly, mono, through`

### `DeviceInsertMode`
`selected_left, selected_right, default`

### `Relation`
`ancestor, equal, descendant`

### `DriftVoiceMode`
`poly, mono, stereo, unison`
