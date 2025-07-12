# Utility functions for XPM parsing and key range calculation
import os
import logging
import json
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape as xml_escape, unescape as xml_unescape

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
    """Calculate low/high note ranges based on root notes."""
    if not mappings:
        return []

    sorted_maps = sorted(mappings, key=lambda m: m.get("root_note", 60))
    for i, current in enumerate(sorted_maps):
        if i == 0:
            current["low_note"] = 0
        else:
            prev = sorted_maps[i - 1]
            midpoint = (prev["root_note"] + current["root_note"]) // 2
            current["low_note"] = midpoint + 1

        if i == len(sorted_maps) - 1:
            current["high_note"] = 127
        else:
            nxt = sorted_maps[i + 1]
            midpoint = (current["root_note"] + nxt["root_note"]) // 2
            current["high_note"] = midpoint

    return sorted_maps


def _parse_xpm_for_rebuild(xpm_path):
    """Return sample mappings and base parameters parsed from ``xpm_path``."""
    mappings = []
    instrument_params = {}
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
                        abs_path = os.path.normpath(os.path.join(xpm_dir, sample_path))
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

                abs_path = os.path.normpath(os.path.join(xpm_dir, sample_rel))

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
