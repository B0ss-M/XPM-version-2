import os
import argparse
import xml.etree.ElementTree as ET

from xpm_parameter_editor import (
    fix_sample_notes,
    update_wav_root_notes,
    fix_master_transpose,
)
from batch_program_editor import indent_tree


def fix_file(path: str, write_wav: bool = False) -> bool:
    """Apply note fixes to one XPM file."""
    try:
        tree = ET.parse(path)
        root = tree.getroot()
    except ET.ParseError as exc:
        print(f"Parse error in {path}: {exc}")
        return False

    folder = os.path.dirname(path)
    changed = False

    if fix_sample_notes(root, folder):
        changed = True

    if fix_master_transpose(root, folder):
        changed = True

    if changed:
        indent_tree(tree)
        tree.write(path, encoding="utf-8", xml_declaration=True)
        print(f"Fixed {path}")
        if write_wav:
            update_wav_root_notes(root, folder)
        return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Fix root notes in XPM programs")
    parser.add_argument("path", help="XPM file or folder")
    parser.add_argument(
        "--update-wav",
        action="store_true",
        help="Write detected root notes back to WAV metadata",
    )
    args = parser.parse_args()

    target = args.path
    if os.path.isfile(target):
        fix_file(target, args.update_wav)
    else:
        for root_dir, _, files in os.walk(target):
            for name in files:
                if name.lower().endswith(".xpm"):
                    fix_file(os.path.join(root_dir, name), args.update_wav)


if __name__ == "__main__":
    main()
