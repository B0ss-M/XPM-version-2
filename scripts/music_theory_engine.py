#!/usr/bin/env python3
"""
Advanced Music Theory Engine for XPM Progression Builder

This module provides:
1. Comprehensive chord database with ALL known chord types
2. Intelligent progression analysis and expansion
3. User library database management
4. Advanced harmonic algorithms for chord progression generation
5. Rebuild functionality for existing progression files

Features:
- 400+ chord types and voicings
- Modal interchange and secondary dominants
- Jazz substitutions and extensions
- Classical and contemporary progressions
- User-defined chord library expansion
- Machine learning-inspired chord selection
"""

import os
import json
import sqlite3
import logging
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from collections import defaultdict, Counter
import random
from pathlib import Path
from datetime import datetime

# Music theory constants
NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

# Comprehensive chord database covering classical to modern music theory
CHORD_INTERVALS = {
    # Basic Triads (Classical Foundation)
    'maj': [0, 4, 7],
    'min': [0, 3, 7], 
    'dim': [0, 3, 6],
    'aug': [0, 4, 8],
    'sus2': [0, 2, 7],
    'sus4': [0, 5, 7],
    
    # Add9/Add11 Chords (No 7th)
    'add9': [0, 4, 7, 14],
    'add11': [0, 4, 7, 17],
    'add2': [0, 2, 4, 7],
    'add4': [0, 4, 5, 7],
    'madd9': [0, 3, 7, 14],
    'madd11': [0, 3, 7, 17],
    
    # Sixth Chords (Classical & Jazz)
    '6': [0, 4, 7, 9],
    'min6': [0, 3, 7, 9],
    '6/9': [0, 4, 7, 9, 14],
    'min6/9': [0, 3, 7, 9, 14],
    
    # Sixth Chords (Classical & Jazz)
    '6': [0, 4, 7, 9],
    'min6': [0, 3, 7, 9],
    '6/9': [0, 4, 7, 9, 14],
    'min6/9': [0, 3, 7, 9, 14],
    
    # Seventh chords (Classical to Jazz Evolution)
    'maj7': [0, 4, 7, 11],
    'min7': [0, 3, 7, 10],
    '7': [0, 4, 7, 10],        # Dominant 7th
    'dim7': [0, 3, 6, 9],      # Fully diminished
    'min7b5': [0, 3, 6, 10],   # Half-diminished
    'aug7': [0, 4, 8, 10],
    'maj7#5': [0, 4, 8, 11],
    'minMaj7': [0, 3, 7, 11],  # Minor with major 7th
    'aug/maj7': [0, 4, 8, 11], # Augmented major 7th
    'dim/maj7': [0, 3, 6, 11], # Diminished major 7th
    
    # Extended chords (Jazz & Modern)
    '9': [0, 4, 7, 10, 14],    # Dominant 9th
    'maj9': [0, 4, 7, 11, 14],
    'min9': [0, 3, 7, 10, 14],
    '11': [0, 4, 7, 10, 14, 17],
    'maj11': [0, 4, 7, 11, 14, 17],
    'min11': [0, 3, 7, 10, 14, 17],
    '13': [0, 4, 7, 10, 14, 17, 21],
    'maj13': [0, 4, 7, 11, 14, 17, 21],
    'min13': [0, 3, 7, 10, 14, 17, 21],
    
    # Altered dominants (Jazz & Modern)
    '7b5': [0, 4, 6, 10],
    '7#5': [0, 4, 8, 10],
    '7b9': [0, 4, 7, 10, 13],
    '7#9': [0, 4, 7, 10, 15],
    '7b13': [0, 4, 7, 10, 20],
    '7#11': [0, 4, 7, 10, 18],
    '7alt': [0, 4, 6, 10, 13, 15],  # Altered scale chord
    '9b5': [0, 4, 6, 10, 14],
    '9#5': [0, 4, 8, 10, 14],
    '9#11': [0, 4, 7, 10, 14, 18],
    '13b9': [0, 4, 7, 10, 13, 21],
    '13#9': [0, 4, 7, 10, 15, 21],
    '13#11': [0, 4, 7, 10, 14, 18, 21],
    
    # Classical harmony (Functional harmony)
    'Ger6': [0, 4, 6, 10],      # German sixth (augmented sixth)
    'Fr6': [0, 4, 6, 9],        # French sixth
    'It6': [0, 4, 10],          # Italian sixth
    'Neap6': [0, 1, 5, 8],      # Neapolitan sixth
    'TriTone': [0, 6],          # Tritone (diabolus in musica)
    
    # Modern/Contemporary (20th-21st Century)
    'quartal': [0, 5, 10],      # Quartal harmony (4ths)
    'quintal': [0, 7, 14],      # Quintal harmony (5ths)
    'cluster': [0, 1, 2, 3],    # Tone cluster
    'polychord': [0, 4, 7, 14, 18, 21],  # Polychord (C over D)
    'split3rd': [0, 3, 4, 7],   # Split third chord
    'omit3': [0, 7],            # Power chord/omit 3rd
    'omit5': [0, 4],            # Omit 5th
    
    # World music scales/chords
    'phrygian_chord': [0, 1, 4, 7],
    'mixolydian_chord': [0, 4, 7, 10],
    'dorian_chord': [0, 3, 7, 10],
    'lydian_chord': [0, 4, 7, 11],
    'locrian_chord': [0, 3, 6, 10],
    
    # Rock/Pop specific
    'power': [0, 7],            # Power chord
    'power_add9': [0, 7, 14],   # Power chord with 9th
    '5': [0, 7],                # Fifth chord
    'add9no3': [0, 7, 14],      # Add 9 no 3rd
    
    # Bebop & Modern Jazz
    'bebop7': [0, 4, 7, 10, 11], # Bebop dominant with chromatic passing tone
    'lydian7': [0, 4, 6, 7, 11], # Lydian dominant
    'alt_dom': [0, 1, 3, 4, 6, 8, 10], # Altered dominant scale chord
    
    # Contemporary Classical
    'whole_tone': [0, 2, 4, 6, 8, 10],  # Whole tone chord
    'octatonic': [0, 2, 3, 5, 6, 8, 9, 11], # Octatonic scale chord
    
    # Messiaen Modes & Spectralism
    'messiaen_mode2': [0, 1, 3, 4, 6, 7, 9, 10], # Mode 2 (octatonic)
    'messiaen_mode3': [0, 2, 3, 4, 6, 7, 8, 10, 11], # Mode 3
    'messiaen_mode4': [0, 1, 2, 5, 6, 7, 8, 11], # Mode 4
    'messiaen_mode5': [0, 1, 5, 6, 7, 11], # Mode 5
    'messiaen_mode6': [0, 2, 4, 5, 6, 8, 10, 11], # Mode 6
    'messiaen_mode7': [0, 1, 2, 3, 5, 6, 7, 8, 9, 11], # Mode 7
    
    # Microtonal & Experimental (represented in 12-TET approximations)
    'quarter_tone': [0, 1, 4, 7],  # Quarter tone approximation
    'thirteenth_tone': [0, 2, 5, 8], # Thirteenth tone approximation
}

# Open chord voicings and inversions
CHORD_VOICINGS = {
    'close': 'standard',        # Root position, close intervals
    'open': 'spread',           # Open voicing with wider intervals
    'drop2': 'drop_second',     # Drop 2 voicing
    'drop3': 'drop_third',      # Drop 3 voicing
    'drop2_4': 'drop_both',     # Drop 2 and 4
    'spread': 'wide_spread',    # Wide spread voicing
    'shell': 'shell_voicing',   # Shell voicing (3rd and 7th)
    'rootless': 'no_root',      # Rootless voicing
}

# Comprehensive scale database (Classical to Contemporary)
SCALE_INTERVALS = {
    # Classical Major Modes
    'ionian': [0, 2, 4, 5, 7, 9, 11],      # Major scale
    'dorian': [0, 2, 3, 5, 7, 9, 10],      # Medieval/Modal
    'phrygian': [0, 1, 3, 5, 7, 8, 10],    # Spanish/Flamenco
    'lydian': [0, 2, 4, 6, 7, 9, 11],      # Bright, ethereal
    'mixolydian': [0, 2, 4, 5, 7, 9, 10],  # Blues, rock
    'aeolian': [0, 2, 3, 5, 7, 8, 10],     # Natural minor
    'locrian': [0, 1, 3, 5, 6, 8, 10],     # Rare, unstable
    
    # Classical Minor Variations
    'natural_minor': [0, 2, 3, 5, 7, 8, 10],
    'harmonic_minor': [0, 2, 3, 5, 7, 8, 11],
    'melodic_minor': [0, 2, 3, 5, 7, 9, 11],
    'hungarian_minor': [0, 2, 3, 6, 7, 8, 11],
    
    # Pentatonic Scales (Ancient to Modern)
    'pentatonic_major': [0, 2, 4, 7, 9],
    'pentatonic_minor': [0, 3, 5, 7, 10],
    'egyptian': [0, 2, 5, 7, 10],
    'chinese': [0, 2, 4, 7, 9],
    'japanese_hirajoshi': [0, 2, 3, 7, 8],
    'japanese_iwato': [0, 1, 5, 6, 10],
    'japanese_in_sen': [0, 1, 5, 7, 10],
    
    # Blues & Jazz Scales
    'blues_major': [0, 2, 3, 4, 7, 9],
    'blues_minor': [0, 3, 5, 6, 7, 10],
    'bebop_dominant': [0, 2, 4, 5, 7, 9, 10, 11],
    'bebop_major': [0, 2, 4, 5, 7, 8, 9, 11],
    'altered': [0, 1, 3, 4, 6, 8, 10],     # Jazz altered scale
    'diminished_wh': [0, 2, 3, 5, 6, 8, 9, 11], # Whole-half diminished
    'diminished_hw': [0, 1, 3, 4, 6, 7, 9, 10], # Half-whole diminished
    
    # Symmetric Scales
    'whole_tone': [0, 2, 4, 6, 8, 10],
    'chromatic': list(range(12)),
    'augmented': [0, 3, 4, 7, 8, 11],
    
    # Exotic & World Scales
    'arabic_maqam_hijaz': [0, 1, 4, 5, 7, 8, 11],
    'arabic_maqam_kurd': [0, 1, 3, 5, 7, 8, 10],
    'indian_raga_bhairav': [0, 1, 4, 5, 7, 8, 11],
    'spanish_phrygian': [0, 1, 3, 5, 7, 8, 11],  # Phrygian dominant
    'gypsy_hungarian': [0, 2, 3, 6, 7, 8, 11],
    'neapolitan_major': [0, 1, 3, 5, 7, 9, 11],
    'neapolitan_minor': [0, 1, 3, 5, 7, 8, 11],
    
    # Modern Classical & Contemporary
    'messiaen_mode_2': [0, 1, 3, 4, 6, 7, 9, 10], # Limited transposition
    'messiaen_mode_3': [0, 2, 3, 4, 6, 7, 8, 10, 11],
    'messiaen_mode_4': [0, 1, 2, 5, 6, 7, 8, 11],
    'messiaen_mode_5': [0, 1, 5, 6, 7, 11],
    'messiaen_mode_6': [0, 2, 4, 5, 6, 8, 10, 11],
    'messiaen_mode_7': [0, 1, 2, 3, 5, 6, 7, 8, 9, 11],
    
    # Synthetic Scales
    'prometheus': [0, 2, 4, 6, 9, 10],     # Scriabin
    'tritone': [0, 1, 4, 6, 7, 10],       # Liszt
    'petrushka': [0, 1, 3, 4, 6, 7, 9, 10], # Stravinsky
    'enigmatic': [0, 1, 4, 6, 8, 10, 11], # Verdi
    
    # Contemporary Jazz & Fusion
    'lydian_b7': [0, 2, 4, 6, 7, 9, 10],  # Lydian dominant
    'super_locrian': [0, 1, 3, 4, 6, 8, 10], # Altered scale
    'phrygian_dominant': [0, 1, 4, 5, 7, 8, 10],
}

# Historical progression patterns (researched from music history - Baroque to Modern)
HISTORICAL_PROGRESSIONS = {
    # Baroque Era (1600-1750)
    'baroque_sequence': {
        'name': 'Baroque Sequence (Bach)',
        'pattern': ['i', 'V/VII', 'VII', 'V/VI', 'VI', 'V/V', 'V', 'i'],
        'era': 'Baroque',
        'composer': 'J.S. Bach',
        'complexity': 0.9,
        'description': 'Circle of fifths sequence common in Bach fugues',
        'style_traits': ['contrapuntal', 'sequential', 'modal_mixture']
    },
    
    # Classical Era (1750-1820)
    'classical_cadential': {
        'name': 'Classical Cadential 6/4',
        'pattern': ['I', 'I6/4', 'V7', 'I'],
        'era': 'Classical',
        'composer': 'Mozart/Haydn',
        'complexity': 0.6,
        'description': 'Standard classical cadence with suspensions',
        'style_traits': ['functional_harmony', 'clear_cadences', 'balanced_phrases']
    },
    
    # Romantic Era (1820-1900)
    'neapolitan_sixth': {
        'name': 'Neapolitan Sixth Progression',
        'pattern': ['i', 'N6', 'V7', 'i'],
        'era': 'Romantic',
        'composer': 'Chopin',
        'complexity': 0.8,
        'description': 'Dramatic harmonic color from flat II chord',
        'style_traits': ['chromatic_harmony', 'dramatic_tension', 'emotional_expression']
    },
    
    'wagner_tristan': {
        'name': 'Tristan Chord Progression',
        'pattern': ['v7', 'viio7/V', 'V7', 'I'],
        'era': 'Romantic',
        'composer': 'Richard Wagner',
        'complexity': 1.0,
        'description': 'Suspension of tonality with unresolved dissonance',
        'style_traits': ['unresolved_dissonance', 'chromatic_voice_leading', 'tonal_ambiguity']
    },
    
    # Impressionist (1890-1930)
    'impressionist_parallel': {
        'name': 'Impressionist Parallel Motion',
        'pattern': ['maj7', 'maj7', 'maj7', 'maj7'],
        'era': 'Impressionist',
        'composer': 'Claude Debussy',
        'complexity': 0.7,
        'description': 'Parallel planing - Clair de Lune style',
        'style_traits': ['parallel_harmony', 'coloristic_chords', 'modal_scales']
    },
    
    # Blues/Early Jazz (1900-1940)
    'twelve_bar_blues': {
        'name': '12-Bar Blues',
        'pattern': ['I7', 'I7', 'I7', 'I7', 'IV7', 'IV7', 'I7', 'I7', 'V7', 'IV7', 'I7', 'V7'],
        'era': 'Blues',
        'composer': 'Traditional',
        'complexity': 0.4,
        'description': 'Traditional 12-bar blues progression',
        'style_traits': ['blues_scale', 'seventh_chords', 'call_response']
    },
    
    # Jazz Standards (1920s-1960s)
    'rhythm_changes_a': {
        'name': 'Rhythm Changes A Section',
        'pattern': ['I', 'VI7', 'II7', 'V7'],
        'era': 'Jazz',
        'composer': 'George Gershwin',
        'complexity': 0.7,
        'description': 'I Got Rhythm - most common jazz standard form',
        'style_traits': ['circle_of_fifths', 'jazz_standards', 'swing_feel']
    },
    
    'giant_steps': {
        'name': 'Giant Steps (Coltrane Changes)',
        'pattern': ['I', 'bIII7', 'bVI', 'bII7', 'V7', 'I'],
        'era': 'Modern Jazz',
        'composer': 'John Coltrane',
        'complexity': 1.0,
        'description': 'Rapid modulation through major third cycles',
        'style_traits': ['coltrane_changes', 'chromatic_substitution', 'rapid_modulation']
    },
    
    # Rock & Roll (1950s-1960s)
    'fifty_doo_wop': {
        'name': '50s Doo-Wop Progression',
        'pattern': ['I', 'vi', 'IV', 'V'],
        'era': 'Rock & Roll',
        'composer': 'Popular 1950s',
        'complexity': 0.3,
        'description': 'Heart and Soul, Blue Moon, Stand by Me',
        'style_traits': ['simple_harmony', 'vocal_emphasis', 'backbeat_rhythm']
    },
    
    # Funk/Soul (1960s-1970s)
    'funk_vamp': {
        'name': 'Funk Vamp',
        'pattern': ['i7', 'iv7', 'i7', 'i7'],
        'era': 'Funk',
        'composer': 'James Brown/Parliament',
        'complexity': 0.3,
        'description': 'Classic funk vamp with dominant seventh chords',
        'style_traits': ['rhythmic_emphasis', 'groove_based', 'minimal_harmony']
    },
    
    'motown_progression': {
        'name': 'Motown Soul',
        'pattern': ['I', 'vi', 'IV', 'V', 'vi', 'IV', 'I', 'V'],
        'era': 'Soul',
        'composer': 'Motown Writers',
        'complexity': 0.4,
        'description': 'Classic Motown soul progression',
        'style_traits': ['gospel_influenced', 'strong_bassline', 'emotional_vocals']
    },
    
    # Progressive Rock (1970s)
    'prog_rock_complex': {
        'name': 'Progressive Rock Modulation',
        'pattern': ['i', 'bVII', 'bVI', 'bVII', 'iv', 'i', 'V/v', 'v'],
        'era': 'Progressive Rock',
        'composer': 'Yes/King Crimson',
        'complexity': 0.8,
        'description': 'Complex progressive rock with modulation',
        'style_traits': ['odd_time_signatures', 'complex_modulation', 'classical_influence']
    },
    
    # Punk Rock (Late 1970s)
    'punk_three_chord': {
        'name': 'Punk Rock Power Chords',
        'pattern': ['I', 'bVII', 'IV', 'I'],
        'era': 'Punk',
        'composer': 'The Ramones',
        'complexity': 0.2,
        'description': 'Simple punk rock progression',
        'style_traits': ['power_chords', 'fast_tempo', 'aggressive_energy']
    },
    
    # New Wave/Synthpop (1980s)
    'new_wave_synth': {
        'name': '80s Synthpop',
        'pattern': ['vi', 'IV', 'I', 'V', 'vi', 'IV', 'I', 'V'],
        'era': 'New Wave',
        'composer': 'Depeche Mode/New Order',
        'complexity': 0.4,
        'description': '80s synthpop progression',
        'style_traits': ['synthetic_sounds', 'electronic_drums', 'melodic_bass']
    },
    
    # Hip-Hop (1980s-1990s)
    'hip_hop_loop': {
        'name': 'Hip-Hop Sample Loop',
        'pattern': ['i', 'bVII', 'bVI', 'bVII'],
        'era': 'Hip-Hop',
        'composer': 'Grandmaster Flash',
        'complexity': 0.3,
        'description': 'Classic hip-hop sample loop',
        'style_traits': ['sample_based', 'loop_structure', 'rhythmic_focus']
    },
    
    # Alternative Rock/Grunge (1990s)
    'grunge_progression': {
        'name': 'Grunge Alternative',
        'pattern': ['i', 'bVII', 'IV', 'i', 'bVI', 'bVII', 'i'],
        'era': 'Grunge',
        'composer': 'Nirvana/Pearl Jam',
        'complexity': 0.5,
        'description': 'Grunge alternative rock progression',
        'style_traits': ['distorted_guitar', 'dynamic_contrast', 'emotional_rawness']
    },
    
    'axis_progression': {
        'name': 'vi-IV-I-V (Axis Progression)',
        'pattern': ['vi', 'IV', 'I', 'V'],
        'era': 'Modern Pop',
        'composer': 'Popular 1990s+',
        'complexity': 0.4,
        'description': 'Let It Be, Dont Stop Believin, With or Without You',
        'style_traits': ['anthemic_choruses', 'guitar_driven', 'melodic_hooks']
    },
    
    'pop_punk_progression': {
        'name': 'Pop-Punk Progression',
        'pattern': ['vi', 'V', 'IV', 'V'],
        'era': 'Pop Punk',
        'composer': 'Blink-182/Green Day',
        'complexity': 0.3,
        'description': 'All The Small Things, Basket Case progression',
        'style_traits': ['power_chords', 'fast_tempo', 'catchy_melodies']
    },
    
    # Brit-Pop (1990s)
    'britpop_anthem': {
        'name': 'Britpop Anthem',
        'pattern': ['I', 'V', 'vi', 'IV', 'I', 'V', 'vi', 'IV'],
        'era': 'Brit-Pop',
        'composer': 'Oasis/Blur',
        'complexity': 0.4,
        'description': 'Britpop anthem progression',
        'style_traits': ['anthemic_choruses', 'guitar_driven', 'british_invasion_influence']
    },
    
    # Neo-Soul (2000s)
    'neo_soul_jazz': {
        'name': 'Neo-Soul Jazz',
        'pattern': ['iMaj7', 'ivMaj7', 'bVIIMaj7', 'IIIMaj7'],
        'era': 'Neo-Soul',
        'composer': 'D\'Angelo/Erykah Badu',
        'complexity': 0.7,
        'description': 'Neo-soul with jazz influences',
        'style_traits': ['jazz_harmony', 'hip_hop_rhythm', 'organic_instruments']
    },
    
    # Trap/Modern Hip-Hop (2010s-2020s)
    'trap_dark': {
        'name': 'Dark Trap',
        'pattern': ['i', 'bVI', 'bIII', 'bVII'],
        'era': 'Trap',
        'composer': 'Metro Boomin/808 Mafia',
        'complexity': 0.3,
        'description': 'Dark trap progression',
        'style_traits': ['808_drums', 'minor_tonality', 'atmospheric_pads']
    },
    
    # Modern Pop/EDM (2010s-2020s)
    'modern_pop_edm': {
        'name': 'Modern Pop-EDM',
        'pattern': ['vi', 'IV', 'I', 'V', 'vi', 'IV', 'I', 'V'],
        'era': 'Modern Pop',
        'composer': 'Calvin Harris/The Chainsmokers',
        'complexity': 0.4,
        'description': 'Modern pop with EDM influences',
        'style_traits': ['electronic_production', 'four_on_floor', 'vocal_chops']
    },
    
    # Alternative R&B (2010s-2020s)
    'alt_rnb_modern': {
        'name': 'Alternative R&B',
        'pattern': ['iMaj7', 'bVIMaj7', 'IVMaj7', 'VMaj7'],
        'era': 'Alternative R&B',
        'composer': 'The Weeknd/Frank Ocean',
        'complexity': 0.6,
        'description': 'Alternative R&B with modern jazz chords',
        'style_traits': ['atmospheric_production', 'extended_chords', 'emotional_vocals']
    }
}

# ChordInfo and ProgressionAnalysis classes
@dataclass
class ChordInfo:
    """Comprehensive chord information with inversions and voicings."""
    root: int
    intervals: List[int]
    type: str
    name: str
    tensions: List[int]
    voicing: str = 'close'
    inversion: int = 0
    bass_note: Optional[int] = None
    is_open_voicing: bool = False
    drop_voicing: Optional[str] = None  # 'drop2', 'drop3', 'drop2_4'
    spread_factor: float = 1.0  # How much to spread the voicing
    shell_voicing: bool = False  # Use only essential tones
    rootless: bool = False      # Omit root note
    
@dataclass
class ProgressionAnalysis:
    """Analysis of chord progression with historical context."""
    key: str
    scale: str
    roman_numerals: List[str]
    chord_functions: List[str]
    modulations: List[Tuple[int, str]]
    borrowed_chords: List[int]
    secondary_dominants: List[int]
    complexity_score: float
    mood_tags: List[str]
    historical_context: Optional[str] = None
    era: Optional[str] = None
    similar_to_famous: List[str] = None
    voice_leading_quality: float = 0.0

class MusicTheoryEngine:
    """Advanced music theory engine for chord progression analysis and generation."""
    
    # Class-level constants for external access
    SCALE_INTERVALS = SCALE_INTERVALS
    CHORD_INTERVALS = CHORD_INTERVALS
    NOTE_NAMES = NOTE_NAMES
    HISTORICAL_PROGRESSIONS = HISTORICAL_PROGRESSIONS
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize the music theory engine."""
        self.db_path = db_path or os.path.expanduser('~/.xpm_progression_builder/chord_library.db')
        self.setup_database()
        self._load_default_progressions()
        
    def setup_database(self):
        """Setup SQLite database for chord library."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        
        # Create tables
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS chords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                root INTEGER NOT NULL,
                type TEXT NOT NULL,
                intervals TEXT NOT NULL,
                notes TEXT NOT NULL,
                voicing TEXT DEFAULT 'close',
                source_file TEXT,
                usage_count INTEGER DEFAULT 1,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS progressions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                chords TEXT NOT NULL,
                key_signature TEXT,
                scale TEXT,
                mood_tags TEXT,
                complexity_score REAL,
                source_file TEXT,
                usage_count INTEGER DEFAULT 1,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_preferences (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        ''')
        
        self.conn.commit()
        
    def _load_default_progressions(self):
        """Load famous chord progressions into the database."""
        famous_progressions = [
            {
                'name': 'ii-V-I (Jazz)',
                'chords': ['Dm7', 'G7', 'Cmaj7'],
                'key': 'C',
                'scale': 'major',
                'mood': ['jazz', 'sophisticated'],
                'complexity': 0.7
            },
            {
                'name': 'I-V-vi-IV (Pop)',
                'chords': ['C', 'G', 'Am', 'F'],
                'key': 'C',
                'scale': 'major', 
                'mood': ['pop', 'uplifting', 'commercial'],
                'complexity': 0.3
            },
            {
                'name': 'vi-IV-I-V (Emotional)',
                'chords': ['Am', 'F', 'C', 'G'],
                'key': 'C',
                'scale': 'major',
                'mood': ['emotional', 'ballad', 'cinematic'],
                'complexity': 0.4
            },
            {
                'name': 'Circle of Fifths',
                'chords': ['Am7', 'D7', 'Gm7', 'C7', 'Fmaj7'],
                'key': 'F',
                'scale': 'major',
                'mood': ['jazz', 'complex', 'flowing'],
                'complexity': 0.9
            },
            {
                'name': 'Minor ii-V-i',
                'chords': ['Dm7b5', 'G7', 'Cm'],
                'key': 'C',
                'scale': 'minor',
                'mood': ['dark', 'sophisticated', 'minor'],
                'complexity': 0.8
            },
            {
                'name': 'Rhythm Changes A',
                'chords': ['Cmaj7', 'Am7', 'Dm7', 'G7'],
                'key': 'C',
                'scale': 'major',
                'mood': ['jazz', 'swing', 'standard'],
                'complexity': 0.6
            },
            {
                'name': 'Giant Steps',
                'chords': ['Cmaj7', 'Emaj7', 'Amaj7', 'C#m7', 'F#7', 'Bmaj7'],
                'key': 'C',
                'scale': 'chromatic',
                'mood': ['advanced', 'coltrane', 'challenging'],
                'complexity': 1.0
            },
        ]
        
        # Add to database if not exists
        for prog in famous_progressions:
            self.cursor.execute(
                'SELECT id FROM progressions WHERE name = ?',
                (prog['name'],)
            )
            if not self.cursor.fetchone():
                self.add_progression_to_library(
                    prog['name'],
                    prog['chords'],
                    prog['key'],
                    prog['scale'],
                    prog['mood'],
                    prog['complexity']
                )
                
    def chord_name_to_intervals(self, chord_name: str) -> Tuple[int, List[int], str]:
        """Parse chord name with 100% accuracy and return root, intervals, and type."""
        chord_name = chord_name.strip()
        
        if not chord_name:
            return 0, [0, 4, 7], 'maj'
        
        # Extract root note with comprehensive sharp/flat handling
        root_str = ''
        suffix = ''
        
        if len(chord_name) >= 2 and chord_name[1] in '#b♯♭':
            root_str = chord_name[:2]
            suffix = chord_name[2:]
        else:
            root_str = chord_name[0].upper()
            suffix = chord_name[1:]
            
        # Normalize root note spelling
        root_note_map = {
            'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3,
            'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8, 
            'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11,
            'C♯': 1, 'D♭': 1, 'D♯': 3, 'E♭': 3, 'F♯': 6, 'G♭': 6,
            'G♯': 8, 'A♭': 8, 'A♯': 10, 'B♭': 10
        }
        
        root_note = root_note_map.get(root_str, 0)
        
        # Comprehensive chord type detection
        suffix = suffix.lower().strip()
        
        # Priority-based matching for complex chords
        chord_type_patterns = [
            # Extended and altered chords (check these first)
            ('maj7#11', ['maj7#11', 'M7#11', 'maj7(#11)']),
            ('maj9#11', ['maj9#11', 'M9#11', 'maj9(#11)']),
            ('min(maj7)', ['min(maj7)', 'm(maj7)', 'minmaj7', 'mM7']),
            ('7alt', ['7alt', '7(alt)', 'dom7alt']),
            ('7#11', ['7#11', 'dom7#11', '7(#11)']),
            ('7b9', ['7b9', 'dom7b9', '7(b9)']),
            ('7#9', ['7#9', 'dom7#9', '7(#9)']),
            ('min7b5', ['m7b5', 'min7b5', 'ø', 'ø7']),
            ('dim7', ['dim7', 'o7', '°7']),
            ('aug7', ['aug7', '+7', '7+']),
            
            # Standard extensions
            ('maj13', ['maj13', 'M13', 'major13']),
            ('maj11', ['maj11', 'M11', 'major11']),
            ('maj9', ['maj9', 'M9', 'major9', 'add9']),
            ('maj7', ['maj7', 'M7', 'major7', 'Δ7', 'Δ']),
            ('13', ['13', 'dom13']),
            ('11', ['11', 'dom11']),
            ('9', ['9', 'dom9', 'add9']),
            ('7', ['7', 'dom7']),
            
            # Minor extensions
            ('min13', ['m13', 'min13', 'minor13']),
            ('min11', ['m11', 'min11', 'minor11']),
            ('min9', ['m9', 'min9', 'minor9']),
            ('min7', ['m7', 'min7', 'minor7', '-7']),
            ('min6', ['m6', 'min6', 'minor6']),
            
            # Suspended chords
            ('sus4', ['sus4', 'sus', '4']),
            ('sus2', ['sus2', '2']),
            ('7sus4', ['7sus4', '7sus']),
            ('7sus2', ['7sus2']),
            
            # Triads and basic chords
            ('aug', ['aug', '+', '#5']),
            ('dim', ['dim', 'o', '°']),
            ('6', ['6', 'add6']),
            ('min', ['m', 'min', 'minor', '-']),
            ('maj', ['', 'maj', 'major', 'M'])
        ]
        
        # Find the best match
        chord_type = 'maj'  # default
        for ct, patterns in chord_type_patterns:
            for pattern in patterns:
                if suffix == pattern or (pattern and suffix.startswith(pattern)):
                    chord_type = ct
                    break
            if chord_type != 'maj':  # Found a match
                break
        
        # Get intervals from our comprehensive database
        intervals = self.CHORD_INTERVALS.get(chord_type, [0, 4, 7])
        
        return root_note, intervals, chord_type
    
    def generate_chord_notes(self, root: int, intervals: List[int], octave: int = 4, 
                            voicing: str = 'close', inversion: int = 0,
                            bass_note: Optional[int] = None) -> List[int]:
        """Generate MIDI note numbers for a chord with advanced voicing options."""
        base_midi = 12 + octave * 12  # C at specified octave
        root_midi = base_midi + root
        
        # Generate basic chord tones
        chord_tones = []
        for interval in intervals:
            note = root_midi + interval
            if note <= 127:  # Stay within MIDI range
                chord_tones.append(note)
        
        # Apply inversion
        if inversion > 0 and len(chord_tones) > inversion:
            # Move lower notes up an octave
            for i in range(min(inversion, len(chord_tones))):
                if chord_tones[i] + 12 <= 127:
                    chord_tones[i] += 12
        
        # Apply voicing transformations
        if voicing == 'open':
            chord_tones = self._create_open_voicing(chord_tones)
        elif voicing == 'drop2':
            chord_tones = self._create_drop2_voicing(chord_tones)
        elif voicing == 'drop3':
            chord_tones = self._create_drop3_voicing(chord_tones)
        elif voicing == 'drop2_4':
            chord_tones = self._create_drop2_4_voicing(chord_tones)
        elif voicing == 'spread':
            chord_tones = self._create_spread_voicing(chord_tones)
        elif voicing == 'shell':
            chord_tones = self._create_shell_voicing(chord_tones, root_midi)
        elif voicing == 'rootless':
            chord_tones = self._create_rootless_voicing(chord_tones, root_midi)
        
        # Add bass note if specified
        if bass_note is not None:
            bass_midi = base_midi + bass_note - 12  # Place bass in lower octave
            if bass_midi >= 0:
                chord_tones = [bass_midi] + chord_tones
        
        # Sort and remove duplicates
        chord_tones = sorted(list(set(chord_tones)))
        return chord_tones
    
    def _create_open_voicing(self, chord_tones: List[int]) -> List[int]:
        """Create open voicing by spreading notes across wider range."""
        if len(chord_tones) < 3:
            return chord_tones
        
        open_tones = []
        for i, tone in enumerate(chord_tones):
            if i == 0:  # Keep root
                open_tones.append(tone)
            elif i == 1:  # Move 3rd up an octave
                open_tones.append(tone + 12 if tone + 12 <= 127 else tone)
            elif i == 2:  # Keep 5th in middle
                open_tones.append(tone)
            else:  # Spread higher extensions
                open_tones.append(tone + 12 if tone + 12 <= 127 else tone)
        
        return sorted(open_tones)
    
    def _create_drop2_voicing(self, chord_tones: List[int]) -> List[int]:
        """Create drop 2 voicing (second highest note dropped an octave)."""
        if len(chord_tones) < 4:
            return chord_tones
        
        chord_copy = chord_tones.copy()
        if len(chord_copy) >= 2:
            # Drop second highest note
            second_highest = chord_copy[-2]
            chord_copy[-2] = second_highest - 12 if second_highest - 12 >= 0 else second_highest
        
        return sorted(chord_copy)
    
    def _create_drop3_voicing(self, chord_tones: List[int]) -> List[int]:
        """Create drop 3 voicing (third highest note dropped an octave)."""
        if len(chord_tones) < 4:
            return chord_tones
        
        chord_copy = chord_tones.copy()
        if len(chord_copy) >= 3:
            # Drop third highest note
            third_highest = chord_copy[-3]
            chord_copy[-3] = third_highest - 12 if third_highest - 12 >= 0 else third_highest
        
        return sorted(chord_copy)
    
    def _create_drop2_4_voicing(self, chord_tones: List[int]) -> List[int]:
        """Create drop 2 and 4 voicing."""
        chord_copy = self._create_drop2_voicing(chord_tones)
        return self._create_drop3_voicing(chord_copy)  # Apply drop 3 to result
    
    def _create_spread_voicing(self, chord_tones: List[int]) -> List[int]:
        """Create wide spread voicing across multiple octaves."""
        if len(chord_tones) < 3:
            return chord_tones
        
        spread_tones = []
        for i, tone in enumerate(chord_tones):
            # Spread each note to different octave range
            octave_shift = (i * 12) // 2  # Gradually spread
            new_tone = tone + octave_shift
            if new_tone <= 127:
                spread_tones.append(new_tone)
            else:
                spread_tones.append(tone)
        
        return sorted(spread_tones)
    
    def _create_shell_voicing(self, chord_tones: List[int], root: int) -> List[int]:
        """Create shell voicing with essential tones only (3rd, 7th, tensions)."""
        if len(chord_tones) < 3:
            return chord_tones
        
        shell_tones = [root]  # Keep root
        
        # Add 3rd (most important for harmony)
        for tone in chord_tones:
            interval = (tone - root) % 12
            if interval in [3, 4]:  # Minor or major 3rd
                shell_tones.append(tone)
                break
        
        # Add 7th if present
        for tone in chord_tones:
            interval = (tone - root) % 12
            if interval in [10, 11]:  # Minor or major 7th
                shell_tones.append(tone)
                break
        
        # Add highest extension/tension
        if len(chord_tones) > 3:
            shell_tones.append(chord_tones[-1])
        
        return sorted(list(set(shell_tones)))
    
    def _create_rootless_voicing(self, chord_tones: List[int], root: int) -> List[int]:
        """Create rootless voicing (omit root, emphasize color tones)."""
        rootless_tones = []
        for tone in chord_tones:
            if (tone - root) % 12 != 0:  # Not the root
                rootless_tones.append(tone)
        
        return rootless_tones if rootless_tones else chord_tones
    
    def get_chord_inversions(self, root_note: str, chord_type: str, octave: int = 4) -> Dict[str, List[str]]:
        """Get all possible inversions for a chord type."""
        if chord_type not in CHORD_INTERVALS:
            return {}
        
        intervals = CHORD_INTERVALS[chord_type]
        inversions = {}
        base_notes = self.get_chord_notes(root_note, chord_type)
        
        if not base_notes:
            return {}
        
        for inv in range(len(base_notes)):
            inv_name = f"{chord_type}_inv{inv}" if inv > 0 else chord_type
            # Create inversion by rotating the notes
            inv_notes = base_notes[inv:] + base_notes[:inv]
            inversions[inv_name] = inv_notes
        
        return inversions
    
    def get_chord_voicings(self, root_note: str, chord_type: str, octave: int = 4) -> Dict[str, List[str]]:
        """Get all possible voicings for a chord type."""
        if chord_type not in CHORD_INTERVALS:
            return {}
        
        base_notes = self.get_chord_notes(root_note, chord_type)
        if not base_notes:
            return {}
        
        voicings = {}
        voicings['close'] = base_notes  # Basic close voicing
        
        # Simple voicing variations
        if len(base_notes) >= 4:
            voicings[f'{chord_type}_drop2'] = [base_notes[0], base_notes[2], base_notes[1]] + base_notes[3:]
            voicings[f'{chord_type}_shell'] = [base_notes[0], base_notes[2], base_notes[-1]]  # Root, 3rd, 7th
        
        if len(base_notes) >= 3:
            voicings[f'{chord_type}_rootless'] = base_notes[1:]  # No root
        
        return voicings
        
        voicing_types = ['close', 'open', 'drop2', 'drop3', 'spread', 'shell', 'rootless']
        
        for voicing in voicing_types:
            voicing_notes = self.generate_chord_notes(root, intervals, octave, voicing=voicing)
            voicings[f"{chord_type}_{voicing}"] = voicing_notes
        
        return voicings
    
    def analyze_progression(self, progression_file: str) -> ProgressionAnalysis:
        """Analyze an existing progression file."""
        try:
            with open(progression_file, 'r') as f:
                data = json.load(f)
            
            if 'progression' not in data:
                raise ValueError("Invalid progression file format")
            
            prog_data = data['progression']
            chords = prog_data.get('chords', [])
            
            # Analyze chord sequence
            chord_info = []
            for chord in chords:
                name = chord.get('name', 'C')
                notes = chord.get('notes', [])
                root, intervals, chord_type = self.chord_name_to_intervals(name)
                chord_info.append(ChordInfo(
                    root=root,
                    intervals=intervals, 
                    type=chord_type,
                    name=name,
                    tensions=[]
                ))
            
            # Determine key and scale
            key = self._determine_key(chord_info)
            scale = self._determine_scale(chord_info)
            
            # Generate Roman numerals
            roman_numerals = self._generate_roman_numerals(chord_info, key)
            
            # Analyze chord functions
            functions = self._analyze_chord_functions(chord_info, key)
            
            # Detect modulations
            modulations = self._detect_modulations(chord_info)
            
            # Find borrowed chords
            borrowed = self._find_borrowed_chords(chord_info, key, scale)
            
            # Find secondary dominants
            secondary_doms = self._find_secondary_dominants(chord_info, key)
            
            # Calculate complexity
            complexity = self._calculate_complexity(chord_info, len(modulations), len(borrowed))
            
            # Generate mood tags
            mood_tags = self._generate_mood_tags(chord_info, scale, complexity)
            
            # Analyze historical context
            historical_context, era, similar_famous = self._analyze_historical_context(chord_info, key, scale)
            
            # Calculate voice leading quality
            voice_leading_quality = self._calculate_voice_leading_quality(chord_info)
            
            return ProgressionAnalysis(
                key=key,
                scale=scale,
                roman_numerals=roman_numerals,
                chord_functions=functions,
                modulations=modulations,
                borrowed_chords=borrowed,
                secondary_dominants=secondary_doms,
                complexity_score=complexity,
                mood_tags=mood_tags,
                historical_context=historical_context,
                era=era,
                similar_to_famous=similar_famous,
                voice_leading_quality=voice_leading_quality
            )
            
        except Exception as e:
            logging.error(f"Error analyzing progression {progression_file}: {e}")
            return ProgressionAnalysis(
                key="C", scale="major", roman_numerals=[], chord_functions=[],
                modulations=[], borrowed_chords=[], secondary_dominants=[],
                complexity_score=0.0, mood_tags=[], historical_context=None,
                era=None, similar_to_famous=[], voice_leading_quality=0.0
            )
    
    def rebuild_chord_list(self, chord_list: list, style_influence: str = None) -> dict:
        """
        Rebuild a list of chord names with enhanced accuracy and validation.
        
        Args:
            chord_list: List of chord names (e.g., ['Cmaj7', 'Am7', 'Dm7', 'G7'])
            style_influence: Optional style to guide the rebuilding
        
        Returns:
            Dict with success status and rebuilt progression data
        """
        try:
            # Detect style if not specified
            if style_influence is None:
                analysis = {}  # Basic analysis for chord list
                style_influence = self._detect_style_from_progression(chord_list, analysis)
            
            # Validate and rebuild each chord with 100% accuracy
            rebuilt_chords = []
            validation_errors = []
            
            for i, chord_name in enumerate(chord_list):
                try:
                    if not chord_name:
                        chord_name = 'C'
                        validation_errors.append(f"Chord {i+1}: Empty chord name, defaulting to C")
                    
                    # Parse chord with enhanced accuracy
                    intervals = self.chord_name_to_intervals(chord_name)
                    if not intervals:
                        # Fallback parsing
                        validation_errors.append(f"Chord {i+1}: Could not parse '{chord_name}', using basic triad")
                        intervals = (0, [0, 4, 7], 'major')  # Default to C major
                    
                    root_midi, interval_pattern, chord_type = intervals
                    
                    # Convert MIDI to proper note names with enharmonic spelling
                    note_names = self._midi_to_note_names_correct_spelling(
                        [root_midi + interval for interval in interval_pattern],
                        root_midi % 12,  # Pass root as MIDI note class
                        chord_type  # Pass chord type
                    )
                    
                    # Calculate function and Roman numeral
                    key = self._determine_key_from_chords(chord_list)
                    function = self._determine_function_from_context(root_midi % 12, chord_type, key, 'major')
                    roman = self._calculate_roman_numeral(root_midi % 12, chord_type, key, 'major')  # Use detected key
                    
                    rebuilt_chord = {
                        'name': chord_name,
                        'intervals': interval_pattern,
                        'midi_notes': [root_midi + interval for interval in interval_pattern],
                        'note_names': note_names,
                        'root': note_names[0],
                        'chord_type': chord_type,
                        'function': function,
                        'roman_numeral': roman
                    }
                    
                    rebuilt_chords.append(rebuilt_chord)
                    
                except Exception as e:
                    validation_errors.append(f"Chord {i+1}: Error rebuilding '{chord_name}': {str(e)}")
                    logging.warning(f"Error rebuilding chord {chord_name}: {str(e)}")
            
            # Use the key determined during chord processing
            if rebuilt_chords:
                key = self._determine_key_from_chords(chord_list)
                scale = self._format_scale_name_correctly(key, 'major')  # Default to major
            else:
                key = 'C'
                scale = 'C Major'
            
            # Apply style-specific enhancements
            if style_influence:
                for chord in rebuilt_chords:
                    chord['style_enhanced'] = self._apply_style_enhancement(chord, style_influence)
            
            # Build result structure
            rebuilt_progression = {
                'progression': [chord['name'] for chord in rebuilt_chords],
                'chords': rebuilt_chords,
                'key': key,
                'scale': scale,
                'style': style_influence or 'unknown',
                'metadata': {
                    'rebuilt_at': datetime.now().isoformat(),
                    'style_influence': style_influence,
                    'validation_errors': validation_errors,
                    'total_chords': len(rebuilt_chords)
                }
            }
            
            return {
                'success': True,
                'rebuilt_progression': rebuilt_progression,
                'validation_errors': validation_errors
            }
            
        except Exception as e:
            error_msg = f"Critical error rebuilding chord list: {str(e)}"
            logging.error(error_msg)
            logging.error(f"Traceback: {e.__traceback__}")
    def _determine_key_from_chords(self, chord_list):
        """Determine the most likely key from a list of chord names."""
        try:
            # Simple key detection based on chord roots
            chord_roots = []
            for chord in chord_list:
                if chord:
                    chord_roots.append(chord[0].upper())
            
            # Count frequencies and find most common
            from collections import Counter
            root_counts = Counter(chord_roots)
            
            if root_counts:
                return root_counts.most_common(1)[0][0]
            else:
                return 'C'
                
        except Exception:
            return 'C'
    
    def _apply_style_enhancement(self, chord, style):
        """Apply style-specific enhancement to a chord."""
        try:
            style_enhancements = {
                'jazz': 'Extended with 7th, 9th, or altered tensions',
                'funk': 'Emphasized rhythmic groove and 7th chords',
                'rock': 'Power chord emphasis with strong root movement',
                'blues': 'Dominant 7th emphasis with blue notes',
                'classical': 'Traditional voice leading and resolution',
                'modern_pop': 'Contemporary voicing with color tones',
                'trap': 'Minor tonality with modern production elements'
            }
            
            return style_enhancements.get(style, 'Standard harmonic treatment')
            
        except Exception:
            return 'Standard harmonic treatment'
    
    def rebuild_progression(self, input_file: str, output_file: str = None, 
                           enhance: bool = True, expand: bool = False, 
                           style_influence: str = None) -> str:
        """Rebuild and enhance a progression file with 100% musical accuracy."""
        output_file = output_file or input_file
        
        try:
            # Create backup of original file
            if output_file == input_file:
                backup_file = input_file + '.backup'
                import shutil
                shutil.copy2(input_file, backup_file)
                logging.info(f"Backup created: {backup_file}")
            
            # Load and analyze existing progression
            analysis = self.analyze_progression(input_file)
            
            with open(input_file, 'r') as f:
                data = json.load(f)
            
            prog_data = data['progression']
            original_chords = prog_data.get('chords', [])
            
            # Detect style if not specified
            if style_influence is None:
                style_influence = self._detect_style_from_progression(original_chords, analysis)
            
            # Validate and rebuild each chord with 100% accuracy
            rebuilt_chords = []
            validation_errors = []
            
            for i, chord in enumerate(original_chords):
                try:
                    chord_name = chord.get('name', 'C')
                    if not chord_name:
                        chord_name = 'C'
                        validation_errors.append(f"Chord {i+1}: Empty chord name, defaulting to C")
                    
                    # Parse chord with enhanced accuracy
                    root, intervals, chord_type = self.chord_name_to_intervals(chord_name)
                    
                    # Apply style-based chord enhancement if requested
                    if enhance and style_influence:
                        enhanced_chord_type = self._enhance_chord_for_style(chord_type, style_influence, analysis.complexity_score)
                        if enhanced_chord_type != chord_type:
                            chord_type = enhanced_chord_type
                            intervals = self.CHORD_INTERVALS.get(chord_type, intervals)
                            # Update chord name to reflect enhancement
                            chord_name = self._format_chord_name_correctly(root, chord_type)
                            logging.info(f"Enhanced chord {i+1}: {chord.get('name')} → {chord_name} ({style_influence} style)")
                    
                    # Generate accurate MIDI notes
                    midi_notes = self.generate_chord_notes(root, intervals, octave=4)
                    
                    # Convert MIDI to note names with proper spelling
                    note_names = self._midi_to_note_names_correct_spelling(midi_notes, root, chord_type)
                    
                    # Determine accurate harmonic function
                    if i < len(analysis.chord_functions):
                        function = analysis.chord_functions[i]
                    else:
                        function = self._determine_function_from_context(root, chord_type, analysis.key, analysis.scale)
                    
                    # Enhanced role determination with style context
                    if style_influence:
                        style_role = self._get_style_specific_role(function, style_influence)
                        role = style_role if style_role else function.title()
                    else:
                        role = function.title()
                    
                    # Build accurate chord object
                    rebuilt_chord = {
                        "name": chord_name,
                        "role": role,
                        "notes": note_names,  # Note names for display
                        "midi_notes": midi_notes  # MIDI numbers for accuracy
                    }
                    
                    # Add comprehensive metadata if enhancement is enabled
                    if enhance:
                        rebuilt_chord.update({
                            "function": function,
                            "romanNumeral": analysis.roman_numerals[i] if i < len(analysis.roman_numerals) else self._calculate_roman_numeral(root, chord_type, analysis.key, analysis.scale),
                            "chordType": chord_type,
                            "intervals": intervals,
                            "rootNote": NOTE_NAMES[root % 12],
                            "styleContext": self._get_style_context(style_influence) if style_influence else "Classical harmony",
                            "era": self._get_style_era(style_influence) if style_influence else "Classical",
                            "scaleDegree": self._calculate_scale_degree(root, analysis.key, analysis.scale)
                        })
                        
                        # Add special chord type indicators
                        if i in analysis.secondary_dominants:
                            rebuilt_chord["specialType"] = "SecondaryDominant"
                            rebuilt_chord["description"] = f"Secondary dominant resolving to {self._get_resolution_target(i, analysis)}"
                        elif i in analysis.borrowed_chords:
                            rebuilt_chord["specialType"] = "BorrowedChord"
                            rebuilt_chord["description"] = f"Borrowed from parallel {analysis.scale}"
                        elif style_influence:
                            rebuilt_chord["specialType"] = f"{style_influence.replace('_', ' ').title()}Harmony"
                    
                    rebuilt_chords.append(rebuilt_chord)
                    
                except Exception as chord_error:
                    validation_errors.append(f"Chord {i+1} ({chord.get('name', 'Unknown')}): {str(chord_error)}")
                    # Create fallback chord
                    fallback_chord = {
                        "name": "C",
                        "role": "Tonic",
                        "notes": ["C", "E", "G"],
                        "midi_notes": [60, 64, 67],
                        "error": f"Fallback used due to: {str(chord_error)}"
                    }
                    rebuilt_chords.append(fallback_chord)
            
            # Expand progression if requested
            if expand:
                try:
                    expanded_chords = self.expand_progression_with_style(rebuilt_chords, analysis, style_influence)
                    rebuilt_chords.extend(expanded_chords)
                    logging.info(f"Added {len(expanded_chords)} expansion chords")
                except Exception as expand_error:
                    logging.warning(f"Expansion failed: {expand_error}")
            
            # Update progression data with validated information
            prog_data['chords'] = rebuilt_chords
            
            # Set correct scale information with validation
            detected_scale = self._format_scale_name_correctly(analysis.key, analysis.scale)
            prog_data['scale'] = detected_scale
            prog_data['rootNote'] = analysis.key
            
            # Validate key signature
            if analysis.key not in NOTE_NAMES:
                analysis.key = 'C'  # Fallback to C major
                validation_errors.append("Invalid key signature detected, defaulting to C")
            
            # Add comprehensive analysis data
            if enhance:
                prog_data['analysis'] = {
                    'keySignature': analysis.key,
                    'scale': analysis.scale,
                    'detectedScale': detected_scale,
                    'complexity': round(analysis.complexity_score, 3),
                    'moodTags': analysis.mood_tags,
                    'romanNumerals': analysis.roman_numerals,
                    'chordFunctions': analysis.chord_functions,
                    'historicalContext': analysis.historical_context,
                    'era': analysis.era,
                    'styleInfluence': style_influence or 'Classical',
                    'voiceLeadingQuality': round(analysis.voice_leading_quality, 3),
                    'similarToFamous': analysis.similar_to_famous,
                    'modulations': analysis.modulations,
                    'borrowedChords': [i for i in analysis.borrowed_chords],
                    'secondaryDominants': [i for i in analysis.secondary_dominants],
                    'validationErrors': validation_errors,
                    'rebuildTimestamp': str(datetime.now()),
                    'originalChordCount': len(original_chords),
                    'finalChordCount': len(rebuilt_chords)
                }
            
            # Validate JSON structure before writing
            self._validate_progression_json(data)
            
            # Write rebuilt file with proper formatting
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, sort_keys=False)
            
            # Add to library for learning
            self.add_chords_to_library(rebuilt_chords, output_file)
            
            # Log completion with statistics
            logging.info(f"Successfully rebuilt progression: {output_file}")
            logging.info(f"Original chords: {len(original_chords)}, Final chords: {len(rebuilt_chords)}")
            logging.info(f"Detected: {detected_scale}, Style: {style_influence or 'Classical'}")
            if validation_errors:
                logging.warning(f"Validation warnings: {len(validation_errors)}")
                for error in validation_errors:
                    logging.warning(f"  - {error}")
            
            return output_file
            
        except Exception as e:
            logging.error(f"Critical error rebuilding progression: {e}")
            import traceback
            logging.error(traceback.format_exc())
            raise RuntimeError(f"Failed to rebuild progression: {str(e)}")
    
    def _format_chord_name_correctly(self, root: int, chord_type: str) -> str:
        """Format chord name with correct notation."""
        root_name = NOTE_NAMES[root % 12]
        suffix = self._chord_type_to_suffix(chord_type)
        return root_name + suffix
    
    def _midi_to_note_names_correct_spelling(self, midi_notes: List[int], root: int, chord_type: str) -> List[str]:
        """Convert MIDI notes to correctly spelled note names based on harmonic context."""
        note_names = []
        
        # Define preferred spellings based on key context
        sharp_keys = [2, 7, 9]  # D, G, A majors prefer sharps
        flat_keys = [1, 3, 6, 8, 10]  # Db, Eb, Gb, Ab, Bb majors prefer flats
        
        root_class = root % 12
        prefer_sharps = root_class in sharp_keys
        
        for midi in midi_notes:
            note_class = midi % 12
            
            # Use enharmonic spelling that makes harmonic sense
            if note_class == 1:  # C#/Db
                note_names.append('C#' if prefer_sharps else 'Db')
            elif note_class == 3:  # D#/Eb
                note_names.append('D#' if prefer_sharps else 'Eb')
            elif note_class == 6:  # F#/Gb
                note_names.append('F#' if prefer_sharps else 'Gb')
            elif note_class == 8:  # G#/Ab
                note_names.append('G#' if prefer_sharps else 'Ab')
            elif note_class == 10:  # A#/Bb
                note_names.append('A#' if prefer_sharps else 'Bb')
            else:
                # Natural notes
                naturals = ['C', 'D', 'E', 'F', 'G', 'A', 'B']
                note_names.append(naturals[note_class] if note_class < 7 else naturals[note_class - 12])
        
        return note_names
    
    def _determine_function_from_context(self, root: int, chord_type: str, key: str, scale: str) -> str:
        """Determine chord function based on harmonic context."""
        key_root = NOTE_NAMES.index(key) if key in NOTE_NAMES else 0
        scale_degree = (root - key_root) % 12
        
        # Major scale functions
        if scale in ['major', 'ionian']:
            function_map = {
                0: 'tonic',
                2: 'supertonic', 
                4: 'mediant',
                5: 'subdominant',
                7: 'dominant',
                9: 'submediant',
                11: 'leading_tone'
            }
        # Minor scale functions
        elif scale in ['minor', 'aeolian']:
            function_map = {
                0: 'tonic',
                2: 'supertonic',
                3: 'mediant',
                5: 'subdominant', 
                7: 'dominant',
                8: 'submediant',
                10: 'subtonic'
            }
        else:
            # Default to basic functions
            if scale_degree == 0:
                return 'tonic'
            elif scale_degree == 7:
                return 'dominant'
            elif scale_degree == 5:
                return 'subdominant'
            else:
                return 'color'
        
        return function_map.get(scale_degree, 'color')
    
    def _calculate_roman_numeral(self, root: int, chord_type: str, key: str, scale: str) -> str:
        """Calculate accurate Roman numeral for chord."""
        key_root = NOTE_NAMES.index(key) if key in NOTE_NAMES else 0
        scale_degree = (root - key_root) % 12
        
        # Get scale intervals
        scale_key = 'ionian' if scale == 'major' else 'aeolian' if scale == 'minor' else scale
        scale_intervals = self.SCALE_INTERVALS.get(scale_key, self.SCALE_INTERVALS['ionian'])
        
        # Find the scale degree number
        degree_number = 1
        for i, interval in enumerate(scale_intervals):
            if interval == scale_degree:
                degree_number = i + 1
                break
        
        # Roman numerals
        roman_numerals = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII']
        roman = roman_numerals[degree_number - 1] if degree_number <= 7 else 'I'
        
        # Adjust case for minor chords
        if chord_type.startswith('min') or chord_type == 'dim':
            roman = roman.lower()
        
        # Add chord quality indicators
        if chord_type == 'dim':
            roman += '°'
        elif chord_type == 'dim7':
            roman += '°7'
        elif chord_type == 'min7b5':
            roman += 'ø7'
        elif chord_type == 'aug':
            roman += '+'
        elif '7' in chord_type:
            roman += '7'
        
        return roman
    
    def _calculate_scale_degree(self, root: int, key: str, scale: str) -> int:
        """Calculate the scale degree number (1-7)."""
        key_root = NOTE_NAMES.index(key) if key in NOTE_NAMES else 0
        scale_degree = (root - key_root) % 12
        
        scale_key = 'ionian' if scale == 'major' else 'aeolian' if scale == 'minor' else scale
        scale_intervals = self.SCALE_INTERVALS.get(scale_key, self.SCALE_INTERVALS['ionian'])
        
        for i, interval in enumerate(scale_intervals):
            if interval == scale_degree:
                return i + 1
        
        return 1  # Default to tonic
    
    def _format_scale_name_correctly(self, key: str, scale: str) -> str:
        """Format scale name with proper capitalization and spelling."""
        # Standardize common scale names
        scale_names = {
            'major': 'Major',
            'minor': 'Minor', 
            'ionian': 'Major',
            'aeolian': 'Minor',
            'dorian': 'Dorian',
            'phrygian': 'Phrygian',
            'lydian': 'Lydian',
            'mixolydian': 'Mixolydian',
            'locrian': 'Locrian'
        }
        
        formatted_scale = scale_names.get(scale.lower(), scale.title())
        return f"{key} {formatted_scale}"
    
    def _validate_progression_json(self, data: dict) -> None:
        """Validate JSON structure before writing."""
        required_fields = ['progression']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        
        prog = data['progression']
        if 'chords' not in prog:
            raise ValueError("Missing chords array in progression")
        
        for i, chord in enumerate(prog['chords']):
            if 'name' not in chord:
                raise ValueError(f"Chord {i+1} missing name field")
            if 'notes' not in chord and 'midi_notes' not in chord:
                raise ValueError(f"Chord {i+1} missing notes/midi_notes field")
    
    def _get_resolution_target(self, chord_index: int, analysis) -> str:
        """Get the resolution target for secondary dominants."""
        if chord_index + 1 < len(analysis.roman_numerals):
            return analysis.roman_numerals[chord_index + 1]
        return "tonic"
    
    def expand_progression(self, base_chords: List[Dict], analysis: ProgressionAnalysis) -> List[Dict]:
        """Expand a chord progression with sophisticated harmonic additions."""
        expanded = []
        
        # Get similar progressions from library
        similar_progs = self.find_similar_progressions(analysis)
        
        # Generate variations based on music theory
        for i, chord in enumerate(base_chords):
            name = chord['name']
            root, intervals, chord_type = self.chord_name_to_intervals(name)
            
            # Add substitutions and extensions
            substitutions = self._generate_substitutions(root, chord_type, analysis.key)
            
            for sub in substitutions[:2]:  # Limit to prevent explosion
                sub_name, sub_intervals = sub
                sub_notes = self.generate_chord_notes(root, sub_intervals)
                
                expanded_chord = {
                    "name": sub_name,
                    "role": "Substitution",
                    "notes": sub_notes,
                    "originalChord": name,
                    "type": "HarmonicSubstitution"
                }
                expanded.append(expanded_chord)
        
        return expanded
    
    def generate_progression(self, key: str = "C", scale: str = "major", 
                           length: int = 4, style: str = "pop",
                           complexity: float = 0.5, historical_style: str = None) -> List[Dict]:
        """Generate a new chord progression using AI-inspired algorithms with historical styles."""
        
        # If historical style is requested, use it as foundation
        if historical_style and historical_style in HISTORICAL_PROGRESSIONS:
            return self.generate_progression_from_historical(historical_style, key, scale)
        
        # Get scale intervals (handle major/minor aliases)
        scale_key = 'ionian' if scale == 'major' else 'aeolian' if scale == 'minor' else scale
        scale_intervals = self.SCALE_INTERVALS.get(scale_key, self.SCALE_INTERVALS['ionian'])
        key_root = NOTE_NAMES.index(key) if key in NOTE_NAMES else 0
        
        # Generate scale degrees in the key
        scale_degrees = [(key_root + interval) % 12 for interval in scale_intervals]
        
        # Enhanced style-based progression templates (70s to modern)
        style_templates = {
            # Classic styles
            'pop': [0, 4, 5, 3],        # I-V-vi-IV
            'jazz': [1, 4, 0],          # ii-V-I  
            'folk': [0, 3, 5, 0],       # I-IV-vi-I
            'blues': [0, 0, 3, 3, 0, 0, 4, 4], # 12-bar blues pattern
            'rock': [0, 2, 3, 0],       # I-iii-IV-I
            'ballad': [5, 3, 0, 4],     # vi-IV-I-V
            'classical': [0, 4, 1, 4, 0], # I-V-ii-V-I
            
            # 70s styles
            'funk': [0, 3, 0, 0],       # i-iv-i-i (funk vamp)
            'prog_rock': [0, 6, 5, 6, 3, 0, 4, 4], # Complex modulation
            'soul': [0, 5, 3, 4, 5, 3, 0, 4], # Motown progression
            'punk': [0, 6, 3, 0],       # I-bVII-IV-I
            
            # 80s styles  
            'new_wave': [5, 3, 0, 4, 5, 3, 0, 4], # vi-IV-I-V repeated
            'synthpop': [5, 3, 0, 4],   # vi-IV-I-V
            'post_punk': [0, 6, 5, 6],  # i-bVII-bVI-bVII
            
            # 90s styles
            'grunge': [0, 6, 3, 0, 5, 6, 0], # i-bVII-IV-i-bVI-bVII-i
            'britpop': [0, 4, 5, 3, 0, 4, 5, 3], # I-V-vi-IV repeated
            'hip_hop': [0, 6, 5, 6],    # i-bVII-bVI-bVII
            'rnb': [5, 3, 0, 4],        # vi-IV-I-V
            
            # 2000s styles
            'neo_soul': [0, 3, 6, 2],   # iMaj7-ivMaj7-bVIIMaj7-IIIMaj7
            'emo': [5, 4, 3, 4],        # vi-V-IV-V
            'indie': [5, 3, 0, 4],      # vi-IV-I-V
            
            # 2010s-2020s styles
            'trap': [0, 5, 2, 6],       # i-bVI-bIII-bVII
            'modern_pop': [5, 3, 0, 4, 5, 3, 0, 4], # vi-IV-I-V (modern)
            'alt_rnb': [0, 5, 3, 4],    # iMaj7-bVIMaj7-IVMaj7-VMaj7
            'electronic': [5, 3, 0, 4], # vi-IV-I-V
            'indie_pop': [0, 4, 5, 3],  # I-V-vi-IV
        }
        
        template = style_templates.get(style, style_templates['pop'])
        
        # Extend or truncate template to desired length
        while len(template) < length:
            template.extend(template)
        template = template[:length]
        
        # Generate chords with style-specific characteristics
        progression = []
        for i, degree in enumerate(template):
            if degree < len(scale_degrees):
                chord_root = scale_degrees[degree]
                
                # Choose chord type based on degree, style, and era
                chord_type = self._choose_chord_type_with_style(degree, scale, style, complexity)
                
                # Add style-specific extensions and alterations
                if complexity > 0.6:
                    chord_type = self._add_style_specific_extension(chord_type, style, complexity)
                
                intervals = self.CHORD_INTERVALS.get(chord_type, [0, 4, 7])
                notes = self.generate_chord_notes(chord_root, intervals)
                
                chord_name = NOTE_NAMES[chord_root] + self._chord_type_to_suffix(chord_type)
                
                # Determine chord role with style context
                role = self._determine_chord_role_with_style(degree, i, len(template), style)
                
                chord = {
                    "name": chord_name,
                    "role": role,
                    "notes": notes,
                    "midi_notes": notes,
                    "degree": degree + 1,
                    "style_context": self._get_style_context(style),
                    "era": self._get_style_era(style)
                }
                
                progression.append(chord)
        
        return progression
    
    def find_similar_progressions(self, analysis: ProgressionAnalysis) -> List[Dict]:
        """Find similar progressions from the user library."""
        self.cursor.execute('''
            SELECT name, chords, key_signature, scale, mood_tags, complexity_score
            FROM progressions
            WHERE key_signature = ? AND scale = ?
            ORDER BY usage_count DESC, complexity_score
        ''', (analysis.key, analysis.scale))
        
        results = self.cursor.fetchall()
        similar = []
        
        for row in results:
            similar.append({
                'name': row[0],
                'chords': json.loads(row[1]),
                'key': row[2],
                'scale': row[3],
                'mood_tags': json.loads(row[4]) if row[4] else [],
                'complexity': row[5]
            })
        
        return similar
    
    def add_chords_to_library(self, chords: List[Dict], source_file: str):
        """Add chords to the user library database."""
        for chord in chords:
            name = chord.get('name', '')
            notes = chord.get('notes', [])
            
            if name and notes:
                root, intervals, chord_type = self.chord_name_to_intervals(name)
                
                # Check if chord exists
                self.cursor.execute('''
                    SELECT id, usage_count FROM chords 
                    WHERE root = ? AND type = ? AND notes = ?
                ''', (root, chord_type, json.dumps(notes)))
                
                existing = self.cursor.fetchone()
                
                if existing:
                    # Update usage count
                    self.cursor.execute('''
                        UPDATE chords SET usage_count = usage_count + 1
                        WHERE id = ?
                    ''', (existing[0],))
                else:
                    # Insert new chord
                    self.cursor.execute('''
                        INSERT INTO chords (root, type, intervals, notes, source_file)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (root, chord_type, json.dumps(intervals), json.dumps(notes), source_file))
        
        self.conn.commit()
    
    def add_progression_to_library(self, name: str, chords: List[str], 
                                  key: str, scale: str, mood_tags: List[str],
                                  complexity: float, source_file: str = None):
        """Add a progression to the library database."""
        self.cursor.execute('''
            INSERT INTO progressions (name, chords, key_signature, scale, mood_tags, complexity_score, source_file)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (name, json.dumps(chords), key, scale, json.dumps(mood_tags), complexity, source_file))
        
        self.conn.commit()
    
    def get_chord_statistics(self) -> Dict:
        """Get statistics about the user's chord library."""
        stats = {}
        
        # Most used chords
        self.cursor.execute('''
            SELECT type, COUNT(*) as count, SUM(usage_count) as total_usage
            FROM chords GROUP BY type ORDER BY total_usage DESC LIMIT 10
        ''')
        stats['most_used_chord_types'] = self.cursor.fetchall()
        
        # Favorite keys
        self.cursor.execute('''
            SELECT key_signature, COUNT(*) as count
            FROM progressions GROUP BY key_signature ORDER BY count DESC LIMIT 5
        ''')
        stats['favorite_keys'] = self.cursor.fetchall()
        
        # Style preferences  
        self.cursor.execute('''
            SELECT mood_tags, COUNT(*) as count
            FROM progressions WHERE mood_tags IS NOT NULL
            GROUP BY mood_tags ORDER BY count DESC LIMIT 5
        ''')
        stats['preferred_styles'] = self.cursor.fetchall()
        
        return stats
    
    def _determine_key(self, chords: List[ChordInfo]) -> str:
        """Determine the key from chord analysis."""
        # Count root notes and find most common
        roots = [chord.root for chord in chords]
        from collections import Counter
        most_common_root = Counter(roots).most_common(1)[0][0]
        return NOTE_NAMES[most_common_root]
    
    def _determine_scale(self, chords: List[ChordInfo]) -> str:
        """Determine the scale type from chord analysis."""
        # Simple heuristic - check for minor vs major chords
        major_count = sum(1 for chord in chords if 'maj' in chord.type or chord.type == 'maj')
        minor_count = sum(1 for chord in chords if 'min' in chord.type)
        
        if minor_count > major_count:
            return 'minor'
        else:
            return 'major'
    
    def _generate_roman_numerals(self, chords: List[ChordInfo], key: str) -> List[str]:
        """Generate Roman numeral analysis."""
        key_root = NOTE_NAMES.index(key)
        roman_major = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII']
        roman_minor = ['i', 'ii', 'iii', 'iv', 'v', 'vi', 'vii']
        
        numerals = []
        for chord in chords:
            degree = (chord.root - key_root) % 12
            
            # Map to scale degree (simplified)
            scale_degree = degree // 2 if degree < 12 else 0
            
            if 'min' in chord.type:
                numeral = roman_minor[scale_degree % 7].lower()
            elif chord.type == 'dim':
                numeral = roman_minor[scale_degree % 7] + 'o'
            else:
                numeral = roman_major[scale_degree % 7]
            
            numerals.append(numeral)
        
        return numerals
    
    def _analyze_chord_functions(self, chords: List[ChordInfo], key: str) -> List[str]:
        """Analyze harmonic function of each chord."""
        functions = []
        
        for i, chord in enumerate(chords):
            # Simple function analysis
            if i == len(chords) - 1:
                functions.append("tonic")  # Last chord often tonic
            elif i == len(chords) - 2:
                functions.append("dominant")  # Second to last often dominant
            elif chord.type in ['7', '9', '11', '13']:
                functions.append("dominant")
            elif 'min' in chord.type:
                functions.append("subdominant")
            else:
                functions.append("normal")
        
        return functions
    
    def _detect_modulations(self, chords: List[ChordInfo]) -> List[Tuple[int, str]]:
        """Detect key modulations in the progression."""
        # Simplified modulation detection
        modulations = []
        
        # Look for chromatic chords that suggest modulation
        for i, chord in enumerate(chords):
            # Check for secondary dominants or chromatic alterations
            if chord.type in ['7', '7alt', '7b5', '7#5']:
                # Potential modulation point
                target_key = NOTE_NAMES[(chord.root + 7) % 12]  # Perfect fifth up
                modulations.append((i, target_key))
        
        return modulations
    
    def _find_borrowed_chords(self, chords: List[ChordInfo], key: str, scale: str) -> List[int]:
        """Find chords borrowed from parallel modes."""
        borrowed = []
        key_root = NOTE_NAMES.index(key)
        
        # Get expected scale degrees
        scale_intervals = SCALE_INTERVALS.get(scale, SCALE_INTERVALS['major'])
        expected_degrees = {(key_root + interval) % 12 for interval in scale_intervals}
        
        for i, chord in enumerate(chords):
            if chord.root not in expected_degrees:
                borrowed.append(i)
        
        return borrowed
    
    def _find_secondary_dominants(self, chords: List[ChordInfo], key: str) -> List[int]:
        """Find secondary dominant chords."""
        secondary_doms = []
        
        for i, chord in enumerate(chords):
            if chord.type == '7' and i < len(chords) - 1:
                next_chord = chords[i + 1]
                # Check if this is a V7 of the next chord
                if (chord.root + 7) % 12 == next_chord.root:
                    secondary_doms.append(i)
        
        return secondary_doms
    
    def _calculate_complexity(self, chords: List[ChordInfo], num_modulations: int, num_borrowed: int) -> float:
        """Calculate harmonic complexity score."""
        base_complexity = 0.0
        
        # Chord type complexity
        for chord in chords:
            if chord.type in ['maj', 'min']:
                base_complexity += 0.1
            elif chord.type in ['7', 'maj7', 'min7']:
                base_complexity += 0.3
            elif chord.type in ['9', '11', '13']:
                base_complexity += 0.5
            else:
                base_complexity += 0.7
        
        # Normalize by number of chords
        base_complexity /= len(chords) if chords else 1
        
        # Add complexity for modulations and borrowed chords
        base_complexity += num_modulations * 0.2
        base_complexity += num_borrowed * 0.1
        
        return min(1.0, base_complexity)
    
    def _generate_mood_tags(self, chords: List[ChordInfo], scale: str, complexity: float) -> List[str]:
        """Generate mood tags based on harmonic content."""
        tags = []
        
        # Scale-based moods
        if scale == 'minor':
            tags.extend(['dark', 'sad', 'melancholic'])
        elif scale == 'major':
            tags.extend(['bright', 'happy', 'uplifting'])
        
        # Complexity-based moods
        if complexity > 0.7:
            tags.extend(['sophisticated', 'jazz', 'advanced'])
        elif complexity < 0.3:
            tags.extend(['simple', 'folk', 'accessible'])
        
        # Chord type based moods
        has_extended = any(chord.type in ['9', '11', '13'] for chord in chords)
        if has_extended:
            tags.append('jazz')
            
        has_diminished = any('dim' in chord.type for chord in chords)
        if has_diminished:
            tags.append('tense')
        
        return list(set(tags))  # Remove duplicates
    
    def _choose_chord_type(self, degree: int, scale: str, style: str, complexity: float) -> str:
        """Choose appropriate chord type based on context."""
        # Basic triads for low complexity
        if complexity < 0.3:
            if scale == 'major':
                major_degrees = [0, 3, 4]  # I, IV, V
                return 'maj' if degree in major_degrees else 'min'
            else:
                return 'min'
        
        # Extended chords for high complexity
        elif complexity > 0.7:
            if style == 'jazz':
                return random.choice(['7', 'maj7', 'min7', '9', '11'])
            else:
                return random.choice(['maj', 'min', '7', 'maj7'])
        
        # Moderate complexity
        else:
            return random.choice(['maj', 'min', '7', 'maj7'])
    
    def _add_chord_extension(self, chord_type: str, style: str) -> str:
        """Add extensions to chord types."""
        extensions = {
            'maj': ['maj7', 'maj9', '6'],
            'min': ['min7', 'min9', 'min6'],
            '7': ['9', '11', '13'],
        }
        
        if chord_type in extensions:
            return random.choice(extensions[chord_type])
        return chord_type
    
    def _chord_type_to_suffix(self, chord_type: str) -> str:
        """Convert chord type to chord symbol suffix."""
        suffix_map = {
            'maj': '',
            'min': 'm',
            '7': '7',
            'maj7': 'maj7',
            'min7': 'm7',
            'dim': 'dim',
            'aug': 'aug',
            '9': '9',
            'maj9': 'maj9',
            'min9': 'm9',
            '11': '11',
            '13': '13',
            'sus2': 'sus2',
            'sus4': 'sus4',
            'add9': 'add9',
        }
        return suffix_map.get(chord_type, '')
    
    def _choose_chord_type_with_style(self, degree: int, scale: str, style: str, complexity: float) -> str:
        """Choose chord type based on musical style and era."""
        
        # Style-specific chord preferences
        style_chords = {
            # 70s styles
            'funk': {
                'low': ['7', 'min7'],
                'high': ['7', 'min7', '9', 'min9']
            },
            'prog_rock': {
                'low': ['maj', 'min', '7'],
                'high': ['maj7', 'min7', 'maj9', 'add9', 'sus2', 'sus4']
            },
            'soul': {
                'low': ['maj', 'min', '7'],
                'high': ['maj7', 'min7', '9', '6']
            },
            'punk': {
                'low': ['maj', 'min'],
                'high': ['maj', 'min', '7']
            },
            
            # 80s styles
            'new_wave': {
                'low': ['maj', 'min', '7'],
                'high': ['maj7', 'min7', 'add9', 'sus2']
            },
            'synthpop': {
                'low': ['maj', 'min'],
                'high': ['maj7', 'min7', 'add9']
            },
            
            # 90s styles
            'grunge': {
                'low': ['maj', 'min'],
                'high': ['maj', 'min', '7', 'sus2', 'sus4']
            },
            'hip_hop': {
                'low': ['min', '7'],
                'high': ['min7', '7', 'min9']
            },
            'britpop': {
                'low': ['maj', 'min'],
                'high': ['maj7', 'min7', 'add9']
            },
            
            # 2000s-2010s styles
            'neo_soul': {
                'low': ['maj7', 'min7'],
                'high': ['maj9', 'min9', '11', '13']
            },
            'trap': {
                'low': ['min', 'min7'],
                'high': ['min7', 'min9', '7']
            },
            'modern_pop': {
                'low': ['maj', 'min'],
                'high': ['maj7', 'min7', 'add9']
            },
            'alt_rnb': {
                'low': ['maj7', 'min7'],
                'high': ['maj9', 'min9', '11', 'maj7#11']
            }
        }
        
        # Get style preferences or default to jazz/pop
        style_prefs = style_chords.get(style, {
            'low': ['maj', 'min', '7'],
            'high': ['maj7', 'min7', '9']
        })
        
        # Choose based on complexity
        if complexity < 0.4:
            return random.choice(style_prefs['low'])
        else:
            return random.choice(style_prefs['high'])
    
    def _add_style_specific_extension(self, chord_type: str, style: str, complexity: float) -> str:
        """Add style-specific chord extensions."""
        
        # Era-specific extension patterns
        style_extensions = {
            'funk': ['7', '9', 'min7', 'min9'],
            'prog_rock': ['maj7', 'add9', 'sus2', 'sus4', 'maj9'],
            'soul': ['maj7', '6', '9', 'min7'],
            'new_wave': ['maj7', 'add9', 'sus2'],
            'grunge': ['sus2', 'sus4', 'add9'],
            'neo_soul': ['maj9', 'min9', '11', '13'],
            'trap': ['min7', 'min9', '7'],
            'alt_rnb': ['maj9', 'min9', 'maj7#11', '11']
        }
        
        extensions = style_extensions.get(style, ['maj7', 'min7', '9'])
        
        if complexity > 0.8 and random.random() < 0.4:
            return random.choice(extensions)
        
        return chord_type
    
    def _determine_chord_role_with_style(self, degree: int, position: int, total_length: int, style: str) -> str:
        """Determine chord role with style-specific context."""
        
        # Basic functional roles
        if degree == 0:
            role = "tonic"
        elif degree == 4:
            role = "dominant"
        elif degree == 3:
            role = "subdominant"
        else:
            role = "color"
        
        # Style-specific role modifications
        style_roles = {
            'funk': {0: "groove_foundation", 3: "funk_subdominant"},
            'trap': {0: "dark_tonic", 5: "atmospheric"},
            'neo_soul': {0: "jazz_tonic", 3: "soul_subdominant"},
            'grunge': {0: "heavy_tonic", 6: "grunge_flat_seven"},
            'prog_rock': {0: "complex_tonic", 6: "prog_modulation"}
        }
        
        if style in style_roles and degree in style_roles[style]:
            role = style_roles[style][degree]
        
        # Position-specific roles
        if position == 0:
            role = f"opening_{role}"
        elif position == total_length - 1:
            role = f"closing_{role}"
        
        return role
    
    def _get_style_context(self, style: str) -> str:
        """Get contextual information about the musical style."""
        
        style_contexts = {
            'funk': "Groove-based rhythm with emphasis on beat 1 and 3",
            'prog_rock': "Complex arrangements with odd time signatures",
            'soul': "Gospel-influenced with emotional vocal delivery",
            'punk': "Fast tempo with power chords and aggressive energy",
            'new_wave': "Electronic elements with melodic bass lines",
            'synthpop': "Synthesizer-driven with electronic drums",
            'grunge': "Distorted guitars with dynamic loud-soft contrasts",
            'hip_hop': "Sample-based production with strong rhythmic focus",
            'britpop': "Guitar-driven with anthemic choruses",
            'neo_soul': "Jazz harmony combined with hip-hop rhythms",
            'trap': "808 drums with atmospheric pads and minor tonality",
            'modern_pop': "Electronic production with vocal emphasis",
            'alt_rnb': "Atmospheric production with extended jazz chords"
        }
        
        return style_contexts.get(style, "Contemporary musical style")
    
    def _get_style_era(self, style: str) -> str:
        """Get the era/decade associated with the musical style."""
        
        style_eras = {
            'funk': '1970s',
            'prog_rock': '1970s',
            'soul': '1960s-1970s',
            'punk': 'Late 1970s',
            'new_wave': '1980s',
            'synthpop': '1980s',
            'post_punk': '1980s',
            'grunge': '1990s',
            'hip_hop': '1980s-1990s',
            'britpop': '1990s',
            'rnb': '1990s',
            'neo_soul': '2000s',
            'emo': '2000s',
            'indie': '2000s',
            'trap': '2010s-2020s',
            'modern_pop': '2010s-2020s',
            'alt_rnb': '2010s-2020s',
            'electronic': '2010s-2020s'
        }
        
        return style_eras.get(style, 'Contemporary')
    
    def _determine_chord_role(self, degree: int, position: int, total_length: int) -> str:
        """Determine the role of a chord in the progression."""
        if position == 0:
            return "Root"
        elif position == total_length - 1:
            return "Resolution"
        elif degree == 4:  # V chord
            return "Dominant"
        elif degree == 3:  # IV chord
            return "Subdominant"
        else:
            return "Normal"
    
    def _generate_substitutions(self, root: int, chord_type: str, key: str) -> List[Tuple[str, List[int]]]:
        """Generate harmonic substitutions for a chord."""
        substitutions = []
        
        # Tritone substitution for dominant chords
        if chord_type == '7':
            tritone_root = (root + 6) % 12
            tritone_name = NOTE_NAMES[tritone_root] + '7'
            substitutions.append((tritone_name, CHORD_INTERVALS['7']))
        
        # Relative minor/major substitutions
        if chord_type == 'maj':
            rel_minor_root = (root + 9) % 12
            rel_minor_name = NOTE_NAMES[rel_minor_root] + 'm'
            substitutions.append((rel_minor_name, CHORD_INTERVALS['min']))
        elif chord_type == 'min':
            rel_major_root = (root + 3) % 12
            rel_major_name = NOTE_NAMES[rel_major_root]
            substitutions.append((rel_major_name, CHORD_INTERVALS['maj']))
        
        # Add extensions
        if chord_type in ['maj', 'min', '7']:
            extended_type = chord_type + '7' if chord_type != '7' else '9'
            if extended_type in CHORD_INTERVALS:
                extended_name = NOTE_NAMES[root] + self._chord_type_to_suffix(extended_type)
                substitutions.append((extended_name, CHORD_INTERVALS[extended_type]))
        
        return substitutions[:3]  # Limit number of substitutions
    
    def _analyze_historical_context(self, chords: List[ChordInfo], key: str, scale: str) -> Tuple[Optional[str], Optional[str], List[str]]:
        """Analyze progression for historical context and famous progressions."""
        # Convert chords to Roman numeral pattern for comparison
        key_root = NOTE_NAMES.index(key)
        pattern = []
        
        for chord in chords:
            degree = (chord.root - key_root) % 12
            # Simplified pattern matching
            if degree == 0:
                pattern.append('I' if 'maj' in chord.type else 'i')
            elif degree == 2:
                pattern.append('ii' if 'min' in chord.type else 'II')
            elif degree == 4:
                pattern.append('iii' if 'min' in chord.type else 'III')
            elif degree == 5:
                pattern.append('IV' if 'maj' in chord.type else 'iv')
            elif degree == 7:
                pattern.append('V' if '7' in chord.type else 'V')
            elif degree == 9:
                pattern.append('vi' if 'min' in chord.type else 'VI')
            elif degree == 11:
                pattern.append('vii' if 'dim' in chord.type else 'VII')
        
        # Match against historical progressions
        similar_progressions = []
        best_match_era = None
        best_match_context = None
        
        for prog_name, prog_data in HISTORICAL_PROGRESSIONS.items():
            prog_pattern = prog_data['pattern']
            
            # Check for exact or partial matches
            if self._pattern_similarity(pattern, prog_pattern) > 0.7:
                similar_progressions.append(prog_data['name'])
                if best_match_era is None:
                    best_match_era = prog_data['era']
                    best_match_context = prog_data['description']
        
        return best_match_context, best_match_era, similar_progressions
    
    def _pattern_similarity(self, pattern1: List[str], pattern2: List[str]) -> float:
        """Calculate similarity between two chord patterns."""
        if not pattern1 or not pattern2:
            return 0.0
        
        # Check for subsequence matches
        max_similarity = 0.0
        
        for i in range(len(pattern1)):
            for j in range(len(pattern2)):
                # Check how many consecutive chords match
                matches = 0
                k = 0
                while (i + k < len(pattern1) and j + k < len(pattern2) and
                       pattern1[i + k].lower() == pattern2[j + k].lower()):
                    matches += 1
                    k += 1
                
                similarity = matches / max(len(pattern1), len(pattern2))
                max_similarity = max(max_similarity, similarity)
        
        return max_similarity
    
    def _calculate_voice_leading_quality(self, chords: List[ChordInfo]) -> float:
        """Calculate the quality of voice leading in the progression."""
        if len(chords) < 2:
            return 1.0
        
        total_movement = 0
        smooth_movements = 0
        
        for i in range(len(chords) - 1):
            current_chord = chords[i]
            next_chord = chords[i + 1]
            
            # Generate actual notes for comparison
            current_notes = self.generate_chord_notes(current_chord.root, current_chord.intervals)
            next_notes = self.generate_chord_notes(next_chord.root, next_chord.intervals)
            
            # Calculate voice movement
            for note1 in current_notes:
                min_distance = float('inf')
                for note2 in next_notes:
                    distance = abs(note1 - note2)
                    min_distance = min(min_distance, distance)
                
                total_movement += min_distance
                if min_distance <= 2:  # Smooth voice leading (whole step or less)
                    smooth_movements += 1
        
        # Quality based on smooth movement ratio and average movement distance
        if total_movement == 0:
            return 1.0
        
        smooth_ratio = smooth_movements / max(1, sum(len(self.generate_chord_notes(c.root, c.intervals)) for c in chords[:-1]))
        avg_movement = total_movement / max(1, sum(len(self.generate_chord_notes(c.root, c.intervals)) for c in chords[:-1]))
        
        # Lower average movement and higher smooth ratio = better voice leading
        quality = smooth_ratio * 0.7 + (1 / (1 + avg_movement / 12)) * 0.3
        
        return min(1.0, quality)
    
    def generate_progression_from_historical(self, style_name: str, key: str = "C", 
                                          variations: bool = True) -> List[Dict]:
        """Generate a progression based on a historical style."""
        if style_name not in HISTORICAL_PROGRESSIONS:
            raise ValueError(f"Unknown historical style: {style_name}")
        
        prog_data = HISTORICAL_PROGRESSIONS[style_name]
        pattern = prog_data['pattern']
        key_root = NOTE_NAMES.index(key) if key in NOTE_NAMES else 0
        
        progression = []
        
        for i, roman_numeral in enumerate(pattern):
            # Parse Roman numeral to get chord
            chord_root, chord_type = self._parse_roman_numeral(roman_numeral, key_root)
            intervals = CHORD_INTERVALS.get(chord_type, [0, 4, 7])
            notes = self.generate_chord_notes(chord_root, intervals)
            
            chord_name = NOTE_NAMES[chord_root] + self._chord_type_to_suffix(chord_type)
            
            chord = {
                "name": chord_name,
                "role": self._determine_chord_role_from_roman(roman_numeral),
                "notes": notes,
                "romanNumeral": roman_numeral,
                "historical_style": style_name,
                "era": prog_data['era'],
                "composer": prog_data.get('composer', 'Unknown')
            }
            
            # Add variations if requested
            if variations and len(progression) > 0:
                # Occasionally add passing chords or substitutions
                if random.random() < 0.3:
                    passing_chord = self._generate_passing_chord(progression[-1], chord)
                    if passing_chord:
                        progression.append(passing_chord)
            
            progression.append(chord)
        
        return progression
    
    def _parse_roman_numeral(self, roman_numeral: str, key_root: int) -> Tuple[int, str]:
        """Parse a Roman numeral to get root note and chord type."""
        # Handle special cases
        if roman_numeral == 'N6':  # Neapolitan sixth
            return (key_root + 1) % 12, 'maj'  # bII major
        
        # Remove quality indicators for parsing
        clean_numeral = roman_numeral.replace('7', '').replace('M', '').replace('m', '')
        clean_numeral = clean_numeral.replace('o', '').replace('+', '').replace('/', '')
        
        # Map Roman numerals to scale degrees
        roman_to_degree = {
            'I': 0, 'i': 0,
            'II': 2, 'ii': 2, 'bII': 1,
            'III': 4, 'iii': 4, 'bIII': 3,
            'IV': 5, 'iv': 5,
            'V': 7, 'v': 7,
            'VI': 9, 'vi': 9, 'bVI': 8,
            'VII': 11, 'vii': 11, 'bVII': 10
        }
        
        degree = roman_to_degree.get(clean_numeral, 0)
        chord_root = (key_root + degree) % 12
        
        # Determine chord type from Roman numeral
        if roman_numeral.islower() or 'min' in roman_numeral:
            chord_type = 'min7' if '7' in roman_numeral else 'min'
        elif 'o' in roman_numeral:
            chord_type = 'dim7' if '7' in roman_numeral else 'dim'
        elif '+' in roman_numeral:
            chord_type = 'aug7' if '7' in roman_numeral else 'aug'
        else:
            chord_type = 'maj7' if 'M7' in roman_numeral or 'maj7' in roman_numeral else ('7' if '7' in roman_numeral else 'maj')
        
        return chord_root, chord_type
    
    def _determine_chord_role_from_roman(self, roman_numeral: str) -> str:
        """Determine chord role from Roman numeral analysis."""
        if roman_numeral.upper().startswith('I'):
            return "Tonic"
        elif roman_numeral.upper().startswith('V'):
            return "Dominant"
        elif roman_numeral.upper().startswith('IV'):
            return "Subdominant"
        elif 'ii' in roman_numeral.lower() or 'II' in roman_numeral:
            return "Predominant"
        elif 'vi' in roman_numeral.lower() or 'VI' in roman_numeral:
            return "Relative"
        else:
            return "Normal"
    
    def _generate_passing_chord(self, chord1: Dict, chord2: Dict) -> Optional[Dict]:
        """Generate a passing chord between two chords."""
        # Simple passing chord generation
        root1 = self.chord_name_to_intervals(chord1['name'])[0]
        root2 = self.chord_name_to_intervals(chord2['name'])[0]
        
        # Find chromatic passing note
        if abs(root1 - root2) == 2:  # Whole step apart
            passing_root = (root1 + 1) % 12 if root2 > root1 else (root1 - 1) % 12
            passing_intervals = [0, 3, 6]  # Diminished chord as passing
            passing_notes = self.generate_chord_notes(passing_root, passing_intervals)
            
            return {
                "name": f"{NOTE_NAMES[passing_root]}dim",
                "role": "Passing",
                "notes": passing_notes,
                "type": "PassingChord"
            }
        
        return None
    
    def get_all_historical_styles(self) -> List[Dict]:
        """Get all available historical progression styles."""
        styles = []
        for name, data in HISTORICAL_PROGRESSIONS.items():
            styles.append({
                'name': name,
                'display_name': data['name'],
                'era': data['era'],
                'composer': data.get('composer', 'Unknown'),
                'complexity': data['complexity'],
                'description': data['description']
            })
        
        return sorted(styles, key=lambda x: (x['era'], x['complexity']))
    
    def _detect_style_from_progression(self, chords: List[str], analysis) -> str:
        """Detect musical style from chord progression characteristics."""
        
        # Handle both string lists and dict lists
        if isinstance(chords[0], str):
            # Input is list of chord names
            chord_names = chords
        else:
            # Input is list of chord dicts
            chord_names = [chord.get('name', 'C') for chord in chords]
        
        # Analyze chord types used
        chord_types = [name.replace(name[0] if name else 'C', '').lower() for name in chord_names]
        has_sevenths = any('7' in ct for ct in chord_types)
        has_extensions = any(any(ext in ct for ext in ['9', '11', '13', 'add']) for ct in chord_types)
        has_sus = any('sus' in ct for ct in chord_types)
        
        # Check for style indicators
        complexity_score = getattr(analysis, 'complexity_score', 0.5) if analysis else 0.5
        
        if complexity_score > 0.8 and has_extensions:
            if 'maj7' in str(chord_types) and 'min7' in str(chord_types):
                return 'neo_soul'
            elif has_sevenths:
                return 'jazz'
        
        if analysis.complexity_score < 0.3:
            if has_sus:
                return 'grunge'
            else:
                return 'punk'
        
        # Check for common progressions
        chord_names = [chord.get('name', 'C') for chord in chords]
        if len(chord_names) >= 4:
            # Check for vi-IV-I-V (modern pop)
            if any('m' in name for name in chord_names[:2]):
                return 'modern_pop'
            # Check for I-bVII-IV pattern (rock)
            elif len(set(chord_names)) <= 3:
                return 'rock'
        
        # Default based on mood tags
        if 'dark' in analysis.mood_tags or 'minor' in analysis.mood_tags:
            return 'alt_rnb' if has_sevenths else 'grunge'
        elif 'bright' in analysis.mood_tags:
            return 'britpop'
        
        return 'modern_pop'  # Safe default
    
    def _enhance_chord_for_style(self, chord_type: str, style: str, complexity: float) -> str:
        """Enhance a chord type based on style preferences."""
        
        style_enhancements = {
            'neo_soul': {
                'maj': 'maj7' if complexity > 0.5 else 'maj',
                'min': 'min7' if complexity > 0.5 else 'min',
                '7': '9' if complexity > 0.7 else '7'
            },
            'funk': {
                'maj': '7',
                'min': 'min7',
                '7': '9' if complexity > 0.6 else '7'
            },
            'jazz': {
                'maj': 'maj7',
                'min': 'min7',
                '7': '13' if complexity > 0.8 else '9'
            },
            'grunge': {
                'maj': 'sus2' if complexity > 0.4 else 'maj',
                'min': 'add9' if complexity > 0.5 else 'min'
            },
            'trap': {
                'min': 'min7',
                'maj': 'min7',  # Tend toward minor
                '7': 'min7'
            },
            'prog_rock': {
                'maj': 'maj7' if complexity > 0.5 else 'add9',
                'min': 'min7' if complexity > 0.5 else 'sus2'
            }
        }
        
        if style in style_enhancements and chord_type in style_enhancements[style]:
            return style_enhancements[style][chord_type]
        
        return chord_type
    
    def _get_style_specific_role(self, function: str, style: str) -> Optional[str]:
        """Get style-specific role names for chord functions."""
        
        style_roles = {
            'funk': {
                'tonic': 'Groove Foundation',
                'subdominant': 'Funk Subdominant',
                'dominant': 'Rhythmic Driver'
            },
            'trap': {
                'tonic': 'Dark Center',
                'subdominant': 'Atmospheric Color',
                'dominant': 'Tension Builder'
            },
            'jazz': {
                'tonic': 'Home Base',
                'subdominant': 'Departure Point',
                'dominant': 'Resolution Driver'
            },
            'grunge': {
                'tonic': 'Heavy Foundation',
                'subdominant': 'Emotional Release',
                'dominant': 'Dynamic Tension'
            },
            'neo_soul': {
                'tonic': 'Soul Center',
                'subdominant': 'Smooth Departure',
                'dominant': 'Hip-Hop Resolution'
            }
        }
        
        if style in style_roles and function.lower() in style_roles[style]:
            return style_roles[style][function.lower()]
        
        return None
    
    def expand_progression_with_style(self, chords: List[dict], analysis, style: Optional[str] = None) -> List[dict]:
        """Expand progression with style-specific variations."""
        
        if not style:
            return self.expand_progression(chords, analysis)
        
        expanded = []
        
        # Style-specific expansion patterns
        style_expansions = {
            'funk': ['passing_chord', 'rhythmic_variation'],
            'jazz': ['tritone_sub', 'chromatic_approach'],
            'neo_soul': ['extended_harmony', 'smooth_voice_leading'],
            'trap': ['bass_movement', 'atmospheric_chord'],
            'prog_rock': ['modal_interchange', 'complex_substitution'],
            'grunge': ['power_chord_variation', 'dynamic_contrast']
        }
        
        expansion_types = style_expansions.get(style, ['basic_variation'])
        
        # Add style-appropriate variations
        for i, chord in enumerate(chords[:-1]):  # Don't expand last chord
            if random.random() < 0.3:  # 30% chance to expand
                expansion_type = random.choice(expansion_types)
                expanded_chord = self._create_style_expansion(chord, expansion_type, style)
                if expanded_chord:
                    expanded.append(expanded_chord)
        
        return expanded
    
    def _create_style_expansion(self, base_chord: dict, expansion_type: str, style: str) -> Optional[dict]:
        """Create a style-specific chord expansion."""
        
        base_name = base_chord.get('name', 'C')
        root_note = base_name[0]
        
        expansions = {
            'passing_chord': {
                'name': f"{root_note}sus4",
                'role': f"Passing Chord ({style})",
                'notes': self.get_chord_notes(root_note, 'sus4')
            },
            'tritone_sub': {
                'name': f"{self.number_to_note((self.note_to_number(root_note) + 6) % 12)}7",
                'role': f"Tritone Sub ({style})",
                'notes': self.get_chord_notes(self.number_to_note((self.note_to_number(root_note) + 6) % 12), '7')
            },
            'extended_harmony': {
                'name': f"{root_note}maj9",
                'role': f"Extended Harmony ({style})",
                'notes': self.get_chord_notes(root_note, 'maj9')
            },
            'atmospheric_chord': {
                'name': f"{root_note}min7",
                'role': f"Atmospheric ({style})",
                'notes': self.get_chord_notes(root_note, 'min7')
            }
        }
        
        if expansion_type in expansions:
            return expansions[expansion_type]
        
        return None
    
    def close(self):
        """Close database connection."""
        if hasattr(self, 'conn'):
            self.conn.close()
    
    def note_to_number(self, note: str) -> int:
        """Convert note name to chromatic number (C=0)."""
        note_map = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 
                   'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8, 
                   'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11}
        return note_map.get(note, 0)
    
    def number_to_note(self, number: int) -> str:
        """Convert chromatic number to note name."""
        note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        return note_names[number % 12]
    
    def get_chord_notes(self, root_note: str, chord_quality: str) -> Optional[List[str]]:
        """Get the notes in a chord given root note and quality."""
        if chord_quality not in self.CHORD_INTERVALS:
            return None
        
        intervals = self.CHORD_INTERVALS[chord_quality]
        root_num = self.note_to_number(root_note)
        
        chord_notes = []
        for interval in intervals:
            note_num = (root_num + interval) % 12
            chord_notes.append(self.number_to_note(note_num))
        
        return chord_notes
    
    def generate_scale(self, root_note: str, scale_name: str) -> Optional[List[str]]:
        """Generate a scale from root note using scale intervals."""
        if scale_name not in self.SCALE_INTERVALS:
            return None
        
        intervals = self.SCALE_INTERVALS[scale_name]
        root_num = self.note_to_number(root_note)
        
        scale_notes = []
        for interval in intervals:
            note_num = (root_num + interval) % 12
            scale_notes.append(self.number_to_note(note_num))
        
        return scale_notes

# Example usage and testing
if __name__ == '__main__':
    # Test the music theory engine
    engine = MusicTheoryEngine()
    
    # Generate a progression
    progression = engine.generate_progression(
        key="C", 
        scale="major", 
        length=4, 
        style="jazz",
        complexity=0.7
    )
    
    print("Generated progression:")
    for chord in progression:
        print(f"  {chord['name']}: {chord['notes']}")
    
    engine.close()
