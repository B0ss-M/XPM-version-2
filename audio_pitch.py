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
            # Calculate appropriate n_fft for the signal length
            n_fft = min(2048, len(y))
            if n_fft < 256:  # Minimum viable n_fft
                n_fft = 256
            S = np.abs(librosa.stft(y, n_fft=n_fft))
            freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
            
            # Find peaks in the magnitude spectrum - fixed for newer librosa
            magnitude_spectrum = np.mean(S, axis=1)
            
            # Use scipy.signal.find_peaks instead of deprecated librosa.util.peak_pick
            try:
                from scipy.signal import find_peaks
                peaks, _ = find_peaks(magnitude_spectrum, 
                                    height=np.max(magnitude_spectrum) * 0.1,  # At least 10% of max
                                    distance=5)  # Minimum distance between peaks
            except ImportError:
                # Fallback: simple manual peak detection
                peaks = []
                for i in range(1, len(magnitude_spectrum) - 1):
                    if (magnitude_spectrum[i] > magnitude_spectrum[i-1] and 
                        magnitude_spectrum[i] > magnitude_spectrum[i+1] and
                        magnitude_spectrum[i] > np.max(magnitude_spectrum) * 0.1):
                        peaks.append(i)
                peaks = np.array(peaks)
            
            if len(peaks) > 0:
                peak_freqs = freqs[peaks]
                peak_magnitudes = magnitude_spectrum[peaks]
                
                # Sort peaks by magnitude (highest first)
                sorted_indices = np.argsort(peak_magnitudes)[::-1]
                peak_freqs = peak_freqs[sorted_indices]
                
                if len(peak_freqs) > 0:
                    # The fundamental is likely the lowest significant peak or strongest peak
                    # Try both approaches and see which gives more harmonic content
                    candidates = []
                    
                    # Candidate 1: Strongest peak
                    fundamental_candidate1 = peak_freqs[0]
                    if fundamental_candidate1 > 0:
                        candidates.append(fundamental_candidate1)
                    
                    # Candidate 2: Lowest significant peak
                    low_peaks = peak_freqs[peak_freqs > 50]  # Above 50Hz
                    if len(low_peaks) > 0:
                        fundamental_candidate2 = np.min(low_peaks)
                        if fundamental_candidate2 != fundamental_candidate1:
                            candidates.append(fundamental_candidate2)
                    
                    # Test which candidate has better harmonic series
                    best_fundamental = None
                    best_confidence = 0
                    
                    for candidate in candidates:
                        # Check harmonic content
                        harmonics_found = 0
                        for harmonic_num in range(2, 6):  # Check 2nd-5th harmonics
                            harmonic_freq = candidate * harmonic_num
                            # Check if this harmonic frequency exists in our peaks
                            harmonic_tolerance = candidate * 0.05  # 5% tolerance
                            if np.any(np.abs(peak_freqs - harmonic_freq) < harmonic_tolerance):
                                harmonics_found += 1
                        
                        confidence = harmonics_found / 4.0  # 4 harmonics checked
                        if confidence > best_confidence:
                            best_confidence = confidence
                            best_fundamental = candidate
                    
                    if best_fundamental and best_fundamental > 0:
                        midi_note = int(round(librosa.hz_to_midi(best_fundamental)))
                        if 0 <= midi_note <= 127:
                            results.append(PitchResult(midi_note, float(best_confidence), 'harmonic'))
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
                        # Calculate appropriate n_fft for the segment length
                        n_fft = min(2048, len(segment))
                        if n_fft < 256:  # Minimum viable n_fft
                            n_fft = 256
                        S_segment = np.abs(librosa.stft(segment, n_fft=n_fft))
                        freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
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

        # Consensus Decision Making with Enhanced Logic
        if results:
            # Enhanced method weights based on sample type analysis
            method_weights = {
                'pyin': 1.0,      # Most reliable for monophonic audio
                'harmonic': 0.95, # Enhanced weight for harmonic analysis
                'chroma': 0.8,    # Good for pitched sounds
                'onset': 0.7      # Good for percussive/attacked sounds
            }
            
            # Analyze signal characteristics to adjust weights
            try:
                # Check if signal is more tonal or percussive
                onset_strength = librosa.onset.onset_strength(y=y, sr=sr)
                onset_count = len(librosa.onset.onset_detect(onset_envelope=onset_strength, sr=sr))
                signal_duration = len(y) / sr
                
                # If many onsets per second, it's likely percussive
                onset_rate = onset_count / signal_duration
                if onset_rate > 10:  # High onset rate = percussive
                    method_weights['onset'] = 0.9
                    method_weights['harmonic'] = 0.7
                elif onset_rate < 2:  # Low onset rate = sustained/tonal
                    method_weights['pyin'] = 1.1
                    method_weights['harmonic'] = 1.0
                    
                # Check spectral characteristics
                spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)
                spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)
                
                # If most energy is in low frequencies, trust fundamental detection more
                if np.mean(spectral_centroids) < sr/8:  # Low spectral centroid
                    method_weights['pyin'] = 1.2
                    method_weights['harmonic'] = 1.1
                    
            except Exception as e:
                logging.debug(f"Signal analysis for weight adjustment failed: {e}")
            
            # Calculate weighted votes with confidence consideration
            note_votes: Dict[int, float] = {}
            for result in results:
                # Boost confidence for results that agree with others
                agreement_bonus = 1.0
                for other in results:
                    if other != result and abs(other.midi_note - result.midi_note) <= 1:
                        agreement_bonus += 0.2  # 20% bonus for near agreement
                        
                weight = method_weights.get(result.method, 0.5) * result.confidence * agreement_bonus
                note_votes[result.midi_note] = note_votes.get(result.midi_note, 0) + weight
            
            if note_votes:
                # Choose the note with the highest weighted votes
                consensus_note = max(note_votes.items(), key=lambda x: x[1])[0]
                total_confidence = max(note_votes.values()) / sum(note_votes.values())
                
                # Log the consensus process for debugging
                methods_str = ', '.join(f"{r.method}:{r.midi_note}({r.confidence:.2f})" for r in results)
                logging.info(f"Pitch detection consensus for {os.path.basename(path)}:")
                logging.info(f"Individual results: {methods_str}")
                logging.info(f"Final consensus: MIDI {consensus_note} (confidence: {total_confidence:.2f})")
                
                return consensus_note

        logging.warning(f"No reliable pitch detection results for {path}")
        return None

    except Exception as e:
        logging.error(f"Pitch detection failed for {path}: {e}")
        if "audioread" in str(e):
            logging.error("This might be caused by a missing audio backend like 'ffmpeg'.")
            logging.error("Please ensure ffmpeg is installed and accessible in your system's PATH.")
        return None
