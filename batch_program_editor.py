import os
import argparse
import logging
import json
import xml.etree.ElementTree as ET
from xpm_parameter_editor import (
    set_layer_keytrack,
    set_volume_adsr,
    load_mod_matrix,
    apply_mod_matrix,
)
from editor_presets import load_presets


def edit_program(
    file_path: str,
    rename: bool,
    version: str | None,
    keytrack: bool | None,
    attack: float | None,
    decay: float | None,
    sustain: float | None,
    release: float | None,
    mod_matrix: dict | None,
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
        ver_elem = root.find('.//Application_Version')
        if ver_elem is not None and ver_elem.text != version:
            ver_elem.text = version
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

    if changed:
        ET.indent(tree, space="  ")
        tree.write(file_path, encoding='utf-8', xml_declaration=True)
        logging.info("Updated %s", file_path)


def process_folder(
    folder: str,
    rename: bool,
    version: str | None,
    keytrack: bool | None,
    attack: float | None,
    decay: float | None,
    sustain: float | None,
    release: float | None,
    mod_matrix: dict | None,
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
                    keytrack,
                    attack,
                    decay,
                    sustain,
                    release,
                    mod_matrix,
                )
            except Exception as exc:
                logging.error("Failed to edit %s: %s", path, exc)


def main():
    parser = argparse.ArgumentParser(description="Batch edit XPM program files")
    parser.add_argument("folder", help="Folder containing .xpm files")
    parser.add_argument("--rename", action="store_true", help="Rename ProgramName to match file name")
    parser.add_argument("--set-version", dest="version", help="Set Application_Version value")
    parser.add_argument("--keytrack", choices=["on", "off"], help="Set KeyTrack for all layers")
    parser.add_argument("--attack", type=float, help="Set VolumeAttack value")
    parser.add_argument("--decay", type=float, help="Set VolumeDecay value")
    parser.add_argument("--sustain", type=float, help="Set VolumeSustain value")
    parser.add_argument("--release", type=float, help="Set VolumeRelease value")
    parser.add_argument("--mod-matrix", dest="mod_matrix", help="JSON file with ModLink definitions")
    parser.add_argument("--preset", help="Preset name from editor_presets.json")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING,
                        format="%(levelname)s - %(message)s")

    presets = load_presets()
    preset_vals = presets.get(args.preset, {}) if args.preset else {}

    keytrack = None
    if args.keytrack:
        keytrack = args.keytrack == "on"
    elif "keytrack" in preset_vals:
        keytrack = bool(preset_vals.get("keytrack"))

    mod_matrix_path = args.mod_matrix or preset_vals.get("mod_matrix")
    mod_matrix = load_mod_matrix(mod_matrix_path) if mod_matrix_path else None

    process_folder(
        args.folder,
        args.rename or preset_vals.get("rename", False),
        args.version or preset_vals.get("version"),
        keytrack,
        args.attack if args.attack is not None else preset_vals.get("attack"),
        args.decay if args.decay is not None else preset_vals.get("decay"),
        args.sustain if args.sustain is not None else preset_vals.get("sustain"),
        args.release if args.release is not None else preset_vals.get("release"),
        mod_matrix,
    )


if __name__ == "__main__":
    main()
