#!/usr/bin/env python3
"""
XPM Repair Doctor - Advanced XPM Structural Repair Tool
======================================================

This tool provides comprehensive repair capabilities for structurally broken XPM files
that were created by batch processing functions but have issues preventing MPC playback:

FIXES:
- 128 empty instruments (structural bloat)
- Missing or broken ProgramPads mapping
- Incorrect keygroup counts and ranges
- Missing instrument layers and sample references
- Broken pad-to-instrument mappings
- Version compatibility issues

INTEGRATION:
- Works with existing Expansion Doctor
- Integrates with Batch Program Fixer
- Uses enhanced pitch detection
- Leverages InstrumentBuilder for rebuilds

The tool can operate in multiple modes:
1. Analysis mode - Detect issues without fixing
2. Repair mode - Fix individual files  
3. Batch mode - Process entire folders
4. Integration mode - Called by other tools
"""

import os
import sys
import json
import shutil
import logging
import traceback
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape as xml_escape, unescape as xml_unescape
from typing import List, Dict, Optional, Tuple, Any

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Import from existing codebase
try:
    from xpm_utils import _parse_xpm_for_rebuild, indent_tree
    import importlib.util
    
    # Import from main file (handle space in filename)
    spec = importlib.util.spec_from_file_location("gemini_main", "Gemini wav_TO_XpmV2.py")
    gemini_main = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gemini_main)
    
    detect_sample_note = gemini_main.detect_sample_note
    InstrumentBuilder = gemini_main.InstrumentBuilder
    InstrumentOptions = gemini_main.InstrumentOptions
    
    IMPORTS_SUCCESSFUL = True
except ImportError as e:
    IMPORTS_SUCCESSFUL = False
    logging.error(f"Failed to import required modules: {e}")


class XPMStructuralIssue:
    """Represents a structural issue found in an XPM file."""
    
    def __init__(self, issue_type: str, description: str, severity: str = "medium", 
                 fix_method: str = None, details: Dict = None):
        self.issue_type = issue_type
        self.description = description
        self.severity = severity  # "critical", "high", "medium", "low"
        self.fix_method = fix_method
        self.details = details or {}
    
    def __str__(self):
        return f"[{self.severity.upper()}] {self.issue_type}: {self.description}"


class XPMRepairAnalysis:
    """Complete analysis result for an XPM file."""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.file_name = os.path.basename(file_path)
        self.issues: List[XPMStructuralIssue] = []
        self.needs_repair = False
        self.is_repairable = True
        self.confidence_score = 0.0
        self.metadata = {}
    
    def add_issue(self, issue: XPMStructuralIssue):
        """Add an issue to the analysis."""
        self.issues.append(issue)
        if issue.severity in ["critical", "high"]:
            self.needs_repair = True
    
    def get_critical_issues(self) -> List[XPMStructuralIssue]:
        return [issue for issue in self.issues if issue.severity == "critical"]
    
    def get_high_issues(self) -> List[XPMStructuralIssue]:
        return [issue for issue in self.issues if issue.severity == "high"]
    
    def summary(self) -> str:
        """Get a summary string of all issues."""
        if not self.issues:
            return "No issues found"
        
        critical = len(self.get_critical_issues())
        high = len(self.get_high_issues())
        total = len(self.issues)
        
        return f"{total} issues found ({critical} critical, {high} high priority)"


class XPMRepairDoctor:
    """Advanced XPM repair and analysis engine."""
    
    def __init__(self):
        self.repair_stats = {
            'analyzed': 0,
            'repaired': 0,
            'failed': 0,
            'skipped': 0
        }
        self.last_errors = []
    
    def analyze_xpm_structure(self, xpm_path: str) -> XPMRepairAnalysis:
        """Perform comprehensive structural analysis of an XPM file."""
        analysis = XPMRepairAnalysis(xpm_path)
        
        try:
            tree = ET.parse(xpm_path)
            root = tree.getroot()
            
            # Basic metadata
            analysis.metadata['file_size'] = os.path.getsize(xpm_path)
            
            # 1. Analyze instrument structure
            self._analyze_instrument_structure(root, analysis)
            
            # 2. Analyze ProgramPads structure
            self._analyze_program_pads(root, analysis)
            
            # 3. Analyze sample references
            self._analyze_sample_references(root, analysis, os.path.dirname(xpm_path))
            
            # 4. Analyze keygroup configuration
            self._analyze_keygroup_config(root, analysis)
            
            # 5. Analyze version compatibility
            self._analyze_version_compatibility(root, analysis)
            
            # 6. Calculate confidence score
            analysis.confidence_score = self._calculate_confidence_score(analysis)
            
            self.repair_stats['analyzed'] += 1
            
        except Exception as e:
            logging.error(f"Error analyzing {xpm_path}: {e}")
            analysis.add_issue(XPMStructuralIssue(
                "analysis_error", f"Failed to analyze file: {str(e)}", "critical"
            ))
            analysis.is_repairable = False
        
        return analysis
    
    def _analyze_instrument_structure(self, root: ET.Element, analysis: XPMRepairAnalysis):
        """Analyze instrument structure for bloat and issues."""
        instruments = root.findall(".//Instrument")
        total_instruments = len(instruments)
        
        analysis.metadata['total_instruments'] = total_instruments
        
        # Count instruments with actual samples
        instruments_with_samples = 0
        empty_instruments = []
        
        for i, instrument in enumerate(instruments):
            has_samples = False
            layers = instrument.findall(".//Layer")
            
            for layer in layers:
                sample_file = layer.find("SampleFile")
                sample_name = layer.find("SampleName")
                
                if ((sample_file is not None and sample_file.text and sample_file.text.strip()) or
                    (sample_name is not None and sample_name.text and sample_name.text.strip())):
                    has_samples = True
                    instruments_with_samples += 1
                    break
            
            if not has_samples:
                empty_instruments.append(i + 1)
        
        analysis.metadata['instruments_with_samples'] = instruments_with_samples
        analysis.metadata['empty_instruments'] = len(empty_instruments)
        
        # Detect structural bloat
        if total_instruments >= 100:
            if instruments_with_samples < (total_instruments * 0.3):  # Less than 30% have samples
                analysis.add_issue(XPMStructuralIssue(
                    "structural_bloat",
                    f"Structural bloat detected: {len(empty_instruments)} empty instruments out of {total_instruments}",
                    "critical",
                    "rebuild_with_correct_structure",
                    {"empty_count": len(empty_instruments), "sample_count": instruments_with_samples}
                ))
        
        # Check for excessive empty instruments
        elif len(empty_instruments) > (total_instruments * 0.8):  # More than 80% empty
            analysis.add_issue(XPMStructuralIssue(
                "excessive_empty_instruments",
                f"Too many empty instruments: {len(empty_instruments)}/{total_instruments}",
                "high",
                "cleanup_empty_instruments"
            ))
        
        # Check for no instruments with samples
        if instruments_with_samples == 0:
            analysis.add_issue(XPMStructuralIssue(
                "no_sample_instruments",
                "No instruments contain sample references",
                "critical",
                "rebuild_from_samples"
            ))
    
    def _analyze_program_pads(self, root: ET.Element, analysis: XPMRepairAnalysis):
        """Analyze ProgramPads structure and mapping."""
        pads_elem = root.find(".//ProgramPads-v2.10")
        if pads_elem is None:
            pads_elem = root.find(".//ProgramPads")
        
        if pads_elem is None or not pads_elem.text:
            analysis.add_issue(XPMStructuralIssue(
                "missing_program_pads",
                "Missing ProgramPads data - required for MPC recognition",
                "critical",
                "regenerate_program_pads"
            ))
            return
        
        try:
            json_text = xml_unescape(pads_elem.text)
            pads_data = json.loads(json_text)
            
            # Check structure
            if not isinstance(pads_data, dict):
                analysis.add_issue(XPMStructuralIssue(
                    "invalid_program_pads_structure",
                    "ProgramPads JSON has invalid structure",
                    "high",
                    "rebuild_program_pads"
                ))
                return
            
            # Check for padToInstrument mapping
            if 'padToInstrument' not in pads_data:
                analysis.add_issue(XPMStructuralIssue(
                    "missing_pad_to_instrument_mapping",
                    "Missing padToInstrument mapping",
                    "high",
                    "rebuild_pad_mapping"
                ))
            
            # Check pads structure
            pads = None
            if "ProgramPads-v2.10" in pads_data and "pads" in pads_data["ProgramPads-v2.10"]:
                pads = pads_data["ProgramPads-v2.10"]["pads"]
            elif "pads" in pads_data:
                pads = pads_data["pads"]
            
            if not pads:
                analysis.add_issue(XPMStructuralIssue(
                    "missing_pads_data",
                    "Missing pads data in ProgramPads",
                    "high",
                    "rebuild_pads_data"
                ))
            else:
                # Count active pads
                active_pads = 0
                for pad_key, pad_data in pads.items():
                    if isinstance(pad_data, dict) and pad_data.get("sampleName"):
                        active_pads += 1
                
                analysis.metadata['active_pads'] = active_pads
                
                # Check if pad count matches instrument count
                instrument_count = analysis.metadata.get('instruments_with_samples', 0)
                if active_pads != instrument_count and instrument_count > 0:
                    analysis.add_issue(XPMStructuralIssue(
                        "pad_instrument_mismatch",
                        f"Pad count ({active_pads}) doesn't match instruments with samples ({instrument_count})",
                        "medium",
                        "sync_pad_instrument_counts"
                    ))
        
        except json.JSONDecodeError as e:
            analysis.add_issue(XPMStructuralIssue(
                "invalid_program_pads_json",
                f"Invalid ProgramPads JSON: {str(e)}",
                "high",
                "rebuild_program_pads"
            ))
    
    def _analyze_sample_references(self, root: ET.Element, analysis: XPMRepairAnalysis, xpm_dir: str):
        """Analyze sample file references and availability."""
        sample_refs = []
        missing_samples = []
        
        # Collect all sample references
        for elem in root.findall(".//SampleFile"):
            if elem.text and elem.text.strip():
                sample_refs.append(elem.text.strip())
        
        for elem in root.findall(".//SampleName"):
            if elem.text and elem.text.strip():
                sample_name = elem.text.strip()
                if not sample_name.endswith('.wav'):
                    sample_name += '.wav'
                sample_refs.append(sample_name)
        
        analysis.metadata['total_sample_refs'] = len(sample_refs)
        
        # Check sample availability
        for sample_ref in sample_refs:
            sample_path = os.path.join(xpm_dir, sample_ref)
            if not os.path.exists(sample_path):
                missing_samples.append(sample_ref)
        
        analysis.metadata['missing_samples'] = len(missing_samples)
        
        if missing_samples:
            severity = "critical" if len(missing_samples) == len(sample_refs) else "medium"
            analysis.add_issue(XPMStructuralIssue(
                "missing_sample_files",
                f"{len(missing_samples)} sample files are missing",
                severity,
                "relink_or_remove_missing_samples",
                {"missing_files": missing_samples}
            ))
    
    def _analyze_keygroup_config(self, root: ET.Element, analysis: XPMRepairAnalysis):
        """Analyze keygroup configuration and ranges."""
        # Check declared keygroup count
        kg_count_elem = root.find(".//KeygroupNumKeygroups")
        declared_count = 0
        
        if kg_count_elem is not None and kg_count_elem.text:
            try:
                declared_count = int(kg_count_elem.text)
            except ValueError:
                analysis.add_issue(XPMStructuralIssue(
                    "invalid_keygroup_count",
                    "Invalid KeygroupNumKeygroups value",
                    "medium",
                    "fix_keygroup_count"
                ))
        
        analysis.metadata['declared_keygroup_count'] = declared_count
        actual_instruments = analysis.metadata.get('instruments_with_samples', 0)
        
        # Check for count mismatch
        if declared_count != actual_instruments and actual_instruments > 0:
            analysis.add_issue(XPMStructuralIssue(
                "keygroup_count_mismatch",
                f"Declared keygroup count ({declared_count}) doesn't match actual instruments ({actual_instruments})",
                "medium",
                "sync_keygroup_count"
            ))
        
        # Check key ranges
        instruments = root.findall(".//Instrument")
        range_issues = 0
        
        for instrument in instruments:
            low_note_elem = instrument.find("LowNote")
            high_note_elem = instrument.find("HighNote")
            
            if low_note_elem is not None and high_note_elem is not None:
                try:
                    low_note = int(low_note_elem.text) if low_note_elem.text else 0
                    high_note = int(high_note_elem.text) if high_note_elem.text else 127
                    
                    # Check for problematic ranges
                    if (low_note == high_note or  # Single note
                        high_note < 84 or         # Limited range (less than C6)
                        low_note > high_note):    # Invalid range
                        range_issues += 1
                        
                except (ValueError, TypeError):
                    range_issues += 1
        
        if range_issues > 0:
            analysis.add_issue(XPMStructuralIssue(
                "keygroup_range_issues",
                f"{range_issues} instruments have problematic key ranges",
                "medium",
                "expand_key_ranges"
            ))
    
    def _analyze_version_compatibility(self, root: ET.Element, analysis: XPMRepairAnalysis):
        """Analyze version compatibility and format issues."""
        version_elem = root.find(".//Version")
        if version_elem is not None:
            file_version_elem = version_elem.find("File_Version")
            app_version_elem = version_elem.find("Application_Version")
            
            if file_version_elem is not None and file_version_elem.text:
                file_version = file_version_elem.text
                analysis.metadata['file_version'] = file_version
                
                # Check for old format
                if file_version in ["1.0", "1.1"]:
                    analysis.add_issue(XPMStructuralIssue(
                        "outdated_file_format",
                        f"Old file format version ({file_version}) - should be updated",
                        "low",
                        "update_file_version"
                    ))
    
    def _calculate_confidence_score(self, analysis: XPMRepairAnalysis) -> float:
        """Calculate confidence score for successful repair (0.0 to 1.0)."""
        if not analysis.is_repairable:
            return 0.0
        
        score = 1.0
        
        # Deduct points based on severity
        for issue in analysis.issues:
            if issue.severity == "critical":
                score -= 0.3
            elif issue.severity == "high":
                score -= 0.2
            elif issue.severity == "medium":
                score -= 0.1
            elif issue.severity == "low":
                score -= 0.05
        
        # Boost score if we have samples
        if analysis.metadata.get('instruments_with_samples', 0) > 0:
            score += 0.2
        
        return max(0.0, min(1.0, score))
    
    def repair_xpm_file(self, xpm_path: str, analysis: XPMRepairAnalysis = None, 
                       create_backup: bool = True) -> bool:
        """Repair an XPM file based on analysis or auto-analyze."""
        try:
            if analysis is None:
                analysis = self.analyze_xpm_structure(xpm_path)
            
            if not analysis.needs_repair:
                logging.info(f"✅ {analysis.file_name} - No repair needed")
                self.repair_stats['skipped'] += 1
                return True
            
            if not analysis.is_repairable:
                logging.error(f"❌ {analysis.file_name} - Not repairable")
                self.repair_stats['failed'] += 1
                return False
            
            # Create backup
            if create_backup:
                backup_path = xpm_path + ".broken.backup"
                if not os.path.exists(backup_path):
                    shutil.copy2(xpm_path, backup_path)
                    logging.info(f"Created backup: {os.path.basename(backup_path)}")
            
            # Apply fixes based on issues found
            success = False
            
            # Check for critical structural issues that require rebuild
            critical_issues = analysis.get_critical_issues()
            structural_issues = [issue for issue in critical_issues 
                               if issue.issue_type in ["structural_bloat", "no_sample_instruments"]]
            
            if structural_issues:
                success = self._rebuild_xpm_structure(xpm_path, analysis)
            else:
                success = self._apply_targeted_fixes(xpm_path, analysis)
            
            if success:
                logging.info(f"✅ Successfully repaired {analysis.file_name}")
                self.repair_stats['repaired'] += 1
                return True
            else:
                logging.error(f"❌ Failed to repair {analysis.file_name}")
                self.repair_stats['failed'] += 1
                return False
                
        except Exception as e:
            error_msg = f"Error repairing {os.path.basename(xpm_path)}: {str(e)}"
            logging.error(error_msg)
            self.last_errors.append(error_msg)
            self.repair_stats['failed'] += 1
            return False
    
    def _rebuild_xpm_structure(self, xpm_path: str, analysis: XPMRepairAnalysis) -> bool:
        """Rebuild XPM with correct structure using InstrumentBuilder."""
        if not IMPORTS_SUCCESSFUL:
            logging.error("Cannot rebuild - required modules not available")
            return False
        
        try:
            # Extract sample mappings from broken file
            mappings, params = _parse_xpm_for_rebuild(xpm_path)
            
            if not mappings:
                logging.error(f"No sample mappings could be extracted from {analysis.file_name}")
                return False
            
            # Filter valid samples
            valid_mappings = []
            for mapping in mappings:
                if os.path.exists(mapping['sample_path']):
                    valid_mappings.append(mapping)
                else:
                    logging.warning(f"Sample not found: {mapping['sample_path']}")
            
            if not valid_mappings:
                logging.error(f"No valid samples found for {analysis.file_name}")
                return False
            
            # Create rebuild options
            options = InstrumentOptions(
                firmware_version="2.12.1",  # Latest stable
                format_version="advanced",  # Modern format
                polyphony=64,
                creative_mode="off"
            )
            
            # Create dummy app for builder
            class DummyApp:
                def __init__(self):
                    self.root = None
                    class PolyphonyVar:
                        def get(self):
                            return 64
                    self.polyphony_var = PolyphonyVar()
            
            dummy_app = DummyApp()
            output_folder = os.path.dirname(xpm_path)
            builder = InstrumentBuilder(output_folder, dummy_app, options)
            
            # Get program name
            program_name = params.get('ProgramName', os.path.splitext(analysis.file_name)[0])
            
            # Rebuild the XPM
            success = builder._create_xpm(
                program_name=program_name,
                sample_files=[],  # Using mappings instead
                output_folder=output_folder,
                mode="multi-sample",
                mappings=valid_mappings,
                instrument_template=params
            )
            
            if success:
                logging.info(f"Rebuilt {analysis.file_name} with {len(valid_mappings)} samples")
                return True
            else:
                logging.error(f"InstrumentBuilder failed for {analysis.file_name}")
                return False
                
        except Exception as e:
            logging.error(f"Error during rebuild of {analysis.file_name}: {e}")
            return False
    
    def _apply_targeted_fixes(self, xpm_path: str, analysis: XPMRepairAnalysis) -> bool:
        """Apply targeted fixes for specific issues."""
        try:
            tree = ET.parse(xpm_path)
            root = tree.getroot()
            modified = False
            
            for issue in analysis.issues:
                if issue.fix_method == "fix_keygroup_count":
                    if self._fix_keygroup_count(root, analysis):
                        modified = True
                        
                elif issue.fix_method == "expand_key_ranges":
                    if self._fix_key_ranges(root):
                        modified = True
                        
                elif issue.fix_method == "update_file_version":
                    if self._update_file_version(root):
                        modified = True
            
            if modified:
                indent_tree(tree)
                tree.write(xpm_path, encoding="utf-8", xml_declaration=True)
                return True
            
            return True  # No modifications needed
            
        except Exception as e:
            logging.error(f"Error applying targeted fixes: {e}")
            return False
    
    def _fix_keygroup_count(self, root: ET.Element, analysis: XPMRepairAnalysis) -> bool:
        """Fix keygroup count mismatch."""
        try:
            kg_count_elem = root.find(".//KeygroupNumKeygroups")
            actual_count = analysis.metadata.get('instruments_with_samples', 0)
            
            if kg_count_elem is not None:
                kg_count_elem.text = str(actual_count)
                return True
            
            return False
        except Exception:
            return False
    
    def _fix_key_ranges(self, root: ET.Element) -> bool:
        """Fix problematic key ranges."""
        try:
            instruments = root.findall(".//Instrument")
            modified = False
            
            for instrument in instruments:
                low_note_elem = instrument.find("LowNote")
                high_note_elem = instrument.find("HighNote")
                
                if low_note_elem is not None and high_note_elem is not None:
                    try:
                        low_note = int(low_note_elem.text) if low_note_elem.text else 0
                        high_note = int(high_note_elem.text) if high_note_elem.text else 127
                        
                        # Fix problematic ranges
                        if (low_note == high_note or high_note < 84 or low_note > high_note):
                            low_note_elem.text = "0"    # C0
                            high_note_elem.text = "127" # G9
                            modified = True
                            
                    except (ValueError, TypeError):
                        low_note_elem.text = "0"
                        high_note_elem.text = "127"
                        modified = True
            
            return modified
        except Exception:
            return False
    
    def _update_file_version(self, root: ET.Element) -> bool:
        """Update file version to modern format."""
        try:
            version_elem = root.find(".//Version")
            if version_elem is not None:
                file_version_elem = version_elem.find("File_Version")
                if file_version_elem is not None:
                    file_version_elem.text = "2.1"
                    return True
            return False
        except Exception:
            return False
    
    def batch_repair_folder(self, folder_path: str, create_backups: bool = True) -> Dict:
        """Repair all XPM files in a folder."""
        if not os.path.isdir(folder_path):
            raise ValueError(f"Invalid folder path: {folder_path}")
        
        # Reset stats
        self.repair_stats = {
            'analyzed': 0,
            'repaired': 0,
            'failed': 0,
            'skipped': 0
        }
        self.last_errors = []
        
        # Find XPM files
        xpm_files = []
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith('.xpm') and not file.startswith('._'):
                    xpm_files.append(os.path.join(root, file))
        
        if not xpm_files:
            return {'error': 'No XPM files found', **self.repair_stats}
        
        logging.info(f"Found {len(xpm_files)} XPM files to analyze")
        
        # Analyze and repair
        analyses = []
        for xpm_path in xpm_files:
            try:
                analysis = self.analyze_xpm_structure(xpm_path)
                analyses.append(analysis)
                
                if analysis.needs_repair:
                    self.repair_xpm_file(xpm_path, analysis, create_backups)
                else:
                    self.repair_stats['skipped'] += 1
                    
            except Exception as e:
                error_msg = f"Error processing {os.path.basename(xpm_path)}: {str(e)}"
                logging.error(error_msg)
                self.last_errors.append(error_msg)
                self.repair_stats['failed'] += 1
        
        # Compile results
        results = {
            'total_files': len(xpm_files),
            'analyses': analyses,
            'errors': self.last_errors,
            **self.repair_stats
        }
        
        return results


class XPMRepairDoctorGUI(tk.Toplevel):
    """GUI interface for the XPM Repair Doctor."""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.doctor = XPMRepairDoctor()
        self.current_analyses = []
        
        self.title("XPM Repair Doctor - Advanced Structural Repair")
        self.geometry("1000x700")
        self.transient(parent)
        
        self.create_widgets()
        
        # Center the window
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
    
    def create_widgets(self):
        """Create the GUI widgets."""
        # Main frame
        main_frame = ttk.Frame(self)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Title
        title_label = ttk.Label(main_frame, text="XPM Repair Doctor", 
                               font=('Arial', 16, 'bold'))
        title_label.pack(pady=(0, 10))
        
        # Subtitle
        subtitle_label = ttk.Label(main_frame, 
                                  text="Advanced structural repair for broken XPM files",
                                  font=('Arial', 10))
        subtitle_label.pack(pady=(0, 20))
        
        # Control frame
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill='x', pady=(0, 10))
        
        # Folder selection
        folder_frame = ttk.Frame(control_frame)
        folder_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(folder_frame, text="Folder:").pack(side='left')
        self.folder_var = tk.StringVar()
        self.folder_entry = ttk.Entry(folder_frame, textvariable=self.folder_var, 
                                     state='readonly')
        self.folder_entry.pack(side='left', fill='x', expand=True, padx=(5, 5))
        
        ttk.Button(folder_frame, text="Browse", 
                  command=self.browse_folder).pack(side='right')
        
        # Action buttons
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Button(button_frame, text="Analyze All", 
                  command=self.analyze_folder).pack(side='left', padx=(0, 5))
        ttk.Button(button_frame, text="Repair All", 
                  command=self.repair_all).pack(side='left', padx=(0, 5))
        ttk.Button(button_frame, text="Repair Selected", 
                  command=self.repair_selected).pack(side='left', padx=(0, 20))
        
        # Options
        options_frame = ttk.Frame(button_frame)
        options_frame.pack(side='right')
        
        self.backup_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Create Backups", 
                       variable=self.backup_var).pack(side='left')
        
        # Results frame
        results_frame = ttk.Frame(main_frame)
        results_frame.pack(fill='both', expand=True)
        
        # Treeview for results
        columns = ('File', 'Status', 'Issues', 'Confidence', 'Actions')
        self.tree = ttk.Treeview(results_frame, columns=columns, show='headings', height=15)
        
        # Define headings
        self.tree.heading('#1', text='File Name')
        self.tree.heading('#2', text='Status')
        self.tree.heading('#3', text='Issues Found')
        self.tree.heading('#4', text='Repair Confidence')
        self.tree.heading('#5', text='Recommended Action')
        
        # Configure columns
        self.tree.column('#1', width=200)
        self.tree.column('#2', width=100)
        self.tree.column('#3', width=300)
        self.tree.column('#4', width=120)
        self.tree.column('#5', width=150)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(results_frame, orient='vertical', command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(results_frame, orient='horizontal', command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack treeview and scrollbars
        self.tree.pack(side='left', fill='both', expand=True)
        v_scrollbar.pack(side='right', fill='y')
        h_scrollbar.pack(side='bottom', fill='x')
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, 
                              relief='sunken', anchor='w')
        status_bar.pack(fill='x', pady=(10, 0))
        
        # Bind double-click for details
        self.tree.bind('<Double-1>', self.show_details)
    
    def browse_folder(self):
        """Browse for folder containing XPM files."""
        folder = filedialog.askdirectory(
            title="Select folder containing XPM files",
            initialdir=self.folder_var.get() or os.getcwd()
        )
        if folder:
            self.folder_var.set(folder)
    
    def analyze_folder(self):
        """Analyze all XPM files in the selected folder."""
        folder = self.folder_var.get()
        if not folder or not os.path.isdir(folder):
            messagebox.showerror("Error", "Please select a valid folder first.")
            return
        
        # Clear previous results
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        self.current_analyses = []
        self.status_var.set("Analyzing XPM files...")
        self.update()
        
        try:
            # Find XPM files
            xpm_files = []
            for root, dirs, files in os.walk(folder):
                for file in files:
                    if file.lower().endswith('.xpm') and not file.startswith('._'):
                        xpm_files.append(os.path.join(root, file))
            
            if not xpm_files:
                messagebox.showinfo("No Files", "No XPM files found in the selected folder.")
                self.status_var.set("Ready")
                return
            
            # Analyze each file
            for i, xpm_path in enumerate(xpm_files):
                self.status_var.set(f"Analyzing {i+1}/{len(xpm_files)}: {os.path.basename(xpm_path)}")
                self.update()
                
                try:
                    analysis = self.doctor.analyze_xpm_structure(xpm_path)
                    self.current_analyses.append(analysis)
                    
                    # Determine status
                    if not analysis.is_repairable:
                        status = "Not Repairable"
                    elif analysis.needs_repair:
                        critical_count = len(analysis.get_critical_issues())
                        if critical_count > 0:
                            status = f"Needs Repair ({critical_count} critical)"
                        else:
                            status = "Needs Repair"
                    else:
                        status = "Good"
                    
                    # Format issues
                    issues_text = analysis.summary()
                    
                    # Format confidence
                    confidence_text = f"{analysis.confidence_score:.1%}"
                    
                    # Recommended action
                    if not analysis.is_repairable:
                        action = "Manual Fix Required"
                    elif len(analysis.get_critical_issues()) > 0:
                        action = "Rebuild Structure"
                    elif analysis.needs_repair:
                        action = "Apply Fixes"
                    else:
                        action = "No Action Needed"
                    
                    # Add to tree
                    self.tree.insert('', 'end', values=(
                        analysis.file_name,
                        status,
                        issues_text,
                        confidence_text,
                        action
                    ))
                    
                except Exception as e:
                    # Add error entry
                    self.tree.insert('', 'end', values=(
                        os.path.basename(xpm_path),
                        "Analysis Error",
                        f"Error: {str(e)}",
                        "0.0%",
                        "Check File"
                    ))
            
            self.status_var.set(f"Analysis complete. Found {len(xpm_files)} XPM files.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error during analysis: {str(e)}")
            self.status_var.set("Ready")
    
    def repair_all(self):
        """Repair all files that need repair."""
        if not self.current_analyses:
            messagebox.showwarning("No Analysis", "Please analyze the folder first.")
            return
        
        files_to_repair = [analysis for analysis in self.current_analyses 
                          if analysis.needs_repair and analysis.is_repairable]
        
        if not files_to_repair:
            messagebox.showinfo("Nothing to Repair", "No files require repair.")
            return
        
        if not messagebox.askyesno("Confirm Repair", 
                                  f"This will repair {len(files_to_repair)} XPM files. Continue?"):
            return
        
        self._repair_files(files_to_repair)
    
    def repair_selected(self):
        """Repair selected files."""
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("No Selection", "Please select files to repair.")
            return
        
        # Get analyses for selected items
        selected_analyses = []
        for item in selected_items:
            index = self.tree.index(item)
            if index < len(self.current_analyses):
                analysis = self.current_analyses[index]
                if analysis.needs_repair and analysis.is_repairable:
                    selected_analyses.append(analysis)
        
        if not selected_analyses:
            messagebox.showinfo("Nothing to Repair", "Selected files don't require repair.")
            return
        
        if not messagebox.askyesno("Confirm Repair", 
                                  f"This will repair {len(selected_analyses)} selected XPM files. Continue?"):
            return
        
        self._repair_files(selected_analyses)
    
    def _repair_files(self, analyses_to_repair):
        """Repair the specified analyses."""
        total = len(analyses_to_repair)
        repaired = 0
        failed = 0
        
        for i, analysis in enumerate(analyses_to_repair):
            self.status_var.set(f"Repairing {i+1}/{total}: {analysis.file_name}")
            self.update()
            
            try:
                success = self.doctor.repair_xpm_file(
                    analysis.file_path, 
                    analysis, 
                    self.backup_var.get()
                )
                
                if success:
                    repaired += 1
                else:
                    failed += 1
                    
            except Exception as e:
                logging.error(f"Error repairing {analysis.file_name}: {e}")
                failed += 1
        
        # Show results
        result_msg = f"Repair complete!\n\nRepaired: {repaired}\nFailed: {failed}"
        if failed == 0:
            messagebox.showinfo("Repair Complete", result_msg)
        else:
            messagebox.showwarning("Repair Complete with Errors", result_msg)
        
        self.status_var.set("Ready")
        
        # Re-analyze to update status
        if repaired > 0:
            self.analyze_folder()
    
    def show_details(self, event):
        """Show detailed analysis for selected file."""
        item = self.tree.selection()[0]
        index = self.tree.index(item)
        
        if index < len(self.current_analyses):
            analysis = self.current_analyses[index]
            self._show_analysis_details(analysis)
    
    def _show_analysis_details(self, analysis: XPMRepairAnalysis):
        """Show detailed analysis window."""
        details_window = tk.Toplevel(self)
        details_window.title(f"Analysis Details - {analysis.file_name}")
        details_window.geometry("600x500")
        details_window.transient(self)
        
        # Create text widget with scrollbar
        frame = ttk.Frame(details_window)
        frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        text_widget = tk.Text(frame, wrap='word')
        scrollbar = ttk.Scrollbar(frame, orient='vertical', command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Format analysis details
        details = f"File: {analysis.file_name}\n"
        details += f"Path: {analysis.file_path}\n"
        details += f"Needs Repair: {'Yes' if analysis.needs_repair else 'No'}\n"
        details += f"Is Repairable: {'Yes' if analysis.is_repairable else 'No'}\n"
        details += f"Confidence Score: {analysis.confidence_score:.1%}\n\n"
        
        details += "METADATA:\n"
        details += "-" * 40 + "\n"
        for key, value in analysis.metadata.items():
            details += f"{key}: {value}\n"
        
        details += "\nISSUES FOUND:\n"
        details += "-" * 40 + "\n"
        if not analysis.issues:
            details += "No issues found.\n"
        else:
            for issue in analysis.issues:
                details += f"\n[{issue.severity.upper()}] {issue.issue_type}\n"
                details += f"Description: {issue.description}\n"
                if issue.fix_method:
                    details += f"Fix Method: {issue.fix_method}\n"
                if issue.details:
                    details += f"Details: {issue.details}\n"
        
        text_widget.insert('1.0', details)
        text_widget.configure(state='disabled')


def main(args=None):
    """Command line interface for XPM Repair Doctor."""
    if args is None:
        # Legacy support - try to get from sys.argv
        if len(sys.argv) < 2:
            print("XPM Repair Doctor - Advanced Structural Repair Tool")
            print("=" * 50)
            print()
            print("Usage:")
            print("  python xpm_repair_doctor.py <file_or_folder> [options]")
            print()
            print("Options:")
            print("  --analyze-only    Only analyze, don't repair")
            print("  --no-backup      Don't create backup files")
            print("  --verbose        Verbose output")
            print()
            print("Examples:")
            print("  python xpm_repair_doctor.py broken_file.xpm")
            print("  python xpm_repair_doctor.py /path/to/xpm/folder")
            print("  python xpm_repair_doctor.py folder --analyze-only")
            sys.exit(1)
        
        path = sys.argv[1]
        analyze_only = "--analyze-only" in sys.argv
        create_backups = "--no-backup" not in sys.argv
    else:
        # New argparse support
        if not args.path:
            print("No path specified. Use --help for usage information.")
            sys.exit(1)
            
        path = args.path
        analyze_only = not args.repair
        create_backups = not args.no_backup
    verbose = "--verbose" in sys.argv
    
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    doctor = XPMRepairDoctor()
    
    if os.path.isfile(path) and path.lower().endswith('.xpm'):
        # Single file processing
        print(f"🔍 Analyzing {os.path.basename(path)}...")
        
        analysis = doctor.analyze_xpm_structure(path)
        
        print(f"\n📋 Analysis Results for {analysis.file_name}:")
        print(f"   Needs Repair: {'Yes' if analysis.needs_repair else 'No'}")
        print(f"   Is Repairable: {'Yes' if analysis.is_repairable else 'No'}")
        print(f"   Confidence Score: {analysis.confidence_score:.1%}")
        print(f"   Issues: {analysis.summary()}")
        
        if analysis.issues:
            print(f"\n📝 Detailed Issues:")
            for issue in analysis.issues:
                print(f"   • [{issue.severity.upper()}] {issue.description}")
        
        if not analyze_only and analysis.needs_repair:
            print(f"\n🔧 Repairing {analysis.file_name}...")
            success = doctor.repair_xpm_file(path, analysis, create_backups)
            if success:
                print(f"✅ Successfully repaired {analysis.file_name}")
            else:
                print(f"❌ Failed to repair {analysis.file_name}")
                sys.exit(1)
        elif not analysis.needs_repair:
            print(f"✅ {analysis.file_name} is in good condition")
    
    elif os.path.isdir(path):
        # Folder processing
        print(f"🔍 Scanning folder: {path}")
        
        results = doctor.batch_repair_folder(path, create_backups and not analyze_only)
        
        print(f"\n📊 Results Summary:")
        print(f"   Total files: {results['total_files']}")
        print(f"   Analyzed: {results['analyzed']}")
        print(f"   Needed repair: {results['analyzed'] - results['skipped']}")
        
        if not analyze_only:
            print(f"   Successfully repaired: {results['repaired']}")
            print(f"   Failed to repair: {results['failed']}")
        
        if results['errors']:
            print(f"\n⚠️  Errors encountered:")
            for error in results['errors'][:5]:  # Show first 5 errors
                print(f"   • {error}")
            if len(results['errors']) > 5:
                print(f"   ... and {len(results['errors']) - 5} more errors")
        
        # Show analyses for files needing repair
        repair_needed = [a for a in results['analyses'] if a.needs_repair]
        if repair_needed:
            print(f"\n📋 Files requiring repair:")
            for analysis in repair_needed[:10]:  # Show first 10
                print(f"   • {analysis.file_name}: {analysis.summary()}")
            if len(repair_needed) > 10:
                print(f"   ... and {len(repair_needed) - 10} more files")
    
    else:
        print(f"❌ Path not found or not an XPM file: {path}")
        sys.exit(1)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="XPM Repair Doctor - Analyze and repair broken XPM files")
    parser.add_argument('path', nargs='?', help='Path to XPM file or folder to analyze/repair')
    parser.add_argument('--gui', action='store_true', help='Launch GUI interface')
    parser.add_argument('--batch', action='store_true', help='Batch process folder')
    parser.add_argument('--repair', action='store_true', help='Actually repair files (default: analyze only)')
    parser.add_argument('--no-backup', action='store_true', help='Skip creating backup files')
    
    args = parser.parse_args()
    
    if args.gui or (not args.path):
        # Launch GUI
        try:
            root = tk.Tk()
            root.withdraw()  # Hide main window
            app = XPMRepairDoctorGUI(root)
            app.mainloop()
        except Exception as e:
            print(f"GUI launch failed: {e}")
            print("Install tkinter for GUI support or use command line interface.")
            if args.path:
                main(args)
    else:
        # Command line interface
        main(args)
