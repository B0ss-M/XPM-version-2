# Drum Keygroup vs Instrument Keygroup
> **Note:** This repository is linked with the Gemini assistant. All conversations and code changes are logged in `Codex Communication Log.md` and `Gemini_Codex_Log.ipynb`.

This document explains the fundamental differences between **drum keygroups** and **instrument keygroups** in XPM/Keygroup-based MPC expansions. Understanding these distinctions will help the AI agent generate valid drum kits by setting the correct parameters for each type of keygroup.

---

## 1. Definitions

- **Drum Keygroup**: A collection of independent samples, each assigned to a single MIDI key with a defined velocity layer or range. There is no cross-key interpolation; each sample triggers only on its assigned key (or velocity sub-range).

- **Instrument Keygroup**: A set of samples spread across a contiguous key range (e.g., piano: C2–C6). Samples are mapped so that neighboring notes interpolate or crossfade, simulating continuous pitch and timbre changes.

---

## 2. Core Parameter Differences

| Parameter         | Drum Keygroup                                     | Instrument Keygroup                                      |
|-------------------|---------------------------------------------------|----------------------------------------------------------|
| `note_low`        | Fixed value (e.g., 36 for kick)                   | Bottom of key range (e.g., 48 for C3)                    |
| `note_high`       | Same as `note_low`                                | Top of key range (e.g., 72 for C6)                       |
| `sample_file`     | Single file per key (e.g., `kick.wav`)            | Multiple files across range (e.g., `piano_C3.wav`, etc.)|
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

```xml
<KeyGroup>
  <Name>Piano C3–C6</Name>
  <NoteLow>48</NoteLow>
  <NoteHigh>72</NoteHigh>
  <VelLow>1</VelLow>
  <VelHigh>127</VelHigh>
  <LoopMode>forward_loop</LoopMode>
  <LoopStart>44100</LoopStart>
  <LoopEnd>176400</LoopEnd>
  <SampleMappings>
    <Sample>
      <File>Piano_C3.wav</File>
      <RootKey>48</RootKey>
    </Sample>
    <Sample>
      <File>Piano_C4.wav</File>
      <RootKey>60</RootKey>
    </Sample>
    <!-- more mappings -->
  </SampleMappings>
</KeyGroup>
```

- **Range**: C3 (48) to C6 (72).
- **Looping**: Sustain loop defined by frame indices.
- **Multiple Samples**: Crossfaded by root-key distances.

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
| `NoteLow`      | Single MIDI note (e.g.,36) | Start of range (e.g.,48)    |
| `NoteHigh`     | Same as `NoteLow`          | End of range (e.g.,72)      |
| `VelLow`       | 1 (or layer-specific)      | 1                           |
| `VelHigh`      | 127 (or layer-specific)    | 127                         |
| `LoopMode`     | `one_shot`                 | `forward_loop` or `none`    |
| `LoopStart/End`| N/A                        | Required for sustain loops  |
| `Samples`      | One per key (or layer)     | Many across range           |

---

*Use this guide to ensure the AI agent outputs valid, standards-compliant drum keygroups for MPC expansions.*

