# Expansion Doctor Enhancements

## Overview
Enhanced the Expansion Doctor tool to comprehensively detect and batch fix multiple XPM file issues as requested.

## New Features

### 1. Comprehensive Issue Analysis
- **Keygroup Count Validation**: Detects when `KeygroupNumKeygroups` doesn't match actual instrument count
- **Key Range Validation**: Finds incorrect or missing `LowNote`/`HighNote` values in keygroups
- **Sample Link Validation**: Identifies missing sample files
- **ProgramPads Validation**: Checks `padToInstrument` mapping consistency
- **Version Validation**: Detects missing or invalid version information

### 2. Enhanced GUI
- **Color-coded Results**: Red for files with issues, green for clean files
- **Issue Summary**: Shows abbreviated issue types (KG Count, Key Range, Missing Samples, etc.)
- **Detailed View**: Double-click any file to see full issue details and available fixes
- **Batch Fix Buttons**: Multiple specialized fix buttons for different issue types

### 3. Batch Fix Capabilities

#### Main Fix Functions
- **🔧 Batch Fix All Issues**: Automatically fixes all detected issues across all files
- **🔢 Fix Keygroup Counts**: Corrects `KeygroupNumKeygroups` values to match actual instruments
- **🎹 Fix Key Ranges**: Repairs invalid `LowNote`/`HighNote` ranges using intelligent defaults
- **📋 Fix Pad Mappings**: Rebuilds `ProgramPads` `padToInstrument` mappings
- **🔗 Relink Samples**: Existing functionality for missing sample files

#### Individual File Fixes
- **Single File Fix**: Fix issues in one specific file from detailed view
- **Intelligent Key Ranges**: Uses sample root notes to set appropriate key ranges
- **Automatic Backups**: Creates `.backup` files before making changes

### 4. Issue Detection Logic

#### Keygroup Count Issues
- Detects when declared count ≠ actual instrument count
- Creates missing `KeygroupNumKeygroups` element if absent
- Updates count to match actual instruments found

#### Key Range Issues
- Invalid ranges: `LowNote > HighNote`
- Zero ranges: Both notes set to 0
- Out-of-bounds: Notes < 0 or > 127
- Missing elements: `LowNote` or `HighNote` not present
- **Fix Strategy**: Sets single-note keygroups based on sample root notes

#### Pad Mapping Issues
- `padToInstrument` array length doesn't match keygroup count
- Corrupted JSON in `ProgramPads` data
- **Fix Strategy**: Rebuilds mapping with first N pads → N instruments

## Usage Instructions

### Basic Usage
1. Open Expansion Doctor from main app
2. Tool automatically scans all XPM files in selected folder
3. Red files = issues detected, Green files = clean
4. Click **🔧 Batch Fix All Issues** to fix everything at once

### Detailed Investigation
1. Double-click any file in the list
2. View detailed issue breakdown
3. Click "Fix This File" to fix individual file
4. Issues are categorized with specific descriptions

### Selective Fixing
- Use specific buttons to fix only certain types of issues
- **🔢 Fix Keygroup Counts**: Only keygroup count mismatches
- **🎹 Fix Key Ranges**: Only key range problems
- **📋 Fix Pad Mappings**: Only ProgramPads mapping issues

## Technical Implementation

### Analysis Method
`analyze_xpm_issues(xmp_path)` returns:
```python
{
    "issues": ["Specific issue descriptions"],
    "fixes": ["fix_keygroup_count", "fix_keygroup_ranges", ...],
    "keygroup_count": 5,
    "declared_count": 3, 
    "missing_samples": ["sample1.wav"],
    "version": "3.5.0"
}
```

### Fix Methods
- `fix_single_keygroup_count()`: Updates KeygroupNumKeygroups value
- `fix_single_key_ranges()`: Repairs LowNote/HighNote using root note intelligence  
- `fix_single_pad_mapping()`: Rebuilds padToInstrument mapping
- `fix_single_version()`: Updates version information

### Safety Features
- **Automatic Backups**: `.backup` files created before modifications
- **Error Handling**: Individual file errors don't stop batch processing
- **Detailed Logging**: All fixes and errors logged for debugging
- **Non-destructive**: Original files preserved as backups

## Issue Categories Detected

1. **KG Count**: KeygroupNumKeygroups mismatch
2. **Key Range**: Invalid LowNote/HighNote values
3. **Missing Samples**: Referenced samples not found
4. **Pad Mapping**: ProgramPads mapping inconsistencies  
5. **Version**: Missing/invalid version information
6. **Other**: Parse errors and other issues

## Benefits

- **Batch Processing**: Fix hundreds of XPM files automatically
- **Comprehensive Coverage**: Addresses all major XPM structural issues
- **Intelligent Fixes**: Uses sample metadata for optimal key range assignment
- **Safe Operation**: Automatic backups prevent data loss
- **User-Friendly**: Clear issue descriptions and fix confirmations
- **Selective Control**: Choose which types of issues to fix

This enhanced Expansion Doctor provides a complete solution for maintaining XPM file integrity across large libraries.
