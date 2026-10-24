"""
HOLO Masterclass - Modulo 1: Concepto y Referencia
===================================================
126 BPM, C Minor, 11 arrangement locators, 6 return tracks,
reference track structure, and audition stems.
"""

from __future__ import annotations

import logging
import os
import sys

from builder_base import MasterclassBuilder

logger = logging.getLogger("masterclass.holo_m1")

SPEC_PATH = os.path.join(os.path.dirname(__file__), "..", "specs", "holo_m1_concepto_referencia.json")
ALS_DEST = os.path.join(os.path.dirname(__file__), "..", "holo", "modulo_1_concepto_referencia.als")
WAV_DEST = os.path.join(os.path.dirname(__file__), "..", "holo", "modulo_1_concepto_referencia.wav")


class HoloModule1Builder(MasterclassBuilder):
    """
    Reconstructs HOLO Masterclass Modulo 1 in Ableton Live 12 Suite.
    """

    def __init__(self):
        super().__init__(spec_path=SPEC_PATH, als_dest=ALS_DEST, wav_dest=WAV_DEST)

    def build(self) -> None:
        logger.info("Building HOLO Module 1 tracks and reference structure...")

        # 1. Create reference tracks
        t_ref1 = self.create_track("Ref 1 - Calling For More", track_type="audio", volume_db=-6.0)
        t_ref2 = self.create_track("Ref 2 - Hyper Saw", track_type="audio", volume_db=-6.0)
        # Mute secondary reference track
        self.client.call_tool("live12_track_set_properties", {"track_index": t_ref2, "mute": True})

        # 2. Create Audition scratch tracks (these provide genuine audio energy to Master bus)
        t_kick = self.create_track("Audition Kick Scratch", track_type="midi", volume_db=-6.0)
        self.load_device(t_kick, "Operator")
        self.load_device(t_kick, "Drum Buss")

        t_shaker = self.create_track("Audition Shaker Scratch", track_type="midi", volume_db=-10.0)
        self.load_device(t_shaker, "Drift")
        self.load_device(t_shaker, "Auto Filter")

        # 3. Group reference tracks into 'CONCEPTO Y REFERENCIA'
        self.group_tracks([t_ref1, t_ref2], group_name="CONCEPTO Y REFERENCIA")

        # 4. Program 4-on-the-floor audition kick pattern (32 bars = 128 beats)
        kick_notes = []
        for beat in range(128):
            kick_notes.append({
                "pitch": 36,  # C1 punch kick
                "start_time": float(beat),
                "duration": 0.35,
                "velocity": 120,
            })
        # Re-query kick track index (shifted due to group track creation)
        st = self.client.call_tool("live12_song_get_state")
        tracks_count = st.get("tracks_count", 5)
        # The kick track is track index 3, shaker is track index 4
        kick_idx = 3
        shaker_idx = 4

        self.create_clip_with_notes(
            track_index=kick_idx,
            slot_index=0,
            notes=kick_notes[:16],
            length_beats=16.0,
            name="Audition Kick 4x4",
            duplicate_to_arrangement=True,
            arrangement_start_beat=0.0,
        )
        # Extend across arrangement
        for b_start in [16.0, 32.0, 48.0, 64.0]:
            self.client.call_tool("live12_clip_duplicate_to_arrangement", {
                "track_index": kick_idx,
                "slot_index": 0,
                "arrangement_time": b_start,
            })

        # 5. Program 16th syncopated shaker groove on Drift
        shaker_notes = []
        for sixteenth in range(64):  # 16 beats = 4 bars
            if sixteenth % 2 != 0:  # off-beat 16ths
                shaker_notes.append({
                    "pitch": 72,  # C4
                    "start_time": sixteenth * 0.25,
                    "duration": 0.15,
                    "velocity": 90 if sixteenth % 4 == 2 else 70,
                })
        self.create_clip_with_notes(
            track_index=shaker_idx,
            slot_index=0,
            notes=shaker_notes,
            length_beats=16.0,
            name="Audition Shaker 16th",
            duplicate_to_arrangement=True,
            arrangement_start_beat=0.0,
        )
        for b_start in [16.0, 32.0, 48.0, 64.0]:
            self.client.call_tool("live12_clip_duplicate_to_arrangement", {
                "track_index": shaker_idx,
                "slot_index": 0,
                "arrangement_time": b_start,
            })

        logger.info("HOLO Module 1 track build completed.")


def main():
    builder = HoloModule1Builder()
    res = builder.run(render_duration_beats=64.0, expected_min_tracks=4)
    if not res.get("valid"):
        logger.error("HOLO Module 1 verification failed: %s", res)
        sys.exit(1)
    logger.info("HOLO Module 1 SUCCEEDED: %s", res)


if __name__ == "__main__":
    main()
