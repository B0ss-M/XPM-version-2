# MIDI Chord Library & Machine Learning Integration

## 🎵 Advanced Music Theory Engine with MIDI Import Capabilities

This system enhances the existing XPM Music Theory Engine with advanced MIDI file reading and machine learning capabilities. The more chords that get added through MIDI imports, the better the algorithm becomes through continuous learning.

## ✨ New Features

### 🎼 MIDI Chord Analysis
- **Intelligent MIDI File Reading**: Automatically detects chord progressions from MIDI files
- **Multi-track Analysis**: Analyzes multiple tracks and selects the best ones for harmonic analysis
- **Advanced Chord Detection**: Uses multiple algorithms (pYIN, harmonic analysis, chroma features)
- **Key Signature Detection**: Automatically detects key signatures using Krumhansl-Schmuckler profiles
- **Voicing Analysis**: Identifies chord voicings (close, open, wide)
- **Real-time Confidence Scoring**: Provides confidence ratings for all detected chords

### 🧠 Machine Learning Engine
- **Adaptive Learning**: System improves accuracy based on user corrections
- **Pattern Recognition**: Learns common chord progression patterns automatically
- **Predictive Analysis**: Suggests next chords based on learned patterns
- **User Preference Learning**: Adapts to individual musical preferences
- **Statistical Analysis**: Tracks improvement metrics over time

### 📊 Enhanced Database
- **MIDI File Tracking**: Stores complete MIDI analysis metadata
- **Chord Instance Details**: Detailed timing, voicing, and confidence data
- **Learning Statistics**: Tracks accuracy improvements and pattern discoveries
- **User Feedback Integration**: Stores corrections for continuous learning

### 🎛️ Integrated GUI
- **Drag & Drop MIDI Import**: Easy file import with visual feedback
- **Real-time Analysis Display**: Live progress tracking during analysis
- **Interactive Correction Interface**: Click to correct detected chords
- **Statistics Dashboard**: View learning progress and accuracy metrics
- **Batch Processing**: Process multiple MIDI files efficiently

## 🛠️ Installation & Setup

### Required Dependencies
```bash
# Core MIDI support
pip install mido

# Enhanced analysis (recommended)
pip install pretty_midi
pip install numpy
pip install scipy

# Machine learning features (optional)
pip install scikit-learn

# Advanced music theory (optional)
pip install music21
```

### Quick Start
```python
# Import the MIDI analyzer
from scripts.midi_chord_analyzer import MIDIChordAnalyzer

# Create analyzer
analyzer = MIDIChordAnalyzer()

# Analyze a MIDI file
analysis = analyzer.analyze_midi_file("path/to/your/song.mid")

if analysis:
    print(f"Key: {analysis.key_signature}")
    print(f"Chords: {' | '.join(analysis.chord_symbols)}")
    print(f"Complexity: {analysis.complexity_score:.2f}")
```

## 📁 File Structure

```
scripts/
├── midi_chord_analyzer.py      # Core MIDI analysis engine
├── database_enhancer.py        # Database enhancement for MIDI data
├── midi_import_gui.py          # MIDI import GUI interface
├── machine_learning_engine.py  # ML engine for continuous improvement
└── progression_rebuilder_gui.py # Enhanced main GUI with MIDI tab
```

## 🎯 Usage Guide

### 1. Accessing MIDI Import
Open the Advanced Progression Builder and look for the "🎵 MIDI Import" tab:
```python
from scripts.progression_rebuilder_gui import ProgressionRebuilderGUI

# Start the GUI
gui = ProgressionRebuilderGUI()
```

### 2. Importing MIDI Files
1. **Select Files**: Choose individual MIDI files or entire folders
2. **Configure Analysis**: Adjust detection thresholds and options
3. **Start Analysis**: Click "🎵 Analyze Selected" to begin processing
4. **Review Results**: View detected chords in the results tab

### 3. Machine Learning Integration
The system automatically learns from:
- **User Corrections**: When you fix incorrectly detected chords
- **Pattern Recognition**: Common progressions in your MIDI files
- **Personal Preferences**: Your musical style and chord choices

### 4. Database Integration
All analyzed MIDI data is automatically stored in your chord library:
- Chord progressions become searchable patterns
- Individual chords are added to your personal library
- Statistics track improvement over time

## 🔧 Advanced Configuration

### MIDI Analyzer Settings
```python
analyzer = MIDIChordAnalyzer()

# Adjust detection sensitivity
analyzer.min_chord_duration = 0.25  # Minimum chord length in seconds
analyzer.chord_detection_threshold = 3  # Minimum notes for chord
analyzer.max_gap_fill = 0.1  # Gap filling for smoother analysis

# Enable/disable features
analyzer.voicing_analysis_enabled = True
analyzer.key_detection_enabled = True
```

### Machine Learning Configuration
```python
from scripts.machine_learning_engine import MachineLearningEngine

ml_engine = MachineLearningEngine(db_path)

# Adjust learning parameters
ml_engine.learning_rate = 0.1
ml_engine.confidence_threshold = 0.7
ml_engine.pattern_min_frequency = 3
```

## 📈 Learning and Improvement

### How the System Learns
1. **Initial Analysis**: System uses built-in music theory rules
2. **Pattern Discovery**: Finds common progressions in your MIDI files
3. **User Feedback**: Learns from your corrections and preferences
4. **Continuous Improvement**: Accuracy increases with more data

### Tracking Progress
View your learning statistics in the Statistics tab:
- **Total MIDI Files Processed**
- **Chord Detection Accuracy**
- **Discovered Patterns**
- **Improvement Trends**

### Best Practices for Learning
1. **Correct Errors**: Always fix incorrectly detected chords
2. **Import Diverse Music**: Various styles improve pattern recognition
3. **Regular Use**: Consistent usage accelerates learning
4. **Quality MIDI Files**: Well-structured MIDI files improve accuracy

## 🎼 Examples

### Basic MIDI Analysis
```python
from scripts.midi_chord_analyzer import MIDIChordAnalyzer

analyzer = MIDIChordAnalyzer()
analysis = analyzer.analyze_midi_file("jazz_standard.mid")

print(f"Detected {len(analysis.chords)} chords")
for i, chord in enumerate(analysis.chords, 1):
    print(f"{i}. {chord.chord_symbol} at {chord.start_time:.1f}s")
```

### Machine Learning Prediction
```python
from scripts.machine_learning_engine import MachineLearningEngine

ml_engine = MachineLearningEngine(db_path)

# Predict next chord in progression
progression = ["C", "Am", "F"]
predictions = ml_engine.predict_next_chord(progression, key="C major")

for pred in predictions[:3]:
    print(f"{pred.chord_symbol}: {pred.confidence:.2f} confidence")
```

### Database Integration
```python
from scripts.database_enhancer import MIDIDataManager

data_manager = MIDIDataManager(db_path)

# Store analysis results
midi_file_id = data_manager.store_midi_analysis(analysis)

# Get learning statistics
stats = data_manager.get_learning_statistics()
print(f"Total chords analyzed: {stats['total_chord_instances']}")
```

## 🚀 Advanced Features

### Batch Processing
Process multiple MIDI files efficiently:
```python
import os
from pathlib import Path

analyzer = MIDIChordAnalyzer()
midi_files = list(Path("midi_folder").glob("*.mid"))

for midi_file in midi_files:
    analysis = analyzer.analyze_midi_file(str(midi_file))
    if analysis:
        print(f"✅ {midi_file.name}: {len(analysis.chords)} chords")
    else:
        print(f"❌ {midi_file.name}: Analysis failed")
```

### Export Results
Export your analyzed data:
```python
import json

# Export as JSON
export_data = {
    'file_path': analysis.file_path,
    'key_signature': analysis.key_signature,
    'chord_progression': analysis.chord_symbols,
    'complexity_score': analysis.complexity_score
}

with open('analysis_results.json', 'w') as f:
    json.dump(export_data, f, indent=2)
```

## 🔍 Troubleshooting

### Common Issues

1. **"mido not available" Error**
   ```bash
   pip install mido
   ```

2. **Poor Detection Accuracy**
   - Ensure MIDI files have clear harmonic content
   - Adjust detection threshold in settings
   - Use well-structured MIDI files

3. **Database Issues**
   - Database is automatically enhanced on first run
   - Check file permissions for database directory
   - Restart application if database seems corrupted

4. **GUI Not Loading MIDI Tab**
   - Verify all dependencies are installed
   - Check for import errors in console output
   - Ensure scripts are in correct directory

### Performance Tips

1. **Large MIDI Files**: For very long files, consider splitting them
2. **Batch Processing**: Use batch mode for multiple files
3. **Memory Usage**: Restart application periodically with large datasets
4. **Analysis Speed**: Reduce track count or simplify MIDI files if too slow

## 🎯 Future Enhancements

The system is designed for continuous improvement and could be enhanced with:

- **Genre Classification**: Automatic style detection
- **Rhythm Analysis**: Beat and tempo pattern recognition
- **Melody Analysis**: Lead instrument detection and analysis
- **Advanced Voicing**: Jazz chord extensions and alterations
- **Real-time MIDI Input**: Live chord detection from MIDI controllers
- **Cloud Learning**: Shared pattern database across users

## 📚 Technical References

### Music Theory Implementation
- **Krumhansl-Schmuckler**: Key detection algorithm
- **Harmonic Series Analysis**: Natural overtone detection
- **Circle of Fifths**: Theoretical chord relationships
- **Functional Harmony**: Traditional chord progressions

### Machine Learning Approaches
- **Naive Bayes**: Chord classification
- **Random Forest**: Pattern prediction
- **Markov Chains**: Progression analysis
- **Bayesian Learning**: Confidence adjustment

### Audio Analysis Methods
- **pYIN Algorithm**: Pitch detection
- **Chroma Features**: Pitch class analysis
- **Constant-Q Transform**: Musical frequency analysis
- **Onset Detection**: Note timing analysis

## 🤝 Contributing

To contribute to this MIDI analysis system:

1. **Report Issues**: Document bugs or accuracy problems
2. **Suggest Features**: Propose new analysis capabilities
3. **Provide MIDI Files**: Share diverse test cases
4. **Improve Algorithms**: Enhance detection accuracy

## 📄 License

This MIDI chord analysis system extends the existing XPM project and follows the same licensing terms.

---

**🎵 The more MIDI files you import and analyze, the smarter the system becomes! Start building your intelligent chord library today.**