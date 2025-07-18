# **XPM Converter Script Documentation**

## **Recent Updates - July 18, 2025**

The Sample Mapping Checker has been significantly enhanced to fix transposition issues and preserve program settings:

1. **Improved Transposition Detection & Correction:**
   - Automatically detects when samples are consistently playing in the wrong octave
   - Calculates the optimal master transpose value to correct octave shifts
   - Preserves all program settings when applying fixes
   - Supports both global transpose adjustment and individual note corrections

2. **Smart Root Note Analysis:**
   - Shows the difference between detected and assigned root notes
   - Offers suggestions for fixing inconsistent mappings
   - Prevents unintended octave shifts when fixing individual notes

3. **Non-Destructive Editing:**
   - Preserves all existing parameters (loop points, fine tuning, etc.)
   - Provides Save As... option to create new files without overwriting
   - Maintains all layer-specific settings during corrections

4. **Automatic Folder Integration:**
   - Automatically loads XPM files from the main window's selected folder
   - Shows a list of all available XPM files for easy switching
   - Added "Refresh Folder" button to check for new files

2. **Interactive Root Note Editing:**
   - Double-click any sample to manually edit its root note
   - Supports both MIDI numbers (0-127) and note names (e.g., C3)
   - Shows immediate feedback with pitch detection and difference display

3. **Advanced Analysis Features:**
   - Real-time display of detected vs. assigned root notes
   - Shows pitch differences for easy identification of mismatched samples
   - Supports both automatic and manual correction methods

4. **Enhanced UI:**
   - Clear folder path display
   - Scrollable XPM file list
   - Comprehensive sample information display
   - Improved error handling and user feedback

*Update by: GitHub Copilot Agent*

## **Core Functions**

### **\_parse\_xpm\_for\_rebuild(xpm\_path)**

This is a globally accessible, robust function for parsing all essential data from any .xpm file, regardless of whether it uses the modern JSON-based format or the legacy XML format. It serves as the primary data extraction engine for the "Batch Program Fixer" and any other tool that needs to rebuild or analyze an existing program.  
**Purpose:**  
To safely read an .xpm file and extract a complete list of its sample mappings and a dictionary of its top-level instrument parameters. This provides a clean, standardized data structure that can be used to rebuild the program from scratch.  
**Parameters:**

* xpm\_path (str): The absolute file path to the .xpm program file to be parsed.

**Process:**

1. **Safety First:** The function is wrapped in a try...except block to handle potential ET.ParseError exceptions if the XML file is corrupted.  
2. **Parameter Extraction:** It finds the first \<Instrument\> block and iterates through its direct children, capturing any existing sound design parameters (e.g., Volume, VolumeAttack, FilterType) into a dictionary.  
3. **Modern Format (JSON) Parsing:** It first attempts to find and parse the ProgramPads-v2.10 (or ProgramPads) tag. If found and valid, it decodes the JSON data and extracts the detailed sample mappings, including root note, key ranges, and velocity ranges.  
4. **Legacy Format (XML) Fallback:** If the modern JSON block is not found or is invalid, the function automatically falls back to parsing the legacy \<Instrument\> and \<Layer\> structure. It iterates through each layer to extract the same set of sample mapping information.  
5. **Path Normalization:** All extracted sample paths are converted to absolute paths to ensure they can be reliably located during the rebuild process.

**Returns:**  
A tuple containing two elements:

1. mappings (list): A list of dictionaries, where each dictionary represents a single sample layer and contains its sample\_path, root\_note, low\_note, high\_note, velocity\_low, and velocity\_high.  
2. instrument\_params (dict): A dictionary of all top-level parameters found in the first instrument block of the XPM file.

This consolidated function ensures that all parts of the application use the exact same logic for reading XPM files, significantly improving the program's stability and maintainability.
