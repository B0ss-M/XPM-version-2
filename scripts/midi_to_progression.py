#!/usr/bin/env python3
"""MIDI -> MPC .progression / .pattern converter

Features:
- Parse one or more MIDI files and extract chord events.
- If given a folder, detect multiple MIDI files; when files contain a single chord each, join them in filename order into one progression.
- Export to .progression (JSON) compatible with MPC format and a best-effort .pattern JSON export.

Notes:
- Uses `mido` when available. If not installed, the module will raise a clear ImportError with instructions.
- .progression format is now JSON matching MPC standards with progression wrapper, chord names, roles, and metadata.
- .pattern JSON is a best-effort format. If you need a specific MPC .pattern binary/XML format, provide an example and I'll adapt the writer accordingly.
"""
import os
import json
import traceback
from typing import List, Dict, Optional, TYPE_CHECKING

try:
    # Allow static type checkers to see mido types while avoiding hard import errors at analysis time.
    # At runtime, attempt to import mido; if it's not installed, fall back to None and mark as unavailable.
    import importlib
    if TYPE_CHECKING:
        import mido  # type: ignore
        MIDO_AVAILABLE = True
    else:
        mido = importlib.import_module('mido')
        MIDO_AVAILABLE = True
except Exception:
    mido = None
    MIDO_AVAILABLE = False

# Reuse the progression writer from ripchord GUI if available
try:
    from scripts.ripchord_to_progression_gui import write_progression
    WRITE_PROGRESSION_AVAILABLE = True
except Exception:
    # Fallback: we'll implement a simple XML writer when needed
    WRITE_PROGRESSION_AVAILABLE = False


def detect_chord_name(notes: List[int], root: int) -> str:
    """Detect chord name from MIDI notes and root.
    Returns chord symbol like 'Cm', 'F7', 'Bb', etc.
    """
    if not notes or root is None:
        return ""
    
    # Note names for display
    note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    
    # Get root note name
    root_name = note_names[root % 12]
    
    # Calculate intervals from root
    intervals = set()
    for note in notes:
        interval = (note - root) % 12
        if interval != 0:  # Skip root
            intervals.add(interval)
    
    # Detect chord types based on intervals
    if not intervals:
        return root_name  # Just root note
    elif intervals == {4, 7}:
        return root_name  # Major triad
    elif intervals == {3, 7}:
        return root_name + 'm'  # Minor triad
    elif intervals == {4, 7, 10}:
        return root_name + '7'  # Dominant 7th
    elif intervals == {4, 7, 11}:
        return root_name + 'maj7'  # Major 7th
    elif intervals == {3, 7, 10}:
        return root_name + 'm7'  # Minor 7th
    elif intervals == {3, 6, 10}:
        return root_name + 'm7b5'  # Half-diminished
    elif intervals == {3, 6}:
        return root_name + 'dim'  # Diminished
    elif intervals == {4, 8}:
        return root_name + 'aug'  # Augmented
    elif intervals == {5, 7}:
        return root_name + 'sus4'  # Suspended 4th
    elif intervals == {2, 7}:
        return root_name + 'sus2'  # Suspended 2nd
    elif 4 in intervals and 7 in intervals:
        # Major-based extended chords
        if 9 in intervals:
            return root_name + 'add9'
        elif 2 in intervals:
            return root_name + 'add2'
        return root_name
    elif 3 in intervals and 7 in intervals:
        # Minor-based extended chords
        if 9 in intervals:
            return root_name + 'm(add9)'
        elif 2 in intervals:
            return root_name + 'm(add2)'
        return root_name + 'm'
    else:
        # Complex or unrecognized chord
        return root_name + f'({len(notes)})'


def parse_midi_file(path: str, time_window: float = 0.06) -> List[Dict]:
    """Parse the MIDI file and return a list of chord dicts: {'root': int|None, 'name': str, 'notes': '60;64;67'}.

    time_window: seconds within which simultaneous note-ons are grouped into the same chord.
    """
    if not MIDO_AVAILABLE:
        raise ImportError("mido is required to parse MIDI files. Install with: pip install mido python-rtmidi")

    try:
        mid = mido.MidiFile(path)
    except Exception as e:
        raise RuntimeError(f'Could not read MIDI file {path}: {e}')

    # Build list of (time_seconds, note) note_on events (note on with velocity>0)
    events = []
    tempo = 500000  # default microseconds per beat
    ticks_per_beat = getattr(mid, 'ticks_per_beat', 480) or 480

    # Merge tracks to get proper chronological ordering and tempo events
    try:
        merged = mido.merge_tracks(mid.tracks)
    except Exception:
        # fallback: iterate tracks individually (less accurate)
        merged = None

    if merged is not None:
        t = 0
        for msg in merged:
            t += getattr(msg, 'time', 0)
            if getattr(msg, 'type', None) == 'set_tempo':
                tempo = msg.tempo
            if getattr(msg, 'type', None) == 'note_on' and getattr(msg, 'velocity', 0) > 0:
                seconds = mido.tick2second(t, ticks_per_beat, tempo)
                events.append((seconds, msg.note))
    else:
        # less accurate: scan each track and collect events with per-track ticks
        for track in mid.tracks:
            t = 0
            local_tempo = tempo
            for msg in track:
                t += getattr(msg, 'time', 0)
                if getattr(msg, 'type', None) == 'set_tempo':
                    local_tempo = msg.tempo
                if getattr(msg, 'type', None) == 'note_on' and getattr(msg, 'velocity', 0) > 0:
                    seconds = mido.tick2second(t, ticks_per_beat, local_tempo)
                    events.append((seconds, msg.note))

    if not events:
        return []

    # Sort events by time
    events.sort(key=lambda x: x[0])

    # Group events into chords by time_window
    chords = []
    bucket = [events[0][1]]
    bucket_time = events[0][0]

    for ev_time, note in events[1:]:
        if ev_time - bucket_time <= time_window:
            bucket.append(note)
        else:
            notes_sorted = sorted(set(bucket))
            root = min(notes_sorted) if notes_sorted else None
            chord_name = detect_chord_name(notes_sorted, root) if root is not None else ""
            chords.append({'root': root, 'name': chord_name, 'notes': ';'.join(str(n) for n in notes_sorted)})
            bucket = [note]
            bucket_time = ev_time

    # flush last bucket
    if bucket:
        notes_sorted = sorted(set(bucket))
        root = min(notes_sorted) if notes_sorted else None
        chord_name = detect_chord_name(notes_sorted, root) if root is not None else ""
        chords.append({'root': root, 'name': chord_name, 'notes': ';'.join(str(n) for n in notes_sorted)})

    return chords


def parse_midi_folder(folder: str, time_window: float = 0.06, recursive: bool = True) -> List[Dict]:
    """Parse multiple MIDI files in a folder. If each file has exactly one chord, join them in filename order.
    Otherwise concatenate chords from each file in filename order.
    
    Args:
        folder: Root folder to search
        time_window: Time window for grouping simultaneous notes
        recursive: If True, search subdirectories recursively
    """
    files = []
    
    if recursive:
        # Walk through all subdirectories
        for root_dir, _, filenames in os.walk(folder):
            for f in sorted(filenames):
                if f.lower().endswith(('.mid', '.midi')):
                    files.append(os.path.join(root_dir, f))
        files.sort()  # Sort full paths for consistent ordering
    else:
        # Only search the immediate folder
        files = [os.path.join(folder, f) for f in sorted(os.listdir(folder)) 
                 if f.lower().endswith(('.mid', '.midi'))]
    
    if not files:
        search_type = "folder and subdirectories" if recursive else "folder"
        raise FileNotFoundError(f'No MIDI files found in {search_type}')

    per_file_chords = []
    for f in files:
        try:
            chords = parse_midi_file(f, time_window=time_window)
        except Exception as e:
            raise RuntimeError(f"Failed parsing {f}: {e}")
        per_file_chords.append((f, chords))

    single_chord_files = all(len(chords) == 1 for _, chords in per_file_chords)

    if single_chord_files:
        # Join single chords into progression by filename order
        joined = []
        for f, chords in per_file_chords:
            joined.append(chords[0])
        return joined

    # Otherwise concatenate all chords in file order
    joined = []
    for f, chords in per_file_chords:
        joined.extend(chords)
    return joined


def batch_convert_midi_folder(folder: str, output_dir: str, output_format: str = 'progression', 
                              pattern_style: str = 'simple', preserve_structure: bool = True, 
                              max_depth: int = None, recursive: bool = True) -> tuple:
    """Convert all MIDI files in folder (and optionally subdirectories) to chosen format.
    
    Args:
        folder: Source folder containing MIDI files
        output_dir: Destination folder for converted files
        output_format: 'progression' or 'pattern'
        pattern_style: 'simple', 'mpcjson', or 'mpcpattern' (when format='pattern')
        preserve_structure: If True, preserve subdirectory structure; if False, flatten to root
        max_depth: Maximum directory depth to preserve (None = preserve all)
        recursive: If True, search subdirectories recursively
        
    Returns:
        (converted_files, errors) tuple
    """
    converted = []
    errors = []
    
    # Find all MIDI files
    midi_files = []
    if recursive:
        for root_dir, _, filenames in os.walk(folder):
            for f in filenames:
                if f.lower().endswith(('.mid', '.midi')):
                    full_path = os.path.join(root_dir, f)
                    rel_path = os.path.relpath(full_path, folder)
                    midi_files.append((full_path, rel_path))
    else:
        for f in os.listdir(folder):
            if f.lower().endswith(('.mid', '.midi')):
                full_path = os.path.join(folder, f)
                midi_files.append((full_path, f))
    
    if not midi_files:
        search_type = "folder and subdirectories" if recursive else "folder"
        raise FileNotFoundError(f'No MIDI files found in {search_type}')
    
    os.makedirs(output_dir, exist_ok=True)
    
    for full_path, rel_path in midi_files:
        try:
            # Parse the MIDI file
            chords = parse_midi_file(full_path)
            base = os.path.splitext(os.path.basename(full_path))[0]
            
            # Determine output path
            if preserve_structure:
                # Preserve directory structure (with optional depth limit)
                rel_dir = os.path.dirname(rel_path)
                if max_depth is not None and rel_dir:
                    # Limit directory depth
                    parts = rel_dir.split(os.sep)[:max_depth]
                    rel_dir = os.sep.join(parts)
                
                out_subdir = os.path.join(output_dir, rel_dir) if rel_dir else output_dir
                os.makedirs(out_subdir, exist_ok=True)
            else:
                # Flatten to root output directory
                out_subdir = output_dir
            
            # Choose extension and write file
            if output_format == 'progression':
                ext = '.progression'
                out_path = os.path.join(out_subdir, base + ext)
                if WRITE_PROGRESSION_AVAILABLE:
                    write_progression(chords, out_path)
                else:
                    # Fallback JSON writer matching MPC progression format
                    import json
                    from collections import Counter
                    
                    prog = {
                        'progression': {
                            'name': base,
                            'rootNote': None,
                            'scale': 'Chromatic', 
                            'recordingOctave': 1,
                            'chords': []
                        }
                    }
                    
                    # Infer root note and octave
                    notes = []
                    for cc in chords:
                        notes_str = cc.get('notes', '')
                        for tok in notes_str.split(';'):
                            if tok:
                                try:
                                    notes.append(int(tok))
                                except:
                                    pass
                    
                    if notes:
                        pcs = [n % 12 for n in notes]
                        counts = Counter(pcs)
                        root_pc, _ = counts.most_common(1)[0]
                        note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
                        prog['progression']['rootNote'] = note_names[root_pc]
                        
                        matching = [n for n in notes if n % 12 == root_pc]
                        if matching:
                            low = min(matching)
                            prog['progression']['recordingOctave'] = max(1, (low // 12) - 1)
                    
                    # Detect scale from progression
                    try:
                        from scripts.ripchord_to_progression_gui import detect_scale_from_chords
                        prog['progression']['scale'] = detect_scale_from_chords(chords)
                    except ImportError:
                        # Fallback to chromatic if scale detection unavailable
                        prog['progression']['scale'] = 'Chromatic'
                    
                    # Add chords
                    for i, c in enumerate(chords):
                        notes_list = [int(n) for n in c.get('notes', '').split(';') if n]
                        prog['progression']['chords'].append({
                            'name': c.get('name') or f'Chord{i+1}',
                            'role': 'Root' if i == 0 else 'Normal',
                            'notes': notes_list
                        })
                    
                    with open(out_path, 'w', encoding='utf-8') as f:
                        json.dump(prog, f, indent=4)
            else:
                # Pattern format
                if pattern_style == 'mpcpattern':
                    ext = '.mpcpattern'
                elif pattern_style == 'mpcjson':
                    ext = '.progression'
                else:
                    ext = '.pattern'
                
                out_path = os.path.join(out_subdir, base + ext)
                write_pattern_json(chords, out_path, name=base, style=pattern_style)
            
            converted.append((full_path, out_path))
            
        except Exception as e:
            errors.append((full_path, str(e)))
    
    return converted, errors


def write_pattern_json(chords: List[Dict], out_path: str, name: Optional[str] = None, style: str = 'simple'):
    """Write a .pattern JSON file.

    Styles:
    - 'simple' (default): {'pattern': {'name': ..., 'chords': [{'name':..., 'notes': [...], 'root': ...}, ...]}}
    - 'mpcjson': MPC progression format: {'progression': {...}} (like attached Superb 3 - This One.progression)
    - 'mpcpattern': MPC pattern format with timed events: {'pattern': {'length': ..., 'events': [...]}} (like attached A_-_i_i_iv_iv_v7_ii5_v_v7.mpcpattern)
    """
    if style not in ('simple', 'mpcjson', 'mpcpattern'):
        raise ValueError('Unknown pattern style. Use: simple, mpcjson, mpcpattern')

    if style == 'mpcpattern':
        # MPC pattern format with timed events (like A_-_i_i_iv_iv_v7_ii5_v_v7.mpcpattern)
        pattern = {
            'pattern': {
                'length': len(chords) * 3840,  # 3840 ticks per chord (quarter note at 960 ppq)
                'events': []
            }
        }
        
        for chord_idx, c in enumerate(chords):
            chord_time = chord_idx * 3840  # Start time for this chord
            notes_str = c.get('notes', '')
            
            for note in notes_str.split(';'):
                note = note.strip()
                if note.isdigit():
                    # Create an event for each note in MPC format
                    event = {
                        'type': 2,  # Note event type
                        'time': chord_time,
                        'len': 3840,  # Duration: quarter note
                        '1': int(note),  # MIDI note number
                        '2': 0.787402,  # Velocity (normalized 0-1, matching example)
                        '3': 0,  # Unknown parameter
                        'mod': 0,  # Modulation
                        'modVal': 0.5,  # Modulation value
                        'prob': 100,  # Probability
                        'ratchet': 1  # Ratchet setting
                    }
                    pattern['pattern']['events'].append(event)

        prog = pattern
    elif style == 'simple':
        prog = {
            'pattern': {
                'name': name or os.path.splitext(os.path.basename(out_path))[0],
                'chords': []
            }
        }
        for c in chords:
            prog['pattern']['chords'].append({
                'name': c.get('name') or '',
                'notes': [int(n) for n in c.get('notes', '').split(';') if n],
                'root': int(c['root']) if c.get('root') is not None else None,
            })
    else:
        # mpcjson style - MPC progression format (like Superb 3 - This One.progression)
        prog = {
            'progression': {
                'name': name or os.path.splitext(os.path.basename(out_path))[0],
                'rootNote': None,
                'scale': 'Chromatic',
                'recordingOctave': 0,
                'chords': []
            }
        }

        # Infer a sensible root note name + recording octave from the chords
        def infer_root_and_octave(chords_list: List[Dict]):
            # Collect all note numbers across chords
            notes = []
            for cc in chords_list:
                s = cc.get('notes') or ''
                for tok in s.split(';'):
                    if tok:
                        try:
                            notes.append(int(tok))
                        except Exception:
                            pass
            if not notes:
                return None, 0

            # Compute pitch class histogram
            from collections import Counter
            pcs = [n % 12 for n in notes]
            counts = Counter(pcs)
            # choose most common pitch class as root
            root_pc, _ = counts.most_common(1)[0]
            note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

            # Find lowest note matching that pitch class to infer recording octave
            matching = [n for n in notes if n % 12 == root_pc]
            if matching:
                low = min(matching)
                # MIDI note -> octave: C4==60 -> octave = (note // 12) - 1
                recording_octave = (low // 12) - 1
            else:
                recording_octave = 0

            return note_names[root_pc], recording_octave

        root_name, rec_oct = infer_root_and_octave(chords)
        if root_name:
            prog['progression']['rootNote'] = root_name
            prog['progression']['recordingOctave'] = rec_oct

        # Detect scale from chord progression
        try:
            from scripts.ripchord_to_progression_gui import detect_scale_from_chords
            prog['progression']['scale'] = detect_scale_from_chords(chords)
        except ImportError:
            # Fallback to chromatic if scale detection unavailable
            prog['progression']['scale'] = 'Chromatic'

        for i, c in enumerate(chords):
            notes_list = [int(n) for n in c.get('notes', '').split(';') if n]
            prog['progression']['chords'].append({
                'name': c.get('name') or f'Chord{i+1}',
                'role': 'Root' if i == 0 else 'Normal',
                'notes': notes_list
            })

    with open(out_path, 'w', encoding='utf-8') as fh:
        json.dump(prog, fh, indent=4)


def convert_path(in_path: str, out_dir: Optional[str] = None, out_format: str = 'progression') -> str:
    """Convert the given file or folder to the chosen format and return the output path.

    out_format: 'progression' or 'pattern'
    """
    if os.path.isdir(in_path):
        chords = parse_midi_folder(in_path)
        base = os.path.basename(os.path.normpath(in_path))
        out_name = base
    elif os.path.isfile(in_path):
        chords = parse_midi_file(in_path)
        base = os.path.splitext(os.path.basename(in_path))[0]
        out_name = base
    else:
        raise FileNotFoundError(in_path)

    out_dir = out_dir or os.path.dirname(in_path)
    os.makedirs(out_dir, exist_ok=True)

    if out_format == 'progression':
        out_path = os.path.join(out_dir, out_name + '.progression')
        if WRITE_PROGRESSION_AVAILABLE:
            write_progression(chords, out_path)
        else:
            # Local JSON writer in case ripchord module isn't importable
            import json
            from collections import Counter
            
            prog = {
                'progression': {
                    'name': out_name,
                    'rootNote': None,
                    'scale': 'Chromatic',
                    'recordingOctave': 1,
                    'chords': []
                }
            }
            
            # Infer root note and octave
            notes = []
            for cc in chords:
                notes_str = cc.get('notes', '')
                for tok in notes_str.split(';'):
                    if tok:
                        try:
                            notes.append(int(tok))
                        except:
                            pass
            
            if notes:
                pcs = [n % 12 for n in notes]
                counts = Counter(pcs)
                root_pc, _ = counts.most_common(1)[0]
                note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
                prog['progression']['rootNote'] = note_names[root_pc]
                
                matching = [n for n in notes if n % 12 == root_pc]
                if matching:
                    low = min(matching)
                    prog['progression']['recordingOctave'] = max(1, (low // 12) - 1)
            
            # Detect scale from progression
            try:
                from scripts.ripchord_to_progression_gui import detect_scale_from_chords
                prog['progression']['scale'] = detect_scale_from_chords(chords)
            except ImportError:
                # Fallback to chromatic if scale detection unavailable
                prog['progression']['scale'] = 'Chromatic'
            
            for i, c in enumerate(chords):
                notes_list = [int(n) for n in c.get('notes', '').split(';') if n]
                prog['progression']['chords'].append({
                    'name': c.get('name') or f'Chord{i+1}',
                    'role': 'Root' if i == 0 else 'Normal',
                    'notes': notes_list
                })
            
            with open(out_path, 'w', encoding='utf-8') as f:
                json.dump(prog, f, indent=4)
    elif out_format == 'pattern':
        out_path = os.path.join(out_dir, out_name + '.pattern')
        write_pattern_json(chords, out_path, name=out_name)
    else:
        raise ValueError('Unknown out_format')

    return out_path


def cli_main():
    import argparse

    p = argparse.ArgumentParser(description='Convert MIDI or folder of MIDIs to MPC .progression or .pattern')
    p.add_argument('input', help='MIDI file or folder containing MIDIs')
    p.add_argument('--out', '-o', help='Output folder (defaults to input folder)')
    p.add_argument('--format', '-f', choices=['progression', 'pattern'], default='progression')
    p.add_argument('--time-window', type=float, default=0.06, help='Grouping window in seconds for simultaneous notes')
    p.add_argument('--pattern-style', choices=['simple', 'mpcjson'], default='simple', help='When writing .pattern JSON, choose the style')
    args = p.parse_args()

    try:
        # pass pattern style through
        if args.format == 'pattern':
            out = convert_path(args.input, out_dir=args.out, out_format=args.format)
            # if pattern-style is mpcjson, re-write using that style
            if args.pattern_style != 'simple':
                # rewrite using chosen style
                from os.path import join, basename, splitext
                out_base = os.path.splitext(os.path.basename(out))[0]
                out_path = os.path.join(args.out or os.path.dirname(args.input), out_base + '.pattern')
                # read chords again
                if os.path.isdir(args.input):
                    chords = parse_midi_folder(args.input, time_window=args.time_window)
                else:
                    chords = parse_midi_file(args.input, time_window=args.time_window)
                write_pattern_json(chords, out_path, name=out_base, style=args.pattern_style)
                out = out_path
        else:
            out = convert_path(args.input, out_dir=args.out, out_format=args.format)
        print('Wrote:', out)
    except Exception as e:
        print('ERROR:', e)
        print(traceback.format_exc())


if __name__ == '__main__':
    cli_main()
