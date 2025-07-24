# Intelligent Key Range Assignment System

## Overview

The XPM Keygroup Fix system has been enhanced with intelligent key range assignment that solves the critical issue: **"C5 plays but C6, C7, C8 don't"** by analyzing sample pitches and assigning musically logical ranges instead of arbitrary 0-127 mappings.

## The Problem

Previously, the Expansion Doctor and key range fixes would:
- Set ALL keygroups to 0-127 range (full keyboard)
- Cause wrong samples to play when high notes are pressed
- Ignore the actual pitch content of samples
- Create unmusical mappings where low samples play on high keys

## The Solution

### Intelligent Range Calculation

The new system:

1. **Analyzes Root Notes**: Extracts actual MIDI root notes from each keygroup's Layer/RootNote
2. **Sorts by Pitch**: Orders keygroups from lowest to highest pitch
3. **Calculates Midpoints**: Assigns range boundaries at the midpoint between adjacent samples
4. **Extends High Range**: Ensures the highest sample (e.g., C5) extends to full keyboard (127) for C6, C7, C8 access

### Example Results

**Before Fix:**
```
KG1: Root=60 (C4), Range=0-127    ❌ Wrong - C4 sample plays across entire keyboard
KG2: Root=72 (C5), Range=0-127    ❌ Wrong - C5 sample also plays across entire keyboard
```

**After Intelligent Fix:**
```
KG1: Root=60 (C4), Range=0-66     ✅ Correct - C4 sample plays C0-F#4
KG2: Root=72 (C5), Range=67-127   ✅ Correct - C5 sample plays G4-G9 (includes C6,C7,C8)
```

## Key Features

### 1. Musical Logic
- Range boundaries calculated at pitch midpoints
- Preserves original note mappings when they make sense
- Fixes only problematic ranges (LowNote > HighNote, 0-0, etc.)

### 2. Extended High Range
- Highest pitched sample ALWAYS extends to MIDI 127 (G9)
- Ensures C5 samples can trigger C6, C7, C8 notes
- Solves the specific "C5 plays but not C6 or C7 or C8" issue

### 3. Fallback Handling
- If root notes can't be extracted, uses sequential division
- Handles edge cases gracefully
- Maintains backwards compatibility

## Implementation Details

### Core Functions

#### `_calculate_extended_key_ranges(mappings)`
```python
def _calculate_extended_key_ranges(self, mappings):
    """Calculate intelligent key ranges with extended high range."""
    sorted_maps = sorted(mappings, key=lambda m: m.get("root_note", 60))
    
    for i, current in enumerate(sorted_maps):
        if i == 0:
            current["low_note"] = 0  # First sample starts from C0
        else:
            prev = sorted_maps[i - 1]
            midpoint = (prev["root_note"] + current["root_note"]) // 2
            current["low_note"] = midpoint + 1
            
        if i == len(sorted_maps) - 1:
            current["high_note"] = 127  # CRITICAL: Last sample extends to full range
        else:
            nxt = sorted_maps[i + 1]
            midpoint = (current["root_note"] + nxt["root_note"]) // 2
            current["high_note"] = midpoint
```

#### `fix_single_key_ranges(xmp_path)`
- Enhanced to use intelligent range calculation
- Preserves good ranges, fixes problematic ones
- Applies the extended algorithm automatically

#### `fix_structural_bloat(xmp_path)`
- Now includes intelligent range assignment after removing empty instruments
- Ensures MPC Live 2 compatibility with proper range mapping
- Logs detailed range information for debugging

## Test Results

### Scenario 1: Typical 5-Sample Chromatic Instrument
```
C2 (MIDI 36): Range  0- 42   ✅ C0-F#2
C3 (MIDI 48): Range 43- 54   ✅ G2-F#3
C4 (MIDI 60): Range 55- 66   ✅ G3-F#4
C5 (MIDI 72): Range 67- 78   ✅ G4-F#5
C6 (MIDI 84): Range 79-127   ✅ G5-G9 (includes C6,C7,C8)
```

### Scenario 2: Sparse 2-Sample Instrument
```
C2 (MIDI 36): Range  0- 60   ✅ C0-C4
C6 (MIDI 84): Range 61-127   ✅ C#4-G9 (includes C5,C6,C7,C8)
```

## Benefits

### For Users
- **Full Keyboard Access**: C5 samples now trigger C6, C7, C8 properly
- **Musical Accuracy**: Samples play in their intended ranges
- **Consistent Behavior**: Works across all XPM files regardless of source

### For MPC Live 2
- **Performance**: Optimized file structure with intelligent ranges
- **Memory Efficiency**: No more bloated 128-instrument files
- **Hardware Compatibility**: Ranges designed for MPC hardware expectations

### For Developers
- **Maintainable**: Clear logic based on musical principles
- **Extensible**: Easy to modify range calculation algorithms
- **Debuggable**: Comprehensive logging of range assignments

## Usage

### Expansion Doctor Window
1. Open Expansion Doctor
2. Run "Batch Fix All Issues" - includes intelligent range assignment
3. Or use "Fix Key Ranges" for range-specific fixes

### Programmatic Usage
```python
doctor = ExpansionDoctorWindow(master)
doctor.fix_single_key_ranges("/path/to/file.xpm")
```

## Migration Notes

### Backwards Compatibility
- Existing XPM files are automatically backed up (.backup extension)
- Original behavior preserved for valid ranges
- Only problematic ranges are modified

### Performance Impact
- Minimal - range calculation is O(n log n) where n = number of keygroups
- Typical instruments (2-20 keygroups) process in milliseconds
- Structural bloat removal provides significant performance gains

## Troubleshooting

### Common Issues

**Issue**: Ranges still seem wrong after fix
**Solution**: Check if RootNote values are correct in the Layer elements

**Issue**: High notes still don't play
**Solution**: Verify the highest sample's high_note is set to 127

**Issue**: Multiple samples playing simultaneously
**Solution**: Ensure ranges don't overlap (should be handled automatically)

### Debug Information
Enable logging to see detailed range assignments:
```python
logging.basicConfig(level=logging.INFO)
```

Look for log messages like:
```
🎹 EXTENDED: Highest sample (root=72) extended to full range: 67-127 for C6,C7,C8 access
🎹 Fixed range for sample_C5.wav: Root=72, Range=67-127
```

## Conclusion

The intelligent key range assignment system solves the fundamental issue of proper keyboard mapping in XPM files. By analyzing actual sample pitches and applying musical logic, users now get full keyboard access with samples playing in their intended ranges.

**Key Achievement**: C5 samples (and any highest sample) now properly trigger C6, C7, C8 and beyond, giving complete keyboard playability as requested.
