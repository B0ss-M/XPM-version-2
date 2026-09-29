# MPC-Compatible Sample Extraction - Critical Implementation Notes

## Problem Statement
The MPC does not accept SFZ files directly. When converting SFZ (or other sampler formats) to XPM, all referenced audio samples must be:
1. **Extracted and accessible** in the file system
2. **Properly referenced** in the XPM file with correct paths
3. **In WAV format** (MPC requirement)
4. **Located relative** to the XPM file for portability

## Critical Implementation Points

### 1. Sample Extraction Process
When processing SFZ files, the converter now:

```python
# For each sample referenced in the SFZ:
1. Locate the actual audio file (try multiple strategies)
2. Copy sample to extraction directory: "{instrument}_extracted_samples/"
3. Convert to WAV if necessary (MPC requirement)
4. Update sample path to relative reference
5. Verify sample accessibility before creating XPM
```

### 2. Path Resolution Strategies
The system tries multiple approaches to find samples:

```
Strategy 1: Direct accessibility check
Strategy 2: Relative to SFZ file location
Strategy 3: Common subdirectories (samples/, audio/, wav/, etc.)
Strategy 4: Recursive search in SFZ directory
```

### 3. MPC Compatibility Requirements

#### Sample Format
- **Required**: WAV format only
- **Automatic**: Non-WAV samples converted to WAV
- **Validation**: Sample format verified before XPM creation

#### Path References
- **Relative Paths**: All samples referenced relative to XPM location
- **Forward Slashes**: Cross-platform path compatibility
- **Extraction Directory**: Samples organized in "{instrument}_extracted_samples/"

#### File Organization
```
output_folder/
├── Instrument.xpm                    # Main XPM file
└── Instrument_extracted_samples/     # Sample directory
    ├── sample1.wav                   # Extracted/copied samples
    ├── sample2.wav
    └── sample3.wav
```

### 4. Enhanced Processing Flow

#### Before (Problematic):
```
SFZ File → Parse Mappings → Create XPM
                ↓
            Missing samples!
```

#### After (MPC-Compatible):
```
SFZ File → Parse Mappings → Extract/Copy Samples → Verify Accessibility → Create XPM
                ↓               ↓                    ↓                 ↓
           Find samples    Copy to extraction    Convert to WAV    Relative paths
```

## Implementation Details

### Key Methods Enhanced

#### `_process_sampler_mapping()`
- **Purpose**: Process individual sample mappings with extraction
- **Key Feature**: Copies samples to extraction directory for MPC compatibility
- **Result**: All samples accessible and properly referenced

#### `_make_sample_path_relative()`
- **Purpose**: Convert absolute paths to MPC-compatible relative paths
- **Logic**: Handles extraction directory structure
- **Output**: Relative paths with forward slashes

#### `_ensure_mpc_compatibility()`
- **Purpose**: Final validation of all samples before XPM creation
- **Checks**: File existence, WAV format, accessibility
- **Result**: Only MPC-compatible samples included

#### `add_layer_parameters()`
- **Enhancement**: Uses relative paths in SampleFile parameter
- **Critical**: MPC reads SampleFile paths relative to XPM location
- **Result**: Proper sample loading in MPC

### ConvertWithMoss Integration

This logic aligns with ConvertWithMoss standards:
- **Professional Standards**: File_Version 2.1, Application_Version compatibility
- **Sample Organization**: Clean directory structure
- **Path Handling**: Relative references for portability
- **Format Compliance**: WAV-only samples for MPC compatibility

### Error Handling & Logging

#### Sample Location Issues
```
Strategy 1: Check direct path
Strategy 2: Try relative to SFZ
Strategy 3: Search common directories
Strategy 4: Recursive directory search
Final: Log error if sample not found
```

#### Format Conversion Issues
```
Attempt: Convert non-WAV to WAV
Success: Use converted WAV file
Failure: Log warning, exclude sample
```

#### MPC Compatibility Issues
```
Check: Sample exists and accessible
Check: Sample is WAV format
Check: Path is relative and clean
Result: Only compatible samples in XPM
```

## Testing & Validation

### Verification Steps
1. **Sample Extraction**: Verify all referenced samples are copied/extracted
2. **Path Accuracy**: Check XPM contains relative paths to extracted samples
3. **Format Compliance**: Ensure all samples are WAV format
4. **MPC Loading**: Test XPM loads correctly in MPC with all samples

### Success Indicators
```
✅ Sample extraction successful: X samples copied
✅ WAV conversion completed: Y samples converted
✅ MPC compatibility verified: Z samples compatible
✅ XPM creation successful with relative paths
```

### Common Issues & Solutions

#### Issue: "Sample not found"
**Solution**: Enhanced path resolution with multiple strategies

#### Issue: "MPC doesn't load samples"
**Solution**: Ensure samples are in extraction directory with relative paths

#### Issue: "Wrong audio format"
**Solution**: Automatic WAV conversion for MPC compatibility

#### Issue: "Samples not playing"
**Solution**: Verify SampleFile paths in XPM are relative and correct

## Usage Example

### Input: SFZ File
```
// Piano.sfz
<region>
sample=samples/piano_c4.wav
key=60
lokey=59
hikey=61

<region>
sample=samples/piano_d4.wav
key=62
lokey=61
hikey=63
```

### Processing:
1. Parse SFZ → Find sample references
2. Locate: `samples/piano_c4.wav`, `samples/piano_d4.wav`
3. Copy to: `Piano_extracted_samples/piano_c4.wav`, `Piano_extracted_samples/piano_d4.wav`
4. Create XPM with relative paths: `Piano_extracted_samples/piano_c4.wav`

### Output: MPC-Compatible XPM
```xml
<Layer>
    <SampleFile>Piano_extracted_samples/piano_c4.wav</SampleFile>
    <RootNote>60</RootNote>
    <!-- Other parameters -->
</Layer>
```

### Result: MPC Loads Successfully
- ✅ XPM file loads in MPC
- ✅ All samples accessible and playing
- ✅ Proper note mapping preserved
- ✅ Portable (relative paths work on any system)

## Critical Success Factors

1. **Always Extract/Copy Samples**: Never rely on external paths
2. **Use Relative Paths**: Essential for MPC compatibility and portability
3. **Ensure WAV Format**: MPC requirement - convert if necessary
4. **Verify Before Creating XPM**: Only include accessible, compatible samples
5. **Organized Directory Structure**: Clean extraction directory for each instrument

This implementation ensures that SFZ (and other sampler format) conversions produce fully functional, MPC-compatible XPM files with all necessary samples properly extracted and accessible.
