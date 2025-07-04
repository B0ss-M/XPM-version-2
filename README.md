# XPM-version-2

This repository contains the **Wav\_To\_Xpm\_Converter** utility. The tool
creates and edits Akai MPC keygroup programs (`.xpm` files) from collections of
WAV samples. Key features include:

* A Tkinter GUI for converting samples and packaging expansions.
* A **Smart Split** mode that scans `.xpm` files first, categorizes them using
  instrument tags found anywhere in the XML, and moves both the program and its
  referenced samples into a matching folder.
* A **Merge Subfolders** tool that collects WAV files from subfolders up to two
  levels deep and safely moves them into the root directory.

See `AGENT.md` for detailed collaboration guidelines.
