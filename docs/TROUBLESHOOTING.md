# Troubleshooting — Ableton Live 12 MCP

Operational notes collected while driving a live **Ableton Live 12.4.6 Suite** instance
through this MCP server. Every recipe below was verified against the running app.

---

## 1. The test suite mutates the live set unless you force mock mode

`tests/harness.py` auto-detects a reachable bridge (`127.0.0.1:11246`). If Live is open,
`pytest` runs **against the live instance**: it creates `__agy_test_*` tracks, rewrites the
song tempo/scale, and can leave stray arrangement clips behind.

```bash
# ALWAYS run the suite in mock mode when Live is open
ABLETON_TEST_MODE=mock python3 -m pytest tests/ -q
```

Recovery after an accidental live run:

```bash
PYTHONPATH=src python3 scripts/inspect_live_set.py          # snapshot of tracks/clips/colors
PYTHONPATH=src python3 -c "
from ableton_live12_mcp.client import Live12Client
c = Live12Client()
c.call('live12_transport_set_tempo', {'tempo': 138.0})
c.call('live12_song_set_scale', {'root_note': 7, 'scale_name': 'Phrygian'})"
```

Stray arrangement clips are removed with the `live12_clip_delete_arrangement` tool
(Session-view clips and arrangement clips need different tools).

---

## 2. Live burns a full CPU core: the bridge timer interval

`Live.Base.Timer` callbacks are dispatched on Ableton's **main thread**. A 5 ms interval
(200 ticks/s) keeps the main thread permanently scheduled and costs **~60 % of a CPU core
inside Live** — with a starved engine, meters stay at `-∞` and renders come out silent.

The bridge now defaults to **20 ms** and the interval is configurable:

```bash
export LIVE12_BRIDGE_TIMER_MS=20     # 20 ms (default) — lower only if you need latency
```

Verify the effect:

```bash
PID=$(pgrep -f "Ableton Live 12 Suite.app/Contents/MacOS/Live")
top -l 3 -pid $PID -stats pid,cpu      # expect single-digit % when idle
```

The value in use is written to Live's log:
`grep "Live.Base.Timer active" ~/Library/Preferences/Ableton/Live\ 12.4.6/Log.txt | tail -1`

---

## 3. No sound in Live (meters stuck at `-∞`, renders silent)

Checklist, in order:

1. **System output muted** (macOS level, not Live):
   ```bash
   osascript -e 'get volume settings'      # output muted: true  ->  fix below
   osascript -e 'set volume output muted false'
   ```
2. **Wrong CoreAudio device**: Live 12 sometimes boots on a *Continuity* input device
   (`iPhone Microphone (1 In, 0 Out)`) that has no output at all.
   `Live ▸ Settings ▸ Audio ▸ Audio Output Device` → pick `MacBook Pro Speakers` or
   `Use System Device`. Confirm what Live actually opened:
   ```bash
   grep "Device init" ~/Library/Preferences/Ableton/Live\ 12.4.6/Log.txt | tail -3
   ```
3. **Another app holds the audio device**: an Android emulator (`qemu-system-aarch64`) or a
   `Virtualization.framework` VM steals the output stream. `coreaudiod` then reports an
   output RMS of about `-80 dB` while the input node is active:
   ```bash
   ps -Ao pid,%cpu,comm | sort -k2 -rn | head -5
   ```
   Stop the emulator/VM (or set its audio to *none*) and restart Live.
4. **Live 12.4.7 is pending** on this machine (`Downloading Live 12.4.7` in the status bar);
   the release notes mention audio fixes that may be required on recent macOS versions.

---

## 4. Driving Ableton's GUI when the AX tree is empty

Native dialogs (Save/Export sheets, Live's own panels) are sometimes not exposed through
Accessibility, so `System Events` cannot type into them. Use synthetic CoreGraphics events
instead — this works for every window, including Live-drawn panels:

```bash
cat > /tmp/click.js <<'EOF'
ObjC.import('CoreGraphics'); ObjC.import('Foundation');
function run(argv) {
  var pt = $.CGPointMake(parseFloat(argv[0]), parseFloat(argv[1]));
  $.CGEventPost($.kCGHIDEventTap, $.CGEventCreateMouseEvent(null, $.kCGEventMouseMoved, pt, $.kCGMouseButtonLeft));
  var down = $.CGEventCreateMouseEvent(null, $.kCGEventLeftMouseDown, pt, $.kCGMouseButtonLeft);
  $.CGEventPost($.kCGHIDEventTap, down);
  $.CGEventPost($.kCGHIDEventTap, $.CGEventCreateMouseEvent(null, $.kCGEventLeftMouseUp, pt, $.kCGMouseButtonLeft));
  return "clicked";
}
EOF
osascript -l JavaScript /tmp/click.js <x_points> <y_points>
```

Screen coordinates are **points** (retina: pixels ÷ 2), origin at the top-left of the main
display.

---

## 5. Export Audio/Video renders the wrong range

The export dialog keeps its own `Render Start` / `Render Length` fields (bars.beats.sixteenths)
and *does not* follow the arrangement loop. A length of `0.0.1` renders a single sixteenth.
Set the length explicitly (`68.1.1` = 68 bars = 272 beats at 4/4) before pressing *Export*,
otherwise the bounce is ~0.1 s and effectively silent.

`masterclasses/scripts/builder_base.py::export_audio_bounce` wraps this flow and converts
the AIFF result to 24-bit PCM WAV.

---

## 6. Useful one-liners

```bash
PYTHONPATH=src python3 scripts/inspect_live_set.py                    # full set snapshot
PYTHONPATH=src python3 scripts/measure_track_levels.py --start-beat 64  # per-track peaks
PYTHONPATH=src python3 masterclasses/scripts/organize_grid_and_export_html.py  # colors + HTML map
```
