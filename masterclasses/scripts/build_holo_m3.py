"""
HOLO Masterclass - Modulo 3: Diseno Sonoro
===========================================
126 BPM, C Minor, Native Suite sound design stems:
Wavetable Lead (Wavetable + Roar + Delay),
Meld Bass & Texture (Meld + Saturator),
Drift Analog Lead (Drift),
Operator FM Sub Stabs (Operator),
SUB Bass Dedicated (Operator + Utility),
Atmospheric Chords & Pads (Wavetable),
Pluck Arp (Drift + Delay),
Grouped into 'SYNTHS' bus with Auto Filter & Glue Compressor.
"""

from __future__ import annotations

import logging
import os
import sys

from builder_base import MasterclassBuilder

logger = logging.getLogger("masterclass.holo_m3")

SPEC_PATH = os.path.join(os.path.dirname(__file__), "..", "specs", "holo_m3_diseno_sonoro.json")
ALS_DEST = os.path.join(os.path.dirname(__file__), "..", "holo", "modulo_3_diseno_sonoro.als")
WAV_DEST = os.path.join(os.path.dirname(__file__), "..", "holo", "modulo_3_diseno_sonoro.wav")


class HoloModule3Builder(MasterclassBuilder):
    """
    Reconstructs HOLO Masterclass Modulo 3 in Ableton Live 12 Suite.
    """

    def __init__(self):
        super().__init__(spec_path=SPEC_PATH, als_dest=ALS_DEST, wav_dest=WAV_DEST)

    def build(self) -> None:
        logger.info("Building HOLO Module 3 sound design synth stems...")

        # 1. Create Synth Tracks
        t_lead = self.create_track("Wavetable Lead", track_type="midi", volume_db=-5.0)
        self.load_device(t_lead, "Wavetable")
        self.load_device(t_lead, "Roar")
        self.load_device(t_lead, "Auto Filter")
        self.load_device(t_lead, "Delay")

        t_meld = self.create_track("Meld Bass & Texture", track_type="midi", volume_db=-6.5)
        self.load_device(t_meld, "Meld")
        self.load_device(t_meld, "Saturator")

        t_drift = self.create_track("Drift Analog Lead", track_type="midi", volume_db=-8.0)
        self.load_device(t_drift, "Drift")

        t_fm = self.create_track("Operator FM Sub Stabs", track_type="midi", volume_db=-7.0)
        self.load_device(t_fm, "Operator")

        t_sub = self.create_track("SUB Bass Dedicated", track_type="midi", volume_db=-5.0)
        self.load_device(t_sub, "Operator")
        self.load_device(t_sub, "Utility")

        t_pad = self.create_track("Atmospheric Chords & Pads", track_type="midi", volume_db=-9.0)
        self.load_device(t_pad, "Wavetable")

        t_pluck = self.create_track("Pluck Arp Call & Response", track_type="midi", volume_db=-9.0)
        self.load_device(t_pluck, "Drift")
        self.load_device(t_pluck, "Delay")

        # 2. Group all 7 synth tracks into 'SYNTHS'
        synth_indices = [t_lead, t_meld, t_drift, t_fm, t_sub, t_pad, t_pluck]
        grp_idx = self.group_tracks(synth_indices, group_name="SYNTHS")
        self.load_device(grp_idx, "Auto Filter")
        self.load_device(grp_idx, "Glue Compressor")

        # 3. Note programming (C Minor: C=48, Eb=51, F=53, G=55, Ab=56, Bb=58)
        # Shifted indices due to group track: tracks become grp_idx + 1 .. grp_idx + 7
        idx_lead = t_lead + 1
        idx_meld = t_meld + 1
        idx_drift = t_drift + 1
        idx_fm = t_fm + 1
        idx_sub = t_sub + 1
        idx_pad = t_pad + 1
        idx_pluck = t_pluck + 1

        # A. SUB Bass: Rolling C Minor sub (C1 = 36, Eb1 = 39, F1 = 41, G1 = 43)
        sub_notes = []
        for b in range(16):
            # 8th note driving pulse
            pitch = 36 if b < 8 else (39 if b < 12 else 34)
            sub_notes.append({"pitch": pitch, "start_time": float(b), "duration": 0.45, "velocity": 115})
            sub_notes.append({"pitch": pitch, "start_time": float(b) + 0.5, "duration": 0.45, "velocity": 100})
        self.create_clip_with_notes(idx_sub, 0, sub_notes, length_beats=16.0, name="Sub Bassline Intro")
        for b_start in [16.0, 32.0, 48.0, 64.0]:
            self.client.call_tool("live12_clip_duplicate_to_arrangement", {
                "track_index": idx_sub, "slot_index": 0, "arrangement_time": b_start
            })

        # B. Atmospheric Pads: Lush C Minor chords (Cm: C3-Eb3-G3-D4, Ab: Ab2-C3-Eb3-Bb3)
        pad_notes = [
            # Bars 1-2 (Cm add9): C3=48, Eb3=51, G3=55, D4=62
            {"pitch": 48, "start_time": 0.0, "duration": 7.8, "velocity": 90},
            {"pitch": 51, "start_time": 0.0, "duration": 7.8, "velocity": 85},
            {"pitch": 55, "start_time": 0.0, "duration": 7.8, "velocity": 88},
            {"pitch": 62, "start_time": 0.0, "duration": 7.8, "velocity": 80},
            # Bars 3-4 (Ab add9): Ab2=44, C3=48, Eb3=51, Bb3=58
            {"pitch": 44, "start_time": 8.0, "duration": 7.8, "velocity": 90},
            {"pitch": 48, "start_time": 8.0, "duration": 7.8, "velocity": 85},
            {"pitch": 51, "start_time": 8.0, "duration": 7.8, "velocity": 88},
            {"pitch": 58, "start_time": 8.0, "duration": 7.8, "velocity": 80},
        ]
        self.create_clip_with_notes(idx_pad, 0, pad_notes, length_beats=16.0, name="Atmospheric Pad Intro")
        for b_start in [16.0, 32.0, 48.0, 64.0]:
            self.client.call_tool("live12_clip_duplicate_to_arrangement", {
                "track_index": idx_pad, "slot_index": 0, "arrangement_time": b_start
            })

        # C. Wavetable Lead Hook (C Minor Melodic Techno lead phrase)
        # Tease motif starting at beat 16.0 (Bar 5)
        lead_notes = [
            {"pitch": 60, "start_time": 0.0, "duration": 0.75, "velocity": 105},
            {"pitch": 63, "start_time": 1.0, "duration": 0.5, "velocity": 110},
            {"pitch": 67, "start_time": 2.0, "duration": 1.5, "velocity": 115},
            {"pitch": 65, "start_time": 4.0, "duration": 0.75, "velocity": 100},
            {"pitch": 63, "start_time": 5.0, "duration": 0.5, "velocity": 95},
            {"pitch": 62, "start_time": 6.0, "duration": 1.75, "velocity": 105},
            {"pitch": 60, "start_time": 8.0, "duration": 0.75, "velocity": 105},
            {"pitch": 67, "start_time": 10.0, "duration": 2.0, "velocity": 118},
            {"pitch": 70, "start_time": 12.0, "duration": 1.0, "velocity": 110},
            {"pitch": 67, "start_time": 14.0, "duration": 1.5, "velocity": 105},
        ]
        self.create_clip_with_notes(idx_lead, 0, lead_notes, length_beats=16.0, name="Lead Main Hook")
        for b_start in [16.0, 32.0, 48.0, 64.0]:
            self.client.call_tool("live12_clip_duplicate_to_arrangement", {
                "track_index": idx_lead, "slot_index": 0, "arrangement_time": b_start
            })

        # D. Pluck Arp 16th syncopation
        pluck_notes = []
        arp_scale = [60, 63, 67, 72, 70, 67, 63, 62]  # C4, Eb4, G4, C5, Bb4, G4, Eb4, D4
        for s in range(32):  # 8 beats
            p = arp_scale[s % len(arp_scale)]
            pluck_notes.append({
                "pitch": p,
                "start_time": s * 0.25,
                "duration": 0.2,
                "velocity": 95 if s % 4 == 0 else 75,
            })
        self.create_clip_with_notes(idx_pluck, 0, pluck_notes, length_beats=8.0, name="Pluck Arp Hook")
        for b_start in [32.0, 40.0, 48.0, 56.0]:
            self.client.call_tool("live12_clip_duplicate_to_arrangement", {
                "track_index": idx_pluck, "slot_index": 0, "arrangement_time": b_start
            })

        logger.info("HOLO Module 3 sound design build completed.")


def main():
    builder = HoloModule3Builder()
    res = builder.run(render_duration_beats=64.0, expected_min_tracks=7)
    if not res.get("valid"):
        logger.error("HOLO Module 3 verification failed: %s", res)
        sys.exit(1)
    logger.info("HOLO Module 3 SUCCEEDED: %s", res)


if __name__ == "__main__":
    main()
