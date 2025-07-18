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
from xpm_utils import _parse_xpm_for_rebuild, indent_tree


NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


def midi_to_name(num: int) -> str:
    """Convert a MIDI note number to a note name (e.g., 60 -> 'C4')."""
    return NOTE_NAMES[num % 12] + str(num // 12 - 1)


def detect_pitch(path: str) -> int | None:
    """Detect the pitch of a sample using multiple methods.
    
    Returns:
        int or None: MIDI note number if detected, None if no pitch could be determined
    """
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

    def create_widgets(self):
        # Top frame for folder info and XPM list
        top_frame = ttk.Frame(self, padding=5)
        top_frame.pack(fill='x', padx=5, pady=5)
        
        # Folder label
        ttk.Label(top_frame, text="Current Folder:").pack(side='left')
        self.folder_label = ttk.Label(top_frame, text="No folder selected")
        self.folder_label.pack(side='left', padx=5)
        
        # XPM List frame with scrollbar
        xpm_frame = ttk.LabelFrame(self, text="XPM Files", padding=5)
        xpm_frame.pack(fill='x', padx=5, pady=(0,5))
        
        # Create a frame to hold listbox and scrollbar
        list_frame = ttk.Frame(xpm_frame)
        list_frame.pack(fill='x', padx=5, pady=5)
        list_frame.grid_columnconfigure(0, weight=1)  # Make listbox expand horizontally
        
        # XPM Listbox with scrollbar
        self.xpm_list = tk.Listbox(list_frame, height=6)  # Increased height to show more files
        self.xpm_list.grid(row=0, column=0, sticky='ew')
        self.xpm_list.bind('<<ListboxSelect>>', self.on_xpm_select)
        
        # Add vertical scrollbar
        xpm_scrollbar = ttk.Scrollbar(list_frame, orient='vertical', 
                                     command=self.xpm_list.yview,
                                     style='Vertical.TScrollbar')
        xpm_scrollbar.grid(row=0, column=1, sticky='ns')
        self.xpm_list.configure(yscrollcommand=xpm_scrollbar.set)
        
        # Add selection count label
        self.selection_label = ttk.Label(xpm_frame, text="0 XPM files found")
        self.selection_label.pack(fill='x', padx=5, pady=(0,5))
        
        # Main frame for sample analysis
        frame = ttk.Frame(self, padding=10)
        frame.pack(fill='both', expand=True)
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        # Sample analysis tree
        self.tree = ttk.Treeview(
            frame,
            columns=('sample', 'xpm', 'detected', 'diff', 'index'),
            show='headings',
            selectmode='browse',
        )
        self.tree.heading('sample', text='Sample File')
        self.tree.heading('xpm', text='XPM Root')
        self.tree.heading('detected', text='Detected')
        self.tree.heading('diff', text='Diff')
        # Hide the index column since it's just for internal use
        self.tree.column('index', width=0, stretch=False)
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
        total_diff = 0
        valid_diffs = 0
        
        if not self.mappings:
            logging.warning("No mappings found to refresh tree")
            return
            
        logging.info(f"Refreshing tree with {len(self.mappings)} mappings")
        
        for i, m in enumerate(self.mappings):
            try:
                sample_path = m['sample_path']
                if not os.path.exists(sample_path):
                    logging.warning(f"Sample file not found: {sample_path}")
                    continue
                    
                xpm_root = int(m['root_note'])
                detected = detect_pitch(sample_path)
                diff = ''
                
                if detected is not None:
                    diff_val = detected - xpm_root
                    diff = f'{diff_val:+d}'
                    if abs(diff_val) > 0:  # Only count non-zero differences
                        total_diff += diff_val
                        valid_diffs += 1
                    detected = midi_to_name(detected)
                else:
                    detected = 'N/A'
                
                # Add item to tree and store mapping index for editing
                item = self.tree.insert('', 'end', values=(
                    os.path.basename(sample_path), 
                    midi_to_name(xpm_root), 
                    detected, 
                    diff
                ))
                self.tree.set(item, 'index', str(i))
            except Exception as e:
                logging.error(f"Error processing mapping {i}: {e}")
                continue
        
        # Calculate suggested transpose if there's a consistent offset
        if valid_diffs > 0 and valid_diffs == len(self.mappings):
            avg_diff = total_diff / valid_diffs
            if abs(avg_diff - round(avg_diff)) < 0.1:  # Check if it's close to a whole number
                self.suggested_transpose = -int(round(avg_diff))  # Negate because we want to correct the difference
                if self.suggested_transpose != 0:
                    messagebox.showinfo('Transpose Suggestion', 
                        f'All samples appear to be {abs(self.suggested_transpose)} semitones ' +
                        ('sharp' if self.suggested_transpose < 0 else 'flat') +
                        '.\nUse Auto Fix Transpose to correct this.',
                        parent=self)
        
        # Bind double-click to edit root note
        self.tree.bind('<Double-1>', self.on_double_click)

    def auto_fix_notes(self):
        """Fix sample mapping by updating individual root notes"""
        if not self.tree_xml:
            return
            
        if not messagebox.askyesno('Confirm Fix',
            'This will update the root note of each sample based on its detected pitch.\n'
            'All other parameters (loop points, tuning, etc.) will be preserved.\n\n'
            'Do you want to proceed? You can use Save As... to create a new file.',
            parent=self):
            return
        
        root = self.tree_xml.getroot()
        changes = 0
        
        # Process each sample and preserve its settings
        for m in self.mappings:
            detected = detect_pitch(m['sample_path'])
            if detected is None:
                continue
                
            current = int(m['root_note'])
            if detected != current:
                changes += 1
                m['root_note'] = detected
                m['low_note'] = detected
                m['high_note'] = detected
                
                # Update the XML tree while preserving all other settings
                for layer in root.findall('.//Layer'):
                    if layer.findtext('SampleFile') == m['sample_path']:
                        root_note = layer.find('RootNote')
                        if root_note is not None:
                            root_note.text = str(detected)
                            
        if changes > 0:
            self.load_mappings()
            messagebox.showinfo('Success', 
                f'Updated root notes for {changes} samples.\n'
                'Use Save As... to save your changes.',
                parent=self)
        else:
            messagebox.showinfo('No Change', 
                'No updates were necessary - all samples appear to be correctly mapped.',
                parent=self)

    def auto_fix_transpose(self):
        """Fix sample mapping by adjusting the master transpose value"""
        if not self.tree_xml:
            return
            
        if not hasattr(self, 'suggested_transpose') or self.suggested_transpose is None:
            messagebox.showinfo('No Action Needed', 
                'No consistent transposition offset detected.\n'
                'Try using Auto Fix Notes instead.', 
                parent=self)
            return
            
        if not messagebox.askyesno('Confirm Fix',
            f'This will adjust the master transpose by {self.suggested_transpose:+d} semitones.\n\n'
            'Do you want to proceed? You can use Save As... to create a new file.',
            parent=self):
            return
            
        # Get current transpose value and add our correction
        root = self.tree_xml.getroot()
        for instr in root.findall('.//Instrument'):
            current = int(instr.findtext('KeygroupMasterTranspose', '0'))
            new_transpose = current + self.suggested_transpose
            transpose_elem = instr.find('KeygroupMasterTranspose')
            if transpose_elem is None:
                transpose_elem = ET.SubElement(instr, 'KeygroupMasterTranspose')
            transpose_elem.text = str(new_transpose)
            
        self.load_mappings()
        messagebox.showinfo('Success', 
            f'Master transpose has been adjusted by {self.suggested_transpose:+d}.\n'
            'Use Save As... to save your changes.',
            parent=self)

    def save_program(self):
        if not self.tree_xml or not self.xpm_path:
            return
        out_path = self._safe_file_dialog('save',
                                       defaultextension='.xpm',
                                       filetypes=[('XPM Files', '*.xpm')],
                                       initialfile=os.path.basename(self.xpm_path))
        if not out_path:
            return
        indent_tree(self.tree_xml)
        self.tree_xml.write(out_path, encoding='utf-8', xml_declaration=True)
        messagebox.showinfo('Saved', f'Saved corrected program to\n{out_path}', parent=self)

    def load_folder(self, folder_path):
        """Load XPM files from the specified folder and subfolders"""
        try:
            if not os.path.isdir(folder_path):
                logging.warning(f"Invalid folder path: {folder_path}")
                return
            
            self.folder = folder_path
            folder_name = os.path.basename(folder_path) or folder_path
            self.folder_label.config(text=folder_name)
            logging.info(f"Loading XPM files from: {folder_path}")
            
            # Find all XPM files in the folder and subfolders
            xpm_files = []
            
            # First, check for XPM files directly in the specified folder
            for file in os.listdir(folder_path):
                file_path = os.path.join(folder_path, file)
                if os.path.isfile(file_path) and file.lower().endswith('.xpm'):
                    xpm_files.append(file)
            
            # Then, look for XPM files in subfolders
            for root, dirs, files in os.walk(folder_path):
                # Skip the top-level folder since we already processed it
                if root == folder_path:
                    continue
                    
                # Process files in this subfolder
                for file in files:
                    # Only include .xpm files (case insensitive)
                    if file.lower().endswith('.xpm'):
                        # Get relative path for better display
                        rel_path = os.path.relpath(os.path.join(root, file), folder_path)
                        xpm_files.append(rel_path)
                        
            logging.info(f"Found {len(xpm_files)} XPM files in {folder_path}")
                        
            # Update the XPM list
            self.xpm_list.delete(0, tk.END)
            for xpm in sorted(xpm_files, key=lambda x: x.lstrip('.')):
                self.xpm_list.insert(tk.END, xpm)
            
            # Update selection count label
            self.selection_label.config(text=f"{len(xpm_files)} XPM files found")
            
            if xpm_files:
                self.xpm_list.select_set(0)
                self.analyze_program(os.path.join(folder_path, xpm_files[0]))
            else:
                logging.info(f"No XPM files found in {folder_path}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load folder: {e}", parent=self)
            logging.error(f"Failed to load folder {folder_path}: {e}")

    def on_xpm_select(self, event):
        """Handle XPM file selection from the list"""
        selection = self.xpm_list.curselection()
        if not selection:
            return
            
        # Get the selected file (might be a relative path)
        xpm_path = self.xpm_list.get(selection[0])
        if self.folder and xpm_path:
            self.analyze_program(os.path.join(self.folder, xpm_path))

    def analyze_program(self, path):
        """Analyze an XPM file and display its sample mappings"""
        try:
            # Handle both relative and absolute paths
            if os.path.isabs(path):
                full_path = path
            else:
                full_path = os.path.join(self.folder, path)
                
            if not full_path or not os.path.exists(full_path):
                logging.warning(f"XPM file not found: {full_path}")
                return
                
            self.xpm_path = full_path
            
            try:
                self.tree_xml = ET.parse(full_path)  # Use full_path here, not path
                logging.info(f"Successfully parsed XPM: {os.path.basename(full_path)}")
            except ET.ParseError as exc:
                messagebox.showerror('Parse Error', 
                    f'Failed to parse {os.path.basename(full_path)}:\n{exc}', 
                    parent=self)
                return
            
            self.load_mappings()
        except Exception as e:
            messagebox.showerror('Error', 
                f'Failed to analyze program {os.path.basename(path)}:\n{e}', 
                parent=self)
            logging.error(f"Failed to analyze program {path}: {e}")
            return

    def refresh_folder(self):
        """Refresh the current folder to check for new XPM files"""
        folder = None
        
        # First try to get folder path from master
        if hasattr(self.master, 'folder_path'):
            if hasattr(self.master.folder_path, 'get'):  # Check if it's a StringVar
                folder = self.master.folder_path.get()
            else:
                folder = self.master.folder_path
                
        # If master doesn't have a valid folder, use our own
        if not folder or not os.path.isdir(folder):
            folder = self.folder
            
        # Finally, load the folder if it's valid
        if folder and os.path.isdir(folder):
            logging.info(f"Refreshing folder: {folder}")
            self.load_folder(folder)
        else:
            logging.warning("No valid folder to refresh")
            messagebox.showinfo("No Folder", "No valid folder selected to refresh.", parent=self)

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
