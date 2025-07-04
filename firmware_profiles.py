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

# Extract a full Instrument element from the reference XPM as a template. The
# template is stripped of layer data so that custom layers can be inserted.
def _load_advanced_instrument_template():
    import os
    import xml.etree.ElementTree as ET

    path = os.path.join(os.path.dirname(__file__), 'Advanced keygroup.xpm')
    if not os.path.exists(path):
        return None

    root = ET.parse(path).getroot()
    inst = root.find('.//Instrument')
    if inst is None:
        return None

    inst_copy = ET.fromstring(ET.tostring(inst))
    layers = inst_copy.find('Layers')
    if layers is not None:
        inst_copy.remove(layers)
    return inst_copy


ADVANCED_INSTRUMENT_TEMPLATE = _load_advanced_instrument_template()

def clone_advanced_instrument():
    """Return a deep copy of the advanced instrument template."""
    import xml.etree.ElementTree as ET

    if ADVANCED_INSTRUMENT_TEMPLATE is None:
        return None
    return ET.fromstring(ET.tostring(ADVANCED_INSTRUMENT_TEMPLATE))

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
    engine = PAD_SETTINGS.get(firmware, PAD_SETTINGS['3.5.0']).get('engine')
    if engine == 'advanced' and ADVANCED_PROGRAM_PARAMS:
        params = ADVANCED_PROGRAM_PARAMS.copy()
    else:
        params = DEFAULT_PROGRAM_PARAMS.copy()
    params['KeygroupNumKeygroups'] = str(num_keygroups)
    for key in LEGACY_REMOVE_KEYS.get(firmware, []):
        params.pop(key, None)
    return params
