import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import xml.etree.ElementTree as ET

from audio_pitch import detect_fundamental_pitch
from xpm_parameter_editor import (
    extract_root_note_from_wav,
    infer_note_from_filename,
    fix_sample_notes,
    fix_master_transpose,
)
from xpm_utils import _parse_xpm_for_rebuild, indent_tree


NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

def midi_to_name(num: int) -> str:
    return NOTE_NAMES[num % 12] + str(num // 12 - 1)


def detect_pitch(path: str) -> int | None:
    midi = extract_root_note_from_wav(path)
    if midi is None:
        midi = infer_note_from_filename(path)
    if midi is None:
        midi = detect_fundamental_pitch(path)
    return midi


class SampleMappingCheckerWindow(tk.Toplevel):
    """Inspect and correct sample mappings in an XPM program."""

    def __init__(self, master):
        super().__init__(master.root if hasattr(master, 'root') else master)
        self.master = master
        self.title('Sample Mapping Checker')
        self.geometry('640x400')
        self.xpm_path = None
        self.tree_xml = None
        self.folder = None
        self.mappings = []
        self.transpose_var = tk.StringVar(value='0')
        self.create_widgets()

    def create_widgets(self):
        frame = ttk.Frame(self, padding=10)
        frame.pack(fill='both', expand=True)
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            frame,
            columns=('sample', 'xpm', 'detected', 'diff'),
            show='headings',
            selectmode='browse',
        )
        self.tree.heading('sample', text='Sample File')
        self.tree.heading('xpm', text='XPM Root')
        self.tree.heading('detected', text='Detected')
        self.tree.heading('diff', text='Diff')
        self.tree.column('sample', width=300)
        self.tree.column('xpm', width=80, anchor='center')
        self.tree.column('detected', width=80, anchor='center')
        self.tree.column('diff', width=60, anchor='center')
        vsb = ttk.Scrollbar(frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')

        bottom = ttk.Frame(self)
        bottom.pack(fill='x', pady=5)
        ttk.Button(bottom, text='Open Program...', command=self.open_program).pack(side='left')
        ttk.Button(bottom, text='Auto Fix Notes', command=self.auto_fix_notes).pack(side='left', padx=5)
        ttk.Button(bottom, text='Auto Fix Transpose', command=self.auto_fix_transpose).pack(side='left')
        ttk.Button(bottom, text='Save As...', command=self.save_program).pack(side='right')
        ttk.Label(bottom, textvariable=self.transpose_var).pack(side='right', padx=5)
        ttk.Label(bottom, text='Master Transpose:').pack(side='right')

    def open_program(self):
        path = filedialog.askopenfilename(
            parent=self,
            filetypes=[
                ('XPM Files', '*.xpm'),
                ('Backup XPM', '*.bak *.xpm.bak *.bak.xpm'),
                ('All Files', '*.*'),
            ],
        )
        if not path:
            return
        self.xpm_path = path
        self.folder = os.path.dirname(path)
        try:
            self.tree_xml = ET.parse(path)
        except ET.ParseError as exc:
            messagebox.showerror('Parse Error', f'Failed to parse:\n{exc}', parent=self)
            return
        self.load_mappings()

    def load_mappings(self):
        self.mappings, params = _parse_xpm_for_rebuild(self.xpm_path)
        if self.mappings is None:
            messagebox.showerror('Error', f'Unable to read mappings from {os.path.basename(self.xpm_path)}', parent=self)
            self.tree.delete(*self.tree.get_children())
            return
        trans = params.get('KeygroupMasterTranspose', '0') if params else '0'
        self.transpose_var.set(str(trans))
        self.refresh_tree()

    def refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        for m in self.mappings:
            detected = detect_pitch(m['sample_path'])
            diff = ''
            if detected is not None:
                diff_val = detected - int(m['root_note'])
                diff = f'{diff_val:+d}'
                detected = midi_to_name(detected)
            else:
                detected = ''
            self.tree.insert('', 'end', values=(os.path.basename(m['sample_path']), midi_to_name(int(m['root_note'])), detected, diff))

    def auto_fix_notes(self):
        if not self.tree_xml:
            return
        changed = fix_sample_notes(self.tree_xml.getroot(), self.folder)
        if changed:
            self.load_mappings()
            messagebox.showinfo('Done', 'Sample notes updated from audio metadata.', parent=self)
        else:
            messagebox.showinfo('No Change', 'No updates were necessary.', parent=self)

    def auto_fix_transpose(self):
        if not self.tree_xml:
            return
        changed = fix_master_transpose(self.tree_xml.getroot(), self.folder)
        if changed:
            self.load_mappings()
            messagebox.showinfo('Done', 'Master transpose adjusted.', parent=self)
        else:
            messagebox.showinfo('No Change', 'No adjustment needed.', parent=self)

    def save_program(self):
        if not self.tree_xml or not self.xpm_path:
            return
        out_path = filedialog.asksaveasfilename(
            parent=self,
            defaultextension='.xpm',
            filetypes=[('XPM Files', '*.xpm')],
            initialfile=os.path.basename(self.xpm_path),
        )
        if not out_path:
            return
        indent_tree(self.tree_xml)
        self.tree_xml.write(out_path, encoding='utf-8', xml_declaration=True)
        messagebox.showinfo('Saved', f'Saved corrected program to\n{out_path}', parent=self)

