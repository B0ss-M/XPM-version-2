import os
import argparse
import xml.etree.ElementTree as ET

from xpm_parameter_editor import fix_sample_notes, indent_tree


def fix_file(path: str) -> bool:
    """Apply note fixes to one XPM file."""
    try:
        tree = ET.parse(path)
        root = tree.getroot()
    except ET.ParseError as exc:
        print(f"Parse error in {path}: {exc}")
        return False

    if fix_sample_notes(root, os.path.dirname(path)):
        indent_tree(tree)
        tree.write(path, encoding="utf-8", xml_declaration=True)
        print(f"Fixed {path}")
        return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Fix root notes in XPM programs")
    parser.add_argument("path", help="XPM file or folder")
    args = parser.parse_args()

    target = args.path
    if os.path.isfile(target):
        fix_file(target)
    else:
        for root_dir, _, files in os.walk(target):
            for name in files:
                if name.lower().endswith(".xpm"):
                    fix_file(os.path.join(root_dir, name))


if __name__ == "__main__":
    main()
