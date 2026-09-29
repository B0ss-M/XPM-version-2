#!/usr/bin/env python3
# Professional XPM Standards (based on ConvertWithMoss analysis):
# 1. Root notes should have +1 offset (MPC hardware convention)
# 2. Use File_Version 2.1 and Application_Version v2.11.6.6
# 3. Group samples by key ranges instead of single notes
# 4. Maximum 4 layers per keygroup (MPC hardware limit)
# 5. Use consecutive key ranges for better playability

"""
Enhanced Batch Transpose Tool for XPM Files

This tool allows you to batch transpose hundreds of XPM files by adjusting
both the KeygroupMasterTranspose parameter and all individual sample mappings.
Useful when instruments are playing at the wrong octave and need global transposition.

NEW FEATURES:
- Updates all sample mappings (LowNote, HighNote, RootNote) in addition to master transpose
- Preserves MIDI note boundaries (0-127)
- Skips invalid RootNote values (0)
- Detailed logging of all changes

Usage:
    python batch_transpose.py -f /path/to/folder -t -24 --fix-mappings

Example use case:
    If you press C2 on MPC and it plays C4 (24 semitones too high),
    use -24 to transpose down 2 octaves and fix all sample mappings.
"""

import argparse
import os
import glob
import xml.etree.ElementTree as ET
from typing import List, Tuple
import logging
from xpm_utils import load_program_pads, write_program_pads

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


def update_sample_mappings(tree: ET.ElementTree, transpose_semitones: float) -> int:
    """
    Update all sample mappings (LowNote, HighNote, RootNote) in the XPM file.
    
    Args:
        tree: Parsed XML tree
        transpose_semitones: Amount to transpose in semitones
    
    Returns:
        Number of mappings updated
    """
    root = tree.getroot()
    updated_count = 0
    
    # Find all instruments and their layers
    for instrument in root.findall(".//Instrument"):
        # Update instrument-level LowNote and HighNote
        for element_name in ['LowNote', 'HighNote']:
            elem = instrument.find(f"./{element_name}")
            if elem is not None and elem.text:
                try:
                    old_value = int(float(elem.text))
                    new_value = max(0, min(127, old_value + int(transpose_semitones)))
                    elem.text = str(new_value)
                    updated_count += 1
                    logger.debug(f"Updated instrument {element_name}: {old_value} → {new_value}")
                except ValueError:
                    continue
        
        # Update layer-level RootNote values
        layers = instrument.find(".//Layers")
        if layers is not None:
            for layer in layers.findall(".//Layer"):
                root_note_elem = layer.find(".//RootNote")
                if root_note_elem is not None and root_note_elem.text:
                    try:
                        old_value = int(float(root_note_elem.text))
                        # Skip if already at 0 (invalid/unset)
                        if old_value == 0:
                            continue
                        new_value = max(0, min(127, old_value + int(transpose_semitones)))
                        root_note_elem.text = str(new_value)
                        updated_count += 1
                        logger.debug(f"Updated layer RootNote: {old_value} → {new_value}")
                    except ValueError:
                        continue

    # Modern programs can carry a second copy of the mapping in ProgramPads.
    # Keep it in sync with the Instrument/Layer XML without changing its shape.
    pads_elem = next((elem for elem in root.iter() if isinstance(elem.tag, str)
                      and (elem.tag == 'ProgramPads' or elem.tag.startswith('ProgramPads-v'))), None)
    data, payload = load_program_pads(pads_elem)
    if payload is not None:
        changed = False
        pads = payload.get('pads', {})
        if isinstance(pads, dict):
            for pad in pads.values():
                if not isinstance(pad, dict):
                    continue
                for field in ('lowNote', 'highNote', 'rootNote'):
                    value = pad.get(field)
                    if value is None:
                        continue
                    try:
                        old = int(float(value))
                    except (TypeError, ValueError):
                        continue
                    if field == 'rootNote' and old == 0:
                        continue
                    new = max(0, min(127, old + int(transpose_semitones)))
                    if new != old:
                        pad[field] = new
                        updated_count += 1
                        changed = True
        if changed:
            write_program_pads(pads_elem, data)
    
    return updated_count


def set_transpose(xpm_path: str, transpose_value: float, backup: bool = True, 
                 fix_mappings: bool = False) -> bool:
    """
    Set the KeygroupMasterTranspose value in an XPM file and optionally fix sample mappings.
    
    Args:
        xpm_path: Path to XPM file
        transpose_value: New transpose value
        backup: Create backup file
        fix_mappings: Also update all sample mappings
    """
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
        old_master_transpose = float(transpose_elem.text) if transpose_elem.text else 0.0
        transpose_elem.text = f"{transpose_value:.6f}"
        
        mapping_updates = 0
        if fix_mappings:
            # Calculate the difference for sample mapping updates
            transpose_diff = transpose_value - old_master_transpose
            mapping_updates = update_sample_mappings(tree, transpose_diff)
        
        # Save the modified file
        indent_tree(tree)
        tree.write(xpm_path, encoding="utf-8", xml_declaration=True)
        
        if fix_mappings and mapping_updates > 0:
            logger.info(f"Updated {os.path.basename(xpm_path)}: Master transpose {old_master_transpose:.1f} → {transpose_value:.1f}, "
                       f"Fixed {mapping_updates} sample mappings")
        else:
            logger.info(f"Updated {os.path.basename(xpm_path)}: {old_master_transpose:.1f} → {transpose_value:.1f} semitones")
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
                   backup: bool = True, dry_run: bool = False,
                   fix_mappings: bool = False) -> Tuple[int, int]:
    """
    Batch transpose all XPM files in a folder.
    
    Args:
        folder_path: Path to folder containing XPM files
        transpose_amount: Amount to transpose in semitones
        relative: If True, add to existing transpose; if False, set absolute value
        recursive: Search subfolders for XPM files
        backup: Create .backup files before modifying
        dry_run: Show what would be done without making changes
        fix_mappings: Also update all sample mappings (LowNote, HighNote, RootNote)
    
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
    
    if fix_mappings:
        logger.info("Sample mapping fix enabled - will update LowNote, HighNote, and RootNote values")
    
    successful = 0
    
    for xpm_path in xpm_files:
        try:
            current_transpose = get_current_transpose(xpm_path)
            
            if relative:
                new_transpose = current_transpose + transpose_amount
            else:
                new_transpose = transpose_amount
            
            if dry_run:
                action_desc = f"transpose {current_transpose:.1f} → {new_transpose:.1f} semitones"
                if fix_mappings:
                    action_desc += " + fix sample mappings"
                logger.info(f"Would update {os.path.basename(xpm_path)}: {action_desc}")
            else:
                if set_transpose(xpm_path, new_transpose, backup, fix_mappings):
                    successful += 1
        
        except Exception as e:
            logger.error(f"Error processing {xpm_path}: {e}")
    
    return successful, len(xpm_files)


def main():
    parser = argparse.ArgumentParser(description="Enhanced Batch Transpose Tool for XPM Files")
    parser.add_argument("-f", "--folder", required=True,
                       help="Folder containing XPM files")
    parser.add_argument("-t", "--transpose", type=float, required=True,
                       help="Transpose amount in semitones (e.g., -24 for down 2 octaves)")
    parser.add_argument("-r", "--relative", action="store_true",
                       help="Add to existing transpose instead of setting absolute value")
    parser.add_argument("--fix-mappings", action="store_true",
                       help="Also update all sample mappings (LowNote, HighNote, RootNote)")
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
        dry_run=args.dry_run,
        fix_mappings=args.fix_mappings
    )
    
    if args.dry_run:
        logger.info(f"Dry run complete. Would have processed {total} files.")
    else:
        logger.info(f"Processing complete. Successfully updated {successful}/{total} files.")
    
    return 0 if successful == total else 1


if __name__ == "__main__":
    exit(main())
