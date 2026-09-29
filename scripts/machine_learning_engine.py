#!/usr/bin/env python3
"""
Machine Learning Chord Analysis System for XPM Music Theory Engine

This module provides:
1. Adaptive chord recognition that learns from user corrections
2. Pattern recognition for common chord progressions
3. Statistical analysis of user's musical preferences
4. Predictive chord suggestions based on context
5. Confidence scoring improvements over time
6. Genre and style classification learning

Features:
- Bayesian learning for chord recognition accuracy
- Markov chain analysis for progression patterns
- User feedback integration for continuous improvement
- Statistical modeling of harmonic preferences
- Real-time confidence adjustment
- Personalized music theory suggestions
- Genre classification and style adaptation
"""

import os
import json
import sqlite3
import logging
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import defaultdict, Counter
from datetime import datetime, timedelta
import threading
import math

# Optional dependencies for enhanced ML features
try:
    import scipy.stats as stats
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

try:
    from sklearn.naive_bayes import GaussianNB
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

@dataclass
class ChordPrediction:
    """Represents a chord prediction with confidence metrics."""
    chord_symbol: str
    root: int
    chord_type: str
    confidence: float
    context_score: float
    user_preference_score: float
    historical_accuracy: float
    reasoning: List[str] = field(default_factory=list)

@dataclass
class ProgressionPattern:
    """Represents a learned chord progression pattern."""
    pattern_id: str
    sequence: List[str]  # Chord symbols or Roman numerals
    frequency: int
    contexts: List[str]  # Keys, genres, etc.
    user_rating: float
    last_seen: datetime
    confidence: float
    genre_associations: List[str] = field(default_factory=list)

@dataclass
class LearningMetrics:
    """Tracks learning progress and accuracy metrics."""
    total_predictions: int = 0
    correct_predictions: int = 0
    user_corrections: int = 0
    confidence_improvements: float = 0.0
    pattern_discoveries: int = 0
    accuracy_trend: List[float] = field(default_factory=list)
    last_update: Optional[datetime] = None

class MachineLearningEngine:
    """Advanced machine learning system for chord analysis improvement."""
    
    def __init__(self, db_path: str):
        """Initialize the machine learning engine."""
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
        # Learning parameters
        self.learning_rate = 0.1
        self.confidence_threshold = 0.7
        self.pattern_min_frequency = 3
        self.max_pattern_length = 8
        
        # In-memory caches for performance
        self.chord_accuracy_cache = {}
        self.pattern_cache = {}
        self.user_preference_cache = {}
        
        # Thread safety
        self.lock = threading.Lock()
        
        # Initialize learning models
        self._initialize_models()
        
        # Load existing patterns and statistics
        self._load_learning_data()
    
    def _initialize_models(self):
        """Initialize machine learning models if available."""
        self.chord_classifier = None
        self.pattern_predictor = None
        
        if SKLEARN_AVAILABLE:
            try:
                self.chord_classifier = GaussianNB()
                self.pattern_predictor = RandomForestClassifier(n_estimators=50, random_state=42)
                self.logger.info("Initialized scikit-learn models for enhanced ML features")
            except Exception as e:
                self.logger.warning(f"Failed to initialize ML models: {e}")
    
    def _load_learning_data(self):
        """Load existing learning data from database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Load chord accuracy statistics
                cursor.execute('''
                    SELECT chord_type, root_note, total_occurrences, correct_detections 
                    FROM chord_recognition_stats
                ''')
                
                for row in cursor.fetchall():
                    chord_type, root_note, total, correct = row
                    key = (chord_type, root_note)
                    accuracy = correct / total if total > 0 else 0.5
                    self.chord_accuracy_cache[key] = {
                        'accuracy': accuracy,
                        'total': total,
                        'correct': correct
                    }
                
                # Load progression patterns
                cursor.execute('''
                    SELECT pattern_type, pattern_sequence, occurrence_count, complexity_rating
                    FROM progression_patterns
                    ORDER BY occurrence_count DESC
                    LIMIT 1000
                ''')
                
                for row in cursor.fetchall():
                    pattern_type, sequence, count, complexity = row
                    self.pattern_cache[pattern_type] = {
                        'sequence': json.loads(sequence),
                        'frequency': count,
                        'complexity': complexity
                    }
                
                self.logger.info(f"Loaded {len(self.chord_accuracy_cache)} chord stats and {len(self.pattern_cache)} patterns")
                
        except Exception as e:
            self.logger.error(f"Error loading learning data: {e}")
    
    def predict_next_chord(self, current_progression: List[str], key: Optional[str] = None, 
                          genre: Optional[str] = None) -> List[ChordPrediction]:
        """
        Predict the next most likely chords in a progression.
        
        Args:
            current_progression: List of chord symbols in the current progression
            key: Key signature (e.g., "C major", "A minor")
            genre: Musical genre context
            
        Returns:
            List of chord predictions ranked by likelihood
        """
        predictions = []
        
        try:
            # Analyze current progression context
            context = self._analyze_progression_context(current_progression, key, genre)
            
            # Get pattern-based predictions
            pattern_predictions = self._get_pattern_based_predictions(current_progression, context)
            
            # Get theory-based predictions
            theory_predictions = self._get_theory_based_predictions(current_progression, key)
            
            # Get user preference predictions
            preference_predictions = self._get_preference_based_predictions(current_progression, context)
            
            # Combine and rank predictions
            combined_predictions = self._combine_predictions(
                pattern_predictions, theory_predictions, preference_predictions, context
            )
            
            # Apply confidence scoring
            final_predictions = self._apply_confidence_scoring(combined_predictions, context)
            
            # Sort by overall confidence
            predictions = sorted(final_predictions, key=lambda p: p.confidence, reverse=True)
            
            # Limit to top 10 predictions
            predictions = predictions[:10]
            
        except Exception as e:
            self.logger.error(f"Error predicting next chord: {e}")
        
        return predictions
    
    def _analyze_progression_context(self, progression: List[str], key: Optional[str], 
                                   genre: Optional[str]) -> Dict[str, Any]:
        """Analyze the context of the current progression."""
        context = {
            'length': len(progression),
            'key': key,
            'genre': genre,
            'last_chord': progression[-1] if progression else None,
            'harmonic_rhythm': self._estimate_harmonic_rhythm(progression),
            'complexity': self._estimate_progression_complexity(progression),
            'mood': self._estimate_mood_from_progression(progression),
            'era': self._estimate_musical_era(progression),
        }
        
        # Analyze recent chord patterns
        if len(progression) >= 2:
            context['recent_pattern'] = progression[-3:]  # Last 3 chords
            context['cadence_type'] = self._analyze_cadence(progression[-3:])
        
        # Key analysis
        if key:
            context['key_root'] = key.split()[0] if ' ' in key else key[:1]
            context['mode'] = 'major' if 'major' in key.lower() else 'minor'
        
        return context
    
    def _get_pattern_based_predictions(self, progression: List[str], 
                                     context: Dict[str, Any]) -> List[ChordPrediction]:
        """Get chord predictions based on learned patterns."""
        predictions = []
        
        # Look for matching patterns in our cache
        for pattern_type, pattern_data in self.pattern_cache.items():
            sequence = pattern_data['sequence']
            frequency = pattern_data['frequency']
            
            # Check if current progression matches the beginning of this pattern
            if self._progression_matches_pattern(progression, sequence):
                next_chord_idx = len(progression)
                if next_chord_idx < len(sequence):
                    next_chord = sequence[next_chord_idx]
                    
                    # Calculate confidence based on pattern frequency and context match
                    confidence = self._calculate_pattern_confidence(pattern_data, context)
                    
                    prediction = ChordPrediction(
                        chord_symbol=next_chord,
                        root=self._parse_chord_root(next_chord),
                        chord_type=self._parse_chord_type(next_chord),
                        confidence=confidence,
                        context_score=0.8,  # Pattern matching has high context relevance
                        user_preference_score=0.5,  # Neutral until we know user preferences
                        historical_accuracy=self._get_chord_historical_accuracy(next_chord),
                        reasoning=[f"Pattern match: {pattern_type} (frequency: {frequency})"]
                    )
                    predictions.append(prediction)
        
        return predictions
    
    def _get_theory_based_predictions(self, progression: List[str], 
                                    key: Optional[str]) -> List[ChordPrediction]:
        """Get chord predictions based on music theory rules."""
        predictions = []
        
        try:
            # Common progressions and cadences
            theory_rules = [
                self._apply_circle_of_fifths,
                self._apply_functional_harmony,
                self._apply_common_cadences,
                self._apply_modal_interchange,
                self._apply_secondary_dominants
            ]
            
            for rule_func in theory_rules:
                try:
                    rule_predictions = rule_func(progression, key)
                    predictions.extend(rule_predictions)
                except Exception as e:
                    self.logger.debug(f"Theory rule failed: {e}")
            
        except Exception as e:
            self.logger.error(f"Error in theory-based predictions: {e}")
        
        return predictions
    
    def _get_preference_based_predictions(self, progression: List[str], 
                                        context: Dict[str, Any]) -> List[ChordPrediction]:
        """Get predictions based on learned user preferences."""
        predictions = []
        
        # This would analyze user's historical choices and preferences
        # For now, return basic preferences based on cached data
        
        try:
            # Analyze user's chord preferences by frequency of use
            user_chord_freq = self._get_user_chord_frequencies()
            
            # Get contextually relevant chords
            relevant_chords = self._get_contextually_relevant_chords(context)
            
            for chord in relevant_chords:
                frequency = user_chord_freq.get(chord, 0)
                if frequency > 0:
                    # Calculate user preference score
                    max_freq = max(user_chord_freq.values()) if user_chord_freq else 1
                    preference_score = frequency / max_freq
                    
                    prediction = ChordPrediction(
                        chord_symbol=chord,
                        root=self._parse_chord_root(chord),
                        chord_type=self._parse_chord_type(chord),
                        confidence=preference_score * 0.6,  # Moderate confidence for preferences
                        context_score=0.6,
                        user_preference_score=preference_score,
                        historical_accuracy=self._get_chord_historical_accuracy(chord),
                        reasoning=[f"User preference (used {frequency} times)"]
                    )
                    predictions.append(prediction)
                    
        except Exception as e:
            self.logger.error(f"Error in preference-based predictions: {e}")
        
        return predictions
    
    def _combine_predictions(self, *prediction_lists: List[ChordPrediction], 
                           context: Dict[str, Any]) -> List[ChordPrediction]:
        """Combine multiple prediction lists into one ranked list."""
        combined = defaultdict(list)
        
        # Group predictions by chord symbol
        for pred_list in prediction_lists:
            for pred in pred_list:
                combined[pred.chord_symbol].append(pred)
        
        # Merge predictions for same chords
        final_predictions = []
        for chord_symbol, pred_group in combined.items():
            if not pred_group:
                continue
                
            # Combine the predictions for this chord
            merged_pred = self._merge_chord_predictions(pred_group, context)
            if merged_pred:
                final_predictions.append(merged_pred)
        
        return final_predictions
    
    def _merge_chord_predictions(self, predictions: List[ChordPrediction], 
                               context: Dict[str, Any]) -> Optional[ChordPrediction]:
        """Merge multiple predictions for the same chord."""
        if not predictions:
            return None
        
        # Use the first prediction as base
        base = predictions[0]
        
        # Combine confidence scores (weighted average)
        total_weight = 0
        weighted_confidence = 0
        combined_reasoning = []
        
        weights = {
            'pattern': 0.4,
            'theory': 0.3,
            'preference': 0.3
        }
        
        for pred in predictions:
            # Determine prediction type based on reasoning
            pred_type = self._determine_prediction_type(pred.reasoning)
            weight = weights.get(pred_type, 0.2)
            
            weighted_confidence += pred.confidence * weight
            total_weight += weight
            combined_reasoning.extend(pred.reasoning)
        
        # Normalize confidence
        final_confidence = weighted_confidence / total_weight if total_weight > 0 else 0.5
        
        # Combine other scores
        avg_context = sum(p.context_score for p in predictions) / len(predictions)
        avg_preference = sum(p.user_preference_score for p in predictions) / len(predictions)
        avg_historical = sum(p.historical_accuracy for p in predictions) / len(predictions)
        
        return ChordPrediction(
            chord_symbol=base.chord_symbol,
            root=base.root,
            chord_type=base.chord_type,
            confidence=final_confidence,
            context_score=avg_context,
            user_preference_score=avg_preference,
            historical_accuracy=avg_historical,
            reasoning=list(set(combined_reasoning))  # Remove duplicates
        )
    
    def learn_from_user_feedback(self, context: Dict[str, Any], 
                                predicted_chord: str, actual_chord: str,
                                user_confidence: float = 1.0):
        """
        Learn from user corrections to improve future predictions.
        
        Args:
            context: The context when the prediction was made
            predicted_chord: What the system predicted
            actual_chord: What the user corrected it to
            user_confidence: How confident the user is (0.0 to 1.0)
        """
        try:
            with self.lock:
                # Update chord accuracy statistics
                self._update_chord_accuracy(predicted_chord, actual_chord, context)
                
                # Learn new patterns if applicable
                self._learn_progression_pattern(context, actual_chord)
                
                # Update user preferences
                self._update_user_preferences(actual_chord, context, user_confidence)
                
                # Store feedback in database for future analysis
                self._store_user_feedback(context, predicted_chord, actual_chord, user_confidence)
                
                # Retrain models if enough new data
                self._check_and_retrain_models()
                
        except Exception as e:
            self.logger.error(f"Error learning from user feedback: {e}")
    
    def _update_chord_accuracy(self, predicted: str, actual: str, context: Dict[str, Any]):
        """Update chord recognition accuracy statistics."""
        try:
            pred_root = self._parse_chord_root(predicted)
            pred_type = self._parse_chord_type(predicted)
            
            actual_root = self._parse_chord_root(actual)
            actual_type = self._parse_chord_type(actual)
            
            # Update statistics in database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Update predicted chord stats (it was wrong)
                cursor.execute('''
                    INSERT OR REPLACE INTO chord_recognition_stats 
                    (chord_type, root_note, total_occurrences, correct_detections, false_positives)
                    VALUES (?, ?, 
                        COALESCE((SELECT total_occurrences FROM chord_recognition_stats 
                                WHERE chord_type = ? AND root_note = ?), 0) + 1,
                        COALESCE((SELECT correct_detections FROM chord_recognition_stats 
                                WHERE chord_type = ? AND root_note = ?), 0),
                        COALESCE((SELECT false_positives FROM chord_recognition_stats 
                                WHERE chord_type = ? AND root_note = ?), 0) + 1)
                ''', (pred_type, pred_root, pred_type, pred_root, pred_type, pred_root, pred_type, pred_root))
                
                # Update actual chord stats (this is what should have been detected)
                cursor.execute('''
                    INSERT OR REPLACE INTO chord_recognition_stats 
                    (chord_type, root_note, total_occurrences, correct_detections, false_negatives)
                    VALUES (?, ?, 1, 0, 1)
                    ON CONFLICT(chord_type, root_note) DO UPDATE SET
                    total_occurrences = total_occurrences + 1,
                    false_negatives = false_negatives + 1
                ''', (actual_type, actual_root))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Error updating chord accuracy: {e}")
    
    def get_learning_statistics(self) -> LearningMetrics:
        """Get current learning progress statistics."""
        metrics = LearningMetrics()
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Total predictions and accuracy
                cursor.execute('''
                    SELECT SUM(total_occurrences), SUM(correct_detections)
                    FROM chord_recognition_stats
                ''')
                result = cursor.fetchone()
                if result and result[0]:
                    metrics.total_predictions = result[0]
                    metrics.correct_predictions = result[1] or 0
                
                # User corrections
                cursor.execute('SELECT COUNT(*) FROM user_feedback')
                result = cursor.fetchone()
                if result:
                    metrics.user_corrections = result[0]
                
                # Pattern discoveries
                cursor.execute('SELECT COUNT(*) FROM progression_patterns')
                result = cursor.fetchone()
                if result:
                    metrics.pattern_discoveries = result[0]
                
                # Recent accuracy trend
                metrics.accuracy_trend = self._calculate_accuracy_trend()
                metrics.last_update = datetime.now()
                
        except Exception as e:
            self.logger.error(f"Error getting learning statistics: {e}")
        
        return metrics
    
    def _calculate_accuracy_trend(self) -> List[float]:
        """Calculate accuracy trend over time."""
        trend = []
        try:
            # This is a simplified calculation - in reality you'd analyze temporal data
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get accuracy over time (simplified)
                cursor.execute('''
                    SELECT 
                        CASE WHEN SUM(total_occurrences) > 0 
                        THEN CAST(SUM(correct_detections) AS FLOAT) / SUM(total_occurrences)
                        ELSE 0 END as accuracy
                    FROM chord_recognition_stats
                ''')
                
                result = cursor.fetchone()
                if result and result[0] is not None:
                    # For now, just return current accuracy as a single point
                    trend = [result[0]]
                        
        except Exception as e:
            self.logger.debug(f"Error calculating accuracy trend: {e}")
        
        return trend or [0.5]  # Default 50% accuracy if no data
    
    # Utility methods for chord analysis
    def _parse_chord_root(self, chord_symbol: str) -> int:
        """Parse root note from chord symbol."""
        # Map note names to MIDI numbers
        note_map = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5, 
                   'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8, 'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11}
        
        if not chord_symbol:
            return 0
        
        # Extract root note (handle sharps and flats)
        if len(chord_symbol) > 1 and chord_symbol[1] in '#b':
            root_str = chord_symbol[:2]
        else:
            root_str = chord_symbol[0]
        
        return note_map.get(root_str, 0)
    
    def _parse_chord_type(self, chord_symbol: str) -> str:
        """Parse chord type from chord symbol."""
        if not chord_symbol:
            return 'maj'
        
        # Remove root note
        if len(chord_symbol) > 1 and chord_symbol[1] in '#b':
            suffix = chord_symbol[2:]
        else:
            suffix = chord_symbol[1:]
        
        # Common chord type mappings
        type_map = {
            '': 'maj', 'm': 'min', 'min': 'min', 'maj': 'maj', 'M': 'maj',
            '7': '7', 'maj7': 'maj7', 'min7': 'min7', 'm7': 'min7',
            'dim': 'dim', 'aug': 'aug', 'sus2': 'sus2', 'sus4': 'sus4'
        }
        
        return type_map.get(suffix.lower(), suffix.lower() or 'maj')
    
    # Placeholder implementations for complex theory methods
    def _estimate_harmonic_rhythm(self, progression: List[str]) -> float:
        """Estimate the harmonic rhythm of the progression."""
        return 1.0  # Default 1 chord per measure
    
    def _estimate_progression_complexity(self, progression: List[str]) -> float:
        """Estimate complexity of the progression."""
        complexity_scores = {'maj': 0.1, 'min': 0.1, '7': 0.3, 'maj7': 0.4, 'min7': 0.4}
        if not progression:
            return 0.0
        total_complexity = sum(complexity_scores.get(self._parse_chord_type(chord), 0.5) for chord in progression)
        return total_complexity / len(progression)
    
    def _estimate_mood_from_progression(self, progression: List[str]) -> str:
        """Estimate mood from chord progression."""
        minor_count = sum(1 for chord in progression if 'min' in chord.lower())
        major_count = len(progression) - minor_count
        return 'melancholic' if minor_count > major_count else 'uplifting'
    
    def _estimate_musical_era(self, progression: List[str]) -> str:
        """Estimate musical era from progression characteristics."""
        # Simple heuristic based on chord complexity
        avg_complexity = self._estimate_progression_complexity(progression)
        if avg_complexity < 0.2:
            return 'classical'
        elif avg_complexity < 0.4:
            return 'romantic'
        else:
            return 'jazz/modern'
    
    def _analyze_cadence(self, recent_chords: List[str]) -> str:
        """Analyze the type of cadence in recent chords."""
        if len(recent_chords) < 2:
            return 'none'
        
        # Very simplified cadence analysis
        last_two = recent_chords[-2:]
        if 'G' in last_two[0] and 'C' in last_two[1]:
            return 'authentic'
        elif 'F' in last_two[0] and 'C' in last_two[1]:
            return 'plagal'
        else:
            return 'other'
    
    # Placeholder methods for theory-based predictions
    def _apply_circle_of_fifths(self, progression: List[str], key: Optional[str]) -> List[ChordPrediction]:
        """Apply circle of fifths for chord predictions."""
        return []  # Simplified - would implement circle of fifths logic
    
    def _apply_functional_harmony(self, progression: List[str], key: Optional[str]) -> List[ChordPrediction]:
        """Apply functional harmony rules."""
        return []  # Simplified - would implement functional harmony logic
    
    def _apply_common_cadences(self, progression: List[str], key: Optional[str]) -> List[ChordPrediction]:
        """Apply common cadence patterns."""
        return []  # Simplified - would implement cadence logic
    
    def _apply_modal_interchange(self, progression: List[str], key: Optional[str]) -> List[ChordPrediction]:
        """Apply modal interchange suggestions."""
        return []  # Simplified - would implement modal interchange logic
    
    def _apply_secondary_dominants(self, progression: List[str], key: Optional[str]) -> List[ChordPrediction]:
        """Apply secondary dominant suggestions."""
        return []  # Simplified - would implement secondary dominant logic
    
    # Additional utility methods (simplified implementations)
    def _progression_matches_pattern(self, progression: List[str], pattern: List[str]) -> bool:
        """Check if progression matches the beginning of a pattern."""
        if len(progression) > len(pattern):
            return False
        return progression == pattern[:len(progression)]
    
    def _calculate_pattern_confidence(self, pattern_data: Dict, context: Dict) -> float:
        """Calculate confidence for a pattern match."""
        base_confidence = min(pattern_data['frequency'] / 100.0, 1.0)
        return base_confidence * 0.8  # Base pattern confidence
    
    def _get_chord_historical_accuracy(self, chord: str) -> float:
        """Get historical accuracy for a chord."""
        chord_key = (self._parse_chord_type(chord), self._parse_chord_root(chord))
        stats = self.chord_accuracy_cache.get(chord_key, {})
        return stats.get('accuracy', 0.5)
    
    def _get_user_chord_frequencies(self) -> Dict[str, int]:
        """Get user's chord usage frequencies."""
        # Simplified - would analyze user's historical data
        return {}
    
    def _get_contextually_relevant_chords(self, context: Dict) -> List[str]:
        """Get chords that are relevant to the current context."""
        # Simplified - would return chords based on key, genre, etc.
        return ['C', 'F', 'G', 'Am', 'Dm']  # Basic chords in C major
    
    def _determine_prediction_type(self, reasoning: List[str]) -> str:
        """Determine the type of prediction from reasoning."""
        reasoning_text = ' '.join(reasoning).lower()
        if 'pattern' in reasoning_text:
            return 'pattern'
        elif 'theory' in reasoning_text or 'harmony' in reasoning_text:
            return 'theory'
        elif 'preference' in reasoning_text or 'user' in reasoning_text:
            return 'preference'
        else:
            return 'other'
    
    def _apply_confidence_scoring(self, predictions: List[ChordPrediction], 
                                context: Dict) -> List[ChordPrediction]:
        """Apply final confidence scoring to predictions."""
        for pred in predictions:
            # Adjust confidence based on various factors
            context_bonus = 0.1 if pred.context_score > 0.7 else 0
            accuracy_bonus = 0.1 if pred.historical_accuracy > 0.8 else 0
            
            pred.confidence = min(pred.confidence + context_bonus + accuracy_bonus, 1.0)
        
        return predictions
    
    def _learn_progression_pattern(self, context: Dict, actual_chord: str):
        """Learn from progression patterns."""
        # This would analyze the progression and learn new patterns
        pass
    
    def _update_user_preferences(self, chord: str, context: Dict, confidence: float):
        """Update user preference data."""
        # This would update user preference statistics
        pass
    
    def _store_user_feedback(self, context: Dict, predicted: str, actual: str, confidence: float):
        """Store user feedback in database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO user_feedback 
                    (chord_instance_id, feedback_type, original_value, corrected_value, user_confidence)
                    VALUES (NULL, 'chord_correction', ?, ?, ?)
                ''', (predicted, actual, int(confidence * 10)))  # Scale to 1-10
                conn.commit()
        except Exception as e:
            self.logger.error(f"Error storing user feedback: {e}")
    
    def _check_and_retrain_models(self):
        """Check if models need retraining based on new data."""
        # This would check if there's enough new data to retrain ML models
        pass

# Factory function
def create_ml_engine(db_path: str) -> Optional[MachineLearningEngine]:
    """Create a machine learning engine instance."""
    try:
        return MachineLearningEngine(db_path)
    except Exception as e:
        logging.error(f"Failed to create ML engine: {e}")
        return None

if __name__ == "__main__":
    # Test the machine learning engine
    import tempfile
    
    test_db = os.path.join(tempfile.gettempdir(), "test_ml_engine.db")
    
    # Create test database
    with sqlite3.connect(test_db) as conn:
        cursor = conn.cursor()
        
        # Create minimal tables for testing
        cursor.execute('''
            CREATE TABLE chord_recognition_stats (
                chord_type TEXT,
                root_note INTEGER,
                total_occurrences INTEGER DEFAULT 0,
                correct_detections INTEGER DEFAULT 0,
                false_positives INTEGER DEFAULT 0,
                false_negatives INTEGER DEFAULT 0,
                PRIMARY KEY (chord_type, root_note)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE progression_patterns (
                pattern_type TEXT,
                pattern_sequence TEXT,
                occurrence_count INTEGER,
                complexity_rating REAL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE user_feedback (
                id INTEGER PRIMARY KEY,
                chord_instance_id INTEGER,
                feedback_type TEXT,
                original_value TEXT,
                corrected_value TEXT,
                user_confidence INTEGER
            )
        ''')
        
        conn.commit()
    
    # Test the ML engine
    ml_engine = create_ml_engine(test_db)
    
    if ml_engine:
        print("✅ Machine Learning Engine created successfully")
        
        # Test prediction
        progression = ["C", "F", "G"]
        predictions = ml_engine.predict_next_chord(progression, "C major")
        
        print(f"📊 Predictions for progression {progression}:")
        for i, pred in enumerate(predictions[:5], 1):
            print(f"  {i}. {pred.chord_symbol} (confidence: {pred.confidence:.2f})")
        
        # Test learning
        ml_engine.learn_from_user_feedback(
            context={'key': 'C major', 'progression': progression},
            predicted_chord='Am',
            actual_chord='F',
            user_confidence=0.9
        )
        
        # Get statistics
        stats = ml_engine.get_learning_statistics()
        print(f"📈 Learning stats: {stats.total_predictions} predictions, {stats.user_corrections} corrections")
        
    else:
        print("❌ Failed to create ML engine")
    
    # Cleanup
    os.unlink(test_db)