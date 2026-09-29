#!/usr/bin/env python3
"""
Advanced MIDI Chord Analyzer for XPM Music Theory Engine

This module provides:
1. MIDI file reading and parsing
2. Intelligent chord detection and analysis from MIDI data
3. Harmonic progression extraction
4. Integration with the existing chord library database
5. Machine learning features for improved chord recognition

Features:
- Multi-track MIDI analysis with smart track filtering
- Chord voicing detection (close, open, drop-2, etc.)
- Time-based progression analysis with tempo consideration
- Jazz substitution detection and analysis
- Modal analysis and key signature detection
- Chord complexity scoring for machine learning
- Export to existing music theory engine database format

Dependencies:
- mido: MIDI file I/O and parsing
- pretty_midi: Advanced MIDI analysis (optional, recommended)
- music21: Music theory analysis (optional, for advanced features)
- numpy: Mathematical analysis
"""

import os
import logging
from typing import List, Dict, Optional, Tuple, Set, Any
from dataclasses import dataclass, field
from collections import defaultdict, Counter
import json
from datetime import datetime
import math
try:
    from scripts.midi_harmony import timed_notes, chord_groups
except ImportError:
    from midi_harmony import timed_notes, chord_groups

# Required dependencies check
try:
    import mido
    MIDO_AVAILABLE = True
except ImportError:
    MIDO_AVAILABLE = False
    logging.warning("mido not available. Install with: pip install mido")

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    logging.warning("numpy not available. Install with: pip install numpy")

# Optional dependencies for enhanced analysis
try:
    import pretty_midi
    PRETTY_MIDI_AVAILABLE = True
except ImportError:
    PRETTY_MIDI_AVAILABLE = False
    logging.info("pretty_midi not available. Install with: pip install pretty_midi for enhanced MIDI analysis")

try:
    import music21
    MUSIC21_AVAILABLE = True
except ImportError:
    MUSIC21_AVAILABLE = False
    logging.info("music21 not available. Install with: pip install music21 for advanced music theory analysis")

# Music theory constants (consistent with existing engine)
NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
CIRCLE_OF_FIFTHS = [0, 7, 2, 9, 4, 11, 6, 1, 8, 3, 10, 5]  # C, G, D, A, E, B, F#, C#, G#, D#, A#, F

@dataclass
class MIDINote:
    """Represents a single MIDI note event."""
    pitch: int
    velocity: int
    start_time: float
    end_time: float
    track: int = 0
    channel: int = 0
    
    @property
    def duration(self) -> float:
        return self.end_time - self.start_time
    
    @property
    def note_name(self) -> str:
        return NOTE_NAMES[self.pitch % 12]

@dataclass
class ChordInstance:
    """Represents a detected chord with timing and analysis data."""
    notes: List[int]  # MIDI note numbers
    root: int
    chord_type: str
    start_time: float
    end_time: float
    voicing: str = "unknown"
    inversion: int = 0
    bass_note: Optional[int] = None
    complexity_score: float = 0.0
    confidence: float = 0.0
    track_sources: List[int] = field(default_factory=list)
    harmonic_function: Optional[str] = None
    
    @property
    def duration(self) -> float:
        return self.end_time - self.start_time
    
    @property
    def chord_symbol(self) -> str:
        """Generate a standard chord symbol."""
        root_name = NOTE_NAMES[self.root % 12]
        bass_suffix = f"/{NOTE_NAMES[self.bass_note % 12]}" if self.bass_note is not None and self.bass_note % 12 != self.root % 12 else ""
        quality = '' if self.chord_type == 'maj' else self.chord_type
        return f"{root_name}{quality}{bass_suffix}"

@dataclass
class ProgressionAnalysis:
    """Complete analysis of a MIDI file's harmonic progression."""
    file_path: str
    chords: List[ChordInstance]
    key_signature: Optional[str] = None
    scale_type: str = "major"
    tempo: float = 120.0
    time_signature: Tuple[int, int] = (4, 4)
    total_duration: float = 0.0
    tracks_analyzed: List[int] = field(default_factory=list)
    complexity_score: float = 0.0
    mood_indicators: List[str] = field(default_factory=list)
    modulations: List[Tuple[float, str, str]] = field(default_factory=list)  # (time, from_key, to_key)
    analysis_metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def chord_symbols(self) -> List[str]:
        return [chord.chord_symbol for chord in self.chords]
    
    @property
    def roman_numerals(self) -> List[str]:
        """Convert chords to Roman numeral analysis if key is known."""
        if not self.key_signature:
            return []
        
        roman_numerals = []
        key_root = NOTE_NAMES.index(self.key_signature.split()[0])
        
        for chord in self.chords:
            chord_root = chord.root % 12
            interval = (chord_root - key_root) % 12
            
            # Basic Roman numeral mapping (can be enhanced)
            roman_map = ['I', 'bII', 'II', 'bIII', 'III', 'IV', 'bV', 'V', 'bVI', 'VI', 'bVII', 'VII']
            numeral = roman_map[interval]
            
            # Adjust for chord quality
            if 'min' in chord.chord_type:
                numeral = numeral.lower()
            elif 'dim' in chord.chord_type:
                numeral = numeral.lower() + '°'
            elif 'aug' in chord.chord_type:
                numeral = numeral + '+'
                
            roman_numerals.append(numeral)
            
        return roman_numerals

class MIDIChordAnalyzer:
    """Advanced MIDI file analyzer for chord progression extraction."""
    
    def __init__(self):
        """Initialize the MIDI chord analyzer."""
        self.logger = logging.getLogger(__name__)
        
        # Analysis parameters
        self.min_chord_duration = 0.25  # Minimum chord duration in seconds
        self.chord_detection_threshold = 3  # Minimum notes for chord detection
        self.max_gap_fill = 0.1  # Maximum gap to fill between notes (seconds)
        self.voicing_analysis_enabled = True
        self.key_detection_enabled = True
        
        # Chord detection patterns (intervals from root)
        self.chord_patterns = {
            'maj': [0, 4, 7],
            'min': [0, 3, 7],
            'dim': [0, 3, 6],
            'aug': [0, 4, 8],
            'sus2': [0, 2, 7],
            'sus4': [0, 5, 7],
            '7': [0, 4, 7, 10],
            'maj7': [0, 4, 7, 11],
            'min7': [0, 3, 7, 10],
            'dim7': [0, 3, 6, 9],
            'min7b5': [0, 3, 6, 10],
            'aug7': [0, 4, 8, 10],
            'maj9': [0, 4, 7, 11, 14],
            'min9': [0, 3, 7, 10, 14],
            '9': [0, 4, 7, 10, 14],
            '11': [0, 4, 7, 10, 14, 17],
            '13': [0, 4, 7, 10, 14, 17, 21],
            'add9': [0, 4, 7, 14],
            '6': [0, 4, 7, 9],
            'min6': [0, 3, 7, 9],
            '7b5': [0, 4, 6, 10],
            '7#5': [0, 4, 8, 10],
            '7b9': [0, 4, 7, 10, 13],
            '7#9': [0, 4, 7, 10, 15],
        }
        
        # Track filtering criteria
        self.track_filters = {
            'ignore_percussion': True,
            'ignore_channel_10': True,  # Standard MIDI percussion channel
            'min_note_count': 3,
            'prefer_piano_tracks': True,
        }
        
    def analyze_midi_file(self, file_path: str) -> Optional[ProgressionAnalysis]:
        """
        Analyze a MIDI file and extract chord progressions.
        
        Args:
            file_path: Path to the MIDI file
            
        Returns:
            ProgressionAnalysis object or None if analysis failed
        """
        if not MIDO_AVAILABLE:
            self.logger.error("mido library not available. Cannot analyze MIDI files.")
            return None
            
        try:
            # Load MIDI file
            mid = mido.MidiFile(file_path)
            self.logger.info(f"Analyzing MIDI file: {file_path}")
            self.logger.info(f"Tracks: {len(mid.tracks)}, Ticks per beat: {mid.ticks_per_beat}")
            
            # Extract notes from all tracks
            all_notes = self._extract_notes_from_midi(mid)
            
            if not all_notes:
                self.logger.warning(f"No notes found in MIDI file: {file_path}")
                return None
                
            self.logger.info(f"Extracted {len(all_notes)} notes from MIDI file")
            
            # Filter and select best tracks for chord analysis
            filtered_notes = self._filter_and_select_tracks(all_notes, mid.tracks)
            
            if len(filtered_notes) < self.chord_detection_threshold:
                self.logger.warning(f"Insufficient notes for chord analysis: {len(filtered_notes)}")
                return None
                
            # Detect chord progressions
            chords = self._detect_chord_progressions(filtered_notes)
            
            # Analyze key signature
            key_sig = self._detect_key_signature(filtered_notes, chords)
            
            # Calculate tempo (if available)
            tempo = self._extract_tempo(mid)
            
            # Get time signature
            time_sig = self._extract_time_signature(mid)
            
            # Create progression analysis
            analysis = ProgressionAnalysis(
                file_path=file_path,
                chords=chords,
                key_signature=key_sig,
                tempo=tempo,
                time_signature=time_sig,
                total_duration=max(note.end_time for note in all_notes) if all_notes else 0.0,
                tracks_analyzed=[note.track for note in filtered_notes],
                analysis_metadata={
                    'total_notes': len(all_notes),
                    'analyzed_notes': len(filtered_notes),
                    'midi_format': mid.type,
                    'ticks_per_beat': mid.ticks_per_beat,
                    'analysis_timestamp': datetime.now().isoformat()
                }
            )
            
            # Enhanced analysis if optional libraries are available
            if PRETTY_MIDI_AVAILABLE:
                self._enhance_analysis_with_pretty_midi(analysis, file_path)
            
            # Calculate complexity and mood indicators
            self._calculate_progression_metrics(analysis)
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing MIDI file {file_path}: {e}")
            return None
    
    def _extract_notes_from_midi(self, mid: 'mido.MidiFile') -> List[MIDINote]:
        """Extract all note events from MIDI file."""
        return [MIDINote(pitch, velocity, start, end, track, channel)
                for start, end, pitch, velocity, track, channel in timed_notes(mid, mido)]

    def _filter_and_select_tracks(self, notes: List[MIDINote], tracks: List) -> List[MIDINote]:
        """Filter notes and select the best tracks for chord analysis."""
        # Group notes by track
        track_notes = defaultdict(list)
        for note in notes:
            track_notes[note.track].append(note)
        
        # Analyze tracks and score them
        track_scores = {}
        for track_idx, track_note_list in track_notes.items():
            score = self._score_track_for_chord_analysis(track_note_list, track_idx)
            if score > 0:
                track_scores[track_idx] = score
        
        # Prefer the strongest chordal track; mixing melody and accompaniment
        # produces false pitch collections at chord boundaries.
        best_tracks = sorted(track_scores.items(), key=lambda x: x[1], reverse=True)[:1]
        selected_track_ids = [track_id for track_id, _ in best_tracks]
        
        # Return notes from selected tracks
        filtered_notes = [note for note in notes if note.track in selected_track_ids]
        
        self.logger.info(f"Selected tracks {selected_track_ids} for chord analysis")
        return filtered_notes
    
    def _score_track_for_chord_analysis(self, track_notes: List[MIDINote], track_idx: int) -> float:
        """Score a track for its suitability for chord analysis."""
        if len(track_notes) < self.track_filters['min_note_count']:
            return 0.0
        
        score = 0.0
        
        # Basic note count score
        score += min(len(track_notes) / 50.0, 1.0) * 10
        
        # Check for percussion (channel 10 or track named with drums)
        if self.track_filters['ignore_percussion']:
            if any(note.channel == 9 for note in track_notes):  # MIDI channel 10 = channel 9 (0-indexed)
                return 0.0
        
        # Prefer tracks with chordal activity (multiple simultaneous notes)
        simultaneous_notes = self._count_simultaneous_notes(track_notes)
        score += min(simultaneous_notes / 10.0, 1.0) * 15
        
        # Prefer tracks with good pitch range for harmony
        pitches = [note.pitch for note in track_notes]
        pitch_range = max(pitches) - min(pitches)
        score += min(pitch_range / 48.0, 1.0) * 10  # 4 octaves = good range
        
        # Prefer tracks with sustained notes (good for chord detection)
        avg_duration = sum(note.duration for note in track_notes) / len(track_notes)
        score += min(avg_duration / 2.0, 1.0) * 5
        
        return score
    
    def _count_simultaneous_notes(self, notes: List[MIDINote]) -> int:
        """Count maximum number of simultaneous notes in a track."""
        events = []
        for note in notes:
            events.append((note.start_time, 1))  # Note on
            events.append((note.end_time, -1))   # Note off
        
        events.sort()
        max_simultaneous = 0
        current_count = 0
        
        for _, delta in events:
            current_count += delta
            max_simultaneous = max(max_simultaneous, current_count)
        
        return max_simultaneous
    
    def _detect_chord_progressions(self, notes: List[MIDINote]) -> List[ChordInstance]:
        """Detect chord progressions from the filtered notes."""
        if not notes:
            return []
        
        chords = []
        for group, pitches, (root, suffix, bass) in chord_groups(
                [(n.start_time, n.end_time, n.pitch, n.velocity, n.track, n.channel)
                 for n in notes]):
            if len(pitches) < self.chord_detection_threshold:
                continue
            chords.append(ChordInstance(
                notes=pitches, root=root, chord_type=suffix or 'maj',
                start_time=min(n[0] for n in group), end_time=max(n[1] for n in group),
                bass_note=min(pitches), confidence=1.0,
                track_sources=sorted({n[4] for n in group})))
        return self._post_process_chords(chords)

    def _create_time_slices(self, notes: List[MIDINote], slice_duration: float = 0.5) -> List[Tuple[float, List[MIDINote]]]:
        """Create time slices for chord analysis."""
        if not notes:
            return []
        
        start_time = notes[0].start_time
        end_time = max(note.end_time for note in notes)
        
        slices = []
        current_time = start_time
        
        while current_time < end_time:
            slice_end = current_time + slice_duration
            
            # Find all notes active during this slice
            active_notes = []
            for note in notes:
                if note.start_time <= slice_end and note.end_time >= current_time:
                    active_notes.append(note)
            
            if active_notes:
                slices.append((current_time, active_notes))
            
            current_time += slice_duration * 0.25  # 75% overlap between slices
        
        return slices
    
    def _analyze_chord_slice(self, slice_notes: List[MIDINote], start_time: float) -> Optional[ChordInstance]:
        """Analyze a time slice to detect chords."""
        if len(slice_notes) < self.chord_detection_threshold:
            return None
        
        # Extract unique pitches from the slice
        pitches = list(set(note.pitch % 12 for note in slice_notes))
        
        if len(pitches) < 3:  # Need at least 3 different pitches for a chord
            return None
        
        # Try to identify the chord
        chord_analysis = self._identify_chord(pitches, slice_notes)
        
        if not chord_analysis:
            return None
        
        root, chord_type, confidence = chord_analysis
        
        # Calculate timing
        end_time = max(note.end_time for note in slice_notes)
        
        # Analyze voicing if enabled
        voicing = "unknown"
        if self.voicing_analysis_enabled:
            voicing = self._analyze_voicing(slice_notes)
        
        # Find bass note
        bass_note = min(note.pitch for note in slice_notes)
        
        # Calculate inversion
        inversion = self._calculate_inversion(root, bass_note)
        
        chord = ChordInstance(
            notes=[note.pitch for note in slice_notes],
            root=root,
            chord_type=chord_type,
            start_time=start_time,
            end_time=end_time,
            voicing=voicing,
            inversion=inversion,
            bass_note=bass_note,
            confidence=confidence,
            track_sources=list(set(note.track for note in slice_notes)),
            complexity_score=self._calculate_chord_complexity(chord_type, len(pitches))
        )
        
        return chord
    
    def _identify_chord(self, pitches: List[int], slice_notes: List[MIDINote]) -> Optional[Tuple[int, str, float]]:
        """Identify chord type from pitches."""
        best_match = None
        best_score = 0.0
        
        # Try each possible root note
        for root in range(12):
            # Normalize pitches relative to this root
            intervals = sorted(set((pitch - root) % 12 for pitch in pitches))
            
            # Try to match against known chord patterns
            for chord_type, pattern in self.chord_patterns.items():
                score = self._match_chord_pattern(intervals, pattern)
                
                if score > best_score and score > 0.6:  # Minimum confidence threshold
                    best_score = score
                    best_match = (root, chord_type, score)
        
        return best_match
    
    def _match_chord_pattern(self, intervals: List[int], pattern: List[int]) -> float:
        """Calculate how well a set of intervals matches a chord pattern."""
        # Simple matching: calculate overlap
        pattern_set = set(interval % 12 for interval in pattern)
        interval_set = set(intervals)
        
        if not pattern_set:
            return 0.0
        
        # Calculate overlap
        overlap = len(pattern_set.intersection(interval_set))
        pattern_coverage = overlap / len(pattern_set)
        
        # Penalty for extra notes not in pattern
        extra_notes = len(interval_set - pattern_set)
        extra_penalty = extra_notes * 0.1
        
        score = pattern_coverage - extra_penalty
        return max(0.0, min(1.0, score))
    
    def _analyze_voicing(self, slice_notes: List[MIDINote]) -> str:
        """Analyze chord voicing."""
        if len(slice_notes) < 3:
            return "unknown"
        
        # Sort notes by pitch
        sorted_notes = sorted(slice_notes, key=lambda n: n.pitch)
        intervals = []
        
        for i in range(len(sorted_notes) - 1):
            interval = sorted_notes[i + 1].pitch - sorted_notes[i].pitch
            intervals.append(interval)
        
        # Simple voicing classification
        max_interval = max(intervals) if intervals else 0
        
        if max_interval <= 12:  # Within an octave
            return "close"
        elif max_interval <= 24:  # Within two octaves
            return "open"
        else:
            return "wide"
    
    def _calculate_inversion(self, root: int, bass_note: int) -> int:
        """Calculate chord inversion."""
        return (bass_note - root) % 12
    
    def _calculate_chord_complexity(self, chord_type: str, num_pitches: int) -> float:
        """Calculate a complexity score for the chord."""
        base_complexity = {
            'maj': 0.1, 'min': 0.1, 'dim': 0.3, 'aug': 0.4,
            'sus2': 0.2, 'sus4': 0.2, '7': 0.3, 'maj7': 0.4,
            'min7': 0.4, 'dim7': 0.6, 'min7b5': 0.7, 'aug7': 0.8,
        }.get(chord_type, 0.5)
        
        # Additional complexity for extended chords
        if '9' in chord_type:
            base_complexity += 0.2
        if '11' in chord_type:
            base_complexity += 0.3
        if '13' in chord_type:
            base_complexity += 0.4
        if 'alt' in chord_type or '#' in chord_type or 'b' in chord_type:
            base_complexity += 0.1
        
        # Factor in number of pitches
        pitch_complexity = min(num_pitches / 6.0, 1.0)
        
        return min(base_complexity + pitch_complexity * 0.2, 1.0)
    
    def _post_process_chords(self, chords: List[ChordInstance]) -> List[ChordInstance]:
        """Post-process detected chords to clean up the progression."""
        if not chords:
            return chords
        
        # Merge similar adjacent chords
        merged_chords = []
        current_chord = chords[0]
        
        for next_chord in chords[1:]:
            if (current_chord.chord_symbol == next_chord.chord_symbol and 
                next_chord.start_time - current_chord.end_time < 0.5):  # Small gap
                # Merge chords
                current_chord.end_time = next_chord.end_time
                current_chord.notes.extend(next_chord.notes)
                current_chord.notes = list(set(current_chord.notes))  # Remove duplicates
                current_chord.confidence = max(current_chord.confidence, next_chord.confidence)
            else:
                merged_chords.append(current_chord)
                current_chord = next_chord
        
        merged_chords.append(current_chord)
        
        # Filter out very short chords
        filtered_chords = [
            chord for chord in merged_chords 
            if chord.duration >= self.min_chord_duration
        ]
        
        return filtered_chords
    
    def _detect_key_signature(self, notes: List[MIDINote], chords: List[ChordInstance]) -> Optional[str]:
        """Detect the key signature of the piece."""
        if not self.key_detection_enabled or not notes:
            return None
        
        # Count pitch classes
        pitch_counts = Counter(note.pitch % 12 for note in notes)
        
        # Try each key and calculate fitness
        best_key = None
        best_score = 0.0
        
        # Major key templates (Krumhansl-Schmuckler key profiles)
        major_profile = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
        minor_profile = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]
        
        for tonic in range(12):
            # Test major key
            major_score = self._calculate_key_score(pitch_counts, tonic, major_profile)
            if major_score > best_score:
                best_score = major_score
                best_key = f"{NOTE_NAMES[tonic]} major"
            
            # Test minor key
            minor_score = self._calculate_key_score(pitch_counts, tonic, minor_profile)
            if minor_score > best_score:
                best_score = minor_score
                best_key = f"{NOTE_NAMES[tonic]} minor"
        
        return best_key if best_score > 0.5 else None
    
    def _calculate_key_score(self, pitch_counts: Counter, tonic: int, profile: List[float]) -> float:
        """Calculate key fitness score."""
        if not NUMPY_AVAILABLE:
            return 0.0
        
        # Create pitch vector
        pitch_vector = [pitch_counts.get((tonic + i) % 12, 0) for i in range(12)]
        
        if sum(pitch_vector) == 0:
            return 0.0
        
        # Normalize
        pitch_vector = np.array(pitch_vector, dtype=float)
        pitch_vector = pitch_vector / np.sum(pitch_vector)
        
        profile = np.array(profile, dtype=float)
        profile = profile / np.sum(profile)
        
        # Calculate correlation
        correlation = np.corrcoef(pitch_vector, profile)[0, 1]
        return correlation if not np.isnan(correlation) else 0.0
    
    def _extract_tempo(self, mid: 'mido.MidiFile') -> float:
        """Extract tempo from MIDI file."""
        for track in mid.tracks:
            for msg in track:
                if msg.type == 'set_tempo':
                    return mido.bpm2tempo(msg.tempo)
        return 120.0  # Default tempo
    
    def _extract_time_signature(self, mid: 'mido.MidiFile') -> Tuple[int, int]:
        """Extract time signature from MIDI file."""
        for track in mid.tracks:
            for msg in track:
                if msg.type == 'time_signature':
                    return (msg.numerator, msg.denominator)
        return (4, 4)  # Default time signature
    
    def _enhance_analysis_with_pretty_midi(self, analysis: ProgressionAnalysis, file_path: str):
        """Enhance analysis using pretty_midi if available."""
        try:
            pm = pretty_midi.PrettyMIDI(file_path)
            
            # Add instrument information
            instrument_info = []
            for instrument in pm.instruments:
                info = {
                    'program': instrument.program,
                    'name': instrument.name,
                    'is_drum': instrument.is_drum,
                    'notes': len(instrument.notes)
                }
                instrument_info.append(info)
            
            analysis.analysis_metadata['instruments'] = instrument_info
            analysis.analysis_metadata['end_time'] = pm.get_end_time()
            
            # Enhanced tempo analysis
            tempo_changes = pm.get_tempo_changes()
            if len(tempo_changes) > 1:
                analysis.analysis_metadata['tempo_changes'] = {
                    'times': tempo_changes[0].tolist(),
                    'tempos': tempo_changes[1].tolist()
                }
            
        except Exception as e:
            self.logger.warning(f"Error in pretty_midi analysis: {e}")
    
    def _calculate_progression_metrics(self, analysis: ProgressionAnalysis):
        """Calculate overall metrics for the progression."""
        if not analysis.chords:
            return
        
        # Calculate complexity score
        complexity_scores = [chord.complexity_score for chord in analysis.chords]
        analysis.complexity_score = sum(complexity_scores) / len(complexity_scores)
        
        # Determine mood indicators
        analysis.mood_indicators = self._analyze_mood_indicators(analysis.chords)
        
        # Detect modulations (simplified)
        if analysis.key_signature:
            # This could be enhanced with more sophisticated modulation detection
            pass
    
    def _analyze_mood_indicators(self, chords: List[ChordInstance]) -> List[str]:
        """Analyze mood indicators from chord progression."""
        mood_indicators = []
        
        # Count chord types
        chord_types = [chord.chord_type for chord in chords]
        type_counts = Counter(chord_types)
        
        # Simple mood classification
        if type_counts.get('min', 0) > type_counts.get('maj', 0):
            mood_indicators.append('melancholic')
        elif type_counts.get('maj', 0) > type_counts.get('min', 0) * 1.5:
            mood_indicators.append('uplifting')
        
        if any('7' in chord_type for chord_type in chord_types):
            mood_indicators.append('sophisticated')
        
        if any('dim' in chord_type for chord_type in chord_types):
            mood_indicators.append('tense')
        
        if any('sus' in chord_type for chord_type in chord_types):
            mood_indicators.append('floating')
        
        return mood_indicators

# Factory function for easy import
def create_midi_analyzer() -> Optional[MIDIChordAnalyzer]:
    """Create a MIDI analyzer instance if dependencies are available."""
    if not MIDO_AVAILABLE:
        logging.error("Cannot create MIDI analyzer: mido library not available")
        return None
    
    return MIDIChordAnalyzer()

if __name__ == "__main__":
    # Test the analyzer
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python midi_chord_analyzer.py <midi_file>")
        sys.exit(1)
    
    analyzer = create_midi_analyzer()
    if not analyzer:
        print("Error: Required dependencies not available")
        sys.exit(1)
    
    result = analyzer.analyze_midi_file(sys.argv[1])
    if result:
        print(f"Analysis of {result.file_path}:")
        print(f"Key: {result.key_signature}")
        print(f"Tempo: {result.tempo}")
        print(f"Chord progression: {' | '.join(result.chord_symbols)}")
        print(f"Complexity: {result.complexity_score:.2f}")
        print(f"Mood: {', '.join(result.mood_indicators)}")
    else:
        print("Analysis failed")
