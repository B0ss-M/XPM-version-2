# Utility functions for XPM parsing and key range calculation
import os
import logging
import json
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape as xml_escape, unescape as xml_unescape


# Professional XPM Standards (based on ConvertWithMoss analysis):
# 1. Root notes should have +1 offset (MPC hardware convention)
# 2. Use File_Version 2.1 and Application_Version v2.11.6.6
# 3. Group samples by key ranges instead of single notes
# 4. Maximum 4 layers per keygroup (MPC hardware limit)
# 5. Use consecutive key ranges for better playability

def indent_tree(tree: ET.ElementTree, space: str = "  ") -> None:
    """Indent an ElementTree for pretty printing on all Python versions."""
    if hasattr(ET, "indent"):
        ET.indent(tree, space=space)
    else:
        def _indent(elem: ET.Element, level: int = 0) -> None:
            i = "\n" + level * space
            if len(elem):
                if not elem.text or not elem.text.strip():
                    elem.text = i + space
                if not elem.tail or not elem.tail.strip():
                    elem.tail = i
                for child in elem:
                    _indent(child, level + 1)
                    if not child.tail or not child.tail.strip():
                        child.tail = i + space
                if not elem[-1].tail or not elem[-1].tail.strip():
                    elem.tail = i
            elif level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i

        _indent(tree.getroot())

    root = tree.getroot()
    if not (root.tail and root.tail.endswith("\n")):
        root.tail = "\n"

# Preserve these layer parameters when rebuilding
LAYER_PARAMS_TO_PRESERVE = [
    "VelStart",
    "VelEnd",
    "SampleStart",
    "SampleEnd",
    "Loop",
    "LoopStart",
    "LoopEnd",
    "Direction",
    "Offset",
    "Volume",
    "Pan",
    "Tune",
    "MuteGroup",
]


def calculate_key_ranges(mappings):
    """
    Enhanced key range calculation for whole instruments.
    Analyzes instrument type and applies appropriate range mapping.
    """
    if not mappings:
        return []

    sorted_maps = sorted(mappings, key=lambda m: m.get("root_note", 60))
    n = len(sorted_maps)
    
    if n == 1:
        # Single sample - full range
        sorted_maps[0]["low_note"] = 0
        sorted_maps[0]["high_note"] = 127
        return sorted_maps
    
    # Analyze the instrument type
    root_notes = [m.get("root_note", 60) for m in sorted_maps]
    note_range = max(root_notes) - min(root_notes)
    avg_interval = note_range / max(1, n - 1) if n > 1 else 12
    
    # Check filenames for instrument type hints
    all_filenames = " ".join([os.path.basename(m.get("sample_path", "")).lower() 
                             for m in sorted_maps])
    
    # Determine instrument type
    if any(keyword in all_filenames for keyword in ["kick", "snare", "hihat", "cymbal", "tom", "clap"]):
        instrument_type = "drum_kit"
    elif note_range <= 12 and avg_interval <= 2.0:
        instrument_type = "chromatic_scale"
    elif note_range <= 24 and avg_interval <= 4.0:
        instrument_type = "modal_scale"
    elif note_range > 36 or avg_interval > 8.0:
        instrument_type = "sparse_instrument"
    else:
        instrument_type = "balanced_instrument"
    
    # Apply appropriate range calculation
    if instrument_type == "drum_kit":
        # Drums map to individual notes
        for m in sorted_maps:
            root = m.get("root_note", 60)
            m["low_note"] = root
            m["high_note"] = root
    elif instrument_type == "chromatic_scale":
        # Tight ranges around each note
        for i, m in enumerate(sorted_maps):
            root = m.get("root_note", 60)
            if i == 0:
                low = max(0, root - 1)
            else:
                prev_root = sorted_maps[i - 1].get("root_note", 60)
                low = max(0, (prev_root + root) // 2)
            
            if i == n - 1:
                high = min(127, root + 6)
            else:
                next_root = sorted_maps[i + 1].get("root_note", 60)
                high = min(127, (root + next_root) // 2)
            
            if high <= low:
                high = min(127, low + 1)
            
            m["low_note"] = low
            m["high_note"] = high
    elif instrument_type == "sparse_instrument":
        # Wide ranges for sparse sampling
        for i, m in enumerate(sorted_maps):
            root = m.get("root_note", 60)
            if i == 0:
                low = 0
            else:
                prev_root = sorted_maps[i - 1].get("root_note", 60)
                gap = root - prev_root
                low = max(0, prev_root + gap // 3)
            
            if i == n - 1:
                high = 127
            else:
                next_root = sorted_maps[i + 1].get("root_note", 60)
                gap = next_root - root
                high = min(127, root + (gap * 2) // 3)
            
            if high - low < 6:
                high = min(127, low + 12)
            
            m["low_note"] = low
            m["high_note"] = high
    else:
        # Balanced/modal approach
        for i, m in enumerate(sorted_maps):
            root = m.get("root_note", 60)
            if i == 0:
                low = 0
            else:
                prev_root = sorted_maps[i - 1].get("root_note", 60)
                low = (prev_root + root) // 2 + 1
            
            if i == n - 1:
                high = 127
            else:
                next_root = sorted_maps[i + 1].get("root_note", 60)
                high = (root + next_root) // 2
            
            if high - low < 2:
                high = min(127, low + 3)
            
            m["low_note"] = low
            m["high_note"] = high

    return sorted_maps


def _parse_xpm_for_rebuild(xpm_path):
    """Return sample mappings and base parameters parsed from ``xpm_path``."""
    mappings = []
    instrument_params = {}
    xpm_path = os.path.abspath(xpm_path)
    xpm_dir = os.path.dirname(xpm_path)

    try:
        tree = ET.parse(xpm_path)
        root = tree.getroot()
    except ET.ParseError as e:
        logging.error(f"Could not parse XPM for rebuild: {xpm_path}. Error: {e}")
        return None, None

    program_name_elem = root.find(".//ProgramName")
    if program_name_elem is not None:
        instrument_params["ProgramName"] = program_name_elem.text

    num_elem = root.find(".//KeygroupNumKeygroups")
    if num_elem is not None and num_elem.text:
        try:
            instrument_params["KeygroupNumKeygroups"] = int(num_elem.text)
        except ValueError:
            logging.warning(
                f"Invalid KeygroupNumKeygroups value in {os.path.basename(xpm_path)}: {num_elem.text}"
            )

    inst = root.find(".//Instrument")
    if inst is not None:
        for child in inst:
            if len(list(child)) == 0 and child.text is not None:
                instrument_params[child.tag] = child.text

    # --- Modern format -----------------------------------------------------

    pads_elem = root.find(".//ProgramPads-v2.10")
    if pads_elem is None:
        pads_elem = root.find(".//ProgramPads")

    if pads_elem is not None and pads_elem.text:
        try:
            data = json.loads(xml_unescape(pads_elem.text))
            pads = data.get("pads", {})
            for pad_data in pads.values():
                if isinstance(pad_data, dict) and pad_data.get("samplePath"):
                    sample_path = pad_data["samplePath"]
                    if sample_path and sample_path.strip():
                        abs_path = os.path.abspath(os.path.join(xpm_dir, sample_path))
                        mappings.append(
                            {
                                "sample_path": abs_path,
                                "root_note": pad_data.get("rootNote", 60),
                                "low_note": pad_data.get("lowNote", 0),
                                "high_note": pad_data.get("highNote", 127),
                                "velocity_low": pad_data.get("velocityLow", 0),
                                "velocity_high": pad_data.get("velocityHigh", 127),
                                "layer_params": {},
                            }
                        )
            if mappings:
                logging.info(
                    f"Parsed {len(mappings)} sample mappings from ProgramPads in {os.path.basename(xpm_path)}"
                )
                return mappings, instrument_params
        except json.JSONDecodeError:
            pass

    # --- Legacy format ----------------------------------------------------
    logging.info(
        f"Parsing legacy Instrument/Layer structure for {os.path.basename(xpm_path)}."
    )
    auto_range_maps = []
    for inst_elem in root.findall(".//Instrument"):
        try:
            low_note_elem = inst_elem.find("LowNote")
            high_note_elem = inst_elem.find("HighNote")
            inst_low = (
                int(low_note_elem.text)
                if low_note_elem is not None and low_note_elem.text
                else None
            )
            inst_high = (
                int(high_note_elem.text)
                if high_note_elem is not None and high_note_elem.text
                else None
            )
            range_missing = inst_low is None or inst_high is None

            for layer in inst_elem.findall(".//Layer"):
                sample_file_elem = layer.find("SampleFile")
                sample_name_elem = layer.find("SampleName")
                root_note_elem = layer.find("RootNote")

                sample_rel = None
                if sample_file_elem is not None and sample_file_elem.text:
                    sample_rel = sample_file_elem.text.strip()
                elif sample_name_elem is not None and sample_name_elem.text:
                    val = sample_name_elem.text.strip()
                    if val:
                        sample_rel = val + ".wav"

                if not sample_rel:
                    continue

                abs_path = os.path.abspath(os.path.join(xpm_dir, sample_rel))

                layer_params = {}
                for param_name in LAYER_PARAMS_TO_PRESERVE:
                    elem = layer.find(param_name)
                    if elem is not None and elem.text is not None:
                        layer_params[param_name] = elem.text

                if root_note_elem is not None and root_note_elem.text:
                    try:
                        root_val = int(root_note_elem.text.strip())
                    except ValueError:
                        root_val = 60
                else:
                    root_val = 60
                mapping = {
                    "sample_path": abs_path,
                    "root_note": root_val,
                    "low_note": inst_low if inst_low is not None else root_val,
                    "high_note": inst_high if inst_high is not None else root_val,
                    "velocity_low": int(layer_params.get("VelStart", 0)),
                    "velocity_high": int(layer_params.get("VelEnd", 127)),
                    "layer_params": layer_params,
                }
                mappings.append(mapping)
                if range_missing:
                    auto_range_maps.append(mapping)
        except (AttributeError, ValueError, TypeError) as e:
            logging.warning(
                f"Skipping malformed Instrument element in {os.path.basename(xpm_path)}: {e}"
            )
            continue

    if auto_range_maps:
        calculate_key_ranges(auto_range_maps)

    if not mappings:
        logging.warning(
            f"No valid sample mappings could be parsed from {os.path.basename(xpm_path)}"
        )
        return None, None

    logging.info(
        f"Successfully parsed {len(mappings)} samples from {os.path.basename(xpm_path)}"
    )
    return mappings, instrument_params
