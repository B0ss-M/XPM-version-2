"""Common ADSR presets for instrument categories."""

INSTRUMENT_ADSR_PRESETS = {
    'piano':   {'VolumeAttack': '0.01', 'VolumeDecay': '0.35', 'VolumeSustain': '0.8', 'VolumeRelease': '0.4'},
    'bell':    {'VolumeAttack': '0.01', 'VolumeDecay': '0.2',  'VolumeSustain': '0.5', 'VolumeRelease': '0.8'},
    'pad':     {'VolumeAttack': '0.5',  'VolumeDecay': '0.5',  'VolumeSustain': '0.8', 'VolumeRelease': '1.2'},
    'keys':    {'VolumeAttack': '0.03', 'VolumeDecay': '0.3',  'VolumeSustain': '0.7', 'VolumeRelease': '0.4'},
    'guitar':  {'VolumeAttack': '0.005','VolumeDecay': '0.4',  'VolumeSustain': '0.6', 'VolumeRelease': '0.4'},
    'bass':    {'VolumeAttack': '0.01', 'VolumeDecay': '0.1',  'VolumeSustain': '0.95','VolumeRelease': '0.1'},
    'lead':    {'VolumeAttack': '0.02', 'VolumeDecay': '0.3',  'VolumeSustain': '0.8', 'VolumeRelease': '0.3'},
    'pluck':   {'VolumeAttack': '0.005','VolumeDecay': '0.2',  'VolumeSustain': '0.6', 'VolumeRelease': '0.25'},
    'drum':    {'VolumeAttack': '0',    'VolumeDecay': '0.1',  'VolumeSustain': '0.8', 'VolumeRelease': '0.05'},
    'fx':      {'VolumeAttack': '0.05', 'VolumeDecay': '0.5',  'VolumeSustain': '0.6', 'VolumeRelease': '0.6'},
    'vocal':   {'VolumeAttack': '0.01', 'VolumeDecay': '0.2',  'VolumeSustain': '0.9', 'VolumeRelease': '0.4'},
    'ambient': {'VolumeAttack': '0.3',  'VolumeDecay': '0.6',  'VolumeSustain': '0.9', 'VolumeRelease': '1.2'},
    'brass':   {'VolumeAttack': '0.05', 'VolumeDecay': '0.2',  'VolumeSustain': '0.8', 'VolumeRelease': '0.5'},
    'strings': {'VolumeAttack': '0.1',  'VolumeDecay': '0.3',  'VolumeSustain': '0.7', 'VolumeRelease': '0.9'},
    'woodwind':{'VolumeAttack': '0.05', 'VolumeDecay': '0.3',  'VolumeSustain': '0.9', 'VolumeRelease': '0.8'},
    'world':   {'VolumeAttack': '0.02', 'VolumeDecay': '0.3',  'VolumeSustain': '0.8', 'VolumeRelease': '0.4'},
    'horn':    {'VolumeAttack': '0.03', 'VolumeDecay': '0.25', 'VolumeSustain': '0.85','VolumeRelease': '0.4'},
}


def get_adsr_preset(name: str) -> dict:
    """Return ADSR settings for an instrument name if available."""
    lower = name.lower()
    for tag, params in INSTRUMENT_ADSR_PRESETS.items():
        if tag in lower:
            return params.copy()
    return {}
