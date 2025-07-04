import os
import zipfile
import argparse
import logging
import traceback
from typing import Iterable


def validate_expansion(folder: str) -> Iterable[str]:
    """Yield problems found with the folder structure."""
    if not os.path.isfile(os.path.join(folder, "Expansion.xml")):
        yield "Missing Expansion.xml"

    samples_dir = os.path.join(folder, "Samples")
    if not os.path.isdir(samples_dir):
        yield "Missing 'Samples' folder"
    elif not any(f.lower().endswith(('.wav', '.aif', '.aiff')) for f in os.listdir(samples_dir)):
        yield "Samples folder has no audio files"

    has_xpm = False
    for _root, _d, files in os.walk(folder):
        if any(f.lower().endswith('.xpm') for f in files):
            has_xpm = True
            break
    if not has_xpm:
        yield "No .xpm program files found"


def package_expansion(folder: str, output_file: str):
    """Create an expansion archive from the given folder."""
    logging.info("Packaging '%s' to '%s'", folder, output_file)
    if not os.path.isdir(folder):
        raise FileNotFoundError(f"Folder not found: {folder}")

    issues = list(validate_expansion(folder))
    if issues:
        raise ValueError("; ".join(issues))

    with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _dirs, files in os.walk(folder):
            for file in files:
                file_path = os.path.join(root, file)
                if os.path.abspath(file_path) == os.path.abspath(output_file):
                    continue
                arcname = os.path.relpath(file_path, os.path.dirname(folder))
                zipf.write(file_path, arcname)


def package_all_expansions(root_folder: str, output_folder: str, ext: str):
    """Package each subfolder in root_folder as a separate expansion."""
    os.makedirs(output_folder, exist_ok=True)
    for name in os.listdir(root_folder):
        folder_path = os.path.join(root_folder, name)
        if not os.path.isdir(folder_path):
            continue
        output_file = os.path.join(output_folder, f"{name}{ext}")
        try:
            package_expansion(folder_path, output_file)
        except Exception as exc:
            logging.error("Failed to package %s: %s\n%s", name, exc, traceback.format_exc())


def main():
    parser = argparse.ArgumentParser(description="Batch package MPC expansions")
    parser.add_argument("source", help="Root folder containing expansion folders")
    parser.add_argument("-o", "--output", default=None, help="Destination folder for archives")
    parser.add_argument("-e", "--ext", choices=["zip", "zpn"], default="zip",
                        help="Archive extension to use (zip or zpn)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING,
                        format="%(levelname)s - %(message)s")

    output_dir = args.output or args.source
    ext = "." + args.ext.lstrip('.')
    package_all_expansions(args.source, output_dir, ext)


if __name__ == "__main__":
    main()
