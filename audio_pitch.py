"""
Utility functions for audio analysis using the robust Librosa library.
This version provides state-of-the-art pitch detection for maximum accuracy.

NOTE: This module requires the 'librosa' library.
Install it by running: pip install librosa
"""

from __future__ import annotations

import logging
import os
from math import log2
from typing import Optional

import numpy as np
import soundfile as sf

# Attempt to import librosa and handle the case where it's not installed.
try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    # Define a placeholder function if librosa is not available
    def detect_fundamental_pitch(path: str) -> Optional[int]:
        logging.critical("The 'librosa' library is not installed. Pitch detection is disabled.")
        logging.critical("Please install it by running: pip install librosa")
        return None

# Only define the real function if librosa was successfully imported
if LIBROSA_AVAILABLE:
    def detect_fundamental_pitch(path: str) -> Optional[int]:
        """
        Return the estimated MIDI pitch of ``path`` using librosa's advanced pYIN algorithm.
        This method is highly accurate and robust for a wide range of musical instruments.
        """
        try:
            # Load the audio file using librosa.
            # It automatically handles resampling to a standard rate (22050 Hz) and converts to mono.
            # This standardization improves consistency and performance.
            y, sr = librosa.load(path, sr=None, mono=True)

            if y.size == 0:
                logging.warning("Audio file is empty: %s", path)
                return None

            # Use the pYIN algorithm for robust fundamental frequency estimation.
            # It provides frame-by-frame pitch (f0), voiced/unvoiced flags, and voicing probability.
            # We define a frequency range to search within, which helps avoid errors.
            f0, voiced_flag, voiced_prob = librosa.pyin(
                y,
                fmin=librosa.note_to_hz('C1'), # Search from a low C
                fmax=librosa.note_to_hz('C7')  # Up to a high C
            )

            # --- Intelligent Pitch Selection ---
            # We need to find the most reliable pitch from the array returned by pYIN.
            
            # 1. Get all frequencies where the signal is considered 'voiced'
            voiced_f0 = f0[voiced_flag]

            if voiced_f0.size == 0:
                logging.warning("No voiced frames found for pitch detection in: %s", path)
                return None

            # 2. Find the most common pitch among the voiced frames.
            # We can do this by finding the median, which is robust to outliers.
            stable_pitch_hz = np.median(voiced_f0)

            if stable_pitch_hz <= 0:
                logging.warning("Could not determine a stable positive pitch for: %s", path)
                return None

            # Convert the final, stable frequency to a MIDI note number
            midi_note = librosa.hz_to_midi(stable_pitch_hz)

            # Round to the nearest integer MIDI note
            midi_note_int = int(round(midi_note))

            if 0 <= midi_note_int <= 127:
                logging.info(f"Librosa detected pitch for {os.path.basename(path)}: {stable_pitch_hz:.2f} Hz -> MIDI {midi_note_int}")
                return midi_note_int
            else:
                logging.warning(f"Calculated MIDI note {midi_note_int} is out of range for {path}")
                return None

        except Exception as e:
            logging.error(f"Librosa pitch detection failed for {path}: {e}")
            # Add a specific check for a common librosa dependency issue on some systems
            if "audioread" in str(e):
                 logging.error("This might be caused by a missing audio backend like 'ffmpeg'.")
                 logging.error("Please ensure ffmpeg is installed and accessible in your system's PATH.")
            return None
