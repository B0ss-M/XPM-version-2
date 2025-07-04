"""Firmware-specific settings for XPM generation."""

PAD_SETTINGS = {
    '2.3.0.0': {'type': 1, 'universal_pad': 32512, 'engine': 'legacy'},
    '2.6.0.17': {'type': 1, 'universal_pad': 32512, 'engine': 'legacy'},
    '3.4.0': {'type': 4, 'universal_pad': 6238976, 'engine': 'advanced'},
    '3.5.0': {'type': 4, 'universal_pad': 6238976, 'engine': 'advanced'},
}

DEFAULT_PROGRAM_PARAMS = {
    'PortamentoTime': '0.0',
    'PortamentoLegato': 'False',
    'PortamentoQuantized': 'False',
    'MonoRetrigger': 'False',
    'GlobalDriftSpeed': '0.0',
    'KeygroupMasterTranspose': '0.0',
    'KeygroupPitchBendRange': '2.0',
    'KeygroupWheelToLfo': '0.0',
    'KeygroupAftertouchToFilter': '0.0',
    'KeygroupPressureToFilter': '0.0',
    'KeygroupPitchBendPositiveRange': '2',
    'KeygroupPitchBendNegativeRange': '2',
    'KeygroupLegacyMode': 'False',
    'KeygroupWheelToLfo2': '0.0',
    'KeygroupAftertouchToFilter2': '0.0',
    'KeygroupTimbreShift': '0',
    'AmpEnvGlobal': 'False',
    'FltEnvGlobal': 'False',
    'PitchEnvGlobal': 'False',
    'AuxEnvGlobal': 'False',
    'StackProcessorMode': '0',
    'UnisonMode': '0',
    'UnisonVoices': '0',
    'UnisonDetune': '0.0',
    'UnisonSpread': '0.0',
    'HarmoniserMix': '0.5',
}

# Some older firmware do not support the newer LFO/aftertouch parameters.
LEGACY_REMOVE_KEYS = {
    '2.3.0.0': ['KeygroupWheelToLfo2', 'KeygroupAftertouchToFilter2'],
    '2.6.0.17': ['KeygroupWheelToLfo2', 'KeygroupAftertouchToFilter2'],
}

def get_pad_settings(firmware: str):
    """Return pad settings dict for a firmware version."""
    return PAD_SETTINGS.get(firmware, PAD_SETTINGS['3.5.0'])


def get_program_parameters(firmware: str, num_keygroups: int) -> dict:
    """Return program parameter dictionary customized per firmware."""
    params = DEFAULT_PROGRAM_PARAMS.copy()
    params['KeygroupNumKeygroups'] = str(num_keygroups)
    for key in LEGACY_REMOVE_KEYS.get(firmware, []):
        params.pop(key, None)
    return params
