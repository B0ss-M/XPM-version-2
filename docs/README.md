# Documentation

This folder contains supplementary documentation for using the XPM tools.

- [Drum vs Instrument Keygroups](drum_vs_instrument_keygroups.md) – explains key differences and provides guidelines for generating drum kits and instruments.
- The `--verify-map` feature of `batch_program_editor.py` can assign unreferenced
  samples to new keygroups using note names from filenames. When rebuilding
  programs through the GUI, you will now be prompted before these extras are
  included.

## Developer Reminder

When updating the code, confirm that any function signature changes are reflected in every file that calls that function. Refer to the [Development Notes](../README.md#development-notes) for more details.

- The helper function `_parse_xpm_for_rebuild()` is now the single entry point
  for parsing both modern and legacy `.xpm` files. Use it whenever sample
  mappings or instrument parameters are required for a rebuild.

### Communication Logs

All interactions with the Gemini assistant are archived in the repository:

- [`Codex Communication Log.md`](../Codex%20Communication%20Log.md) provides a
  running summary of notable discussions.
- [`Gemini_Codex_Log.ipynb`](../Gemini_Codex_Log.ipynb) captures the detailed
  notebook history.
