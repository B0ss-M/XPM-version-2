"""
Utility functions for audio analysis using an improved pitch detection algorithm.
"""

from __future__ import annotations

import logging
import os
from math import log2
from typing import Optional

import numpy as np
import soundfile as sf

def detect_fundamental_pitch(path: str, harmonics_to_check: int = 5) -> Optional[int]:
    """
    Return the estimated MIDI pitch of ``path`` using the Harmonic Product Spectrum (HPS) algorithm.
    HPS is more robust against overtones being mistaken for the fundamental frequency.
    """
    try:
        data, sr = sf.read(path, always_2d=True)
        if data.size == 0 or sr <= 0:
            logging.warning("Audio file is empty or has an invalid sample rate: %s", path)
            return None
            
        mono = data.mean(axis=1)
        
        # Analyze a stable portion of the sound, avoiding the initial transient
        # We'll take a chunk from the first part of the file after the initial attack
        start_frame = int(sr * 0.05) # Skip first 50ms
        n = min(len(mono) - start_frame, int(sr * 0.5)) # Analyze up to 0.5 seconds of audio
        
        if n <= 16:
            logging.warning("Not enough audio data to analyze pitch in: %s", path)
            return None
            
        segment = mono[start_frame : start_frame + n]
        
        # Ensure segment is not silent
        if np.max(np.abs(segment)) < 1e-5:
            logging.info("Segment is silent for pitch detection in: %s", path)
            return None

        # Apply a Hanning window to reduce spectral leakage
        window = np.hanning(len(segment))
        spectrum = np.fft.rfft(segment * window)
        mags = np.abs(spectrum)

        # --- CORRECTED Harmonic Product Spectrum (HPS) ---
        # The original array is not modified. We work with slices.
        hps_len = len(mags) // harmonics_to_check
        hps = mags[:hps_len].copy()

        # Downsample the spectrum and multiply
        for i in range(2, harmonics_to_check + 1):
            hps *= mags[::i][:hps_len]

        # Find the peak in the HPS
        # We search from a low frequency (e.g., 40Hz) to avoid DC offset and low-freq noise
        min_freq = 40
        min_index = int(min_freq * len(segment) / sr)
        
        if hps_len <= min_index:
            logging.warning("Not enough spectral data for HPS analysis in: %s", path)
            return None
            
        peak_index = np.argmax(hps[min_index:]) + min_index

        # Convert peak index to frequency
        freq = peak_index * sr / len(segment)
        
        if freq <= 0:
            return None

        # Convert frequency to MIDI note
        midi = round(69 + 12 * log2(freq / 440.0))
        
        logging.info("Detected pitch for %s: Freq=%.2f Hz, MIDI=%d", os.path.basename(path), freq, midi)
        
        return midi if 0 <= midi <= 127 else None

    except Exception as exc:
        logging.error("Pitch detection failed for %s: %s", path, exc)
        return None
