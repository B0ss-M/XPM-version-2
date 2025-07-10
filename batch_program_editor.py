import os
import argparse
import logging
import xml.etree.ElementTree as ET

def indent_tree(tree: ET.ElementTree, space: str = "  ") -> None:
    """Indent an ElementTree for pretty printing."""
    if hasattr(ET, "indent"):
        ET.indent(tree, space=space)
    else:
        def _indent(elem: ET.Element, level: int = 0) -> None:
            i = "\n" + level * space
            if len(elem):
                if not elem.text or not elem.text.strip():
                    elem.text = i + space
                for child in elem:
                    _indent(child, level + 1)
                if not child.tail or not child.tail.strip():  # type: ignore
                    child.tail = i  # type: ignore
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i

        _indent(tree.getroot())

from xpm_parameter_editor import (
    set_layer_keytrack,
    set_volume_adsr,
    load_mod_matrix,
    apply_mod_matrix,
    set_engine_mode,
    set_application_version,
    fix_sample_notes,
)


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


if __name__ == "__main__":
    main()
