# TRANSLATOR ROOT NOTE ISSUE ANALYSIS

## Pattern Detected in Keys-SI Magnetic Keys.xpm:

| Sample Name | Expected MIDI | Current MIDI | Offset |
|-------------|---------------|--------------|--------|
| C1          | 24            | 37           | +13    |
| G1          | 31            | 44           | +13    |
| D2          | 38            | 51           | +13    |
| A2          | 45            | 58           | +13    |
| E3          | 52            | 65           | +13    |
| B3          | 59            | 72           | +13    |
| F#4         | 66            | 79           | +13    |

## TRANSLATOR BUG IDENTIFIED:
- **Consistent +13 semitone offset** (1 octave + 1 semitone)
- This causes samples to play an octave and a semitone too high
- Explains why user needs global transpose to make C2 play as C2

## SOLUTION:
1. Detect this consistent +13 offset pattern
2. Automatically subtract 13 from all root notes when pattern is detected
3. Fix individual LowNote/HighNote ranges after root note correction
4. Preserve the overall keygroup structure while fixing mapping

## IMPLEMENTATION:
- Enhanced `_fix_single_root_note_mapping()` function
- Detect consistent offset patterns across multiple instruments
- Apply batch correction when pattern is confirmed
- Create backup before applying fixes

This will eliminate the need for manual global transpose workarounds!
