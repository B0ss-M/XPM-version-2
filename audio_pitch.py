"""
Advanced audio analysis module using multiple pitch detection techniques.
This version combines several state-of-the-art methods from librosa for maximum accuracy:
1. YIN algorithm (via librosa.pyin)
2. Harmonic structure analysis
3. Onset detection and note segmentation
4. Spectral centroid analysis
5. Multi-method consensus
6. Chroma feature analysis
7. Constant-Q transform analysis

NOTE: Requires the following libraries:
- librosa (pip install librosa)
"""

from __future__ import annotations

import logging
import os
from math import log2
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass
from statistics import mode, median_high

import numpy as np
import soundfile as sf

# Data structure for pitch detection results
@dataclass
class PitchResult:
    midi_note: int
    confidence: float
    method: str

# Import required libraries and handle cases where they're not installed
try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    logging.critical("The 'librosa' library is not installed. Pitch detection is disabled.")
    logging.critical("Please install it by running: pip install librosa")

if not LIBROSA_AVAILABLE:
    def detect_fundamental_pitch(path: str) -> Optional[int]:
        logging.critical("No pitch detection libraries available. Please install at least one of:")
        logging.critical("- librosa (pip install librosa)")
        logging.critical("- crepe (pip install crepe)")
        logging.critical("- aubio (pip install aubio)")
        return None

def detect_fundamental_pitch(path: str) -> Optional[int]:
    """
    Detect the fundamental pitch of an audio file using multiple advanced techniques.
    
    This enhanced version uses multiple librosa-based methods:
    1. pYIN (Probabilistic YIN) algorithm
    2. Harmonic structure analysis
    3. Onset detection and note segmentation
    4. Spectral centroid analysis
    5. Chroma feature analysis
    6. Constant-Q transform analysis
    
    Returns:
        Optional[int]: MIDI note number (0-127) or None if detection fails
    """
    if not LIBROSA_AVAILABLE:
        return None
        
    results: List[PitchResult] = []
    
    try:
        # Load audio file
        y, sr = librosa.load(path, sr=None, mono=True)
        
        if y.size == 0:
            logging.warning("Audio file is empty: %s", path)
            return None

        # 1. pYIN algorithm
        try:
            # Increased frame_length to 4096 and adjusted fmin to 43.066 Hz (slightly higher than C1)
            # This addresses the warning about inaccurate pitch detection due to insufficient periods
            f0, voiced_flag, voiced_prob = librosa.pyin(
                y,
                fmin=43.066,  # Slightly higher than C1 (32.7 Hz) to ensure accurate detection
                fmax=librosa.note_to_hz('C7'),
                sr=sr,
                frame_length=4096  # Increased from default 2048 to allow for more periods of low frequencies
            )
            
            voiced_f0 = f0[voiced_flag]
            voiced_probs = voiced_prob[voiced_flag]
            
            if voiced_f0.size > 0:
                # Use weighted histogram to find the most stable pitch
                hist, bins = np.histogram(voiced_f0, bins=100, weights=voiced_probs)
                bin_centers = (bins[:-1] + bins[1:]) / 2
                stable_pitch_hz = bin_centers[np.argmax(hist)]
                
                midi_note = int(round(librosa.hz_to_midi(stable_pitch_hz)))
                if 0 <= midi_note <= 127:
                    # Calculate confidence based on peak prominence and probability
                    peak_height = np.max(hist)
                    total_height = np.sum(hist)
                    confidence = float(np.mean(voiced_probs) * (peak_height / total_height))
                    results.append(PitchResult(midi_note, confidence, 'pyin'))
        except Exception as e:
            logging.warning(f"pYIN detection failed: {e}")

        # 2. Harmonic Structure Analysis
        try:
            S = np.abs(librosa.stft(y))
            freqs = librosa.fft_frequencies(sr=sr)
            
            # Find peaks in the magnitude spectrum
            peaks = librosa.util.peak_pick(np.mean(S, axis=1), 3, 3, 3, 5, 0.5, 0.5)
            peak_freqs = freqs[peaks]
            
            if len(peak_freqs) > 0:
                # Analyze harmonic relationships
                fundamental = peak_freqs[0]
                harmonics = peak_freqs[1:] / fundamental
                
                harmonic_error = np.min(np.abs(harmonics - np.round(harmonics)))
                confidence = 1.0 / (1.0 + harmonic_error)
                
                midi_note = int(round(librosa.hz_to_midi(fundamental)))
                if 0 <= midi_note <= 127:
                    results.append(PitchResult(midi_note, float(confidence), 'harmonic'))
        except Exception as e:
            logging.warning(f"Harmonic analysis failed: {e}")

        # 3. Chroma Feature Analysis
        try:
            # Compute chromagram using CQT
            C = np.abs(librosa.cqt(y, sr=sr, hop_length=512, fmin=43.066))
            chroma = librosa.feature.chroma_cqt(C=C, sr=sr)
            
            # Find the strongest pitch class
            pitch_class = np.argmax(np.mean(chroma, axis=1))
            
            # Estimate octave using spectral centroid
            cent = librosa.feature.spectral_centroid(y=y, sr=sr)
            octave = int(np.log2(np.mean(cent) / 440.0) + 4)
            
            # Combine pitch class and octave
            midi_note = pitch_class + (octave + 1) * 12
            if 0 <= midi_note <= 127:
                # Confidence based on how dominant the pitch class is
                max_magnitude = np.max(np.mean(chroma, axis=1))
                mean_magnitude = np.mean(np.mean(chroma, axis=1))
                confidence = (max_magnitude - mean_magnitude) / max_magnitude
                results.append(PitchResult(midi_note, float(confidence), 'chroma'))
        except Exception as e:
            logging.warning(f"Chroma analysis failed: {e}")

        # 4. Onset-based Analysis
        try:
            # Detect note onsets
            onset_env = librosa.onset.onset_strength(y=y, sr=sr)
            onset_frames = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr)
            
            if len(onset_frames) > 0:
                # Analyze pitch in the stable part of each onset
                onset_pitches = []
                onset_confidences = []
                
                for start, end in zip(onset_frames[:-1], onset_frames[1:]):
                    # Get the segment after attack
                    segment_start = start + (end - start) // 4  # Skip initial attack
                    segment = y[segment_start * 512:end * 512]
                    
                    if len(segment) > 512:  # Ensure segment is long enough
                        # Use STFT for frequency analysis
                        S_segment = np.abs(librosa.stft(segment))
                        freqs = librosa.fft_frequencies(sr=sr)
                        peak_idx = np.argmax(np.mean(S_segment, axis=1))
                        freq = freqs[peak_idx]
                        
                        midi_note = int(round(librosa.hz_to_midi(freq)))
                        if 0 <= midi_note <= 127:
                            # Confidence based on peak prominence
                            prominence = np.mean(S_segment, axis=1)[peak_idx] / np.mean(S_segment)
                            onset_pitches.append(midi_note)
                            onset_confidences.append(prominence)
                
                if onset_pitches:
                    # Use most common pitch from onset analysis
                    midi_note = mode(onset_pitches)
                    confidence = np.mean([c for p, c in zip(onset_pitches, onset_confidences) if p == midi_note])
                    results.append(PitchResult(midi_note, float(confidence), 'onset'))
        except Exception as e:
            logging.warning(f"Onset analysis failed: {e}")

        # Consensus Decision Making
        if results:
            # Weight results by method reliability and confidence
            method_weights = {
                'pyin': 1.0,      # Most reliable for monophonic audio
                'harmonic': 0.9,  # Good for clean recordings
                'chroma': 0.8,    # Good for pitched sounds
                'onset': 0.7      # Good for percussive/attacked sounds
            }
            
            # Calculate weighted votes
            note_votes: Dict[int, float] = {}
            for result in results:
                weight = method_weights.get(result.method, 0.5) * result.confidence
                note_votes[result.midi_note] = note_votes.get(result.midi_note, 0) + weight
            
            if note_votes:
                # Choose the note with the highest weighted votes
                consensus_note = max(note_votes.items(), key=lambda x: x[1])[0]
                
                # Log the consensus process
                methods_str = ', '.join(f"{r.method}:{r.midi_note}" for r in results)
                logging.info(f"Pitch detection consensus for {os.path.basename(path)}:")
                logging.info(f"Individual results: {methods_str}")
                logging.info(f"Final consensus: MIDI {consensus_note}")
                
                return consensus_note

        logging.warning(f"No reliable pitch detection results for {path}")
        return None

    except Exception as e:
        logging.error(f"Pitch detection failed for {path}: {e}")
        if "audioread" in str(e):
            logging.error("This might be caused by a missing audio backend like 'ffmpeg'.")
            logging.error("Please ensure ffmpeg is installed and accessible in your system's PATH.")
        return None
