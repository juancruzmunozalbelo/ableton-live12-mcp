"""
HOLO Masterclass - Modulo 4: Bases Armonicas y Melodicas
=========================================================
126 BPM, C Minor (Aeolian). Extended MIDI programming:
Cm(add9) - Ab(add9) - Fm(add9) - Gm7 chord progression,
Rolling 16th bassline,
PC2 triplet bass motif (3-3-2),
Main melodic lead theme,
Arpeggiated counter-melody,
Structural fills & risers (real audio take lane injection),
Grouped into 'HARMONICS & MELODICS' bus with Glue Compressor.
"""

from __future__ import annotations

import logging
import os
import sys

from builder_base import MasterclassBuilder

logger = logging.getLogger("masterclass.holo_m4")

SPEC_PATH = os.path.join(os.path.dirname(__file__), "..", "specs", "holo_m4_bases_armonicas_melodicas.json")
ALS_DEST = os.path.join(os.path.dirname(__file__), "..", "holo", "modulo_4_bases_armonicas_melodicas.als")
WAV_DEST = os.path.join(os.path.dirname(__file__), "..", "holo", "modulo_4_bases_armonicas_melodicas.wav")

SNARE_ROLL_SAMPLE = "/Users/juancruz/Downloads/ClaSE PEAK jULIO 25 Project/Samples/Imported/TA_MK4_SNARE_ROLL_MASSIVE_126.wav"
RISER_SAMPLE = "/Users/juancruz/Downloads/ClaSE PEAK jULIO 25 Project/Samples/Imported/ESM_7th_Dimension_Build_Up_Rising_Riser_Cinematic_Trailer_Movie_Transition.wav"


class HoloModule4Builder(MasterclassBuilder):
    """
    Reconstructs HOLO Masterclass Modulo 4 in Ableton Live 12 Suite.
    """

    def __init__(self):
        super().__init__(spec_path=SPEC_PATH, als_dest=ALS_DEST, wav_dest=WAV_DEST)

    def build(self) -> None:
        logger.info("Building HOLO Module 4 harmonic and melodic structures...")

        # 1. Create Tracks
        t_chords = self.create_track("Progression Chords & Pads", track_type="midi", volume_db=-7.0)
        self.load_device(t_chords, "Wavetable")
        self.load_device(t_chords, "Delay")

        t_rolling = self.create_track("Rolling 16th Bass", track_type="midi", volume_db=-5.0)
        self.load_device(t_rolling, "Operator")
        self.load_device(t_rolling, "Auto Filter")

        t_triplet = self.create_track("PC2 Triplet Bass Motif", track_type="midi", volume_db=-6.0)
        self.load_device(t_triplet, "Drift")
        self.load_device(t_triplet, "Saturator")

        t_lead = self.create_track("Main Melodic Theme (Lead)", track_type="midi", volume_db=-4.5)
        self.load_device(t_lead, "Wavetable")
        self.load_device(t_lead, "Roar")
        self.load_device(t_lead, "Delay")

        t_arp = self.create_track("Arpeggiated Counter-Melody", track_type="midi", volume_db=-8.0)
        self.load_device(t_arp, "Drift")
        self.load_device(t_arp, "Echo")

        t_fills = self.create_track("Structural Fills & Turnarounds", track_type="audio", volume_db=-6.0)
        t_risers = self.create_track("Build Risers & Tension FX", track_type="audio", volume_db=-7.0)

        # 2. Group all 7 tracks into 'HARMONICS & MELODICS'
        all_indices = [t_chords, t_rolling, t_triplet, t_lead, t_arp, t_fills, t_risers]
        grp_idx = self.group_tracks(all_indices, group_name="HARMONICS & MELODICS")
        self.load_device(grp_idx, "Glue Compressor")

        # Shifted indices
        idx_chords = t_chords + 1
        idx_rolling = t_rolling + 1
        idx_triplet = t_triplet + 1
        idx_lead = t_lead + 1
        idx_arp = t_arp + 1
        idx_fills = t_fills + 1
        idx_risers = t_risers + 1

        # 3. Harmonic Progression: 16-bar progression (64 beats)
        # Cm(add9): C3(48), Eb3(51), G3(55), D4(62) - 16 beats (bars 1-4)
        # Ab(add9): Ab2(44), C3(48), Eb3(51), Bb3(58) - 16 beats (bars 5-8)
        # Fm(add9): F2(41), Ab2(44), C3(48), G3(55) - 16 beats (bars 9-12)
        # Gm7:      G2(43), Bb2(46), D3(50), F3(53) - 16 beats (bars 13-16)
        chord_prog = []
        # Cm add9 (0..16)
        for p in [48, 51, 55, 62]:
            chord_prog.append({"pitch": p, "start_time": 0.0, "duration": 15.8, "velocity": 85})
        # Ab add9 (16..32)
        for p in [44, 48, 51, 58]:
            chord_prog.append({"pitch": p, "start_time": 16.0, "duration": 15.8, "velocity": 85})
        # Fm add9 (32..48)
        for p in [41, 44, 48, 55]:
            chord_prog.append({"pitch": p, "start_time": 32.0, "duration": 15.8, "velocity": 85})
        # Gm7 (48..64)
        for p in [43, 46, 50, 53]:
            chord_prog.append({"pitch": p, "start_time": 48.0, "duration": 15.8, "velocity": 85})

        self.create_clip_with_notes(idx_chords, 0, chord_prog, length_beats=64.0, name="Progression Chords 16-bar")

        # 4. Rolling 16th Bass (driving roots: C1=36, Ab0=32, F0=29, G0=31)
        rolling_notes = []
        roots = [(0.0, 16.0, 36), (16.0, 32.0, 32), (32.0, 48.0, 29), (48.0, 64.0, 31)]
        for start_b, end_b, root_pitch in roots:
            step_count = int((end_b - start_b) * 4)  # 16ths
            for s in range(step_count):
                st = start_b + s * 0.25
                p = root_pitch if s % 8 != 6 else root_pitch + 7  # fifth variation
                vel = 110 if s % 4 == 0 else (95 if s % 2 == 0 else 75)
                rolling_notes.append({"pitch": p, "start_time": st, "duration": 0.2, "velocity": vel})

        self.create_clip_with_notes(idx_rolling, 0, rolling_notes, length_beats=64.0, name="Rolling 16th Bass 16-bar")

        # 5. PC2 Triplet Bass Motif (3-3-2 feel: beats 0, 0.75, 1.5, 2.0, 2.75, 3.5)
        triplet_notes = []
        pattern_offsets = [0.0, 0.75, 1.5, 2.0, 2.75, 3.5]
        for bar in range(16):
            b_base = bar * 4.0
            r_pitch = 36 if bar < 4 else (32 if bar < 8 else (29 if bar < 12 else 31))
            for off in pattern_offsets:
                triplet_notes.append({
                    "pitch": r_pitch,
                    "start_time": b_base + off,
                    "duration": 0.35,
                    "velocity": 105 if off in [0.0, 2.0] else 90,
                })
        self.create_clip_with_notes(idx_triplet, 0, triplet_notes, length_beats=64.0, name="PC2 Triplet Bass Motif")

        # 6. Main Melodic Theme (Lead)
        # 16-bar soaring melodic techno lead
        lead_phrases = [
            # Phrase 1 over Cm (bars 1-4)
            {"pitch": 60, "start_time": 2.0, "duration": 1.5, "velocity": 110},
            {"pitch": 63, "start_time": 4.0, "duration": 1.0, "velocity": 112},
            {"pitch": 67, "start_time": 6.0, "duration": 3.5, "velocity": 120},
            {"pitch": 70, "start_time": 10.0, "duration": 1.5, "velocity": 115},
            {"pitch": 68, "start_time": 12.0, "duration": 1.0, "velocity": 108},
            {"pitch": 67, "start_time": 13.5, "duration": 2.5, "velocity": 114},
            # Phrase 2 over Ab (bars 5-8)
            {"pitch": 68, "start_time": 18.0, "duration": 1.5, "velocity": 110},
            {"pitch": 67, "start_time": 20.0, "duration": 1.0, "velocity": 105},
            {"pitch": 65, "start_time": 22.0, "duration": 3.0, "velocity": 112},
            {"pitch": 63, "start_time": 26.0, "duration": 1.5, "velocity": 108},
            {"pitch": 62, "start_time": 28.0, "duration": 3.5, "velocity": 110},
            # Phrase 3 over Fm (bars 9-12)
            {"pitch": 65, "start_time": 34.0, "duration": 1.5, "velocity": 112},
            {"pitch": 68, "start_time": 36.0, "duration": 1.0, "velocity": 115},
            {"pitch": 72, "start_time": 38.0, "duration": 3.5, "velocity": 122},
            {"pitch": 70, "start_time": 42.0, "duration": 1.5, "velocity": 110},
            {"pitch": 67, "start_time": 44.0, "duration": 3.5, "velocity": 116},
            # Phrase 4 over Gm (bars 13-16)
            {"pitch": 67, "start_time": 50.0, "duration": 1.5, "velocity": 114},
            {"pitch": 70, "start_time": 52.0, "duration": 1.0, "velocity": 118},
            {"pitch": 74, "start_time": 54.0, "duration": 3.0, "velocity": 124},
            {"pitch": 72, "start_time": 58.0, "duration": 1.5, "velocity": 112},
            {"pitch": 67, "start_time": 60.0, "duration": 3.5, "velocity": 115},
        ]
        self.create_clip_with_notes(idx_lead, 0, lead_phrases, length_beats=64.0, name="Lead Theme 16-bar")

        # 7. Counter Arp: High syncopated bubbling arp
        counter_notes = []
        arp_pitches = [72, 75, 79, 82, 84, 82, 79, 75]  # High register
        for s in range(256):  # 64 beats of 16ths
            p = arp_pitches[s % len(arp_pitches)]
            counter_notes.append({
                "pitch": p,
                "start_time": s * 0.25,
                "duration": 0.2,
                "velocity": 90 if s % 4 == 0 else 70,
            })
        self.create_clip_with_notes(idx_arp, 0, counter_notes, length_beats=64.0, name="Counter Arp 16-bar")

        # 8. Inject Real Audio Samples on Audio Tracks
        if os.path.exists(SNARE_ROLL_SAMPLE):
            logger.info("Injecting Snare Roll audio sample into track %d...", idx_fills)
            self.inject_audio_sample(idx_fills, SNARE_ROLL_SAMPLE, start_beat=48.0, length_beats=16.0)

        if os.path.exists(RISER_SAMPLE):
            logger.info("Injecting Riser audio sample into track %d...", idx_risers)
            self.inject_audio_sample(idx_risers, RISER_SAMPLE, start_beat=32.0, length_beats=32.0)

        logger.info("HOLO Module 4 build completed.")


def main():
    builder = HoloModule4Builder()
    res = builder.run(render_duration_beats=64.0, expected_min_tracks=7)
    if not res.get("valid"):
        logger.error("HOLO Module 4 verification failed: %s", res)
        sys.exit(1)
    logger.info("HOLO Module 4 SUCCEEDED: %s", res)


if __name__ == "__main__":
    main()
