#!/usr/bin/env python3
"""Inspect the live Ableton Live 12 set through the Live12Bridge.

Read-only snapshot of the running instance: song meta, per-track
name/color/mixer values, device chains and arrangement clips.

Usage:
    PYTHONPATH=src python3 scripts/inspect_live_set.py [--json]
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from ableton_live12_mcp.client import Live12Client  # noqa: E402


def _norm_to_db(norm: float) -> float:
    """Live normalized mixer volume -> dB.

    Live's volume curve is `normalized = 0.85 * 10 ** (dB / 40)`, i.e. 0.85 is
    unity (the Main track sits exactly there), so the inverse is
    `dB = 40 * log10(normalized / 0.85)`.
    """
    if norm is None or norm <= 0.0:
        return -120.0
    return round(40.0 * math.log10(norm / 0.85), 1)


def _mixer(client: Live12Client, track_index: int, prop: str):
    try:
        return client.call(
            "live12_lom_get",
            {"target_path": f"song.tracks.{track_index}.mixer_device.{prop}", "property_name": "value"},
        ).get("value")
    except Exception:
        return None


def snapshot(client: Live12Client | None = None) -> dict:
    c = client or Live12Client()

    def g(path: str, prop: str):
        try:
            return c.call("live12_lom_get", {"target_path": path, "property_name": prop}).get("value")
        except Exception:
            return None

    song = {
        "name": g("song", "name"),
        "tempo": g("song", "tempo"),
        "current_song_time": g("song", "current_song_time"),
        "loop_start": g("song", "loop_start"),
        "loop_end": g("song", "loop_end"),
        "scale_name": g("song", "scale_name"),
        "scale_root": g("song", "scale_root"),
    }

    tracks = []
    try:
        n_tracks = len(c.call("live12_lom_get", {"target_path": "song.tracks", "property_name": "tracks"}).get("value") or [])
    except Exception:
        n_tracks = 0
    if n_tracks == 0:
        for i in range(64):
            if g(f"song.tracks.{i}", "name") is None:
                break
            n_tracks = i + 1

    for i in range(n_tracks):
        vol = _mixer(c, i, "volume")
        pan = _mixer(c, i, "panning")
        try:
            devices = c.call("live12_device_list", {"track_index": i}).get("devices", [])
        except Exception:
            devices = []
        clips = []
        raw_clips = g(f"song.tracks.{i}", "arrangement_clips") or []
        for j in range(len(raw_clips)):
            st = g(f"song.tracks.{i}.arrangement_clips.{j}", "start_time")
            et = g(f"song.tracks.{i}.arrangement_clips.{j}", "end_time")
            nm = g(f"song.tracks.{i}.arrangement_clips.{j}", "name")
            cl = g(f"song.tracks.{i}.arrangement_clips.{j}", "color_index")
            clips.append({
                "index": j,
                "name": nm,
                "start_beat": st,
                "end_beat": et,
                "color_index": cl,
            })
        tracks.append({
            "index": i,
            "name": g(f"song.tracks.{i}", "name"),
            "color_index": g(f"song.tracks.{i}", "color_index"),
            "mute": g(f"song.tracks.{i}", "mute"),
            "solo": g(f"song.tracks.{i}", "solo"),
            "volume": vol,
            "volume_db": _norm_to_db(vol),
            "panning": pan,
            "devices": [{"index": d.get("index"), "name": d.get("name")} for d in devices],
            "clips": clips,
        })

    return {"song": song, "tracks": tracks}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="raw JSON output")
    args = ap.parse_args()

    snap = snapshot()
    if args.json:
        print(json.dumps(snap, ensure_ascii=False, indent=2))
        return 0

    s = snap["song"]
    print(f"Song      : {s['name']}  |  {s['tempo']} BPM  |  scale {s['scale_root']} {s['scale_name']}")
    print(f"Loop      : {s['loop_start']} .. {s['loop_end']} beats | time {s['current_song_time']}")
    print(f"Tracks    : {len(snap['tracks'])}")
    print("-" * 100)
    for t in snap["tracks"]:
        devs = ", ".join(str(d["name"]) for d in t["devices"]) or "-"
        print(f"[{t['index']:2d}] {str(t['name'])[:40]:40s} color={t['color_index']:>3} "
              f"vol={t['volume_db']:>7} dB pan={t['panning']:+.2f} "
              f"clips={len(t['clips']):2d} | {devs[:44]}")
        for cl in t["clips"]:
            sb, eb = cl["start_beat"], cl["end_beat"]
            print(f"       - c.{int((sb or 0) // 4) + 1:>2}  {str(cl['name'])[:52]:52s} "
                  f"({sb}..{eb})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
