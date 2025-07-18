import os
import tkinter as tk
from tkinter import ttk, filedialog, simpledialog, messagebox
from collections import defaultdict

from audio_pitch import detect_fundamental_pitch
from xpm_parameter_editor import (
    extract_root_note_from_wav,
    infer_note_from_filename,
    name_to_midi,
)
from batch_program_editor import build_program_pads_json
from firmware_profiles import fw_program_parameters, get_pad_settings
from xml.sax.saxutils import escape as xml_escape
import json
import xml.etree.ElementTree as ET
from xpm_utils import _parse_xpm_for_rebuild

NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

def midi_to_name(num: int) -> str:
    return NOTE_NAMES[num % 12] + str(num // 12 - 1)

AUDIO_EXTS = ('.wav', '.aif', '.aiff', '.flac', '.mp3', '.ogg', '.m4a')




def detect_pitch(path: str) -> int:
    # First try to detect from filename - this is often more reliable for properly named files
    midi = infer_note_from_filename(path)
    
    # If filename detection fails, try to extract from embedded WAV metadata
    if midi is None:
        midi = extract_root_note_from_wav(path)
        
    # If metadata extraction fails, use audio analysis
    if midi is None:
        midi = detect_fundamental_pitch(path)
        
    # Default to middle C if all detection methods fail
    if midi is None:
        midi = 60
        
    return midi


class SampleMappingEditorWindow(tk.Toplevel):
    def __init__(self, master, xpm_path):
        super().__init__(master.root if hasattr(master, 'root') else master)
        self.master = master
        self.xpm_path = xpm_path
        self.title(os.path.basename(xpm_path))
        self.geometry('600x400')
        self.mappings, self.params = _parse_xpm_for_rebuild(xpm_path)
        self.create_widgets()
        self.refresh_tree()

    def create_widgets(self):
        frame = ttk.Frame(self, padding='10')
        frame.pack(fill='both', expand=True)
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        
        # Enhanced treeview with detection method column
        self.tree = ttk.Treeview(frame, columns=('sample', 'note', 'method'), show='headings', selectmode='extended')
        self.tree.heading('sample', text='Sample File')
        self.tree.heading('note', text='Root Note')
        self.tree.heading('method', text='Detection Method')
        self.tree.column('sample', width=350)
        self.tree.column('note', width=80, anchor='center')
        self.tree.column('method', width=120)
        
        vsb = ttk.Scrollbar(frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')

        # Control buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill='x', pady=5)
        ttk.Button(btn_frame, text='Add Samples...', command=self.add_samples).pack(side='left')
        ttk.Button(btn_frame, text='Remove Selected', command=self.remove_selected).pack(side='left', padx=5)
        ttk.Button(btn_frame, text='Set Root Note...', command=self.set_root_note).pack(side='left')
        ttk.Button(btn_frame, text='Batch Detect Notes', command=self.batch_detect_notes).pack(side='left', padx=5)
        ttk.Button(btn_frame, text='Rebuild Program', command=self.rebuild).pack(side='right')

    def refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        for m in self.mappings:
            # Get detection method if available, otherwise show "unknown"
            method = m.get('detection_method', 'unknown')
            
            # Format method display to be more user-friendly
            if method == 'filename':
                method_display = 'Filename'
            elif method == 'audio analysis':
                method_display = 'Audio Analysis'
            elif method == 'default':
                method_display = 'Default (C3)'
            else:
                method_display = 'Unknown'
                
            self.tree.insert('', 'end', values=(
                os.path.basename(m['sample_path']), 
                midi_to_name(m['root_note']),
                method_display
            ))

    def _safe_file_dialog(self, dialog_type='open', **kwargs):
        """Safely handle file dialogs to prevent macOS NSInvalidArgumentException"""
        try:
            # Ensure we have a parent
            kwargs.setdefault('parent', self)
            # Set initial directory if not specified
            if 'initialdir' not in kwargs:
                kwargs['initialdir'] = os.path.expanduser("~")

            if dialog_type == 'open':
                result = filedialog.askopenfilenames(**kwargs)
            elif dialog_type == 'save':
                result = filedialog.asksaveasfilename(**kwargs)
            else:
                result = None

            # Never return None
            if dialog_type == 'open':
                return result if result else ()
            else:
                return result if result else ""
        except Exception as e:
            print(f"File dialog error: {e}")
            return () if dialog_type == 'open' else ""

    def add_samples(self):
        """Add additional audio files to the mapping list."""
        # Create a single, space-separated string of wildcard patterns
        # from the ``AUDIO_EXTS`` tuple for macOS compatibility.
        audio_patterns = " ".join([f"*{ext}" for ext in AUDIO_EXTS])

        paths = self._safe_file_dialog(
            title="Select Audio Files",
            filetypes=[
                ('Audio Files', audio_patterns),
                ('All Files', '*.*'),
            ],
        )
        
        if not paths:
            return
            
        detection_summary = {
            "total": 0,
            "detected": 0,
            "default": 0
        }
        
        for path in paths:
            if not path:
                continue
                
            detection_summary["total"] += 1
            
            # Try to get note from filename first
            filename_midi = infer_note_from_filename(path)
            if filename_midi is not None:
                midi = filename_midi
                detection_summary["detected"] += 1
                detection_method = "filename"
            else:
                # Try other methods if filename detection fails
                midi = detect_pitch(path)
                if midi == 60 and not extract_root_note_from_wav(path) and not detect_fundamental_pitch(path):
                    detection_summary["default"] += 1
                    detection_method = "default"
                else:
                    detection_summary["detected"] += 1
                    detection_method = "audio analysis"
                    
            self.mappings.append({
                'sample_path': path,
                'root_note': midi,
                'low_note': midi,
                'high_note': midi,
                'velocity_low': 0,
                'velocity_high': 127,
                'detection_method': detection_method
            })
            
        # Show detection summary to the user
        if detection_summary["total"] > 0:
            self.refresh_tree()
            msg = f"Added {detection_summary['total']} samples:\n"
            msg += f"- {detection_summary['detected']} with detected root notes\n"
            if detection_summary["default"] > 0:
                msg += f"- {detection_summary['default']} assigned to default note (C3/60)\n"
            msg += "\nCheck the tree view and adjust root notes if needed."
            messagebox.showinfo("Sample Detection Results", msg, parent=self)
        
    def remove_selected(self):
        to_remove = []
        for item in self.tree.selection():
            idx = self.tree.index(item)
            to_remove.append(idx)
        for idx in reversed(to_remove):
            del self.mappings[idx]
        if to_remove:
            self.refresh_tree()

    def set_root_note(self):
        items = self.tree.selection()
        if not items:
            return
        item = items[0]
        idx = self.tree.index(item)
        current = self.mappings[idx]['root_note']
        res = simpledialog.askstring('Root Note', 'Enter root note (e.g., C3 or 60):', parent=self, initialvalue=midi_to_name(current))
        if not res:
            return
        midi = name_to_midi(res)
        if midi is None:
            try:
                midi = int(res)
                if not (0 <= midi <= 127):
                    raise ValueError
            except Exception:
                messagebox.showerror('Invalid Note', 'Please enter a valid MIDI note or note name.', parent=self)
                return
        self.mappings[idx]['root_note'] = midi
        self.mappings[idx]['low_note'] = midi
        self.mappings[idx]['high_note'] = midi
        self.mappings[idx]['detection_method'] = 'manual'
        self.refresh_tree()
        
    def batch_detect_notes(self):
        """Re-analyze all samples to detect root notes from filenames."""
        if not self.mappings:
            messagebox.showinfo("No Samples", "No samples to analyze", parent=self)
            return
            
        if not messagebox.askyesno("Confirm Detection", 
                                 "This will attempt to detect root notes from filenames for all samples.\n\n"
                                 "Any manually set notes will be overwritten. Continue?", 
                                 parent=self):
            return
            
        detection_stats = {
            "total": 0,
            "filename": 0,
            "audio": 0,
            "default": 0
        }
        
        for idx, m in enumerate(self.mappings):
            detection_stats["total"] += 1
            sample_path = m['sample_path']
            
            # First try filename detection
            filename_midi = infer_note_from_filename(sample_path)
            if filename_midi is not None:
                self.mappings[idx]['root_note'] = filename_midi
                self.mappings[idx]['low_note'] = filename_midi
                self.mappings[idx]['high_note'] = filename_midi
                self.mappings[idx]['detection_method'] = 'filename'
                detection_stats["filename"] += 1
                continue
                
            # Try audio detection if filename fails
            audio_midi = extract_root_note_from_wav(sample_path)
            if audio_midi is None:
                audio_midi = detect_fundamental_pitch(sample_path)
                
            if audio_midi is not None:
                self.mappings[idx]['root_note'] = audio_midi
                self.mappings[idx]['low_note'] = audio_midi
                self.mappings[idx]['high_note'] = audio_midi
                self.mappings[idx]['detection_method'] = 'audio analysis'
                detection_stats["audio"] += 1
            else:
                # Use default C3 if all detection fails
                self.mappings[idx]['root_note'] = 60
                self.mappings[idx]['low_note'] = 60
                self.mappings[idx]['high_note'] = 60
                self.mappings[idx]['detection_method'] = 'default'
                detection_stats["default"] += 1
                
        self.refresh_tree()
        
        # Show results
        msg = f"Detection Results ({detection_stats['total']} samples):\n\n"
        msg += f"- {detection_stats['filename']} detected from filenames\n"
        msg += f"- {detection_stats['audio']} detected from audio analysis\n"
        msg += f"- {detection_stats['default']} set to default (C3/60)\n\n"
        msg += "Review the results and make manual adjustments if needed."
        messagebox.showinfo("Note Detection Complete", msg, parent=self)

    def rebuild(self):
        program_name = os.path.splitext(os.path.basename(self.xpm_path))[0]
        output_folder = os.path.dirname(self.xpm_path)
        firmware = self.master.firmware_version.get() if hasattr(self.master, 'firmware_version') else '3.5.0'
        fmt = 'advanced'
        options = {
            'Polyphony': str(get_pad_settings(firmware, fmt).get('polyphony', 16))
        }
        params = fw_program_parameters(firmware, len(self.mappings), engine_override=fmt)
        options.update(params)
        root = ET.Element('MPCVObject')
        version = ET.SubElement(root, 'Version')
        ET.SubElement(version, 'File_Version').text = '2.1'
        ET.SubElement(version, 'Application').text = 'MPC-V'
        ET.SubElement(version, 'Application_Version').text = firmware
        ET.SubElement(version, 'Platform').text = 'Linux'
        program = ET.SubElement(root, 'Program', {'type': 'Keygroup'})
        ET.SubElement(program, 'ProgramName').text = xml_escape(program_name)
        note_layers = defaultdict(list)
        for m in self.mappings:
            note_layers[(m['low_note'], m['high_note'])].append(m)
        pads_json = build_program_pads_json(
            firmware,
            self.mappings,
            engine_override=fmt,
            num_instruments=len(note_layers),
        )
        pads_tag = 'ProgramPads-v2.10' if firmware in {'3.4.0', '3.5.0'} else 'ProgramPads'
        ET.SubElement(program, pads_tag).text = pads_json
        for k, v in options.items():
            ET.SubElement(program, k).text = str(v)
        instruments = ET.SubElement(program, 'Instruments')
        for idx, (low, high) in enumerate(sorted(note_layers.keys())):
            inst = ET.SubElement(instruments, 'Instrument', {'number': str(idx)})
            ET.SubElement(inst, 'LowNote').text = str(low)
            ET.SubElement(inst, 'HighNote').text = str(high)
            layers = ET.SubElement(inst, 'Layers')
            for lid, m in enumerate(sorted(note_layers[(low, high)], key=lambda x: x['velocity_low']), start=1):
                layer = ET.SubElement(layers, 'Layer', {'number': str(lid)})
                ET.SubElement(layer, 'SampleName').text = os.path.splitext(os.path.basename(m['sample_path']))[0]
                ET.SubElement(layer, 'SampleFile').text = os.path.basename(m['sample_path'])
                ET.SubElement(layer, 'VelStart').text = str(m['velocity_low'])
                ET.SubElement(layer, 'VelEnd').text = str(m['velocity_high'])
                ET.SubElement(layer, 'SampleEnd').text = '0'
                ET.SubElement(layer, 'RootNote').text = str(m['root_note'])
                ET.SubElement(layer, 'SampleStart').text = '0'
                ET.SubElement(layer, 'Loop').text = 'Off'
                ET.SubElement(layer, 'Direction').text = '0'
                ET.SubElement(layer, 'Offset').text = '0'
                ET.SubElement(layer, 'Volume').text = '1.0'
                ET.SubElement(layer, 'Pan').text = '0.5'
                ET.SubElement(layer, 'Tune').text = '0.0'
                ET.SubElement(layer, 'MuteGroup').text = '0'
        tree = ET.ElementTree(root)
        output_path = os.path.join(output_folder, f"{program_name}_rebuilt.xpm")
        tree.write(output_path, encoding='utf-8', xml_declaration=True)
        messagebox.showinfo('Rebuild Complete', f'Created {output_path}', parent=self)
        self.destroy()
