# Intelligent Sample Extraction System

## Overview

The enhanced multi-format converter now includes an intelligent sample extraction system that efficiently handles samples from compressed/archive formats while avoiding unnecessary duplication of accessible files.

## Key Features

### Smart Accessibility Detection
- **File Accessibility Check**: Automatically detects if samples are accessible before attempting extraction
- **Path Resolution**: Tries multiple strategies to locate missing samples (relative paths, common subdirectories, recursive search)
- **No Unnecessary Duplication**: Only extracts/copies samples when they're not directly accessible

### Supported Extraction Formats

#### Embedded Sample Formats
- **SF2 (SoundFont)**: Extracts embedded samples from SoundFont files
- **Kontakt (NKI/NKM)**: Handles Kontakt instrument samples (NCW decompression planned)
- **REX/RX2**: REX loop extraction (implementation planned)
- **Akai Archives**: Extracts samples from Akai MPC program archives

#### Archive Formats
- **ZIP**: Standard ZIP archive extraction
- **RAR**: RAR archive support (requires rarfile library)
- **7Z**: 7-Zip archive support (requires py7zr library)

### Intelligent Processing Workflow

1. **Sample Analysis**
   - Check if sample path is accessible
   - Determine if sample is embedded in archive/format
   - Identify required extraction method

2. **Extraction Strategy**
   - **Accessible Files**: Use directly without copying
   - **Missing Files**: Try multiple location strategies
   - **Embedded Samples**: Extract only when necessary
   - **Archive Samples**: Extract to organized directories

3. **Path Resolution Strategies**
   - Try relative to source file
   - Check common sample subdirectories (samples/, audio/, wav/, etc.)
   - Recursive search in source directory
   - Archive-specific extraction paths

## Usage Examples

### SFZ Files with Missing Samples
```
Before: SFZ references samples that can't be found
After:  Automatically locates samples in common directories or extracts from archives
```

### SF2 SoundFont Files
```
Before: SF2 file with embedded samples
After:  Extracts only the needed samples to organized directories
```

### Archive-Based Instruments
```
Before: ZIP/RAR containing instrument + samples
After:  Extracts samples intelligently, avoiding duplication
```

## Directory Organization

When extraction is needed, samples are organized in dedicated directories:
```
output_folder/
├── instrument.xpm
└── instrument_extracted_samples/
    ├── sample1.wav
    ├── sample2.wav
    └── sample3.wav
```

## Performance Benefits

1. **Reduced Disk Usage**: No unnecessary file duplication
2. **Faster Processing**: Direct use of accessible files
3. **Organized Output**: Extracted samples in dedicated folders
4. **Smart Caching**: Extracted samples can be reused

## Format-Specific Features

### SFZ Enhancement
- Preserves original sample references when accessible
- Intelligent relative path resolution
- Support for complex SFZ directory structures

### SF2 Enhancement
- Embedded sample extraction with proper WAV formatting
- Preserves sample metadata (sample rate, root note)
- Efficient handling of large SoundFont files

### Kontakt Enhancement
- Handles both XML and binary NKI formats
- NCW sample decompression (planned)
- Intelligent path resolution for external samples

## Error Handling

- **Graceful Degradation**: Falls back to simpler methods if advanced extraction fails
- **Detailed Logging**: Reports extraction status and accessibility checks
- **Cleanup**: Automatic cleanup of temporary files
- **Validation**: Verifies extracted samples before use

## Dependencies

### Required
- Python standard library (zipfile, os, logging)

### Optional (for enhanced features)
- `sf2utils`: Advanced SF2 parsing
- `rarfile`: RAR archive support  
- `py7zr`: 7-Zip archive support
- `librosa`: Advanced audio analysis

## Configuration

The system automatically detects available libraries and adapts functionality accordingly. No manual configuration required.

## Logging

Enable verbose logging to see detailed extraction information:
```python
logging.basicConfig(level=logging.DEBUG)
```

Log messages include:
- Sample accessibility status
- Extraction decisions
- Path resolution attempts
- Success/failure notifications

## Future Enhancements

1. **NCW Decompression**: Full Kontakt NCW sample extraction
2. **REX Implementation**: Complete REX/RX2 loop extraction
3. **Advanced Archives**: Support for more archive formats
4. **Caching System**: Smart sample cache for repeated conversions
5. **Batch Optimization**: Parallel extraction for large collections
