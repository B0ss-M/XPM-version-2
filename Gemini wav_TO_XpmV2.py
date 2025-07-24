import tkinter as tk
import os
import shutil
import glob
import wave
import logging
import traceback
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape as xml_escape, unescape as xml_unescape
import random
import sys
import subprocess
import threading
from dataclasses import dataclass, field
from tkinter import ttk, filedialog, messagebox
from tkinter.ttk import Treeview
from collections import defaultdict
import struct
import re
import json
from typing import Optional, Dict, List, Tuple, Any, Union
from contextlib import contextmanager
import functools
import time
import zipfile
from typing import Optional

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None

try:
    from PIL import Image

    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

# Attempt to import optional dependencies, handle if they are not present
try:
    from audio_pitch import detect_fundamental_pitch
    from xpm_parameter_editor import (
        set_layer_keytrack,
        set_volume_adsr,
        load_mod_matrix,
        apply_mod_matrix,
        set_engine_mode,
        set_application_version,
        fix_sample_notes,
        fix_master_transpose,
        find_program_pads,
        infer_note_from_filename,
        extract_root_note_from_wav,
    )
    from drumkit_grouping import group_similar_files
    from multi_sample_builder import MultiSampleBuilderWindow, AUDIO_EXTS
    from sample_mapping_editor import SampleMappingEditorWindow
    from sample_mapping_checker import SampleMappingCheckerWindow
    from firmware_profiles import (
        get_pad_settings,
        get_program_parameters as fw_program_parameters,
        ADVANCED_INSTRUMENT_PARAMS,
    )

    IMPORTS_SUCCESSFUL = True
except ImportError as e:
    IMPORTS_SUCCESSFUL = False
    MISSING_MODULE = str(e)
    # Ensure optional classes are defined to avoid NameError later
    SampleMappingEditorWindow = None
    SampleMappingCheckerWindow = None
    MultiSampleBuilderWindow = None
from xpm_utils import (
    LAYER_PARAMS_TO_PRESERVE,
    calculate_key_ranges,
    _parse_xpm_for_rebuild,
    indent_tree,
)


# --- User Experience Enhancements ---
class KeyboardShortcuts:
    """Manage keyboard shortcuts for the application."""
    
    @staticmethod
    def setup_shortcuts(window, callbacks: Dict[str, callable]):
        """
        Set up keyboard shortcuts for a window.
        
        Args:
            window: Tkinter window to bind shortcuts to
            callbacks: Dictionary mapping shortcut names to callback functions
        """
        shortcuts = {
            '<Control-o>': 'open_file',
            '<Control-s>': 'save_current',
            '<F5>': 'refresh',
            '<Control-z>': 'undo',
            '<Control-y>': 'redo',
            '<Escape>': 'cancel_operation',
            '<Control-q>': 'quit_application',
            '<Control-a>': 'select_all',
            '<Delete>': 'delete_selected',
            '<F1>': 'show_help'
        }
        
        for shortcut, action in shortcuts.items():
            if action in callbacks:
                window.bind(shortcut, lambda e, cb=callbacks[action]: cb())

class StatusManager:
    """Enhanced status management with progress indication and message history."""
    
    def __init__(self, status_var: tk.StringVar, max_history: int = 50):
        self.status_var = status_var
        self.max_history = max_history
        self.message_history = []
        self.current_operation = None
        self.operation_start_time = None
    
    def set_status(self, message: str, level: str = "info"):
        """
        Set status message with timestamp and level indication.
        
        Args:
            message: Status message to display
            level: Message level (info, warning, error, success)
        """
        # Add level indicator
        level_indicators = {
            "info": "ℹ️",
            "warning": "⚠️", 
            "error": "❌",
            "success": "✅",
            "progress": "⏳"
        }
        
        indicator = level_indicators.get(level, "ℹ️")
        formatted_message = f"{indicator} {message}"
        
        self.status_var.set(formatted_message)
        
        # Add to history with timestamp
        timestamp = time.strftime("%H:%M:%S")
        self.message_history.append(f"[{timestamp}] {formatted_message}")
        
        # Limit history size
        if len(self.message_history) > self.max_history:
            self.message_history.pop(0)
        
        # Log the status change
        logging.info(f"Status: {message}")
    
    def start_operation(self, operation_name: str):
        """Start tracking a long-running operation."""
        self.current_operation = operation_name
        self.operation_start_time = time.time()
        self.set_status(f"Starting {operation_name}...", "progress")
    
    def update_operation_progress(self, current: int, total: int, detail: str = None):
        """Update progress for current operation."""
        if not self.current_operation:
            return
        
        percentage = (current / max(total, 1)) * 100
        elapsed = time.time() - (self.operation_start_time or 0)
        
        message = f"{self.current_operation}: {current}/{total} ({percentage:.1f}%)"
        if detail:
            message += f" - {detail}"
        if elapsed > 1:  # Show timing for operations > 1 second
            message += f" | {elapsed:.1f}s"
        
        self.set_status(message, "progress")
    
    def finish_operation(self, success: bool = True, result_message: str = None):
        """Finish tracking current operation."""
        if not self.current_operation:
            return
        
        elapsed = time.time() - (self.operation_start_time or 0)
        
        if result_message:
            message = result_message
        else:
            message = f"{self.current_operation} {'completed' if success else 'failed'}"
        
        message += f" ({elapsed:.1f}s)"
        
        self.set_status(message, "success" if success else "error")
        self.current_operation = None
        self.operation_start_time = None
    
    def get_history(self) -> List[str]:
        """Get message history for debugging."""
        return self.message_history.copy()

def create_tooltip(widget, text: str):
    """
    Create a tooltip for a widget with helpful information.
    
    Args:
        widget: Tkinter widget to attach tooltip to
        text: Tooltip text to display
    """
    def show_tooltip(event):
        tooltip = tk.Toplevel()
        tooltip.wm_overrideredirect(True)
        tooltip.wm_geometry(f"+{event.x_root + 10}+{event.y_root + 10}")
        
        label = tk.Label(
            tooltip, 
            text=text, 
            background="lightyellow",
            relief="solid",
            borderwidth=1,
            font=("Arial", 9),
            justify="left"
        )
        label.pack()
        
        def hide_tooltip():
            tooltip.destroy()
        
        tooltip.after(3000, hide_tooltip)  # Auto-hide after 3 seconds
    
    def on_enter(event):
        widget.after(500, lambda: show_tooltip(event))  # Delay tooltip
    
    widget.bind("<Enter>", on_enter)

# --- Enhanced Logging & Debugging ---
def setup_detailed_logging(log_level: str = "INFO", log_file: str = None) -> logging.Logger:
    """
    Set up enhanced logging with detailed formatting and optional file output.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional file path for log output
        
    Returns:
        Configured logger instance
    """
    # Create detailed formatter
    detailed_formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(funcName)s() | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Get or create logger
    logger = logging.getLogger('XPM_Processor')
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(detailed_formatter)
    logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
            file_handler.setFormatter(detailed_formatter)
            logger.addHandler(file_handler)
            logger.info(f"Logging to file: {log_file}")
        except Exception as e:
            logger.warning(f"Could not set up file logging: {e}")
    
    return logger

def log_function_entry_exit(func):
    """
    Decorator to log function entry and exit with parameters and timing.
    Useful for debugging complex operations.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = logging.getLogger('XPM_Processor')
        func_name = func.__name__
        
        # Log entry with parameters (but limit size for readability)
        args_str = ', '.join(str(arg)[:50] + '...' if len(str(arg)) > 50 else str(arg) for arg in args)
        kwargs_str = ', '.join(f"{k}={str(v)[:30]}{'...' if len(str(v)) > 30 else ''}" for k, v in kwargs.items())
        params = ', '.join(filter(None, [args_str, kwargs_str]))
        
        logger.debug(f"→ ENTER {func_name}({params})")
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time
            logger.debug(f"← EXIT {func_name} | {elapsed:.3f}s | Success")
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.debug(f"← EXIT {func_name} | {elapsed:.3f}s | ERROR: {e}")
            raise
    
    return wrapper

def log_xml_operation(operation: str, file_path: str, details: str = None):
    """
    Log XML file operations with consistent formatting.
    
    Args:
        operation: Description of the operation (e.g., "parse", "write", "validate")
        file_path: Path to the XML file
        details: Optional additional details
    """
    logger = logging.getLogger('XPM_Processor')
    filename = os.path.basename(file_path)
    message = f"XML {operation}: {filename}"
    if details:
        message += f" | {details}"
    logger.debug(message)

# --- Input Validation & Type Safety ---
def validate_file_path(file_path: str, must_exist: bool = True) -> str:
    """
    Validate file path and return normalized path.
    
    Args:
        file_path: Path to validate
        must_exist: Whether the file must already exist
    
    Returns:
        Normalized absolute path
        
    Raises:
        FileNotFoundError: If file doesn't exist and must_exist=True
        ValueError: If path is invalid
    """
    if not file_path or not isinstance(file_path, str):
        raise ValueError("File path must be a non-empty string")
    
    normalized_path = os.path.abspath(file_path)
    
    if must_exist and not os.path.exists(normalized_path):
        raise FileNotFoundError(f"File not found: {normalized_path}")
    
    return normalized_path

def validate_midi_note(note: Union[int, str]) -> int:
    """
    Validate MIDI note number.
    
    Args:
        note: MIDI note number (0-127)
    
    Returns:
        Valid MIDI note number
        
    Raises:
        ValueError: If note is out of range
    """
    try:
        note_int = int(note)
    except (ValueError, TypeError):
        raise ValueError(f"MIDI note must be a number, got: {note}")
    
    if not 0 <= note_int <= 127:
        raise ValueError(f"MIDI note must be 0-127, got: {note_int}")
    
    return note_int

def validate_sample_mappings(mappings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Validate sample mapping data structure.
    
    Args:
        mappings: List of sample mapping dictionaries
    
    Returns:
        Validated mappings with defaults filled in
        
    Raises:
        ValueError: If mappings are invalid
    """
    if not isinstance(mappings, list):
        raise ValueError("Sample mappings must be a list")
    
    validated_mappings = []
    
    for i, mapping in enumerate(mappings):
        if not isinstance(mapping, dict):
            raise ValueError(f"Mapping {i} must be a dictionary")
        
        # Validate required fields
        if "sample_path" not in mapping:
            raise ValueError(f"Mapping {i} missing required 'sample_path'")
        
        # Validate and normalize fields
        validated_mapping = {
            "sample_path": str(mapping["sample_path"]),
            "root_note": validate_midi_note(mapping.get("root_note", 60)),
            "low_note": validate_midi_note(mapping.get("low_note", 0)),
            "high_note": validate_midi_note(mapping.get("high_note", 127)),
            "velocity_low": max(0, min(127, int(mapping.get("velocity_low", 0)))),
            "velocity_high": max(0, min(127, int(mapping.get("velocity_high", 127)))),
        }
        
        # Validate range logic
        if validated_mapping["low_note"] > validated_mapping["high_note"]:
            raise ValueError(f"Mapping {i}: low_note ({validated_mapping['low_note']}) > high_note ({validated_mapping['high_note']})")
        
        if validated_mapping["velocity_low"] > validated_mapping["velocity_high"]:
            raise ValueError(f"Mapping {i}: velocity_low > velocity_high")
        
        validated_mappings.append(validated_mapping)
    
    return validated_mappings

def validate_xpm_structure(root: ET.Element) -> bool:
    """
    Validate basic XMP file structure.
    
    Args:
        root: XML root element
    
    Returns:
        True if structure is valid
        
    Raises:
        ValueError: If structure is invalid
    """
    if root.tag != "MPCVObject":
        raise ValueError(f"Invalid root element: expected 'MPCVObject', got '{root.tag}'")
    
    program = root.find("Program")
    if program is None:
        raise ValueError("Missing Program element")
    
    program_type = program.get("type")
    if program_type not in ["Keygroup", "Drum"]:
        raise ValueError(f"Invalid program type: {program_type}")
    
    return True

# --- Enhanced Error Handling & File Safety ---
class XPMProcessingError(Exception):
    """Custom exception for XPM processing errors with context."""
    def __init__(self, message, file_path=None, original_exception=None):
        self.file_path = file_path
        self.original_exception = original_exception
        super().__init__(message)

class FileOperationError(Exception):
    """Exception for file operation failures."""
    pass

@dataclass
class ProcessingStats:
    """Track processing statistics for performance monitoring."""
    start_time: float = field(default_factory=time.time)
    files_processed: int = 0
    files_failed: int = 0
    total_size_processed: int = 0
    errors: list = field(default_factory=list)
    
    @property
    def elapsed_time(self) -> float:
        return time.time() - self.start_time
    
    @property
    def files_per_second(self) -> float:
        return self.files_processed / max(self.elapsed_time, 0.001)
    
    @property
    def success_rate(self) -> float:
        total = self.files_processed + self.files_failed
        return (self.files_processed / max(total, 1)) * 100
    
    def add_error(self, error_msg: str, file_path: str = None):
        """Add an error to the tracking list."""
        error_entry = f"{error_msg}"
        if file_path:
            error_entry = f"{os.path.basename(file_path)}: {error_msg}"
        self.errors.append(error_entry)
        self.files_failed += 1
    
    def add_success(self, file_size: int = 0):
        """Record a successful operation."""
        self.files_processed += 1
        self.total_size_processed += file_size
    
    def get_summary(self) -> str:
        """Get a formatted summary of processing statistics."""
        return (f"Processed {self.files_processed} files in {self.elapsed_time:.1f}s "
               f"({self.files_per_second:.1f} files/sec, {self.success_rate:.1f}% success)")

class ProgressTracker:
    """Track and display progress for long-running operations."""
    
    def __init__(self, total_items: int, status_callback=None):
        self.total_items = total_items
        self.completed_items = 0
        self.stats = ProcessingStats()
        self.status_callback = status_callback
        self.last_update_time = time.time()
        self.update_interval = 0.5  # Update UI every 0.5 seconds
    
    def update_progress(self, increment: int = 1, current_item: str = None):
        """Update progress and optionally refresh UI."""
        self.completed_items += increment
        
        # Throttle UI updates for performance
        current_time = time.time()
        if current_time - self.last_update_time >= self.update_interval:
            self._update_ui(current_item)
            self.last_update_time = current_time
    
    def _update_ui(self, current_item: str = None):
        """Update the UI with current progress."""
        if self.status_callback:
            progress_percent = (self.completed_items / max(self.total_items, 1)) * 100
            status_msg = f"Processing {self.completed_items}/{self.total_items} ({progress_percent:.1f}%)"
            if current_item:
                status_msg += f" - {current_item}"
            self.status_callback(status_msg)
    
    def finish(self) -> str:
        """Mark processing as finished and return summary."""
        if self.status_callback:
            summary = self.stats.get_summary()
            self.status_callback(f"Complete: {summary}")
        return self.stats.get_summary()

@contextmanager
def safe_xml_operation(file_path, create_backup=True):
    """
    Context manager for safe XML operations with automatic backup, rollback, and detailed logging.
    
    Args:
        file_path: Path to the file being modified
        create_backup: Whether to create a backup before modification
    """
    backup_path = None
    if create_backup:
        backup_path = f"{file_path}.temp_backup_{int(time.time())}"
    
    filename = os.path.basename(file_path)
    
    try:
        # Create backup if requested
        if create_backup and os.path.exists(file_path):
            shutil.copy2(file_path, backup_path)
            log_xml_operation("backup_created", file_path, f"→ {os.path.basename(backup_path)}")
        
        log_xml_operation("operation_start", file_path)
        yield file_path
        
        # If we reach here, operation was successful - remove backup
        if backup_path and os.path.exists(backup_path):
            os.remove(backup_path)
            log_xml_operation("operation_complete", file_path, "backup removed")
        else:
            log_xml_operation("operation_complete", file_path)
            
    except Exception as e:
        # Operation failed - restore from backup if it exists
        if backup_path and os.path.exists(backup_path):
            if os.path.exists(file_path):
                os.remove(file_path)
            shutil.move(backup_path, file_path)
            log_xml_operation("operation_failed", file_path, f"restored from backup: {e}")
        else:
            log_xml_operation("operation_failed", file_path, str(e))
        
        # Re-raise with enhanced context
        raise XPMProcessingError(
            f"Failed to process {filename}: {e}",
            file_path=file_path,
            original_exception=e
        ) from e

def retry_on_failure(max_retries=3, delay=1.0, backoff_factor=2.0):
    """
    Decorator for retrying failed operations with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff_factor: Multiplier for delay on each retry
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt == max_retries:
                        logging.error(f"Function {func.__name__} failed after {max_retries} retries: {e}")
                        break
                    
                    logging.warning(f"Function {func.__name__} failed on attempt {attempt + 1}, retrying in {current_delay:.1f}s: {e}")
                    time.sleep(current_delay)
                    current_delay *= backoff_factor
            
            # All retries exhausted
            raise last_exception
        
        return wrapper
    return decorator

# --- Application Configuration ---
APP_VERSION = "24.1"  # Final Stable Release with Pitch Fix

# --- Global Constants ---
MPC_BEIGE = "#EAE6DA"
MPC_DARK_GREY = "#414042"
MPC_PAD_GREY = "#7B7C7D"
MPC_RED = "#B91C1C"
MPC_WHITE = "#FFFFFF"
SCW_FRAME_THRESHOLD = 5000
CREATIVE_FILTER_TYPE_MAP = {"LPF": "0", "HPF": "2", "BPF": "1"}
EXPANSION_IMAGE_SIZE = (600, 600)  # default icon size


# <editor-fold desc="Logging and Core Helpers">
class TextHandler(logging.Handler):
    """This handler sends logging records to a Tkinter Text widget."""

    def __init__(self, text_widget):
        logging.Handler.__init__(self)
        self.text_widget = text_widget

    def emit(self, record):
        """Safely write log messages to the associated Text widget."""
        try:
            msg = self.format(record)
        except Exception as exc:  # pragma: no cover - formatting errors are rare
            print(f"Logging format error: {exc}", file=sys.stderr)
            return

        if not msg:
            return

        msg = str(msg)

        def append():
            try:
                if msg and self.text_widget and self.text_widget.winfo_exists():
                    self.text_widget.configure(state="normal")
                    self.text_widget.insert(tk.END, msg + "\n")
                    self.text_widget.configure(state="disabled")
                    self.text_widget.yview(tk.END)
            except Exception as exc:
                # Fallback to stderr if the Tk widget is unavailable
                print(f"Text widget error: {exc}", file=sys.stderr)

        if self.text_widget and self.text_widget.winfo_exists():
            self.text_widget.after_idle(append)
        else:
            print(msg)


def build_program_pads_json(
    firmware, mappings=None, engine_override=None, num_instruments=None
):
    """Return ProgramPads JSON escaped for XML embedding.

    ``num_instruments`` is used to populate the ``padToInstrument``
    mapping so the MPC knows exactly how many keygroups are defined.
    """
    if not IMPORTS_SUCCESSFUL:
        return "{}"
    pad_cfg = get_pad_settings(firmware, engine_override)
    pads_type = pad_cfg["type"]
    universal_pad = pad_cfg["universal_pad"]
    engine = pad_cfg.get("engine")

    pads = {f"value{i}": 0 for i in range(128)}
    if mappings:
        for m in mappings:
            try:
                # For instruments, the pad index is less important than the key ranges.
                # Using the rootNote is a reasonable default.
                pad_index = int(m.get("root_note", 0))
                if 0 <= pad_index < 128:
                    if not isinstance(pads[f"value{pad_index}"], dict):
                        pads[f"value{pad_index}"] = {}
                    pads[f"value{pad_index}"] = {
                        "samplePath": m.get("sample_path", ""),
                        "rootNote": int(m.get("root_note", 60)),
                        "lowNote": int(m.get("low_note", 0)),
                        "highNote": int(m.get("high_note", 127)),
                        "velocityLow": int(m.get("velocity_low", 0)),
                        "velocityHigh": int(m.get("velocity_high", 127)),
                    }
            except (ValueError, TypeError):
                logging.warning(f"Could not process mapping: {m}")

    pads_obj = {
        "Universal": {"value0": True},
        "Type": {"value0": pads_type},
        "universalPad": universal_pad,
        "pads": pads,
        "UnusedPads": {"value0": 1},
        "PadsFollowTrackColour": {"value0": False},
    }
    if engine:
        pads_obj["engine"] = engine
    if isinstance(num_instruments, int) and num_instruments > 0:
        pads_obj["padToInstrument"] = {str(i): i for i in range(num_instruments)}
    json_str = json.dumps(pads_obj, indent=4)
    return xml_escape(json_str)


def validate_xpm_file(xpm_path, expected_samples):
    """
    Validate a generated XPM file. It checks for the modern ProgramPads section
    first. If that's not found, it falls back to checking for the legacy
    Instruments section. This ensures both modern and legacy-formatted XPMs
    can be validated correctly.
    
    Also verifies that KeygroupNumKeygroups matches the actual instrument count.
    """
    try:
        with open(xpm_path, "r", encoding="utf-8") as f:
            xml_text = f.read()
        root = ET.fromstring(xml_text)
        
        # Check if KeygroupNumKeygroups is consistent with actual instruments
        kg_count_elem = root.find(".//KeygroupNumKeygroups")
        instruments = root.findall(".//Instruments/Instrument")
        actual_kg_count = len(instruments)
        
        if kg_count_elem is not None:
            declared_kg_count = int(kg_count_elem.text)
            if declared_kg_count != actual_kg_count:
                logging.warning(
                    f"Keygroup count mismatch in {os.path.basename(xpm_path)}: "
                    f"Declared {declared_kg_count}, but found {actual_kg_count} instruments."
                )
                # Fix the count
                kg_count_elem.text = str(actual_kg_count)
                tree = ET.ElementTree(root)
                tree.write(xpm_path, encoding="utf-8", xml_declaration=True)
                logging.info(f"Fixed keygroup count in {os.path.basename(xpm_path)}.")

        # Check for modern ProgramPads section
        pads_elem = find_program_pads(root)
        if pads_elem is not None and pads_elem.text:
            # If it exists, validate its contents
            json_text = xml_unescape(pads_elem.text)
            data = json.loads(json_text)
            pads = data.get("pads", {})
            entries = [
                v for v in pads.values() if isinstance(v, dict) and v.get("samplePath")
            ]
            
            # Also check if padToInstrument mapping is correct
            if 'padToInstrument' in data:
                pad_to_inst = data['padToInstrument']
                if len(pad_to_inst) != actual_kg_count:
                    logging.warning(
                        f"padToInstrument mapping mismatch in {os.path.basename(xpm_path)}: "
                        f"Found {len(pad_to_inst)} entries, but {actual_kg_count} instruments."
                    )

            if expected_samples > 0 and len(entries) == 0:
                logging.warning(
                    f"Validation failed for {os.path.basename(xpm_path)}: ProgramPads exists but has no sample entries."
                )
                return False

            logging.info(
                f"Modern validation successful for {os.path.basename(xpm_path)}."
            )
            return True

        # If ProgramPads is missing, search for legacy style sample references
        inst_root = root.find(".//Instruments")
        if inst_root is not None:
            if (
                inst_root.find(".//SampleFile") is not None
                or inst_root.find(".//SampleName") is not None
            ):
                logging.info(
                    f"Legacy validation successful for {os.path.basename(xpm_path)} (found Instruments section)."
                )
                return True

        # Final fallback: look for any SampleFile tags anywhere in the document
        if (
            root.find(".//SampleFile") is not None
            or root.find(".//SampleName") is not None
        ):
            logging.info(
                f"Legacy validation successful for {os.path.basename(xpm_path)} (found sample references)."
            )
            return True

        # If neither is found, then it's a real failure.
        logging.warning(
            f"Validation failed for {os.path.basename(xpm_path)}: Neither ProgramPads nor Instruments section found."
        )
        return False

    except Exception as e:
        logging.error(f"XPM validation error for {os.path.basename(xpm_path)}: {e}")
        return False


def get_clean_sample_info(filepath):
    """Extracts basic info from a file path."""
    base = os.path.basename(filepath)
    folder = os.path.basename(os.path.dirname(filepath))
    name, ext = os.path.splitext(base)
    note = infer_note_from_filename(base)
    return {"base": name, "ext": ext, "note": note, "folder": folder}


def get_instrument_category_from_text(text):
    """Returns a known instrument tag if it appears in the provided text."""
    tags = [
        "piano",
        "bell",
        "pad",
        "keys",
        "guitar",
        "bass",
        "lead",
        "pluck",
        "drum",
        "fx",
        "vocal",
        "ambient",
        "brass",
        "strings",
        "woodwind",
        "world",
        "horn",
    ]
    lower = text.lower()
    for tag in tags:
        if tag in lower:
            return tag
    return None


def get_base_instrument_name(filepath, xpm_content=None):
    """Returns an instrument tag based on the path or optional XPM contents."""
    if xpm_content:
        category = get_instrument_category_from_text(xpm_content)
        if category:
            return category

    tags = [
        "piano",
        "bell",
        "pad",
        "keys",
        "guitar",
        "bass",
        "lead",
        "pluck",
        "drum",
        "fx",
        "vocal",
        "ambient",
        "brass",
        "strings",
        "woodwind",
        "world",
        "horn",
    ]
    path = filepath.lower()
    for tag in tags:
        if tag in path:
            return tag
    parent_folder = os.path.basename(os.path.dirname(filepath))
    cleaned_folder = re.sub(r"[_-]", " ", parent_folder).strip()
    return cleaned_folder if cleaned_folder else "instrument"


def get_wav_frames(filepath):
    """Returns the number of frames in a WAV file."""
    try:
        with wave.open(filepath, "rb") as w:
            return w.getnframes()
    except Exception:
        return 0


def parse_xpm_samples(xpm_path):
    """Return a list of sample paths referenced by an XPM."""
    samples = []
    try:
        tree = ET.parse(xpm_path)
        root = tree.getroot()

        pads_elem = find_program_pads(root)
        if pads_elem is not None and pads_elem.text:
            try:
                data = json.loads(xml_unescape(pads_elem.text))
            except json.JSONDecodeError as e:
                logging.error(f"JSON decode error in {xpm_path}: {e}")
                data = {}
            pads = data.get("pads", {})
            for pad in pads.values():
                if isinstance(pad, dict) and pad.get("samplePath"):
                    samples.append(pad["samplePath"])

        for elem in root.findall(".//SampleName"):
            if elem.text:
                samples.append(elem.text + ".wav")

        for elem in root.findall(".//SampleFile"):
            if elem.text:
                samples.append(elem.text)
    except Exception as e:
        logging.error(f"Could not parse samples from {xpm_path}: {e}")
    return samples


def get_xpm_version(xpm_path):
    """Return Application_Version string from an XPM or 'Unknown'."""
    try:
        tree = ET.parse(xpm_path)
        ver = tree.find(".//Application_Version")
        if ver is not None and ver.text:
            return ver.text
    except Exception as e:
        logging.error(f"Version parse failed for {xpm_path}: {e}")
    return "Unknown"


def is_valid_xpm(xpm_path):
    """Basic validity check using validate_xpm_file."""
    sample_count = len(parse_xpm_samples(xpm_path))
    return validate_xpm_file(xpm_path, sample_count)


# --- ENHANCED: detect_sample_note with improved accuracy and validation ---
@retry_on_failure(max_retries=2, delay=0.5)
def detect_sample_note(path: str) -> int:
    """
    Return the MIDI note for a sample using metadata, filename, or pitch analysis.
    Enhanced with cross-validation and improved accuracy.
    
    Args:
        path: Path to the audio sample file
        
    Returns:
        MIDI note number (0-127)
        
    Raises:
        FileNotFoundError: If sample file doesn't exist
        ValueError: If path is invalid
    """
    # Validate input
    validated_path = validate_file_path(path, must_exist=True)
    filename = os.path.basename(validated_path)

    # Store all detection results for cross-validation
    detection_results = []

    # 1. Try reading from WAV 'smpl' chunk metadata
    try:
        from xpm_parameter_editor import extract_root_note_from_wav
        midi = extract_root_note_from_wav(validated_path)
        if midi is not None:
            validated_midi = validate_midi_note(midi)
            detection_results.append(('wav_metadata', validated_midi))
            logging.debug(f"WAV metadata note for '{filename}': {validated_midi}")
    except Exception as e:
        logging.debug(f"WAV metadata extraction failed for '{filename}': {e}")

    # 2. Try inferring from the filename (often most reliable for user-named files)
    try:
        from xpm_parameter_editor import infer_note_from_filename
        midi = infer_note_from_filename(validated_path)
        if midi is not None:
            validated_midi = validate_midi_note(midi)
            detection_results.append(('filename', validated_midi))
            logging.debug(f"Filename inference note for '{filename}': {validated_midi}")
    except Exception as e:
        logging.debug(f"Filename inference failed for '{filename}': {e}")

    # 3. Try audio analysis (fallback)
    try:
        midi = detect_fundamental_pitch(validated_path)
        if midi is not None:
            validated_midi = validate_midi_note(midi)
            detection_results.append(('audio_analysis', validated_midi))
            logging.debug(f"Audio analysis note for '{filename}': {validated_midi}")
    except Exception as e:
        logging.debug(f"Pitch analysis failed for '{filename}': {e}")

    # 4. Intelligent selection of best result
    if not detection_results:
        logging.warning(f"All detection methods failed for '{filename}'. Defaulting to C4 (60).")
        return 60
    
    # If we have multiple results, use intelligent selection
    if len(detection_results) == 1:
        method, note = detection_results[0]
        logging.info(f"Note for '{filename}' detected via {method}: {note}")
        return note
    
    # Multiple results - use cross-validation logic
    selected_note = _select_best_pitch_detection(detection_results, filename)
    return selected_note


def _select_best_pitch_detection(results, filename):
    """
    Intelligently select the best pitch detection result from multiple methods.
    
    Args:
        results: List of (method_name, midi_note) tuples
        filename: Name of the file for logging
        
    Returns:
        int: Best MIDI note number
    """
    if not results:
        return 60  # Default to C4
    
    if len(results) == 1:
        method, note = results[0]
        logging.info(f"Note for '{filename}' detected via {method}: {note}")
        return note
    
    # Create a map of methods to notes
    method_notes = {method: note for method, note in results}
    
    # Priority order (most reliable first)
    priority_order = ['filename', 'audio_analysis', 'wav_metadata']
    
    # Check for consensus (notes within 1 semitone of each other)
    notes = [note for _, note in results]
    
    # If filename detection exists and is reasonable, prefer it
    if 'filename' in method_notes:
        filename_note = method_notes['filename']
        
        # Check if other methods are close to filename detection
        close_methods = []
        for method, note in results:
            if abs(note - filename_note) <= 2:  # Within 2 semitones
                close_methods.append((method, note))
        
        if len(close_methods) >= 2:  # At least filename + one other method agree
            logging.info(f"Note for '{filename}' - filename detection ({filename_note}) confirmed by other methods")
            return filename_note
    
    # Check for exact consensus
    if len(set(notes)) == 1:
        note = notes[0]
        methods = [method for method, _ in results]
        logging.info(f"Note for '{filename}' - all methods agree: {note} (methods: {', '.join(methods)})")
        return note
    
    # Check for majority consensus (within 1 semitone)
    for target_note in set(notes):
        close_notes = [note for note in notes if abs(note - target_note) <= 1]
        if len(close_notes) >= len(notes) * 0.6:  # 60% consensus
            methods = [method for method, note in results if abs(note - target_note) <= 1]
            logging.info(f"Note for '{filename}' - majority consensus: {target_note} (methods: {', '.join(methods)})")
            return target_note
    
    # No consensus - use priority order
    for method in priority_order:
        if method in method_notes:
            note = method_notes[method]
            other_methods = [m for m, _ in results if m != method]
            logging.warning(f"Note for '{filename}' - no consensus, using {method}: {note} (other methods: {other_methods})")
            return note
    
    # Fallback
    method, note = results[0]
    logging.warning(f"Note for '{filename}' - fallback to first result ({method}): {note}")
    return note


# REVISED: Stricter unreferenced file finder
def find_unreferenced_audio_files(xpm_path, mappings):
    """
    Return a list of audio files in the same folder that are not referenced
    in the mappings AND are intelligently linked to the XPM by name.
    """
    xpm_dir = os.path.dirname(xpm_path)
    program_name = os.path.splitext(os.path.basename(xpm_path))[0]

    # Guard against invalid or hidden file names
    if not program_name or program_name.startswith("."):
        logging.warning(
            f"Skipping unreferenced file search for invalid program name: '{program_name}'"
        )
        return []

    program_name_lower = program_name.lower()
    potential_files = []
    try:
        for f in os.listdir(xpm_dir):
            f_lower = f.lower()
            if os.path.splitext(f_lower)[1] in AUDIO_EXTS:
                # More precise matching:
                # 1. Exact match (e.g., 'Program.wav' for 'Program.xpm')
                # 2. Match followed by a common separator
                if (
                    os.path.splitext(f_lower)[0] == program_name_lower
                    or f_lower.startswith(program_name_lower + " ")
                    or f_lower.startswith(program_name_lower + "_")
                    or f_lower.startswith(program_name_lower + "-")
                ):
                    potential_files.append(f)
    except Exception as e:
        logging.error(f"Error scanning for unreferenced files in {xpm_dir}: {e}")
        return []

    used = {os.path.basename(m.get("sample_path", "")).lower() for m in mappings}
    unreferenced = [
        os.path.join(xpm_dir, f) for f in potential_files if f.lower() not in used
    ]
    logging.info(
        f"Found {len(unreferenced)} potential unreferenced files for {program_name}"
    )
    return unreferenced


# </editor-fold>


# <editor-fold desc="GUI: Utility Windows">
# RESTORED: All utility window classes are now included.
class ExpansionDoctorWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master.root if hasattr(master, "root") else master)
        self.title("Expansion Doctor - Enhanced")
        self.geometry("700x450")
        self.resizable(True, True)
        self.master = master
        self.format_var = tk.StringVar(value="advanced")
        self.status = tk.StringVar(value="Ready.")
        self.version_var = tk.StringVar(value=master.firmware_version.get())
        self.format_var = tk.StringVar(value="advanced")
        self.broken_links = {}
        self.file_info = {}
        
        # Enhanced status management
        self.status_manager = StatusManager(self.status)
        
        # Set up keyboard shortcuts
        shortcuts = {
            'refresh': self.scan_broken_links,
            'select_all': self.select_all_files,
            'cancel_operation': self.cancel_current_operation,
            'show_help': self.show_help
        }
        KeyboardShortcuts.setup_shortcuts(self, shortcuts)
        
        self.create_widgets()
        self.status_manager.set_status("Expansion Doctor ready", "success")
        self.scan_broken_links()
    
    def select_all_files(self):
        """Select all files in the tree view."""
        for item in self.tree.get_children():
            self.tree.selection_add(item)
        self.status_manager.set_status(f"Selected all {len(self.tree.get_children())} files", "info")
    
    def cancel_current_operation(self):
        """Cancel any running operation."""
        self.status_manager.set_status("Operation cancelled by user", "warning")
    
    def show_help(self):
        """Show help dialog with keyboard shortcuts."""
        help_text = """
Expansion Doctor - Keyboard Shortcuts:

F5 - Refresh/Rescan files
Ctrl+A - Select all files  
Esc - Cancel current operation
F1 - Show this help

Double-click file - Show detailed issues
Right-click - Context menu (coming soon)

Expansion Doctor fixes:
• Structural bloat (empty instruments)
• Keygroup count mismatches
• Key range issues (C5→C6,C7,C8 access)
• Missing sample links
• Version inconsistencies
• Pad mapping problems
        """
        messagebox.showinfo("Expansion Doctor Help", help_text, parent=self)

    def create_widgets(self):
        frame = ttk.Frame(self, padding="10")
        frame.pack(fill="both", expand=True)
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        self.status_label = ttk.Label(frame, textvariable=self.status)
        self.status_label.grid(row=0, column=0, sticky="ew", pady=(0, 5))

        tree_frame = ttk.Frame(frame)
        tree_frame.grid(row=1, column=0, sticky="nsew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        self.tree = Treeview(
            tree_frame,
            columns=("XPM", "Version", "Valid", "Issues"),
            show="headings",
        )
        self.tree.heading("XPM", text="XPM File")
        self.tree.heading("Version", text="Version")
        self.tree.heading("Valid", text="Valid")
        self.tree.heading("Issues", text="Issues Detected")
        self.tree.column("XPM", width=250)
        self.tree.column("Version", width=80, anchor="center")
        self.tree.column("Valid", width=60, anchor="center")
        self.tree.column("Issues", width=350)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        # Add double-click event to show detailed issue information
        self.tree.bind("<Double-1>", self.show_detailed_issues)

        option_frame = ttk.Frame(frame)
        option_frame.grid(row=2, column=0, sticky="ew", pady=(5, 0))
        ttk.Label(option_frame, text="Firmware:").pack(side="left")
        ttk.Combobox(
            option_frame,
            textvariable=self.version_var,
            values=["2.3.0.0", "2.6.0.17", "3.4.0", "3.5.0"],
            width=10,
            state="readonly",
        ).pack(side="left", padx=5)
        ttk.Label(option_frame, text="Format:").pack(side="left")
        ttk.Combobox(
            option_frame,
            textvariable=self.format_var,
            values=["legacy", "advanced"],
            width=8,
            state="readonly",
        ).pack(side="left", padx=5)

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=3, column=0, sticky="ew", pady=(5, 0))
        
        # Row 1: Main fix buttons
        ttk.Button(
            btn_frame, text="🔧 Batch Fix All Issues", command=self.batch_fix_all_issues, 
            style="Accent.TButton"
        ).pack(side="left", padx=5)
        ttk.Button(
            btn_frame, text="🔢 Fix Keygroup Counts", command=self.fix_keygroup_counts
        ).pack(side="left", padx=5)
        ttk.Button(
            btn_frame, text="🎹 Fix Key Ranges", command=self.fix_key_ranges
        ).pack(side="left", padx=5)
        
        # Row 2: Specific fix buttons  
        btn_frame2 = ttk.Frame(frame)
        btn_frame2.grid(row=4, column=0, sticky="ew", pady=(5, 0))
        ttk.Button(
            btn_frame2, text="🔗 Relink Samples...", command=self.relink_samples
        ).pack(side="left", padx=5)
        ttk.Button(
            btn_frame2, text="📋 Fix Pad Mappings", command=self.fix_pad_mappings
        ).pack(side="left", padx=5)
        ttk.Button(btn_frame2, text="Fix Keygroups", command=self.fix_keygroups).pack(
            side="left", padx=5
        )
        
        # Row 3: Version and control buttons
        options = ttk.Frame(btn_frame2)
        options.pack(side="left", padx=10)
        ttk.Label(options, text="Format:").pack(side="left")
        ttk.Combobox(
            options,
            textvariable=self.format_var,
            values=["legacy", "advanced"],
            state="readonly",
            width=9,
        ).pack(side="left")
        ttk.Button(btn_frame2, text="Rewrite Versions", command=self.fix_versions).pack(
            side="left", padx=5
        )
        ttk.Button(btn_frame2, text="📊 Rescan", command=self.scan_broken_links).pack(
            side="left", padx=5
        )
        ttk.Button(btn_frame2, text="Close", command=self.destroy).pack(
            side="right", padx=5
        )

    def relink_samples(self):
        if not self.broken_links:
            messagebox.showinfo(
                "No Broken Links", "There are no broken links to relink.", parent=self
            )
            return

        folder = filedialog.askdirectory(
            parent=self, title="Select Folder Containing Missing Samples"
        )
        if not folder:
            return

        fixed_count = 0
        for xpm_path, missing_list in self.broken_links.items():
            try:
                tree = ET.parse(xpm_path)
                root = tree.getroot()
                changed = False

                samples_to_find = set(missing_list)

                for elem in root.findall(".//SampleFile"):
                    if elem is not None and elem.text:
                        sample_basename = os.path.basename(
                            elem.text.replace("/", os.sep)
                        )
                        if sample_basename in samples_to_find:
                            for f in os.listdir(folder):
                                if f.lower() == sample_basename.lower():
                                    dest_path = os.path.join(
                                        os.path.dirname(xpm_path), sample_basename
                                    )
                                    shutil.copy2(os.path.join(folder, f), dest_path)
                                    logging.info(
                                        f"Relinked '{sample_basename}' to '{dest_path}' for {xpm_path}"
                                    )
                                    changed = True
                                    samples_to_find.remove(sample_basename)
                                    break
                if changed:
                    indent_tree(tree)
                    tree.write(xpm_path, encoding="utf-8", xml_declaration=True)
                    fixed_count += 1
            except Exception as e:
                logging.error(f"Error relinking samples for {xpm_path}: {e}")

        self.status.set(f"Relinked samples for {fixed_count} XPM(s). Rescanning...")
        self.scan_broken_links()

    def fix_versions(self):
        folder = self.master.folder_path.get()
        if not folder or not os.path.isdir(folder):
            messagebox.showerror("Error", "No valid folder selected.", parent=self)
            return
        target_fw = self.version_var.get()
        target_fmt = self.format_var.get()

        params = {"rename": False, "version": target_fw, "format_version": target_fmt}
        updated = batch_edit_programs(folder, params)

        self.status.set(
            f"Updated {updated} XPM(s) to version {target_fw} ({target_fmt}). Rescanning..."
        )
        self.scan_broken_links()

    def fix_keygroups(self):
        folder = self.master.folder_path.get()
        if not folder or not os.path.isdir(folder):
            messagebox.showerror("Error", "No valid folder selected.", parent=self)
            return

        firmware = self.version_var.get()
        fmt = self.format_var.get()
        fixed = 0

        for path in glob.glob(os.path.join(folder, "**", "*.xpm"), recursive=True):
            try:
                mappings, inst_params = _parse_xpm_for_rebuild(path)
                if not mappings:
                    continue

                program_name = os.path.splitext(os.path.basename(path))[0]
                extras = find_unreferenced_audio_files(path, mappings)
                for wav_path in extras:
                    if (
                        os.path.basename(wav_path)
                        .lower()
                        .startswith(program_name.lower())
                    ):
                        midi = detect_sample_note(wav_path)
                        mappings.append(
                            {
                                "sample_path": wav_path,
                                "root_note": midi,
                                "low_note": midi,
                                "high_note": midi,
                                "velocity_low": 0,
                                "velocity_high": 127,
                            }
                        )

                ranges = {(m["low_note"], m["high_note"]) for m in mappings}
                keygroup_count = len(ranges)
                declared = int(inst_params.get("KeygroupNumKeygroups", keygroup_count))
                needs_rebuild = (
                    declared != keygroup_count
                    or (len(ranges) == 1 and len(mappings) > 1)
                    or extras
                )
                if not needs_rebuild:
                    continue

                new_maps = []
                for m in mappings:
                    note = detect_sample_note(m["sample_path"])
                    if note is None:
                        note = m.get("root_note", 60)
                    new_maps.append(
                        {
                            "sample_path": m["sample_path"],
                            "root_note": note,
                            "low_note": note,
                            "high_note": note,
                            "velocity_low": m.get("velocity_low", 0),
                            "velocity_high": m.get("velocity_high", 127),
                        }
                    )

                options = InstrumentOptions(
                    firmware_version=firmware,
                    polyphony=self.master.polyphony_var.get(),
                    format_version=fmt,
                )
                builder = InstrumentBuilder(os.path.dirname(path), self.master, options)
                shutil.copy2(path, path + ".kgfix.bak")
                if builder._create_xpm(
                    program_name,
                    [],
                    os.path.dirname(path),
                    mode="multi-sample",
                    mappings=new_maps,
                    instrument_template=inst_params,
                ):
                    fixed += 1
            except Exception as exc:
                logging.error(f"Keygroup fix failed for {path}: {exc}")

        messagebox.showinfo("Keygroup Fixer", f"Fixed {fixed} program(s).", parent=self)
        self.scan_broken_links()

    def _apply_format(self, root, fmt):
        changed = False
        program = root.find("Program")
        if program is None:
            return changed

        keygroup_mode = program.find("KeygroupLegacyMode")
        if keygroup_mode is not None:
            val = "True" if fmt == "legacy" else "False"
            if keygroup_mode.text != val:
                keygroup_mode.text = val
                changed = True

        pads_elem = find_program_pads(program)
        if pads_elem is not None and pads_elem.text:
            try:
                data = json.loads(xml_unescape(pads_elem.text))
                target_engine = "legacy" if fmt == "legacy" else "advanced"
                if data.get("engine") != target_engine:
                    data["engine"] = target_engine
                    pads_elem.text = xml_escape(json.dumps(data, indent=4))
                    changed = True
            except Exception as e:
                logging.error(f"_apply_format JSON error: {e}")

        return changed

    def categorize_issue_summary(self, issues_list):
        """Create an intelligent summary of issues with priorities and counts."""
        if not issues_list:
            return []
            
        # Count issues by category
        categories = {
            "🔥 Critical Bloat": 0,
            "⚠️ Performance": 0,
            "KG Count": 0,
            "Key Range": 0,
            "Missing Samples": 0,
            "Pad Mapping": 0,
            "Version": 0,
            "Format Error": 0,
            "Engine": 0,
            "Note Setup": 0,
            "Config Issue": 0
        }
        
        # Categorize each issue
        for issue in issues_list:
            if "🔥" in issue or "BLOAT" in issue.upper() or "CRITICAL" in issue.upper():
                categories["🔥 Critical Bloat"] += 1
            elif "⚠️" in issue or "SEVERE" in issue or "MODERATE" in issue:
                categories["⚠️ Performance"] += 1
            elif "KeygroupNumKeygroups" in issue or "Missing KeygroupNumKeygroups" in issue:
                categories["KG Count"] += 1
            elif any(x in issue for x in ["LowNote", "HighNote", "KG"]) and any(x in issue for x in ["Missing", "Invalid", "range", "notes"]):
                categories["Key Range"] += 1
            elif "Missing samples" in issue:
                categories["Missing Samples"] += 1
            elif "PadToInstrument" in issue or "Pad Mapping" in issue:
                categories["Pad Mapping"] += 1
            elif "version" in issue.lower():
                categories["Version"] += 1
            elif "JSON" in issue or "Corrupted" in issue or "Parse error" in issue:
                categories["Format Error"] += 1
            elif "engine" in issue.lower():
                categories["Engine"] += 1
            elif any(x in issue for x in ["polyphony", "Polyphony", "root", "Root", "note"]):
                categories["Note Setup"] += 1
            else:
                categories["Config Issue"] += 1
        
        # Build summary with counts for categories that have issues
        summary = []
        priority_order = ["🔥 Critical Bloat", "⚠️ Performance", "Missing Samples", "KG Count", 
                         "Key Range", "Pad Mapping", "Format Error", "Version", "Engine", 
                         "Note Setup", "Config Issue"]
        
        for category in priority_order:
            count = categories[category]
            if count > 0:
                if count == 1:
                    summary.append(category)
                else:
                    summary.append(f"{category} ({count})")
        
        return summary

    def analyze_xpm_issues(self, xpm_path):
        """Comprehensive analysis of XPM file issues."""
        issues = []
        fixes = []
        
        try:
            tree = ET.parse(xpm_path)
            root = tree.getroot()
            
            # Issue 1: Check KeygroupNumKeygroups vs actual instrument count
            kg_count_elem = root.find(".//KeygroupNumKeygroups")
            instruments = root.findall(".//Instrument")
            actual_kg_count = len(instruments)
            declared_kg_count = 0
            
            if kg_count_elem is not None and kg_count_elem.text:
                declared_kg_count = int(kg_count_elem.text)
                if declared_kg_count != actual_kg_count:
                    issues.append(f"KeygroupNumKeygroups mismatch: declared {declared_kg_count}, found {actual_kg_count}")
                    fixes.append("fix_keygroup_count")
            else:
                issues.append("Missing KeygroupNumKeygroups element")
                fixes.append("fix_keygroup_count")
            
            # CRITICAL ISSUE: Check for structural bloat (MPC Live 2 compatibility)
            if actual_kg_count >= 50:  # Suspicious number of instruments
                instruments_with_samples = 0
                for instrument in instruments:
                    has_samples = False
                    layers = instrument.find("Layers")
                    if layers is not None:
                        for layer in layers.findall("Layer"):
                            sample_name_elem = layer.find("SampleName")
                            sample_file_elem = layer.find("SampleFile")
                            if ((sample_name_elem is not None and sample_name_elem.text and sample_name_elem.text.strip()) or
                                (sample_file_elem is not None and sample_file_elem.text and sample_file_elem.text.strip())):
                                has_samples = True
                                break
                    if has_samples:
                        instruments_with_samples += 1
                
                empty_instruments = actual_kg_count - instruments_with_samples
                if empty_instruments > 10:
                    # Calculate performance impact
                    bloat_ratio = (empty_instruments / actual_kg_count) * 100
                    estimated_size_mb = (actual_kg_count * 20) / 1024  # Rough estimate
                    
                    issues.append(f"🔥 CRITICAL BLOAT: {empty_instruments}/{actual_kg_count} empty instruments "
                                f"({bloat_ratio:.0f}% bloat, ~{estimated_size_mb:.1f}MB wasted)")
                    fixes.append("fix_structural_bloat")
                    
                    # Additional context for user understanding
                    if empty_instruments >= 100:
                        issues.append("⚠️ SEVERE: This level of bloat causes significant MPC Live 2 performance issues")
                    elif empty_instruments >= 50:
                        issues.append("⚠️ MODERATE: Noticeable performance impact on MPC Live 2")
            elif actual_kg_count == 128 and declared_kg_count < 20:
                # Special case: exactly 128 instruments with few declared = classic bloat pattern
                issues.append("🔥 CLASSIC BLOAT PATTERN: 128 instruments created for few keygroups (Expansion Doctor issue)")
                fixes.append("fix_structural_bloat")
            
            # Issue 2: Check LowNote/HighNote ranges in keygroups
            keygroup_issues = []
            for i, instrument in enumerate(instruments):
                low_note_elem = instrument.find("LowNote")
                high_note_elem = instrument.find("HighNote")
                
                if low_note_elem is None or high_note_elem is None:
                    keygroup_issues.append(f"KG{i+1}: Missing LowNote/HighNote")
                    if "fix_keygroup_ranges" not in fixes:
                        fixes.append("fix_keygroup_ranges")
                else:
                    try:
                        low_note = int(low_note_elem.text) if low_note_elem.text else 0
                        high_note = int(high_note_elem.text) if high_note_elem.text else 127
                        
                        if low_note > high_note:
                            keygroup_issues.append(f"KG{i+1}: LowNote ({low_note}) > HighNote ({high_note})")
                            if "fix_keygroup_ranges" not in fixes:
                                fixes.append("fix_keygroup_ranges")
                        elif low_note == high_note == 0:
                            keygroup_issues.append(f"KG{i+1}: Both notes set to 0")
                            if "fix_keygroup_ranges" not in fixes:
                                fixes.append("fix_keygroup_ranges")
                        elif low_note < 0 or high_note > 127:
                            keygroup_issues.append(f"KG{i+1}: Notes out of MIDI range (0-127)")
                            if "fix_keygroup_ranges" not in fixes:
                                fixes.append("fix_keygroup_ranges")
                    except (ValueError, TypeError):
                        keygroup_issues.append(f"KG{i+1}: Invalid note values")
                        if "fix_keygroup_ranges" not in fixes:
                            fixes.append("fix_keygroup_ranges")
            
            if keygroup_issues:
                issues.extend(keygroup_issues)
            
            # Issue 3: Check for missing sample files
            missing_samples = set()
            for elem in root.findall(".//SampleFile"):
                if elem is not None and elem.text:
                    normalized_rel_path = elem.text.replace("/", os.sep)
                    sample_abs_path = os.path.normpath(
                        os.path.join(os.path.dirname(xpm_path), normalized_rel_path)
                    )
                    if not os.path.exists(sample_abs_path):
                        missing_samples.add(os.path.basename(elem.text))
            
            if missing_samples:
                issues.append(f"Missing samples: {', '.join(sorted(missing_samples))}")
                fixes.append("fix_missing_samples")
            
            # Issue 4: Check ProgramPads consistency (modern format)
            pads_elem = root.find(".//ProgramPads-v2.10")
            if pads_elem is None:
                pads_elem = root.find(".//ProgramPads")
            if pads_elem is not None and pads_elem.text:
                try:
                    pads_data = json.loads(xml_unescape(pads_elem.text))
                    if isinstance(pads_data, dict):
                        # Check padToInstrument mapping
                        pad_to_inst = pads_data.get("padToInstrument", {})
                        if len(pad_to_inst) != actual_kg_count:
                            issues.append(f"PadToInstrument mapping mismatch: {len(pad_to_inst)} entries for {actual_kg_count} keygroups")
                            fixes.append("fix_pad_mapping")
                except (json.JSONDecodeError, TypeError):
                    issues.append("Corrupted ProgramPads JSON data")
                    fixes.append("fix_pad_mapping")
            
            # Issue 5: Check version consistency
            version = get_xpm_version(xpm_path)
            if version == "Unknown":
                issues.append("Missing or invalid version information")
                fixes.append("fix_version")
            
            return {
                "issues": issues,
                "fixes": fixes,
                "keygroup_count": actual_kg_count,
                "declared_count": declared_kg_count,
                "missing_samples": sorted(list(missing_samples)),
                "version": version
            }
            
        except Exception as e:
            return {
                "issues": [f"Parse error: {str(e)}"],
                "fixes": [],
                "keygroup_count": 0,
                "declared_count": 0,
                "missing_samples": [],
                "version": "Unknown"
            }

    def scan_broken_links(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        self.broken_links.clear()
        self.file_info.clear()
        folder = self.master.folder_path.get()
        if not folder or not os.path.isdir(folder):
            self.status.set("No folder selected.")
            return

        xpms = glob.glob(os.path.join(folder, "**", "*.xpm"), recursive=True)
        total = len(xpms)
        issues_found = 0

        for xpm_path in xpms:
            # Use comprehensive analysis
            analysis = self.analyze_xpm_issues(xpm_path)
            
            # Create summary of issues for display
            issue_summary = []
            if analysis["issues"]:
                issues_found += 1
                # Use the improved categorization function
                issue_summary = self.categorize_issue_summary(analysis["issues"])
            
            # Display in tree
            self.tree.insert(
                "",
                "end",
                values=(
                    os.path.relpath(xpm_path, folder),
                    analysis["version"],
                    "No" if analysis["issues"] else "Yes",
                    ", ".join(issue_summary) if issue_summary else "OK",
                ),
                tags=("issue",) if analysis["issues"] else ("ok",)
            )
            
            # Store detailed info
            self.file_info[xpm_path] = analysis
            if analysis["missing_samples"]:
                self.broken_links[xpm_path] = analysis["missing_samples"]

        # Configure colors for different issue types
        self.tree.tag_configure("issue", foreground="red")
        self.tree.tag_configure("ok", foreground="green")

        # Finish operation with detailed summary
        if issues_found > 0:
            # Count issue types across all files
            all_issue_categories = []
            for file_info in self.file_info.values():
                if file_info["issues"]:
                    all_issue_categories.extend(self.categorize_issue_summary(file_info["issues"]))
            
            # Count unique categories
            category_counts = {}
            for category in all_issue_categories:
                # Remove count suffix for aggregation
                base_category = category.split(" (")[0] if " (" in category else category
                category_counts[base_category] = category_counts.get(base_category, 0) + 1
            
            # Create a comprehensive status message
            most_common = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            issue_types = [f"{cat} ({count})" if count > 1 else cat for cat, count in most_common]
            
            result_msg = f"Scanned {total} XPM files - {issues_found} with issues"
            if len(self.broken_links) > 0:
                result_msg += f", {len(self.broken_links)} with missing samples"
            if issue_types:
                result_msg += f" | Most common: {', '.join(issue_types)}"
            
            self.status_manager.finish_operation(True, result_msg)
        else:
            result_msg = f"Scanned {total} XPM files - All files are healthy! ✅"
            self.status_manager.finish_operation(True, result_msg)

    def show_detailed_issues(self, event):
        """Show detailed issue information for selected XPM."""
        selection = self.tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.tree.item(item)["values"]
        if not values:
            return
            
        xmp_rel_path = values[0]
        folder = self.master.folder_path.get()
        xmp_path = os.path.join(folder, xmp_rel_path)
        
        if xmp_path not in self.file_info:
            return
        
        analysis = self.file_info[xmp_path]
        
        # Create detailed info window
        detail_window = tk.Toplevel(self)
        detail_window.title(f"Detailed Issues - {os.path.basename(xmp_path)}")
        detail_window.geometry("600x400")
        
        frame = ttk.Frame(detail_window, padding="10")
        frame.pack(fill="both", expand=True)
        
        # File info
        info_text = f"File: {xmp_rel_path}\\n"
        info_text += f"Version: {analysis.get('version', 'Unknown')}\\n"
        info_text += f"Keygroups: {analysis.get('keygroup_count', 0)} (declared: {analysis.get('declared_count', 0)})\\n\\n"
        
        # Issues
        issues = analysis.get('issues', [])
        if issues:
            info_text += f"Issues Found ({len(issues)}):\\n"
            for i, issue in enumerate(issues, 1):
                info_text += f"{i}. {issue}\\n"
        else:
            info_text += "No issues detected.\\n"
        
        # Missing samples
        missing = analysis.get('missing_samples', [])
        if missing:
            info_text += f"\\nMissing Samples ({len(missing)}):\\n"
            for sample in missing:
                info_text += f"• {sample}\\n"
        
        # Recommended fixes
        fixes = analysis.get('fixes', [])
        if fixes:
            info_text += f"\\nRecommended Fixes ({len(fixes)}):\\n"
            fix_descriptions = {
                "fix_keygroup_count": "🔢 Fix KeygroupNumKeygroups count mismatch",
                "fix_keygroup_ranges": "🎹 Fix LowNote/HighNote ranges", 
                "fix_pad_mapping": "📋 Fix ProgramPads mapping consistency",
                "fix_missing_samples": "🔗 Relink missing sample files",
                "fix_version": "📝 Update version information",
                "fix_structural_bloat": "🔥 Fix structural bloat (critical for MPC Live 2)"
            }
            for fix in fixes:
                desc = fix_descriptions.get(fix, f"• {fix.replace('_', ' ').title()}")
                info_text += f"{desc}\\n"
            
            # Add usage hints
            info_text += f"\\n💡 Quick Fix Tips:\\n"
            info_text += f"• Use '🔧 Batch Fix All Issues' to fix everything at once\\n"
            if "fix_structural_bloat" in fixes:
                info_text += f"• Structural bloat fix will dramatically improve MPC Live 2 performance\\n"
            if "fix_keygroup_count" in fixes or "fix_keygroup_ranges" in fixes:
                info_text += f"• Keygroup fixes will ensure proper C0-C8 keyboard access\\n"
        
        # Create scrollable text widget
        text_frame = ttk.Frame(frame)
        text_frame.pack(fill="both", expand=True)
        
        text_widget = tk.Text(text_frame, wrap="word", height=20, width=70)
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        text_widget.insert("1.0", info_text)
        text_widget.config(state="disabled")
        
        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x", pady=(10, 0))
        
        if fixes:
            ttk.Button(btn_frame, text="Fix This File", 
                      command=lambda: self.fix_single_file(xmp_path, detail_window)).pack(side="left")
        
        ttk.Button(btn_frame, text="Close", command=detail_window.destroy).pack(side="right")

    def fix_single_file(self, xmp_path, parent_window):
        """Fix issues in a single XPM file."""
        if xmp_path not in self.file_info:
            return
        
        analysis = self.file_info[xmp_path]
        fixes = analysis.get("fixes", [])
        
        if not fixes:
            messagebox.showinfo("No Fixes", "No fixes available for this file.", parent=parent_window)
            return
        
        # Create backup
        backup_path = xmp_path + ".backup"
        if not os.path.exists(backup_path):
            shutil.copy2(xmp_path, backup_path)
        
        fixed_issues = []
        
        try:
            for fix_type in fixes:
                if fix_type == "fix_keygroup_count":
                    if self.fix_single_keygroup_count(xmp_path):
                        fixed_issues.append("keygroup count")
                elif fix_type == "fix_keygroup_ranges":
                    if self.fix_single_key_ranges(xmp_path):
                        fixed_issues.append("key ranges")
                elif fix_type == "fix_pad_mapping":
                    if self.fix_single_pad_mapping(xmp_path):
                        fixed_issues.append("pad mapping")
                elif fix_type == "fix_version":
                    if self.fix_single_version(xmp_path):
                        fixed_issues.append("version")
                elif fix_type == "fix_structural_bloat":
                    if self.fix_structural_bloat(xmp_path):
                        fixed_issues.append("structural bloat")
            
            if fixed_issues:
                messagebox.showinfo("Fix Complete", 
                                   f"Successfully fixed: {', '.join(fixed_issues)}", 
                                   parent=parent_window)
                parent_window.destroy()
                self.scan_broken_links()
            else:
                messagebox.showwarning("No Changes", "No changes were made.", parent=parent_window)
                
        except Exception as e:
            messagebox.showerror("Error", f"Error fixing file: {e}", parent=parent_window)

    def batch_fix_all_issues(self):
        """Fix all detected issues in batch with enhanced progress tracking."""
        if not self.file_info:
            messagebox.showwarning("No Data", "Please run a scan first.", parent=self)
            return
        
        files_with_issues = [path for path, info in self.file_info.items() if info.get("issues")]
        if not files_with_issues:
            messagebox.showinfo("No Issues", "No issues found to fix.", parent=self)
            return
        
        confirm_msg = (f"This will attempt to fix all detected issues in {len(files_with_issues)} XPM file(s).\n\n"
                      "The following fixes will be applied:\n"
                      "• Keygroup count corrections\n"
                      "• Key range fixes (LowNote/HighNote)\n"
                      "• ProgramPads mapping corrections\n"
                      "• Version updates\n"
                      "• CRITICAL: Remove structural bloat (empty instruments)\n"
                      "• CRITICAL: Optimize for MPC Live 2 compatibility\n\n"
                      "Backup files (.backup) will be created. Continue?")
        
        if not messagebox.askyesno("Batch Fix All Issues", confirm_msg, parent=self):
            return
        
        # Initialize progress tracking
        progress_tracker = ProgressTracker(
            total_items=len(files_with_issues),
            status_callback=lambda msg: (self.status.set(msg), self.update())
        )
        
        fixed_count = 0
        
        for i, xmp_path in enumerate(files_with_issues):
            current_file = os.path.basename(xmp_path)
            progress_tracker.update_progress(current_item=current_file)
            
            try:
                # Get file size for statistics
                file_size = os.path.getsize(xmp_path) if os.path.exists(xmp_path) else 0
                
                # Create backup
                backup_path = xmp_path + ".backup"
                if not os.path.exists(backup_path):
                    shutil.copy2(xmp_path, backup_path)
                
                analysis = self.file_info[xmp_path]
                fixed_issues = []
                
                # CRITICAL FIX: Apply structural bloat removal FIRST
                try:
                    if self.fix_structural_bloat(xmp_path):
                        fixed_issues.append("structural bloat")
                except XPMProcessingError as e:
                    logging.error(f"Structural bloat fix failed for {current_file}: {e}")
                    progress_tracker.stats.add_error(f"Structural bloat fix failed: {e}", xmp_path)
                
                # Apply individual fixes based on detected issues
                for fix_type in analysis.get("fixes", []):
                    try:
                        if fix_type == "fix_keygroup_count":
                            if self.fix_single_keygroup_count(xmp_path):
                                fixed_issues.append("keygroup count")
                        elif fix_type == "fix_keygroup_ranges":
                            if self.fix_single_key_ranges(xmp_path):
                                fixed_issues.append("key ranges")
                        elif fix_type == "fix_pad_mapping":
                            if self.fix_single_pad_mapping(xmp_path):
                                fixed_issues.append("pad mapping")
                        elif fix_type == "fix_version":
                            if self.fix_single_version(xmp_path):
                                fixed_issues.append("version")
                    except Exception as e:
                        logging.error(f"Fix {fix_type} failed for {current_file}: {e}")
                        progress_tracker.stats.add_error(f"Fix {fix_type} failed: {e}", xmp_path)
                
                if fixed_issues:
                    fixed_count += 1
                    progress_tracker.stats.add_success(file_size)
                    logging.info(f"Fixed {', '.join(fixed_issues)} in {current_file}")
                else:
                    progress_tracker.stats.add_success(file_size)
                
            except Exception as e:
                progress_tracker.stats.add_error(str(e), xmp_path)
                logging.error(f"Error fixing {current_file}: {e}")
        
        # Show enhanced results with statistics
        summary = progress_tracker.finish()
        result_msg = f"Batch Fix Complete!\n\n{summary}\n\n"
        result_msg += f"Files with fixes applied: {fixed_count}\n"
        result_msg += f"Total data processed: {progress_tracker.stats.total_size_processed / 1024 / 1024:.1f} MB"
        
        if progress_tracker.stats.errors:
            result_msg += f"\n\nErrors ({len(progress_tracker.stats.errors)}):\n"
            result_msg += "\n".join(progress_tracker.stats.errors[:5])
            if len(progress_tracker.stats.errors) > 5:
                result_msg += f"\n... and {len(progress_tracker.stats.errors) - 5} more errors"
        
        messagebox.showinfo("Batch Fix Complete", result_msg, parent=self)
        self.status.set("Batch fix complete. Rescanning...")
        self.scan_broken_links()

    def fix_keygroup_counts(self):
        """Fix KeygroupNumKeygroups values in batch."""
        files_to_fix = []
        for path, info in self.file_info.items():
            if "fix_keygroup_count" in info.get("fixes", []):
                files_to_fix.append(path)
        
        if not files_to_fix:
            messagebox.showinfo("No Issues", "No keygroup count issues found.", parent=self)
            return
        
        if not messagebox.askyesno("Fix Keygroup Counts", 
                                   f"Fix keygroup count mismatches in {len(files_to_fix)} file(s)?", parent=self):
            return
        
        fixed = 0
        for xmp_path in files_to_fix:
            if self.fix_single_keygroup_count(xmp_path):
                fixed += 1
        
        messagebox.showinfo("Keygroup Counts Fixed", f"Fixed {fixed} file(s).", parent=self)
        self.scan_broken_links()

    def fix_key_ranges(self):
        """Fix LowNote/HighNote ranges in batch."""
        files_to_fix = []
        for path, info in self.file_info.items():
            if "fix_keygroup_ranges" in info.get("fixes", []):
                files_to_fix.append(path)
        
        if not files_to_fix:
            messagebox.showinfo("No Issues", "No key range issues found.", parent=self)
            return
        
        if not messagebox.askyesno("Fix Key Ranges", 
                                   f"Fix key range issues in {len(files_to_fix)} file(s)?", parent=self):
            return
        
        fixed = 0
        for xmp_path in files_to_fix:
            if self.fix_single_key_ranges(xmp_path):
                fixed += 1
        
        messagebox.showinfo("Key Ranges Fixed", f"Fixed {fixed} file(s).", parent=self)
        self.scan_broken_links()

    def fix_pad_mappings(self):
        """Fix ProgramPads mappings in batch."""
        files_to_fix = []
        for path, info in self.file_info.items():
            if "fix_pad_mapping" in info.get("fixes", []):
                files_to_fix.append(path)
        
        if not files_to_fix:
            messagebox.showinfo("No Issues", "No pad mapping issues found.", parent=self)
            return
        
        if not messagebox.askyesno("Fix Pad Mappings", 
                                   f"Fix pad mapping issues in {len(files_to_fix)} file(s)?", parent=self):
            return
        
        fixed = 0
        for xmp_path in files_to_fix:
            if self.fix_single_pad_mapping(xmp_path):
                fixed += 1
        
        messagebox.showinfo("Pad Mappings Fixed", f"Fixed {fixed} file(s).", parent=self)
        self.scan_broken_links()

    def fix_single_keygroup_count(self, xmp_path):
        """Fix KeygroupNumKeygroups for a single file."""
        try:
            tree = ET.parse(xmp_path)
            root = tree.getroot()
            
            kg_count_elem = root.find(".//KeygroupNumKeygroups")
            instruments = root.findall(".//Instrument")
            actual_count = len(instruments)
            
            if kg_count_elem is None:
                # Create element if it doesn't exist
                program_elem = root.find(".//Program")
                if program_elem is not None:
                    kg_count_elem = ET.SubElement(program_elem, "KeygroupNumKeygroups")
                else:
                    return False
            
            kg_count_elem.text = str(actual_count)
            
            tree.write(xmp_path, encoding="utf-8", xml_declaration=True)
            return True
            
        except Exception as e:
            logging.error(f"Error fixing keygroup count in {xmp_path}: {e}")
            return False

    def fix_single_key_ranges(self, xmp_path):
        """Fix LowNote/HighNote ranges for a single file using intelligent range calculation."""
        try:
            with safe_xml_operation(xmp_path, create_backup=True):
                tree = ET.parse(xmp_path)
                root = tree.getroot()
                instruments = root.findall(".//Instrument")
                fixed = False
                
                # Extract sample info from all instruments to calculate intelligent ranges
                sample_mappings = []
                instrument_data = []
                
                for i, instrument in enumerate(instruments):
                    # Extract root note from layer
                    layer = instrument.find("Layer")
                    root_note = 60  # Default to C4
                    sample_path = None
                    
                    if layer is not None:
                        root_note_elem = layer.find("RootNote")
                        if root_note_elem is not None and root_note_elem.text:
                            try:
                                root_note = int(root_note_elem.text)
                            except (ValueError, TypeError):
                                root_note = 60
                        
                        # Get sample path for additional analysis if needed
                        sample_file_elem = layer.find("SampleFile")
                        sample_name_elem = layer.find("SampleName")
                        if sample_file_elem is not None and sample_file_elem.text:
                            sample_path = sample_file_elem.text
                        elif sample_name_elem is not None and sample_name_elem.text:
                            sample_path = sample_name_elem.text
                    
                    sample_mappings.append({
                        "root_note": root_note,
                        "sample_path": sample_path,
                        "instrument_index": i
                    })
                    instrument_data.append(instrument)
                
                # Calculate intelligent key ranges using a simple algorithm
                if sample_mappings:
                    # Sort samples by root note
                    sorted_samples = sorted(sample_mappings, key=lambda x: x.get("root_note", 60))
                    n = len(sorted_samples)
                    
                    if n == 1:
                        # Single sample gets full range
                        calculated_ranges = [{
                            "instrument_index": sorted_samples[0]["instrument_index"],
                            "root_note": sorted_samples[0]["root_note"],
                            "low_note": 0,
                            "high_note": 127
                        }]
                    else:
                        # Multiple samples - assign ranges so each covers halfway to the next
                        calculated_ranges = []
                        for i, sample in enumerate(sorted_samples):
                            root = sample.get("root_note", 60)
                            
                            if i == 0:
                                low = 0
                            else:
                                prev_root = sorted_samples[i - 1].get("root_note", 60)
                                low = (prev_root + root) // 2 + 1
                            
                            if i == n - 1:
                                high = 127
                            else:
                                next_root = sorted_samples[i + 1].get("root_note", 60)
                                high = (root + next_root) // 2
                                
                            calculated_ranges.append({
                                "instrument_index": sample["instrument_index"],
                                "root_note": root,
                                "low_note": low,
                                "high_note": high
                            })
                    
                    for mapping in calculated_ranges:
                        i = mapping["instrument_index"]
                        instrument = instrument_data[i]
                        
                        low_note_elem = instrument.find("LowNote")
                        high_note_elem = instrument.find("HighNote")
                        
                        # Create missing elements
                        if low_note_elem is None:
                            low_note_elem = ET.SubElement(instrument, "LowNote")
                        if high_note_elem is None:
                            high_note_elem = ET.SubElement(instrument, "HighNote")
                        
                        # Get current values
                        try:
                            current_low = int(low_note_elem.text) if low_note_elem.text else 0
                            current_high = int(high_note_elem.text) if high_note_elem.text else 127
                        except (ValueError, TypeError):
                            current_low = 0
                            current_high = 127
                        
                        # Apply intelligent range if current values are problematic
                        needs_fix = (
                            current_low > current_high or 
                            current_low == current_high == 0 or 
                            current_low < 0 or 
                            current_high > 127 or
                            current_low == 0 and current_high == 127  # Full range = likely incorrect
                        )
                        
                        if needs_fix:
                            new_low = mapping["low_note"]
                            new_high = mapping["high_note"]
                            
                            low_note_elem.text = str(new_low)
                            high_note_elem.text = str(new_high)
                            fixed = True
                            
                            logging.info(f"🎹 Fixed key range for instrument {i+1}: "
                                       f"Root={mapping['root_note']}, Range={new_low}-{new_high}")
                
                if fixed:
                    tree.write(xmp_path, encoding="utf-8", xml_declaration=True)
                    logging.info(f"✅ Intelligently fixed key ranges in {os.path.basename(xmp_path)}")
                
                return fixed
                
        except XPMProcessingError:
            # Re-raise XPMProcessingError as-is (already has context)
            raise
        except Exception as e:
            # Wrap other exceptions
            raise XPMProcessingError(
                f"Unexpected error fixing key ranges: {e}",
                file_path=xmp_path,
                original_exception=e
            ) from e

    def fix_single_pad_mapping(self, xmp_path):
        """Fix ProgramPads mapping for a single file."""
        try:
            tree = ET.parse(xmp_path)
            root = tree.getroot()
            instruments = root.findall(".//Instrument")
            actual_count = len(instruments)
            
            pads_elem = root.find(".//ProgramPads-v2.10")
            if pads_elem is None:
                pads_elem = root.find(".//ProgramPads")
            if pads_elem is None or not pads_elem.text:
                return False
            
            pads_data = json.loads(xml_unescape(pads_elem.text))
            if not isinstance(pads_data, dict):
                return False
            
            # Fix padToInstrument mapping
            pad_to_inst = pads_data.get("padToInstrument", {})
            if len(pad_to_inst) != actual_count:
                # Rebuild mapping - first N pads map to N instruments
                new_mapping = {}
                for i in range(actual_count):
                    new_mapping[str(i)] = i
                pads_data["padToInstrument"] = new_mapping
                
                # Update the element
                pads_elem.text = xml_escape(json.dumps(pads_data, indent=4))
                tree.write(xmp_path, encoding="utf-8", xml_declaration=True)
                return True
            
            return False
            
        except Exception as e:
            logging.error(f"Error fixing pad mapping in {xmp_path}: {e}")
            return False

    def fix_single_version(self, xmp_path):
        """Fix version information for a single file."""
        try:
            tree = ET.parse(xmp_path)
            root = tree.getroot()
            
            version_elem = root.find(".//Application_Version")
            target_version = self.version_var.get()
            
            if version_elem is None:
                # Create version element
                version_elem = ET.SubElement(root, "Application_Version")
            
            if version_elem.text != target_version:
                version_elem.text = target_version
                tree.write(xmp_path, encoding="utf-8", xml_declaration=True)
                return True
            
            return False
            
        except Exception as e:
            logging.error(f"Error fixing version in {xmp_path}: {e}")
            return False

    @log_function_entry_exit
    def fix_structural_bloat(self, xmp_path):
        """
        CRITICAL FIX: Remove structural bloat that causes MPC Live 2 compatibility issues.
        
        This addresses the core problem where Expansion Doctor creates 128 <Instrument> elements
        even when only 10-15 actually contain samples, causing:
        - Memory overload on MPC Live 2
        - Slow parsing and loading times
        - Performance degradation during playback
        - Voice allocation confusion
        
        Solution: Keep only instruments that have actual sample content and apply intelligent range mapping.
        """
        try:
            tree = ET.parse(xmp_path)
            root = tree.getroot()
            
            # Validate XMP structure
            validate_xpm_structure(root)
            log_xml_operation("structure_validated", xmp_path)
            
            instruments_container = root.find(".//Instruments")
            if instruments_container is None:
                return False
            
            instruments = instruments_container.findall("Instrument")
            original_count = len(instruments)
            
            # Only proceed if we have a suspiciously high number of instruments
            if original_count < 50:
                return False  # Probably not bloated
            
            instruments_with_samples = []
            empty_instruments = []
            
            for instrument in instruments:
                has_samples = False
                
                # Check for layers with samples
                layers = instrument.find("Layers")
                if layers is not None:
                    for layer in layers.findall("Layer"):
                        sample_name_elem = layer.find("SampleName")
                        sample_file_elem = layer.find("SampleFile")
                        
                        if ((sample_name_elem is not None and sample_name_elem.text and sample_name_elem.text.strip()) or
                            (sample_file_elem is not None and sample_file_elem.text and sample_file_elem.text.strip())):
                            has_samples = True
                            break
                
                if has_samples:
                    instruments_with_samples.append(instrument)
                else:
                    empty_instruments.append(instrument)
            
            # If we found significant bloat, remove empty instruments
            if len(empty_instruments) > 10:  # Significant bloat detected
                logging.info(f"🔧 STRUCTURAL BLOAT FIX: Removing {len(empty_instruments)} empty instruments from {os.path.basename(xmp_path)}")
                
                # Remove empty instruments from the container
                for empty_instrument in empty_instruments:
                    instruments_container.remove(empty_instrument)
                
                # Renumber remaining instruments to be sequential starting from 1
                for i, instrument in enumerate(instruments_with_samples):
                    instrument.set("number", str(i + 1))
                
                # Update KeygroupNumKeygroups to match actual instrument count
                kg_count_elem = root.find(".//KeygroupNumKeygroups")
                if kg_count_elem is not None:
                    kg_count_elem.text = str(len(instruments_with_samples))
                
                # CRITICAL: Update file format to modern version for better MPC compatibility
                # BUT avoid creating ProgramPads JSON that would collapse multi-sample structure
                version_elem = root.find(".//File_Version")
                if version_elem is not None:
                    version_elem.text = "2.1"
                
                app_version_elem = root.find(".//Application_Version")
                if app_version_elem is not None:
                    app_version_elem.text = "3.5.0.54"
                
                platform_elem = root.find(".//Platform")
                if platform_elem is not None:
                    platform_elem.text = "Linux"
                
                # Save the optimized file (XML-only format, no ProgramPads JSON)
                tree.write(xmp_path, encoding="utf-8", xml_declaration=True)
                
                logging.info(f"✅ OPTIMIZED: {os.path.basename(xmp_path)} - {original_count} → {len(instruments_with_samples)} instruments")
                return True
            
            return False
            
        except Exception as e:
            logging.error(f"Error fixing structural bloat in {xmp_path}: {e}")
            return False


class ExpansionBuilderWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master.root if hasattr(master, "root") else master)
        self.title("Expansion Builder")
        self.geometry("600x330")
        self.resizable(True, True)
        self.master = master
        self.create_widgets()

    def create_widgets(self):
        frame = ttk.Frame(self, padding="10")
        frame.pack(fill="both", expand=True)
        frame.grid_columnconfigure(1, weight=1)

        ttk.Label(frame, text="Identifier:").grid(
            row=0, column=0, sticky="e", padx=5, pady=2
        )
        self.identifier_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.identifier_var).grid(
            row=0, column=1, columnspan=2, sticky="ew", pady=2
        )

        ttk.Label(frame, text="Title:").grid(
            row=1, column=0, sticky="e", padx=5, pady=2
        )
        self.title_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.title_var).grid(
            row=1, column=1, columnspan=2, sticky="ew", pady=2
        )

        ttk.Label(frame, text="Manufacturer:").grid(
            row=2, column=0, sticky="e", padx=5, pady=2
        )
        self.manufacturer_var = tk.StringVar(value="Akai Professional / MSX")
        ttk.Entry(frame, textvariable=self.manufacturer_var).grid(
            row=2, column=1, columnspan=2, sticky="ew", pady=2
        )

        ttk.Label(frame, text="Version:").grid(
            row=3, column=0, sticky="e", padx=5, pady=2
        )
        self.version_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.version_var).grid(
            row=3, column=1, columnspan=2, sticky="ew", pady=2
        )

        ttk.Label(frame, text="Type:").grid(row=4, column=0, sticky="e", padx=5, pady=2)
        self.type_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.type_var).grid(
            row=4, column=1, columnspan=2, sticky="ew", pady=2
        )

        ttk.Label(frame, text="Image (JPG/PNG):").grid(
            row=5, column=0, sticky="e", padx=5, pady=2
        )
        self.image_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.image_var).grid(
            row=5, column=1, sticky="ew", pady=2
        )
        ttk.Button(frame, text="Browse...", command=self.browse_image).grid(
            row=5, column=2, padx=5, pady=2
        )

        ttk.Label(frame, text="Directory:").grid(
            row=6, column=0, sticky="e", padx=5, pady=2
        )
        default_dir = (
            os.path.basename(self.master.folder_path.get())
            if hasattr(self.master, "folder_path")
            else ""
        )
        self.directory_var = tk.StringVar(value=default_dir)
        ttk.Entry(frame, textvariable=self.directory_var).grid(
            row=6, column=1, columnspan=2, sticky="ew", pady=2
        )

        ttk.Label(frame, text="Separator:").grid(
            row=7, column=0, sticky="e", padx=5, pady=2
        )
        self.separator_var = tk.StringVar(value="-")
        ttk.Entry(frame, textvariable=self.separator_var).grid(
            row=7, column=1, columnspan=2, sticky="ew", pady=2
        )

        ttk.Button(frame, text="Create Expansion.xml", command=self.create_file).grid(
            row=8, column=0, columnspan=3, pady=10
        )

    def browse_image(self):
        path = filedialog.askopenfilename(
            parent=self,
            title="Select Image",
            filetypes=[("Image Files", "*.jpg *.jpeg *.png")],
        )
        if path:
            self.image_var.set(path)
            self.master.last_browse_path = os.path.dirname(path)

    def create_file(self):
        folder = self.master.folder_path.get()
        if not folder or not os.path.isdir(folder):
            messagebox.showerror("Error", "No valid folder selected.", parent=self)
            return

        identifier = self.identifier_var.get().strip()
        title = self.title_var.get().strip()
        manufacturer = self.manufacturer_var.get().strip()
        version = self.version_var.get().strip()
        type_value = self.type_var.get().strip()
        directory = self.directory_var.get().strip() or os.path.basename(folder)
        separator = self.separator_var.get().strip()
        image_path = self.image_var.get().strip()

        if not identifier or not title:
            messagebox.showerror(
                "Error", "Identifier and Title are required.", parent=self
            )
            return

        xml_path = os.path.join(folder, "Expansion.xml")
        root = ET.Element("expansion", version="1.0")
        ET.SubElement(root, "identifier").text = identifier
        ET.SubElement(root, "title").text = title
        ET.SubElement(root, "manufacturer").text = manufacturer
        ET.SubElement(root, "version").text = version
        ET.SubElement(root, "type").text = type_value

        if image_path and os.path.exists(image_path):
            image_basename = os.path.basename(image_path)
            ET.SubElement(root, "img").text = image_basename
            dest_path = os.path.join(folder, image_basename)
            try:
                if PIL_AVAILABLE:
                    img = Image.open(image_path)
                    img = img.convert("RGB")
                    img = img.resize(EXPANSION_IMAGE_SIZE, Image.LANCZOS)
                    img.save(dest_path)
                else:
                    shutil.copy2(image_path, dest_path)
            except Exception as e:
                logging.error(f"Failed to copy image: {e}")
                messagebox.showerror(
                    "Image Error",
                    f"Failed to copy image to expansion folder:\n{e}",
                    parent=self,
                )

        ET.SubElement(root, "directory").text = directory
        ET.SubElement(root, "separator").text = separator

        tree = ET.ElementTree(root)
        indent_tree(tree)
        tree.write(xml_path, encoding="UTF-8", xml_declaration=True)
        messagebox.showinfo(
            "Success", f"Expansion.xml created at {xml_path}", parent=self
        )
        self.destroy()


class FileRenamerWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master.root if hasattr(master, "root") else master)
        self.title("File Renamer")
        self.geometry("900x600")
        self.resizable(True, True)
        self.master = master
        self.folder_path = master.folder_path.get()
        self.include_folder_var = tk.BooleanVar(value=True)
        self.rename_proposals = []
        self.check_vars = {}
        self.create_widgets()
        self.scan_files()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill="both", expand=True)
        main_frame.grid_rowconfigure(2, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)

        top_frame = ttk.Frame(main_frame)
        top_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        ttk.Button(top_frame, text="Rescan Files", command=self.scan_files).pack(
            side="left"
        )
        ttk.Checkbutton(
            top_frame,
            text="Include Folder Name in Suggestion",
            variable=self.include_folder_var,
            command=self.update_all_suggestions,
        ).pack(side="left", padx=10)

        batch_frame = ttk.LabelFrame(main_frame, text="Batch Operations", padding="5")
        batch_frame.grid(row=1, column=0, sticky="ew", pady=(0, 5))
        ttk.Label(batch_frame, text="Remove chars:").pack(side="left")
        self.remove_chars_entry = ttk.Entry(batch_frame, width=10)
        self.remove_chars_entry.pack(side="left", padx=2)
        ttk.Button(batch_frame, text="Apply", command=self.batch_remove_chars).pack(
            side="left"
        )
        ttk.Label(batch_frame, text="Replace:").pack(side="left", padx=(10, 0))
        self.replace_from_entry = ttk.Entry(batch_frame, width=10)
        self.replace_from_entry.pack(side="left", padx=2)
        ttk.Label(batch_frame, text="with").pack(side="left")
        self.replace_to_entry = ttk.Entry(batch_frame, width=10)
        self.replace_to_entry.pack(side="left", padx=2)
        ttk.Button(batch_frame, text="Apply", command=self.batch_replace).pack(
            side="left"
        )
        ttk.Button(
            batch_frame, text="Title Case", command=lambda: self.batch_case("title")
        ).pack(side="left", padx=(10, 2))
        ttk.Button(
            batch_frame, text="UPPERCASE", command=lambda: self.batch_case("upper")
        ).pack(side="left", padx=2)
        ttk.Button(
            batch_frame, text="lowercase", command=lambda: self.batch_case("lower")
        ).pack(side="left", padx=2)

        tree_frame = ttk.Frame(main_frame)
        tree_frame.grid(row=2, column=0, sticky="nsew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        self.tree = Treeview(
            tree_frame, columns=("Select", "Original", "Suggested"), show="headings"
        )
        self.tree.heading("Select", text="Select")
        self.tree.heading("Original", text="Original Filename")
        self.tree.heading("Suggested", text="Suggested New Filename")
        self.tree.column("Select", width=60, anchor="center", stretch=False)
        self.tree.column("Original", width=350)
        self.tree.column("Suggested", width=350)
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        self.tree.bind("<Button-1>", self.on_tree_click)
        self.tree.bind("<Double-1>", self.on_edit_cell)

        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.grid(row=3, column=0, sticky="ew", pady=(5, 0))
        ttk.Button(
            bottom_frame,
            text="Select All",
            command=lambda: self.toggle_all_checks(True),
        ).pack(side="left")
        ttk.Button(
            bottom_frame,
            text="Deselect All",
            command=lambda: self.toggle_all_checks(False),
        ).pack(side="left", padx=5)
        self.apply_button = ttk.Button(
            bottom_frame,
            text="Apply Selected Renames",
            command=self.apply_renames,
            state="disabled",
        )
        self.apply_button.pack(side="right")

    def _generate_suggestion(self, proposal):
        info = get_clean_sample_info(proposal["original_path"])
        note_str = str(proposal["note"]) if proposal["note"] is not None else ""
        parts = []
        if self.include_folder_var.get():
            parts.append(info["folder"].strip())

        base_name_cleaned = re.sub(
            r"([A-G][#b]?\-?\d+)", "", info["base"], flags=re.IGNORECASE
        ).strip()
        base_name_cleaned = re.sub(r"\b(\d{2,3})\b", "", base_name_cleaned).strip()
        parts.append(base_name_cleaned)

        if note_str:
            parts.append(note_str)

        final_base = " ".join(filter(None, parts))
        return f"{final_base}{info['ext']}"

    def update_all_suggestions(self):
        for i, row_id in enumerate(self.tree.get_children()):
            proposal = self.rename_proposals[i]
            new_name = self._generate_suggestion(proposal)
            proposal["new_name"] = new_name
            self.tree.set(row_id, "Suggested", new_name)

    def scan_files(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        self.rename_proposals.clear()
        self.check_vars.clear()

        if not self.folder_path or not os.path.isdir(self.folder_path):
            messagebox.showwarning(
                "No Folder", "Please select a source folder first.", parent=self
            )
            return

        wav_files = glob.glob(
            os.path.join(self.folder_path, "**", "*.wav"), recursive=True
        )
        for path in wav_files:
            if ".xpm.wav" in path.lower():
                continue

            info = get_clean_sample_info(path)
            proposal = {
                "original_path": path,
                "original_name": os.path.basename(path),
                "new_name": "",
                "folder": info["folder"],
                "note": info["note"],
                "ext": info["ext"],
                "base": info["base"],
            }
            proposal["new_name"] = self._generate_suggestion(proposal)
            self.rename_proposals.append(proposal)

        for i, proposal in enumerate(self.rename_proposals):
            row_id = self.tree.insert(
                "",
                "end",
                values=("No", proposal["original_name"], proposal["new_name"]),
            )
            self.check_vars[row_id] = tk.BooleanVar(value=False)

        self.apply_button.config(
            state="normal" if self.rename_proposals else "disabled"
        )

    def on_tree_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        col = self.tree.identify_column(event.x)
        row_id = self.tree.identify_row(event.y)
        if not row_id:
            return

        if col == "#1":
            current_val = self.check_vars[row_id].get()
            self.check_vars[row_id].set(not current_val)
            self.tree.set(row_id, "Select", "Yes" if not current_val else "No")

    def batch_remove_chars(self):
        chars = self.remove_chars_entry.get()
        if not chars:
            return
        for row_id in self.tree.get_children():
            if self.check_vars.get(row_id, tk.BooleanVar(value=False)).get():
                current_name = self.tree.set(row_id, "Suggested")
                new_name = current_name.translate({ord(c): None for c in chars})
                self.tree.set(row_id, "Suggested", new_name)

    def batch_replace(self):
        old = self.replace_from_entry.get()
        new = self.replace_to_entry.get()
        if not old:
            return
        for row_id in self.tree.get_children():
            if self.check_vars.get(row_id, tk.BooleanVar(value=False)).get():
                current_name = self.tree.set(row_id, "Suggested")
                new_name = current_name.replace(old, new)
                self.tree.set(row_id, "Suggested", new_name)

    def batch_case(self, mode):
        for row_id in self.tree.get_children():
            if self.check_vars.get(row_id, tk.BooleanVar(value=False)).get():
                current_name = self.tree.set(row_id, "Suggested")
                name_part, ext_part = os.path.splitext(current_name)
                if mode == "upper":
                    new_name_part = name_part.upper()
                elif mode == "lower":
                    new_name_part = name_part.lower()
                elif mode == "title":
                    new_name_part = name_part.title()
                else:
                    continue
                self.tree.set(row_id, "Suggested", new_name_part + ext_part)

    def on_edit_cell(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        col = self.tree.identify_column(event.x)
        if col == "#3":
            row_id = self.tree.identify_row(event.y)
            if not row_id:
                return
            x, y, width, height = self.tree.bbox(row_id, col)
            value = self.tree.set(row_id, "Suggested")
            entry = ttk.Entry(self.tree)
            entry.place(x=x, y=y, width=width, height=height)
            entry.insert(0, value)
            entry.focus()

            def save_edit(event=None):
                self.tree.set(row_id, "Suggested", entry.get())
                entry.destroy()

            entry.bind("<Return>", save_edit)
            entry.bind("<FocusOut>", save_edit)

    def apply_renames(self):
        selected_proposals = []
        for i, row_id in enumerate(self.tree.get_children()):
            if self.check_vars.get(row_id, tk.BooleanVar(value=False)).get():
                proposal = self.rename_proposals[i]
                proposal["new_name"] = self.tree.set(row_id, "Suggested")
                selected_proposals.append(proposal)

        if not selected_proposals:
            messagebox.showinfo(
                "No Selection", "No files were selected to rename.", parent=self
            )
            return

        if not messagebox.askyesno(
            "Confirm Rename",
            f"This will rename {len(selected_proposals)} file(s) and modify all affected .xpm programs. This action CANNOT be undone. Are you sure?",
            parent=self,
        ):
            return

        rename_map = {
            item["original_path"]: os.path.join(
                os.path.dirname(item["original_path"]), item["new_name"]
            )
            for item in selected_proposals
        }

        all_xpms = glob.glob(
            os.path.join(self.folder_path, "**", "*.xpm"), recursive=True
        )

        for xpm_path in all_xpms:
            try:
                tree = ET.parse(xpm_path)
                root = tree.getroot()
                changed = False
                for elem in root.findall(".//SampleFile"):
                    if elem is not None and elem.text:
                        rel_path = elem.text.replace("/", os.sep)
                        original_sample_path = os.path.normpath(
                            os.path.join(os.path.dirname(xpm_path), rel_path)
                        )
                        if original_sample_path in rename_map:
                            new_sample_path = rename_map[original_sample_path]
                            new_rel_path = os.path.relpath(
                                new_sample_path, os.path.dirname(xpm_path)
                            )
                            elem.text = new_rel_path.replace(os.sep, "/")

                            # Update SampleName element as well - find parent Layer
                            parent_layer = elem.getparent()
                            if parent_layer is not None:
                                sample_name_elem = parent_layer.find("SampleName")
                                if sample_name_elem is not None:
                                    sample_name_elem.text = os.path.splitext(
                                        os.path.basename(new_sample_path)
                                    )[0]
                            changed = True
                if changed:
                    indent_tree(tree)
                    tree.write(xpm_path, encoding="utf-8", xml_declaration=True)
            except Exception as e:
                logging.error(f"Error updating XPM {xpm_path}: {e}")

        for original, new in rename_map.items():
            try:
                if os.path.exists(original):
                    os.rename(original, new)
                else:
                    logging.warning(f"Original file not found for renaming: {original}")
            except Exception as e:
                logging.error(f"Error renaming {original} to {new}: {e}")

        messagebox.showinfo(
            "Success", "Files renamed and programs updated.", parent=self
        )
        self.scan_files()

    def toggle_all_checks(self, select_all):
        for row_id in self.tree.get_children():
            self.check_vars[row_id].set(select_all)
            self.tree.set(row_id, "Select", "Yes" if select_all else "No")


class CreativeModeConfigWindow(tk.Toplevel):
    def __init__(self, master, mode):
        super().__init__(master.root)
        self.title(f"Configure '{mode}' Mode")
        self.geometry("350x200")
        self.master = master
        self.mode = mode
        self.config = {}

        frame = ttk.Frame(self, padding="10")
        frame.pack(fill="both", expand=True)

        if self.mode == "synth":
            ttk.Label(frame, text="Resonance (0.0-1.0):").pack(anchor="w")
            self.resonance = tk.DoubleVar(
                value=master.creative_config.get("synth", {}).get("resonance", 0.2)
            )
            ttk.Scale(
                frame, from_=0, to=1, variable=self.resonance, orient="horizontal"
            ).pack(fill="x", pady=2)
            ttk.Label(frame, text="Release Time (0.0-2.0s):").pack(
                anchor="w", pady=(10, 0)
            )
            self.release = tk.DoubleVar(
                value=master.creative_config.get("synth", {}).get("release", 0.5)
            )
            ttk.Scale(
                frame, from_=0, to=2, variable=self.release, orient="horizontal"
            ).pack(fill="x", pady=2)
        elif self.mode == "lofi":
            ttk.Label(frame, text="Filter Cutoff (0.1-0.8):").pack(anchor="w")
            self.cutoff = tk.DoubleVar(
                value=master.creative_config.get("lofi", {}).get("cutoff", 0.5)
            )
            ttk.Scale(
                frame, from_=0.1, to=0.8, variable=self.cutoff, orient="horizontal"
            ).pack(fill="x", pady=2)
            ttk.Label(frame, text="Pitch Wobble Amount (0.0-0.5):").pack(
                anchor="w", pady=(10, 0)
            )
            self.pitch_wobble = tk.DoubleVar(
                value=master.creative_config.get("lofi", {}).get("pitch_wobble", 0.1)
            )
            ttk.Scale(
                frame, from_=0, to=0.5, variable=self.pitch_wobble, orient="horizontal"
            ).pack(fill="x", pady=2)

        ttk.Button(frame, text="Save Configuration", command=self.save).pack(
            side="bottom", pady=10
        )

    def save(self):
        try:
            if self.mode == "synth":
                resonance = self.resonance.get()
                release = self.release.get()
                
                # Validate ranges
                if not (0.0 <= resonance <= 1.0):
                    messagebox.showerror("Invalid Value", "Resonance must be between 0.0 and 1.0", parent=self)
                    return
                if not (0.0 <= release <= 2.0):
                    messagebox.showerror("Invalid Value", "Release time must be between 0.0 and 2.0", parent=self)
                    return
                    
                self.config = {
                    "resonance": resonance,
                    "release": release,
                }
            elif self.mode == "lofi":
                cutoff = self.cutoff.get()
                pitch_wobble = self.pitch_wobble.get()
                
                # Validate ranges
                if not (0.1 <= cutoff <= 0.8):
                    messagebox.showerror("Invalid Value", "Filter cutoff must be between 0.1 and 0.8", parent=self)
                    return
                if not (0.0 <= pitch_wobble <= 0.5):
                    messagebox.showerror("Invalid Value", "Pitch wobble must be between 0.0 and 0.5", parent=self)
                    return
                    
                self.config = {
                    "cutoff": cutoff,
                    "pitch_wobble": pitch_wobble,
                }

            self.master.creative_config[self.mode] = self.config
            logging.info(f"Updated creative config for '{self.mode}': {self.config}")
            messagebox.showinfo("Settings Saved", f"Configuration for '{self.mode}' mode has been saved.", parent=self)
            self.destroy()
            
        except Exception as e:
            logging.error(f"Error saving creative config: {e}")
            messagebox.showerror("Save Error", f"Failed to save configuration: {e}", parent=self)


class SCWToolWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master.root)
        self.title("Single-Cycle Waveform (SCW) Tool")
        self.geometry("600x400")
        self.master = master
        self.scw_files = []
        self.create_widgets()
        self.scan_for_scw()

    def create_widgets(self):
        frame = ttk.Frame(self, padding="10")
        frame.pack(fill="both", expand=True)
        ttk.Label(
            frame,
            text=f"Found potential SCWs (WAV files < {SCW_FRAME_THRESHOLD} frames):",
        ).pack(anchor="w")

        list_frame = ttk.Frame(frame)
        list_frame.pack(fill="both", expand=True, pady=5)
        self.listbox = tk.Listbox(list_frame, selectmode="extended")
        self.listbox.pack(side="left", fill="both", expand=True)
        vsb = ttk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        vsb.pack(side="right", fill="y")
        self.listbox.config(yscrollcommand=vsb.set)

        ttk.Button(
            frame,
            text="Create Looped Instruments from Selected",
            command=self.create_instruments,
        ).pack(pady=5)

    def scan_for_scw(self):
        folder = self.master.folder_path.get()
        wav_files = glob.glob(os.path.join(folder, "**", "*.wav"), recursive=True)
        for wav_path in wav_files:
            if get_wav_frames(wav_path) < SCW_FRAME_THRESHOLD:
                self.scw_files.append(wav_path)
                self.listbox.insert(tk.END, os.path.relpath(wav_path, folder))

    def create_instruments(self):
        selected_indices = self.listbox.curselection()
        if not selected_indices:
            messagebox.showwarning(
                "No Selection",
                "Please select one or more files from the list.",
                parent=self,
            )
            return

        selected_files = [self.scw_files[i] for i in selected_indices]

        options = InstrumentOptions(
            loop_one_shots=True,
            polyphony=1,
            firmware_version=self.master.firmware_version.get(),
        )

        builder = InstrumentBuilder(self.master.folder_path.get(), self.master, options)

        for file_path in selected_files:
            rel_path = os.path.relpath(file_path, self.master.folder_path.get())
            program_name = os.path.splitext(os.path.basename(file_path))[0]
            output_folder = os.path.dirname(file_path)
            builder._create_xpm(
                program_name, [rel_path], output_folder, mode="one-shot"
            )

        messagebox.showinfo(
            "Success", f"Created {len(selected_files)} looped instruments.", parent=self
        )
        self.destroy()


class BatchTransposeWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master.root)
        self.title("Batch Transpose XPM Files")
        self.geometry("650x500")
        self.master = master
        self.folder_path = tk.StringVar()
        self.transpose_amount = tk.DoubleVar(value=-24.0)
        self.relative_mode = tk.BooleanVar(value=False)
        self.intelligent_mode = tk.BooleanVar(value=False)
        self.recursive_search = tk.BooleanVar(value=True)
        self.create_backups = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="Ready")
        self.xpm_files = []
        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill="both", expand=True)
        main_frame.grid_rowconfigure(2, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)

        # Folder selection
        folder_frame = ttk.LabelFrame(main_frame, text="Select Folder", padding="10")
        folder_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        folder_frame.grid_columnconfigure(1, weight=1)
        
        ttk.Label(folder_frame, text="XPM Folder:").grid(row=0, column=0, sticky="w", padx=(0, 5))
        ttk.Entry(folder_frame, textvariable=self.folder_path).grid(row=0, column=1, sticky="ew", padx=(0, 5))
        ttk.Button(folder_frame, text="Browse...", command=self.browse_folder).grid(row=0, column=2)
        
        ttk.Button(folder_frame, text="Scan Folder", command=self.scan_folder).grid(row=0, column=3, padx=(5, 0))

        # Transpose settings
        settings_frame = ttk.LabelFrame(main_frame, text="Transpose Settings", padding="10")
        settings_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        settings_frame.grid_columnconfigure(1, weight=1)

        ttk.Label(settings_frame, text="Transpose Amount (semitones):").grid(row=0, column=0, sticky="w", pady=2)
        transpose_entry = ttk.Entry(settings_frame, textvariable=self.transpose_amount, width=10)
        transpose_entry.grid(row=0, column=1, sticky="w", padx=(5, 0), pady=2)
        
        # Quick preset buttons
        preset_frame = ttk.Frame(settings_frame)
        preset_frame.grid(row=0, column=2, sticky="e", padx=(10, 0))
        
        ttk.Button(preset_frame, text="-24 (Down 2 oct)", width=15,
                   command=lambda: self.transpose_amount.set(-24)).pack(side="left", padx=2)
        ttk.Button(preset_frame, text="-12 (Down 1 oct)", width=15,
                   command=lambda: self.transpose_amount.set(-12)).pack(side="left", padx=2)
        ttk.Button(preset_frame, text="+12 (Up 1 oct)", width=15,
                   command=lambda: self.transpose_amount.set(12)).pack(side="left", padx=2)
        
        ttk.Label(settings_frame, text="Mode:").grid(row=1, column=0, sticky="w", pady=(10, 2))
        mode_frame = ttk.Frame(settings_frame)
        mode_frame.grid(row=1, column=1, columnspan=2, sticky="w", padx=(5, 0), pady=(10, 2))
        
        ttk.Radiobutton(mode_frame, text="Set absolute value", 
                        variable=self.relative_mode, value=False).pack(side="left", padx=(0, 10))
        ttk.Radiobutton(mode_frame, text="Add to existing transpose",
                        variable=self.relative_mode, value=True).pack(side="left")

        # Intelligence mode
        intelligence_frame = ttk.Frame(settings_frame)
        intelligence_frame.grid(row=2, column=0, columnspan=3, sticky="w", pady=(10, 0))
        
        ttk.Checkbutton(intelligence_frame, text="🧠 Intelligent Mode - Auto-calculate optimal transpose for each XPM", 
                        variable=self.intelligent_mode).pack(side="left", padx=(0, 20))

        # Options
        options_frame = ttk.Frame(settings_frame)
        options_frame.grid(row=3, column=0, columnspan=3, sticky="w", pady=(5, 0))
        
        ttk.Checkbutton(options_frame, text="Search subfolders recursively", 
                        variable=self.recursive_search).pack(side="left", padx=(0, 20))
        ttk.Checkbutton(options_frame, text="Create backup files (.backup)", 
                        variable=self.create_backups).pack(side="left")

        # File list
        list_frame = ttk.LabelFrame(main_frame, text="XPM Files Found", padding="10")
        list_frame.grid(row=2, column=0, sticky="nsew", pady=(0, 10))
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        # Create treeview for file list
        self.tree = ttk.Treeview(list_frame, columns=("Path", "Current", "New", "Analysis"), show="headings")
        self.tree.heading("Path", text="File Path")
        self.tree.heading("Current", text="Current Transpose")
        self.tree.heading("New", text="New Transpose")
        self.tree.heading("Analysis", text="Issue/Notes")
        self.tree.column("Path", width=250)
        self.tree.column("Current", width=100, anchor="center")
        self.tree.column("New", width=100, anchor="center")
        self.tree.column("Analysis", width=200)
        self.tree.grid(row=0, column=0, sticky="nsew")

        tree_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        tree_scroll.grid(row=0, column=1, sticky="ns")
        self.tree.config(yscrollcommand=tree_scroll.set)

        # Action buttons and status
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.grid(row=3, column=0, sticky="ew")
        bottom_frame.grid_columnconfigure(0, weight=1)

        # Status
        status_frame = ttk.Frame(bottom_frame)
        status_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        status_frame.grid_columnconfigure(0, weight=1)
        ttk.Label(status_frame, textvariable=self.status_var).grid(row=0, column=0, sticky="w")

        # Buttons
        button_frame = ttk.Frame(bottom_frame)
        button_frame.grid(row=1, column=0, sticky="e")
        
        ttk.Button(button_frame, text="Preview Changes", command=self.preview_changes).pack(side="left", padx=5)
        ttk.Button(button_frame, text="🔧 Fix Key Ranges", command=self.fix_existing_key_ranges, 
                   ).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Apply Transpose", command=self.apply_transpose, 
                   style="Accent.TButton").pack(side="left", padx=5)
        ttk.Button(button_frame, text="Close", command=self.destroy).pack(side="left", padx=5)

        # Bind transpose amount change to update preview
        self.transpose_amount.trace_add("write", self.update_preview)
        self.relative_mode.trace_add("write", self.update_preview)
        self.intelligent_mode.trace_add("write", self.update_preview)

    def browse_folder(self):
        folder = filedialog.askdirectory(
            parent=self,
            title="Select Folder Containing XPM Files",
            initialdir=self.master.last_browse_path
        )
        if folder:
            self.folder_path.set(folder)
            self.master.last_browse_path = folder
            self.scan_folder()

    def scan_folder(self):
        folder = self.folder_path.get()
        if not folder or not os.path.isdir(folder):
            messagebox.showerror("Error", "Please select a valid folder first.", parent=self)
            return

        self.status_var.set("Scanning for XPM files...")
        self.tree.delete(*self.tree.get_children())
        self.xpm_files = []

        try:
            if self.recursive_search.get():
                pattern = os.path.join(folder, "**", "*.xpm")
                files = glob.glob(pattern, recursive=True)
            else:
                pattern = os.path.join(folder, "*.xpm")
                files = glob.glob(pattern)

            self.xpm_files = files
            self.update_file_list()
            
            if files:
                self.status_var.set(f"Found {len(files)} XPM file(s)")
            else:
                self.status_var.set("No XPM files found")
                
        except Exception as e:
            self.status_var.set(f"Error scanning folder: {e}")
            messagebox.showerror("Error", f"Error scanning folder: {e}", parent=self)

    def get_current_transpose(self, xpm_path):
        """Get current transpose value from XPM file."""
        try:
            tree = ET.parse(xpm_path)
            root = tree.getroot()
            transpose_elem = root.find(".//KeygroupMasterTranspose")
            if transpose_elem is not None and transpose_elem.text:
                return float(transpose_elem.text)
            return 0.0
        except Exception as e:
            logging.warning(f"Could not read transpose from {xpm_path}: {e}")
            return 0.0
    
    def analyze_xpm_pitch_issues(self, xpm_path):
        """Intelligently analyze XPM file to detect optimal transpose for C0-C8 playability."""
        try:
            tree = ET.parse(xpm_path)
            root = tree.getroot()
            
            # Get current master transpose
            current_transpose = self.get_current_transpose(xpm_path)
            
            # Analyze sample root notes and key ranges
            sample_notes = []
            key_ranges = []
            
            # Check modern format (ProgramPads JSON)
            pads_elem = root.find(".//ProgramPads-v2.10")
            if pads_elem is None:
                pads_elem = root.find(".//ProgramPads")
            if pads_elem is not None and pads_elem.text:
                try:
                    # Parse the JSON data
                    import json
                    from xml.sax.saxutils import unescape as xml_unescape
                    pads_data = json.loads(xml_unescape(pads_elem.text))
                    
                    if isinstance(pads_data, dict) and "pads" in pads_data:
                        pads = pads_data["pads"]
                        for pad_key, pad_data in pads.items():
                            if isinstance(pad_data, dict):
                                root_note = pad_data.get("rootNote")
                                if root_note is not None:
                                    sample_notes.append(int(root_note))
                except:
                    pass
            
            # Check legacy format (Layer elements)
            for layer in root.findall(".//Layer"):
                root_note_elem = layer.find("RootNote")
                if root_note_elem is not None and root_note_elem.text:
                    sample_notes.append(int(root_note_elem.text))
            
            # Check instrument key ranges
            for instrument in root.findall(".//Instrument"):
                low_note_elem = instrument.find("LowNote")
                high_note_elem = instrument.find("HighNote")
                if low_note_elem is not None and high_note_elem is not None:
                    if low_note_elem.text and high_note_elem.text:
                        low = int(low_note_elem.text)
                        high = int(high_note_elem.text)
                        key_ranges.append((low, high))
            
            # Calculate analysis
            analysis = {
                "current_transpose": current_transpose,
                "sample_notes": sample_notes,
                "key_ranges": key_ranges,
                "min_note": min(sample_notes) if sample_notes else 60,
                "max_note": max(sample_notes) if sample_notes else 60,
                "avg_note": sum(sample_notes) / len(sample_notes) if sample_notes else 60,
            }
            
            # Calculate optimal transpose for C0-C8 (0-96) playability
            optimal_transpose = self.calculate_optimal_transpose(analysis)
            
            analysis["recommended_transpose"] = optimal_transpose
            analysis["issue_detected"] = abs(current_transpose - optimal_transpose) > 1.0
            
            return analysis
            
        except Exception as e:
            logging.error(f"Error analyzing {xpm_path}: {e}")
            return {
                "current_transpose": 0.0,
                "sample_notes": [],
                "key_ranges": [],
                "min_note": 60,
                "max_note": 60,
                "avg_note": 60,
                "recommended_transpose": 0.0,
                "issue_detected": False,
                "error": str(e)
            }
    
    def calculate_optimal_transpose(self, analysis):
        """Calculate optimal transpose value for maximum keyboard playability."""
        sample_notes = analysis["sample_notes"]
        current_transpose = analysis["current_transpose"]
        
        # If we have sample data, use it
        if sample_notes and any(note > 0 for note in sample_notes):
            min_note = analysis["min_note"]
            max_note = analysis["max_note"]
            avg_note = analysis["avg_note"]
            
            # Calculate effective range with current transpose
            effective_min = min_note + current_transpose
            effective_max = max_note + current_transpose
            
            # Special cases for common issues:
            # 1. If instrument is playing 2+ octaves too high (common issue)
            if effective_min > 72:  # Everything above C5
                return -24.0  # Down 2 octaves
                
            # 2. If instrument is playing 1+ octave too high  
            elif effective_min > 60:  # Everything above C4
                return -12.0  # Down 1 octave
                
            # 3. If instrument is too low
            elif effective_max < 24:  # Everything below C2
                return 12.0   # Up 1 octave
                
            # 4. Center on a reasonable range
            else:
                # Target center around C3-C4 (48-60)
                target_center = 54  # F#3
                current_center = (effective_min + effective_max) / 2
                adjustment = target_center - (min_note + max_note) / 2
                return max(-48, min(48, adjustment))
        
        else:
            # No sample data found - make intelligent guess based on current transpose
            # This handles the case where XPM is a template without loaded samples
            
            # If current transpose is very high positive, it's likely too high
            if current_transpose > 12:
                return -24.0  # Bring it down significantly
            elif current_transpose > 0:
                return -12.0  # Bring it down moderately
            
            # If current transpose is very low negative, samples might be too low
            elif current_transpose < -36:
                return -24.0  # Still too low, but not as extreme
            elif current_transpose < -12:
                return -24.0  # Probably the right range for fixing C2->C4 issue
                
            # If transpose is in reasonable range, minimal adjustment
            else:
                # For the specific issue: C2 plays as C4 = need -24 semitones
                # This is the most common case for user's problem
                return -24.0
        
        # Fallback
        return -24.0

    def calculate_new_transpose(self, current_value, xpm_path=None):
        """Calculate new transpose value based on mode."""
        if self.intelligent_mode.get() and xpm_path:
            # Use intelligent analysis to determine optimal transpose
            analysis = self.analyze_xpm_pitch_issues(xpm_path)
            return analysis["recommended_transpose"]
        else:
            # Use manual transpose amount
            transpose_amount = self.transpose_amount.get()
            if self.relative_mode.get():
                return current_value + transpose_amount
            else:
                return transpose_amount

    def update_file_list(self):
        """Update the file list with current and new transpose values."""
        for xpm_path in self.xpm_files:
            rel_path = os.path.relpath(xpm_path, self.folder_path.get())
            current_transpose = self.get_current_transpose(xpm_path)
            
            # Get analysis information if in intelligent mode
            analysis_text = ""
            if self.intelligent_mode.get():
                analysis = self.analyze_xpm_pitch_issues(xpm_path)
                if analysis.get("issue_detected", False):
                    sample_notes = analysis.get("sample_notes", [])
                    if sample_notes:
                        min_note = min(sample_notes)
                        max_note = max(sample_notes)
                        if min_note > 72:
                            analysis_text = "Too high (>C5)"
                        elif min_note > 60:
                            analysis_text = "High (>C4)"
                        elif max_note < 24:
                            analysis_text = "Too low (<C2)"
                        elif current_transpose > 12:
                            analysis_text = f"High transpose (+{current_transpose:.1f})"
                        elif current_transpose < -12:
                            analysis_text = f"Low transpose ({current_transpose:.1f})"
                        else:
                            analysis_text = "Needs adjustment"
                    else:
                        analysis_text = "No samples found"
                else:
                    analysis_text = "OK"
                    
                if "error" in analysis:
                    analysis_text = "Parse error"
            
            new_transpose = self.calculate_new_transpose(current_transpose, xpm_path)
            
            self.tree.insert("", "end", values=(
                rel_path,
                f"{current_transpose:.1f}",
                f"{new_transpose:.1f}",
                analysis_text
            ))

    def update_preview(self, *args):
        """Update the preview when transpose amount or mode changes."""
        if hasattr(self, 'tree') and self.xpm_files:
            for i, item in enumerate(self.tree.get_children()):
                if i < len(self.xpm_files):
                    values = self.tree.item(item)["values"]
                    if len(values) >= 3:
                        current_transpose = float(values[1])
                        xpm_path = self.xpm_files[i]
                        new_transpose = self.calculate_new_transpose(current_transpose, xpm_path)
                        
                        # Update analysis if in intelligent mode
                        analysis_text = ""
                        if self.intelligent_mode.get():
                            analysis = self.analyze_xpm_pitch_issues(xpm_path)
                            if analysis.get("issue_detected", False):
                                analysis_text = "Needs adjustment"
                            else:
                                analysis_text = "OK"
                        
                        # Update the columns
                        self.tree.set(item, "New", f"{new_transpose:.1f}")
                        if len(self.tree.item(item)["values"]) >= 4:
                            self.tree.set(item, "Analysis", analysis_text)

    def preview_changes(self):
        """Show a preview of what changes will be made."""
        if not self.xpm_files:
            messagebox.showwarning("No Files", "Please scan for XPM files first.", parent=self)
            return

        preview_text = f"Transpose Settings:\n"
        if self.intelligent_mode.get():
            preview_text += f"• Mode: 🧠 Intelligent (auto-calculated per file)\n"
            preview_text += f"• Manual Amount: {self.transpose_amount.get()} semitones (ignored in intelligent mode)\n"
        else:
            preview_text += f"• Amount: {self.transpose_amount.get()} semitones\n"
            preview_text += f"• Mode: {'Relative (add to existing)' if self.relative_mode.get() else 'Absolute (set value)'}\n"
        preview_text += f"• Backups: {'Yes' if self.create_backups.get() else 'No'}\n"
        preview_text += f"• Files to process: {len(self.xpm_files)}\n\n"
        
        preview_text += "Sample changes:\n"
        count = 0
        for item in self.tree.get_children():
            if count >= 5:  # Show max 5 examples
                preview_text += f"... and {len(self.xpm_files) - count} more files\n"
                break
                
            values = self.tree.item(item)["values"]
            preview_text += f"• {values[0]}: {values[1]} → {values[2]} semitones\n"
            count += 1

        messagebox.showinfo("Preview Changes", preview_text, parent=self)

    def apply_transpose(self):
        """Apply the transpose changes to all XPM files."""
        if not self.xpm_files:
            messagebox.showwarning("No Files", "Please scan for XPM files first.", parent=self)
            return

        # Confirm with user
        if self.intelligent_mode.get():
            confirm_msg = (f"This will intelligently analyze and transpose {len(self.xpm_files)} XPM file(s) "
                          f"to optimize playability across C0-C8.\n\n"
                          f"Each file will be analyzed individually and transposed as needed.\n"
                          f"Backups: {'Yes' if self.create_backups.get() else 'No'}\n\n"
                          "This operation cannot be undone (except from backups). Continue?")
        else:
            confirm_msg = (f"This will modify {len(self.xpm_files)} XPM file(s) with transpose amount {self.transpose_amount.get()} semitones.\n\n"
                          f"Mode: {'Relative (add to existing)' if self.relative_mode.get() else 'Absolute (set value)'}\n"
                          f"Backups: {'Yes' if self.create_backups.get() else 'No'}\n\n"
                          "This operation cannot be undone (except from backups). Continue?")
        
        if not messagebox.askyesno("Confirm Transpose", confirm_msg, parent=self):
            return

        # Apply changes
        successful = 0
        errors = []
        
        for i, xpm_path in enumerate(self.xpm_files):
            try:
                self.status_var.set(f"Processing {i+1}/{len(self.xpm_files)}: {os.path.basename(xpm_path)}")
                self.update()  # Update GUI
                
                # Create backup if requested
                if self.create_backups.get():
                    backup_path = xpm_path + ".backup"
                    if not os.path.exists(backup_path):
                        shutil.copy2(xpm_path, backup_path)
                
                # Calculate new transpose value
                current_transpose = self.get_current_transpose(xpm_path)
                new_transpose = self.calculate_new_transpose(current_transpose, xpm_path)
                
                # Parse and modify XPM
                tree = ET.parse(xpm_path)
                root = tree.getroot()
                
                # Find or create KeygroupMasterTranspose element
                transpose_elem = root.find(".//KeygroupMasterTranspose")
                if transpose_elem is None:
                    program_elem = root.find(".//Program")
                    if program_elem is not None:
                        transpose_elem = ET.SubElement(program_elem, "KeygroupMasterTranspose")
                    else:
                        errors.append(f"{os.path.basename(xpm_path)}: Could not find Program element")
                        continue
                
                # Set new value
                transpose_elem.text = f"{new_transpose:.6f}"
                
                # CRITICAL FIX: Update keygroup ranges to ensure full keyboard playability
                # This prevents issues where notes above certain ranges don't play after transpose
                self.fix_keygroup_ranges_after_transpose(root, current_transpose, new_transpose)
                
                # Save file
                tree.write(xpm_path, encoding="utf-8", xml_declaration=True)
                successful += 1
                
            except Exception as e:
                errors.append(f"{os.path.basename(xpm_path)}: {str(e)}")

        # Show results
        self.status_var.set(f"Complete: {successful}/{len(self.xpm_files)} files processed")
        
        result_msg = f"Successfully processed {successful} out of {len(self.xpm_files)} files."
        if errors:
            result_msg += f"\n\nErrors ({len(errors)}):\n" + "\n".join(errors[:10])
            if len(errors) > 10:
                result_msg += f"\n... and {len(errors) - 10} more errors"
        
        messagebox.showinfo("Transpose Complete", result_msg, parent=self)
        
        # Refresh the file list to show new values
        self.scan_folder()

    def fix_keygroup_ranges_after_transpose(self, root, old_transpose, new_transpose):
        """
        CRITICAL FIX: Update keygroup LowNote/HighNote ranges after transpose to ensure FULL keyboard playability.
        
        Problem: When transposing by -24 semitones, the KeygroupMasterTranspose changes but individual
        keygroup ranges (LowNote/HighNote) may restrict playability to only the original range.
        This causes notes C5 (72) and above to not play even though the samples are transposed correctly.
        
        Solution: AGGRESSIVELY expand keygroup ranges to ensure COMPLETE keyboard coverage C0-C8 (0-96).
        The user reported C5 plays but C6, C7, C8 don't - this means we need FULL range expansion.
        """
        instruments = root.findall(".//Instrument")
        transpose_change = new_transpose - old_transpose
        
        logging.info(f"🔧 KEYGROUP RANGE FIX: Transpose change = {transpose_change:.1f} semitones")
        
        for i, instrument in enumerate(instruments):
            low_note_elem = instrument.find("LowNote")
            high_note_elem = instrument.find("HighNote")
            
            if low_note_elem is not None and high_note_elem is not None:
                try:
                    current_low = int(low_note_elem.text) if low_note_elem.text else 60
                    current_high = int(high_note_elem.text) if high_note_elem.text else 60
                    
                    # 🎯 AGGRESSIVE STRATEGY: ALWAYS ensure full keyboard playability
                    # The user needs C0-C8 (0-96) to work, not just partial ranges
                    
                    # Strategy 1: ANY transpose operation gets FULL keyboard range
                    # This ensures C6, C7, C8 will ALWAYS play regardless of original range
                    if abs(transpose_change) >= 6:  # Any significant transpose (half octave+)
                        new_low = 0    # C0 - Full low range
                        new_high = 127 # G9 - Full high range (beyond C8 for safety)
                        logging.info(f"KG{i+1}: FULL EXPANSION for transpose {transpose_change:.1f}: {current_low}-{current_high} → {new_low}-{new_high}")
                    
                    # Strategy 2: Small transpose but limited original range - still expand aggressively
                    elif current_high < 96:  # Original range doesn't reach C7 (96)
                        new_low = max(0, current_low - 12)  # Extend down 1 octave
                        new_high = 127  # Full high range to ensure C6, C7, C8 play
                        logging.info(f"KG{i+1}: AGGRESSIVE EXPANSION for limited range: {current_low}-{current_high} → {new_low}-{new_high}")
                    
                    # Strategy 3: Single-note keygroups always get full range
                    elif current_low == current_high:
                        new_low = 0    # C0
                        new_high = 127 # G9 
                        logging.info(f"KG{i+1}: SINGLE-NOTE EXPANSION: {current_low} → full range (0-127)")
                    
                    # Strategy 4: Range already adequate but ensure C8 coverage
                    else:
                        new_low = max(0, min(current_low, current_low - 6))  # Extend down slightly
                        new_high = 127  # Always ensure full high range for C6, C7, C8
                        logging.info(f"KG{i+1}: SAFETY EXPANSION: {current_low}-{current_high} → {new_low}-{new_high}")
                    
                    # 🎯 VERIFICATION: Ensure we can play the full keyboard after transpose
                    effective_low_after = new_low + new_transpose
                    effective_high_after = new_high + new_transpose
                    
                    # Double-check that C6 (84), C7 (96), C8 (108) will be playable
                    if effective_high_after < 108:  # Less than C8
                        logging.warning(f"KG{i+1}: Effective high {effective_high_after:.1f} < C8 (108), forcing full range")
                        new_high = 127  # Force maximum range
                    
                    # Apply the new ranges
                    low_note_elem.text = str(new_low)
                    high_note_elem.text = str(new_high)
                    
                    logging.info(f"KG{i+1}: ✅ Final range: {new_low}-{new_high} (effective after transpose: {effective_low_after:.1f}-{effective_high_after:.1f})")
                    
                except (ValueError, TypeError) as e:
                    # If there are invalid values, set to full range as failsafe
                    logging.warning(f"Invalid note values in keygroup {i+1}, setting to full range: {e}")
                    if low_note_elem is not None:
                        low_note_elem.text = "0"
                    if high_note_elem is not None:
                        high_note_elem.text = "127"

    def fix_existing_key_ranges(self):
        """Fix key ranges in existing XPM files that may have playability issues."""
        if not self.xpm_files:
            messagebox.showwarning("No Files", "Please scan for XPM files first.", parent=self)
            return
        
        confirm_msg = (f"This will analyze and fix key range issues in {len(self.xpm_files)} XPM file(s).\n\n"
                      "This addresses the issue where notes C5 and above don't play after transposing.\n"
                      "Key ranges will be expanded to ensure full keyboard playability.\n\n"
                      f"Backups: {'Yes' if self.create_backups.get() else 'No'}\n\n"
                      "Continue?")
        
        if not messagebox.askyesno("Fix Key Ranges", confirm_msg, parent=self):
            return
        
        fixed_count = 0
        errors = []
        
        for i, xpm_path in enumerate(self.xpm_files):
            try:
                self.status_var.set(f"Fixing {i+1}/{len(self.xpm_files)}: {os.path.basename(xpm_path)}")
                self.update()
                
                # Create backup if requested
                if self.create_backups.get():
                    backup_path = xpm_path + ".keyfix.backup"
                    if not os.path.exists(backup_path):
                        shutil.copy2(xpm_path, backup_path)
                
                # Parse XPM
                tree = ET.parse(xpm_path)
                root = tree.getroot()
                
                # Check if file needs fixing
                needs_fix = False
                instruments = root.findall(".//Instrument")
                
                for instrument in instruments:
                    low_note_elem = instrument.find("LowNote")
                    high_note_elem = instrument.find("HighNote")
                    
                    if low_note_elem is not None and high_note_elem is not None:
                        try:
                            low_note = int(low_note_elem.text) if low_note_elem.text else 0
                            high_note = int(high_note_elem.text) if high_note_elem.text else 127
                            
                            # Check for common issues
                            if (low_note == high_note or  # Single note keygroups
                                high_note < 84 or         # Limited high range (less than C6)
                                low_note > high_note):    # Invalid range
                                needs_fix = True
                                break
                        except (ValueError, TypeError):
                            needs_fix = True
                            break
                
                if needs_fix:
                    # Apply the ENHANCED fixing logic - same as after transpose
                    # Use aggressive expansion to ensure FULL keyboard coverage (C0-C8)
                    current_transpose = self.get_current_transpose(xpm_path)
                    
                    # Force aggressive expansion for existing range issues
                    instruments = root.findall(".//Instrument")
                    for i, instrument in enumerate(instruments):
                        low_note_elem = instrument.find("LowNote")
                        high_note_elem = instrument.find("HighNote")
                        
                        if low_note_elem is not None and high_note_elem is not None:
                            try:
                                current_low = int(low_note_elem.text) if low_note_elem.text else 60
                                current_high = int(high_note_elem.text) if high_note_elem.text else 60
                                
                                # AGGRESSIVE EXPANSION for existing files with range issues
                                # These files need full keyboard access immediately
                                new_low = 0    # C0 - Full low range
                                new_high = 127 # G9 - Full high range (ensures C6, C7, C8)
                                
                                low_note_elem.text = str(new_low)
                                high_note_elem.text = str(new_high)
                                
                                logging.info(f"Fixed KG{i+1}: {current_low}-{current_high} → {new_low}-{new_high} (FULL keyboard access)")
                                
                            except (ValueError, TypeError) as e:
                                logging.warning(f"Invalid note values in keygroup {i+1}, setting to full range: {e}")
                                if low_note_elem is not None:
                                    low_note_elem.text = "0"
                                if high_note_elem is not None:
                                    high_note_elem.text = "127"
                    
                    # Save file
                    tree.write(xpm_path, encoding="utf-8", xml_declaration=True)
                    fixed_count += 1
                    
            except Exception as e:
                errors.append(f"{os.path.basename(xpm_path)}: {str(e)}")
        
        # Show results
        result_msg = f"Analyzed {len(self.xpm_files)} files, fixed key ranges in {fixed_count} files."
        if errors:
            result_msg += f"\n\nErrors ({len(errors)}):\n" + "\n".join(errors[:5])
            if len(errors) > 5:
                result_msg += f"\n... and {len(errors) - 5} more errors"
        
        messagebox.showinfo("Key Range Fix Complete", result_msg, parent=self)
        self.status_var.set(f"Fixed key ranges in {fixed_count} files.")

    def open_advanced_xpm_doctor(self):
        """Open the Advanced XPM Doctor window."""
        try:
            if not self.xpm_files:
                messagebox.showwarning("No Files", "Please scan for XPM files first before using Advanced XPM Doctor.", parent=self)
                return
            AdvancedXpmDoctorWindow(self, self.xpm_files)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open Advanced XPM Doctor: {e}", parent=self)


class AdvancedXpmDoctorWindow(tk.Toplevel):
    """Advanced XPM Doctor - Comprehensive analysis and fixing of XPM file issues."""
    
    def __init__(self, parent, xpm_files):
        super().__init__(parent)
        self.title("🩺 Advanced XPM Doctor - Comprehensive File Analysis")
        self.geometry("900x700")
        self.parent = parent
        self.xpm_files = xpm_files
        self.analysis_results = []
        self.create_widgets()
        self.analyze_all_files()
    
    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill="both", expand=True)
        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        
        # Header
        header_frame = ttk.Frame(main_frame)
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header_frame.grid_columnconfigure(1, weight=1)
        
        ttk.Label(header_frame, text="🩺 Advanced XPM Doctor", 
                  font=("Arial", 14, "bold")).grid(row=0, column=0, sticky="w")
        
        self.status_var = tk.StringVar(value="Analyzing files...")
        ttk.Label(header_frame, textvariable=self.status_var).grid(row=0, column=1, sticky="e")
        
        # Analysis results tree
        tree_frame = ttk.LabelFrame(main_frame, text="File Analysis Results", padding="10")
        tree_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Create treeview with detailed columns
        self.tree = ttk.Treeview(tree_frame, columns=("Status", "Issues", "Keygroups", "Ranges", "Fixes"), show="headings")
        self.tree.heading("#0", text="File")
        self.tree.heading("Status", text="Status")
        self.tree.heading("Issues", text="Critical Issues")
        self.tree.heading("Keygroups", text="Keygroups")
        self.tree.heading("Ranges", text="Range Issues")
        self.tree.heading("Fixes", text="Recommended Fixes")
        
        self.tree.column("Status", width=100, anchor="center")
        self.tree.column("Issues", width=150)
        self.tree.column("Keygroups", width=100, anchor="center")
        self.tree.column("Ranges", width=150)
        self.tree.column("Fixes", width=200)
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        
        tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        tree_scroll.grid(row=0, column=1, sticky="ns")
        self.tree.config(yscrollcommand=tree_scroll.set)
        
        # Bind double-click to show detailed analysis
        self.tree.bind("<Double-1>", self.show_detailed_analysis)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)
        
        left_buttons = ttk.Frame(button_frame)
        left_buttons.grid(row=0, column=0, sticky="w")
        
        ttk.Button(left_buttons, text="🔍 Re-Analyze", command=self.analyze_all_files).pack(side="left", padx=5)
        ttk.Button(left_buttons, text="📋 Export Report", command=self.export_report).pack(side="left", padx=5)
        
        right_buttons = ttk.Frame(button_frame)
        right_buttons.grid(row=0, column=1, sticky="e")
        
        ttk.Button(right_buttons, text="🔧 Fix Selected Issues", command=self.fix_selected_issues).pack(side="left", padx=5)
        ttk.Button(right_buttons, text="🩹 Fix All Issues", command=self.fix_all_issues, 
                   style="Accent.TButton").pack(side="left", padx=5)
        ttk.Button(right_buttons, text="Close", command=self.destroy).pack(side="left", padx=5)
    
    def analyze_xpm_file(self, xpm_path):
        """Comprehensive analysis of an XPM file."""
        try:
            tree = ET.parse(xpm_path)
            root = tree.getroot()
            
            analysis = {
                'file_path': xpm_path,
                'file_name': os.path.basename(xpm_path),
                'issues': [],
                'critical_issues': [],
                'warnings': [],
                'fix_suggestions': []
            }
            
            # Check format - Look for KeygroupLegacyMode to determine format type
            legacy_mode_elem = root.find(".//KeygroupLegacyMode")
            if legacy_mode_elem is not None:
                is_legacy = legacy_mode_elem.text == "True"
                analysis['format'] = 'Legacy MPC' if is_legacy else 'MPC-V (Advanced)'
            else:
                analysis['format'] = 'Legacy MPC'  # Default for older files
            
            # Analyze KeygroupMasterTranspose
            transpose_elem = root.find(".//KeygroupMasterTranspose")
            if transpose_elem is not None:
                try:
                    transpose_value = float(transpose_elem.text) if transpose_elem.text else 0.0
                    analysis['master_transpose'] = transpose_value
                except ValueError:
                    analysis['issues'].append("Invalid transpose value")
                    analysis['master_transpose'] = 0.0
            else:
                analysis['master_transpose'] = 0.0
            
            # CRITICAL FIX: Count keygroups correctly based on MPC structure
            # The declared count comes from KeygroupNumKeygroups
            keygroup_count_elem = root.find(".//KeygroupNumKeygroups")
            declared_count = 0
            if keygroup_count_elem is not None:
                try:
                    declared_count = int(keygroup_count_elem.text) if keygroup_count_elem.text else 0
                except ValueError:
                    analysis['issues'].append("Invalid keygroup count")
            
            # CORRECT METHOD: Count actual active keygroups
            # MPC uses the ProgramPads JSON to determine active keygroups, not <Keygroup> elements
            active_keygroups = 0
            keygroup_ranges = []
            
            # Try to parse ProgramPads JSON for accurate keygroup count
            pads_elem = root.find(".//ProgramPads-v2.10")
            if pads_elem is not None and pads_elem.text:
                try:
                    # Unescape XML entities
                    from xml.sax.saxutils import unescape as xml_unescape
                    json_text = xml_unescape(pads_elem.text)
                    import json
                    pads_data = json.loads(json_text)
                    
                    # Extract keygroup information from JSON
                    if isinstance(pads_data, dict):
                        # Look for pads data structure
                        if "ProgramPads-v2.10" in pads_data:
                            pads_content = pads_data["ProgramPads-v2.10"]
                            if "pads" in pads_content:
                                pads = pads_content["pads"]
                                # Count active pads/keygroups
                                for pad_key, pad_data in pads.items():
                                    if isinstance(pad_data, dict) and pad_data.get("sampleName"):
                                        active_keygroups += 1
                                        
                                        # Extract range information
                                        low_note = pad_data.get("lowNote", 0)
                                        high_note = pad_data.get("highNote", 127)
                                        if low_note is not None and high_note is not None:
                                            keygroup_ranges.append({
                                                'kg': active_keygroups,
                                                'low': int(low_note),
                                                'high': int(high_note)
                                            })
                                            
                except (json.JSONDecodeError, KeyError, AttributeError) as e:
                    # Fallback: JSON parsing failed, count non-empty Instrument elements
                    analysis['warnings'].append(f"Could not parse ProgramPads JSON: {e}")
                    instruments = root.findall(".//Instrument")
                    for i, instrument in enumerate(instruments):
                        # Check if instrument has layers with samples
                        layers = instrument.findall(".//Layer")
                        has_samples = False
                        for layer in layers:
                            sample_name_elem = layer.find("SampleName")
                            if sample_name_elem is not None and sample_name_elem.text:
                                has_samples = True
                                break
                        
                        if has_samples:
                            active_keygroups += 1
                            
                            # Get range from instrument
                            low_note_elem = instrument.find("LowNote")
                            high_note_elem = instrument.find("HighNote")
                            if low_note_elem is not None and high_note_elem is not None:
                                try:
                                    low_note = int(low_note_elem.text) if low_note_elem.text else 0
                                    high_note = int(high_note_elem.text) if high_note_elem.text else 127
                                    keygroup_ranges.append({
                                        'kg': i + 1,
                                        'low': low_note,
                                        'high': high_note
                                    })
                                except ValueError:
                                    pass
            else:
                # No ProgramPads JSON - likely a template or broken file
                analysis['warnings'].append("No ProgramPads-v2.10 data found")
                # Count non-empty Instrument elements as fallback
                instruments = root.findall(".//Instrument")
                for i, instrument in enumerate(instruments):
                    layers = instrument.findall(".//Layer")
                    has_samples = False
                    for layer in layers:
                        sample_name_elem = layer.find("SampleName") 
                        if sample_name_elem is not None and sample_name_elem.text:
                            has_samples = True
                            break
                    
                    if has_samples:
                        active_keygroups += 1
            
            # Analyze range issues
            range_issues = []
            for kg_range in keygroup_ranges:
                low_note = kg_range['low']
                high_note = kg_range['high']
                
                # Check for range issues that prevent C5+ playability
                if low_note == high_note:
                    range_issues.append(f"KG{kg_range['kg']}: Single-note ({low_note})")
                elif low_note > high_note:
                    analysis['critical_issues'].append(f"KG{kg_range['kg']}: Invalid range ({low_note}>{high_note})")
                elif high_note < 72:  # Less than C5
                    range_issues.append(f"KG{kg_range['kg']}: Limited to {high_note} (C5+ blocked)")
                elif high_note < 84:  # Less than C6  
                    range_issues.append(f"KG{kg_range['kg']}: Range {low_note}-{high_note} (C6+ limited)")
            
            analysis['declared_keygroup_count'] = declared_count
            analysis['actual_keygroup_count'] = active_keygroups
            analysis['keygroup_ranges'] = keygroup_ranges
            analysis['range_issues'] = range_issues
            
            # Check keygroup count mismatch
            if declared_count != active_keygroups:
                if active_keygroups == 0:
                    analysis['critical_issues'].append(f"Empty file: Declared {declared_count} KGs, found 0")
                else:
                    analysis['issues'].append(f"Count mismatch: Declared {declared_count}, actual {active_keygroups}")
            
            # Generate fix suggestions
            if declared_count != active_keygroups:
                analysis['fix_suggestions'].append(f"Update keygroup count to {active_keygroups}")
            
            if range_issues:
                analysis['fix_suggestions'].append("Expand keygroup ranges for full keyboard access")
            
            if any("Single-note" in issue for issue in range_issues):
                analysis['fix_suggestions'].append("Convert single-note keygroups to full range")
            
            # Determine overall status
            if analysis['critical_issues']:
                analysis['status'] = 'CRITICAL'
            elif analysis['issues'] or range_issues:
                analysis['status'] = 'NEEDS_FIXING'
            elif analysis['warnings']:
                analysis['status'] = 'WARNINGS'
            else:
                analysis['status'] = 'OK'
            
            return analysis
            
        except Exception as e:
            return {
                'file_path': xpm_path,
                'file_name': os.path.basename(xpm_path),
                'error': str(e),
                'status': 'ERROR',
                'issues': [f"Parse error: {e}"],
                'critical_issues': [],
                'warnings': [],
                'fix_suggestions': []
            }
    
    def analyze_all_files(self):
        """Analyze all XPM files and populate the tree."""
        self.status_var.set("Analyzing files...")
        self.tree.delete(*self.tree.get_children())
        self.analysis_results = []
        
        for i, xpm_path in enumerate(self.xpm_files):
            self.status_var.set(f"Analyzing {i+1}/{len(self.xpm_files)}: {os.path.basename(xpm_path)}")
            self.update()
            
            analysis = self.analyze_xpm_file(xpm_path)
            self.analysis_results.append(analysis)
            
            # Determine status icon
            status_icon = {
                'CRITICAL': '🚨 CRITICAL',
                'NEEDS_FIXING': '⚠️ ISSUES',
                'WARNINGS': '⚠️ WARNINGS', 
                'OK': '✅ OK',
                'ERROR': '❌ ERROR'
            }.get(analysis['status'], '❓ UNKNOWN')
            
            # Format issues for display
            critical_issues = "; ".join(analysis['critical_issues'][:2])
            if len(analysis['critical_issues']) > 2:
                critical_issues += f" (+{len(analysis['critical_issues'])-2} more)"
            
            range_issues_str = "; ".join(analysis.get('range_issues', [])[:2])
            if len(analysis.get('range_issues', [])) > 2:
                range_issues_str += f" (+{len(analysis.get('range_issues', []))-2} more)"
            
            keygroups_str = f"{analysis.get('actual_keygroup_count', 0)}/{analysis.get('declared_keygroup_count', 0)}"
            
            fixes_str = "; ".join(analysis['fix_suggestions'][:2])
            if len(analysis['fix_suggestions']) > 2:
                fixes_str += f" (+{len(analysis['fix_suggestions'])-2} more)"
            
            # Insert into tree
            self.tree.insert("", "end", text=analysis['file_name'], values=(
                status_icon,
                critical_issues,
                keygroups_str,
                range_issues_str,
                fixes_str
            ))
        
        # Summary
        critical_count = sum(1 for r in self.analysis_results if r['status'] == 'CRITICAL')
        issues_count = sum(1 for r in self.analysis_results if r['status'] == 'NEEDS_FIXING')
        ok_count = sum(1 for r in self.analysis_results if r['status'] == 'OK')
        
        self.status_var.set(f"Analysis complete: {critical_count} critical, {issues_count} with issues, {ok_count} OK")
    
    def show_detailed_analysis(self, event):
        """Show detailed analysis for selected file."""
        selection = self.tree.selection()
        if not selection:
            return
        
        item = selection[0]
        index = self.tree.index(item)
        if index < len(self.analysis_results):
            analysis = self.analysis_results[index]
            DetailedAnalysisWindow(self, analysis)
    
    def fix_selected_issues(self):
        """Fix issues in selected files."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select files to fix.", parent=self)
            return
        
        selected_indices = [self.tree.index(item) for item in selection]
        selected_analyses = [self.analysis_results[i] for i in selected_indices]
        
        self.apply_fixes(selected_analyses)
    
    def fix_all_issues(self):
        """Fix issues in all files that need fixing."""
        analyses_to_fix = [a for a in self.analysis_results if a['status'] in ['CRITICAL', 'NEEDS_FIXING']]
        
        if not analyses_to_fix:
            messagebox.showinfo("No Issues", "No files need fixing!", parent=self)
            return
        
        confirm_msg = (f"This will attempt to fix issues in {len(analyses_to_fix)} XPM file(s).\n\n"
                      "Fixes include:\n"
                      "• Updating keygroup counts\n"
                      "• Expanding keygroup ranges for full keyboard access\n"
                      "• Fixing range validation issues\n\n"
                      f"Backups: {'Yes' if hasattr(self.parent, 'create_backups') and self.parent.create_backups.get() else 'Recommended'}\n\n"
                      "Continue?")
        
        if messagebox.askyesno("Fix All Issues", confirm_msg, parent=self):
            self.apply_fixes(analyses_to_fix)
    
    def apply_fixes(self, analyses_to_fix):
        """Apply fixes to the specified analyses."""
        fixed_count = 0
        errors = []
        
        for i, analysis in enumerate(analyses_to_fix):
            try:
                self.status_var.set(f"Fixing {i+1}/{len(analyses_to_fix)}: {analysis['file_name']}")
                self.update()
                
                xpm_path = analysis['file_path']
                
                # Create backup if parent has the option
                if hasattr(self.parent, 'create_backups') and self.parent.create_backups.get():
                    backup_path = xpm_path + ".doctor.backup"
                    if not os.path.exists(backup_path):
                        shutil.copy2(xpm_path, backup_path)
                
                # Parse and modify XPM
                tree = ET.parse(xpm_path)
                root = tree.getroot()
                
                # Fix 1: Update keygroup count to match actual active keygroups
                if analysis.get('declared_keygroup_count', 0) != analysis.get('actual_keygroup_count', 0):
                    keygroup_count_elem = root.find(".//KeygroupNumKeygroups")
                    if keygroup_count_elem is not None:
                        keygroup_count_elem.text = str(analysis['actual_keygroup_count'])
                        logging.info(f"Fixed keygroup count: {analysis['declared_keygroup_count']} → {analysis['actual_keygroup_count']}")
                
                # Fix 2: Expand instrument ranges for full keyboard access
                # Real MPC files use <Instrument> elements with <LowNote>/<HighNote>
                instruments = root.findall(".//Instrument")
                ranges_fixed = 0
                
                for kg_range in analysis.get('keygroup_ranges', []):
                    kg_index = kg_range['kg'] - 1  # Convert to 0-based index
                    
                    if kg_index < len(instruments):
                        instrument = instruments[kg_index]
                        
                        # Find LowNote and HighNote elements directly in the Instrument
                        low_note_elem = instrument.find("LowNote")
                        high_note_elem = instrument.find("HighNote")
                        
                        # If elements don't exist, create them
                        if low_note_elem is None:
                            low_note_elem = ET.SubElement(instrument, "LowNote")
                        if high_note_elem is None:
                            high_note_elem = ET.SubElement(instrument, "HighNote")
                        
                        # Apply aggressive range expansion for full keyboard access
                        # Expand if: limited range (< C6), single note, or invalid range
                        if (kg_range['high'] < 84 or 
                            kg_range['low'] == kg_range['high'] or 
                            kg_range['low'] > kg_range['high']):
                            
                            old_range = f"{kg_range['low']}-{kg_range['high']}"
                            low_note_elem.text = "0"    # C0
                            high_note_elem.text = "127" # G9
                            ranges_fixed += 1
                            logging.info(f"Expanded KG{kg_range['kg']} range: {old_range} → 0-127")
                
                # Fix 3: Update ProgramPads JSON if ranges were changed
                # This ensures the MPC recognizes the expanded ranges
                if ranges_fixed > 0:
                    pads_elem = root.find(".//ProgramPads-v2.10")
                    if pads_elem is not None and pads_elem.text:
                        try:
                            from xml.sax.saxutils import unescape as xml_unescape, escape as xml_escape
                            import json
                            
                            # Unescape and parse JSON
                            json_text = xml_unescape(pads_elem.text)
                            pads_data = json.loads(json_text)
                            
                            # Update pad ranges in JSON
                            if isinstance(pads_data, dict) and "ProgramPads-v2.10" in pads_data:
                                pads_content = pads_data["ProgramPads-v2.10"]
                                if "pads" in pads_content:
                                    pads = pads_content["pads"]
                                    for pad_key, pad_data in pads.items():
                                        if isinstance(pad_data, dict) and pad_data.get("sampleName"):
                                            # Expand pad ranges to 0-127
                                            if (pad_data.get("highNote", 127) < 84 or 
                                                pad_data.get("lowNote", 0) == pad_data.get("highNote", 127)):
                                                pad_data["lowNote"] = 0
                                                pad_data["highNote"] = 127
                            elif isinstance(pads_data, dict) and "pads" in pads_data:
                                # Handle direct pads structure
                                pads = pads_data["pads"]
                                for pad_key, pad_data in pads.items():
                                    if isinstance(pad_data, dict) and pad_data.get("sampleName"):
                                        # Expand pad ranges to 0-127
                                        if (pad_data.get("highNote", 127) < 84 or 
                                            pad_data.get("lowNote", 0) == pad_data.get("highNote", 127)):
                                            pad_data["lowNote"] = 0
                                            pad_data["highNote"] = 127
                            
                            # Re-escape and save JSON
                            updated_json = json.dumps(pads_data, separators=(',', ':'))
                            pads_elem.text = xml_escape(updated_json)
                            logging.info(f"Updated ProgramPads JSON ranges")
                            
                        except (json.JSONDecodeError, KeyError) as e:
                            logging.warning(f"Could not update ProgramPads JSON: {e}")
                
                # Save file with proper XML declaration
                tree.write(xpm_path, encoding="utf-8", xml_declaration=True)
                fixed_count += 1
                logging.info(f"Successfully fixed {analysis['file_name']}")
                
            except Exception as e:
                error_msg = f"{analysis['file_name']}: {str(e)}"
                errors.append(error_msg)
                logging.error(f"Failed to fix {analysis['file_name']}: {e}")
        
        # Show results
        result_msg = f"Successfully fixed {fixed_count} out of {len(analyses_to_fix)} files."
        if errors:
            result_msg += f"\n\nErrors ({len(errors)}):\n" + "\n".join(errors[:5])
            if len(errors) > 5:
                result_msg += f"\n... and {len(errors) - 5} more errors"
        
        messagebox.showinfo("Fix Complete", result_msg, parent=self)
        
        # Re-analyze to show updated results
        self.analyze_all_files()
    
    def export_report(self):
        """Export analysis report to a text file."""
        try:
            report_path = filedialog.asksaveasfilename(
                parent=self,
                title="Export Analysis Report",
                defaultextension=".txt",
                filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
            )
            
            if report_path:
                with open(report_path, 'w', encoding='utf-8') as f:
                    f.write("🩺 ADVANCED XPM DOCTOR - ANALYSIS REPORT\n")
                    f.write("=" * 60 + "\n\n")
                    
                    for analysis in self.analysis_results:
                        f.write(f"📁 FILE: {analysis['file_name']}\n")
                        f.write("-" * 40 + "\n")
                        f.write(f"Status: {analysis['status']}\n")
                        f.write(f"Format: {analysis.get('format', 'Unknown')}\n")
                        f.write(f"Master Transpose: {analysis.get('master_transpose', 0):.1f} semitones\n")
                        f.write(f"Keygroups: {analysis.get('actual_keygroup_count', 0)} active "
                               f"(declared: {analysis.get('declared_keygroup_count', 0)})\n")
                        
                        if analysis['critical_issues']:
                            f.write(f"\nCRITICAL ISSUES:\n")
                            for issue in analysis['critical_issues']:
                                f.write(f"  • {issue}\n")
                        
                        if analysis['issues']:
                            f.write(f"\nISSUES:\n")
                            for issue in analysis['issues']:
                                f.write(f"  • {issue}\n")
                        
                        if analysis.get('range_issues'):
                            f.write(f"\nRANGE ISSUES:\n")
                            for issue in analysis['range_issues']:
                                f.write(f"  • {issue}\n")
                        
                        if analysis['fix_suggestions']:
                            f.write(f"\nRECOMMENDED FIXES:\n")
                            for fix in analysis['fix_suggestions']:
                                f.write(f"  • {fix}\n")
                        
                        f.write("\n" + "=" * 60 + "\n\n")
                
                messagebox.showinfo("Export Complete", f"Report exported to: {report_path}", parent=self)
                
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export report: {e}", parent=self)


class DetailedAnalysisWindow(tk.Toplevel):
    """Show detailed analysis for a single XPM file."""
    
    def __init__(self, parent, analysis):
        super().__init__(parent)
        self.title(f"📋 Detailed Analysis - {analysis['file_name']}")
        self.geometry("600x500")
        self.analysis = analysis
        self.create_widgets()
    
    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(fill="both", expand=True)
        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        
        # Header
        header_frame = ttk.Frame(main_frame)
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        
        ttk.Label(header_frame, text=f"📁 {self.analysis['file_name']}", 
                  font=("Arial", 12, "bold")).pack(anchor="w")
        ttk.Label(header_frame, text=f"Status: {self.analysis['status']} | "
                                     f"Format: {self.analysis.get('format', 'Unknown')}").pack(anchor="w")
        
        # Details in scrollable text
        text_frame = ttk.Frame(main_frame)
        text_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 15))
        text_frame.grid_rowconfigure(0, weight=1)
        text_frame.grid_columnconfigure(0, weight=1)
        
        self.text_widget = tk.Text(text_frame, wrap="word", font=("Consolas", 10))
        self.text_widget.grid(row=0, column=0, sticky="nsew")
        
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.text_widget.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.text_widget.config(yscrollcommand=scrollbar.set)
        
        # Populate details
        self.populate_details()
        
        # Close button
        ttk.Button(main_frame, text="Close", command=self.destroy).grid(row=2, column=0)
    
    def populate_details(self):
        """Populate the text widget with detailed analysis."""
        details = "🩺 DETAILED ANALYSIS REPORT\n"
        details += "=" * 50 + "\n\n"
        details += "📋 BASIC INFORMATION:\n"
        details += f"• File: {self.analysis['file_name']}\n"
        details += f"• Status: {self.analysis['status']}\n"
        details += f"• Format: {self.analysis.get('format', 'Unknown')}\n"
        details += f"• Master Transpose: {self.analysis.get('master_transpose', 0):.1f} semitones\n\n"
        details += "🔢 KEYGROUP ANALYSIS:\n"
        details += f"• Declared Keygroups: {self.analysis.get('declared_keygroup_count', 0)}\n"
        details += f"• Active Keygroups: {self.analysis.get('actual_keygroup_count', 0)}\n\n"
        details += "📊 KEYGROUP RANGES:\n"

        if self.analysis.get('keygroup_ranges'):
            for kg_range in self.analysis['keygroup_ranges']:
                details += f"• KG{kg_range['kg']}: {kg_range['low']}-{kg_range['high']}\n"
        else:
            details += "• No active keygroups found\n"

        if self.analysis.get('critical_issues'):
            details += "\n🚨 CRITICAL ISSUES:\n"
            for issue in self.analysis['critical_issues']:
                details += f"• {issue}\n"

        if self.analysis.get('issues'):
            details += "\n⚠️ ISSUES:\n"
            for issue in self.analysis['issues']:
                details += f"• {issue}\n"

        if self.analysis.get('range_issues'):
            details += "\n📏 RANGE ISSUES:\n"
            for issue in self.analysis['range_issues']:
                details += f"• {issue}\n"

        if self.analysis.get('warnings'):
            details += "\n⚠️ WARNINGS:\n"
            for warning in self.analysis['warnings']:
                details += f"• {warning}\n"

        if self.analysis.get('fix_suggestions'):
            details += "\n🔧 RECOMMENDED FIXES:\n"
            for fix in self.analysis['fix_suggestions']:
                details += f"• {fix}\n"

        if 'error' in self.analysis:
            details += f"\n❌ ERROR:\n• {self.analysis['error']}\n"

        details += "\n" + "=" * 50 + "\n"
        details += "🩺 Advanced XPM Doctor Analysis Complete\n"

        self.text_widget.insert("1.0", details)
        self.text_widget.config(state="disabled")


class BatchProgramEditorWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master.root)
        self.master = master
        self.title("Batch Program Editor")
        self.geometry("450x550")  # Increased height for tabs
        self.resizable(True, True)
        self.params = {}
        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill="both", expand=True)

        # --- Top-level options ---
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill="x", pady=(0, 10))
        top_frame.columnconfigure(1, weight=1)

        self.params["rename"] = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            top_frame,
            text="Rename ProgramName to file name",
            variable=self.params["rename"],
        ).grid(row=0, column=0, columnspan=2, sticky="w")

        ttk.Label(top_frame, text="Application Version:").grid(
            row=1, column=0, sticky="w", pady=(5, 0)
        )
        self.params["version"] = tk.StringVar(value=self.master.firmware_version.get())
        versions = ["2.3.0.0", "2.6.0.17", "3.4.0", "3.5.0"]
        ttk.Combobox(
            top_frame,
            textvariable=self.params["version"],
            values=versions,
            state="readonly",
        ).grid(row=1, column=1, sticky="ew", pady=(5, 0))

        ttk.Label(top_frame, text="Format:").grid(
            row=2, column=0, sticky="w", pady=(5, 0)
        )
        self.params["format_version"] = tk.StringVar(value="advanced")
        ttk.Combobox(
            top_frame,
            textvariable=self.params["format_version"],
            values=["legacy", "advanced"],
            state="readonly",
        ).grid(row=2, column=1, sticky="ew", pady=(5, 0))

        # --- Notebook for Basic and Advanced tabs ---
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill="both", expand=True, pady=5)

        basic_tab = ttk.Frame(notebook, padding="10")
        advanced_tab = ttk.Frame(notebook, padding="10")
        notebook.add(basic_tab, text="Basic")
        notebook.add(advanced_tab, text="Advanced")

        self.create_basic_tab(basic_tab)
        self.create_advanced_tab(advanced_tab)

        # --- Bottom buttons ---
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=(10, 0))
        ttk.Button(
            btn_frame,
            text="Apply Edits",
            command=self.apply_edits,
            style="Accent.TButton",
        ).pack(side="right")
        ttk.Button(btn_frame, text="Close", command=self.destroy).pack(
            side="right", padx=(0, 5)
        )

    def create_basic_tab(self, parent):
        """Populates the Basic settings tab."""
        parent.columnconfigure(1, weight=1)

        # Creative Mode
        ttk.Label(parent, text="Creative Mode:").grid(
            row=0, column=0, sticky="w", pady=2
        )
        creative_frame = ttk.Frame(parent)
        creative_frame.grid(row=0, column=1, sticky="ew", pady=2)
        creative_frame.columnconfigure(0, weight=1)
        self.params["creative_mode"] = tk.StringVar(value="off")
        modes = ["off", "subtle", "synth", "lofi", "reverse", "stereo_spread"]
        creative_combo = ttk.Combobox(
            creative_frame,
            textvariable=self.params["creative_mode"],
            values=modes,
            state="readonly",
        )
        creative_combo.grid(row=0, column=0, sticky="ew")
        creative_combo.bind("<<ComboboxSelected>>", self.toggle_config_btn)
        self.config_btn = ttk.Button(
            creative_frame,
            text="Cfg",
            command=self.open_config,
            state="disabled",
            width=4,
        )
        self.config_btn.grid(row=0, column=1, padx=(5, 0))

        # Volume ADSR
        ttk.Label(parent, text="Volume ADSR:").grid(row=1, column=0, sticky="w", pady=2)
        adsr_frame = ttk.Frame(parent)
        adsr_frame.grid(row=1, column=1, sticky="ew", pady=2)
        self.params["attack"] = self.create_param_entry(adsr_frame, "A", 4)
        self.params["decay"] = self.create_param_entry(adsr_frame, "D", 4)
        self.params["sustain"] = self.create_param_entry(adsr_frame, "S", 4)
        self.params["release"] = self.create_param_entry(adsr_frame, "R", 4)

        # Mod Matrix
        ttk.Label(parent, text="Mod Matrix File:").grid(
            row=2, column=0, sticky="w", pady=2
        )
        mm_frame = ttk.Frame(parent)
        mm_frame.grid(row=2, column=1, sticky="ew", pady=2)
        mm_frame.columnconfigure(0, weight=1)
        self.params["mod_matrix_file"] = tk.StringVar()
        ttk.Entry(mm_frame, textvariable=self.params["mod_matrix_file"]).grid(
            row=0, column=0, sticky="ew"
        )
        ttk.Button(mm_frame, text="Browse...", command=self.browse_mod_matrix).grid(
            row=0, column=1, padx=(5, 0)
        )

        # Checkboxes
        self.params["fix_notes"] = tk.BooleanVar()
        ttk.Checkbutton(
            parent,
            text="Fix sample notes from WAV metadata",
            variable=self.params["fix_notes"],
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(5, 0))

        self.params["keytrack"] = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            parent, text="Keytrack (Layer Transpose)", variable=self.params["keytrack"]
        ).grid(row=4, column=0, columnspan=2, sticky="w")

    def create_advanced_tab(self, parent):
        """Populates the Advanced settings tab."""
        parent.columnconfigure(1, weight=1)
        parent.columnconfigure(3, weight=1)

        # Filter Env
        ttk.Label(parent, text="Filter ADSR:", font="-weight bold").grid(
            row=0, column=0, columnspan=4, sticky="w", pady=(0, 5)
        )

        ttk.Label(parent, text="ADSR:").grid(row=1, column=0, sticky="w", pady=2)
        f_adsr_frame = ttk.Frame(parent)
        f_adsr_frame.grid(row=1, column=1, sticky="ew", pady=2)
        self.params["filter_attack"] = self.create_param_entry(f_adsr_frame, "A", 4)
        self.params["filter_decay"] = self.create_param_entry(f_adsr_frame, "D", 4)
        self.params["filter_sustain"] = self.create_param_entry(f_adsr_frame, "S", 4)
        self.params["filter_release"] = self.create_param_entry(f_adsr_frame, "R", 4)

        ttk.Label(parent, text="Env Amt:").grid(
            row=1, column=2, sticky="w", padx=(10, 0), pady=2
        )
        self.params["filter_env_amount"] = tk.StringVar()
        ttk.Entry(parent, textvariable=self.params["filter_env_amount"], width=6).grid(
            row=1, column=3, sticky="ew", pady=2
        )

        # Velocity Mods
        ttk.Label(parent, text="Velocity Mod:", font="-weight bold").grid(
            row=2, column=0, columnspan=4, sticky="w", pady=(10, 5)
        )

        ttk.Label(parent, text="-> Level:").grid(row=3, column=0, sticky="w", pady=2)
        self.params["velocity_to_level"] = tk.StringVar()
        ttk.Entry(parent, textvariable=self.params["velocity_to_level"], width=6).grid(
            row=3, column=1, sticky="ew", pady=2
        )

        ttk.Label(parent, text="-> Attack:").grid(
            row=3, column=2, sticky="w", padx=(10, 0), pady=2
        )
        self.params["velocity_to_attack"] = tk.StringVar()
        ttk.Entry(parent, textvariable=self.params["velocity_to_attack"], width=6).grid(
            row=3, column=3, sticky="ew", pady=2
        )

        ttk.Label(parent, text="-> Start:").grid(row=4, column=0, sticky="w", pady=2)
        self.params["velocity_to_start"] = tk.StringVar()
        ttk.Entry(parent, textvariable=self.params["velocity_to_start"], width=6).grid(
            row=4, column=1, sticky="ew", pady=2
        )

        # LFOs
        ttk.Label(parent, text="LFO 1:", font="-weight bold").grid(
            row=5, column=0, columnspan=4, sticky="w", pady=(10, 5)
        )

        ttk.Label(parent, text="Rate:").grid(row=6, column=0, sticky="w", pady=2)
        self.params["lfo1_rate"] = tk.StringVar()
        ttk.Entry(parent, textvariable=self.params["lfo1_rate"], width=6).grid(
            row=6, column=1, sticky="ew", pady=2
        )

        ttk.Label(parent, text="Shape:").grid(
            row=6, column=2, sticky="w", padx=(10, 0), pady=2
        )
        self.params["lfo1_shape"] = tk.StringVar()
        ttk.Combobox(
            parent,
            textvariable=self.params["lfo1_shape"],
            values=["Sine", "Triangle", "Saw", "Square", "S&H"],
            state="readonly",
        ).grid(row=6, column=3, sticky="ew", pady=2)

    def create_param_entry(self, parent, label, width):
        """Helper to create a small labeled entry for ADSR-style widgets."""
        ttk.Label(parent, text=label).pack(side="left")
        var = tk.StringVar()
        ttk.Entry(parent, width=width, textvariable=var).pack(side="left", padx=(0, 5))
        return var

    def toggle_config_btn(self, event=None):
        if self.params["creative_mode"].get() in ["synth", "lofi"]:
            self.config_btn.config(state="normal")
        else:
            self.config_btn.config(state="disabled")

    def open_config(self):
        self.master.open_window(
            CreativeModeConfigWindow, self.params["creative_mode"].get()
        )

    def browse_mod_matrix(self):
        path = filedialog.askopenfilename(
            parent=self,
            title="Select Mod Matrix JSON",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
            initialdir=self.master.last_browse_path,
        )
        if path:
            self.params["mod_matrix_file"].set(path)
            self.master.last_browse_path = os.path.dirname(path)

    def apply_edits(self):
        # Collect all parameters from the StringVars
        args_dict = {}
        for key, var in self.params.items():
            value = var.get()
            # Only include non-empty strings, and handle booleans
            if isinstance(value, bool):
                args_dict[key] = value
            elif value:
                args_dict[key] = value

        self.master.run_batch_process(batch_edit_programs, args_dict)
        self.destroy()


class SmartSplitWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master.root)
        self.title("Smart Split Files")
        self.geometry("400x200")
        self.master = master
        self.split_mode = tk.StringVar(value="word")
        self.create_widgets()

    def create_widgets(self):
        frame = ttk.Frame(self, padding="10")
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Choose a method to split files into folders:").pack(
            anchor="w", pady=5
        )
        ttk.Radiobutton(
            frame,
            text="By First Word (e.g., 'Kick Drum.wav' -> 'Kick' folder)",
            variable=self.split_mode,
            value="word",
        ).pack(anchor="w")
        ttk.Radiobutton(
            frame,
            text="By Repeating Prefix (e.g., 'AAA_Snare.wav' -> 'AAA' folder)",
            variable=self.split_mode,
            value="prefix",
        ).pack(anchor="w")
        ttk.Radiobutton(
            frame,
            text="By Instrument Category (e.g., 'Bass', 'Piano', etc.)",
            variable=self.split_mode,
            value="category",
        ).pack(anchor="w")
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x", pady=(20, 0))
        ttk.Button(btn_frame, text="Apply Split", command=self.apply_split).pack(
            side="right"
        )
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(
            side="right", padx=5
        )

    def apply_split(self):
        mode = self.split_mode.get()
        self.destroy()
        self.master.run_batch_process(split_files_smartly, {"mode": mode})


class MergeSubfoldersWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master.root)
        self.title("Merge Subfolders")
        self.geometry("400x220")
        self.master = master
        self.target_depth = tk.IntVar(value=0)
        # IntVar used to control how deep subfolders are scanned when merging
        # files. Renamed variable to avoid confusion with the `max_depth`
        # argument in the merge functions below.
        self.max_depth_var = tk.IntVar(value=2)
        self.create_widgets()

    def create_widgets(self):
        frame = ttk.Frame(self, padding="10")
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Move files up to level:").pack(anchor="w")
        ttk.Radiobutton(frame, text="Root", variable=self.target_depth, value=0).pack(
            anchor="w"
        )
        ttk.Radiobutton(
            frame, text="1st Level", variable=self.target_depth, value=1
        ).pack(anchor="w")
        ttk.Radiobutton(
            frame, text="2nd Level", variable=self.target_depth, value=2
        ).pack(anchor="w")

        opt_frame = ttk.Frame(frame)
        opt_frame.pack(anchor="w", pady=(10, 0))
        ttk.Label(opt_frame, text="Max depth to scan:").pack(side="left")
        ttk.Spinbox(
            opt_frame, from_=1, to=10, textvariable=self.max_depth_var, width=4
        ).pack(side="left")

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x", pady=(20, 0))
        ttk.Button(btn_frame, text="Merge", command=self.apply_merge).pack(side="right")
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(
            side="right", padx=5
        )

    def apply_merge(self):
        depth = self.target_depth.get()
        max_depth = self.max_depth_var.get()
        self.destroy()
        # wrap merge_subfolders so run_batch_process can call it with two args
        merge_func = lambda folder, _=None: merge_subfolders(
            folder, {"target_depth": depth, "max_depth": max_depth}
        )
        self.master.run_batch_process(
            merge_func,
            {},
            confirm=True,
            confirm_message="This will move all files up and remove empty folders. This can't be undone. Continue?",
        )


# </editor-fold>


# <editor-fold desc="NEW & IMPROVED: SampleSelectorWindow">
class SampleSelectorWindow(tk.Toplevel):
    """A dialog to manually add/remove samples before rebuilding an XPM."""

    def __init__(self, master, xpm_path, initial_mappings, unreferenced_files):
        super().__init__(master)
        self.title(f"Sample Selector for {os.path.basename(xpm_path)}")
        self.geometry("800x500")
        self.resizable(True, True)

        self.final_mappings = initial_mappings
        self.unreferenced_files = {os.path.basename(f): f for f in unreferenced_files}
        self.result = None  # To store the final decision

        self.filter_var = tk.StringVar()
        self.filter_var.trace_add("write", self.update_available_list)

        self.create_widgets()
        self.populate_lists()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill="both", expand=True)
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(2, weight=1)

        # Included Samples List
        included_frame = ttk.LabelFrame(
            main_frame, text="Samples to Include in Rebuild", padding="5"
        )
        included_frame.grid(row=0, column=2, sticky="nsew", padx=(5, 0))
        included_frame.grid_rowconfigure(0, weight=1)
        included_frame.grid_columnconfigure(0, weight=1)
        self.included_list = tk.Listbox(included_frame, selectmode="extended")
        self.included_list.grid(row=0, column=0, sticky="nsew")
        vsb1 = ttk.Scrollbar(
            included_frame, orient="vertical", command=self.included_list.yview
        )
        vsb1.grid(row=0, column=1, sticky="ns")
        self.included_list.config(yscrollcommand=vsb1.set)

        # Available Samples List
        available_frame = ttk.LabelFrame(
            main_frame, text="Available Unreferenced Samples", padding="5"
        )
        available_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        available_frame.grid_rowconfigure(1, weight=1)
        available_frame.grid_columnconfigure(0, weight=1)

        # NEW: Filter entry
        filter_entry_frame = ttk.Frame(available_frame)
        filter_entry_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 5))
        ttk.Label(filter_entry_frame, text="Filter:").pack(side="left", padx=(0, 5))
        filter_entry = ttk.Entry(filter_entry_frame, textvariable=self.filter_var)
        filter_entry.pack(side="left", fill="x", expand=True)

        self.available_list = tk.Listbox(available_frame, selectmode="extended")
        self.available_list.grid(row=1, column=0, sticky="nsew")
        vsb2 = ttk.Scrollbar(
            available_frame, orient="vertical", command=self.available_list.yview
        )
        vsb2.grid(row=1, column=1, sticky="ns")
        self.available_list.config(yscrollcommand=vsb2.set)

        # Control Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=0, column=1, sticky="ns", padx=10)
        ttk.Button(button_frame, text="<-- Add", command=self.add_selected).pack(pady=5)
        ttk.Button(button_frame, text="Remove -->", command=self.remove_selected).pack(
            pady=5
        )

        # Bottom Buttons
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        ttk.Button(
            bottom_frame,
            text="Apply and Rebuild",
            command=self.apply_changes,
            style="Accent.TButton",
        ).pack(side="right")
        ttk.Button(bottom_frame, text="Cancel", command=self.cancel).pack(
            side="right", padx=5
        )

    def populate_lists(self):
        self.included_list.delete(0, tk.END)
        # Sort by basename for consistent order
        sorted_mappings = sorted(
            self.final_mappings, key=lambda m: os.path.basename(m["sample_path"])
        )
        for mapping in sorted_mappings:
            self.included_list.insert(tk.END, os.path.basename(mapping["sample_path"]))
        self.update_available_list()

    # NEW: Method to filter the available list based on entry text
    def update_available_list(self, *args):
        self.available_list.delete(0, tk.END)
        filter_text = self.filter_var.get().lower()
        for basename in sorted(self.unreferenced_files.keys()):
            if not filter_text or filter_text in basename.lower():
                self.available_list.insert(tk.END, basename)

    def add_selected(self):
        selected_indices = self.available_list.curselection()
        if not selected_indices:
            return

        for i in reversed(selected_indices):
            basename = self.available_list.get(i)
            # Find the full path from the dictionary and remove it
            full_path = self.unreferenced_files.pop(basename, None)
            if not full_path:
                continue

            # Create a new mapping for the added sample
            midi = infer_note_from_filename(basename) or 60
            new_mapping = {
                "sample_path": full_path,
                "root_note": midi,
                "low_note": midi,
                "high_note": midi,
                "velocity_low": 0,
                "velocity_high": 127,
            }
            self.final_mappings.append(new_mapping)

        self.populate_lists()

    def remove_selected(self):
        selected_indices = self.included_list.curselection()
        if not selected_indices:
            return

        for i in reversed(selected_indices):
            basename = self.included_list.get(i)
            # Find the corresponding mapping and remove it
            mapping_to_remove = next(
                (
                    m
                    for m in self.final_mappings
                    if os.path.basename(m["sample_path"]) == basename
                ),
                None,
            )
            if mapping_to_remove:
                self.final_mappings.remove(mapping_to_remove)
                # Add it back to the available list
                self.unreferenced_files[basename] = mapping_to_remove["sample_path"]

        self.populate_lists()

    def apply_changes(self):
        self.result = self.final_mappings
        self.destroy()

    def cancel(self):
        self.result = None
        self.destroy()


# </editor-fold>


# <editor-fold desc="REVISED: BatchProgramFixerWindow">
class BatchProgramFixerWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master.root if hasattr(master, "root") else master)
        self.title("Batch Program Fixer")
        self.geometry("800x600")
        self.master = master
        self.folder_path = tk.StringVar()
        self.firmware_var = tk.StringVar(value=master.firmware_version.get())
        self.format_var = tk.StringVar(value="advanced")
        self.status_var = tk.StringVar(value="Ready")
        self.check_vars = {}
        self.xpm_map = {}  # Maps treeview item ID to absolute path
        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill="both", expand=True)
        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)

        # Top bar for folder selection and scanning
        top_bar = ttk.Frame(main_frame)
        top_bar.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        top_bar.grid_columnconfigure(1, weight=1)
        ttk.Label(top_bar, text="Program Folder:").pack(side="left", padx=(0, 5))
        ttk.Entry(top_bar, textvariable=self.folder_path).pack(
            side="left", expand=True, fill="x"
        )
        ttk.Button(top_bar, text="Browse...", command=self.browse_folder).pack(
            side="left", padx=5
        )
        ttk.Button(top_bar, text="Scan Folder", command=self.scan_folder).pack(
            side="left"
        )

        # Treeview for displaying XPM files
        tree_frame = ttk.Frame(main_frame)
        tree_frame.grid(row=1, column=0, sticky="nsew", pady=5)
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        self.tree = Treeview(
            tree_frame, columns=("Select", "File", "Version", "Status"), show="headings"
        )
        self.tree.heading("Select", text="Select")
        self.tree.heading("File", text="Program File")
        self.tree.heading("Version", text="Version")
        self.tree.heading("Status", text="Status")
        self.tree.column("Select", width=60, anchor="center", stretch=False)
        self.tree.column("File", width=350)
        self.tree.column("Version", width=100, anchor="center")
        self.tree.column("Status", width=200)
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        self.tree.bind("<Button-1>", self.on_tree_click)
        main_frame.grid_rowconfigure(1, weight=1)

        # Action buttons
        # Status bar
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=2, column=0, sticky="ew", pady=5)
        ttk.Label(status_frame, textvariable=self.status_var, anchor="w").pack(side="left", fill="x", expand=True)
        
        actions_frame = ttk.LabelFrame(main_frame, text="Batch Actions", padding="10")
        actions_frame.grid(row=3, column=0, sticky="ew", pady=5)
        actions_frame.grid_columnconfigure(1, weight=1)
        actions_frame.grid_columnconfigure(2, weight=1)
        options_frame = ttk.Frame(actions_frame)
        options_frame.pack(side="left", padx=5)
        ttk.Label(options_frame, text="Firmware:").grid(row=0, column=0, sticky="e")
        ttk.Combobox(
            options_frame,
            textvariable=self.firmware_var,
            values=["2.3.0.0", "2.6.0.17", "3.4.0", "3.5.0"],
            state="readonly",
            width=10,
        ).grid(row=0, column=1)
        ttk.Label(options_frame, text="Format:").grid(row=1, column=0, sticky="e")
        ttk.Combobox(
            options_frame,
            textvariable=self.format_var,
            values=["legacy", "advanced"],
            state="readonly",
            width=10,
        ).grid(row=1, column=1)
        ttk.Button(
            actions_frame,
            text="Select All",
            command=lambda: self.toggle_all_checks(True),
        ).pack(side="left", padx=5)
        ttk.Button(
            actions_frame,
            text="Deselect All",
            command=lambda: self.toggle_all_checks(False),
        ).pack(side="left", padx=5)
        ttk.Button(
            actions_frame,
            text="Analyze & Relink Selected",
            command=self.run_relink_thread,
        ).pack(side="left", padx=20)
        ttk.Button(
            actions_frame,
            text="Fix Keygroup Counts",
            command=self.fix_keygroup_counts,
        ).pack(side="left", padx=5)
        ttk.Button(
            actions_frame,
            text="Rebuild Selected",
            command=self.run_rebuild_thread,
            style="Accent.TButton",
        ).pack(side="left", padx=5)
        ttk.Button(
            actions_frame, text="Edit Samples...", command=self.open_sample_editor
        ).pack(side="left", padx=5)

    def update_status(self, message):
        """Update the status bar message."""
        if threading.current_thread() is threading.main_thread():
            self.status_var.set(message)
        else:
            self.master.root.after_idle(lambda: self.status_var.set(message))
    
    def _show_info_safe(self, title, message):
        self.master.root.after_idle(
            lambda: messagebox.showinfo(title, message, parent=self)
        )

    def _ask_yesno_safe(self, title, message):
        """Safely ask a yes/no question from a background thread."""
        result = threading.Event()
        answer = tk.BooleanVar()

        def ask():
            answer.set(messagebox.askyesno(title, message, parent=self))
            result.set()

        self.master.root.after_idle(ask)
        result.wait()
        return answer.get()

    def _ask_directory_safe(self, title):
        """Safely ask for a directory from a background thread."""
        result = threading.Event()
        path = tk.StringVar()

        def ask():
            res = filedialog.askdirectory(
                parent=self, title=title, initialdir=self.master.last_browse_path
            )
            if res:
                path.set(res)
                self.master.last_browse_path = res
            result.set()

        self.master.root.after_idle(ask)
        result.wait()
        return path.get()

    # NEW: Thread-safe way to open the sample selector and get the result
    def _open_sample_selector_safe(self, xpm_path, initial_mappings, extras):
        """Open SampleSelectorWindow in a thread-safe manner.

        If called from the main thread, the dialog can be opened directly.
        When called from a worker thread, it schedules the dialog using
        ``after`` and waits for it to close.
        """

        # If we're already on the main thread, no special handling is needed.
        if threading.current_thread() is threading.main_thread():
            dialog = SampleSelectorWindow(self, xpm_path, initial_mappings, extras)
            self.wait_window(dialog)
            return dialog.result

        # Otherwise we're in a worker thread and must coordinate with Tk
        result_container = {}
        done_event = threading.Event()

        def open_dialog():
            dialog = SampleSelectorWindow(self, xpm_path, initial_mappings, extras)
            self.wait_window(dialog)
            result_container["result"] = dialog.result
            done_event.set()

        self.master.root.after_idle(open_dialog)
        done_event.wait()
        return result_container.get("result")

    def browse_folder(self):
        path = filedialog.askdirectory(
            parent=self,
            title="Select Folder Containing XPM Programs",
            initialdir=self.master.last_browse_path,
        )
        if path:
            self.folder_path.set(path)
            self.master.last_browse_path = path
            self.scan_folder()

    def scan_folder(self):
        folder = self.folder_path.get()
        if not folder or not os.path.isdir(folder):
            messagebox.showerror(
                "Error", "Please select a valid folder first.", parent=self
            )
            return

        # Clear existing data
        for i in self.tree.get_children():
            self.tree.delete(i)
        self.check_vars.clear()
        self.xpm_map.clear()

        self.update_status("Scanning for XPM files...")
        
        try:
            xpm_files = glob.glob(os.path.join(folder, "**", "*.xpm"), recursive=True)
            
            for i, path in enumerate(xpm_files):
                # Update status periodically
                if i % 10 == 0:
                    self.update_status(f"Scanning... {i+1}/{len(xpm_files)} files")
                    self.update()
                    
                version = get_xpm_version(path)
                rel_path = os.path.relpath(path, folder)
                
                # Basic validation
                status = "Ready"
                try:
                    # Quick validation check
                    tree = ET.parse(path)
                    root = tree.getroot()
                    if root.find(".//Program") is None:
                        status = "Invalid XPM"
                except Exception:
                    status = "Parse Error"
                
                item_id = self.tree.insert(
                    "", "end", values=("No", rel_path, version, status)
                )
                self.check_vars[item_id] = tk.BooleanVar(value=False)
                self.xpm_map[item_id] = path
                
            self.update_status(f"Found {len(xpm_files)} XPM files")
            
        except Exception as e:
            self.update_status(f"Error scanning folder: {e}")
            messagebox.showerror("Scan Error", f"Error scanning folder: {e}", parent=self)

    def get_selected_items(self):
        selected = []
        for item_id, var in self.check_vars.items():
            if var.get():
                selected.append(item_id)
        return selected

    def on_tree_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        col = self.tree.identify_column(event.x)
        row_id = self.tree.identify_row(event.y)
        if not row_id:
            return

        if col == "#1":
            current_val = self.check_vars[row_id].get()
            self.check_vars[row_id].set(not current_val)
            self.tree.set(row_id, "Select", "Yes" if not current_val else "No")

    def toggle_all_checks(self, select_all):
        for row_id in self.tree.get_children():
            if row_id in self.check_vars:
                self.check_vars[row_id].set(select_all)
                self.tree.set(row_id, "Select", "Yes" if select_all else "No")

    def run_relink_thread(self):
        selected_ids = self.get_selected_items()
        if not selected_ids:
            messagebox.showwarning(
                "No Selection",
                "Please select at least one program to analyze.",
                parent=self,
            )
            return
        threading.Thread(
            target=self.analyze_and_relink_batch, args=(selected_ids,), daemon=True
        ).start()
        
    def fix_keygroup_counts(self):
        """Fix keygroup counts in all XPM files in the selected folder."""
        folder = self.folder_path.get()
        if not folder or not os.path.isdir(folder):
            messagebox.showerror("Error", "Please select a valid folder first.", parent=self)
            return
        
        # Ask user for confirmation
        if not messagebox.askyesno(
            "Fix Keygroup Counts",
            "This will scan all XPM files in the selected folder and fix any keygroup count mismatches. Continue?",
            parent=self
        ):
            return
            
        # Run the fix operation in a separate thread
        def run_fix():
            from batch_program_editor import fix_keygroup_counts
            try:
                self.update_status("Fixing keygroup counts...")
                fixed = fix_keygroup_counts(folder)
                self.master.root.after_idle(
                    lambda: messagebox.showinfo(
                        "Fix Complete", 
                        f"Fixed keygroup count in {fixed} XPM file(s).",
                        parent=self
                    )
                )
                self.scan_folder()
            except Exception as e:
                logging.error(f"Error fixing keygroup counts: {e}")
                self.master.root.after_idle(
                    lambda: messagebox.showerror(
                        "Error", 
                        f"Failed to fix keygroup counts: {e}",
                        parent=self
                    )
                )
            finally:
                self.update_status("Ready")
                
        threading.Thread(target=run_fix, daemon=True).start()

    def run_rebuild_thread(self):
        selected_ids = self.get_selected_items()
        if not selected_ids:
            messagebox.showwarning(
                "No Selection",
                "Please select at least one program to rebuild.",
                parent=self,
            )
            return
        threading.Thread(
            target=self.rebuild_batch, args=(selected_ids,), daemon=True
        ).start()

    def open_sample_editor(self):
        selected_ids = self.get_selected_items()
        if len(selected_ids) != 1:
            messagebox.showwarning(
                "Select One Program",
                "Please select exactly one program to edit.",
                parent=self,
            )
            return
        item_id = selected_ids[0]
        xpm_path = self.xpm_map[item_id]

        # Parse the existing mappings and parameters
        mappings, params = _parse_xpm_for_rebuild(xpm_path)
        if mappings is None:
            messagebox.showerror(
                "Parse Error",
                "Failed to read the selected program.",
                parent=self,
            )
            return

        # Find extra audio files that live next to the program
        extras = find_unreferenced_audio_files(xpm_path, mappings)

        # Launch the selector dialog so the user can add/remove samples
        final_mappings = self._open_sample_selector_safe(xpm_path, mappings, extras)
        if final_mappings is None:
            return  # user cancelled
        if not final_mappings:
            messagebox.showwarning(
                "No Samples",
                "Rebuild cancelled because no samples were selected.",
                parent=self,
            )
            return

        # Rebuild the program with the chosen mappings
        program_name = os.path.splitext(os.path.basename(xpm_path))[0]
        output_folder = os.path.dirname(xpm_path)
        options = InstrumentOptions(
            firmware_version=self.firmware_var.get(),
            polyphony=self.master.polyphony_var.get(),
            format_version=self.format_var.get(),
        )
        builder = InstrumentBuilder(output_folder, self.master, options)

        shutil.copy2(xpm_path, xpm_path + ".edit.bak")
        success = builder._create_xpm(
            program_name,
            [],
            output_folder,
            mode="multi-sample",
            mappings=final_mappings,
            instrument_template=params,
        )

        if success:
            self.tree.set(item_id, "Status", "Rebuilt")
            self.tree.set(item_id, "Version", self.firmware_var.get())
            self._show_info_safe("Rebuild Complete", f"Updated {program_name}.xpm")
        else:
            self.tree.set(item_id, "Status", "Rebuild Failed")
            messagebox.showerror(
                "Error",
                f"Failed to rebuild {program_name}.xpm",
                parent=self,
            )

    def analyze_and_relink_batch(self, item_ids):
        all_missing_samples = set()
        programs_with_missing = defaultdict(list)

        # Step 1: Gather all missing samples from all selected programs
        for item_id in item_ids:
            xpm_path = self.xpm_map[item_id]
            self.tree.set(item_id, "Status", "Analyzing...")
            try:
                tree = ET.parse(xpm_path)
                root = tree.getroot()
                xpm_dir = os.path.dirname(xpm_path)

                found_missing_for_this_file = False
                for elem in root.findall(".//SampleFile"):
                    if elem is not None and elem.text:
                        sample_rel_path = elem.text.replace("/", os.sep)
                        sample_abs_path = os.path.normpath(
                            os.path.join(xpm_dir, sample_rel_path)
                        )
                        if not os.path.exists(sample_abs_path):
                            sample_basename = os.path.basename(elem.text)
                            all_missing_samples.add(sample_basename)
                            programs_with_missing[xpm_path].append(sample_basename)
                            found_missing_for_this_file = True

                self.tree.set(
                    item_id,
                    "Status",
                    "Missing samples" if found_missing_for_this_file else "OK",
                )

            except Exception as e:
                self.tree.set(item_id, "Status", "XML Error")
                logging.error(f"Error analyzing {xpm_path}: {e}")

        if not all_missing_samples:
            self._show_info_safe(
                "Analysis Complete", "No missing samples found in selected programs."
            )
            return

        # Step 2: Ask user for the location of the missing samples
        msg = f"Found {len(all_missing_samples)} unique missing samples across {len(programs_with_missing)} program(s).\n\nLocate the folder containing these samples?"
        if not self._ask_yesno_safe("Missing Samples Found", msg):
            return

        sample_folder = self._ask_directory_safe(
            "Select Folder Containing Missing Samples"
        )
        if not sample_folder:
            return

        # Step 3: Relink and copy
        total_relinked = 0
        for xpm_path, missing_list in programs_with_missing.items():
            self.tree.set(self.get_id_from_path(xpm_path), "Status", "Relinking...")
            try:
                tree = ET.parse(xpm_path)
                root = tree.getroot()
                changed = False
                xpm_dir = os.path.dirname(xpm_path)

                for elem in root.findall(".//SampleFile"):
                    sample_basename = os.path.basename(elem.text.replace("/", os.sep))
                    if sample_basename in missing_list:
                        found_path = os.path.join(sample_folder, sample_basename)
                        if os.path.exists(found_path):
                            dest_path = os.path.join(xpm_dir, sample_basename)
                            shutil.copy2(found_path, dest_path)
                            elem.text = (
                                sample_basename  # Update path to be relative to XPM
                            )
                            changed = True
                            total_relinked += 1

                if changed:
                    shutil.copy2(xpm_path, xpm_path + ".bak")
                    indent_tree(tree)
                    tree.write(xpm_path, encoding="utf-8", xml_declaration=True)
                    self.tree.set(self.get_id_from_path(xpm_path), "Status", "Relinked")
            except Exception as e:
                self.tree.set(self.get_id_from_path(xpm_path), "Status", "Relink Error")
                logging.error(f"Error relinking {xpm_path}: {e}")

        self._show_info_safe(
            "Relink Complete", f"Finished. Relinked {total_relinked} sample instances."
        )

    # REVISED: Rebuild batch now uses the new sample selector
    def rebuild_batch(self, item_ids):
        target_firmware = self.firmware_var.get()
        target_format = self.format_var.get()
        if not self._ask_yesno_safe(
            "Confirm Rebuild",
            f"This will rebuild {len(item_ids)} program(s) for firmware {target_firmware} in {target_format} format. Backups will be created. Continue?",
        ):
            return

        for item_id in item_ids:
            xpm_path = self.xpm_map[item_id]
            self.tree.set(item_id, "Status", "Rebuilding...")
            try:
                # 1. Parse the existing XPM to get current samples and parameters
                initial_mappings, inst_params = _parse_xpm_for_rebuild(xpm_path)
                if initial_mappings is None:  # Check for parsing failure
                    self.tree.set(item_id, "Status", "Parse Error")
                    logging.warning(
                        f"Could not parse mappings from {xpm_path}, skipping rebuild."
                    )
                    continue

                # 2. Find any related but unreferenced audio files
                extra_files = find_unreferenced_audio_files(xpm_path, initial_mappings)

                # 3. Open the sample selector window to let the user decide
                final_mappings = self._open_sample_selector_safe(
                    xpm_path, initial_mappings, extra_files
                )

                # If the user cancelled the dialog, final_mappings will be None
                if final_mappings is None:
                    self.tree.set(item_id, "Status", "Rebuild Cancelled")
                    continue

                if not final_mappings:
                    self.tree.set(item_id, "Status", "Rebuild Failed (No Samples)")
                    logging.warning(
                        f"Rebuild for {xpm_path} skipped as no samples were selected."
                    )
                    continue

                # 4. Proceed with the rebuild using the user-confirmed sample list
                program_name = os.path.splitext(os.path.basename(xpm_path))[0]
                output_folder = os.path.dirname(xpm_path)

                options = InstrumentOptions(
                    firmware_version=target_firmware,
                    polyphony=self.master.polyphony_var.get(),
                    format_version=target_format,
                )
                builder = InstrumentBuilder(output_folder, self.master, options)

                shutil.copy2(xpm_path, xpm_path + f".rebuild-{target_firmware}.bak")
                success = builder._create_xpm(
                    program_name,
                    [],
                    output_folder,
                    mode="multi-sample",
                    mappings=final_mappings,  # Use the user-approved list
                    instrument_template=inst_params,
                )

                if success:
                    self.tree.set(item_id, "Status", f"Rebuilt for {target_firmware}")
                    self.tree.set(item_id, "Version", target_firmware)
                else:
                    self.tree.set(item_id, "Status", "Rebuild Failed")
            except Exception as e:
                self.tree.set(item_id, "Status", "Rebuild Error")
                logging.error(
                    f"Critical error rebuilding {xpm_path}: {e}\n{traceback.format_exc()}"
                )

        self._show_info_safe(
            "Rebuild Complete", "Finished rebuilding selected programs."
        )

    def get_id_from_path(self, path):
        for item_id, item_path in self.xpm_map.items():
            if item_path == path:
                return item_id
        return None


# </editor-fold>


@dataclass
class InstrumentOptions:
    loop_one_shots: bool = False
    analyze_scw: bool = True
    creative_mode: str = "off"
    recursive_scan: bool = True
    firmware_version: str = "3.5.0"
    polyphony: int = 16
    format_version: str = "advanced"
    creative_config: dict = field(default_factory=dict)


# <editor-fold desc="InstrumentBuilder Class">
class InstrumentBuilder:
    def __init__(self, folder_path, app, options: InstrumentOptions):
        self.folder_path = folder_path
        self.app = app
        self.options = options

    # <editor-fold desc="GUI Safe Callbacks">
    def _show_info_safe(self, title, message):
        self.app.root.after_idle(
            lambda: messagebox.showinfo(title, message, parent=self.app.root)
        )

    def _show_warning_safe(self, title, message):
        self.app.root.after_idle(
            lambda: messagebox.showwarning(title, message, parent=self.app.root)
        )

    def _show_error_safe(self, title, message):
        self.app.root.after_idle(
            lambda: messagebox.showerror(title, message, parent=self.app.root)
        )

    def _ask_yesno_safe(self, title, message):
        result = threading.Event()
        answer = tk.BooleanVar()

        def ask():
            answer.set(messagebox.askyesno(title, message, parent=self.app.root))
            result.set()

        self.app.root.after_idle(ask)
        result.wait()
        return answer.get()

    # </editor-fold>

    def validate_options(self):
        if not self.folder_path or not os.path.isdir(self.folder_path):
            self._show_error_safe(
                "Validation Error", "A valid source folder must be selected."
            )
            return False
        return True

    # NEW: Dedicated function to create a playable keymap
    def _calculate_key_ranges(self, sample_infos):
        """Assigns key ranges for multi-sample instruments based on root notes."""
        # Sort samples by root_note
        sorted_samples = sorted(sample_infos, key=lambda x: x.get("root_note", 60))
        n = len(sorted_samples)
        if n == 0:
            return []
        # Assign key ranges so each sample covers halfway to the next
        for i, sample in enumerate(sorted_samples):
            root = sample.get("root_note", 60)
            if i == 0:
                low = 0
            else:
                prev_root = sorted_samples[i - 1].get("root_note", 60)
                low = (prev_root + root) // 2 + 1
            if i == n - 1:
                high = 127
            else:
                next_root = sorted_samples[i + 1].get("root_note", 60)
                high = (root + next_root) // 2
            sample["low_note"] = low
            sample["high_note"] = high
        return sorted_samples

    def create_instruments(self, mode="multi-sample", files=None):
        logging.info("create_instruments starting with mode %s", mode)
        if not self.validate_options():
            return

        created_xpms, created_count, error_count = [], 0, 0
        try:
            self.app.status_text.set("Analyzing files...")

            # If files are passed directly (from MultiSampleBuilderWindow), use them.
            # Otherwise, group files from the main folder path.
            if files:
                instrument_groups = files
            elif mode == "drum-kit":
                # For drum kits, use the specialized drumkit grouping if available
                instrument_groups = (
                    group_similar_files(self.folder_path) if IMPORTS_SUCCESSFUL else {}
                )
                # If drumkit grouping failed or returned empty, fall back to intelligent grouping
                if not instrument_groups:
                    instrument_groups = self._group_samples_intelligently([
                        f for f in glob.glob(os.path.join(self.folder_path, "**", "*.wav"), recursive=True)
                        if ".xpm.wav" not in f.lower()
                    ])
            else:
                instrument_groups = self.group_wav_files(mode)

            if not instrument_groups:
                self.app.status_text.set("No suitable WAV files found for this mode.")
                self._show_info_safe(
                    "Finished", "No suitable .wav files found to create instruments."
                )
                return

            total_groups = len(instrument_groups)
            self.app.progress["maximum"] = total_groups

            for i, (program_name, group_files) in enumerate(instrument_groups.items()):
                try:
                    self.app.status_text.set(f"Creating: {program_name}")
                    self.app.progress["value"] = i + 1

                    sanitized_name = re.sub(r'[\\/*?:"<>|]', "", program_name)
                    first_file_abs_path = os.path.join(self.folder_path, group_files[0])
                    output_folder = os.path.dirname(first_file_abs_path)

                    if self._create_xpm(
                        sanitized_name, group_files, output_folder, mode
                    ):
                        created_count += 1
                        created_xpms.append(
                            os.path.join(output_folder, f"{sanitized_name}.xpm")
                        )
                    else:
                        error_count += 1
                except Exception as e:
                    logging.error(
                        f"Error processing group {program_name}: {e}\n{traceback.format_exc()}"
                    )
                    error_count += 1

            with open("xpm_output.log", "w", encoding="utf-8") as f:
                f.write(f"--- XPM Creation Summary ---\n")
                f.write(f"Created: {created_count}, Failed: {error_count}\n\n")
                if created_xpms:
                    f.write("Generated XPM Files:\n")
                    for xpm in created_xpms:
                        f.write(f"- {xpm}\n")

            if created_count > 0 and self._ask_yesno_safe(
                "Generate Previews",
                "Would you like to generate audio previews for the new instruments?",
            ):
                self.process_previews_only()

            if created_count > 0 and not os.path.exists(
                os.path.join(self.folder_path, "Expansion.xml")
            ):
                if self._ask_yesno_safe(
                    "Create Expansion File",
                    "No Expansion.xml found. Would you like to create one now?",
                ):
                    self.app.root.after_idle(self.app.open_expansion_builder)

            self.app.status_text.set("Processing complete.")
            if error_count > 0:
                self._show_warning_safe(
                    "Completed with Errors",
                    f"Successfully created {created_count} instruments.\nFailed to create {error_count} instruments.\nCheck converter.log for details.",
                )
            elif created_count > 0:
                self._show_info_safe(
                    "Success", f"Successfully created {created_count} instruments."
                )
        except Exception as e:
            logging.error(f"create_instruments failed: {e}\n{traceback.format_exc()}")
            self._show_error_safe("Error", f"An unexpected error occurred: {e}")
        finally:
            self.app.progress["value"] = 0

    def _create_xpm(
        self,
        program_name,
        sample_files,
        output_folder,
        mode,
        midi_notes=None,
        mappings=None,
        instrument_template=None,
    ):
        """Create a single XPM file from samples or an existing mapping."""
        if mappings:
            logging.info(
                "_create_xpm rebuilding '%s' using mapping with %d entry(ies)",
                program_name,
                len(mappings),
            )
        else:
            logging.info(
                "_create_xpm building '%s' with %d sample(s)",
                program_name,
                len(sample_files),
            )
        try:
            sample_infos = []
            start_note = 60
            if mappings:
                # This path is for rebuilding from existing mappings
                for m in mappings:
                    abs_path = m["sample_path"]
                    info = self.validate_sample_info(abs_path)
                    if not info.get("is_valid"):
                        continue
                    # Preserve all parameters from the mapping
                    info.update(m)
                    rel_path = os.path.relpath(abs_path, output_folder)
                    info["sample_path"] = rel_path.replace(os.sep, "/")
                    sample_infos.append(info)
            else:
                # This path is for building a NEW instrument from files
                for idx, file_path in enumerate(sample_files):
                    abs_path = (
                        os.path.join(self.folder_path, file_path)
                        if not os.path.isabs(file_path)
                        else file_path
                    )
                    info = self.validate_sample_info(abs_path)
                    if info.get("is_valid"):
                        if midi_notes and idx < len(midi_notes):
                            midi_note = midi_notes[idx]
                        else:
                            # Use found root note, or filename note, or default to 60
                            midi_note = info.get("root_note") or 60
                            logging.info(
                                f"Sample {os.path.basename(file_path)} assigned root note: {midi_note}"
                            )

                        info["root_note"] = midi_note
                        info["velocity_low"] = 0
                        info["velocity_high"] = 127
                        rel_path = os.path.relpath(abs_path, output_folder)
                        info["sample_path"] = rel_path.replace(os.sep, "/")
                        sample_infos.append(info)

                # REVISED: Apply correct key range logic based on build mode
                if mode == "multi-sample":
                    sample_infos = self._calculate_key_ranges(sample_infos)
                elif mode == "one-shot":
                    for info in sample_infos:
                        info["low_note"] = 0
                        info["high_note"] = 127
                else:  # drum-kit
                    for idx, info in enumerate(sample_infos):
                        note = min(start_note + idx, 127)
                        info["low_note"] = note
                        info["high_note"] = note

            if not sample_infos:
                logging.warning(f"No valid samples for program: {program_name}")
                return False

            # Group samples by their key range to create keygroups
            note_layers = defaultdict(list)
            for info in sample_infos:
                key = (info["low_note"], info["high_note"])
                note_layers[key].append(info)
                
            # Store both the total sample count and the keygroup count
            sample_count = len(sample_infos)
            keygroup_count = len(note_layers)
            
            # Log if there's a mismatch between samples and keygroups
            if sample_count != keygroup_count:
                logging.warning(
                    f"Sample count ({sample_count}) differs from keygroup count ({keygroup_count}) for {program_name}. "
                    f"This may happen when multiple samples share the same key range."
                )

            root = ET.Element("MPCVObject")
            version = ET.SubElement(root, "Version")
            ET.SubElement(version, "File_Version").text = "2.1"
            ET.SubElement(version, "Application").text = "MPC-V"
            ET.SubElement(version, "Application_Version").text = (
                self.options.firmware_version
            )
            ET.SubElement(version, "Platform").text = "Linux"

            program = ET.SubElement(root, "Program", {"type": "Keygroup"})
            ET.SubElement(program, "ProgramName").text = xml_escape(program_name)

            # Build the JSON section (less critical for keygroups, but good to be accurate)
            pads_json_str = build_program_pads_json(
                self.options.firmware_version,
                sample_infos,
                engine_override=self.options.format_version,
                num_instruments=keygroup_count,
            )
            pads_tag = (
                "ProgramPads-v2.10"
                if self.options.firmware_version in ["3.4.0", "3.5.0"]
                else "ProgramPads"
            )
            ET.SubElement(program, pads_tag).text = pads_json_str

            program_params = self.get_program_parameters(keygroup_count)
            program_params["KeygroupLegacyMode"] = (
                "True" if self.options.format_version == "legacy" else "False"
            )
            for key, val in program_params.items():
                ET.SubElement(program, key).text = val

            # Build the critical <Instruments> section
            instruments = ET.SubElement(program, "Instruments")
            sorted_keys = sorted(note_layers.keys())
            for i, key in enumerate(sorted_keys):
                low_key, high_key = key
                inst = self.build_instrument_element(instruments, i, low_key, high_key)
                if instrument_template:
                    for k, v in instrument_template.items():
                        elem = inst.find(k)
                        if elem is not None:
                            elem.text = str(v)
                        else:
                            ET.SubElement(inst, k).text = str(v)
                layers_elem = ET.SubElement(inst, "Layers")

                layers_for_note = sorted(
                    note_layers[key], key=lambda x: x.get("velocity_low", 0)
                )
                num_layers = min(len(layers_for_note), 8)
                vel_split = 128 // num_layers

                for lidx, sample_info in enumerate(layers_for_note[:num_layers]):
                    layer = ET.SubElement(
                        layers_elem, "Layer", {"number": str(lidx + 1)}
                    )
                    vel_start = sample_info.get("velocity_low", lidx * vel_split)
                    vel_end = sample_info.get(
                        "velocity_high",
                        (lidx + 1) * vel_split - 1 if lidx < num_layers - 1 else 127,
                    )
                    self.add_layer_parameters(layer, sample_info, vel_start, vel_end)
                    self.apply_creative_mode(inst, layer, lidx, num_layers)

            output_path = os.path.join(output_folder, f"{program_name}.xpm")
            tree = ET.ElementTree(root)
            indent_tree(tree)
            tree.write(output_path, encoding="utf-8", xml_declaration=True)

            if not validate_xpm_file(output_path, len(sample_infos)):
                logging.warning(
                    f"Post-creation validation failed for {os.path.basename(output_path)}"
                )

            return True

        except Exception as e:
            logging.error(
                f"Critical error in _create_xpm for {program_name}: {e}\n{traceback.format_exc()}"
            )
            return False

    def get_program_parameters(self, num_keygroups):
        if not IMPORTS_SUCCESSFUL:
            return {}
        firmware = self.options.firmware_version
        return fw_program_parameters(
            firmware,
            num_keygroups,
            engine_override=self.options.format_version,
        )

    def build_instrument_element(self, parent, num, low, high):
        instrument = ET.SubElement(parent, "Instrument", {"number": str(num)})
        if not IMPORTS_SUCCESSFUL:
            # Fallback for missing imports
            params = {
                "Polyphony": str(self.options.polyphony),
                "LowNote": str(low),
                "HighNote": str(high),
            }
        else:
            engine = get_pad_settings(
                self.options.firmware_version, self.options.format_version
            ).get("engine")
            if engine == "advanced" and ADVANCED_INSTRUMENT_PARAMS:
                params = ADVANCED_INSTRUMENT_PARAMS.copy()
            else:
                params = {}  # Start with an empty dictionary for legacy

            # Universal parameters applied to both legacy and advanced
            params.update(
                {
                    "Polyphony": str(self.options.polyphony),
                    "LowNote": str(low),
                    "HighNote": str(high),
                }
            )

            # Add legacy-specific default parameters if not in advanced mode
            if engine != "advanced":
                legacy_defaults = {
                    "Volume": "1.0",
                    "Pan": "0.5",
                    "Tune": "0.0",
                    "MuteGroup": "0",
                    "VoiceOverlap": "Poly",
                    "VolumeAttack": "0.0",
                    "VolumeDecay": "0.0",
                    "VolumeSustain": "1.0",
                    "VolumeRelease": "0.05",
                    "FilterType": "Off",
                    "Cutoff": "1.0",
                    "Resonance": "0.0",
                    "FilterKeytrack": "0.0",
                    "FilterAttack": "0.0",
                    "FilterDecay": "0.0",
                    "FilterSustain": "1.0",
                    "FilterRelease": "0.0",
                    "FilterEnvAmount": "0.0",
                }
                params.update(legacy_defaults)

        for key, val in params.items():
            ET.SubElement(instrument, key).text = val
        return instrument

    # REVISED: This function now preserves all layer parameters
    def add_layer_parameters(self, layer_element, sample_info, vel_start, vel_end):
        sample_name, _ = os.path.splitext(os.path.basename(sample_info["sample_path"]))
        frames = sample_info.get("frames", 0)

        # Start with defaults, then override with preserved values
        params = {
            "SampleName": sample_name,
            "SampleFile": sample_info["sample_path"],
            "VelStart": str(vel_start),
            "VelEnd": str(vel_end),
            "RootNote": str(sample_info["root_note"]),
            "SampleStart": "0",
            "SampleEnd": str(frames),
            "Loop": "Off",
            "Direction": "0",
            "Offset": "0",
            "Volume": "1.0",
            "Pan": "0.5",
            "Tune": "0.0",
            "MuteGroup": "0",
        }

        # Override defaults with any parameters preserved from the original file
        if "layer_params" in sample_info:
            for key, value in sample_info["layer_params"].items():
                if key in params:
                    params[key] = value

        # Special handling for loop points if loop is on
        if params.get("Loop") == "On":
            params["LoopStart"] = sample_info.get("layer_params", {}).get(
                "LoopStart", "0"
            )
            params["LoopEnd"] = sample_info.get("layer_params", {}).get(
                "LoopEnd", str(max(frames - 1, 0))
            )

        for key, value in params.items():
            ET.SubElement(layer_element, key).text = str(value)

    def apply_creative_mode(
        self, instrument_element, layer_element, layer_index, total_layers
    ):
        mode = self.options.creative_mode
        config = self.options.creative_config.get(mode, {})
        if mode == "off":
            return

        params = {}
        if mode == "reverse" and layer_index % 2 == 1:
            params["Direction"] = "1"
        if mode == "stereo_spread" and total_layers > 1:
            params["Pan"] = str(round(layer_index / (total_layers - 1), 3))

        if layer_index == 0:
            if mode == "subtle":
                params["Cutoff"] = str(round(1.0 + random.uniform(-0.05, 0.05), 3))
            elif mode == "synth":
                params.update(
                    {
                        "FilterType": CREATIVE_FILTER_TYPE_MAP[
                            random.choice(["LPF", "HPF", "BPF"])
                        ],
                        "Cutoff": str(round(random.uniform(0.5, 1.0), 3)),
                        "Resonance": str(
                            config.get("resonance", round(random.uniform(0.15, 0.4), 3))
                        ),
                        "VolumeAttack": str(round(random.uniform(0.001, 0.05), 4)),
                        "VolumeRelease": str(
                            config.get("release", round(random.uniform(0.2, 0.7), 3))
                        ),
                    }
                )
            elif mode == "lofi":
                params.update(
                    {
                        "Cutoff": str(
                            config.get("cutoff", round(random.uniform(0.2, 0.6), 3))
                        ),
                        "Resonance": str(round(random.uniform(0.2, 0.5), 3)),
                        "PitchEnvAmount": str(
                            config.get(
                                "pitch_wobble", round(random.uniform(-0.2, 0.2), 3)
                            )
                        ),
                    }
                )

        for key, value in params.items():
            target_element = (
                layer_element if key in ["Direction", "Pan"] else instrument_element
            )
            elem = target_element.find(key)
            if elem is not None:
                elem.text = value
            else:
                ET.SubElement(target_element, key).text = value

    def process_previews_only(self):
        """Generates audio previews for all existing XPM files in the folder."""
        logging.info("process_previews_only starting")
        self.app.status_text.set("Generating previews...")
        self.app.progress.config(mode="indeterminate")
        self.app.progress.start()
        folder = self.folder_path
        xpm_files = glob.glob(os.path.join(folder, "**", "*.xpm"), recursive=True)
        if not xpm_files:
            self._show_info_safe(
                "No XPMs Found", "No .xpm files were found to generate previews for."
            )
            self.app.progress.stop()
            self.app.progress.config(mode="determinate")
            return

        preview_count = 0
        for xpm_path in xpm_files:
            try:
                preview_folder_path = os.path.join(
                    os.path.dirname(xpm_path), "[Previews]"
                )
                os.makedirs(preview_folder_path, exist_ok=True)

                tree = ET.parse(xpm_path)
                root = tree.getroot()
                preview_sample_name = None

                # Modern format check (JSON inside ProgramPads)
                pads_elem = find_program_pads(root)
                if pads_elem is not None and pads_elem.text:
                    pads_data = json.loads(xml_unescape(pads_elem.text))
                    pads = pads_data.get("pads", {})
                    # Find first valid sample path
                    for i in range(128):
                        pad = pads.get(f"value{i}")
                        if isinstance(pad, dict) and pad.get("samplePath"):
                            preview_sample_name = pad["samplePath"]
                            break

                # Legacy format check (if no ProgramPads or no sample found in it)
                if not preview_sample_name:
                    first_sample_elem = root.find(".//Layer/SampleName")
                    if first_sample_elem is not None and first_sample_elem.text:
                        preview_sample_name = first_sample_elem.text + ".wav"

                if preview_sample_name:
                    xpm_dir = os.path.dirname(xpm_path)
                    sample_basename = os.path.basename(
                        preview_sample_name.replace("/", os.sep)
                    )
                    source_sample_abs = os.path.join(xpm_dir, sample_basename)

                    if os.path.exists(source_sample_abs):
                        program_name = os.path.splitext(os.path.basename(xpm_path))[0]
                        preview_filename = f"{program_name}.xpm.wav"
                        dest_path = os.path.join(preview_folder_path, preview_filename)
                        if not os.path.exists(dest_path):
                            shutil.copy2(source_sample_abs, dest_path)
                            preview_count += 1
                            logging.info(
                                f"Generated preview for {os.path.basename(xpm_path)}"
                            )
                    else:
                        logging.warning(
                            f"Preview source sample not found for {os.path.basename(xpm_path)}. Looked for: {source_sample_abs}"
                        )
                else:
                    logging.warning(
                        f"Could not find any sample reference in {os.path.basename(xpm_path)}."
                    )

            except Exception as e:
                logging.error(
                    f"Failed to generate preview for {os.path.basename(xpm_path)}: {e}"
                )

        self.app.progress.stop()
        self.app.progress.config(mode="determinate")
        self.app.status_text.set("Preview generation complete.")
        self._show_info_safe("Done", f"Generated {preview_count} new audio previews.")

    def group_wav_files(self, mode):
        """Groups WAV files by instrument name for XPM creation with intelligent similarity detection."""
        search_path = (
            os.path.join(self.folder_path, "**", "*.wav")
            if self.options.recursive_scan
            else os.path.join(self.folder_path, "*.wav")
        )
        all_wavs = glob.glob(search_path, recursive=self.options.recursive_scan)

        if mode == "one-shot":
            # For one-shot mode, each sample gets its own instrument
            groups = defaultdict(list)
            for wav_path in all_wavs:
                if ".xpm.wav" in wav_path.lower():
                    continue
                relative_path = os.path.relpath(wav_path, self.folder_path)
                instrument_name = os.path.splitext(os.path.basename(wav_path))[0]
                groups[instrument_name].append(relative_path)
            return groups
        else:
            # For multi-sample mode, use intelligent grouping
            return self._group_samples_intelligently(all_wavs)

    def _group_samples_intelligently(self, all_wavs):
        """Advanced sample grouping with similarity detection and pattern recognition."""
        from difflib import SequenceMatcher
        
        # Filter out preview files
        valid_wavs = [wav for wav in all_wavs if ".xpm.wav" not in wav.lower()]
        
        if not valid_wavs:
            return {}
        
        logging.info(f"🎵 Intelligent grouping: Processing {len(valid_wavs)} samples")
        
        groups = defaultdict(list)
        processed_files = set()
        
        for wav_path in valid_wavs:
            if wav_path in processed_files:
                continue
                
            relative_path = os.path.relpath(wav_path, self.folder_path)
            base_name = os.path.splitext(os.path.basename(wav_path))[0]
            
            # Extract core instrument name using multiple strategies
            group_name = self._extract_instrument_group_name(base_name, wav_path)
            
            # Find similar files that should be grouped together
            similar_files = [relative_path]
            processed_files.add(wav_path)
            
            # Look for files with similar names
            for other_wav in valid_wavs:
                if other_wav in processed_files:
                    continue
                    
                other_base = os.path.splitext(os.path.basename(other_wav))[0]
                other_relative = os.path.relpath(other_wav, self.folder_path)
                
                # Check if files should be grouped together
                if self._should_group_together(base_name, other_base, wav_path, other_wav):
                    similar_files.append(other_relative)
                    processed_files.add(other_wav)
            
            # Sort files within group for consistent ordering
            similar_files.sort()
            groups[group_name].extend(similar_files)
            
            # Log grouping results for debugging
            if len(similar_files) > 1:
                logging.info(f"📁 Grouped {len(similar_files)} samples under '{group_name}': {[os.path.basename(f) for f in similar_files[:3]]}{'...' if len(similar_files) > 3 else ''}")
        
        # Merge groups that are very similar (catch edge cases)
        original_group_count = len(groups)
        groups = self._merge_similar_groups(groups)
        
        if len(groups) != original_group_count:
            logging.info(f"🔀 Merged similar groups: {original_group_count} → {len(groups)} groups")
        
        # Final summary
        total_samples = sum(len(files) for files in groups.values())
        avg_samples_per_group = total_samples / len(groups) if groups else 0
        logging.info(f"✅ Intelligent grouping complete: {total_samples} samples → {len(groups)} groups (avg {avg_samples_per_group:.1f} samples/group)")
        
        return dict(groups)

    def _extract_instrument_group_name(self, base_name, full_path):
        """Extract the core instrument name from a sample filename using multiple strategies."""
        # Strategy 1: Remove common suffixes and patterns
        clean_name = base_name.lower()
        
        # Remove note indicators (C4, D#3, etc.)
        clean_name = re.sub(r'[_\s-]*[a-g][#b]?[0-9]?[_\s-]*', '', clean_name, flags=re.IGNORECASE)
        
        # Remove velocity indicators (v1, vel1, velocity_01, etc.)
        clean_name = re.sub(r'[_\s-]*v(el)?(ocity)?[_\s-]?[0-9]+[_\s-]*', '', clean_name, flags=re.IGNORECASE)
        
        # Remove round-robin indicators (rr1, round1, etc.)
        clean_name = re.sub(r'[_\s-]*(rr|round)[_\s-]?[0-9]+[_\s-]*', '', clean_name, flags=re.IGNORECASE)
        
        # Remove generic numbered suffixes (01, 001, _1, etc.)
        clean_name = re.sub(r'[_\s-]*[0-9]+$', '', clean_name)
        
        # Remove common sample descriptors
        descriptors = ['sample', 'smp', 'wav', 'loop', 'shot', 'hit', 'one', 'multi']
        for desc in descriptors:
            clean_name = re.sub(rf'[_\s-]*{desc}[_\s-]*', '', clean_name, flags=re.IGNORECASE)
        
        # Strategy 2: Use folder context if name is too generic
        if len(clean_name.strip()) < 3 or clean_name.strip() in ['', 'a', 'an', 'the']:
            parent_folder = os.path.basename(os.path.dirname(full_path))
            if parent_folder and parent_folder.lower() != os.path.basename(self.folder_path).lower():
                clean_name = parent_folder.lower()
        
        # Strategy 3: Look for instrument type keywords
        instrument_keywords = {
            'piano': ['piano', 'pno', 'key', 'grand'],
            'bass': ['bass', 'sub', 'low', 'fundamental'],
            'lead': ['lead', 'melody', 'main', 'solo'],
            'pad': ['pad', 'string', 'choir', 'warm', 'soft'],
            'pluck': ['pluck', 'harp', 'pizz', 'mute'],
            'bell': ['bell', 'chime', 'glock', 'metal'],
            'brass': ['brass', 'horn', 'trumpet', 'trombone', 'tuba'],
            'drum': ['drum', 'kick', 'snare', 'hi-hat', 'hat', 'cymbal', 'tom'],
            'fx': ['fx', 'effect', 'sweep', 'noise', 'impact', 'riser'],
            'vocal': ['vocal', 'voice', 'choir', 'ah', 'oh', 'la'],
            'synth': ['synth', 'synthetic', 'digital', 'electronic']
        }
        
        original_clean = clean_name
        for category, keywords in instrument_keywords.items():
            for keyword in keywords:
                if keyword in base_name.lower() or keyword in original_clean:
                    # Extract the specific variant if it exists
                    variant_match = re.search(rf'({keyword}[_\s-]*\w*)', base_name.lower())
                    if variant_match:
                        return variant_match.group(1).replace('_', ' ').replace('-', ' ').strip()
                    else:
                        return category
        
        # Strategy 4: Clean up and return
        clean_name = re.sub(r'[_\s-]+', ' ', clean_name).strip()
        if not clean_name:
            # Last resort: use first few characters of original name
            clean_name = re.sub(r'[_\s-]+', ' ', base_name[:8].lower()).strip()
        
        return clean_name if clean_name else "instrument"

    def _should_group_together(self, name1, name2, path1, path2):
        """Determine if two samples should be grouped together based on multiple criteria."""
        from difflib import SequenceMatcher
        
        # Criterion 1: High string similarity
        similarity = SequenceMatcher(None, name1.lower(), name2.lower()).ratio()
        if similarity > 0.8:
            return True
        
        # Criterion 2: Same core name with different suffixes
        core1 = self._extract_instrument_group_name(name1, path1)
        core2 = self._extract_instrument_group_name(name2, path2)
        if core1 == core2 and core1 != "instrument":
            return True
        
        # Criterion 3: Common prefix with note/velocity/round-robin variations
        # Remove numbers and common suffixes to find base
        clean1 = re.sub(r'[_\s-]*[0-9]+[_\s-]*$', '', name1.lower())
        clean2 = re.sub(r'[_\s-]*[0-9]+[_\s-]*$', '', name2.lower())
        
        if clean1 == clean2 and len(clean1) > 3:
            return True
        
        # Criterion 4: Note variations (C4, D4, etc.)
        note_pattern = r'^(.+?)[_\s-]*[a-g][#b]?[0-9]?[_\s-]*'
        match1 = re.match(note_pattern, name1.lower())
        match2 = re.match(note_pattern, name2.lower())
        
        if match1 and match2:
            base1 = match1.group(1).strip('_- ')
            base2 = match2.group(1).strip('_- ')
            if base1 == base2 and len(base1) > 2:
                return True
        
        # Criterion 5: Velocity variations (v1, v2, vel01, etc.)
        vel_pattern = r'^(.+?)[_\s-]*v(el)?(ocity)?[_\s-]*[0-9]+.*$'
        match1 = re.match(vel_pattern, name1.lower())
        match2 = re.match(vel_pattern, name2.lower())
        
        if match1 and match2:
            base1 = match1.group(1).strip('_- ')
            base2 = match2.group(1).strip('_- ')
            if base1 == base2 and len(base1) > 2:
                return True
        
        # Criterion 6: Same folder and similar length names
        if os.path.dirname(path1) == os.path.dirname(path2):
            if abs(len(name1) - len(name2)) <= 2 and similarity > 0.6:
                return True
        
        return False

    def _merge_similar_groups(self, groups):
        """Merge groups that have very similar names (catch edge cases)."""
        from difflib import SequenceMatcher
        
        group_items = list(groups.items())
        merged_groups = defaultdict(list)
        processed_groups = set()
        
        for i, (group_name, files) in enumerate(group_items):
            if group_name in processed_groups:
                continue
                
            # Find groups to merge with this one
            current_files = files[:]
            merged_name = group_name
            processed_groups.add(group_name)
            
            for j, (other_name, other_files) in enumerate(group_items[i+1:], i+1):
                if other_name in processed_groups:
                    continue
                    
                # Check if group names are similar enough to merge
                similarity = SequenceMatcher(None, group_name.lower(), other_name.lower()).ratio()
                
                if similarity > 0.85:  # Very high similarity threshold for group merging
                    current_files.extend(other_files)
                    processed_groups.add(other_name)
                    # Use the shorter, cleaner name
                    if len(other_name) < len(merged_name) and other_name.strip():
                        merged_name = other_name
            
            if current_files:
                merged_groups[merged_name] = sorted(list(set(current_files)))
        
        return merged_groups

    def preview_sample_grouping(self, mode="multi-sample"):
        """Preview how samples will be grouped without creating instruments (for debugging)."""
        if not self.folder_path or not os.path.isdir(self.folder_path):
            return "No valid folder selected."
        
        search_path = (
            os.path.join(self.folder_path, "**", "*.wav")
            if self.options.recursive_scan
            else os.path.join(self.folder_path, "*.wav")
        )
        all_wavs = glob.glob(search_path, recursive=self.options.recursive_scan)
        
        if mode == "drum-kit":
            groups = group_similar_files(self.folder_path) if IMPORTS_SUCCESSFUL else {}
            if not groups:
                groups = self._group_samples_intelligently(all_wavs)
        else:
            groups = self.group_wav_files(mode)
        
        if not groups:
            return "No WAV files found or no groups created."
        
        preview_text = f"Sample Grouping Preview ({mode} mode):\n"
        preview_text += f"Found {sum(len(files) for files in groups.values())} samples in {len(groups)} groups\n\n"
        
        for group_name, files in groups.items():
            preview_text += f"📁 Group: '{group_name}' ({len(files)} samples)\n"
            for file_path in files[:5]:  # Show first 5 files
                preview_text += f"   • {os.path.basename(file_path)}\n"
            if len(files) > 5:
                preview_text += f"   ... and {len(files) - 5} more files\n"
            preview_text += "\n"
        
        return preview_text

    def test_pitch_detection_accuracy(self, sample_path):
        """
        Comprehensive pitch detection test showing results from all available methods.
        
        Args:
            sample_path: Path to the audio sample to test
            
        Returns:
            Detailed analysis report as a string
        """
        if not os.path.exists(sample_path):
            return f"❌ Error: File not found: {sample_path}"
        
        if not sample_path.lower().endswith('.wav'):
            return f"❌ Error: File must be a WAV file: {sample_path}"
        
        filename = os.path.basename(sample_path)
        report = f"🎵 Pitch Detection Test: {filename}\n"
        report += "=" * 60 + "\n\n"
        
        # Test Method 1: WAV Metadata (smpl chunk)
        try:
            from firmware_profiles import extract_root_note_from_wav
            metadata_note = extract_root_note_from_wav(sample_path)
            if metadata_note is not None:
                note_name = self._midi_to_note_name(metadata_note)
                report += f"✅ WAV Metadata (smpl chunk): MIDI {metadata_note} ({note_name})\n"
            else:
                report += f"❌ WAV Metadata: No 'smpl' chunk found\n"
        except Exception as e:
            report += f"❌ WAV Metadata: Error - {e}\n"
        
        # Test Method 2: Filename Inference
        try:
            from firmware_profiles import infer_note_from_filename
            filename_note = infer_note_from_filename(sample_path)
            if filename_note is not None:
                note_name = self._midi_to_note_name(filename_note)
                report += f"✅ Filename Inference: MIDI {filename_note} ({note_name})\n"
            else:
                report += f"❌ Filename Inference: No note pattern found in filename\n"
        except Exception as e:
            report += f"❌ Filename Inference: Error - {e}\n"
        
        # Test Method 3: Audio Analysis (multiple techniques)
        try:
            if IMPORTS_SUCCESSFUL:
                pitch_note = detect_fundamental_pitch(sample_path)
                if pitch_note is not None:
                    note_name = self._midi_to_note_name(pitch_note)
                    report += f"✅ Audio Analysis: MIDI {pitch_note} ({note_name})\n"
                else:
                    report += f"❌ Audio Analysis: Detection failed\n"
            else:
                report += f"❌ Audio Analysis: Required libraries not available\n"
        except Exception as e:
            report += f"❌ Audio Analysis: Error - {e}\n"
        
        # Test the main detection function
        report += "\n" + "-" * 40 + "\n"
        report += "🎯 Main Detection Function (detect_sample_note):\n"
        try:
            main_result = detect_sample_note(sample_path)
            note_name = self._midi_to_note_name(main_result)
            report += f"✅ Final Result: MIDI {main_result} ({note_name})\n"
        except Exception as e:
            report += f"❌ Main Function: Error - {e}\n"
        
        # Add file information
        report += "\n" + "-" * 40 + "\n"
        report += "📊 File Information:\n"
        try:
            import wave
            with wave.open(sample_path, 'rb') as wav:
                frames = wav.getnframes()
                framerate = wav.getframerate()
                channels = wav.getnchannels()
                duration = frames / framerate
                
                report += f"Duration: {duration:.2f} seconds\n"
                report += f"Sample Rate: {framerate} Hz\n"
                report += f"Channels: {channels}\n"
                report += f"Frames: {frames:,}\n"
        except Exception as e:
            report += f"Could not read file info: {e}\n"
        
        # Advanced analysis if librosa is available
        try:
            if IMPORTS_SUCCESSFUL and NUMPY_AVAILABLE:
                report += "\n" + "-" * 40 + "\n"
                report += "🔬 Advanced Audio Analysis:\n"
                
                import librosa
                y, sr = librosa.load(sample_path, sr=None, mono=True)
                
                # Spectral features
                centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
                rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)
                zcr = librosa.feature.zero_crossing_rate(y)
                
                report += f"Spectral Centroid: {np.mean(centroid):.2f} Hz\n"
                report += f"Spectral Rolloff: {np.mean(rolloff):.2f} Hz\n"
                report += f"Zero Crossing Rate: {np.mean(zcr):.4f}\n"
                
                # Estimate if it's harmonic content
                y_harmonic, y_percussive = librosa.effects.hpss(y)
                harmonic_energy = np.sum(y_harmonic**2)
                percussive_energy = np.sum(y_percussive**2)
                total_energy = harmonic_energy + percussive_energy
                
                if total_energy > 0:
                    harmonic_ratio = harmonic_energy / total_energy
                    report += f"Harmonic Content: {harmonic_ratio:.2%}\n"
                    
                    if harmonic_ratio > 0.7:
                        report += "🎼 High harmonic content - Good for pitch detection\n"
                    elif harmonic_ratio > 0.3:
                        report += "🥁 Mixed harmonic/percussive content\n"
                    else:
                        report += "🥁 Mostly percussive content - Pitch detection may be unreliable\n"
            elif not NUMPY_AVAILABLE:
                report += "\nAdvanced analysis requires numpy (pip install numpy)\n"
                
        except Exception as e:
            report += f"\nAdvanced analysis failed: {e}\n"
        
        # Recommendations
        report += "\n" + "=" * 60 + "\n"
        report += "💡 Recommendations:\n"
        report += "• For best results, include note information in filename (e.g., 'Piano_C4.wav')\n"
        report += "• WAV files with 'smpl' chunks provide the most reliable pitch information\n"
        report += "• Audio analysis works best with harmonic (tonal) content\n"
        report += "• Percussive samples may require manual pitch assignment\n"
        
        return report
    
    def _midi_to_note_name(self, midi_note):
        """Convert MIDI note number to note name (e.g., 60 -> C4)."""
        if not isinstance(midi_note, int) or midi_note < 0 or midi_note > 127:
            return "Invalid"
        
        note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        octave = (midi_note // 12) - 1
        note = note_names[midi_note % 12]
        return f"{note}{octave}"

    def validate_sample_info(self, sample_path):
        """Validates a WAV file and extracts info. Detects SCWs if enabled."""
        try:
            if not os.path.exists(sample_path) or not sample_path.lower().endswith(
                ".wav"
            ):
                return {"is_valid": False, "reason": "File not found or not a WAV"}

            frames = get_wav_frames(sample_path)
            is_scw = False
            if self.options.analyze_scw and 0 < frames < SCW_FRAME_THRESHOLD:
                is_scw = True

            # REVISED: Prioritize filename, then pitch detection
            root_note = infer_note_from_filename(sample_path)
            if root_note is None:
                root_note = detect_fundamental_pitch(sample_path)

            return {
                "is_valid": True,
                "path": sample_path,
                "frames": frames,
                "root_note": root_note,
                "is_scw": is_scw,
            }
        except Exception as e:
            logging.error(f"Could not validate sample {sample_path}: {e}")
            return {"is_valid": False, "reason": str(e)}


# </editor-fold>


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.root = self
        
        if not IMPORTS_SUCCESSFUL:
            self.withdraw()
            messagebox.showerror(
                "Missing Dependencies",
                f"A required file could not be found:\n\n{MISSING_MODULE}\n\nPlease make sure all script files are in the same directory.",
            )
            sys.exit(1)

        self.firmware_version = tk.StringVar(value="3.5.0")
        self.title(f"Wav to XPM Converter v{APP_VERSION}")
        self.geometry("850x750")
        self.minsize(700, 600)

        self.creative_config = {}
        self.last_browse_path = os.path.expanduser("~")  # Remember last path

        self.setup_retro_theme()

        main_frame = ttk.Frame(self, padding="10", style="Retro.TFrame")
        main_frame.pack(fill="both", expand=True)
        main_frame.grid_rowconfigure(6, weight=1)  # Adjusted for new row
        main_frame.grid_columnconfigure(0, weight=1)

        self.create_browser_bar(main_frame)
        self.create_advanced_options_frame(main_frame)
        self.create_action_buttons(main_frame)
        self.create_advanced_tools(main_frame)
        self.create_quick_edits_frame(main_frame)  # New frame
        self.create_batch_tools(main_frame)
        self.create_log_viewer(main_frame)
        self.create_status_bar(main_frame)

        self.setup_logging()

    def _safe_file_dialog(self, dialog_type='folder', **kwargs):
        """Safely handle file dialogs to prevent macOS NSInvalidArgumentException"""
        try:
            if dialog_type == 'folder':
                # Ensure we have an initial directory
                kwargs.setdefault('initialdir', os.path.expanduser("~"))
                # Ensure we have a parent
                kwargs.setdefault('parent', self)
                result = filedialog.askdirectory(**kwargs)
            else:
                result = None
                
            # Never return None
            return result if result else ""
        except Exception as e:
            print(f"File dialog error: {e}")
            return ""

    def __init__(self):
        super().__init__()
        self.root = self
        
        if not IMPORTS_SUCCESSFUL:
            self.withdraw()
            messagebox.showerror(
                "Missing Dependencies",
                f"A required file could not be found:\n\n{MISSING_MODULE}\n\nPlease make sure all script files are in the same directory.",
            )
            sys.exit(1)

        self.firmware_version = tk.StringVar(value="3.5.0")
        self.title(f"Wav to XPM Converter v{APP_VERSION}")
        self.geometry("850x750")
        self.minsize(700, 600)

        self.creative_config = {}
        self.last_browse_path = os.path.expanduser("~")  # Remember last path

        self.setup_retro_theme()

        main_frame = ttk.Frame(self, padding="10", style="Retro.TFrame")
        main_frame.pack(fill="both", expand=True)
        main_frame.grid_rowconfigure(6, weight=1)  # Adjusted for new row
        main_frame.grid_columnconfigure(0, weight=1)

        self.create_browser_bar(main_frame)
        self.create_advanced_options_frame(main_frame)
        self.create_action_buttons(main_frame)
        self.create_advanced_tools(main_frame)
        self.create_quick_edits_frame(main_frame)  # New frame
        self.create_batch_tools(main_frame)
        self.create_log_viewer(main_frame)
        self.create_status_bar(main_frame)

        self.setup_logging()

    def setup_logging(self):
        log_format = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(funcName)s - %(message)s"
        )
        text_handler = TextHandler(self.log_text)
        text_handler.setFormatter(log_format)
        root_logger = logging.getLogger()
        if root_logger.hasHandlers():
            root_logger.handlers.clear()

        file_handler = logging.FileHandler("converter.log", mode="a", encoding="utf-8")
        file_handler.setFormatter(log_format)
        root_logger.addHandler(file_handler)

        root_logger.addHandler(text_handler)
        root_logger.setLevel(logging.INFO)
        logging.info(f"Application started. Version {APP_VERSION}.")

    # <editor-fold desc="GUI Creation Methods">
    def setup_retro_theme(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        self.configure(background=MPC_BEIGE)
        style.configure("TFrame", background=MPC_BEIGE)
        style.configure("Retro.TFrame", background=MPC_BEIGE)
        style.configure("TLabelframe", background=MPC_BEIGE, bordercolor=MPC_DARK_GREY)
        style.configure(
            "TLabelframe.Label",
            background=MPC_BEIGE,
            foreground=MPC_DARK_GREY,
            font=("Helvetica", 10, "bold"),
        )
        style.configure(
            "TLabel",
            background=MPC_BEIGE,
            foreground=MPC_DARK_GREY,
            font=("Helvetica", 10),
        )
        style.configure(
            "TButton",
            background=MPC_PAD_GREY,
            foreground=MPC_WHITE,
            borderwidth=1,
            focusthickness=3,
            focuscolor="none",
        )
        style.map(
            "TButton",
            background=[("active", MPC_DARK_GREY)],
            foreground=[("active", MPC_WHITE)],
        )
        style.configure(
            "Accent.TButton",
            background=MPC_RED,
            foreground=MPC_WHITE,
            font=("Helvetica", 10, "bold"),
        )
        style.map("Accent.TButton", background=[("active", "#A01818")])
        style.configure(
            "TEntry",
            fieldbackground=MPC_WHITE,
            foreground=MPC_DARK_GREY,
            bordercolor=MPC_DARK_GREY,
            insertcolor=MPC_DARK_GREY,
        )
        style.configure(
            "TCombobox",
            fieldbackground=MPC_WHITE,
            foreground=MPC_DARK_GREY,
            bordercolor=MPC_DARK_GREY,
            arrowcolor=MPC_DARK_GREY,
        )
        style.configure("TCheckbutton", background=MPC_BEIGE, foreground=MPC_DARK_GREY)
        style.map(
            "TCheckbutton",
            background=[("active", MPC_BEIGE)],
            indicatorcolor=[("selected", MPC_RED), ("!selected", MPC_DARK_GREY)],
        )
        style.configure(
            "Treeview",
            background=MPC_WHITE,
            fieldbackground=MPC_WHITE,
            foreground=MPC_DARK_GREY,
        )
        style.configure(
            "Treeview.Heading",
            background=MPC_PAD_GREY,
            foreground=MPC_WHITE,
            font=("Helvetica", 10, "bold"),
        )
        style.map("Treeview.Heading", background=[("active", MPC_DARK_GREY)])
        style.configure(
            "TProgressbar",
            troughcolor=MPC_PAD_GREY,
            background=MPC_RED,
            bordercolor=MPC_DARK_GREY,
        )
        style.configure(
            "Vertical.TScrollbar",
            troughcolor=MPC_BEIGE,
            background=MPC_PAD_GREY,
            bordercolor=MPC_DARK_GREY,
            arrowcolor=MPC_WHITE,
        )

    def create_browser_bar(self, parent):
        bar = ttk.LabelFrame(parent, text="Source Folder", padding="5")
        bar.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        bar.grid_columnconfigure(0, weight=1)
        self.folder_path = tk.StringVar()
        ttk.Entry(bar, textvariable=self.folder_path).grid(row=0, column=0, sticky="ew")
        ttk.Button(bar, text="Browse...", command=self.browse_folder).grid(
            row=0, column=1, padx=(5, 0)
        )

    def create_advanced_options_frame(self, parent):
        frame = ttk.LabelFrame(parent, text="Keygroup Options", padding="10")
        frame.grid(row=1, column=0, sticky="ew", pady=5)
        frame.grid_columnconfigure(1, weight=1)

        ttk.Label(frame, text="Target Firmware:").grid(
            row=0, column=0, sticky="e", padx=5, pady=2
        )
        ttk.Combobox(
            frame,
            textvariable=self.firmware_version,
            values=["2.3.0.0", "2.6.0.17", "3.4.0", "3.5.0"],
            state="readonly",
        ).grid(row=0, column=1, sticky="ew")

        ttk.Label(frame, text="Polyphony:").grid(
            row=1, column=0, sticky="e", padx=5, pady=2
        )
        self.polyphony_var = tk.IntVar(value=16)
        ttk.Spinbox(frame, from_=1, to=64, textvariable=self.polyphony_var).grid(
            row=1, column=1, sticky="ew"
        )

        creative_frame = ttk.Frame(frame)
        creative_frame.grid(row=2, column=1, sticky="ew")
        creative_frame.grid_columnconfigure(0, weight=1)

        ttk.Label(frame, text="Creative Mode:").grid(
            row=2, column=0, sticky="e", padx=5, pady=2
        )
        self.creative_mode_var = tk.StringVar(value="off")
        creative_modes = ["off", "subtle", "synth", "lofi", "reverse", "stereo_spread"]
        self.creative_combo = ttk.Combobox(
            creative_frame,
            textvariable=self.creative_mode_var,
            values=creative_modes,
            state="readonly",
        )
        self.creative_combo.grid(row=0, column=0, sticky="ew")
        self.creative_combo.bind("<<ComboboxSelected>>", self.on_creative_mode_change)
        self.creative_mode_var.trace_add(
            "write", lambda *a: self.on_creative_mode_change()
        )

        self.creative_config_btn = ttk.Button(
            creative_frame,
            text="Configure...",
            command=self.open_creative_config,
            state="disabled",
        )
        self.creative_config_btn.grid(row=0, column=1, padx=(5, 0))

        check_frame = ttk.Frame(frame)
        check_frame.grid(row=3, column=0, columnspan=2, sticky="w", pady=5)
        self.loop_one_shots_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            check_frame, text="Loop One-Shots", variable=self.loop_one_shots_var
        ).pack(side="left", padx=5)
        self.analyze_scw_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            check_frame, text="Analyze SCW", variable=self.analyze_scw_var
        ).pack(side="left", padx=5)
        self.recursive_scan_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            check_frame, text="Recursive Scan", variable=self.recursive_scan_var
        ).pack(side="left", padx=5)

    def create_action_buttons(self, parent):
        frame = ttk.LabelFrame(parent, text="Build Instruments", padding="10")
        frame.grid(row=2, column=0, sticky="ew", pady=5)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=1)

        ttk.Button(
            frame,
            text="Build Multi-Sampled Instruments",
            command=self.build_multi_sample_instruments,
            style="Accent.TButton",
        ).grid(row=0, column=0, sticky="ew", padx=2, pady=2)
        ttk.Button(
            frame,
            text="Build One-Shot Instruments",
            command=self.build_one_shot_instruments,
        ).grid(row=0, column=1, sticky="ew", padx=2, pady=2)
        ttk.Button(
            frame, text="Build Drum Kit", command=self.build_drum_kit_instruments
        ).grid(row=1, column=0, columnspan=2, sticky="ew", padx=2, pady=2)

    def create_advanced_tools(self, parent):
        frame = ttk.LabelFrame(parent, text="Advanced Tools", padding="10")
        frame.grid(row=3, column=0, sticky="ew", pady=5)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=1)
        ttk.Button(
            frame,
            text="Single-Cycle Waveform (SCW) Tool...",
            command=lambda: self.open_window(SCWToolWindow),
        ).grid(row=0, column=0, sticky="ew", padx=2, pady=2)
        ttk.Button(
            frame,
            text="Batch Program Editor...",
            command=lambda: self.open_window(BatchProgramEditorWindow),
        ).grid(row=0, column=1, sticky="ew", padx=2, pady=2)
        ttk.Button(
            frame,
            text="Batch Program Fixer...",
            command=lambda: self.open_window(BatchProgramFixerWindow),
        ).grid(row=1, column=0, columnspan=2, sticky="ew", padx=2, pady=2)
        ttk.Button(
            frame,
            text="Sample Mapping Checker...",
            command=lambda: self.open_window(SampleMappingCheckerWindow),
        ).grid(row=2, column=0, columnspan=2, sticky="ew", padx=2, pady=2)

    def create_quick_edits_frame(self, parent):
        frame = ttk.LabelFrame(parent, text="Quick Edits", padding="10")
        frame.grid(row=4, column=0, sticky="ew", pady=5)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=1)
        ttk.Button(
            frame, text="Set All Programs to MONO", command=self.run_set_all_to_mono
        ).grid(row=0, column=0, sticky="ew", padx=2, pady=2)
        ttk.Button(
            frame, text="Normalize Program Levels", command=self.run_normalize_levels
        ).grid(row=0, column=1, sticky="ew", padx=2, pady=2)

    def create_batch_tools(self, parent):
        frame = ttk.LabelFrame(parent, text="Utilities & Batch Tools", padding="10")
        frame.grid(row=5, column=0, sticky="ew", pady=(10, 0))
        for i in range(5):
            frame.grid_columnconfigure(i, weight=1)
        ttk.Button(
            frame, text="Expansion Doctor", command=self.open_expansion_doctor
        ).grid(row=0, column=0, sticky="ew", padx=2)
        ttk.Button(frame, text="File Renamer", command=self.open_file_renamer).grid(
            row=0, column=1, sticky="ew", padx=2
        )
        ttk.Button(
            frame, text="Generate All Previews", command=self.generate_previews
        ).grid(row=0, column=2, sticky="ew", padx=2)
        ttk.Button(
            frame, text="Clean All Previews", command=self.run_clean_all_previews
        ).grid(row=0, column=3, sticky="ew", padx=2)
        ttk.Button(
            frame, text="Expansion Builder", command=self.open_expansion_builder
        ).grid(row=0, column=4, sticky="ew", padx=2)

        ttk.Button(
            frame, text="Merge Subfolders", command=self.open_merge_subfolders
        ).grid(row=1, column=0, sticky="ew", padx=2, pady=2)
        ttk.Button(
            frame, text="Smart Split...", command=self.open_smart_split_window
        ).grid(row=1, column=1, sticky="ew", padx=2, pady=2)
        ttk.Button(
            frame, text="Batch Transpose", command=self.open_batch_transpose
        ).grid(row=1, column=2, sticky="ew", padx=2, pady=2)
        ttk.Button(
            frame,
            text="Package Expansion (.zip)",
            command=self.package_expansion,
            style="Accent.TButton",
        ).grid(row=1, column=3, columnspan=2, sticky="ew", padx=2, pady=2)

    def create_log_viewer(self, parent):
        log_frame = ttk.LabelFrame(parent, text="Log", padding=5)
        log_frame.grid(row=6, column=0, sticky="nsew", pady=(10, 0))
        log_frame.grid_rowconfigure(0, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)

        self.log_text = tk.Text(
            log_frame,
            height=10,
            wrap="word",
            state="disabled",
            bg=MPC_WHITE,
            fg=MPC_DARK_GREY,
        )
        self.log_text.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(
            log_frame,
            orient="vertical",
            command=self.log_text.yview,
            style="Vertical.TScrollbar",
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text["yscrollcommand"] = scrollbar.set

    def create_status_bar(self, parent):
        frame = ttk.Frame(parent, padding=(5, 2))
        frame.grid(row=7, column=0, sticky="ew", pady=(5, 0))
        frame.grid_columnconfigure(0, weight=1)
        self.status_text = tk.StringVar(value="Ready.")
        ttk.Label(frame, textvariable=self.status_text, anchor="w").grid(
            row=0, column=0, sticky="ew"
        )
        self.progress = ttk.Progressbar(
            frame, orient="horizontal", length=150, mode="determinate"
        )
        self.progress.grid(row=0, column=1, sticky="e")

    # </editor-fold>

    # <editor-fold desc="GUI Event Handlers & Window Openers">
    def browse_folder(self):
        try:
            # Use the safe file dialog method
            folder = self._safe_file_dialog(
                'folder',
                title="Select Sample Folder",
                initialdir=getattr(self, 'last_browse_path', os.path.expanduser("~"))
            )
            
            if folder and os.path.exists(folder):
                self.folder_path.set(folder)
                self.last_browse_path = folder
                logging.info(f"Selected folder: {folder}")
        except Exception as e:
            logging.error(f"Error in folder browse dialog: {e}")
            # Fallback to basic dialog if the advanced one fails
            try:
                folder = filedialog.askdirectory(
                    parent=self,
                    title="Select Sample Folder",
                    initialdir=getattr(self, 'last_browse_path', os.path.expanduser("~"))
                )
                if folder and os.path.exists(folder):
                    self.folder_path.set(folder)
                    self.last_browse_path = folder
                    logging.info(f"Selected folder (fallback): {folder}")
            except Exception as e2:
                logging.error(f"Both folder dialog methods failed: {e2}")
                messagebox.showerror("Error", f"Failed to open folder selection dialog: {e2}", parent=self)

    def on_creative_mode_change(self, event=None):
        """Enable config button only for configurable modes."""
        configurable_modes = ["synth", "lofi"]
        if self.creative_mode_var.get() in configurable_modes:
            self.creative_config_btn.config(state="normal")
        else:
            self.creative_config_btn.config(state="disabled")

    # REVISED: Corrected window opening logic with improved SampleMappingChecker support
    def open_window(self, window_class, *args):
        if window_class is None:
            messagebox.showerror(
                "Missing Dependency",
                f"This feature is unavailable. Missing module: {MISSING_MODULE}",
                parent=self.root,
            )
            return
            
        # Define windows that can be opened without a source folder
        folder_independent_windows = [
            ExpansionBuilderWindow,
            BatchProgramFixerWindow,
            CreativeModeConfigWindow,
        ]
        
        # Special case for SampleMappingCheckerWindow - we want to pass the folder but not require it
        if hasattr(window_class, '__name__') and window_class.__name__ == "SampleMappingCheckerWindow":
            folder_independent_windows.append(window_class)
            
        if window_class not in folder_independent_windows and (
            not self.folder_path.get() or not os.path.isdir(self.folder_path.get())
        ):
            messagebox.showerror(
                "Error", "Please select a valid source folder first.", parent=self.root
            )
            return
            
        try:
            # Check if window is already open
            for win in self.winfo_children():
                if isinstance(win, tk.Toplevel) and type(win) == window_class:
                    win.focus()
                    win.lift()
                    return
                    
            # Create new window
            window = window_class(self, *args)
            
            # Special handling for Sample Mapping Checker - make sure it loads the folder
            if hasattr(window_class, '__name__') and window_class.__name__ == "SampleMappingCheckerWindow" and hasattr(window, "load_folder"):
                folder = self.folder_path.get()
                if folder and os.path.isdir(folder):
                    logging.info(f"Loading folder {folder} in Sample Mapping Checker")
                    # Ensure the window is fully created before loading the folder
                    # Use a delay to allow the window to initialize properly
                    self.root.after(200, lambda f=folder: window.load_folder(f))
                    
        except Exception as e:
            logging.error(
                f"Error opening {getattr(window_class, '__name__', str(window_class))}: {e}\n{traceback.format_exc()}"
            )
            messagebox.showerror(
                "Error", f"Failed to open window.\n{e}", parent=self.root
            )

    def open_expansion_doctor(self):
        self.open_window(ExpansionDoctorWindow)

    def open_file_renamer(self):
        self.open_window(FileRenamerWindow)

    def open_expansion_builder(self):
        self.open_window(ExpansionBuilderWindow)

    def open_smart_split_window(self):
        self.open_window(SmartSplitWindow)

    def open_batch_transpose(self):
        self.open_window(BatchTransposeWindow)

    def open_creative_config(self):
        self.open_window(CreativeModeConfigWindow, self.creative_mode_var.get())

    # </editor-fold>

    # RESTORED: Build buttons now open the MultiSampleBuilderWindow
    def build_multi_sample_instruments(self):
        if IMPORTS_SUCCESSFUL:
            self.open_window(
                MultiSampleBuilderWindow,
                InstrumentBuilder,
                InstrumentOptions,
                "multi-sample",
            )
        else:
            messagebox.showerror(
                "Missing Dependency",
                "The 'multi_sample_builder.py' script is required for this feature.",
            )

    def build_one_shot_instruments(self):
        if IMPORTS_SUCCESSFUL:
            self.open_window(
                MultiSampleBuilderWindow,
                InstrumentBuilder,
                InstrumentOptions,
                "one-shot",
            )
        else:
            messagebox.showerror(
                "Missing Dependency",
                "The 'multi_sample_builder.py' script is required for this feature.",
            )

    def build_drum_kit_instruments(self):
        if IMPORTS_SUCCESSFUL:
            self.open_window(
                MultiSampleBuilderWindow,
                InstrumentBuilder,
                InstrumentOptions,
                "drum-kit",
            )
        else:
            messagebox.showerror(
                "Missing Dependency",
                "The 'multi_sample_builder.py' script is required for this feature.",
            )

    def run_batch_process(
        self, process_func, params_dict, confirm=False, confirm_message=""
    ):
        folder = self.folder_path.get()
        if not folder or not os.path.isdir(folder):
            messagebox.showerror(
                "Error", "Please select a valid folder first.", parent=self.root
            )
            return

        if confirm and not messagebox.askyesno(
            "Confirm Action", confirm_message, parent=self.root
        ):
            return

        def run():
            self.progress.config(mode="indeterminate")
            self.progress.start()
            try:
                result = process_func(folder, params_dict)
                logging.info(
                    f"Batch process '{process_func.__name__}' completed. {result or 0} item(s) affected."
                )

                def show_success():
                    messagebox.showinfo(
                        "Done",
                        f"Process complete. {result or 0} item(s) affected.",
                        parent=self.root,
                    )

                self.root.after_idle(show_success)
            except Exception as e:
                error_msg = str(e)
                logging.error(
                    f"Error in batch process: {error_msg}\n{traceback.format_exc()}"
                )

                def show_error():
                    messagebox.showerror(
                        "Error", f"Operation failed:\n{error_msg}", parent=self.root
                    )

                self.root.after_idle(show_error)
            finally:
                self.progress.stop()
                self.progress.config(mode="determinate")
                self.status_text.set("Ready.")

        self.status_text.set(f"Running {process_func.__name__}...")
        threading.Thread(target=run, daemon=True).start()

    def run_set_all_to_mono(self):
        """Wrapper to run the set_to_mono function in a thread."""
        folder = self.folder_path.get()
        if not folder or not os.path.isdir(folder):
            messagebox.showerror(
                "Error", "Please select a valid folder first.", parent=self.root
            )
            return

        if not messagebox.askyesno(
            "Confirm Action",
            "This will modify all .xpm files in the selected folder to be monophonic. This action is fast but cannot be easily undone. Continue?",
            parent=self.root,
        ):
            return

        def run():
            self.status_text.set("Setting programs to mono...")
            self.progress.config(mode="indeterminate")
            self.progress.start()
            try:
                count = quick_edit_set_mono(folder)
                self.root.after_idle(
                    lambda: messagebox.showinfo(
                        "Success",
                        f"Updated {count} program(s) to mono.",
                        parent=self.root,
                    ),
                )
            except Exception as e:
                logging.error(
                    f"Failed to set programs to mono: {e}\n{traceback.format_exc()}"
                )
                self.root.after_idle(
                    lambda: messagebox.showerror(
                        "Error", f"An error occurred: {e}", parent=self.root
                    ),
                )
            finally:
                self.progress.stop()
                self.progress.config(mode="determinate")
                self.status_text.set("Ready.")

        threading.Thread(target=run, daemon=True).start()

    def run_normalize_levels(self):
        """Wrapper to run the normalize levels function in a thread."""
        folder = self.folder_path.get()
        if not folder or not os.path.isdir(folder):
            messagebox.showerror(
                "Error", "Please select a valid folder first.", parent=self.root
            )
            return

        if not messagebox.askyesno(
            "Confirm Action",
            "This will set the Volume parameter to 0.95 for all instruments in all .xpm files in the selected folder. This action cannot be easily undone. Continue?",
            parent=self.root,
        ):
            return

        def run():
            self.status_text.set("Normalizing program levels...")
            self.progress.config(mode="indeterminate")
            self.progress.start()
            try:
                count = quick_edit_normalize_levels(folder)
                self.root.after_idle(
                    lambda: messagebox.showinfo(
                        "Success",
                        f"Normalized volume for {count} program(s).",
                        parent=self.root,
                    ),
                )
            except Exception as e:
                logging.error(
                    f"Failed to normalize program levels: {e}\n{traceback.format_exc()}"
                )
                self.root.after_idle(
                    lambda: messagebox.showerror(
                        "Error", f"An error occurred: {e}", parent=self.root
                    ),
                )
            finally:
                self.progress.stop()
                self.progress.config(mode="determinate")
                self.status_text.set("Ready.")

        threading.Thread(target=run, daemon=True).start()

    def run_clean_all_previews(self):
        """Wrapper to run the clean previews function in a thread."""
        folder = self.folder_path.get()
        if not folder or not os.path.isdir(folder):
            messagebox.showerror(
                "Error", "Please select a valid folder first.", parent=self.root
            )
            return

        if not messagebox.askyesno(
            "Confirm Deletion",
            "WARNING: This will permanently delete all folders named '[Previews]' in the selected directory and all its subdirectories.\n\nThis action cannot be undone. Are you sure you want to continue?",
            parent=self.root,
            icon="warning",
        ):
            return

        def run():
            self.status_text.set("Cleaning all preview files...")
            self.progress.config(mode="indeterminate")
            self.progress.start()
            try:
                count = clean_all_previews(folder)
                self.root.after_idle(
                    lambda: messagebox.showinfo(
                        "Success",
                        f"Deleted {count} preview folder(s).",
                        parent=self.root,
                    ),
                )
            except Exception as e:
                logging.error(
                    f"Failed to clean previews: {e}\n{traceback.format_exc()}"
                )
                self.root.after_idle(
                    lambda: messagebox.showerror(
                        "Error",
                        f"An error occurred while cleaning previews: {e}",
                        parent=self.root,
                    ),
                )
            finally:
                self.progress.stop()
                self.progress.config(mode="determinate")
                self.status_text.set("Ready.")

        threading.Thread(target=run, daemon=True).start()

    def open_merge_subfolders(self):
        self.open_window(MergeSubfoldersWindow)

    def generate_previews(self):
        builder = InstrumentBuilder(self.folder_path.get(), self, InstrumentOptions())
        threading.Thread(target=builder.process_previews_only, daemon=True).start()

    def package_expansion(self):
        folder = self.folder_path.get()
        if not folder or not os.path.isdir(folder):
            messagebox.showerror(
                "Error", "Please select a valid folder first.", parent=self.root
            )
            return

        save_path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Save Expansion As ZIP",
            defaultextension=".zip",
            filetypes=[("ZIP Archive", "*.zip")],
            initialdir=self.last_browse_path,
        )
        if not save_path:
            return

        def run():
            self.progress.config(mode="indeterminate")
            self.progress.start()
            self.status_text.set("Packaging expansion...")
            try:
                logging.info("Starting expansion packaging process...")

                if not os.path.exists(os.path.join(folder, "Expansion.xml")):
                    if messagebox.askyesno(
                        "Create Expansion File",
                        "No Expansion.xml found. Would you like to create one now to include it in the package?",
                        parent=self.root,
                    ):
                        logging.warning(
                            "Expansion.xml missing. User prompted to create one."
                        )

                self.status_text.set("Creating ZIP archive...")
                with zipfile.ZipFile(save_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk(folder):
                        for file in files:
                            if os.path.join(root, file) == save_path:
                                continue
                            zipf.write(
                                os.path.join(root, file),
                                os.path.relpath(
                                    os.path.join(root, file), os.path.dirname(folder)
                                ),
                            )

                logging.info(f"Expansion successfully packaged to {save_path}")
                self.root.after_idle(
                    lambda: messagebox.showinfo(
                        "Success",
                        f"Expansion packaged successfully to:\n{save_path}",
                        parent=self.root,
                    ),
                )

            except Exception as e:
                logging.error(f"Error during packaging: {e}\n{traceback.format_exc()}")
                self.root.after_idle(
                    lambda: messagebox.showerror(
                        "Error", f"Packaging failed:\n{e}", parent=self.root
                    ),
                )
            finally:
                self.progress.stop()
                self.progress.config(mode="determinate")
                self.status_text.set("Ready.")

        threading.Thread(target=run, daemon=True).start()


def merge_subfolders(folder_path, params):
    """Moves files from subfolders up to the specified depth."""
    moved_count = 0
    target_depth = params.get("target_depth", 0)
    max_depth = params.get("max_depth", 2)
    for root, dirs, files in os.walk(folder_path, topdown=False):
        rel = os.path.relpath(root, folder_path)
        depth = 0 if rel == "." else len(rel.split(os.sep))
        if depth == 0 or depth > max_depth or depth <= target_depth:
            continue
        dest_dir = (
            folder_path
            if target_depth == 0
            else os.path.join(folder_path, *rel.split(os.sep)[:target_depth])
        )
        os.makedirs(dest_dir, exist_ok=True)
        for file in files:
            src_path = os.path.join(root, file)
            dest_path = os.path.join(dest_dir, file)
            if os.path.exists(dest_path):
                subfolder_name = os.path.basename(root)
                name, ext = os.path.splitext(file)
                dest_path = os.path.join(dest_dir, f"{subfolder_name}_{name}{ext}")
            try:
                shutil.move(src_path, dest_path)
                moved_count += 1
            except Exception as e:
                logging.error(f"Could not move {src_path}: {e}")
        if not os.listdir(root):
            try:
                os.rmdir(root)
                logging.info(f"Removed empty subfolder: {root}")
            except OSError as e:
                logging.warning(f"Could not remove directory {root}: {e}")
    return moved_count


def merge_subfolders_to_root(folder_path, max_depth=2):
    """Backward compatible wrapper for merging to the root folder."""
    return merge_subfolders(folder_path, {"target_depth": 0, "max_depth": max_depth})


def split_files_smartly(folder_path, params):
    """Organizes XPMs and WAVs into subfolders based on the chosen mode."""
    moved_count = 0
    mode = params.get("mode", "word")

    # First process XPM files so samples move with them
    xpm_files = glob.glob(os.path.join(folder_path, "*.xpm"))
    for xpm_path in xpm_files:
        try:
            basename = os.path.basename(xpm_path)
            subfolder_name = None

            if mode == "word":
                subfolder_name = basename.split(" ")[0].split("_")[0].split("-")[0]
            elif mode == "prefix":
                m = re.match(r"([A-Za-z0-9]+[_-])", basename)
                if m:
                    subfolder_name = m.group(1).strip("_-")
            else:  # category
                with open(xpm_path, "r", encoding="utf-8", errors="ignore") as f:
                    xpm_text = f.read()
                subfolder_name = get_base_instrument_name(xpm_path, xpm_text)

            if not subfolder_name:
                continue

            subfolder_path = os.path.join(folder_path, subfolder_name)
            os.makedirs(subfolder_path, exist_ok=True)
            dest_xpm = os.path.join(subfolder_path, basename)
            shutil.move(xpm_path, dest_xpm)
            moved_count += 1

            for sample in parse_xpm_samples(dest_xpm):
                sample_norm = sample.replace("/", os.sep)
                sample_abs = (
                    os.path.join(folder_path, sample_norm)
                    if not os.path.isabs(sample_norm)
                    else sample_norm
                )
                if os.path.exists(sample_abs):
                    dest_sample = os.path.join(
                        subfolder_path, os.path.basename(sample_norm)
                    )
                    if os.path.exists(dest_sample):
                        base, ext = os.path.splitext(os.path.basename(sample_norm))
                        dest_sample = os.path.join(subfolder_path, f"{base}_1{ext}")
                    try:
                        shutil.move(sample_abs, dest_sample)
                        moved_count += 1
                    except Exception as e:
                        logging.error(f"Could not move {sample_abs}: {e}")
        except Exception as e:
            logging.error(f"Could not process {xpm_path}: {e}")

    # Now process remaining WAV files
    all_wavs = glob.glob(os.path.join(folder_path, "*.wav"))
    for wav_path in all_wavs:
        try:
            subfolder_name = None
            basename = os.path.basename(wav_path)

            if mode == "word":
                subfolder_name = basename.split(" ")[0].split("_")[0].split("-")[0]
            elif mode == "prefix":
                match = re.match(r"([A-Za-z0-9]+[_-])", basename)
                if match:
                    subfolder_name = match.group(1).strip("_-")
            else:  # category
                subfolder_name = get_base_instrument_name(wav_path)

            if subfolder_name:
                subfolder_path = os.path.join(folder_path, subfolder_name)
                os.makedirs(subfolder_path, exist_ok=True)
                dest_path = os.path.join(subfolder_path, basename)
                if os.path.exists(dest_path):
                    base, ext = os.path.splitext(basename)
                    dest_path = os.path.join(subfolder_path, f"{base}_1{ext}")
                shutil.move(wav_path, dest_path)
                moved_count += 1
        except Exception as e:
            logging.error(f"Could not split file {wav_path}: {e}")

    return moved_count


def quick_edit_set_mono(folder_path):
    """
    Iterates through all XPM files and sets their VoiceOverlap to Mono.
    This is a direct XML edit for speed.
    """
    count = 0
    xpm_files = glob.glob(os.path.join(folder_path, "**", "*.xpm"), recursive=True)
    for path in xpm_files:
        try:
            tree = ET.parse(path)
            root = tree.getroot()
            changed = False
            # Find all VoiceOverlap tags within any Instrument
            for vo_element in root.findall(".//Instrument/VoiceOverlap"):
                if vo_element.text != "Mono":
                    vo_element.text = "Mono"
                    changed = True

            if changed:
                indent_tree(tree)
                tree.write(path, encoding="utf-8", xml_declaration=True)
                count += 1
                logging.info(f"Set {os.path.basename(path)} to Mono.")
        except ET.ParseError as e:
            logging.error(f"Could not parse {path}: {e}")
        except Exception as e:
            logging.error(f"Failed to process {path} for mono edit: {e}")
    return count


def quick_edit_normalize_levels(folder_path):
    """
    Iterates through all XPM files and sets their instrument Volume to 0.95.
    This is a direct XML edit for speed.
    """
    count = 0
    xpm_files = glob.glob(os.path.join(folder_path, "**", "*.xpm"), recursive=True)
    for path in xpm_files:
        try:
            tree = ET.parse(path)
            root = tree.getroot()
            changed = False
            # Find all Volume tags within any Instrument
            for vol_element in root.findall(".//Instrument/Volume"):
                if vol_element.text != "0.95":
                    vol_element.text = "0.95"
                    changed = True

            if changed:
                indent_tree(tree)
                tree.write(path, encoding="utf-8", xml_declaration=True)
                count += 1
                logging.info(f"Normalized volume for {os.path.basename(path)}.")
        except ET.ParseError as e:
            logging.error(f"Could not parse {path}: {e}")
        except Exception as e:
            logging.error(f"Failed to process {path} for normalize edit: {e}")
    return count


def clean_all_previews(folder_path):
    """
    Recursively finds and deletes all folders named '[Previews]'.
    """
    deleted_count = 0
    for root, dirs, files in os.walk(folder_path):
        for d in dirs:
            if d.lower() == "[previews]":
                dir_to_delete = os.path.join(root, d)
                try:
                    shutil.rmtree(dir_to_delete)
                    logging.info(f"Deleted preview folder: {dir_to_delete}")
                    deleted_count += 1
                except OSError as e:
                    logging.error(f"Error deleting folder {dir_to_delete}: {e}")
    return deleted_count


def batch_edit_programs(folder_path, params):
    """
    Batch rebuilds XPM files, converting legacy to advanced if specified,
    and applies all user tweaks passed in the params dictionary.
    """
    edited = 0
    if not IMPORTS_SUCCESSFUL:
        logging.error("Cannot run batch edit, required modules are missing.")
        return 0

    # The App instance is not available here, so we create a dummy one for the builder
    dummy_app = type("DummyApp", (), {"root": None})()

    options = InstrumentOptions(
        firmware_version=params.get("version"),
        format_version=params.get("format_version", "advanced"),
        creative_mode=params.get("creative_mode", "off"),
        creative_config=params.get("creative_config", {}),
    )
    builder = InstrumentBuilder(folder_path, dummy_app, options)

    mod_matrix_file = params.get("mod_matrix_file")
    matrix = load_mod_matrix(mod_matrix_file) if mod_matrix_file else None
    if matrix == {}:
        matrix = None

    for root_dir, _dirs, files in os.walk(folder_path):
        for file in files:
            if not file.lower().endswith(".xpm") or file.startswith("._"):
                continue

            path = os.path.join(root_dir, file)
            logging.info(f"Rebuilding program: {file}")

            try:
                # 1. Parse the existing file to get its core data
                mappings, existing_params = _parse_xpm_for_rebuild(path)
                if not mappings:
                    logging.warning(f"Could not parse mappings from {file}. Skipping.")
                    continue

                # 2. Determine the program name
                program_name = (
                    os.path.splitext(file)[0]
                    if params.get("rename")
                    else existing_params.get("ProgramName", os.path.splitext(file)[0])
                )

                # 3. Create the template for the new instrument, starting with existing params
                instrument_template = existing_params.copy()

                # 4. Override template with user-specified tweaks from the params dict
                param_map = {
                    "attack": "VolumeAttack",
                    "decay": "VolumeDecay",
                    "sustain": "VolumeSustain",
                    "release": "VolumeRelease",
                    "filter_attack": "FilterAttack",
                    "filter_decay": "FilterDecay",
                    "filter_sustain": "FilterSustain",
                    "filter_release": "FilterRelease",
                    "filter_env_amount": "FilterEnvAmount",
                    "velocity_to_level": "VelocityToLevel",
                    "velocity_to_attack": "VelocityToAttack",
                    "velocity_to_start": "VelocityToStart",
                    "lfo1_rate": "Lfo1Rate",
                    "lfo1_shape": "Lfo1Shape",
                }
                for key, value in params.items():
                    if key in param_map:
                        instrument_template[param_map[key]] = str(value)

                # 5. Create a backup and then rebuild the file from scratch
                bak_path = path + ".bak"
                if not os.path.exists(bak_path):
                    shutil.copy2(path, bak_path)

                success = builder._create_xpm(
                    program_name=program_name,
                    sample_files=[],  # Pass empty list as we are using mappings
                    output_folder=root_dir,
                    mode="multi-sample",  # This mode is best for handling mappings
                    mappings=mappings,
                    instrument_template=instrument_template,
                )

                if success:
                    # Post-rebuild modifications if needed (Mod Matrix, etc.)
                    tree = ET.parse(path)
                    root = tree.getroot()
                    post_change = False
                    if matrix and apply_mod_matrix(root, matrix):
                        post_change = True
                    if params.get("fix_notes") and fix_sample_notes(
                        root, os.path.dirname(path)
                    ):
                        post_change = True
                    if fix_master_transpose(root, os.path.dirname(path)):
                        post_change = True
                    if "keytrack" in params and set_layer_keytrack(
                        root, params["keytrack"]
                    ):
                        post_change = True

                    if post_change:
                        indent_tree(tree)
                        tree.write(path, encoding="utf-8", xml_declaration=True)

                    edited += 1
                else:
                    logging.error(
                        f"Failed to rebuild {file}. Original restored from .bak if possible."
                    )
                    if os.path.exists(bak_path):
                        shutil.move(bak_path, path)  # Restore on failure

            except Exception as exc:
                logging.error(
                    f"Failed to process and rebuild {path}: {exc}\n{traceback.format_exc()}"
                )

    return edited


def main():
    if sys.platform == "darwin" and sys.version_info[:2] >= (3, 13):
        print(
            "WARNING: Python 3.13 on macOS has known Tkinter issues that can "
            "cause crashes. Run this script with Python 3.12 or earlier for "
            "best results.",
            file=sys.stderr,
        )

    if sys.platform == "linux" and "DISPLAY" not in os.environ:
        try:
            subprocess.run(
                ["which", "Xvfb"], check=True, capture_output=True, text=True
            )
            subprocess.Popen(["Xvfb", ":99", "-screen", "0", "1280x720x16"])
            os.environ["DISPLAY"] = ":99"
        except (FileNotFoundError, subprocess.CalledProcessError):
            print(
                "ERROR: This application requires a graphical display. Please install Xvfb.",
                file=sys.stderr,
            )
            sys.exit(1)

    try:
        app = App()
        app.mainloop()
    except Exception as e:
        logging.basicConfig(filename="fatal_error.log", level=logging.ERROR)
        logging.error(
            f"A fatal, unhandled error occurred: {e}\n{traceback.format_exc()}"
        )
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "Fatal Error",
                f"An unrecoverable error occurred and the application must close.\n\nDetails have been saved to fatal_error.log.",
            )
        except:
            pass


if __name__ == "__main__":
    main()
