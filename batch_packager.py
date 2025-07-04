import os
import zipfile
import argparse
import logging
import traceback


def package_expansion(folder: str, output_zip: str):
    """Create a ZIP archive from the given expansion folder."""
    logging.info("Packaging '%s' to '%s'", folder, output_zip)
    if not os.path.isdir(folder):
        raise FileNotFoundError(f"Folder not found: {folder}")

    if not os.path.exists(os.path.join(folder, "Expansion.xml")):
        logging.warning("Expansion.xml missing in %s", folder)

    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _dirs, files in os.walk(folder):
            for file in files:
                file_path = os.path.join(root, file)
                if os.path.abspath(file_path) == os.path.abspath(output_zip):
                    continue
                arcname = os.path.relpath(file_path, os.path.dirname(folder))
                zipf.write(file_path, arcname)


def package_all_expansions(root_folder: str, output_folder: str):
    """Package each subfolder in root_folder as a separate expansion."""
    os.makedirs(output_folder, exist_ok=True)
    for name in os.listdir(root_folder):
        folder_path = os.path.join(root_folder, name)
        if not os.path.isdir(folder_path):
            continue
        output_zip = os.path.join(output_folder, f"{name}.zip")
        try:
            package_expansion(folder_path, output_zip)
        except Exception as exc:
            logging.error("Failed to package %s: %s\n%s", name, exc, traceback.format_exc())


def main():
    parser = argparse.ArgumentParser(description="Batch package MPC expansions")
    parser.add_argument("source", help="Root folder containing expansion folders")
    parser.add_argument("-o", "--output", default=None, help="Destination folder for zip files")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING,
                        format="%(levelname)s - %(message)s")

    output_dir = args.output or args.source
    package_all_expansions(args.source, output_dir)


if __name__ == "__main__":
    main()
