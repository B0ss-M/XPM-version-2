# Batch Transpose Tool - Usage Guide

This tool helps you batch transpose hundreds of XPM files when they're playing at the wrong octave.

## 🎵 **INTEGRATED IN MAIN APP** 🎵

**The batch transpose feature is now fully integrated into your main application!**

### Quick Access:
1. Launch your main app: `python "Gemini wav_TO_XpmV2.py"`
2. Look for the **"Batch Transpose"** button in the **"Utilities & Batch Tools"** section
3. Select your folder, set transpose amount, and process hundreds of files with a few clicks!

---

## Your Problem
- You press C2 on the MPC and it plays C4 (24 semitones too high)
- You need to manually go into settings and globally transpose by -24 for each instrument

## Solution - Two Ways to Use:

### 1. 🖥️ **GUI Method (Recommended)**
Use the integrated graphical interface in your main application:

1. **Launch Main App**: `python "Gemini wav_TO_XpmV2.py"`
2. **Find Batch Tools**: Look for "Utilities & Batch Tools" section
3. **Click "Batch Transpose"**: Opens the dedicated transpose window
4. **Select Folder**: Browse to your XPM files folder
5. **Set Amount**: Use the "-24 (Down 2 oct)" quick button or enter -24 manually
6. **Preview**: Click "Preview Changes" to see what will happen
7. **Apply**: Click "Apply Transpose" to fix all files at once

#### 🎯 **GUI Features:**
- **Real-time preview** of current vs new transpose values
- **Quick preset buttons** (-24, -12, +12 semitones)
- **File scanning** with recursive subfolder search
- **Automatic backups** (.backup extension)
- **Progress tracking** during processing
- **Error reporting** for any failed files
- **Absolute or relative** transpose modes

### 2. ⌨️ **Command Line Method**
Use the standalone script for automation/scripting:

```bash
# Fix instruments playing 2 octaves too high:
python batch_transpose.py -f /path/to/your/xpm/folder -t -24

# First, do a dry run to see what would change:
python batch_transpose.py -f /path/to/your/xpm/folder -t -24 --dry-run
```

### Process only current folder (no subfolders):
```bash
python batch_transpose.py -f /path/to/your/xpm/folder -t -24 --no-recursive
```

### Skip creating backups (if you already have backups):
```bash
python batch_transpose.py -f /path/to/your/xpm/folder -t -24 --no-backup
```

### Add transpose to existing values instead of setting absolute:
```bash
python batch_transpose.py -f /path/to/your/xpm/folder -t -24 --relative
```

## Examples

### Most common use case (your problem):
```bash
# First, test what would happen:
python batch_transpose.py -f /Users/marlsz/Documents/MyXPMFiles -t -24 --dry-run

# If it looks good, run for real:
python batch_transpose.py -f /Users/marlsz/Documents/MyXPMFiles -t -24
```

### Other transpose amounts:
```bash
# Down 1 octave
python batch_transpose.py -f /path/to/folder -t -12

# Up 1 octave  
python batch_transpose.py -f /path/to/folder -t 12

# Down 1 semitone
python batch_transpose.py -f /path/to/folder -t -1
```

## What it does
1. Finds all .xpm files in the specified folder (and subfolders by default)
2. Creates backup files (.backup extension) before making changes
3. Modifies the `KeygroupMasterTranspose` parameter in each XPM file
4. This is equivalent to manually setting the global transpose in MPC settings

## Safety Features
- **Automatic backups**: Creates .backup files before modifying originals
- **Dry run mode**: See what would change without making modifications  
- **Verbose logging**: Shows exactly what's being changed
- **Error handling**: Continues processing if individual files fail

## Backup Recovery
If something goes wrong, you can restore from backups:
```bash
# Restore a single file
mv myinstrument.xpm.backup myinstrument.xpm

# Restore all files in a folder
for f in *.backup; do mv "$f" "${f%.backup}"; done
```

## Notes
- The tool modifies the XPM files directly - your WAV samples are not affected
- This sets the global transpose for the entire instrument
- Positive values transpose up, negative values transpose down
- The tool works with both legacy and modern XPM format versions
