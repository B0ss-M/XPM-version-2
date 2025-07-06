# Changelog: XPM Keygroup File Format Changes (Firmware 2.0 → 3.5)

## 🟦 Firmware 2.x – Stable Before 3.0

- **Initial XPM keygroup format**  
  - Structure based on `<MPCVObject>` XML with `<Program>` and `<ProgramPads-v2.10>` blocks.  
  - JSON inside `<ProgramPads-v2.10>` was simple arrays/dictionaries without XML escaping.  
  - Supported velocity-layer mapping (4 sample layers per keygroup) and basic pad/sample metadata.

- **Version 2.14 → 2.15**  
  - Introduction of new keygroup metadata fields to support stem separation features.  
  - `.xpm` included new flags in the JSON block such as sample assignment for vs. stems.  
  - However, JSON blocks remained unescaped, which was tolerated by MPC 2.x but technically invalid XML.

---

## 🟧 Firmware 3.0 – MPC 3 Architecture Introduction

- **Unified Track–Program model**  
  - XPM now had a `type="Keygroup"` attribute inside `<Program>`.  
  - `<ProgramPads-v2.10>` internal JSON added a `"type"` key to match new architecture.  
  - Included metadata for velocity layers, pad assignments, envelope settings, and pad modulation sources.

- **Update to support per-pad metadata**  
  - New key–velocity range data fields introduced.  
  - Pads in JSON gained fields like `"velocityMin"`, `"velocityMax"` and envelope triggers.  
  - Still lacked proper escaping of JSON strings—consistent with XML rules but not enforced in parser.

---

## 🟩 Firmware 3.4.x – Legacy vs. Advanced Keygroup Engines

- **Dual engine support in `.xpm`**  
  - In extracted `.xpm`, `"engine": "legacy"` or `"engine": "advanced"` flag appeared in JSON.  
  - `"legacy"` used older pad behavior; `"advanced"` enabled dual filters, per-voice envelopes.
  - `.xpm` also included envelope parameter objects (`"env": {...}`), LFO definitions, mod matrix routing.
  - **Critical issue**: still inserted raw JSON strings with quotes and ampersands–XML invalid but parser-tolerant.

- **New `"legacy"` toggle field in `.xpm` JSON**  
  - Allowed MPC to parse to legacy engine mode even when loaded on newer firmware.

---

## 🟨 Firmware 3.5 – Advanced Keygroup Synthesis Engine

- **Massive expansion of synthesis metadata**  
  `.xpm` files contain deeply structured JSON under `<ProgramPads-v2.10>`, covering:

  - **Filters**: dual (parallel/series), blending and cutoff/resonance values.  
  - **Envelopes**: multi-stage, per-voice filter/pitch/aux envelopes.  
  - **LFOs**: two per voice + two global; each with shape, rate, routing.  
  - **Mod Matrix**: up to 32 routing slots, with unipolar/bipolar switch.  
  - **Note Counters**: two counters, up to 64-step range.  
  - **Unison/harmonizer**, **portamento**, **timbreshift**, **per-voice drift LFOs**, etc.

- **Multiple new JSON metadata fields**:
  - `"modMatrix": [...]`, `"noteCounters": [...]`, `"filters": {...}`, `"lfos": {...}`, `"unison": {...}`, etc.

- **Key structural fix**: `.xpm` JSON MUST now be XML-escaped
  - Proof: Script-generated XPMs containing raw `"` and `&` in JSON fail validation.
  - Correct files escape strings: `&quot;`, `&amp;`, etc. :contentReference[oaicite:1]{index=1}
  - Without escaping, MPC can't parse `<ProgramPads-v2.10>` node content → invalid XPM.

- **Legacy-engine fallback**:
  - When loading older XPM, firmware sets `"engine": "legacy"` and parser still interprets correctly.
  - Advanced engine XPMs require fully escaped JSON to be loaded.

---

## ✅ Summary of XPM & Keygroup Format Evolution

| Version | Engine Type     | JSON Complexity                | XML Escaping Required? |
|:-------:|----------------|-------------------------------|:----------------------:|
| 2.x     | Legacy only     | Basic layers, sample & pad    | No (parser-tolerant)  |
| 3.0+    | Legacy + Basic Adv | Envelope & velocity metadata | No (parser-tolerant) |
| 3.4.x   | Legacy & Advanced | Dual filters, mod matrix    | No (parser-tolerant)  |
| 3.5     | Advanced by default | Full synth engine JSON     | **Yes – mandatory**    |

---

## 🚧 Developer Action – Script Update Required

- **Your script must XML-escape the JSON** embedded in `<ProgramPads-v2.10>`:
  - Use `xml.sax.saxutils.escape(json_string)` to replace `"`, `&`, `<`, `>` with safe equivalents.
  - Ensures `.xpm` remains valid XML and loads the advanced engine properly.

- **Ensure metadata completeness** for advanced engine:
  - Include all new fields: filters, LFOs, modMatrix, unison, noteCounters, envelopes, etc.
  - Maintain `"engine"` flag if compatible with legacy behavior.

- **Testing**:
  1. Generate XPM using updated script.
  2. Load on MPC/Force with firmware 3.5 → Program Edit should show advanced engine UI.
  3. Inspect resulting `.xpm`: raw JSON should be escaped.

---