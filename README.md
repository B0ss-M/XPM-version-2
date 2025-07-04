# XPM-version-2

This repository contains tools for working with Akai MPC Keygroup programs.

## Scripts

- `Gemini wav_TO_XpmV2.py` – main Tkinter GUI application for converting WAV files and managing expansions.
- `batch_packager.py` – command-line tool to package each subfolder of a directory into its own expansion archive (`.zip` or `.zpn`). It checks for `Expansion.xml`, a `Samples` folder with audio, and at least one `.xpm` program.
- `batch_program_editor.py` – batch editor for `.xpm` program files allowing rename and firmware version changes.
- `pitch_detector.py` – detect the fundamental note of audio samples using `librosa` and output the results to the console or a CSV file.
