# BATCH TRANSPOSE & MULTI-CONVERTER ENHANCEMENTS

## Issues Fixed

### Issue 1: Batch Transpose Sample Mapping Fix
**Problem:** The batch transpose tool only modified the `KeygroupMasterTranspose` value but didn't update individual sample mappings (`LowNote`, `HighNote`, `RootNote`) within each instrument/layer.

**Solution:** Enhanced `batch_transpose.py` with:
- New `--fix-mappings` option to update all sample mappings
- `update_sample_mappings()` function that traverses the XPM structure
- Updates all `LowNote`, `HighNote`, and `RootNote` values by the transpose amount
- Preserves MIDI note boundaries (0-127)
- Skips invalid RootNote values (0)
- Detailed logging of all changes

### Issue 2: Multi-Converter Whole Instrument Processing
**Problem:** The multi-converter was treating individual audio files instead of grouping related samples to create whole instruments.

**Solution:** Enhanced `MultiFormatConverterWindow` with:
- New "Group by instrument" checkbox option (enabled by default)
- Intelligent file grouping using `_group_audio_files()` method
- Pattern matching to extract instrument names from filenames
- Removes note indicators (C4, D#3), velocity indicators (v1, vel1), round-robin indicators (rr1)
- Creates single XPM files from all related samples
- Maintains backward compatibility with individual file processing

## Usage

### Enhanced Batch Transpose
```bash
# Traditional usage (only master transpose)
python batch_transpose.py -f /path/to/folder -t -24

# NEW: Fix all sample mappings too
python batch_transpose.py -f /path/to/folder -t -24 --fix-mappings

# Dry run to see what would be changed
python batch_transpose.py -f /path/to/folder -t -24 --fix-mappings --dry-run
```

### Enhanced Multi-Converter
1. Open "Multi-Format to XPM Converter" from main app
2. **New Option:** "Group by instrument" checkbox (default: ON)
   - **ON:** Creates whole instruments from related samples (Piano_C4.wav, Piano_D4.wav → Piano.xpm)
   - **OFF:** Creates individual XPM for each file (old behavior)
3. Select files and convert

## Technical Details

### Batch Transpose Enhancements
- **File:** `batch_transpose.py`
- **New Function:** `update_sample_mappings(tree, transpose_semitones)`
- **Elements Updated:**
  - `//Instrument/LowNote`
  - `//Instrument/HighNote` 
  - `//Instrument/Layers/Layer/RootNote`
- **Boundary Checking:** Ensures MIDI values stay within 0-127 range
- **Smart Skipping:** Ignores RootNote values of 0 (considered invalid)

### Multi-Converter Enhancements
- **File:** `Gemini wav_TO_XpmV2.py`
- **Enhanced Function:** `_perform_conversion()`
- **New Logic:**
  1. Separates audio files from sampler files
  2. If grouping enabled: Groups audio files by instrument name
  3. Creates single XPM from all samples in each group
  4. Updates all related files with group status
- **Pattern Recognition:** Advanced regex patterns to extract instrument names

## Benefits

### For Batch Transpose
- **Complete Transposition:** Both master transpose AND sample mappings
- **Eliminates Manual Work:** No need to use Expansion Doctor after transpose
- **Preserves Playability:** Samples play at correct octaves without global transpose adjustment
- **Safe Operation:** Respects MIDI boundaries and skips invalid values

### For Multi-Converter  
- **True Instrument Creation:** Multi-sample instruments instead of single-sample XPMs
- **Intelligent Grouping:** Automatically detects related samples by name patterns
- **Better Organization:** Creates fewer, more meaningful XPM files
- **Maintains Flexibility:** Optional - can still process files individually

## Examples

### Batch Transpose with Sample Mapping Fix
**Before:**
- `KeygroupMasterTranspose`: 0.0
- `RootNote`: 60 (C4)
- `LowNote`: 36, `HighNote`: 84

**Command:** `python batch_transpose.py -f /folder -t -12 --fix-mappings`

**After:**
- `KeygroupMasterTranspose`: -12.0
- `RootNote`: 48 (C3) 
- `LowNote`: 24, `HighNote`: 72

### Multi-Converter Grouping
**Input Files:**
- Piano_C4_v1.wav
- Piano_C4_v2.wav  
- Piano_D4_v1.wav
- Piano_D4_v2.wav

**Output (Group by instrument ON):**
- Piano.xpm (contains all 4 samples as velocity layers across C4-D4 range)

**Output (Group by instrument OFF):**
- Piano_C4_v1.xpm
- Piano_C4_v2.xpm
- Piano_D4_v1.xpm  
- Piano_D4_v2.xpm

## Compatibility

- **Backward Compatible:** All existing functionality preserved
- **Optional Features:** New features are opt-in via checkboxes/flags
- **Safe Defaults:** Grouping enabled by default for better user experience
- **Comprehensive Logging:** Detailed output for troubleshooting

These enhancements address the core user requests while maintaining the stability and compatibility of the existing tools.
