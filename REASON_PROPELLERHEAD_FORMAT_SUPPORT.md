# 🎛️ Reason Propellerhead Format Support Guide

## 🎯 **Enhanced Reason Integration**

The Multi-Format Converter now provides comprehensive support for **Reason Propellerhead** file formats, allowing you to decode and convert various Reason files directly to XPM format for use in MPC hardware/software.

---

## 🎹 **Supported Reason Formats**

### **1. REX/REX2 Loops (.rex, .rx2)**
- **Description**: Tempo-synced audio loops with slice information
- **Detection**: Automatic slice count and tempo extraction
- **Conversion**: Maps slices to drum kit (C2-D#3 range)
- **Details**: Shows slice count and BPM information

**Example Display:**
```
🔊 Breakbeat_130.rex2 - 16 slices @ 130 BPM
```

### **2. NN-XT Sampler Files (.sxt, .nnxt)**
- **Description**: Reason's advanced sampler instrument patches
- **Detection**: XML-based zone parsing with key/velocity mapping
- **Conversion**: Multi-sample instrument with velocity layers
- **Details**: Shows zone count and sample mappings

**Example Display:**
```
🎹 Piano_Patch.sxt - 24 zones with velocity layers
```

### **3. Reason Song Files (.rns)**
- **Description**: Complete Reason project files with embedded instruments
- **Detection**: Binary format parsing for embedded samples/instruments
- **Conversion**: Extracts instrument references to XPM
- **Details**: Shows embedded content analysis

**Example Display:**
```
🎵 My_Song.rns - Reason project with embedded instruments
```

### **4. Reason ReFills (.rfl)**
- **Description**: Compressed archive containing Reason content (patches, samples)
- **Detection**: Archive parsing for NN-XT patches and samples  
- **Conversion**: Extracts and converts embedded content
- **Details**: Shows patch and sample count

**Example Display:**
```
📦 Orchestral_ReFill.rfl - ReFill archive with 50+ patches
```

---

## 🔍 **Advanced Parsing Capabilities**

### **REX File Analysis (`parse_rex_file`)**
```python
# Extracts:
- Slice count and tempo information
- Individual slice mappings to MIDI notes
- Original tempo for tempo-sync preservation
- REX vs REX2 format detection
```

### **NN-XT Patch Analysis (`parse_reason_nnxt_file`)**
```python
# Extracts:
- Sample zone key ranges (LowKey/HighKey)
- Velocity layer mapping (LowVelocity/HighVelocity)
- Root note assignments per zone
- Tuning, volume, and pan settings
- Sample file path resolution
```

### **Reason Song Analysis (`parse_reason_song_file`)**
```python
# Extracts:
- Embedded sample file references
- Binary format instrument detection
- Device and sample path extraction
- Project-level instrument organization
```

### **ReFill Archive Analysis (`parse_reason_refill`)**
```python
# Extracts:
- ZIP-based archive content parsing
- Embedded NN-XT patch extraction
- Sample file catalog and organization
- Nested content structure analysis
```

---

## 🔄 **Conversion Process**

### **1. REX → XPM Drum Kit**
```
Input: Breakbeat.rex2 (16 slices)
Output: Breakbeat.xpm 
├── Slice 1 → C2 (MIDI 36)
├── Slice 2 → C#2 (MIDI 37)
├── ...
└── Slice 16 → D#3 (MIDI 51)
```

### **2. NN-XT → XPM Multi-Sample**
```
Input: Piano.sxt (24 zones)
Output: Piano.xmp
├── Zone 1: C1-B1 (Root: F#1)
├── Zone 2: C2-B2 (Root: F#2)
├── ...
└── Zone 24: C6-C8 (Root: C7)
```

### **3. Reason Song → XPM Collection**
```
Input: Project.rns (embedded instruments)
Output: Multiple XPM files
├── Bass_01.xpm (extracted bass)
├── Lead_Synth.xpm (extracted lead)
└── Drums.xpm (extracted drum kit)
```

### **4. ReFill → XPM Library**
```
Input: Orchestra.rfl (ReFill archive)
Output: Extracted instrument collection
├── Strings.xpm (from embedded NN-XT)
├── Brass.xpm (from embedded patches)
└── Percussion.xpm (from samples)
```

---

## 🎵 **Usage Instructions**

### **1. Load Reason Files**
1. **Open Multi-Format Converter** from Tools menu
2. **Select folder** containing Reason files
3. **Files automatically detected** and categorized:
   - 🔊 REX loops show slice information
   - 🎹 NN-XT patches show zone details
   - 🎵 Song files show project content
   - 📦 ReFills show archive contents

### **2. View Format Details**
- **Format column** shows file type (REX2, SXT, RNS, RFL)
- **Details column** shows content analysis:
  - REX: "16 slices @ 130 BPM"
  - NN-XT: "24 zones with velocity layers"
  - Song: "Reason project file"
  - ReFill: "Archive with 50+ patches"

### **3. Convert to XPM**
1. **Select Reason files** you want to convert
2. **Choose conversion mode:**
   - **Multi-sample** for NN-XT patches
   - **Drum-kit** for REX loops
   - **One-shot** for individual samples
3. **Set target firmware** (3.5.0 recommended)
4. **Click Convert Selected** or **Convert All**

### **4. Results**
- **REX files** → Drum kit XPM with slice mapping
- **NN-XT files** → Multi-sample XPM with zones
- **Song files** → Multiple XPM files (one per instrument)
- **ReFill files** → Collection of XPM instruments

---

## 💡 **Pro Tips**

### **For REX Loops:**
- **Tempo information preserved** - Use with MPC's tempo sync
- **Slice mapping optimized** for drum pad layout
- **Original timing maintained** in converted XPM

### **For NN-XT Patches:**
- **Velocity layers preserved** from original zones
- **Key ranges maintained** for proper playback
- **Sample paths resolved** automatically

### **For Reason Songs:**
- **Multiple instruments extracted** from single file
- **Device routing preserved** where possible
- **Sample references maintained**

### **For ReFills:**
- **Archive content cataloged** before conversion
- **Embedded patches processed** individually
- **Sample library organized** by instrument type

---

## 🚀 **Benefits**

### **1. Complete Reason Integration**
- **No external tools needed** - Built into Multi-Format Converter
- **Native format support** - Direct file reading
- **Intelligent parsing** - Extracts maximum information

### **2. Preservation of Musical Intent**
- **Key ranges maintained** from original mappings
- **Velocity layers preserved** for expressive playing
- **Tempo information retained** for sync applications

### **3. MPC Optimization**
- **Firmware-specific formatting** for target MPC/Force
- **Intelligent key assignment** for playable ranges
- **Modern XPM format** with all latest features

### **4. Workflow Efficiency**
- **Batch conversion** - Process multiple files at once
- **Format detection** - Automatic file type recognition
- **Quality preservation** - Non-destructive conversion

---

## 🔧 **Technical Details**

### **Supported Versions:**
- **REX**: Original REX and REX2 formats
- **NN-XT**: All Reason versions (XML and text-based)
- **Song Files**: Reason 4.0+ binary format
- **ReFills**: Standard and compressed archives

### **Conversion Quality:**
- **Lossless audio** - Original sample data preserved
- **Mapping accuracy** - Exact key/velocity reproduction
- **Parameter preservation** - Tuning, volume, pan maintained

### **Output Format:**
- **Modern XPM 2.1** format for maximum compatibility
- **Firmware optimization** - Tuned for target MPC version
- **Advanced parameters** - Full 3.5.0 feature support

---

**🎉 Your Multi-Format Converter now fully supports Reason Propellerhead formats! Convert REX loops, NN-XT patches, song files, and ReFills directly to playable XPM instruments for your MPC/Force workflow.**
