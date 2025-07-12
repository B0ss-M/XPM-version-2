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
    midi = extract_root_note_from_wav(path)
    if midi is None:
        midi = detect_fundamental_pitch(path)
    if midi is None:
        midi = infer_note_from_filename(path)
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
        self.tree = ttk.Treeview(frame, columns=('sample', 'note'), show='headings', selectmode='extended')
        self.tree.heading('sample', text='Sample File')
        self.tree.heading('note', text='Root')
        self.tree.column('sample', width=400)
        self.tree.column('note', width=80, anchor='center')
        vsb = ttk.Scrollbar(frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill='x', pady=5)
        ttk.Button(btn_frame, text='Add Samples...', command=self.add_samples).pack(side='left')
        ttk.Button(btn_frame, text='Remove Selected', command=self.remove_selected).pack(side='left', padx=5)
        ttk.Button(btn_frame, text='Set Root Note...', command=self.set_root_note).pack(side='left')
        ttk.Button(btn_frame, text='Rebuild Program', command=self.rebuild).pack(side='right')

    def refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        for m in self.mappings:
            self.tree.insert('', 'end', values=(os.path.basename(m['sample_path']), midi_to_name(m['root_note'])))

    def add_samples(self):
        paths = filedialog.askopenfilenames(parent=self, filetypes=[('Audio', '*.wav *.aif *.aiff *.flac *.mp3 *.ogg *.m4a')])
        for path in paths:
            if not path:
                continue
            midi = detect_pitch(path)
            self.mappings.append({
                'sample_path': path,
                'root_note': midi,
                'low_note': midi,
                'high_note': midi,
                'velocity_low': 0,
                'velocity_high': 127
            })
        if paths:
            self.refresh_tree()

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
        self.refresh_tree()

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
