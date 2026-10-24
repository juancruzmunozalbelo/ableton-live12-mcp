"""
HOLO Masterclass - Modulo 2: Groove y Baterías
===============================================
126 BPM, C Minor, Drum programming: punch kick, Mau5 sub body,
16th rumble chain, clap-snare, shaker, hi-hats, drum rack aux perc,
16th swing, and group bus processing.
"""

from __future__ import annotations

import logging
import os
import sys

from builder_base import MasterclassBuilder

logger = logging.getLogger("masterclass.holo_m2")

SPEC_PATH = os.path.join(os.path.dirname(__file__), "..", "specs", "holo_m2_groove_baterias.json")
ALS_DEST = os.path.join(os.path.dirname(__file__), "..", "holo", "modulo_2_groove_baterias.als")
WAV_DEST = os.path.join(os.path.dirname(__file__), "..", "holo", "modulo_2_groove_baterias.wav")


class HoloModule2Builder(MasterclassBuilder):
    """
    Reconstructs HOLO Masterclass Modulo 2 in Ableton Live 12 Suite.
    """

    def __init__(self):
        super().__init__(spec_path=SPEC_PATH, als_dest=ALS_DEST, wav_dest=WAV_DEST)

    def build(self) -> None:
        logger.info("Building HOLO Module 2 drum stems and groove chains...")

        # 1. Create drum tracks
        t_kick_p = self.create_track("Kick Punch", track_type="midi", volume_db=-4.0)
        self.load_device(t_kick_p, "Operator")
        self.load_device(t_kick_p, "Drum Buss")
        self.load_device(t_kick_p, "EQ Eight")

        t_kick_b = self.create_track("Kick Sub Body", track_type="midi", volume_db=-9.0)
        self.load_device(t_kick_b, "Operator")
        self.load_device(t_kick_b, "Auto Filter")

        t_rumble = self.create_track("Kick Sub Rumble", track_type="midi", volume_db=-7.5)
        self.load_device(t_rumble, "Operator")
        self.load_device(t_rumble, "Delay")
        self.load_device(t_rumble, "Reverb")
        self.load_device(t_rumble, "Saturator")
        self.load_device(t_rumble, "Utility")

        t_clap = self.create_track("Clap-Snare Main", track_type="midi", volume_db=-8.0)
        self.load_device(t_clap, "Drift")
        self.load_device(t_clap, "EQ Eight")

        t_shaker = self.create_track("Shaker Loop 16th", track_type="midi", volume_db=-13.0)
        self.load_device(t_shaker, "Drift")
        self.load_device(t_shaker, "Auto Filter")

        t_hats = self.create_track("Hi-Hats Offbeat & 16th", track_type="midi", volume_db=-11.0)
        self.load_device(t_hats, "Drift")
        self.load_device(t_hats, "Delay")

        t_aux = self.create_track("Drum Rack Aux Perc", track_type="midi", volume_db=-10.0)
        self.load_device(t_aux, "Operator")
        self.load_device(t_aux, "Reverb")

        t_top = self.create_track("PERCUSSIVE Top Loop", track_type="midi", volume_db=-14.0)
        self.load_device(t_top, "Drift")
        self.load_device(t_top, "Auto Filter")

        # 2. Group all 8 drum tracks into 'DRUMS'
        drum_indices = [t_kick_p, t_kick_b, t_rumble, t_clap, t_shaker, t_hats, t_aux, t_top]
        grp_idx = self.group_tracks(drum_indices, group_name="DRUMS")
        self.load_device(grp_idx, "Glue Compressor")
        self.load_device(grp_idx, "EQ Eight")

        # 3. Program Drum Patterns & Duplicate to Arrangement
        # Kick Punch: 4-on-the-floor (velocity 120)
        kick_p_notes = [
            {"pitch": 36, "start_time": float(b), "duration": 0.4, "velocity": 120}
            for b in range(16)
        ]
        self.create_clip_with_notes(t_kick_p + 1, 0, kick_p_notes, length_beats=16.0, name="Kick Punch 4x4")
        for b in [16.0, 32.0, 48.0]:
            self.client.call_tool("live12_clip_duplicate_to_arrangement", {
                "track_index": t_kick_p + 1, "slot_index": 0, "arrangement_time": b
            })

        # Kick Rumble: rolling 16ths
        rumble_notes = []
        for s in range(64):
            if s % 4 != 0:  # offbeat 16ths
                rumble_notes.append({
                    "pitch": 36, "start_time": s * 0.25, "duration": 0.2, "velocity": 95 if s % 2 == 0 else 80
                })
        self.create_clip_with_notes(t_rumble + 1, 0, rumble_notes, length_beats=16.0, name="Sub Rumble 16th")
        for b in [16.0, 32.0, 48.0]:
            self.client.call_tool("live12_clip_duplicate_to_arrangement", {
                "track_index": t_rumble + 1, "slot_index": 0, "arrangement_time": b
            })

        # Clap: Beats 2 and 4 (beat indices 1.0, 3.0, 5.0, 7.0 ...)
        clap_notes = [
            {"pitch": 60, "start_time": float(b), "duration": 0.25, "velocity": 105}
            for b in range(16) if b % 2 == 1
        ]
        self.create_clip_with_notes(t_clap + 1, 0, clap_notes, length_beats=16.0, name="Clap-Snare 2&4")
        for b in [16.0, 32.0, 48.0]:
            self.client.call_tool("live12_clip_duplicate_to_arrangement", {
                "track_index": t_clap + 1, "slot_index": 0, "arrangement_time": b
            })

        # Hi-Hats: offbeats (0.5, 1.5, 2.5 ...)
        hat_notes = [
            {"pitch": 64, "start_time": float(b) + 0.5, "duration": 0.2, "velocity": 110}
            for b in range(16)
        ]
        self.create_clip_with_notes(t_hats + 1, 0, hat_notes, length_beats=16.0, name="Offbeat Hats")
        for b in [16.0, 32.0, 48.0]:
            self.client.call_tool("live12_clip_duplicate_to_arrangement", {
                "track_index": t_hats + 1, "slot_index": 0, "arrangement_time": b
            })

        logger.info("HOLO Module 2 build completed.")


def main():
    builder = HoloModule2Builder()
    res = builder.run(render_duration_beats=64.0, expected_min_tracks=8)
    if not res.get("valid"):
        logger.error("HOLO Module 2 verification failed: %s", res)
        sys.exit(1)
    logger.info("HOLO Module 2 SUCCEEDED: %s", res)


if __name__ == "__main__":
    main()
