import os
import logging
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import xml.etree.ElementTree as ET

from xpm_parameter_editor import (
    extract_root_note_from_wav,
    infer_note_from_filename,
    fix_sample_notes,
    fix_master_transpose,
    name_to_midi,
)

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
        self.last_path = os.path.expanduser("~")
        self.create_widgets()
        
        # If master has a folder path, load XPM files from that folder
        if hasattr(master, 'folder_path'):
            folder = master.folder_path.get()
            if folder and os.path.isdir(folder):
                self.load_folder(folder)
        
    def _safe_file_dialog(self, dialog_type='open', **kwargs):
        """Safely handle file dialogs to prevent macOS NSInvalidArgumentException"""
        try:
            # Ensure we have a parent
            kwargs.setdefault('parent', self)
            # Set initial directory if not specified
            if 'initialdir' not in kwargs:
                kwargs['initialdir'] = getattr(self, 'last_path', os.path.expanduser("~"))

            if dialog_type == 'open':
                result = filedialog.askopenfilename(**kwargs)
            elif dialog_type == 'save':
                result = filedialog.asksaveasfilename(**kwargs)
            else:
                result = None

            # Store the last used directory
            if result:
                self.last_path = os.path.dirname(result)
            
            # Never return None
            return result if result else ""
        except Exception as e:
            print(f"File dialog error: {e}")
            return ""

    def create_widgets(self):
        # Top frame for folder info and XPM list
        top_frame = ttk.Frame(self, padding=5)
        top_frame.pack(fill='x', padx=5, pady=5)
        
        # Folder label
        ttk.Label(top_frame, text="Current Folder:").pack(side='left')
        self.folder_label = ttk.Label(top_frame, text="No folder selected")
        self.folder_label.pack(side='left', padx=5)
        
        # XPM List frame
        xpm_frame = ttk.LabelFrame(self, text="XPM Files", padding=5)
        xpm_frame.pack(fill='x', padx=5, pady=(0,5))
        
        # XPM Listbox
        self.xpm_list = tk.Listbox(xpm_frame, height=3)
        self.xpm_list.pack(fill='x', padx=5, pady=5)
        self.xpm_list.bind('<<ListboxSelect>>', self.on_xpm_select)
        
        # Main frame for sample analysis
        frame = ttk.Frame(self, padding=10)
        frame.pack(fill='both', expand=True)
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        # Sample analysis tree
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
        ttk.Button(bottom, text='Refresh Folder', command=self.refresh_folder).pack(side='left')
        ttk.Button(bottom, text='Auto Fix Notes', command=self.auto_fix_notes).pack(side='left', padx=5)
        ttk.Button(bottom, text='Auto Fix Transpose', command=self.auto_fix_transpose).pack(side='left')
        ttk.Button(bottom, text='Save As...', command=self.save_program).pack(side='right')
        ttk.Label(bottom, textvariable=self.transpose_var).pack(side='right', padx=5)
        ttk.Label(bottom, text='Master Transpose:').pack(side='right')

    def load_folder(self, folder_path):
        """Load XPM files from the specified folder"""
        try:
            if not os.path.isdir(folder_path):
                return
            
            self.folder = folder_path
            self.folder_label.config(text=os.path.basename(folder_path))
            
            # Find all XPM files in the folder
            xpm_files = []
            for file in os.listdir(folder_path):
                if file.lower().endswith('.xpm'):
                    xpm_files.append(file)
            
            # Update the XPM list
            self.xpm_list.delete(0, tk.END)
            for xpm in sorted(xpm_files):
                self.xpm_list.insert(tk.END, xpm)
            
            if xpm_files:
                self.xpm_list.select_set(0)
                self.analyze_program(os.path.join(folder_path, xpm_files[0]))
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load folder: {e}", parent=self)
            logging.error(f"Failed to load folder {folder_path}: {e}")

    def refresh_folder(self):
        """Refresh the current folder to check for new XPM files"""
        if hasattr(self.master, 'folder_path'):
            folder = self.master.folder_path.get()
            if folder and os.path.isdir(folder):
                self.load_folder(folder)
                return
        
        if self.folder and os.path.isdir(self.folder):
            self.load_folder(self.folder)
            
    def on_double_click(self, event):
        """Handle double-click on a tree item to edit root note"""
        item = self.tree.identify('item', event.x, event.y)
        if not item:
            return
            
        # Get the current mapping index and root note
        idx = int(self.tree.set(item, 'index'))
        current = self.mappings[idx]['root_note']
        current_name = midi_to_name(current)
        
        # Ask for new root note
        res = simpledialog.askstring(
            'Edit Root Note', 
            'Enter new root note (e.g., C3 or 60):\nUse note names (C3) or MIDI numbers (60)',
            parent=self,
            initialvalue=current_name
        )
        if not res:
            return
            
        # Convert input to MIDI note number
        try:
            if res.isdigit():
                midi = int(res)
                if not 0 <= midi <= 127:
                    raise ValueError("MIDI note must be between 0 and 127")
            else:
                midi = name_to_midi(res)
                if midi is None:
                    raise ValueError("Invalid note name")
                    
            # Update mapping and refresh display
            self.mappings[idx]['root_note'] = midi
            self.mappings[idx]['low_note'] = midi
            self.mappings[idx]['high_note'] = midi
            self.tree_xml.dirty = True  # Mark as modified
            self.refresh_tree()
            
        except Exception as e:
            messagebox.showerror('Invalid Note', str(e), parent=self)

    def on_xpm_select(self, event):
        """Handle XPM file selection from the list"""
        selection = self.xpm_list.curselection()
        if not selection:
            return
            
        xpm_name = self.xpm_list.get(selection[0])
        if self.folder and xpm_name:
            xpm_path = os.path.join(self.folder, xpm_name)
            self.analyze_program(xpm_path)

    def analyze_program(self, path):
        """Analyze an XPM file and display its sample mappings"""
        try:
            if not path or not os.path.exists(path):
                return
                
            self.xpm_path = path
            
            try:
                self.tree_xml = ET.parse(path)
            except ET.ParseError as exc:
                messagebox.showerror('Parse Error', 
                    f'Failed to parse {os.path.basename(path)}:\n{exc}', 
                    parent=self)
                return
            
            self.load_mappings()
        except Exception as e:
            messagebox.showerror('Error', 
                f'Failed to analyze program {os.path.basename(path)}:\n{e}', 
                parent=self)
            logging.error(f"Failed to analyze program {path}: {e}")
            return

    def _safe_file_dialog(self, dialog_type='open', **kwargs):
        """Safely handle file dialogs to prevent macOS NSInvalidArgumentException"""
        try:
            # Ensure we have a parent
            kwargs.setdefault('parent', self)
            # Set initial directory if not specified
            if 'initialdir' not in kwargs:
                kwargs['initialdir'] = os.path.expanduser("~")

            if dialog_type == 'open':
                result = filedialog.askopenfilename(**kwargs)
            elif dialog_type == 'save':
                result = filedialog.asksaveasfilename(**kwargs)
            else:
                raise ValueError(f"Unsupported dialog_type: {dialog_type}")
            
            # Store the last used directory if a file was selected
            if result:
                self.last_path = os.path.dirname(result)
            
            # Never return None
            return result if result else ""
        except Exception as e:
            logging.error(f"File dialog error: {e}")
            return ""

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
        """Update the tree view with current sample mappings and detected pitches"""
        self.tree.delete(*self.tree.get_children())
        for m in self.mappings:
            detected = detect_pitch(m['sample_path'])
            diff = ''
            if detected is not None:
                diff_val = detected - int(m['root_note'])
                diff = f'{diff_val:+d}'
                detected = midi_to_name(detected)
            else:
                detected = 'N/A'
            
            # Add item to tree and store mapping index for editing
            item = self.tree.insert('', 'end', values=(
                os.path.basename(m['sample_path']), 
                midi_to_name(int(m['root_note'])), 
                detected, 
                diff
            ))
            self.tree.set(item, 'index', str(self.mappings.index(m)))
            
        # Bind double-click to edit root note
        self.tree.bind('<Double-1>', self.on_double_click)

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
        out_path = self._safe_file_dialog(
            'save',
            defaultextension='.xpm',
            filetypes=[('XPM Files', '*.xpm')],
            initialfile=os.path.basename(self.xpm_path),
        )
        if not out_path:
            return
        indent_tree(self.tree_xml)
        self.tree_xml.write(out_path, encoding='utf-8', xml_declaration=True)
        messagebox.showinfo('Saved', f'Saved corrected program to\n{out_path}', parent=self)

