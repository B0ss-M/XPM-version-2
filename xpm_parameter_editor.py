"""Helper functions for editing XPM program parameters."""

from __future__ import annotations

import json
import logging
import os
import re
import struct
import xml.etree.ElementTree as ET
from typing import Dict, Optional
from xml.sax.saxutils import escape as xml_escape, unescape as xml_unescape

from audio_pitch import detect_fundamental_pitch
from collections import Counter


def _update_text(elem: Optional[ET.Element], value: Optional[str]) -> bool:
    """Update ``elem.text`` if ``value`` differs.

    Returns ``True`` if the element text was changed.
    """

    if elem is None or value is None:
        return False
    if elem.text != value:
        elem.text = value
        return True
    return False


def find_program_pads(root: ET.Element) -> Optional[ET.Element]:
    """Return the ProgramPads element regardless of version."""

    pads_elem = root.find(".//ProgramPads-v2.10")
    if pads_elem is None:
        pads_elem = root.find(".//ProgramPads")
    if pads_elem is not None:
        return pads_elem

    for elem in root.iter():
        tag = getattr(elem, "tag", "")
        if isinstance(tag, str) and tag.startswith("ProgramPads-v"):
            return elem
    return None


def set_layer_keytrack(root: ET.Element, keytrack: bool) -> bool:
    """Enable or disable KeyTrack on all ``Layer`` elements."""

    changed = False
    val = "True" if keytrack else "False"
    for layer in root.findall(".//Layer"):
        changed |= _update_text(layer.find("KeyTrack"), val)
    return changed


def set_volume_adsr(
    root: ET.Element,
    attack: Optional[float],
    decay: Optional[float],
    sustain: Optional[float],
    release: Optional[float],
) -> bool:
    """Update the volume envelope ADSR values."""

    changed = False
    for inst in root.findall(".//Instrument"):
        changed |= _update_text(
            inst.find("VolumeAttack"), str(attack) if attack is not None else None
        )
        changed |= _update_text(
            inst.find("VolumeDecay"), str(decay) if decay is not None else None
        )
        changed |= _update_text(
            inst.find("VolumeSustain"), str(sustain) if sustain is not None else None
        )
        changed |= _update_text(
            inst.find("VolumeRelease"), str(release) if release is not None else None
        )
    return changed


def load_mod_matrix(path: str) -> Dict[int, Dict[str, str]]:
    """Return a modulation matrix dictionary from ``path``.

    The returned dictionary is indexed by ``Num`` values from the JSON file.
    """

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        logging.error("Could not load mod matrix '%s': %s", path, exc)
        return {}

    matrix: Dict[int, Dict[str, str]] = {}
    if isinstance(data, list):
        for entry in data:
            num = entry.get("Num")
            if num is None:
                continue
            matrix[int(num)] = {k: str(v) for k, v in entry.items() if k != "Num"}
    elif isinstance(data, dict):
        for num, params in data.items():
            matrix[int(num)] = {k: str(v) for k, v in params.items()}

    return matrix


def apply_mod_matrix(root: ET.Element, matrix: Dict[int, Dict[str, str]]) -> bool:
    """Apply modulation matrix values to existing ``ModLink`` elements."""

    changed = False
    for link in root.findall(".//ModLink"):
        try:
            num = int(link.get("Num", -1))
        except ValueError:
            continue
        params = matrix.get(num)
        if not params:
            continue
        for attr, val in params.items():
            if link.get(attr) != val:
                link.set(attr, val)
                changed = True
    return changed


def set_application_version(root: ET.Element, version: Optional[str]) -> bool:
    """Set the ``Application_Version`` element to ``version``."""

    ver_elem = root.find(".//Application_Version")
    return _update_text(ver_elem, version)


def set_engine_mode(root: ET.Element, mode: str) -> bool:
    """Switch between legacy and advanced engine modes."""

    if mode not in {"legacy", "advanced"}:
        return False

    changed = False

    pads_elem = find_program_pads(root)
    if pads_elem is not None and pads_elem.text:
        try:
            data = json.loads(xml_unescape(pads_elem.text))
        except json.JSONDecodeError:
            data = {}
        if not isinstance(data, dict):
            data = {}
        if data.get("engine") != mode:
            data["engine"] = mode
            pads_elem.text = xml_escape(json.dumps(data, indent=4))
            changed = True

    legacy_elem = root.find(".//KeygroupLegacyMode")
    changed |= _update_text(legacy_elem, "True" if mode == "legacy" else "False")
    return changed


def name_to_midi(note_name: str) -> Optional[int]:
    """Convert a note name such as ``C#4`` to a MIDI note number."""

    if not note_name:
        return None

    note_name = note_name.strip().upper()
    note_map = {
        "C": 0,
        "C#": 1,
        "DB": 1,
        "D": 2,
        "D#": 3,
        "EB": 3,
        "E": 4,
        "F": 5,
        "F#": 6,
        "GB": 6,
        "G": 7,
        "G#": 8,
        "AB": 8,
        "A": 9,
        "A#": 10,
        "BB": 10,
        "B": 11,
    }

    m = re.match(r"^([A-G][#B]?)(-?\d+)$", note_name)
    if not m:
        return None
    note, octave_str = m.groups()
    if note not in note_map:
        return None
    try:
        midi = 12 + note_map[note] + 12 * int(octave_str)
        return midi if 0 <= midi <= 127 else None
    except (ValueError, TypeError):
        return None


def infer_note_from_filename(filename: str) -> Optional[int]:
    """Try to infer a MIDI note number from ``filename``.

    The function now scans the entire basename for multiple note tokens like
    ``A3`` or ``C#4`` and returns the **last** valid note found. This allows
    patterns such as ``Piano_A3-64.wav`` or ``VNLGF41C2.wav`` to resolve
    correctly. If no note name is detected, it falls back to the last numeric
    sequence that looks like a MIDI value (e.g. ``64``).
    """

    base = os.path.splitext(os.path.basename(filename))[0]

    note_matches = re.findall(
        r"(?<![A-Za-z])([A-G][#b]?-?\d{1,2})(?![A-Za-z0-9])", base, re.IGNORECASE
    )
    for note in reversed(note_matches):
        midi = name_to_midi(note)
        if midi is not None:
            return midi

    num_matches = re.findall(r"\b(\d{2,3})\b", base)
    if num_matches:
        num = int(num_matches[-1])
        if 0 <= num <= 127:
            return num
    return None


def extract_root_note_from_wav(filepath: str) -> Optional[int]:
    """Return the MIDI root note from a WAV file.

    If the ``smpl`` chunk is missing, the function returns ``None``.
    Pitch detection is handled separately when fixing sample notes.
    """

    try:
        with open(filepath, "rb") as f:
            data = f.read()
        idx = data.find(b"smpl")
        if idx != -1 and idx + 36 <= len(data):
            # The MIDI unity note is stored 20 bytes after the 'smpl' tag
            # (after the 8-byte chunk header and three 32-bit fields).
            note = struct.unpack("<I", data[idx + 20 : idx + 24])[0]
            if 0 <= note <= 127:
                return note
    except Exception as exc:
        logging.error("Could not extract root note from WAV %s: %s", filepath, exc)

    # Pitch detection disabled due to unreliable results
    return None


def write_root_note_to_wav(path: str, midi_note: int) -> bool:
    """Write ``midi_note`` to the WAV file's ``smpl`` chunk.

    If the chunk does not exist, it will be created. The RIFF size
    field is updated when appending a new chunk.
    Returns ``True`` if the file was modified.
    """

    try:
        with open(path, "r+b") as f:
            data = f.read()
            idx = data.find(b"smpl")
            if idx != -1 and idx + 24 <= len(data):
                f.seek(idx + 20)
                f.write(struct.pack("<I", midi_note))
                return True

            # create new chunk at end
            if len(data) >= 8 and data[:4] == b"RIFF" and data[8:12] == b"WAVE":
                riff_size = struct.unpack("<I", data[4:8])[0]
                new_chunk = b"smpl" + struct.pack("<I", 36) + struct.pack(
                    "<9I", 0, 0, 0, midi_note, 0, 0, 0, 0, 0
                )
                f.seek(4)
                f.write(struct.pack("<I", riff_size + len(new_chunk)))
                f.seek(0, os.SEEK_END)
                f.write(new_chunk)
                return True
    except Exception as exc:  # pragma: no cover - best effort
        logging.error("Could not write root note to %s: %s", path, exc)
    return False


def update_wav_root_notes(root: ET.Element, folder: str) -> bool:
    """Write root note metadata for each referenced WAV file."""

    changed = False

    pads_elem = find_program_pads(root)
    if pads_elem is not None and pads_elem.text:
        try:
            data = json.loads(xml_unescape(pads_elem.text))
        except json.JSONDecodeError:
            data = {}
        pads = data.get("pads", {}) if isinstance(data, dict) else {}
        for pad in pads.values():
            if isinstance(pad, dict):
                sample = pad.get("samplePath")
                root_note = pad.get("rootNote")
                if sample and root_note is not None:
                    abs_path = sample if os.path.isabs(sample) else os.path.join(folder, sample)
                    if write_root_note_to_wav(abs_path, int(root_note)):
                        changed = True

    for layer in root.findall(".//Layer"):
        sample_elem = layer.find("SampleFile")
        root_elem = layer.find("RootNote")
        if sample_elem is None or root_elem is None:
            continue
        sample = sample_elem.text
        midi = root_elem.text
        if not sample or not midi:
            continue
        abs_path = sample if os.path.isabs(sample) else os.path.join(folder, sample)
        if write_root_note_to_wav(abs_path, int(midi)):
            changed = True

    return changed


def fix_sample_notes(root: ET.Element, folder: str) -> bool:
    """Update root/low/high notes using metadata, filenames, or pitch detection."""

    changed = False

    pads_elem = find_program_pads(root)
    if pads_elem is not None and pads_elem.text:
        try:
            data = json.loads(xml_unescape(pads_elem.text))
        except json.JSONDecodeError:
            data = {}
        if not isinstance(data, dict):
            data = {}
        pads = data.get("pads", {})
        for pad in pads.values():
            if isinstance(pad, dict) and pad.get("samplePath"):
                sample_path = pad["samplePath"]
                abs_path = (
                    sample_path
                    if os.path.isabs(sample_path)
                    else os.path.join(folder, sample_path)
                )
                midi = (
                    extract_root_note_from_wav(abs_path)
                    or infer_note_from_filename(sample_path)
                    or detect_fundamental_pitch(abs_path)
                )
                if midi is None:
                    continue
                if pad.get("rootNote") != midi:
                    pad["rootNote"] = midi
                    changed = True
                # Preserve existing note ranges when present
                if pad.get("lowNote") in (None, pad.get("rootNote")):
                    if pad.get("lowNote") != midi:
                        pad["lowNote"] = midi
                        changed = True
                if pad.get("highNote") in (None, pad.get("rootNote")):
                    if pad.get("highNote") != midi:
                        pad["highNote"] = midi
                        changed = True
        # Build padToInstrument mapping so the MPC reports the correct number
        # of keygroups. This is required for older programs that may be
        # missing this section.
        pad_to_inst = {}
        inst_idx = 0
        for idx in range(128):
            pad = pads.get(f"value{idx}")
            if isinstance(pad, dict) and pad.get("samplePath"):
                pad_to_inst[str(idx)] = inst_idx
                inst_idx += 1
        if inst_idx > 0:
            if data.get("padToInstrument") != pad_to_inst:
                data["padToInstrument"] = pad_to_inst
                changed = True
        elif "padToInstrument" in data:
            data.pop("padToInstrument")
            changed = True

        if changed:
            pads_elem.text = xml_escape(json.dumps(data, indent=4))

    for inst in root.findall(".//Instrument"):
        low_elem = inst.find("LowNote")
        high_elem = inst.find("HighNote")
        inst_midi = None
        for layer in inst.findall(".//Layer"):
            sample_elem = layer.find("SampleFile")
            root_elem = layer.find("RootNote")
            if sample_elem is None or not sample_elem.text:
                continue
            sample_path = sample_elem.text
            abs_path = (
                sample_path
                if os.path.isabs(sample_path)
                else os.path.join(folder, sample_path)
            )
            midi = (
                extract_root_note_from_wav(abs_path)
                or infer_note_from_filename(sample_path)
                or detect_fundamental_pitch(abs_path)
            )
            if midi is None:
                continue
            if inst_midi is None:
                inst_midi = midi
            if root_elem is not None and root_elem.text != str(midi):
                root_elem.text = str(midi)
                changed = True
        if inst_midi is None:
            continue
        # Only adjust range if missing or equal
        if (
            low_elem is not None
            and high_elem is not None
            and (low_elem.text == high_elem.text or not low_elem.text or not high_elem.text)
        ):
            if low_elem.text != str(inst_midi):
                low_elem.text = str(inst_midi)
                changed = True
            if high_elem.text != str(inst_midi):
                high_elem.text = str(inst_midi)
                changed = True

    # Ensure KeygroupNumKeygroups matches the number of instruments
    keygroup_elem = root.find(".//KeygroupNumKeygroups")
    num_kgs = len(root.findall(".//Instrument"))
    if keygroup_elem is not None and keygroup_elem.text != str(num_kgs):
        keygroup_elem.text = str(num_kgs)
        changed = True

    return changed


def fix_master_transpose(root: ET.Element, folder: str) -> bool:
    """Detect and correct a global note offset via ``KeygroupMasterTranspose``."""

    diffs = []

    pads_elem = find_program_pads(root)
    if pads_elem is not None and pads_elem.text:
        try:
            data = json.loads(xml_unescape(pads_elem.text))
        except json.JSONDecodeError:
            data = {}
        pads = data.get("pads", {}) if isinstance(data, dict) else {}
        for pad in pads.values():
            if not isinstance(pad, dict):
                continue
            sample_path = pad.get("samplePath")
            root_note = pad.get("rootNote")
            if sample_path and root_note is not None:
                abs_path = (
                    sample_path
                    if os.path.isabs(sample_path)
                    else os.path.join(folder, sample_path)
                )
                midi = (
                    extract_root_note_from_wav(abs_path)
                    or infer_note_from_filename(sample_path)
                    or detect_fundamental_pitch(abs_path)
                )
                if midi is not None:
                    try:
                        diffs.append(int(midi) - int(root_note))
                    except (ValueError, TypeError):
                        pass
    for layer in root.findall(".//Layer"):
        sample_elem = layer.find("SampleFile")
        root_elem = layer.find("RootNote")
        if sample_elem is None or root_elem is None:
            continue
        sample_path = sample_elem.text
        root_note = root_elem.text
        if not sample_path or not root_note:
            continue
        abs_path = (
            sample_path if os.path.isabs(sample_path) else os.path.join(folder, sample_path)
        )
        midi = (
            extract_root_note_from_wav(abs_path)
            or infer_note_from_filename(sample_path)
            or detect_fundamental_pitch(abs_path)
        )
        if midi is not None:
            try:
                diffs.append(int(midi) - int(root_note))
            except (ValueError, TypeError):
                pass

    if not diffs:
        return False

    common_diff, count = Counter(diffs).most_common(1)[0]
    if count < len(diffs) * 0.6 or common_diff == 0:
        return False

    elem = root.find(".//KeygroupMasterTranspose")
    if elem is None:
        return False

    new_val = f"{float(common_diff):.6f}"
    if elem.text != new_val:
        elem.text = new_val
        return True
    return False


# Note: File ends after this line to avoid stray indentation.
