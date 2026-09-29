#!/usr/bin/env python3
"""
Database Enhancement for MIDI Chord Library Integration

This module enhances the existing music theory engine database to support:
1. MIDI file analysis data storage
2. Advanced chord voicing and timing information
3. Machine learning features for chord recognition improvement
4. MIDI track and instrument metadata
5. Progressive learning statistics and analytics

Features:
- Backward compatible with existing database schema
- New tables for MIDI-specific data
- Enhanced existing tables with new fields
- Analytics and statistics for machine learning
- Data migration support for existing databases
"""

import os
import sqlite3
import logging
import json
from typing import Optional, Dict, List, Any
from datetime import datetime
import traceback

# Import ProgressionAnalysis for type hints
try:
    from midi_chord_analyzer import ProgressionAnalysis
except ImportError:
    # Create dummy class for type hints if not available
    class ProgressionAnalysis:
        pass

class DatabaseEnhancer:
    """Enhances the music theory engine database for MIDI support."""
    
    def __init__(self, db_path: str):
        """Initialize the database enhancer."""
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self.conn = None
        self.cursor = None
        
    def enhance_database(self) -> bool:
        """
        Enhance the existing database with new tables and fields for MIDI support.
        
        Returns:
            True if enhancement was successful, False otherwise
        """
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            
            # Check database version and create version table if needed
            self._setup_version_tracking()
            
            current_version = self._get_database_version()
            target_version = "2.0.0"  # MIDI enhancement version
            
            if current_version == target_version:
                self.logger.info(f"Database already at version {target_version}")
                return True
            
            self.logger.info(f"Enhancing database from version {current_version} to {target_version}")
            
            # Start transaction
            self.cursor.execute("BEGIN TRANSACTION")
            
            # Enhance existing tables
            self._enhance_existing_tables()
            
            # Create new tables for MIDI data
            self._create_midi_tables()
            
            # Create analytics tables
            self._create_analytics_tables()
            
            # Update database version
            self._set_database_version(target_version)
            
            # Commit transaction
            self.conn.commit()
            
            self.logger.info("Database enhancement completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Database enhancement failed: {e}")
            self.logger.error(traceback.format_exc())
            if self.conn:
                self.conn.rollback()
            return False
        finally:
            if self.conn:
                self.conn.close()
    
    def _setup_version_tracking(self):
        """Setup version tracking table."""
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS database_version (
                version TEXT PRIMARY KEY,
                upgraded_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            )
        ''')
        
        # Check if we have any version entries
        self.cursor.execute("SELECT COUNT(*) FROM database_version")
        if self.cursor.fetchone()[0] == 0:
            # First time setup - assume version 1.0.0
            self.cursor.execute('''
                INSERT INTO database_version (version, description) 
                VALUES ('1.0.0', 'Initial music theory engine database')
            ''')
    
    def _get_database_version(self) -> str:
        """Get current database version."""
        self.cursor.execute(
            "SELECT version FROM database_version ORDER BY upgraded_date DESC LIMIT 1"
        )
        result = self.cursor.fetchone()
        return result[0] if result else "1.0.0"
    
    def _set_database_version(self, version: str):
        """Set database version."""
        self.cursor.execute('''
            INSERT INTO database_version (version, description) 
            VALUES (?, 'Enhanced for MIDI support')
        ''', (version,))
    
    def _enhance_existing_tables(self):
        """Enhance existing tables with new fields for MIDI support."""
        # Enhance chords table
        self._add_column_if_not_exists('chords', 'inversion', 'INTEGER DEFAULT 0')
        self._add_column_if_not_exists('chords', 'bass_note', 'INTEGER')
        self._add_column_if_not_exists('chords', 'complexity_score', 'REAL DEFAULT 0.0')
        self._add_column_if_not_exists('chords', 'confidence_score', 'REAL DEFAULT 1.0')
        self._add_column_if_not_exists('chords', 'midi_source_id', 'INTEGER')
        self._add_column_if_not_exists('chords', 'timing_data', 'TEXT')  # JSON for start_time, end_time, duration
        self._add_column_if_not_exists('chords', 'pitch_range', 'TEXT')  # JSON for min_pitch, max_pitch
        self._add_column_if_not_exists('chords', 'velocity_data', 'TEXT')  # JSON for velocity statistics
        
        # Enhance progressions table
        self._add_column_if_not_exists('progressions', 'tempo', 'REAL DEFAULT 120.0')
        self._add_column_if_not_exists('progressions', 'time_signature', 'TEXT DEFAULT "4/4"')
        self._add_column_if_not_exists('progressions', 'total_duration', 'REAL DEFAULT 0.0')
        self._add_column_if_not_exists('progressions', 'modulations', 'TEXT')  # JSON array of modulations
        self._add_column_if_not_exists('progressions', 'mood_indicators', 'TEXT')  # JSON array
        self._add_column_if_not_exists('progressions', 'roman_numerals', 'TEXT')  # JSON array
        self._add_column_if_not_exists('progressions', 'harmonic_rhythm', 'REAL DEFAULT 0.0')
        self._add_column_if_not_exists('progressions', 'midi_source_id', 'INTEGER')
        
        self.logger.info("Enhanced existing tables with MIDI-specific fields")
    
    def _create_midi_tables(self):
        """Create new tables for MIDI-specific data."""
        
        # MIDI files table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS midi_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL UNIQUE,
                file_name TEXT NOT NULL,
                file_size INTEGER,
                midi_format INTEGER,
                num_tracks INTEGER,
                ticks_per_beat INTEGER,
                duration REAL,
                analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                analysis_version TEXT,
                metadata TEXT,  -- JSON for additional metadata
                processing_status TEXT DEFAULT 'pending'  -- pending, completed, failed
            )
        ''')
        
        # MIDI tracks table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS midi_tracks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                midi_file_id INTEGER NOT NULL,
                track_number INTEGER NOT NULL,
                track_name TEXT,
                instrument_name TEXT,
                instrument_program INTEGER,
                is_drum_track BOOLEAN DEFAULT FALSE,
                channel INTEGER,
                num_notes INTEGER,
                note_range_min INTEGER,
                note_range_max INTEGER,
                total_duration REAL,
                used_for_analysis BOOLEAN DEFAULT FALSE,
                track_score REAL DEFAULT 0.0,  -- Score for chord analysis suitability
                notes_data TEXT,  -- JSON array of note events
                FOREIGN KEY (midi_file_id) REFERENCES midi_files (id) ON DELETE CASCADE
            )
        ''')
        
        # MIDI chord instances table (detailed chord occurrences)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS midi_chord_instances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                midi_file_id INTEGER NOT NULL,
                progression_id INTEGER,
                chord_id INTEGER,
                start_time REAL NOT NULL,
                end_time REAL NOT NULL,
                duration REAL NOT NULL,
                confidence REAL DEFAULT 0.0,
                detected_notes TEXT NOT NULL,  -- JSON array of MIDI note numbers
                track_sources TEXT,  -- JSON array of track numbers
                voicing_analysis TEXT,  -- JSON with voicing details
                harmonic_context TEXT,  -- JSON with harmonic analysis
                FOREIGN KEY (midi_file_id) REFERENCES midi_files (id) ON DELETE CASCADE,
                FOREIGN KEY (progression_id) REFERENCES progressions (id) ON DELETE CASCADE,
                FOREIGN KEY (chord_id) REFERENCES chords (id) ON DELETE CASCADE
            )
        ''')
        
        # Key detection results
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS key_detection_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                midi_file_id INTEGER NOT NULL,
                detected_key TEXT,
                confidence REAL DEFAULT 0.0,
                analysis_method TEXT,
                pitch_class_distribution TEXT,  -- JSON with pitch class counts
                krumhansl_scores TEXT,  -- JSON with all key scores
                time_segments TEXT,  -- JSON for time-based key analysis
                modulation_points TEXT,  -- JSON array of detected modulations
                FOREIGN KEY (midi_file_id) REFERENCES midi_files (id) ON DELETE CASCADE
            )
        ''')
        
        self.logger.info("Created MIDI-specific tables")
    
    def _create_analytics_tables(self):
        """Create tables for machine learning analytics."""
        
        # Chord recognition statistics
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS chord_recognition_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chord_type TEXT NOT NULL,
                root_note INTEGER NOT NULL,
                total_occurrences INTEGER DEFAULT 0,
                correct_detections INTEGER DEFAULT 0,
                false_positives INTEGER DEFAULT 0,
                false_negatives INTEGER DEFAULT 0,
                average_confidence REAL DEFAULT 0.0,
                improvement_score REAL DEFAULT 0.0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(chord_type, root_note)
            )
        ''')
        
        # Pattern analysis results
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS progression_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT NOT NULL,  -- e.g., "ii-V-I", "vi-IV-I-V"
                pattern_sequence TEXT NOT NULL,  -- JSON array of chord symbols
                key_context TEXT,
                occurrence_count INTEGER DEFAULT 1,
                complexity_rating REAL DEFAULT 0.0,
                mood_associations TEXT,  -- JSON array
                genre_associations TEXT,  -- JSON array
                classical_period TEXT,
                jazz_era TEXT,
                first_detected TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_detected TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Learning progress tracking
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS learning_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                measurement_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_points_count INTEGER DEFAULT 0,
                improvement_rate REAL DEFAULT 0.0,
                notes TEXT
            )
        ''')
        
        # User feedback for machine learning
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                midi_file_id INTEGER,
                chord_instance_id INTEGER,
                feedback_type TEXT NOT NULL,  -- 'chord_correction', 'key_correction', 'progression_rating'
                original_value TEXT,
                corrected_value TEXT,
                user_confidence INTEGER DEFAULT 5,  -- 1-10 scale
                feedback_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                applied_to_learning BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (midi_file_id) REFERENCES midi_files (id) ON DELETE CASCADE,
                FOREIGN KEY (chord_instance_id) REFERENCES midi_chord_instances (id) ON DELETE CASCADE
            )
        ''')
        
        self.logger.info("Created analytics and machine learning tables")
    
    def _add_column_if_not_exists(self, table_name: str, column_name: str, column_definition: str):
        """Add a column to a table if it doesn't already exist."""
        try:
            # Check if column exists
            self.cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [row[1] for row in self.cursor.fetchall()]
            
            if column_name not in columns:
                self.cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}")
                self.logger.info(f"Added column {column_name} to table {table_name}")
            else:
                self.logger.debug(f"Column {column_name} already exists in table {table_name}")
                
        except Exception as e:
            self.logger.error(f"Error adding column {column_name} to {table_name}: {e}")
            raise

class MIDIDataManager:
    """Manager for MIDI-specific data operations with the enhanced database."""
    
    def __init__(self, db_path: str):
        """Initialize the MIDI data manager."""
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
    def store_midi_analysis(self, analysis: 'ProgressionAnalysis') -> Optional[int]:
        """
        Store MIDI analysis results in the database.
        
        Args:
            analysis: ProgressionAnalysis object from MIDI analyzer
            
        Returns:
            MIDI file ID if successful, None otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Store MIDI file information
                cursor.execute('''
                    INSERT OR REPLACE INTO midi_files 
                    (file_path, file_name, midi_format, num_tracks, ticks_per_beat, 
                     duration, metadata, processing_status) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'completed')
                ''', (
                    analysis.file_path,
                    os.path.basename(analysis.file_path),
                    analysis.analysis_metadata.get('midi_format', 0),
                    len(analysis.tracks_analyzed),
                    analysis.analysis_metadata.get('ticks_per_beat', 480),
                    analysis.total_duration,
                    json.dumps(analysis.analysis_metadata),
                ))
                
                midi_file_id = cursor.lastrowid
                
                # Store progression information
                cursor.execute('''
                    INSERT INTO progressions 
                    (name, chords, key_signature, scale, mood_tags, complexity_score, 
                     tempo, time_signature, total_duration, modulations, mood_indicators, 
                     roman_numerals, source_file, midi_source_id) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    f"MIDI: {os.path.basename(analysis.file_path)}",
                    json.dumps(analysis.chord_symbols),
                    analysis.key_signature or "",
                    analysis.scale_type,
                    json.dumps(analysis.mood_indicators),
                    analysis.complexity_score,
                    analysis.tempo,
                    f"{analysis.time_signature[0]}/{analysis.time_signature[1]}",
                    analysis.total_duration,
                    json.dumps([{"time": t, "from": f, "to": to} for t, f, to in analysis.modulations]),
                    json.dumps(analysis.mood_indicators),
                    json.dumps(analysis.roman_numerals),
                    analysis.file_path,
                    midi_file_id
                ))
                
                progression_id = cursor.lastrowid
                
                # Store individual chord instances
                for chord in analysis.chords:
                    # First, store the chord definition if it's new
                    cursor.execute('''
                        INSERT OR IGNORE INTO chords 
                        (root, type, intervals, notes, voicing, inversion, bass_note, 
                         complexity_score, confidence_score, timing_data, midi_source_id) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        chord.root,
                        chord.chord_type,
                        json.dumps([0, 4, 7]),  # Default intervals - could be enhanced
                        json.dumps(chord.notes),
                        chord.voicing,
                        chord.inversion,
                        chord.bass_note,
                        chord.complexity_score,
                        chord.confidence,
                        json.dumps({
                            'start_time': chord.start_time,
                            'end_time': chord.end_time,
                            'duration': chord.duration
                        }),
                        midi_file_id
                    ))
                    
                    # Get the chord ID
                    cursor.execute('''
                        SELECT id FROM chords 
                        WHERE root = ? AND type = ? AND midi_source_id = ? 
                        ORDER BY id DESC LIMIT 1
                    ''', (chord.root, chord.chord_type, midi_file_id))
                    
                    chord_id_result = cursor.fetchone()
                    chord_id = chord_id_result[0] if chord_id_result else None
                    
                    # Store the chord instance
                    cursor.execute('''
                        INSERT INTO midi_chord_instances 
                        (midi_file_id, progression_id, chord_id, start_time, end_time, 
                         duration, confidence, detected_notes, track_sources, 
                         voicing_analysis, harmonic_context) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        midi_file_id,
                        progression_id,
                        chord_id,
                        chord.start_time,
                        chord.end_time,
                        chord.duration,
                        chord.confidence,
                        json.dumps(chord.notes),
                        json.dumps(chord.track_sources),
                        json.dumps({'voicing': chord.voicing, 'inversion': chord.inversion}),
                        json.dumps({'harmonic_function': chord.harmonic_function})
                    ))
                
                # Store key detection results if available
                if analysis.key_signature:
                    cursor.execute('''
                        INSERT INTO key_detection_results 
                        (midi_file_id, detected_key, confidence, analysis_method) 
                        VALUES (?, ?, ?, ?)
                    ''', (
                        midi_file_id,
                        analysis.key_signature,
                        0.8,  # Default confidence - could be enhanced with actual confidence
                        'krumhansl_schmuckler'
                    ))
                
                self.logger.info(f"Successfully stored MIDI analysis for {analysis.file_path}")
                return midi_file_id
                
        except Exception as e:
            self.logger.error(f"Error storing MIDI analysis: {e}")
            return None
    
    def get_learning_statistics(self) -> Dict[str, Any]:
        """Get statistics for machine learning progress."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                stats = {}
                
                # Total MIDI files processed
                cursor.execute("SELECT COUNT(*) FROM midi_files WHERE processing_status = 'completed'")
                stats['total_midi_files'] = cursor.fetchone()[0]
                
                # Total chords detected
                cursor.execute("SELECT COUNT(*) FROM midi_chord_instances")
                stats['total_chord_instances'] = cursor.fetchone()[0]
                
                # Unique chord types discovered
                cursor.execute("SELECT COUNT(DISTINCT type) FROM chords WHERE midi_source_id IS NOT NULL")
                stats['unique_chord_types'] = cursor.fetchone()[0]
                
                # Average confidence scores
                cursor.execute("SELECT AVG(confidence) FROM midi_chord_instances WHERE confidence > 0")
                result = cursor.fetchone()
                stats['average_detection_confidence'] = result[0] if result[0] else 0.0
                
                # Key detection success rate
                cursor.execute("SELECT COUNT(*) FROM key_detection_results WHERE confidence > 0.6")
                stats['successful_key_detections'] = cursor.fetchone()[0]
                
                # Most common progressions
                cursor.execute('''
                    SELECT chords, COUNT(*) as count 
                    FROM progressions 
                    WHERE midi_source_id IS NOT NULL 
                    GROUP BY chords 
                    ORDER BY count DESC 
                    LIMIT 10
                ''')
                stats['common_progressions'] = [
                    {'chords': row[0], 'count': row[1]} 
                    for row in cursor.fetchall()
                ]
                
                return stats
                
        except Exception as e:
            self.logger.error(f"Error getting learning statistics: {e}")
            return {}

def enhance_music_theory_database(db_path: str) -> bool:
    """
    Public function to enhance an existing music theory database for MIDI support.
    
    Args:
        db_path: Path to the database file
        
    Returns:
        True if enhancement was successful, False otherwise
    """
    enhancer = DatabaseEnhancer(db_path)
    return enhancer.enhance_database()

if __name__ == "__main__":
    # Test the database enhancement
    import tempfile
    import sys
    
    # Create a test database
    test_db_path = os.path.join(tempfile.gettempdir(), "test_music_theory.db")
    
    print(f"Testing database enhancement with: {test_db_path}")
    
    # Create basic database structure first (simulate existing database)
    with sqlite3.connect(test_db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE chords (
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
        cursor.execute('''
            CREATE TABLE progressions (
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
        conn.commit()
    
    # Test enhancement
    success = enhance_music_theory_database(test_db_path)
    
    if success:
        print("✅ Database enhancement successful!")
        
        # Test MIDI data manager
        manager = MIDIDataManager(test_db_path)
        stats = manager.get_learning_statistics()
        print("📊 Learning statistics:", stats)
        
    else:
        print("❌ Database enhancement failed!")
        sys.exit(1)
    
    # Cleanup
    os.unlink(test_db_path)
    print("🧹 Test database cleaned up")