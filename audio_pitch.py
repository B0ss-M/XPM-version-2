"""Utility functions for audio analysis."""

from __future__ import annotations

import logging
from math import log2
from typing import Optional

import numpy as np
import soundfile as sf


def detect_fundamental_pitch(path: str) -> Optional[int]:
    """Return the estimated MIDI pitch of ``path`` using a simple FFT analysis."""

    try:
        data, sr = sf.read(path, always_2d=True)
        if data.size == 0 or sr <= 0:
            return None
        mono = data.mean(axis=1)
        n = min(len(mono), int(sr))  # analyze up to the first second
        if n <= 16:
            return None
        segment = mono[:n]
        segment = segment - float(np.mean(segment))
        window = np.hanning(len(segment))
        spectrum = np.fft.rfft(segment * window)
        mags = np.abs(spectrum)
        if len(mags) < 2:
            return None
        peak_index = int(np.argmax(mags[1:]) + 1)
        freq = peak_index * sr / len(segment)
        if freq <= 0:
            return None
        midi = round(69 + 12 * log2(freq / 440.0))
        return midi if 0 <= midi <= 127 else None
    except Exception as exc:
        logging.error("Pitch detection failed for %s: %s", path, exc)
        return None
