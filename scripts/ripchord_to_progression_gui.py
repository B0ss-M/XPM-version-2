#!/usr/bin/env python3
"""Ripchord (.rpc) -> .progression converter with a simple Tkinter GUI.

This module supports:
- Parsing .rpc files into chord lists
- Writing .progression JSON files (MPC format)
- Optional MIDI import (via scripts/midi_to_progression.py)
- GUI as a Toplevel so it can be embedded into the main app

The .progression format is now JSON-based matching MPC standards:
{
    "progression": {
        "name": "Progression Name",
        "rootNote": "C", 
        "scale": "Chromatic", 
        "recordingOctave": 1,
        "chords": [
            {"name": "Cm", "role": "Root", "notes": [48, 51, 55]},
            {"name": "F7", "role": "Normal", "notes": [53, 57, 60, 63]}
        ]
    }
}
"""
import os
import json
import tkinter as tk
from tkinter import messagebox, filedialog
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element, SubElement, ElementTree
import traceback
from typing import Optional, List, Dict

# Use safe file dialog helpers to avoid macOS Tk issues when available
try:
    from tk_file_utils import (
        askopenfilenames as safe_askopenfilenames,
        askopenfilename as safe_askopenfilename,
        askdirectory as safe_askdirectory,
    )
except Exception:
    safe_askopenfilenames = filedialog.askopenfilenames
    safe_askopenfilename = filedialog.askopenfilename
    safe_askdirectory = filedialog.askdirectory

# Optional drag & drop support using tkinterdnd2
try:
    from tkinterdnd2 import DND_FILES
    TkdndAvailable = True
except Exception:
    DND_FILES = None
    TkdndAvailable = False

# Optional MIDI converter helpers (midi_to_progression provides parsing/writing)
try:
    from scripts.midi_to_progression import (
        parse_midi_file,
        parse_midi_folder,
        write_pattern_json,
    )
    MIDI_AVAILABLE = True
except Exception:
    parse_midi_file = None
    parse_midi_folder = None
    write_pattern_json = None
    MIDI_AVAILABLE = False


def parse_rpc_file(rpc_path: str) -> List[Dict]:
    """Parse a Ripchord .rpc file and return a list of chord dicts.

    Each dict: {'root': int|None, 'name': str, 'notes': '60;64;67'}
    """
    try:
        tree = ET.parse(rpc_path)
        root = tree.getroot()
    except Exception as e:
        raise RuntimeError(f"Could not parse RPC file {rpc_path}: {e}")

    chords: List[Dict] = []

    # Common Ripchord structures
    for preset in root.findall('.//preset'):
        for input_elem in preset.findall('input'):
            note_attr = input_elem.get('note')
            try:
                root_note = int(note_attr) if note_attr is not None else None
            except Exception:
                root_note = None

            for chord_elem in input_elem.findall('chord'):
                name = chord_elem.get('name') or ''
                notes = chord_elem.get('notes') or ''
                chords.append({'root': root_note, 'name': name, 'notes': notes})

    # Fallback: any <chord> elements elsewhere
    for chord_elem in root.findall('.//chord'):
        name = chord_elem.get('name') or chord_elem.get('label') or ''
        notes = chord_elem.get('notes') or chord_elem.get('notesList') or ''
        root_attr = chord_elem.get('root') or chord_elem.get('input') or chord_elem.get('note')
        try:
            root_note = int(root_attr) if root_attr is not None else None
        except Exception:
            root_note = None
        entry = {'root': root_note, 'name': name, 'notes': notes}
        if entry not in chords and notes:
            chords.append(entry)

    # Last-resort: look for chord-like children under input elements
    if not chords:
        for input_elem in root.findall('.//input'):
            try:
                note_attr = input_elem.get('note')
                root_note = int(note_attr) if note_attr is not None else None
            except Exception:
                root_note = None
            for child in list(input_elem):
                if child.tag.lower().endswith('chord'):
                    name = child.get('name') or ''
                    notes = child.get('notes') or ''
                    chords.append({'root': root_note, 'name': name, 'notes': notes})

    return chords


# Settings persistence for remembering last folders
def _get_settings_file():
    """Get the path to the settings file."""
    home_dir = os.path.expanduser('~')
    settings_dir = os.path.join(home_dir, '.xpm_progression_builder')
    os.makedirs(settings_dir, exist_ok=True)
    return os.path.join(settings_dir, 'settings.json')


def _load_settings():
    """Load settings from file, return default dict if file doesn't exist."""
    try:
        with open(_get_settings_file(), 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            'last_input_folder': '',
            'last_output_folder': '',
            'last_midi_folder': '',
            'last_batch_folder': ''
        }


def _save_settings(settings):
    """Save settings to file."""
    try:
        with open(_get_settings_file(), 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2)
    except Exception:
        pass  # Silently fail if we can't save settings


def write_progression(chords: List[Dict], out_path: str):
    """Write chords to a properly formatted .progression JSON file (MPC format)."""
    import json
    import os
    from collections import Counter
    
    # Create progression structure matching Superb format
    prog = {
        'progression': {
            'name': os.path.splitext(os.path.basename(out_path))[0],
            'rootNote': None,
            'scale': 'Chromatic',  # Will be updated below
            'recordingOctave': 1,
            'chords': []
        }
    }

    # Infer root note and recording octave from chord data
    def infer_root_and_octave(chords_list: List[Dict]):
        notes = []
        for cc in chords_list:
            notes_str = cc.get('notes', '')
            if isinstance(notes_str, str):
                for tok in notes_str.split(';'):
                    if tok:
                        try:
                            notes.append(int(tok))
                        except Exception:
                            pass
            elif isinstance(notes_str, list):
                notes.extend(notes_str)
        
        if not notes:
            return None, 1

        # Find most common pitch class as root
        pcs = [n % 12 for n in notes]
        counts = Counter(pcs)
        root_pc, _ = counts.most_common(1)[0]
        note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

        # Find lowest note matching that pitch class for recording octave
        matching = [n for n in notes if n % 12 == root_pc]
        if matching:
            low = min(matching)
            recording_octave = max(1, (low // 12) - 1)  # Default to at least octave 1
        else:
            recording_octave = 1

        return note_names[root_pc], recording_octave

    # Set root note and recording octave
    root_name, rec_oct = infer_root_and_octave(chords)
    if root_name:
        prog['progression']['rootNote'] = root_name
        prog['progression']['recordingOctave'] = rec_oct

    # Detect scale from chord progression
    detected_scale = detect_scale_from_chords(chords)
    prog['progression']['scale'] = detected_scale

    # Convert chords to MPC format
    for i, c in enumerate(chords):
        notes_str = c.get('notes', '')
        if isinstance(notes_str, str):
            notes_list = [int(n) for n in notes_str.split(';') if n]
        elif isinstance(notes_str, list):
            notes_list = notes_str
        else:
            notes_list = []
        
        chord_name = c.get('name', '')
        if not chord_name and notes_list:
            # Generate chord name if missing
            root = min(notes_list)
            chord_name = detect_chord_name(notes_list, root) if root is not None else f'Chord{i+1}'
        
        prog['progression']['chords'].append({
            'name': chord_name or f'Chord{i+1}',
            'role': 'Root' if i == 0 else 'Normal',
            'notes': notes_list
        })

    # Write JSON file with proper formatting
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(prog, f, indent=4)


def detect_chord_name(notes: List[int], root: int) -> str:
    """Detect chord name from MIDI notes and root. (Import from midi_to_progression if available)"""
    try:
        from scripts.midi_to_progression import detect_chord_name as midi_detect
        return midi_detect(notes, root)
    except ImportError:
        # Fallback implementation
        if not notes or root is None:
            return ""
        
        note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        root_name = note_names[root % 12]
        
        intervals = set()
        for note in notes:
            interval = (note - root) % 12
            if interval != 0:
                intervals.add(interval)
        
        if not intervals:
            return root_name
        elif intervals == {4, 7}:
            return root_name  # Major
        elif intervals == {3, 7}:
            return root_name + 'm'  # Minor
        elif intervals == {4, 7, 10}:
            return root_name + '7'  # Dominant 7th
        elif intervals == {4, 7, 11}:
            return root_name + 'maj7'  # Major 7th
        elif intervals == {3, 7, 10}:
            return root_name + 'm7'  # Minor 7th
        else:
            return root_name


def detect_scale_from_chords(chords_list: List[Dict]) -> str:
    """Analyze chord progression to determine the most likely scale/key."""
    if not chords_list:
        return 'Chromatic'
    
    # Collect all pitch classes used in the progression
    pitch_classes = set()
    chord_roots = []
    
    for chord in chords_list:
        notes_str = chord.get('notes', '')
        if isinstance(notes_str, str):
            for note_str in notes_str.split(';'):
                if note_str:
                    try:
                        note = int(note_str)
                        pitch_classes.add(note % 12)
                    except:
                        pass
        elif isinstance(notes_str, list):
            for note in notes_str:
                pitch_classes.add(note % 12)
        
        # Collect chord roots for progression analysis
        root = chord.get('root')
        if root is not None:
            chord_roots.append(root % 12)
    
    if len(pitch_classes) < 3:
        return 'Chromatic'
    
    # Define major and minor scales
    note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    
    # Major scale intervals: W-W-H-W-W-W-H
    major_intervals = [0, 2, 4, 5, 7, 9, 11]
    # Natural minor scale intervals: W-H-W-W-H-W-W  
    minor_intervals = [0, 2, 3, 5, 7, 8, 10]
    
    # Test all 12 possible keys
    best_scale = 'Chromatic'
    best_match_score = 0
    
    for tonic in range(12):
        # Test major scale
        major_scale = {(tonic + interval) % 12 for interval in major_intervals}
        major_matches = len(pitch_classes.intersection(major_scale))
        major_score = major_matches / len(pitch_classes) if pitch_classes else 0
        
        # Test minor scale  
        minor_scale = {(tonic + interval) % 12 for interval in minor_intervals}
        minor_matches = len(pitch_classes.intersection(minor_scale))
        minor_score = minor_matches / len(pitch_classes) if pitch_classes else 0
        
        # Bonus points for chord progression patterns
        progression_bonus = 0
        if chord_roots:
            # Look for common progressions
            if len(chord_roots) >= 2:
                # Check for V-I resolution (strong tonal indicator)
                for i in range(len(chord_roots) - 1):
                    if (chord_roots[i] - tonic) % 12 == 7 and chord_roots[i + 1] == tonic:
                        progression_bonus += 0.2
                
                # Check for ii-V progression
                for i in range(len(chord_roots) - 1):
                    if (chord_roots[i] - tonic) % 12 == 2 and (chord_roots[i + 1] - tonic) % 12 == 7:
                        progression_bonus += 0.1
                
                # Check for vi chord in major (relative minor)
                if (tonic + 9) % 12 in chord_roots:
                    progression_bonus += 0.05
        
        # Apply progression bonus
        major_score += progression_bonus
        minor_score += progression_bonus * 0.8  # Slightly favor major
        
        # Update best match
        if major_score > best_match_score and major_score > 0.6:  # 60% threshold
            best_match_score = major_score
            best_scale = note_names[tonic] + ' Major'
        
        if minor_score > best_match_score and minor_score > 0.6:
            best_match_score = minor_score
            best_scale = note_names[tonic] + ' Minor'
    
    # Test some common modal and jazz scales if no clear major/minor match
    if best_match_score < 0.6:
        # Test pentatonic scales (common in many genres)
        major_pentatonic = [0, 2, 4, 7, 9]
        minor_pentatonic = [0, 3, 5, 7, 10]
        blues_scale = [0, 3, 5, 6, 7, 10]
        
        for tonic in range(12):
            # Test pentatonic scales
            maj_pent_scale = {(tonic + interval) % 12 for interval in major_pentatonic}
            min_pent_scale = {(tonic + interval) % 12 for interval in minor_pentatonic}
            blues_scale_set = {(tonic + interval) % 12 for interval in blues_scale}
            
            maj_pent_score = len(pitch_classes.intersection(maj_pent_scale)) / len(pitch_classes)
            min_pent_score = len(pitch_classes.intersection(min_pent_scale)) / len(pitch_classes)
            blues_score = len(pitch_classes.intersection(blues_scale_set)) / len(pitch_classes)
            
            if maj_pent_score > best_match_score and maj_pent_score > 0.7:
                best_match_score = maj_pent_score
                best_scale = note_names[tonic] + ' Pentatonic'
            
            if min_pent_score > best_match_score and min_pent_score > 0.7:
                best_match_score = min_pent_score  
                best_scale = note_names[tonic] + ' Minor Pentatonic'
                
            if blues_score > best_match_score and blues_score > 0.7:
                best_match_score = blues_score
                best_scale = note_names[tonic] + ' Blues'
    
    # If we still don't have a good match, check if it's chromatic
    if best_match_score < 0.5:
        if len(pitch_classes) >= 8:  # 8+ different pitch classes suggests chromatic
            return 'Chromatic'
        else:
            # Default to the most common root note + major
            if chord_roots:
                from collections import Counter
                most_common_root = Counter(chord_roots).most_common(1)[0][0]
                return note_names[most_common_root] + ' Major'
    
    return best_scale


def convert_rpc_file(path: str, out_dir: Optional[str] = None):
    """Convert a single .rpc to .progression and return (out_path, chords)."""
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    chords = parse_rpc_file(path)
    out_dir = out_dir or os.path.dirname(path)
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(path))[0]
    out_path = os.path.join(out_dir, base + '.progression')
    write_progression(chords, out_path)
    return out_path, chords


def convert_rpc_folder(folder: str, out_dir: Optional[str] = None):
    """Convert all .rpc files in folder; return list of (in_path, out_path) and errors list."""
    if not os.path.isdir(folder):
        raise FileNotFoundError(folder)
    out_dir = out_dir or folder
    os.makedirs(out_dir, exist_ok=True)
    results = []
    errors = []
    for root_dir, _, files in os.walk(folder):
        for f in sorted(files):
            if f.lower().endswith('.rpc'):
                in_path = os.path.join(root_dir, f)
                try:
                    out_path, chords = convert_rpc_file(in_path, out_dir=out_dir)
                    results.append((in_path, out_path))
                except Exception as e:
                    errors.append((in_path, str(e)))
    return results, errors


class ConverterApp(tk.Toplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title('Ripchord (.rpc) & MIDI → .progression Converter')
        self.geometry('720x360')

        # Load persistent settings for folder memory
        self.settings = _load_settings()

        self.input_var = tk.StringVar()
        self.output_var = tk.StringVar()

        # Set default output folder from settings if available
        if self.settings.get('last_output_folder'):
            self.output_var.set(self.settings['last_output_folder'])

        frm = tk.Frame(self)
        frm.pack(fill='both', expand=True, padx=12, pady=12)

        tk.Label(frm, text='Input (.rpc/.mid file or folder):').grid(row=0, column=0, sticky='w')
        tk.Entry(frm, textvariable=self.input_var, width=60).grid(row=0, column=1, sticky='w')
        tk.Button(frm, text='Browse', command=self.browse_input).grid(row=0, column=2, padx=6)

        tk.Label(frm, text='Output folder (optional):').grid(row=1, column=0, sticky='w')
        tk.Entry(frm, textvariable=self.output_var, width=60).grid(row=1, column=1, sticky='w')
        tk.Button(frm, text='Browse', command=self.browse_output).grid(row=1, column=2, padx=6)

        # Preview area
        preview_frame = tk.LabelFrame(frm, text='Preview Chords (first file / selection)')
        preview_frame.grid(row=2, column=0, columnspan=3, sticky='nsew', pady=8)
        preview_frame.columnconfigure(0, weight=1)

        self.preview_list = tk.Listbox(preview_frame, height=8)
        self.preview_list.pack(fill='both', expand=True, padx=6, pady=6)

        btn_frame = tk.Frame(frm)
        btn_frame.grid(row=3, column=0, columnspan=3, pady=6)

        # Output format options
        self.format_var = tk.StringVar(value='progression')
        tk.Label(btn_frame, text='Output format:').grid(row=0, column=0, sticky='w')
        tk.OptionMenu(btn_frame, self.format_var, 'progression', 'pattern').grid(row=0, column=1, sticky='w')
        self.pattern_style_var = tk.StringVar(value='simple')
        tk.Label(btn_frame, text='Pattern style:').grid(row=0, column=2, sticky='w')
        tk.OptionMenu(btn_frame, self.pattern_style_var, 'simple', 'mpcjson', 'mpcpattern').grid(row=0, column=3, sticky='w')

        # Directory structure options (second row)
        tk.Label(btn_frame, text='Folder structure:').grid(row=1, column=0, sticky='w')
        self.preserve_structure_var = tk.BooleanVar(value=True)
        tk.Checkbutton(btn_frame, text='Preserve subdirectories', variable=self.preserve_structure_var).grid(row=1, column=1, sticky='w')
        
        tk.Label(btn_frame, text='Max depth:').grid(row=1, column=2, sticky='w')
        self.max_depth_var = tk.StringVar(value='')
        depth_entry = tk.Entry(btn_frame, textvariable=self.max_depth_var, width=8)
        depth_entry.grid(row=1, column=3, sticky='w')
        
        # Main action buttons (third row)
        tk.Button(btn_frame, text='Convert File', command=self.convert_file, width=20).grid(row=2, column=0, padx=4)
        tk.Button(btn_frame, text='Convert Folder (batch)', command=self.convert_folder, width=20).grid(row=2, column=1, padx=4)
        tk.Button(btn_frame, text='Validate Current', command=self.validate_current, width=20).grid(row=2, column=2, padx=4)
        tk.Button(btn_frame, text='Close', command=self.close, width=12).grid(row=2, column=3, padx=4)
        # Batch convert multiple selected files (fourth row)
        tk.Button(btn_frame, text='Batch Convert Files...', command=self.batch_convert_files, width=20).grid(row=3, column=0, padx=4, pady=(6, 0))
        tk.Button(btn_frame, text='Advanced Folder Batch...', command=self.advanced_folder_batch, width=20).grid(row=3, column=1, padx=4, pady=(6, 0))

        self.status = tk.Label(self, text='Ready', anchor='w')
        self.status.pack(fill='x', padx=12, pady=(0, 12))

        # Optional drag & drop: populate input_var with dropped file
        if TkdndAvailable:
            try:
                self.drop_target_register(DND_FILES)
                self.dnd_bind('<<Drop>>', self._on_drop)
            except Exception:
                pass

        # MIDI import buttons
        midi_frame = tk.Frame(frm)
        midi_frame.grid(row=4, column=0, columnspan=3, pady=(6, 0), sticky='w')
        tk.Button(midi_frame, text='Import MIDI File', command=self.browse_midi_file).grid(row=0, column=0, padx=4)
        tk.Button(midi_frame, text='Import MIDI Folder', command=self.browse_midi_folder).grid(row=0, column=1, padx=4)

    def _on_drop(self, event):
        data = event.data
        files = self.tk.splitlist(data)
        if files:
            self.input_var.set(files[0])
            self._update_preview(files[0])

    def close(self):
        # Save current settings before closing
        if hasattr(self, 'settings'):
            # Save current output folder if it's valid
            current_output = self.output_var.get().strip()
            if current_output:
                self.settings['last_output_folder'] = current_output
            _save_settings(self.settings)
        
        try:
            self.destroy()
        except Exception:
            pass

    def browse_input(self):
        # Start from last used folder if available
        initial_dir = self.settings.get('last_input_folder') or None
        
        p = safe_askopenfilename(
            title='Select .rpc or .mid file',
            filetypes=[('Ripchord', '*.rpc'), ('MIDI', '*.mid *.midi'), ('All files', '*.*')],
            initialdir=initial_dir
        )
        if p:
            self.input_var.set(p)
            
            # Save the folder for next time
            folder = os.path.dirname(p)
            self.settings['last_input_folder'] = folder
            _save_settings(self.settings)
            
            # show preview depending on file type
            ext = os.path.splitext(p)[1].lower()
            if ext in ('.mid', '.midi') and MIDI_AVAILABLE:
                try:
                    chords = parse_midi_file(p)
                    self._populate_preview_list(chords)
                except Exception:
                    self._update_preview(p)
            else:
                self._update_preview(p)

    def browse_output(self):
        # Start from last used output folder if available
        initial_dir = self.settings.get('last_output_folder') or None
        
        p = safe_askdirectory(title='Select output folder', initialdir=initial_dir)
        if p:
            self.output_var.set(p)
            
            # Save the folder for next time
            self.settings['last_output_folder'] = p
            _save_settings(self.settings)

    def browse_midi_file(self):
        if not MIDI_AVAILABLE:
            messagebox.showerror('MIDI support missing', 'MIDI support requires the midi_to_progression module and mido')
            return
        
        # Start from last used MIDI folder if available
        initial_dir = self.settings.get('last_input_folder') or None
        
        p = safe_askopenfilename(
            title='Select MIDI file',
            filetypes=[('MIDI', '*.mid *.midi'), ('All files', '*.*')],
            initialdir=initial_dir
        )
        if p:
            self.input_var.set(p)
            
            # Save the folder for next time
            folder = os.path.dirname(p)
            self.settings['last_input_folder'] = folder
            _save_settings(self.settings)
            
            try:
                chords = parse_midi_file(p)
                self._populate_preview_list(chords)
            except Exception as e:
                messagebox.showerror('Error', f'{e}\n\n{traceback.format_exc()}')

    def browse_midi_folder(self):
        if not MIDI_AVAILABLE:
            messagebox.showerror('MIDI support missing', 'MIDI support requires the midi_to_progression module and mido')
            return
        
        # Start from last used MIDI folder if available
        initial_dir = self.settings.get('last_midi_folder') or self.settings.get('last_input_folder') or None
        
        p = safe_askdirectory(title='Select folder containing MIDI files', initialdir=initial_dir)
        if p:
            self.input_var.set(p)
            
            # Save the folder for next time
            self.settings['last_midi_folder'] = p
            self.settings['last_input_folder'] = p
            _save_settings(self.settings)
            
            try:
                chords = parse_midi_folder(p, recursive=True)  # Enable recursive search
                self._populate_preview_list(chords)
            except Exception as e:
                messagebox.showerror('Error parsing MIDI folder', f"{e}\n\n{traceback.format_exc()}")

    def _get_max_depth(self):
        """Get max depth value from GUI, return None if empty or invalid."""
        depth_str = self.max_depth_var.get().strip()
        if not depth_str:
            return None
        try:
            return max(1, int(depth_str))
        except ValueError:
            return None

    def _pattern_extension(self):
        # Choose extension based on pattern style for clarity
        style = self.pattern_style_var.get()
        if style == 'mpcpattern':
            return '.mpcpattern'
        elif style == 'mpcjson':
            return '.progression'  # MPC progression format
        else:
            return '.pattern'  # Simple pattern format

    def convert_file(self):
        path = self.input_var.get().strip()
        if not path:
            messagebox.showwarning('Input required', 'Please choose a file to convert')
            return
        if os.path.isdir(path):
            messagebox.showwarning('Input is folder', 'Use Convert Folder for folders')
            return

        out_dir = self.output_var.get().strip() or os.path.dirname(path)
        ext = os.path.splitext(path)[1].lower()
        try:
            if ext == '.rpc':
                out_path, chords = convert_rpc_file(path, out_dir=out_dir)
            elif ext in ('.mid', '.midi'):
                if not MIDI_AVAILABLE:
                    raise RuntimeError('MIDI support unavailable (mido missing)')
                chords = parse_midi_file(path)
                base = os.path.splitext(os.path.basename(path))[0]
                if self.format_var.get() == 'progression':
                    out_path = os.path.join(out_dir, base + '.progression')
                    write_progression(chords, out_path)
                else:
                    extn = self._pattern_extension()
                    out_path = os.path.join(out_dir, base + extn)
                    if write_pattern_json:
                        write_pattern_json(chords, out_path, name=base, style=self.pattern_style_var.get())
                    else:
                        # fallback simple writer
                        simple = {'pattern': {'name': base, 'chords': []}}
                        for c in chords:
                            notes = [int(n) for n in (c.get('notes') or '').split(';') if n]
                            simple['pattern']['chords'].append({'name': c.get('name') or '', 'notes': notes, 'root': c.get('root')})
                        with open(out_path, 'w', encoding='utf-8') as fh:
                            json.dump(simple, fh, indent=2)
            else:
                raise RuntimeError('Unsupported input type for Convert File')

            self._populate_preview_list(chords)
            self.status.config(text=f'Wrote {out_path}')
            messagebox.showinfo('Done', f'Created {out_path}')
        except Exception as e:
            tb = traceback.format_exc()
            messagebox.showerror('Error', f"{e}\n\n{tb}")

    def convert_folder(self):
        # Start from last used batch folder if available
        initial_dir = self.settings.get('last_batch_folder') or self.settings.get('last_input_folder') or None
        
        folder = safe_askdirectory(title='Select folder containing .rpc or MIDI files', initialdir=initial_dir)
        if not folder:
            return
            
        # Save the folder for next time
        self.settings['last_batch_folder'] = folder
        self.settings['last_input_folder'] = folder
        _save_settings(self.settings)
        out_dir = self.output_var.get().strip() or folder
        
        # Enhanced logic to handle both .rpc and MIDI files
        try:
            results = []
            errors = []
            
            # Find all supported files
            rpc_files = []
            midi_files = []
            
            for root_dir, _, filenames in os.walk(folder):
                for f in filenames:
                    if f.lower().endswith('.rpc'):
                        rpc_files.append(os.path.join(root_dir, f))
                    elif f.lower().endswith(('.mid', '.midi')):
                        midi_files.append(os.path.join(root_dir, f))
            
            # Process .rpc files individually
            for rpc_file in rpc_files:
                try:
                    chords = parse_rpc_file(rpc_file)
                    base = os.path.splitext(os.path.basename(rpc_file))[0]
                    
                    if self.format_var.get() == 'progression':
                        out_path = os.path.join(out_dir, base + '.progression')
                        write_progression(chords, out_path)
                    else:
                        extn = self._pattern_extension()
                        out_path = os.path.join(out_dir, base + extn)
                        if write_pattern_json:
                            write_pattern_json(chords, out_path, name=base, style=self.pattern_style_var.get())
                        else:
                            simple = {'pattern': {'name': base, 'chords': []}}
                            for c in chords:
                                notes = [int(n) for n in (c.get('notes') or '').split(';') if n]
                                simple['pattern']['chords'].append({'name': c.get('name') or '', 'notes': notes, 'root': c.get('root')})
                            with open(out_path, 'w', encoding='utf-8') as fh:
                                json.dump(simple, fh, indent=2)
                    
                    results.append((rpc_file, out_path))
                except Exception as e:
                    errors.append((rpc_file, str(e)))
            
            # Process MIDI files (combine into single progression if preferred)
            if midi_files:
                if not MIDI_AVAILABLE:
                    for midi_file in midi_files:
                        errors.append((midi_file, 'MIDI support unavailable (mido missing)'))
                else:
                    # Process MIDI files individually
                    for midi_file in midi_files:
                        try:
                            chords = parse_midi_file(midi_file)
                            base = os.path.splitext(os.path.basename(midi_file))[0]
                            
                            if self.format_var.get() == 'progression':
                                out_path = os.path.join(out_dir, base + '.progression')
                                write_progression(chords, out_path)
                            else:
                                extn = self._pattern_extension()
                                out_path = os.path.join(out_dir, base + extn)
                                if write_pattern_json:
                                    write_pattern_json(chords, out_path, name=base, style=self.pattern_style_var.get())
                                else:
                                    simple = {'pattern': {'name': base, 'chords': []}}
                                    for c in chords:
                                        notes = [int(n) for n in (c.get('notes') or '').split(';') if n]
                                        simple['pattern']['chords'].append({'name': c.get('name') or '', 'notes': notes, 'root': c.get('root')})
                                    with open(out_path, 'w', encoding='utf-8') as fh:
                                        json.dump(simple, fh, indent=2)
                            
                            results.append((midi_file, out_path))
                        except Exception as e:
                            errors.append((midi_file, str(e)))
            
            if not rpc_files and not midi_files:
                messagebox.showwarning('No supported files', 'No .rpc or .mid/.midi files found in folder and subdirectories')
                return

            msg = f'Converted {len(results)} files.'
            if errors:
                msg += f' {len(errors)} errors.'
            self.status.config(text=msg)
            messagebox.showinfo('Batch complete', msg)
        except Exception as e:
            tb = traceback.format_exc()
            messagebox.showerror('Batch error', f"{e}\n\n{tb}")

    def validate_current(self):
        path = self.input_var.get().strip()
        if not path or not os.path.exists(path):
            messagebox.showwarning('No file', 'Choose an RPC or MIDI file to validate')
            return
        try:
            ext = os.path.splitext(path)[1].lower()
            if ext == '.rpc':
                chords = parse_rpc_file(path)
            elif ext in ('.mid', '.midi'):
                if not MIDI_AVAILABLE:
                    raise RuntimeError('MIDI support unavailable (mido missing)')
                chords = parse_midi_file(path)
            else:
                messagebox.showwarning('Unsupported', 'Unsupported file type for validation')
                return

            if not chords:
                messagebox.showwarning('Validation', 'No chords found in file')
            else:
                messagebox.showinfo('Validation', f'Found {len(chords)} chords; first: {chords[0]}')
                self._populate_preview_list(chords)
        except Exception as e:
            tb = traceback.format_exc()
            messagebox.showerror('Validation Error', f"{e}\n\n{tb}")

    def _populate_preview_list(self, chords: List[Dict]):
        self.preview_list.delete(0, tk.END)
        for c in chords[:200]:
            display = f"root={c.get('root')} name={c.get('name')} notes={c.get('notes')}"
            self.preview_list.insert(tk.END, display)

    def _update_preview(self, path: str):
        try:
            chords = parse_rpc_file(path)
            self._populate_preview_list(chords)
        except Exception:
            self.preview_list.delete(0, tk.END)

    def batch_convert_files(self):
        """Select multiple files and convert each to the chosen output format.

        Writes .progression or pattern files per-file according to the UI options.
        """
        # Start from last used input folder if available
        initial_dir = self.settings.get('last_input_folder') or None
        
        files = safe_askopenfilenames(
            title='Select .rpc and/or MIDI files to batch convert',
            filetypes=[('RPC/MIDI', '*.rpc *.mid *.midi'), ('All files', '*.*')],
            initialdir=initial_dir
        )
        if not files:
            return

        # Save the folder from the first selected file for next time
        if files:
            folder = os.path.dirname(files[0])
            self.settings['last_input_folder'] = folder
            _save_settings(self.settings)

        out_dir = self.output_var.get().strip() or None
        created = []
        errors = []

        for p in files:
            try:
                ext = os.path.splitext(p)[1].lower()
                base = os.path.splitext(os.path.basename(p))[0]
                target_dir = out_dir or os.path.dirname(p)

                if ext == '.rpc':
                    chords = parse_rpc_file(p)
                elif ext in ('.mid', '.midi'):
                    if not MIDI_AVAILABLE:
                        raise RuntimeError('MIDI support missing (mido)')
                    chords = parse_midi_file(p)
                else:
                    raise RuntimeError('Unsupported file type')

                if self.format_var.get() == 'progression':
                    outp = os.path.join(target_dir, base + '.progression')
                    write_progression(chords, outp)
                else:
                    extn = self._pattern_extension()
                    outp = os.path.join(target_dir, base + extn)
                    if write_pattern_json:
                        write_pattern_json(chords, outp, name=base, style=self.pattern_style_var.get())
                    else:
                        simple = {'pattern': {'name': base, 'chords': []}}
                        for c in chords:
                            notes = [int(n) for n in (c.get('notes') or '').split(';') if n]
                            simple['pattern']['chords'].append({'name': c.get('name') or '', 'notes': notes, 'root': c.get('root')})
                        with open(outp, 'w', encoding='utf-8') as fh:
                            json.dump(simple, fh, indent=2)

                created.append(outp)
            except Exception as e:
                errors.append((p, str(e)))

        summary = f"Created {len(created)} files."
        if created:
            summary += '\n' + '\n'.join(created[:50])
        if errors:
            summary += f"\n\n{len(errors)} errors occurred:\n"
            summary += '\n'.join(f"{f}: {err}" for f, err in errors[:20])

        messagebox.showinfo('Batch Conversion Complete', summary)

    def advanced_folder_batch(self):
        """Advanced folder batch conversion with directory structure options for MIDI and RPC files."""
        # Start from last used batch folder if available
        initial_dir = self.settings.get('last_batch_folder') or self.settings.get('last_input_folder') or None
            
        folder = safe_askdirectory(
            title='Select folder containing .rpc and/or MIDI files (will search subdirectories)',
            initialdir=initial_dir
        )
        if not folder:
            return
        
        # Save the source folder for next time
        self.settings['last_batch_folder'] = folder
        self.settings['last_input_folder'] = folder
        _save_settings(self.settings)
        
        # Start from last used output folder if available
        output_initial_dir = self.settings.get('last_output_folder') or None
            
        out_dir = safe_askdirectory(
            title='Select output folder',
            initialdir=output_initial_dir
        ) or self.output_var.get().strip() or folder
        if not out_dir:
            return
            
        # Save the output folder for next time
        if os.path.isdir(out_dir):
            self.settings['last_output_folder'] = out_dir
            _save_settings(self.settings)
        
        try:
            # Get options from GUI
            output_format = self.format_var.get()
            pattern_style = self.pattern_style_var.get() if output_format == 'pattern' else 'simple'
            preserve_structure = self.preserve_structure_var.get()
            max_depth = self._get_max_depth()
            
            all_converted = []
            all_errors = []
            
            # Find all supported files
            rpc_files = []
            midi_files = []
            
            for root_dir, _, filenames in os.walk(folder):
                for f in filenames:
                    full_path = os.path.join(root_dir, f)
                    if f.lower().endswith('.rpc'):
                        rpc_files.append(full_path)
                    elif f.lower().endswith(('.mid', '.midi')):
                        midi_files.append(full_path)
            
            # Process RPC files
            if rpc_files:
                for rpc_file in rpc_files:
                    try:
                        chords = parse_rpc_file(rpc_file)
                        base = os.path.splitext(os.path.basename(rpc_file))[0]
                        
                        # Determine output path with structure preservation
                        if preserve_structure:
                            rel_path = os.path.relpath(rpc_file, folder)
                            rel_dir = os.path.dirname(rel_path)
                            if max_depth is not None and rel_dir:
                                # Limit directory depth
                                parts = rel_dir.split(os.sep)[:max_depth]
                                rel_dir = os.sep.join(parts)
                            
                            out_subdir = os.path.join(out_dir, rel_dir) if rel_dir else out_dir
                            os.makedirs(out_subdir, exist_ok=True)
                        else:
                            out_subdir = out_dir
                        
                        if output_format == 'progression':
                            out_path = os.path.join(out_subdir, base + '.progression')
                            write_progression(chords, out_path)
                        else:
                            extn = self._pattern_extension()
                            out_path = os.path.join(out_subdir, base + extn)
                            if write_pattern_json:
                                write_pattern_json(chords, out_path, name=base, style=pattern_style)
                            else:
                                simple = {'pattern': {'name': base, 'chords': []}}
                                for c in chords:
                                    notes = [int(n) for n in (c.get('notes') or '').split(';') if n]
                                    simple['pattern']['chords'].append({'name': c.get('name') or '', 'notes': notes, 'root': c.get('root')})
                                with open(out_path, 'w', encoding='utf-8') as fh:
                                    json.dump(simple, fh, indent=2)
                        
                        all_converted.append((rpc_file, out_path))
                    except Exception as e:
                        all_errors.append((rpc_file, str(e)))
            
            # Process MIDI files using the existing batch function
            if midi_files:
                if MIDI_AVAILABLE:
                    from scripts.midi_to_progression import batch_convert_midi_folder
                    
                    converted, errors = batch_convert_midi_folder(
                        folder=folder,
                        output_dir=out_dir,
                        output_format=output_format,
                        recursive=True,
                        preserve_structure=preserve_structure,
                        max_depth=max_depth,
                        pattern_style=pattern_style
                    )
                    all_converted.extend(converted)
                    all_errors.extend(errors)
                else:
                    # Add MIDI files to error list if MIDI support is unavailable
                    for midi_file in midi_files:
                        all_errors.append((midi_file, 'MIDI support missing (mido)'))
            
            if not rpc_files and not midi_files:
                messagebox.showwarning('No Files Found', 'No .rpc or .mid/.midi files found in the selected folder.')
                return
                
            # Show results
            total_files = len(rpc_files) + len(midi_files)
            summary = f'Found {total_files} files ({len(rpc_files)} .rpc, {len(midi_files)} MIDI)\n'
            summary += f'Successfully converted: {len(all_converted)}\n'
            summary += f'Errors: {len(all_errors)}'
            
            if all_errors:
                summary += f"\n\nFirst few errors:\n"
                summary += '\n'.join(f"{os.path.basename(f)}: {err}" for f, err in all_errors[:10])
                if len(all_errors) > 10:
                    summary += f"\n... and {len(all_errors) - 10} more errors"

            messagebox.showinfo('Advanced Batch Conversion Complete', summary)
            
            # Show options summary
            options_msg = f"Options:\n"
            options_msg += f"- Output format: {output_format}\n"
            if output_format == 'pattern':
                options_msg += f"- Pattern style: {pattern_style}\n"
            options_msg += f"- Preserve directory structure: {'Yes' if preserve_structure else 'No (flatten)'}\n"
            if preserve_structure and max_depth:
                options_msg += f"- Maximum directory depth: {max_depth}\n"
            options_msg += f"\nProceed with batch conversion?"
            
            if not messagebox.askyesno('Confirm Batch Conversion', options_msg):
                return
            
            self.status.config(text='Converting folder... please wait')
            self.update()
            
            # Perform batch conversion
            converted, errors = batch_convert_midi_folder(
                folder=folder,
                output_dir=out_dir,
                output_format=output_format,
                pattern_style=pattern_style,
                preserve_structure=preserve_structure,
                max_depth=max_depth,
                recursive=True
            )
            
            # Show results
            summary = f"Advanced folder batch conversion completed!\n\n"
            summary += f"Files converted: {len(converted)}\n"
            summary += f"Errors: {len(errors)}\n\n"
            
            if converted:
                summary += "Sample converted files:\n"
                for src, dst in converted[:10]:  # Show first 10
                    rel_src = os.path.relpath(src, folder)
                    rel_dst = os.path.relpath(dst, out_dir)
                    summary += f"  {rel_src} → {rel_dst}\n"
                if len(converted) > 10:
                    summary += f"  ... and {len(converted) - 10} more\n"
            
            if errors:
                summary += f"\nErrors encountered:\n"
                for src, err in errors[:5]:  # Show first 5 errors
                    rel_src = os.path.relpath(src, folder)
                    summary += f"  {rel_src}: {err}\n"
                if len(errors) > 5:
                    summary += f"  ... and {len(errors) - 5} more errors\n"
                    
            self.status.config(text=f'Converted {len(converted)} files, {len(errors)} errors')
            messagebox.showinfo('Advanced Batch Complete', summary)
            
        except Exception as e:
            self.status.config(text='Batch conversion failed')
            tb = traceback.format_exc()
            messagebox.showerror('Advanced Batch Error', f"{e}\n\n{tb}")


def main():
    # When run standalone, create a hidden root and use Toplevel as the app window
    root = tk.Tk()
    root.withdraw()
    app = ConverterApp(master=root)
    app.transient(root)
    app.grab_set()
    app.mainloop()


if __name__ == '__main__':
    main()
