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

# Automatically load advanced-engine defaults from the reference XPM.
def _load_advanced_params():
    """Parse 'Advanced keygroup.xpm' to build a dictionary of program-level
    parameters. Only simple text elements are captured so the resulting
    dictionary can be merged directly with DEFAULT_PROGRAM_PARAMS."""
    import os
    import xml.etree.ElementTree as ET

    path = os.path.join(os.path.dirname(__file__), 'Advanced keygroup.xpm')
    if not os.path.exists(path):
        return {}

    root = ET.parse(path).getroot()
    program = root.find('Program')
    advanced = {}
    if program is None:
        return advanced

    for child in program:
        if child.tag in {'ProgramName', 'ProgramPads-v2.10', 'Instruments', 'Version'}:
            continue
        if len(list(child)) == 0:
            advanced[child.tag] = child.text or ''
    return advanced


ADVANCED_PROGRAM_PARAMS = _load_advanced_params()

# Extract default instrument parameter values from the reference XPM. Only
# capture simple text elements so they can be merged directly with the
# dictionary used in InstrumentBuilder.
def _load_advanced_instrument_params():
    import os
    import xml.etree.ElementTree as ET

    path = os.path.join(os.path.dirname(__file__), 'Advanced keygroup.xpm')
    if not os.path.exists(path):
        return {}

    root = ET.parse(path).getroot()
    inst = root.find('.//Instrument')
    params = {}
    if inst is None:
        return params

    for child in inst:
        if len(list(child)) == 0:
            params[child.tag] = child.text or ''
    return params


ADVANCED_INSTRUMENT_PARAMS = _load_advanced_instrument_params()

# Some older firmware do not support the newer LFO/aftertouch parameters.
LEGACY_REMOVE_KEYS = {
    '2.3.0.0': ['KeygroupWheelToLfo2', 'KeygroupAftertouchToFilter2'],
    '2.6.0.17': ['KeygroupWheelToLfo2', 'KeygroupAftertouchToFilter2'],
}

def get_pad_settings(firmware: str, engine_override: str | None = None):
    """Return pad settings dict for a firmware version.

    The optional ``engine_override`` parameter allows callers to force
    the ``engine`` value regardless of the firmware's default. This is
    used when rebuilding programs where the user wants to explicitly
    choose between legacy (v2) and advanced (v3) formats.
    """
    settings = PAD_SETTINGS.get(firmware, PAD_SETTINGS['3.5.0']).copy()
    if engine_override in {'legacy', 'advanced'}:
        settings['engine'] = engine_override
    return settings


def get_program_parameters(firmware: str, num_keygroups: int) -> dict:
    """Return program parameter dictionary customized per firmware."""
    engine = PAD_SETTINGS.get(firmware, PAD_SETTINGS['3.5.0']).get('engine')
    if engine == 'advanced' and ADVANCED_PROGRAM_PARAMS:
        params = ADVANCED_PROGRAM_PARAMS.copy()
    else:
        params = DEFAULT_PROGRAM_PARAMS.copy()
    params['KeygroupNumKeygroups'] = str(num_keygroups)
    for key in LEGACY_REMOVE_KEYS.get(firmware, []):
        params.pop(key, None)
    return params
