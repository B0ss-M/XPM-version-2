import json
import logging
import xml.etree.ElementTree as ET
from typing import Optional, Dict


def _update_text(elem: Optional[ET.Element], value: Optional[str]) -> bool:
    if elem is None or value is None:
        return False
    if elem.text != value:
        elem.text = value
        return True
    return False


def set_layer_keytrack(root: ET.Element, keytrack: bool) -> bool:
    """Set KeyTrack value on all Layer elements."""
    changed = False
    val = "True" if keytrack else "False"
    for layer in root.findall('.//Layer'):
        changed |= _update_text(layer.find('KeyTrack'), val)
    return changed


def set_volume_adsr(root: ET.Element,
                     attack: Optional[float],
                     decay: Optional[float],
                     sustain: Optional[float],
                     release: Optional[float]) -> bool:
    """Update volume envelope ADSR on all instruments."""
    changed = False
    for inst in root.findall('.//Instrument'):
        changed |= _update_text(inst.find('VolumeAttack'),
                                str(attack) if attack is not None else None)
        changed |= _update_text(inst.find('VolumeDecay'),
                                str(decay) if decay is not None else None)
        changed |= _update_text(inst.find('VolumeSustain'),
                                str(sustain) if sustain is not None else None)
        changed |= _update_text(inst.find('VolumeRelease'),
                                str(release) if release is not None else None)
    return changed


def load_mod_matrix(path: str) -> Dict[int, Dict[str, str]]:
    """Load a mod matrix JSON file into a dictionary."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        logging.error("Could not load mod matrix '%s': %s", path, e)
        return {}

    matrix: Dict[int, Dict[str, str]] = {}
    if isinstance(data, list):
        for entry in data:
            num = entry.get('Num')
            if num is None:
                continue
            matrix[int(num)] = {k: str(v) for k, v in entry.items() if k != 'Num'}
    elif isinstance(data, dict):
        for num, params in data.items():
            matrix[int(num)] = {k: str(v) for k, v in params.items()}
    return matrix


def apply_mod_matrix(root: ET.Element, matrix: Dict[int, Dict[str, str]]) -> bool:
    """Apply mod matrix settings to existing ModLink elements."""
    changed = False
    for link in root.findall('.//ModLink'):
        try:
            num = int(link.get('Num', -1))
        except ValueError:
            continue
        params = matrix.get(num)
        if not params:
            continue
        for attr, val in params.items():
            if link.get(attr) != val:
                link.set(attr, val)
                changed = True
    return changed
