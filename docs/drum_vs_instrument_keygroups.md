# Drum Keygroup vs Instrument Keygroup
> **Note:** This repository is linked with the Gemini assistant. All conversations and code changes are logged in `Codex Communication Log.md` and `Gemini_Codex_Log.ipynb`.

This document explains the fundamental differences between **drum keygroups** and **instrument keygroups** in XPM/Keygroup-based MPC expansions. Understanding these distinctions will help the AI agent generate valid drum kits by setting the correct parameters for each type of keygroup.

---

## 1. Definitions

- **Drum Keygroup**: A collection of independent samples, each assigned to a single MIDI key with a defined velocity layer or range. There is no cross-key interpolation; each sample triggers only on its assigned key (or velocity sub-range).

- **Instrument Keygroup**: A multi-sampled instrument built from a series of individual keygroups. Each source sample lives in its own keygroup with its own note range. Layers are reserved only for velocity switching, **not** for mapping additional notes.

---

## 2. Core Parameter Differences

| Parameter         | Drum Keygroup                                     | Instrument Keygroup                                      |
|-------------------|---------------------------------------------------|----------------------------------------------------------|
| `note_low`        | Fixed value (e.g., 36 for kick)                   | Start of the keygroup's zone (e.g., 48 for C2 sample)    |
| `note_high`       | Same as `note_low`                                | End of the keygroup's zone (e.g., 59 for C2 sample)      |
| `sample_file`     | Single file per key (e.g., `kick.wav`)            | One file per keygroup (e.g., `piano_C2.wav`)             |
| `transpose`       | Usually `0`                                       | May vary per sample to align root note                  |
| `velocity_low`    | Defines bottom of velocity layer                  | Often `1` for full-range instruments                     |
| `velocity_high`   | Defines top of velocity layer                     | Often `127`                                             |
| `loop_mode`       | Typically `one-shot`                              | `forward_loop` or `pingpong_loop` for sustained notes    |
| `loop_start`      | N/A                                               | Frame index for loop start                               |
| `loop_end`        | N/A                                               | Frame index for loop end                                 |
| `group_type`      | `drum`                                            | `instrument`                                            |


---

## 3. Structural Examples

### 3.1 Drum Keygroup Example

```xml
<KeyGroup>
  <Name>Kick</Name>
  <NoteLow>36</NoteLow>
  <NoteHigh>36</NoteHigh>
  <VelLow>1</VelLow>
  <VelHigh>127</VelHigh>
  <SampleFile>Kick_01.wav</SampleFile>
  <Transpose>0</Transpose>
  <LoopMode>one_shot</LoopMode>
</KeyGroup>
```

- **Single Key**: `NoteLow` = `NoteHigh` = 36 (C1).
- **Velocity**: Entire range (1–127) triggers the same sample.
- **One-shot**: The sample plays fully without looping.

### 3.2 Instrument Keygroup Example

Each sample occupies its own keygroup. The `Number` tag should match the keygroup's order in the program.

```xml
<KeyGroup>
  <Number>1</Number>
  <Name>Piano_C2</Name>
  <NoteLow>36</NoteLow>
  <NoteHigh>47</NoteHigh>
  <VelLow>1</VelLow>
  <VelHigh>127</VelHigh>
  <LoopMode>forward_loop</LoopMode>
  <Layers>
    <Layer number="1">
      <SampleFile>Piano_C2.wav</SampleFile>
      <RootNote>36</RootNote>
    </Layer>
  </Layers>
</KeyGroup>

<KeyGroup>
  <Number>2</Number>
  <Name>Piano_C3</Name>
  <NoteLow>48</NoteLow>
  <NoteHigh>59</NoteHigh>
  <VelLow>1</VelLow>
  <VelHigh>127</VelHigh>
  <LoopMode>forward_loop</LoopMode>
  <Layers>
    <Layer number="1">
      <SampleFile>Piano_C3.wav</SampleFile>
      <RootNote>48</RootNote>
    </Layer>
  </Layers>
</KeyGroup>
```

- **Zones**: Each keygroup defines its own `NoteLow`/`NoteHigh` range.
- **Looping**: Optional sustain loops per keygroup.
- **Layers**: Additional layers are used only for velocity splits.

---

## 4. AI Agent Guidelines for Drum Kit Generation

1. **Assign One Sample per Key**:
   - For each drum sound (kick, snare, hat, etc.), create a KeyGroup where `note_low` == `note_high` at the MIDI note you choose.
   - Set `group_type = "drum"`.

2. **Define Velocity Layers (Optional)**:
   - If using multiple velocity layers, split samples by dynamics:
     - e.g., `VelLow=1, VelHigh=63` for soft, `VelLow=64, VelHigh=127` for loud.

3. **No Looping**:
   - Always use `LoopMode = "one_shot"`.
   - Do not include `LoopStart` or `LoopEnd` parameters.

4. **Naming and Paths**:
   - Use clear filenames: `<KitName>_<Instrument>_v<Layer>.wav`.
   - Match `SampleFile` exactly (case-sensitive).

5. **Parameter Templates**:
   ```xml
   <KeyGroup>
     <Name>{KitName}_{DrumName}</Name>
     <NoteLow>{MIDI_Note}</NoteLow>
     <NoteHigh>{MIDI_Note}</NoteHigh>
     <VelLow>{VelLow}</VelLow>
     <VelHigh>{VelHigh}</VelHigh>
     <SampleFile>{SampleFilename}</SampleFile>
     <Transpose>0</Transpose>
     <LoopMode>one_shot</LoopMode>
   </KeyGroup>
   ```

---

## 5. Quick Reference Table

| Field          | Drum Kit Value             | Instrument Kit Value        |
|----------------|----------------------------|-----------------------------|
| `NoteLow`      | Single MIDI note (e.g.,36) | Zone start for that sample  |
| `NoteHigh`     | Same as `NoteLow`          | Zone end for that sample    |
| `VelLow`       | 1 (or layer-specific)      | 1                           |
| `VelHigh`      | 127 (or layer-specific)    | 127                         |
| `LoopMode`     | `one_shot`                 | `forward_loop` or `none`    |
| `LoopStart/End`| N/A                        | Required for sustain loops  |
| `Samples`      | One per key (or layer)     | One per keygroup; consecutive keygroups cover the range |

---

## 6. Automatic Mapping Repairs

The `batch_program_editor.py` tool offers a `--verify-map` mode. When enabled it searches each program's folder for audio files that are not referenced in the XPM. Any extras are assigned to new keygroups automatically. The target note is guessed from the file name (e.g., `Piano_C3.wav` → MIDI 60) or extracted from WAV metadata if present.
If no metadata is found, the tools now analyze the sample itself to detect its fundamental pitch automatically.

---

*Use this guide to ensure the AI agent outputs valid, standards-compliant drum keygroups for MPC expansions.*

