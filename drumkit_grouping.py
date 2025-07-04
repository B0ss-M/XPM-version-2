import os
import glob
import re
from collections import defaultdict


def extract_group_name(filename: str) -> str:
    """Return a simplified group name based on underscores, spaces and digits."""
    base = os.path.splitext(os.path.basename(filename))[0]
    base = re.sub(r'([A-G][#b]?[-_]?\d+)$', '', base, flags=re.IGNORECASE)
    base = re.sub(r'\d+$', '', base)
    parts = re.split(r'[ _-]+', base)
    return parts[0].lower() if parts else base.lower()


def group_similar_files(folder: str) -> dict:
    """Group WAV files in a folder by similar names."""
    groups = defaultdict(list)
    for wav in glob.glob(os.path.join(folder, '*.wav')):
        name = extract_group_name(wav)
        groups[name].append(os.path.relpath(wav, folder))
    for files in groups.values():
        files.sort()
    return groups

