# XPM-version-2

This repository contains tools for working with Akai MPC Keygroup programs.

Additional documentation can be found in the [docs/](docs/) directory, including a summary of the differences between drum and instrument keygroups. A technical overview of shared helper functions is available in [docs_README.md](docs_README.md).

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
  `--format`, `--mod-matrix`, and the new `--fix-notes` flag for repairing sample note assignments. The `--verify-map` option can also rebuild programs when extra WAV files are found, assigning them to new keygroups based on their filenames.
- `fix_xpm_notes.py` – standalone utility to repair root note mappings and automatically adjust the global transpose when a consistent offset is detected. Use `--update-wav` to also write the detected notes back into each WAV file.


### New in this update
- Batch Program Fixer rebuild option now includes firmware and format selectors. You
  can rebuild programs into legacy (v2) or advanced (v3) formats while preserving
  all sample layers.

## Recent Changes
- Build Instruments window now lists `.wav` files regardless of case so samples with `.WAV` extensions appear correctly.
- Expansion Doctor displays invalid or corrupt `.xpm` files instead of skipping them.
- Auto Group Folders now previews folder names with sample counts before grouping.
- Multi-sample builder prompts for Drum Program or Instrument Keygroup when building.
- Multi-sample builder can group selected files by prefix and rename groups.
- Root notes can be detected from WAVs and appended to filenames automatically.
- Expansion Builder resizes uploaded artwork to 600x600 if Pillow is installed.
- Expansion Doctor can rewrite programs to any firmware version and legacy or advanced format.
- Unknown samples without note metadata are now analyzed to detect their pitch automatically.
- Filenames are scanned for multiple note patterns, using the last valid match
  to determine the MIDI value (e.g. `Piano_A3-64.wav`, `VNLGF41C2.wav`).
- `fix_xpm_notes.py` uses the same detection logic to correct older programs, update the master transpose, and can embed root notes into WAV files with `--update-wav`.

## Installation

1. Install the requirements:
   ```bash
   pip install -r requirements.txt
   ```
   The package list includes **soundfile** and **numpy** which are required for automatic pitch detection.
2. Launch the GUI:
   ```bash
   python "Gemini wav_TO_XpmV2.py"
   ```
   The filename contains a space after `Gemini`, so quoting the command is required.

   **macOS Python Version Warning:** Recent builds of Python 3.13 on macOS ship
   with an unstable Tkinter framework that can crash when running this
   application. If you encounter a sudden "NSInvalidArgumentException" at
   startup, install Python 3.12 or earlier and run the script again.

## Development Notes

When modifying or extending the Python scripts, keep function signatures synchronized across all files. If you add or remove parameters in one module, search the repository for that function name and update every call site accordingly. Mismatched argument counts can cause runtime errors that are difficult to debug.

## Gemini <> Codex Communication

This repository is connected to the Gemini AI service. Responses sent through
Gemini are recorded and stored in two files:

- **`Codex Communication Log.md`** – a human-readable summary of notable
  exchanges and code changes.
- **`Gemini_Codex_Log.ipynb`** – a Jupyter notebook capturing detailed
  interaction history.

Because the GitHub account is linked to Gemini, any future messages or code
updates made through the assistant will automatically appear in these logs.
