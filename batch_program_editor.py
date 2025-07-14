import os
import argparse
import logging
import xml.etree.ElementTree as ET
import json
from collections import defaultdict
from xpm_utils import _parse_xpm_for_rebuild, indent_tree
from xml.sax.saxutils import escape as xml_escape, unescape as xml_unescape

from xpm_parameter_editor import (
    set_layer_keytrack,
    set_volume_adsr,
    load_mod_matrix,
    apply_mod_matrix,
    set_engine_mode,
    set_application_version,
    fix_sample_notes,
    find_program_pads,
    infer_note_from_filename,
    extract_root_note_from_wav,
)
from firmware_profiles import get_pad_settings


def build_program_pads_json(
    firmware: str,
    mappings=None,
    engine_override: str | None = None,
    num_instruments: int | None = None,
) -> str:
    """Return ProgramPads JSON escaped for XML embedding.

    When ``num_instruments`` is provided, a ``padToInstrument`` mapping is
    included so the MPC recognizes all keygroups.
    """
    pad_cfg = get_pad_settings(firmware, engine_override)
    pads_type = pad_cfg['type']
    universal_pad = pad_cfg['universal_pad']
    engine = pad_cfg.get('engine')

    pads = {f"value{i}": 0 for i in range(128)}
    if mappings:
        for m in mappings:
            try:
                pad_index = int(m.get('pad', m.get('midi_note', 0)))
                if 0 <= pad_index < 128:
                    pads[f"value{pad_index}"] = {
                        'samplePath': m.get('sample_path', ''),
                        'rootNote': int(m.get('midi_note', 60)),
                        'lowNote': int(m.get('low_note', 0)),
                        'highNote': int(m.get('high_note', 127)),
                        'velocityLow': int(m.get('velocity_low', 0)),
                        'velocityHigh': int(m.get('velocity_high', 127)),
                    }
            except (ValueError, TypeError):
                logging.warning("Could not process mapping: %s", m)

    pads_obj = {
        'Universal': {'value0': True},
        'Type': {'value0': pads_type},
        'universalPad': universal_pad,
        'pads': pads,
        'UnusedPads': {'value0': 1},
        'PadsFollowTrackColour': {'value0': False},
    }
    if engine:
        pads_obj['engine'] = engine
    if isinstance(num_instruments, int) and num_instruments > 0:
        pads_obj['padToInstrument'] = {str(i): i for i in range(num_instruments)}
    return xml_escape(json.dumps(pads_obj, indent=4))




def find_unreferenced_audio_files(xpm_path: str, mappings: list[dict]) -> list[str]:
    """Return audio files in the same folder not referenced by mappings."""
    xpm_dir = os.path.dirname(xpm_path)
    try:
        audio_files = [f for f in os.listdir(xpm_dir) if os.path.splitext(f)[1].lower() in ('.wav', '.aif', '.aiff', '.flac', '.mp3', '.ogg', '.m4a')]
    except Exception:
        return []

    used = {os.path.basename(m.get('sample_path', '')).lower() for m in mappings}
    return [os.path.join(xpm_dir, f) for f in audio_files if f.lower() not in used]


def create_simple_xpm(program_name: str, mappings: list[dict], output_folder: str, firmware: str, format_version: str, inst_params: dict | None = None) -> bool:
    """Create a minimal XPM file from mappings."""
    note_layers: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for m in mappings:
        key = (m['low_note'], m['high_note'])
        note_layers[key].append(m)

    root = ET.Element('MPCVObject')
    version = ET.SubElement(root, 'Version')
    ET.SubElement(version, 'File_Version').text = '2.1'
    ET.SubElement(version, 'Application').text = 'MPC-V'
    ET.SubElement(version, 'Application_Version').text = firmware
    ET.SubElement(version, 'Platform').text = 'Linux'

    program = ET.SubElement(root, 'Program', {'type': 'Keygroup'})
    ET.SubElement(program, 'ProgramName').text = xml_escape(program_name)

    pads_tag = 'ProgramPads-v2.10' if firmware in {'3.4.0', '3.5.0'} else 'ProgramPads'
    pads_json = build_program_pads_json(
        firmware,
        mappings,
        engine_override=format_version,
        num_instruments=len(note_layers),
    )
    ET.SubElement(program, pads_tag).text = pads_json

    if inst_params and 'KeygroupNumKeygroups' in inst_params:
        ET.SubElement(program, 'KeygroupNumKeygroups').text = str(inst_params['KeygroupNumKeygroups'])

    instruments = ET.SubElement(program, 'Instruments')
    for idx, (low, high) in enumerate(sorted(note_layers.keys())):
        inst_elem = ET.SubElement(instruments, 'Instrument', {'number': str(idx)})
        ET.SubElement(inst_elem, 'LowNote').text = str(low)
        ET.SubElement(inst_elem, 'HighNote').text = str(high)
        if inst_params:
            for k, v in inst_params.items():
                if k == 'KeygroupNumKeygroups':
                    continue
                ET.SubElement(inst_elem, k).text = v
        layers = ET.SubElement(inst_elem, 'Layers')
        for l_idx, m in enumerate(sorted(note_layers[(low, high)], key=lambda x: x.get('velocity_low', 0)), start=1):
            layer = ET.SubElement(layers, 'Layer', {'number': str(l_idx)})
            ET.SubElement(layer, 'SampleName').text = os.path.splitext(os.path.basename(m['sample_path']))[0]
            ET.SubElement(layer, 'SampleFile').text = os.path.basename(m['sample_path'])
            ET.SubElement(layer, 'VelStart').text = str(m.get('velocity_low', 0))
            ET.SubElement(layer, 'VelEnd').text = str(m.get('velocity_high', 127))
            ET.SubElement(layer, 'SampleEnd').text = '0'
            ET.SubElement(layer, 'RootNote').text = str(m['root_note'])
            ET.SubElement(layer, 'SampleStart').text = '0'
            ET.SubElement(layer, 'Loop').text = 'Off'
            ET.SubElement(layer, 'Direction').text = '0'
            ET.SubElement(layer, 'Offset').text = '0'
            ET.SubElement(layer, 'Volume').text = '1.0'
            ET.SubElement(layer, 'Pan').text = '0.5'
            ET.SubElement(layer, 'Tune').text = '0.0'
            ET.SubElement(layer, 'MuteGroup').text = '0'

    tree = ET.ElementTree(root)
    indent_tree(tree)
    output_path = os.path.join(output_folder, f"{program_name}_fixed.xpm")
    tree.write(output_path, encoding='utf-8', xml_declaration=True)
    return True


def edit_program(
    file_path: str,
    rename: bool,
    version: str | None,
    format_version: str | None,
    keytrack: bool | None,
    attack: float | None,
    decay: float | None,
    sustain: float | None,
    release: float | None,
    mod_matrix: dict | None,
    fix_notes: bool = False,
):
    """Edit a single XPM program in-place."""
    tree = ET.parse(file_path)
    root = tree.getroot()
    changed = False

    program_name_elem = root.find('.//ProgramName')
    if program_name_elem is not None and rename:
        new_name = os.path.splitext(os.path.basename(file_path))[0]
        if program_name_elem.text != new_name:
            program_name_elem.text = new_name
            changed = True

    if version:
        if set_application_version(root, version):
            changed = True

    if format_version:
        if set_engine_mode(root, format_version):
            changed = True

    if keytrack is not None:
        if set_layer_keytrack(root, keytrack):
            changed = True

    if any(v is not None for v in (attack, decay, sustain, release)):
        if set_volume_adsr(root, attack, decay, sustain, release):
            changed = True

    if mod_matrix:
        if apply_mod_matrix(root, mod_matrix):
            changed = True

    if fix_notes:
        if fix_sample_notes(root, os.path.dirname(file_path)):
            changed = True

    if changed:
        indent_tree(tree)
        tree.write(file_path, encoding='utf-8', xml_declaration=True)
        logging.info("Updated %s", file_path)


def process_folder(
    folder: str,
    rename: bool,
    version: str | None,
    format_version: str | None,
    keytrack: bool | None,
    attack: float | None,
    decay: float | None,
    sustain: float | None,
    release: float | None,
    mod_matrix: dict | None,
    fix_notes: bool = False,
):
    for root_dir, _dirs, files in os.walk(folder):
        for file in files:
            if file.startswith('._') or not file.lower().endswith('.xpm'):
                continue
            path = os.path.join(root_dir, file)
            try:
                edit_program(
                    path,
                    rename,
                    version,
                    format_version,
                    keytrack,
                    attack,
                    decay,
                    sustain,
                    release,
                    mod_matrix,
                    fix_notes,
                )
            except Exception as exc:
                logging.error("Failed to edit %s: %s", path, exc)


def verify_mappings(folder: str, firmware: str, fmt: str | None) -> None:
    """Rebuild programs if audio files are missing from the mapping."""
    for root_dir, _dirs, files in os.walk(folder):
        for file in files:
            if file.startswith('._') or not file.lower().endswith('.xpm'):
                continue
            path = os.path.join(root_dir, file)
            mappings, params = _parse_xpm_for_rebuild(path)
            if not mappings:
                continue
            extras = find_unreferenced_audio_files(path, mappings)
            keygroup_count = len({(m['low_note'], m['high_note']) for m in mappings})
            declared = int(params.get('KeygroupNumKeygroups', keygroup_count))
            if not extras and declared == keygroup_count:
                continue
            for wav_path in extras:
                midi = extract_root_note_from_wav(wav_path) or infer_note_from_filename(wav_path) or 60
                mappings.append({
                    'sample_path': wav_path,
                    'root_note': midi,
                    'low_note': midi,
                    'high_note': midi,
                    'velocity_low': 0,
                    'velocity_high': 127,
                })
            new_count = len({(m['low_note'], m['high_note']) for m in mappings})
            params['KeygroupNumKeygroups'] = str(new_count)
            create_simple_xpm(
                os.path.splitext(os.path.basename(path))[0],
                mappings,
                os.path.dirname(path),
                firmware,
                fmt or 'advanced',
                params,
            )


def main():
    parser = argparse.ArgumentParser(description="Batch edit XPM program files")
    parser.add_argument("folder", help="Folder containing .xpm files")
    parser.add_argument("--rename", action="store_true", help="Rename ProgramName to match file name")
    parser.add_argument("--set-version", dest="version", help="Set Application_Version value")
    parser.add_argument("--format", choices=["legacy", "advanced"], help="Set engine format (legacy or advanced)")
    parser.add_argument("--keytrack", choices=["on", "off"], help="Set KeyTrack for all layers")
    parser.add_argument("--attack", type=float, help="Set VolumeAttack value")
    parser.add_argument("--decay", type=float, help="Set VolumeDecay value")
    parser.add_argument("--sustain", type=float, help="Set VolumeSustain value")
    parser.add_argument("--release", type=float, help="Set VolumeRelease value")
    parser.add_argument("--mod-matrix", dest="mod_matrix", help="JSON file with ModLink definitions")
    parser.add_argument("--fix-notes", action="store_true", help="Adjust note mappings using sample names")
    parser.add_argument("--verify-map", action="store_true", help="Rebuild programs if audio files are missing")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING,
                        format="%(levelname)s - %(message)s")

    keytrack = None
    if args.keytrack:
        keytrack = args.keytrack == "on"
    mod_matrix = load_mod_matrix(args.mod_matrix) if args.mod_matrix else None
    fmt = args.format if args.format else None
    fix_notes = args.fix_notes

    process_folder(
        args.folder,
        args.rename,
        args.version,
        fmt,
        keytrack,
        args.attack,
        args.decay,
        args.sustain,
        args.release,
        mod_matrix,
        fix_notes,
    )

    if args.verify_map:
        verify_mappings(args.folder, args.version or '3.5.0', fmt)


if __name__ == "__main__":
    main()
