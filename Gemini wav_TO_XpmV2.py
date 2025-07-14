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
import zipfile
from typing import Optional

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
    MultiSampleBuilderWindow = None
from xpm_utils import (
    LAYER_PARAMS_TO_PRESERVE,
    calculate_key_ranges,
    _parse_xpm_for_rebuild,
    indent_tree,
)


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
    """
    try:
        with open(xpm_path, "r", encoding="utf-8") as f:
            xml_text = f.read()
        root = ET.fromstring(xml_text)

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


# --- REVISED: detect_sample_note with improved logging ---
def detect_sample_note(path: str) -> int:
    """
    Return the MIDI note for a sample using metadata, filename, or pitch analysis.
    Logs the successful detection method for better debugging.
    """
    filename = os.path.basename(path)

    # 1. Try reading from WAV 'smpl' chunk metadata
    midi = extract_root_note_from_wav(path)
    if midi is not None:
        logging.info(f"Note for '{filename}' found in WAV metadata: {midi}")
        return midi

    # 2. Try inferring from the filename
    midi = infer_note_from_filename(path)
    if midi is not None:
        logging.info(f"Note for '{filename}' inferred from filename: {midi}")
        return midi

    # 3. Fallback to audio analysis (Librosa)
    midi = detect_fundamental_pitch(path)
    if midi is not None:
        # The detect_fundamental_pitch function already logs its success
        return midi

    # 4. If all methods fail, use C4 as a default
    logging.warning(
        f"All detection methods failed for '{filename}'. Defaulting to C4 (60)."
    )
    return 60


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
        self.title("Expansion Doctor")
        self.geometry("700x450")
        self.resizable(True, True)
        self.master = master
        self.format_var = tk.StringVar(value="advanced")
        self.status = tk.StringVar(value="Ready.")
        self.version_var = tk.StringVar(value=master.firmware_version.get())
        self.format_var = tk.StringVar(value="advanced")
        self.broken_links = {}
        self.file_info = {}
        self.create_widgets()
        self.scan_broken_links()

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
            columns=("XPM", "Version", "Valid", "Missing Samples"),
            show="headings",
        )
        self.tree.heading("XPM", text="XPM File")
        self.tree.heading("Version", text="Version")
        self.tree.heading("Valid", text="Valid")
        self.tree.heading("Missing Samples", text="Missing Samples")
        self.tree.column("XPM", width=250)
        self.tree.column("Version", width=80, anchor="center")
        self.tree.column("Valid", width=60, anchor="center")
        self.tree.column("Missing Samples", width=320)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

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
        ttk.Button(
            btn_frame, text="Relink Samples...", command=self.relink_samples
        ).pack(side="left", padx=5)
        options = ttk.Frame(btn_frame)
        options.pack(side="left", padx=5)
        ttk.Label(options, text="Format:").pack(side="left")
        ttk.Combobox(
            options,
            textvariable=self.format_var,
            values=["legacy", "advanced"],
            state="readonly",
            width=9,
        ).pack(side="left")
        ttk.Button(btn_frame, text="Fix Keygroups", command=self.fix_keygroups).pack(
            side="left", padx=5
        )
        ttk.Button(btn_frame, text="Rewrite Versions", command=self.fix_versions).pack(
            side="left", padx=5
        )
        ttk.Button(btn_frame, text="Rescan", command=self.scan_broken_links).pack(
            side="left", padx=5
        )
        ttk.Button(btn_frame, text="Close", command=self.destroy).pack(
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

        for xpm_path in xpms:
            try:
                tree = ET.parse(xpm_path)
                root = tree.getroot()
            except Exception as e:
                rel = os.path.relpath(xpm_path, folder)
                logging.error(f"Error scanning {xpm_path}: {e}")
                self.tree.insert(
                    "",
                    "end",
                    values=(rel, "Unknown", "No", "Invalid XPM"),
                )
                self.file_info[xpm_path] = {
                    "version": "Unknown",
                    "valid": False,
                    "missing": [],
                }
                continue

            missing = set()
            for elem in root.findall(".//SampleFile"):
                if elem is not None and elem.text:
                    normalized_rel_path = elem.text.replace("/", os.sep)
                    sample_abs_path = os.path.normpath(
                        os.path.join(os.path.dirname(xpm_path), normalized_rel_path)
                    )
                    if not os.path.exists(sample_abs_path):
                        missing.add(os.path.basename(elem.text))

            missing_list = sorted(list(missing))
            version = get_xpm_version(xpm_path)
            valid = is_valid_xpm(xpm_path)
            self.tree.insert(
                "",
                "end",
                values=(
                    os.path.relpath(xpm_path, folder),
                    version,
                    "Yes" if valid else "No",
                    ", ".join(missing_list),
                ),
            )
            self.file_info[xpm_path] = {
                "version": version,
                "valid": valid,
                "missing": missing_list,
            }
            if missing_list:
                self.broken_links[xpm_path] = missing_list

        broken = len(self.broken_links)
        self.status.set(f"Scanned {total} XPM(s). {broken} with missing samples.")


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

                            parent_layer = root.find(
                                f".//Layer[SampleFile='{elem.text}']"
                            )
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
        if self.mode == "synth":
            self.config = {
                "resonance": self.resonance.get(),
                "release": self.release.get(),
            }
        elif self.mode == "lofi":
            self.config = {
                "cutoff": self.cutoff.get(),
                "pitch_wobble": self.pitch_wobble.get(),
            }

        self.master.creative_config[self.mode] = self.config
        logging.info(f"Updated creative config for '{self.mode}': {self.config}")
        self.destroy()


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
            filetypes=[("JSON Files", "*.json"), ("All Files", "*")],
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
        actions_frame = ttk.LabelFrame(main_frame, text="Batch Actions", padding="10")
        actions_frame.grid(row=2, column=0, sticky="ew", pady=5)
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
            text="Rebuild Selected",
            command=self.run_rebuild_thread,
            style="Accent.TButton",
        ).pack(side="left", padx=5)
        ttk.Button(
            actions_frame, text="Edit Samples...", command=self.open_sample_editor
        ).pack(side="left", padx=5)

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

        for i in self.tree.get_children():
            self.tree.delete(i)
        self.check_vars.clear()
        self.xpm_map.clear()

        xpm_files = glob.glob(os.path.join(folder, "**", "*.xpm"), recursive=True)
        for path in xpm_files:
            version = get_xpm_version(path)
            rel_path = os.path.relpath(path, folder)
            item_id = self.tree.insert(
                "", "end", values=("No", rel_path, version, "Ready")
            )
            self.check_vars[item_id] = tk.BooleanVar(value=False)
            self.xpm_map[item_id] = path

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
                instrument_groups = (
                    group_similar_files(self.folder_path) if IMPORTS_SUCCESSFUL else {}
                )
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
            keygroup_count = len(note_layers)

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
        """Groups WAV files by instrument name for XPM creation."""
        search_path = (
            os.path.join(self.folder_path, "**", "*.wav")
            if self.options.recursive_scan
            else os.path.join(self.folder_path, "*.wav")
        )
        all_wavs = glob.glob(search_path, recursive=self.options.recursive_scan)

        groups = defaultdict(list)
        for wav_path in all_wavs:
            if ".xpm.wav" in wav_path.lower():
                continue

            relative_path = os.path.relpath(wav_path, self.folder_path)

            if mode == "one-shot":
                instrument_name = os.path.splitext(os.path.basename(wav_path))[0]
                groups[instrument_name].append(relative_path)
            else:
                instrument_name = get_base_instrument_name(wav_path)
                groups[instrument_name].append(relative_path)
        return groups

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
        self.last_browse_path = os.path.expanduser("~")  # NEW: Remember last path

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
            text="Sample Mapping Editor...",
            command=self.open_sample_mapping_editor,
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
            frame,
            text="Package Expansion (.zip)",
            command=self.package_expansion,
            style="Accent.TButton",
        ).grid(row=1, column=2, columnspan=3, sticky="ew", padx=2, pady=2)

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
        folder = filedialog.askdirectory(
            parent=self.root,
            title="Select Sample Folder",
            initialdir=self.last_browse_path,
        )
        if folder:
            self.folder_path.set(folder)
            self.last_browse_path = folder
            logging.info(f"Selected folder: {folder}")

    def on_creative_mode_change(self, event=None):
        """Enable config button only for configurable modes."""
        configurable_modes = ["synth", "lofi"]
        if self.creative_mode_var.get() in configurable_modes:
            self.creative_config_btn.config(state="normal")
        else:
            self.creative_config_btn.config(state="disabled")

    # REVISED: Corrected window opening logic
    def open_window(self, window_class, *args):
        if window_class is None:
            messagebox.showerror(
                "Missing Dependency",
                f"This feature is unavailable. Missing module: {MISSING_MODULE}",
                parent=self.root,
            )
            return
        folder_independent_windows = [
            ExpansionBuilderWindow,
            BatchProgramFixerWindow,
            globals().get("SampleMappingEditorWindow"),
            CreativeModeConfigWindow,  # Added missing class here
        ]
        if window_class not in folder_independent_windows and (
            not self.folder_path.get() or not os.path.isdir(self.folder_path.get())
        ):
            messagebox.showerror(
                "Error", "Please select a valid source folder first.", parent=self.root
            )
            return
        try:
            for win in self.winfo_children():
                if isinstance(win, tk.Toplevel) and isinstance(win, window_class):
                    win.focus()
                    return
            # Simplified logic - no special cases needed now
            window_class(self, *args)
        except Exception as e:
            logging.error(
                f"Error opening {window_class.__name__}: {e}\n{traceback.format_exc()}"
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

    def open_sample_mapping_editor(self):
        if globals().get("SampleMappingEditorWindow") is None:
            messagebox.showerror(
                "Missing Dependency",
                f"Sample Mapping Editor is unavailable. Missing module: {MISSING_MODULE}",
                parent=self.root,
            )
            return
        path = filedialog.askopenfilename(
            parent=self.root,
            title="Select XPM Program",
            filetypes=[
                ("XPM Files", "*.xpm"),
                ("Backup XPM", "*.bak *.bak.xpm *.xpm.bak"),
            ],
            initialdir=self.last_browse_path,
        )
        if path:
            self.last_browse_path = os.path.dirname(path)
            self.open_window(globals().get("SampleMappingEditorWindow"), path)

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
