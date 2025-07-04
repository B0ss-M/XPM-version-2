import os
import argparse
import logging
import xml.etree.ElementTree as ET


def edit_program(file_path: str, rename: bool, version: str | None):
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

    if changed:
        ET.indent(tree, space="  ")
        tree.write(file_path, encoding='utf-8', xml_declaration=True)
        logging.info("Updated %s", file_path)


def process_folder(folder: str, rename: bool, version: str | None):
    for root_dir, _dirs, files in os.walk(folder):
        for file in files:
            if file.lower().endswith('.xpm'):
                path = os.path.join(root_dir, file)
                try:
                    edit_program(path, rename, version)
                except Exception as exc:
                    logging.error("Failed to edit %s: %s", path, exc)


def main():
    parser = argparse.ArgumentParser(description="Batch edit XPM program files")
    parser.add_argument("folder", help="Folder containing .xpm files")
    parser.add_argument("--rename", action="store_true", help="Rename ProgramName to match file name")
    parser.add_argument("--set-version", dest="version", help="Set Application_Version value")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING,
                        format="%(levelname)s - %(message)s")

    process_folder(args.folder, args.rename, args.version)


if __name__ == "__main__":
    main()
