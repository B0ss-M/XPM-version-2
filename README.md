# XPM-version-2

This repository contains tools for working with Akai MPC Keygroup programs.

Additional documentation can be found in the [docs/](docs/) directory, including a summary of the differences between drum and instrument keygroups.

## Scripts

- `Gemini wav_TO_XpmV2.py` – main Tkinter GUI application for converting WAV files and managing expansions. This filename supersedes the earlier `wav_to_xpm_converter_v22.py` and is the canonical script name used throughout this repository.
- `batch_packager.py` – command-line tool to package each subfolder of a directory into its own expansion ZIP.
- `batch_program_editor.py` – batch editor for `.xpm` program files allowing rename, firmware version, and format changes.
  This functionality is also accessible from the GUI via **Batch Program Editor...** under Advanced Tools.
  The editor includes drop-downs for **Application Version** and engine **Format**, a
  checkbox for fixing sample note mappings, and a **Browse...** button for selecting a Mod Matrix JSON file.
  The matrix file should be a `.json` list where each entry contains a `Num` value and the desired
  parameters for that modulation slot.
  parameters for that modulation slot. The command-line version exposes the same options via
  `--format`, `--mod-matrix`, and the new `--fix-notes` flag for repairing sample note assignments.
- `batch_program_editor.py` – batch editor for `.xpm` program files allowing rename, firmware, and format changes.
  This functionality is also accessible from the GUI via **Batch Program Editor...** under Advanced Tools.
  The editor now provides drop-down selectors for **Application Version** and **Format**
  (legacy or advanced) plus a **Browse...** button for selecting a Mod Matrix JSON file.
  The matrix file should be a `.json` list where each entry contains a `Num` value
  and the desired parameters for that modulation slot.
  When using the command-line tool you can pass `--format legacy` or `--format advanced`
  to produce programs in either layout.


### New in this update
- Batch Program Fixer rebuild option now includes firmware and format selectors. You
  can rebuild programs into legacy (v2) or advanced (v3) formats while preserving
  all sample layers.

## Recent Changes
- Build Instruments window now lists `.wav` files regardless of case so samples with `.WAV` extensions appear correctly.
- Expansion Doctor displays invalid or corrupt `.xpm` files instead of skipping them.
- Auto Group Folders now previews folder names with sample counts before grouping.
- Multi-sample builder prompts for Drum Program or Instrument Keygroup when building.
- Expansion Builder resizes uploaded artwork to 600x600 if Pillow is installed.
- Expansion Doctor can rewrite programs to any firmware version and legacy or advanced format.

## Installation

1. Install the requirements:
   ```bash
   pip install -r requirements.txt
   ```
2. Launch the GUI:
   ```bash
    python "Gemini wav_TO_XpmV2.py"
    ```
   The filename contains a space after `Gemini`, so quoting the command is required.
