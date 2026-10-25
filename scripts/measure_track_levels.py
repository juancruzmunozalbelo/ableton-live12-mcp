#!/usr/bin/env python3
"""Measure per-track output levels of the live Ableton set while it plays.

Usage:
    PYTHONPATH=src python3 scripts/measure_track_levels.py --start-beat 64 --seconds 8
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from ableton_live12_mcp.client import Live12Client  # noqa: E402


def _levels(value):
    """Live reports meter levels as {'left': x, 'right': y}; the bridge may flatten them."""
    if isinstance(value, dict):
        return [float(v) for v in value.values() if isinstance(v, (int, float))]
    if isinstance(value, (int, float)):
        return [float(value)]
    return []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start-beat", type=float, default=64.0)
    ap.add_argument("--seconds", type=float, default=8.0)
    ap.add_argument("--interval", type=float, default=0.05)
    ap.add_argument("--settle", type=float, default=3.0, help="seconds to let peak-hold decay after the seek")
    args = ap.parse_args()

    c = Live12Client()

    def g(path, prop="value"):
        try:
            return c.call("live12_lom_get", {"target_path": path, "property_name": prop}).get("value")
        except Exception:
            return None

    n_tracks = 0
    while g(f"song.tracks.{n_tracks}", "name") is not None:
        n_tracks += 1

    names = [str(g(f"song.tracks.{i}", "name")) for i in range(n_tracks)]
    peaks = [-120.0] * n_tracks
    master_peak = -120.0

    c.call("live12_transport_set_loop", {"enabled": False, "start": 0.0, "length": 4.0})
    # Stop first: Live's meter reading is a PEAK-HOLD value, so it must be reset
    # (transport stopped + a short pause) before measuring a new section.
    # Live 12 ignores a playhead move while the transport is stopped: the position
    # must be set WHILE playing (hot seek). Start, seek, then measure.
    c.call("live12_transport_play", {"restart": True})
    time.sleep(0.4)
    c.call("live12_lom_set", {"target_path": "song", "property_name": "current_song_time",
                              "value": float(args.start_beat)})
    # Live's meter reading is a PEAK-HOLD: let the peaks of the previous position
    # decay before sampling the new section.
    time.sleep(float(args.settle))

    deadline = time.time() + args.seconds
    while time.time() < deadline:
        for i in range(n_tracks):
            lvl = g(f"song.tracks.{i}", "output_meter_level")
            for v in _levels(lvl):
                if v > peaks[i]:
                    peaks[i] = v
        m = g("song.master_track", "output_meter_level")
        for v in _levels(m):
            if v > master_peak:
                master_peak = v
        time.sleep(args.interval)

    c.call("live12_transport_stop")

    print(f"Measured {args.seconds:.0f}s from beat {args.start_beat} | master peak {master_peak:.1f} dB")
    print("-" * 78)
    order = sorted(range(n_tracks), key=lambda i: peaks[i], reverse=True)
    for i in order:
        bar = "#" * max(0, int(peaks[i] + 60))
        print(f"[{i:2d}] {names[i][:44]:44s} peak {peaks[i]:7.1f} dB  {bar}")
    print("-" * 78)
    print(json.dumps({"peaks_db": peaks, "master_peak_db": master_peak}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
