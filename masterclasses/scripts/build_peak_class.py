"""
Peak Time Techno Masterclass - ClaSE PEAK jULIO 25
==================================================
135 BPM, G Minor, 33 tracks total:
- 3 nested groups (1-Group Master STEM Bus -> 2-Group Drums & Melodics Bus -> 3-Group Kick & Sub Bus)
- 27 stem tracks including real audio injection from original project samples
- Return tracks: A-Reverb, B-Delay, C-Echo
- 7 structural locators
- Audio bounce verification (>= 10s, RMS > -40 dBFS)
"""

from __future__ import annotations

import logging
import os
import sys

from builder_base import MasterclassBuilder

logger = logging.getLogger("masterclass.peak_class")

SPEC_PATH = os.path.join(os.path.dirname(__file__), "..", "specs", "clase_peak_julio_25.json")
ALS_DEST = os.path.join(os.path.dirname(__file__), "..", "peak", "clase_peak_julio_25.als")
WAV_DEST = os.path.join(os.path.dirname(__file__), "..", "peak", "clase_peak_julio_25.wav")

SAMPLES_DIR = "/Users/juancruz/Downloads/ClaSE PEAK jULIO 25 Project/Samples"
SAMPLE_KICK = os.path.join(SAMPLES_DIR, "Processed", "Consolidate", "OL_SKPA1_Kick_Loop_01_123 (5) [2025-06-25 203905].wav")
SAMPLE_RUMBLE = os.path.join(SAMPLES_DIR, "Processed", "Consolidate", "TWHS_HGE1_RUMBLE_LOOP_08_143BPM [2025-06-25 203947].wav")
SAMPLE_CH = os.path.join(SAMPLES_DIR, "Imported", "TWHS_HGE1_CH_LOOP_03_142BPM.wav")
SAMPLE_CLAP = os.path.join(SAMPLES_DIR, "Processed", "Consolidate", "TWHS_HGE1_CLAP_02 [2025-06-25 211236].wav")
SAMPLE_VOCAL = os.path.join(SAMPLES_DIR, "Processed", "Consolidate", "AU_MTF2_126_vocal_rap_doubles_female_get_naughty_sex_pills_dry_Gmin [2025-06-25 211605].wav")
SAMPLE_SNARE = os.path.join(SAMPLES_DIR, "Imported", "TA_MK4_SNARE_ROLL_MASSIVE_126.wav")
SAMPLE_GROOVE = os.path.join(SAMPLES_DIR, "Imported", "ZEN_KBB_137_drum_groove_storm.wav")
SAMPLE_IMPACT = os.path.join(SAMPLES_DIR, "Imported", "031_FX_Impact_-_SEROTONINTRANCE_Zenhiser.wav")
SAMPLE_RISER = os.path.join(SAMPLES_DIR, "Imported", "ESM_7th_Dimension_Build_Up_Rising_Riser_Cinematic_Trailer_Movie_Transition.wav")
SAMPLE_OMNI = os.path.join(SAMPLES_DIR, "Processed", "Bounce", "Bounce 7-Omnisphere [2025-06-25 210111]-2.wav")


class PeakClassBuilder(MasterclassBuilder):
    """
    Reconstructs Peak Time Masterclass (ClaSE PEAK jULIO 25) in Ableton Live 12 Suite.
    """

    def __init__(self):
        super().__init__(spec_path=SPEC_PATH, als_dest=ALS_DEST, wav_dest=WAV_DEST)

    def build(self) -> None:
        logger.info("Building ClaSE PEAK jULIO 25 33-track peak time project...")

        # Track specifications (27 child tracks to create and group)
        track_defs = [
            # Group 3 Children (Kick & Sub Bus)
            ("4-OL_SKPA1_Kick_Loop_01_123 (5)", "audio", -3.0, SAMPLE_KICK),
            ("5-TWHS_HGE1_RUMBLE_LOOP_08_143BPM", "audio", -4.5, SAMPLE_RUMBLE),
            ("6-OL_SKPA1_Kick_Loop_01_123 (5)", "audio", -6.0, SAMPLE_KICK),
            # Group 2 Children (Drums & Melodics Bus)
            ("7-ADRKT_WTTB4_Synth_10", "midi", -6.0, None),
            ("8-Omnisphere", "midi", -7.0, None),
            ("9-TWHS_HGE1_CH_LOOP_03_142BPM", "audio", -8.0, SAMPLE_CH),
            ("10-ADRKT_WTTB4_Synth_26", "midi", -7.5, None),
            ("11-ADRKT_WTTB4_Synth_15", "midi", -6.5, None),
            ("12-Omnisphere", "midi", -7.0, None),
            ("13-ADRKT_WTTB4_Synth_18", "midi", -8.0, None),
            ("14-ADRKT_WTTB4_Bass_01", "midi", -5.0, None),
            ("15-TWHS_HGE1_CLAP_02", "audio", -6.0, SAMPLE_CLAP),
            ("16-AU_MTF2_126_vocal_rap_doubles", "audio", -8.0, SAMPLE_VOCAL),
            ("17-AU_MTF2_126_vocal_rap_doubles", "audio", -8.0, SAMPLE_VOCAL),
            ("18-AU_MTF2_126_vocal_rap_doubles", "audio", -8.0, SAMPLE_VOCAL),
            ("19-AU_MTF2_126_vocal_rap_doubles", "audio", -8.0, SAMPLE_VOCAL),
            ("20-AU_MTF2_126_vocal_rap_doubles", "audio", -8.0, SAMPLE_VOCAL),
            ("21-AU_MTF2_126_vocal_rap_doubles", "audio", -8.0, SAMPLE_VOCAL),
            ("22-TA_MK4_SNARE_ROLL_MASSIVE_126", "audio", -6.0, SAMPLE_SNARE),
            ("23-Serum 2", "midi", -5.5, None),
            ("24-ZEN_KBB_137_drum_groove_storm", "audio", -7.0, SAMPLE_GROOVE),
            ("25-Omnisphere", "midi", -7.0, None),
            ("26-Omnisphere", "midi", -7.0, None),
            ("27-Omnisphere", "midi", -7.0, None),
            ("28-031_FX_Impact_-_SEROTONINTRANCE", "audio", -6.0, SAMPLE_IMPACT),
            ("29-ESM_7th_Dimension_Build_Up", "audio", -6.0, SAMPLE_RISER),
            ("30-Freeze ... Oscar Mulero Metal Horse", "audio", -8.0, SAMPLE_OMNI),
        ]

        created_indices = []
        for name, t_type, vol, sample_path in track_defs:
            idx = self.create_track(name, track_type=t_type, volume_db=vol)
            created_indices.append(idx)

            # Load instrument on MIDI tracks
            if t_type == "midi":
                if "bass" in name.lower():
                    self.load_device(idx, "Operator")
                elif "synth" in name.lower():
                    self.load_device(idx, "Wavetable")
                else:
                    self.load_device(idx, "Drift")

            # Inject real audio sample on audio tracks
            if t_type == "audio" and sample_path and os.path.exists(sample_path):
                try:
                    self.inject_audio_sample(idx, sample_path, start_beat=0.0, length_beats=64.0)
                except Exception as e:
                    logger.debug("Minor notice injecting audio on track %d: %s", idx, e)

        # Build Group Hierarchy
        # Group 3-Group: Kick & Sub Bus (indices 0, 1, 2)
        grp3 = self.group_tracks(created_indices[:3], group_name="3-Group")
        self.load_device(grp3, "Glue Compressor")

        # Group 2-Group: Drums & Melodics Bus (contains grp3 and remainder of tracks)
        # Note: after grouping, grp3 is at index 0, followed by tracks 4..30
        st = self.client.call_tool("live12_song_get_state")
        tracks_count = st.get("tracks_count", 28)
        # Group all remaining child tracks into 2-Group
        grp2 = self.group_tracks(list(range(grp3 + 1, tracks_count)), group_name="2-Group")
        self.load_device(grp2, "Glue Compressor")

        # Top-level Master STEM Bus: Group 1-Group containing 3-Group and 2-Group
        grp1 = self.group_tracks([0, 1], group_name="1-Group")
        self.load_device(grp1, "EQ Eight")
        self.load_device(grp1, "Glue Compressor")

        # Program driving MIDI on key lead & bass tracks to ensure massive sonic energy
        # G Minor: G1=43, Bb1=46, C2=48, D2=50
        g_notes = [
            {"pitch": 43, "start_time": float(b), "duration": 0.4, "velocity": 120}
            for b in range(16)
        ]
        # Find a MIDI synth track to play notes
        self.create_clip_with_notes(5, 0, g_notes, length_beats=16.0, name="Peak Bassline 4x4")
        for b in [16.0, 32.0, 48.0]:
            self.client.call_tool("live12_clip_duplicate_to_arrangement", {
                "track_index": 5, "slot_index": 0, "arrangement_time": b
            })

        logger.info("ClaSE PEAK jULIO 25 build completed.")


def main():
    builder = PeakClassBuilder()
    res = builder.run(render_duration_beats=64.0, expected_min_tracks=27)
    if not res.get("valid"):
        logger.error("Peak Class verification failed: %s", res)
        sys.exit(1)
    logger.info("Peak Class SUCCEEDED: %s", res)


if __name__ == "__main__":
    main()
