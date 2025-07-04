# Drum vs Instrument Keygroups

This project generates `.xpm` keygroup programs for Akai MPC hardware and software. Keygroups fall into two main categories:

## Drum Keygroups
- Typically represent a drum kit where each sample is mapped to its own MIDI note/pad.
- Root note equals the pad note and the usable range is restricted to that one note.
- Often used for collections of single hits (kicks, snares, etc.) with minimal velocity layering.

## Instrument Keygroups
- Create a playable instrument across the keyboard.
- Multiple samples are mapped to different root notes to cover a range of pitches.
- Velocity layers can be used to trigger different samples at various dynamic levels.

The `InstrumentBuilder` in the main application understands these modes via the `mode` argument:

- `drum-kit` – builds a drum style keygroup with each sample assigned to consecutive MIDI notes.
- `one-shot` – maps all provided samples to a single note for use as triggered FX or phrases.
- `multi-sample` – spreads samples across the keyboard based on their detected root notes.

Refer to `Gemini wav_TO_XpmV2.py` for the full implementation.

## Tools
- **Multi-Sample Instrument Builder** now searches for `.wav` files case-insensitively so samples with `.WAV` extensions appear.
- **Expansion Doctor** lists invalid or corrupt `.xpm` files instead of silently skipping them during scans.
