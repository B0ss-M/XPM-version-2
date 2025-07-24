# Victory Brass XMP Structure Analysis

## 📋 **Complete Structure Breakdown**

### **Header (Correct Format)**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<MPCVObject>
  <Version>
    <File_Version>2.1</File_Version>
    <Application>MPC-V</Application>
    <Application_Version>3.5.0.54</Application_Version>
    <Platform>Linux</Platform>
  </Version>
```

### **Program Declaration**
```xml
<Program type="Keygroup">
    <ProgramName>Victory Brass</ProgramName>
    <ProgramPads-v2.10>{
    "ProgramPads-v2.10": {...}
}</ProgramPads-v2.10>
```

### **Audio Configuration**
```xml
<CueBusEnable>False</CueBusEnable>
<AudioRoute>
  <AudioRoute>2</AudioRoute>
  <AudioRouteSubIndex>0</AudioRouteSubIndex>
  <AudioRouteChannelBitmap>3</AudioRouteChannelBitmap>
  <InsertsEnabled>True</InsertsEnabled>
</AudioRoute>
<Send1>0.000000</Send1>
<Send2>0.000000</Send2>
<Send3>0.000000</Send3>
<Send4>0.000000</Send4>
<Volume>0.707946</Volume>
<Mute>False</Mute>
<Solo>False</Solo>
<Pan>0.500000</Pan>
<AutomationFilter>1</AutomationFilter>
```

### **Core Program Parameters**
```xml
<Pitch>0.000000</Pitch>
<TuneCoarse>0</TuneCoarse>
<TuneFine>0</TuneFine>
<Mono>False</Mono>
<Program_Polyphony>0</Program_Polyphony>
<PortamentoTime>0.000000</PortamentoTime>
<PortamentoLegato>False</PortamentoLegato>
<PortamentoQuantized>False</PortamentoQuantized>
<Program.Xfader.Route>0</Program.Xfader.Route>
<MonoRetrigger>False</MonoRetrigger>
```

### **LFO Configuration (Critical)**
```xml
<FreeRunningLFO Num="0">
  <Type>Sine</Type>
  <Rate>0.500000</Rate>
  <Sync>0</Sync>
  <DelaySync>0</DelaySync>
  <FadeinSync>0</FadeinSync>
  <LfoDelay>0.000000</LfoDelay>
  <LfoLevel>1.000000</LfoLevel>
  <LfoFadein>0.000000</LfoFadein>
  <Reset>True</Reset>
</FreeRunningLFO>
<FreeRunningLFO Num="1">
  <Type>Sine</Type>
  <Rate>0.500000</Rate>
  <Sync>0</Sync>
  <DelaySync>0</DelaySync>
  <FadeinSync>0</FadeinSync>
  <LfoDelay>0.000000</LfoDelay>
  <LfoLevel>1.000000</LfoLevel>
  <LfoFadein>0.000000</LfoFadein>
  <Reset>True</Reset>
</FreeRunningLFO>
```

### **Instruments Section (CRITICAL)**
```xml
<Instruments>
  <!-- ONLY 21 instruments, NOT 128 -->
  <Instrument number="1"></Instrument>
  <Instrument number="2"></Instrument>
  <!-- ... up to 21 only ... -->
  <Instrument number="21"></Instrument>
</Instruments>
```

### **Pad Mapping**
```xml
<PadNoteMap>
  <!-- Only 22 pad notes, not 128 -->
  <PadNote number="1"></PadNote>
  <PadNote number="2"></PadNote>
  <!-- ... up to 22 ... -->
  <PadNote number="22"></PadNote>
</PadNoteMap>
```

### **Keygroup Parameters**
```xml
<KeygroupMasterTranspose>0.500000</KeygroupMasterTranspose>
<KeygroupNumKeygroups>21</KeygroupNumKeygroups>
<KeygroupPitchBendRange>0.000000</KeygroupPitchBendRange>
<KeygroupWheelToLfo>0.000000</KeygroupWheelToLfo>
<KeygroupAftertouchToFilter>0.000000</KeygroupAftertouchToFilter>
<KeygroupPressureToFilter>0.000000</KeygroupPressureToFilter>
<KeygroupPitchBendPositiveRange>2</KeygroupPitchBendPositiveRange>
<KeygroupPitchBendNegativeRange>2</KeygroupPitchBendNegativeRange>
<KeygroupLegacyMode>True</KeygroupLegacyMode>
<KeygroupWheelToLfo2>0.000000</KeygroupWheelToLfo2>
<KeygroupAftertouchToFilter2>0.000000</KeygroupAftertouchToFilter2>
<KeygroupNoteCountSize Id="0">2</KeygroupNoteCountSize>
<KeygroupNoteCountSize Id="1">2</KeygroupNoteCountSize>
<KeygroupTimbreShift>0</KeygroupTimbreShift>
```

### **Envelope Settings**
```xml
<AmpEnvGlobal>False</AmpEnvGlobal>
<FltEnvGlobal>False</FltEnvGlobal>
<PitchEnvGlobal>False</PitchEnvGlobal>
<AuxEnvGlobal>False</AuxEnvGlobal>
```

### **Advanced Processing**
```xml
<StackProcessorMode>0</StackProcessorMode>
<UnisonMode>0</UnisonMode>
<UnisonVoices>0</UnisonVoices>
<UnisonDetune>0.000000</UnisonDetune>
<UnisonSpread>0.000000</UnisonSpread>
<HarmoniserMix>0.500000</HarmoniserMix>
```

### **Harmoniser Configuration**
```xml
<HarmoniserNotes Num="0" Enabled="1" Shift="0" Detune="0.0" Pan="0.0" VelShift="1.0"
                 Volume="0.25" Delay="0.0" SyncDelay="0"/>
<HarmoniserNotes Num="1" Enabled="1" Shift="0" Detune="0.0" Pan="0.0" VelShift="1.0"
                 Volume="0.25" Delay="0.0" SyncDelay="0"/>
<HarmoniserNotes Num="2" Enabled="1" Shift="0" Detune="0.0" Pan="0.0" VelShift="1.0"
                 Volume="0.25" Delay="0.0" SyncDelay="0"/>
<HarmoniserNotes Num="3" Enabled="1" Shift="0" Detune="0.0" Pan="0.0" VelShift="1.0"
                 Volume="0.25" Delay="0.0" SyncDelay="0"/>
```

### **Modulation Links (32 total)**
```xml
<ModLink Num="0" Source="0" Target="0" Shaper="0" Min="0.0" Max="1.0" Bipolar="0"/>
<ModLink Num="1" Source="0" Target="0" Shaper="0" Min="0.0" Max="1.0" Bipolar="0"/>
<!-- ... continues to Num="31" ... -->
```

### **Closing**
```xml
<SynthSection>
</SynthSection>
</Program>
</MPCVObject>
```

## 🔍 **Key Differences from Legacy vs Advanced**

### **Legacy Mode Difference**
- **Victory Brass.xpm**: `<KeygroupLegacyMode>True</KeygroupLegacyMode>`
- **Victory Brass-Adv.xpm**: `<KeygroupLegacyMode>False</KeygroupLegacyMode>`

### **Critical Observations**

1. **NO 128-instrument bloat** - Only creates instruments that are actually used
2. **Modern format version 2.1** - Not legacy 1.0
3. **Complete parameter set** - All modern MPC parameters included
4. **Proper pad mapping** - Limited to actual used pads
5. **Advanced processing options** - Harmoniser, Unison, Stack processing
6. **32 modulation links** - Full modulation matrix

## 🚨 **CRITICAL FIXES NEEDED IN SCRIPT**

1. **Update to format version 2.1**
2. **Remove 128-instrument bloat completely**
3. **Add all missing modern parameters**
4. **Include proper LFO, harmoniser, and modulation setup**
5. **Set correct keygroup count and pad mapping**
