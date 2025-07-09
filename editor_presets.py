import json
import logging
import os

PRESET_FILE = os.path.join(os.path.dirname(__file__), 'editor_presets.json')


def load_presets() -> dict:
    """Load editor presets from JSON file."""
    try:
        with open(PRESET_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception as exc:
        logging.warning("Could not load presets: %s", exc)
    return {}
