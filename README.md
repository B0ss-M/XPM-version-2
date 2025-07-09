# XPM-version-2

This repository contains tools for working with Akai MPC Keygroup programs.

Additional documentation can be found in the [docs/](docs/) directory, including a summary of the differences between drum and instrument keygroups.

## Scripts

- `Gemini wav_TO_XpmV2.py` – main Tkinter GUI application for converting WAV files and managing expansions.
- `batch_packager.py` – command-line tool to package each subfolder of a directory into its own expansion ZIP.
- `batch_program_editor.py` – batch editor for `.xpm` program files allowing rename and firmware version changes.
  This functionality is also accessible from the GUI via **Batch Program Editor...** under Advanced Tools.

### New in this update
- Batch Program Fixer rebuild option now includes firmware and format selectors. You
  can rebuild programs into legacy (v2) or advanced (v3) formats while preserving
  all sample layers.

## Recent Changes
- Build Instruments window now lists `.wav` files regardless of case so samples with `.WAV` extensions appear correctly.
- Expansion Doctor displays invalid or corrupt `.xpm` files instead of skipping them.
- Auto Group Folders now previews folder names with sample counts before grouping.
- Multi-sample builder prompts for Drum Program or Instrument Keygroup when building.
