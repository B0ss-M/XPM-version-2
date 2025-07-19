#!/usr/bin/env python3
"""
Batch Transpose Tool for XPM Files

This tool allows you to batch transpose hundreds of XPM files by adjusting
the KeygroupMasterTranspose parameter. Useful when instruments are playing
at the wrong octave and need global transposition.

Usage:
    python batch_transpose.py -f /path/to/folder -t -24

Example use case:
    If you press C2 on MPC and it plays C4 (24 semitones too high),
    use -24 to transpose down 2 octaves.
"""

import argparse
import os
import glob
import xml.etree.ElementTree as ET
from typing import List, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def indent_tree(tree: ET.ElementTree) -> None:
    """Add indentation to XML tree for better formatting."""
    def _indent(elem, level=0):
        i = "\n" + level * "    "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "    "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for child in elem:
                _indent(child, level + 1)
            if not child.tail or not child.tail.strip():
                child.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i
    
    _indent(tree.getroot())


def get_current_transpose(xpm_path: str) -> float:
    """Get the current KeygroupMasterTranspose value from an XPM file."""
    try:
        tree = ET.parse(xpm_path)
        root = tree.getroot()
        
        transpose_elem = root.find(".//KeygroupMasterTranspose")
        if transpose_elem is not None and transpose_elem.text:
            return float(transpose_elem.text)
        return 0.0
    except Exception as e:
        logger.error(f"Error reading transpose from {xpm_path}: {e}")
        return 0.0


def set_transpose(xpm_path: str, transpose_value: float, backup: bool = True) -> bool:
    """Set the KeygroupMasterTranspose value in an XPM file."""
    try:
        # Create backup if requested
        if backup:
            backup_path = xpm_path + ".backup"
            if not os.path.exists(backup_path):
                import shutil
                shutil.copy2(xpm_path, backup_path)
                logger.debug(f"Created backup: {backup_path}")
        
        # Parse the XPM file
        tree = ET.parse(xpm_path)
        root = tree.getroot()
        
        # Find or create the KeygroupMasterTranspose element
        transpose_elem = root.find(".//KeygroupMasterTranspose")
        
        if transpose_elem is None:
            # If the element doesn't exist, find the Program element and add it
            program_elem = root.find(".//Program")
            if program_elem is not None:
                transpose_elem = ET.SubElement(program_elem, "KeygroupMasterTranspose")
            else:
                logger.error(f"Could not find Program element in {xpm_path}")
                return False
        
        # Set the new transpose value
        old_value = float(transpose_elem.text) if transpose_elem.text else 0.0
        transpose_elem.text = f"{transpose_value:.6f}"
        
        # Save the modified file
        indent_tree(tree)
        tree.write(xpm_path, encoding="utf-8", xml_declaration=True)
        
        logger.info(f"Updated {os.path.basename(xpm_path)}: {old_value:.1f} → {transpose_value:.1f} semitones")
        return True
        
    except Exception as e:
        logger.error(f"Error updating {xpm_path}: {e}")
        return False


def find_xpm_files(folder_path: str, recursive: bool = True) -> List[str]:
    """Find all XPM files in the specified folder."""
    if recursive:
        pattern = os.path.join(folder_path, "**", "*.xpm")
        return glob.glob(pattern, recursive=True)
    else:
        pattern = os.path.join(folder_path, "*.xpm")
        return glob.glob(pattern)


def batch_transpose(folder_path: str, transpose_amount: float, 
                   relative: bool = False, recursive: bool = True, 
                   backup: bool = True, dry_run: bool = False) -> Tuple[int, int]:
    """
    Batch transpose all XPM files in a folder.
    
    Args:
        folder_path: Path to folder containing XPM files
        transpose_amount: Amount to transpose in semitones
        relative: If True, add to existing transpose; if False, set absolute value
        recursive: Search subfolders for XPM files
        backup: Create .backup files before modifying
        dry_run: Show what would be done without making changes
    
    Returns:
        Tuple of (successful_count, total_count)
    """
    xpm_files = find_xpm_files(folder_path, recursive)
    
    if not xpm_files:
        logger.warning(f"No XPM files found in {folder_path}")
        return 0, 0
    
    logger.info(f"Found {len(xpm_files)} XPM file(s)")
    
    if dry_run:
        logger.info("DRY RUN - No files will be modified")
    
    successful = 0
    
    for xpm_path in xpm_files:
        try:
            current_transpose = get_current_transpose(xpm_path)
            
            if relative:
                new_transpose = current_transpose + transpose_amount
            else:
                new_transpose = transpose_amount
            
            if dry_run:
                logger.info(f"Would update {os.path.basename(xpm_path)}: "
                           f"{current_transpose:.1f} → {new_transpose:.1f} semitones")
            else:
                if set_transpose(xpm_path, new_transpose, backup):
                    successful += 1
        
        except Exception as e:
            logger.error(f"Error processing {xpm_path}: {e}")
    
    return successful, len(xpm_files)


def main():
    parser = argparse.ArgumentParser(description="Batch transpose XPM files")
    parser.add_argument("-f", "--folder", required=True,
                       help="Folder containing XPM files")
    parser.add_argument("-t", "--transpose", type=float, required=True,
                       help="Transpose amount in semitones (e.g., -24 for down 2 octaves)")
    parser.add_argument("-r", "--relative", action="store_true",
                       help="Add to existing transpose instead of setting absolute value")
    parser.add_argument("--no-recursive", action="store_true",
                       help="Don't search subfolders")
    parser.add_argument("--no-backup", action="store_true",
                       help="Don't create backup files")
    parser.add_argument("-n", "--dry-run", action="store_true",
                       help="Show what would be done without making changes")
    parser.add_argument("-v", "--verbose", action="store_true",
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if not os.path.isdir(args.folder):
        logger.error(f"Folder not found: {args.folder}")
        return 1
    
    logger.info(f"Processing XPM files in: {args.folder}")
    logger.info(f"Transpose amount: {args.transpose} semitones")
    logger.info(f"Mode: {'Relative' if args.relative else 'Absolute'}")
    
    successful, total = batch_transpose(
        folder_path=args.folder,
        transpose_amount=args.transpose,
        relative=args.relative,
        recursive=not args.no_recursive,
        backup=not args.no_backup,
        dry_run=args.dry_run
    )
    
    if args.dry_run:
        logger.info(f"Dry run complete. Would have processed {total} files.")
    else:
        logger.info(f"Processing complete. Successfully updated {successful}/{total} files.")
    
    return 0 if successful == total else 1


if __name__ == "__main__":
    exit(main())
