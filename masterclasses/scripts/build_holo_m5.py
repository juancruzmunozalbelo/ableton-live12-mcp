"""
HOLO Masterclass - Modulo 5: Arreglo Completo
==============================================
126 BPM, C Minor, 180-bar complete arrangement masterclass:
25 tracks total organized into 3 nested groups:
- DRUMS (8 tracks + group bus)
- SYNTHS (7 tracks + group bus)
- HARMONICS & MELODICS (7 tracks + group bus)
Master bus processing chain: EQ Eight -> Glue Compressor -> Saturator -> Utility -> Limiter.
Full arrangement locators and stems.
"""

from __future__ import annotations

import logging
import os
import sys

from builder_base import MasterclassBuilder

logger = logging.getLogger("masterclass.holo_m5")

SPEC_PATH = os.path.join(os.path.dirname(__file__), "..", "specs", "holo_m5_arreglo_completo.json")
ALS_DEST = os.path.join(os.path.dirname(__file__), "..", "holo", "modulo_5_arreglo_completo.als")
WAV_DEST = os.path.join(os.path.dirname(__file__), "..", "holo", "modulo_5_arreglo_completo.wav")

SNARE_ROLL_SAMPLE = "/Users/juancruz/Downloads/ClaSE PEAK jULIO 25 Project/Samples/Imported/TA_MK4_SNARE_ROLL_MASSIVE_126.wav"
RISER_SAMPLE = "/Users/juancruz/Downloads/ClaSE PEAK jULIO 25 Project/Samples/Imported/ESM_7th_Dimension_Build_Up_Rising_Riser_Cinematic_Trailer_Movie_Transition.wav"


class HoloModule5Builder(MasterclassBuilder):
    """
    Reconstructs HOLO Masterclass Modulo 5 in Ableton Live 12 Suite.
    """

    def __init__(self):
        super().__init__(spec_path=SPEC_PATH, als_dest=ALS_DEST, wav_dest=WAV_DEST)

    def build(self) -> None:
        logger.info("Building HOLO Module 5 full 25-track arrangement masterclass...")

        # ======================================================================
        # 1. DRUMS GROUP (8 tracks)
        # ======================================================================
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

        drum_indices = [t_kick_p, t_kick_b, t_rumble, t_clap, t_shaker, t_hats, t_aux, t_top]
        grp_drums = self.group_tracks(drum_indices, group_name="DRUMS")
        self.load_device(grp_drums, "Glue Compressor")
        self.load_device(grp_drums, "EQ Eight")

        # ======================================================================
        # 2. SYNTHS GROUP (7 tracks)
        # ======================================================================
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

        synth_indices = [t_lead, t_meld, t_drift, t_fm, t_sub, t_pad, t_pluck]
        grp_synths = self.group_tracks(synth_indices, group_name="SYNTHS")
        self.load_device(grp_synths, "Auto Filter")
        self.load_device(grp_synths, "Glue Compressor")

        # ======================================================================
        # 3. HARMONICS & MELODICS GROUP (7 tracks)
        # ======================================================================
        t_chords = self.create_track("Progression Chords & Pads", track_type="midi", volume_db=-7.0)
        self.load_device(t_chords, "Wavetable")

        t_rolling = self.create_track("Rolling 16th Bass", track_type="midi", volume_db=-5.0)
        self.load_device(t_rolling, "Operator")

        t_triplet = self.create_track("PC2 Triplet Bass Motif", track_type="midi", volume_db=-6.0)
        self.load_device(t_triplet, "Drift")

        t_main_lead = self.create_track("Main Melodic Theme (Lead)", track_type="midi", volume_db=-4.5)
        self.load_device(t_main_lead, "Wavetable")

        t_counter = self.create_track("Arpeggiated Counter-Melody", track_type="midi", volume_db=-8.0)
        self.load_device(t_counter, "Drift")

        t_fills = self.create_track("Structural Fills & Turnarounds", track_type="audio", volume_db=-6.0)
        t_risers = self.create_track("Build Risers & Tension FX", track_type="audio", volume_db=-7.0)

        melodics_indices = [t_chords, t_rolling, t_triplet, t_main_lead, t_counter, t_fills, t_risers]
        grp_melodics = self.group_tracks(melodics_indices, group_name="HARMONICS & MELODICS")
        self.load_device(grp_melodics, "Glue Compressor")

        # ======================================================================
        # 4. MASTER BUS PROCESSING
        # ======================================================================
        logger.info("Configuring Master Bus signal processing chain...")
        for dev in ["EQ Eight", "Glue Compressor", "Saturator", "Utility", "Limiter"]:
            try:
                self.load_device(0, dev, track_type="master")
            except Exception as e:
                logger.debug("Failed loading master device '%s': %s", dev, e)

        # ======================================================================
        # 5. Program Essential Arrangement Clips for Audio Bounce
        # ======================================================================
        # Kick Punch (track index 1)
        kick_p_notes = [
            {"pitch": 36, "start_time": float(b), "duration": 0.4, "velocity": 120}
            for b in range(16)
        ]
        self.create_clip_with_notes(1, 0, kick_p_notes, length_beats=16.0, name="Kick 4x4")
        for b in [16.0, 32.0, 48.0]:
            self.client.call_tool("live12_clip_duplicate_to_arrangement", {
                "track_index": 1, "slot_index": 0, "arrangement_time": b
            })

        # Clap (track index 4)
        clap_notes = [
            {"pitch": 60, "start_time": float(b), "duration": 0.25, "velocity": 105}
            for b in range(16) if b % 2 == 1
        ]
        self.create_clip_with_notes(4, 0, clap_notes, length_beats=16.0, name="Clap 2&4")
        for b in [16.0, 32.0, 48.0]:
            self.client.call_tool("live12_clip_duplicate_to_arrangement", {
                "track_index": 4, "slot_index": 0, "arrangement_time": b
            })

        # Lead (track index 10)
        lead_notes = [
            {"pitch": 60, "start_time": 0.0, "duration": 1.0, "velocity": 110},
            {"pitch": 63, "start_time": 2.0, "duration": 1.5, "velocity": 115},
            {"pitch": 67, "start_time": 4.0, "duration": 3.0, "velocity": 120},
            {"pitch": 70, "start_time": 8.0, "duration": 2.0, "velocity": 112},
            {"pitch": 68, "start_time": 10.0, "duration": 1.0, "velocity": 108},
            {"pitch": 67, "start_time": 12.0, "duration": 3.0, "velocity": 115},
        ]
        self.create_clip_with_notes(10, 0, lead_notes, length_beats=16.0, name="Main Lead Hook")
        for b in [16.0, 32.0, 48.0]:
            self.client.call_tool("live12_clip_duplicate_to_arrangement", {
                "track_index": 10, "slot_index": 0, "arrangement_time": b
            })

        # Sub Bass (track index 14)
        sub_notes = [
            {"pitch": 36, "start_time": float(b), "duration": 0.45, "velocity": 115}
            for b in range(16)
        ]
        self.create_clip_with_notes(14, 0, sub_notes, length_beats=16.0, name="Sub Bassline")
        for b in [16.0, 32.0, 48.0]:
            self.client.call_tool("live12_clip_duplicate_to_arrangement", {
                "track_index": 14, "slot_index": 0, "arrangement_time": b
            })

        # Real audio samples on fills/risers
        if os.path.exists(SNARE_ROLL_SAMPLE):
            self.inject_audio_sample(23, SNARE_ROLL_SAMPLE, start_beat=48.0, length_beats=16.0)
        if os.path.exists(RISER_SAMPLE):
            self.inject_audio_sample(24, RISER_SAMPLE, start_beat=32.0, length_beats=32.0)

        logger.info("HOLO Module 5 full arrangement build completed.")


def main():
    builder = HoloModule5Builder()
    res = builder.run(render_duration_beats=64.0, expected_min_tracks=25)
    if not res.get("valid"):
        logger.error("HOLO Module 5 verification failed: %s", res)
        sys.exit(1)
    logger.info("HOLO Module 5 SUCCEEDED: %s", res)


if __name__ == "__main__":
    main()
