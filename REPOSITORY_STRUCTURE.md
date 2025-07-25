# XPM Converter - Repository Structure

## 🎯 **Essential Files (Git Tracked)**

### **Core Application**
- `Gemini wav_TO_XpmV2.py` - Main XPM converter application with GUI
- `xpm_utils.py` - Core XPM parsing and utility functions
- `requirements.txt` - Python dependencies
- `setup.sh` - Installation script

### **Audio & MIDI Processing**
- `audio_pitch.py` - Audio analysis and pitch detection
- `firmware_profiles.py` - MPC firmware compatibility profiles

### **GUI Components**
- `keyboard_mapper_window.py` - Keyboard mapping interface
- `sample_mapping_checker.py` - Sample mapping validation GUI
- `sample_mapping_editor.py` - Sample mapping editor interface
- `multi_sample_builder.py` - Multi-sample instrument builder
- `enhanced_keyboard_mapper.py` - Advanced keyboard mapping

### **Batch Processing Tools**
- `batch_transpose.py` - Batch transpose XPM files
- `batch_packager.py` - Batch processing utilities
- `batch_program_editor.py` - Batch program editing
- `drumkit_grouping.py` - Intelligent drum kit sample grouping

### **XPM Repair & Analysis**
- `xpm_repair_doctor.py` - XPM file repair and validation
- `xmp_mapping_corrector.py` - Sample mapping correction tools
- `xpm_parameter_editor.py` - XPM parameter editing utilities

### **Documentation**
- `README.md` - Main project documentation
- `docs/` - Additional documentation
  - `README.md` - Documentation index
  - `drum_vs_instrument_keygroups.md` - Technical documentation
- `KEYBOARD_MAPPER_GUIDE.md` - Keyboard mapping guide
- `INTELLIGENT_KEY_RANGES_GUIDE.md` - Key range calculation guide
- `BATCH_TRANSPOSE_USAGE.md` - Batch transpose usage guide
- Various changelog and feature documentation files

### **Configuration & Examples**
- `Advanced keygroup.xpm` - Example advanced XPM file
- `3.5 keygroup_Correct_MPC_OS.txt` - MPC configuration reference
- `Keygroup XPM Advance.txt` - Advanced keygroup documentation
- `Keygroup XPM Legacy.txt` - Legacy keygroup documentation

## 🚫 **Excluded Files (Not Tracked)**

### **Test & Debug Files**
- `test_*.py` - All test scripts
- `analyze_*.py` - Analysis utilities
- `fix_*.py` - Repair utilities
- `apply_*.py` - Application utilities

### **Media Files**
- `*.wav` - Audio sample files
- `*.pdf` - PDF documentation
- `*.epub` - eBook files
- `*.jar` - Java archives

### **Backup & Temporary Files**
- `*.backup*` - Backup files
- `*.bak*` - Backup files
- `*.tmp` - Temporary files
- `*.log` - Log files

### **Generated/Output Files**
- `[Previews]/` - Generated preview folders
- `*.xpm.wav` - Generated preview audio
- `__pycache__/` - Python cache
- `.DS_Store` - macOS system files

### **Development Tools**
- `.venv/` - Virtual environment
- `tools/` - Development utilities
- `components/` - Component testing
- `ConvertWithMoss/` - External tool integration

## 📝 **Repository Guidelines**

### **What to Commit:**
✅ Core Python modules and GUI components  
✅ Documentation and guides  
✅ Configuration files and examples  
✅ Setup and installation scripts  

### **What NOT to Commit:**
❌ Audio samples or media files  
❌ Test and debug scripts  
❌ Backup and temporary files  
❌ Generated output files  
❌ Personal configuration or cache files  

### **File Size Limits:**
- Keep individual files under 1MB when possible
- No audio/video/binary files over 10MB
- Use Git LFS for any necessary large files

## 🔄 **Maintenance**

Run periodically to keep repository clean:
```bash
git status --ignored  # Check what's being ignored
git gc --prune=now    # Clean up repository
git count-objects -v  # Check repository size
```

The `.gitignore` file is configured to automatically exclude development artifacts and maintain a clean, production-ready repository focused on the essential XPM conversion toolkit.
