import os
import re
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

# Optional pygame import for audio playback
try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    
# Check if librosa is available for pitch detection
try:
    from audio_pitch import LIBROSA_AVAILABLE
except ImportError:
    LIBROSA_AVAILABLE = False
    
    
def is_hidden_file(filepath):
    """Check if a file is hidden (starts with dot or has hidden attribute)"""
    name = os.path.basename(filepath)
    # Check for files starting with a dot
    if name.startswith('.'):
        return True
    # Check for macOS hidden files
    try:
        if os.path.exists(filepath) and bool(os.stat(filepath).st_flags & 0x8000):
            return True
    except (AttributeError, OSError):
        # st_flags might not be available on all platforms
        pass
    return False


NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


def midi_to_name(num: int) -> str:
    """Convert a MIDI note number to a note name (e.g., 60 -> 'C4')."""
    return NOTE_NAMES[num % 12] + str(num // 12 - 1)


def detect_pitch(path: str) -> int | None:
    """Detect the pitch of a sample using multiple methods.
    
    Returns:
        int or None: MIDI note number if detected, None if no pitch could be determined
    """
    logging.debug(f"Detecting pitch for: {os.path.basename(path)}")
    
    # First try to get the pitch from the embedded MIDI note in the WAV file
    midi = extract_root_note_from_wav(path)
    if midi is not None:
        logging.debug(f"WAV embedded root note: {midi}")
        return midi
    
    # Next try to infer the note from the filename using our improved function
    midi = infer_note_from_filename(path)
    if midi is not None:
        logging.debug(f"Filename-based note detection: {midi}")
        return midi
        
    # Fall back to audio analysis if librosa is available
    if LIBROSA_AVAILABLE:
        try:
            midi = detect_fundamental_pitch(path)
            if midi is not None:
                logging.debug(f"Audio analysis detected pitch {midi} for {os.path.basename(path)}")
                return midi
        except Exception as e:
            logging.debug(f"Error in audio analysis: {e}")
    
    # Special case for the MPC filenames with embedded MIDI notes
    base = os.path.splitext(os.path.basename(path))[0]
    
    # Special case for "mtmonchg" style filenames with numbered suffixes (mtmonchg2.wav -> MIDI 47)
    if base.startswith('mtmonchg'):
        # Check for the number at the end
        mpc_match = re.search(r'mtmonchg(\d+)', base)
        if mpc_match:
            try:
                # The numbers in these files correspond to specific MIDI notes
                # Extract the number and add the base MIDI value (typically 45)
                idx = int(mpc_match.group(1))
                potential_midi = 45 + idx
                if 0 <= potential_midi <= 127:
                    logging.debug(f"Extracted MIDI note from mtmonchg pattern: {potential_midi}")
                    return potential_midi
            except ValueError:
                pass
    
    # Check for patterns like "1_021_a-1.wav" where a number represents the MIDI note
    midi_match = re.search(r'_?0?(\d{2})[\D_]', base)
    if midi_match:
        try:
            potential_midi = int(midi_match.group(1))
            if 0 <= potential_midi <= 127:
                logging.debug(f"Extracted MIDI number from filename pattern: {potential_midi}")
                return potential_midi
        except ValueError:
            pass
    
    # Last attempt with raw number search
    midi_match = re.search(r'\b(\d{2,3})\b', base)
    if midi_match:
        try:
            potential_midi = int(midi_match.group(1))
            if 0 <= potential_midi <= 127:
                logging.debug(f"Using raw MIDI number from filename: {potential_midi}")
                return potential_midi
        except ValueError:
            pass
                
    # Ultimate fallback
    logging.debug(f"No pitch detected for {path}, using default C4 (60)")
    return 60  # Default to middle C if nothing else works


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
        
        # Create context menu for right-click options
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Edit Root Note", command=self.edit_root_note)
        self.context_menu.add_command(label="Override Detected Pitch", command=self.override_detected_pitch)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Play Sample", command=self.play_selected_sample)
        self.context_menu.add_command(label="Stop Audio", command=self.stop_audio)
        
        # Bind right-click to show context menu
        self.tree.bind("<Button-3>", self.show_context_menu)
        # Double-click still edits root note for backward compatibility
        self.tree.bind('<Double-1>', self.on_double_click)

        bottom = ttk.Frame(self)
        bottom.pack(fill='x', pady=5)
        ttk.Button(bottom, text='Refresh Folder', command=self.refresh_folder).pack(side='left')
        ttk.Button(bottom, text='Auto Fix Notes', command=self.auto_fix_notes).pack(side='left', padx=5)
        ttk.Button(bottom, text='Auto Fix Transpose', command=self.auto_fix_transpose).pack(side='left')
        ttk.Button(bottom, text='Manual Correction', command=self.batch_manual_correction).pack(side='left', padx=5)
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
            
        # Filter out hidden sample files
        if self.mappings:
            orig_count = len(self.mappings)
            self.mappings = [m for m in self.mappings if not is_hidden_file(m.get('sample_path', ''))]
            hidden_count = orig_count - len(self.mappings)
            if hidden_count > 0:
                logging.info(f"Filtered out {hidden_count} hidden sample files")
                
        # Process each mapping to detect pitches
        processed_mappings = []
        for idx, m in enumerate(self.mappings):
            sample_path = m.get('sample_path', '')
            sample_name = os.path.basename(sample_path)
            root_note = m.get('root_note', 60)
            
            # Only process files that exist
            if os.path.exists(sample_path):
                detected = detect_pitch(sample_path)
                if detected is None:
                    detected = root_note  # Use root note if detection fails
                
                # Calculate difference
                diff = detected - root_note
                
                processed_mappings.append({
                    'sample_path': sample_path,
                    'sample': sample_name,
                    'root_note': root_note,
                    'detected': detected,
                    'diff': diff,
                    'index': idx
                })
        
        self.mappings = processed_mappings
        self.suggested_transpose = self._calculate_suggested_transpose()
                
        trans = params.get('KeygroupMasterTranspose', '0') if params else '0'
        self.transpose_var.set(str(trans))
        self.refresh_tree()

    def _calculate_suggested_transpose(self):
        """Calculate the suggested master transpose value based on the average difference"""
        if not self.mappings:
            return 0
            
        # Get all diff values
        diffs = [m.get('diff', 0) for m in self.mappings]
        
        # If no diffs, return 0
        if not diffs:
            return 0
            
        # Calculate the most common diff value (mode)
        from collections import Counter
        counts = Counter(diffs)
        most_common = counts.most_common(1)
        if most_common:
            return most_common[0][0]
        
        # Fallback to average if no mode
        return round(sum(diffs) / len(diffs))
    
    def batch_manual_correction(self):
        """Open a dialog for batch manual correction of detected pitches"""
        if not self.mappings:
            messagebox.showinfo("No Data", "No samples loaded to correct", parent=self)
            return
            
        # Create a new top-level window for batch corrections
        correction_window = tk.Toplevel(self)
        correction_window.title("Batch Manual Correction")
        correction_window.geometry("800x500")
        correction_window.transient(self)  # Make it modal
        
        # Ensure audio stops when window is closed
        correction_window.protocol("WM_DELETE_WINDOW", 
                                 lambda: [self._stop_audio(correction_window), 
                                          correction_window.destroy()])
        
        # Create a frame with scrollable area
        main_frame = ttk.Frame(correction_window)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create canvas with scrollbar
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Add header
        ttk.Label(scrollable_frame, text="Sample File", width=40).grid(row=0, column=0, padx=5, pady=5)
        ttk.Label(scrollable_frame, text="Root Note", width=10).grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(scrollable_frame, text="Detected", width=10).grid(row=0, column=2, padx=5, pady=5)
        ttk.Label(scrollable_frame, text="Manual", width=10).grid(row=0, column=3, padx=5, pady=5)
        ttk.Label(scrollable_frame, text="Play", width=5).grid(row=0, column=4, padx=5, pady=5)
        
        # Track the manual entry widgets for later retrieval
        manual_entries = {}
        
        # Add rows for each sample
        row = 1
        for idx, mapping in enumerate(self.mappings):
            if 'sample_path' not in mapping:
                continue
                
            sample_path = mapping['sample_path']
            if not os.path.exists(sample_path):  # Skip missing samples
                continue
                
            # Sample filename (truncated if needed)
            basename = os.path.basename(sample_path)
            if len(basename) > 40:
                basename = basename[:37] + "..."
            ttk.Label(scrollable_frame, text=basename).grid(row=row, column=0, padx=5, pady=2, sticky="w")
            
            # Root note (read-only)
            root_note = mapping.get('root_note', '')
            root_name = midi_to_name(root_note) if root_note is not None else ""
            ttk.Label(scrollable_frame, text=root_name).grid(row=row, column=1, padx=5, pady=2)
            
            # Detected note (read-only)
            detected = mapping.get('detected', '')
            detected_name = midi_to_name(detected) if detected is not None else ""
            ttk.Label(scrollable_frame, text=detected_name).grid(row=row, column=2, padx=5, pady=2)
            
            # Manual override entry
            entry_var = tk.StringVar()
            if mapping.get('manual_detection'):
                entry_var.set(detected_name)
            entry = ttk.Entry(scrollable_frame, width=10, textvariable=entry_var)
            entry.grid(row=row, column=3, padx=5, pady=2)
            manual_entries[idx] = entry_var
            
            # Play/audio control frame
            audio_frame = ttk.Frame(scrollable_frame)
            audio_frame.grid(row=row, column=4, padx=5, pady=2)
            
            # Play button
            play_btn = ttk.Button(
                audio_frame, 
                text="▶",
                width=3,
                command=lambda path=sample_path: self._play_audio(path, correction_window)
            )
            play_btn.pack(side='left', padx=(0,2))
            
            # Stop button (individual for each row)
            stop_btn = ttk.Button(
                audio_frame, 
                text="■",
                width=3,
                command=lambda: self._stop_audio(correction_window)
            )
            stop_btn.pack(side='left')
            
            row += 1
        
        # Buttons at the bottom
        btn_frame = ttk.Frame(correction_window)
        btn_frame.pack(fill='x', pady=10)
        
        def apply_changes():
            for idx, entry_var in manual_entries.items():
                value = entry_var.get().strip()
                if value:
                    try:
                        # Convert note name to MIDI
                        if value.isdigit():
                            midi = int(value)
                            if not 0 <= midi <= 127:
                                raise ValueError(f"MIDI note out of range: {midi}")
                        else:
                            midi = name_to_midi(value)
                            if midi is None:
                                raise ValueError(f"Invalid note name: {value}")
                        
                        # Update in the mappings
                        self.mappings[idx]['detected'] = midi
                        self.mappings[idx]['manual_detection'] = True
                        
                        # Recalculate difference
                        root_note = self.mappings[idx]['root_note']
                        self.mappings[idx]['diff'] = root_note - midi
                    except ValueError as e:
                        messagebox.showwarning("Invalid Note", f"Skipping invalid note '{value}': {e}", parent=correction_window)
            
            # Update the tree view
            self.refresh_tree()
            correction_window.destroy()
        
        # Add a global stop button
        ttk.Button(
            btn_frame, 
            text="Stop Audio", 
            command=lambda: self._stop_audio(correction_window)
        ).pack(side="left", padx=5)
        
        ttk.Button(btn_frame, text="Apply Changes", command=apply_changes).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=correction_window.destroy).pack(side="right", padx=5)
    
    def _play_audio(self, file_path, parent_window):
        """Helper method to play audio in batch correction dialog"""
        if not os.path.exists(file_path):
            messagebox.showerror("File Not Found", f"Sample file not found:\n{file_path}", parent=parent_window)
            return
            
        if not PYGAME_AVAILABLE:
            messagebox.showinfo("Playback Unavailable", 
                               "Audio playback requires pygame. Install it with 'pip install pygame'.",
                               parent=parent_window)
            return
            
        try:
            # Play using pygame which was already imported at module level
            pygame.mixer.init()
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            
            # Create or show the stop button if it doesn't exist yet
            if not hasattr(parent_window, 'stop_button'):
                parent_window.stop_button = ttk.Button(
                    parent_window, 
                    text="Stop Audio", 
                    command=lambda: self._stop_audio(parent_window)
                )
                parent_window.stop_button.pack(side='left', padx=5, pady=5, before=parent_window.winfo_children()[0])
            else:
                parent_window.stop_button.pack(side='left', padx=5, pady=5)
                
        except Exception as e:
            messagebox.showerror("Playback Error", 
                                f"Couldn't play the sample: {e}\n\nMake sure the file is valid.",
                                parent=parent_window)
    
    def _stop_audio(self, parent_window):
        """Stop audio playback"""
        if PYGAME_AVAILABLE and pygame.mixer.get_init():
            pygame.mixer.music.stop()
            # Hide the stop button
            if hasattr(parent_window, 'stop_button'):
                parent_window.stop_button.pack_forget()
    
    def refresh_tree(self):
        """Refresh the tree view display"""
        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # Add mappings back
        for mapping in self.mappings:
            if 'sample_path' not in mapping:
                continue
            
            # Skip hidden files
            if is_hidden_file(mapping['sample_path']):
                continue
                
            self.tree.insert('', 'end', values=(
                mapping['sample'],
                mapping['root_note'],
                mapping['detected'],
                mapping['diff'],
                mapping['index']
            ))

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
                # Skip hidden files
                if is_hidden_file(file_path):
                    continue
                if os.path.isfile(file_path) and file.lower().endswith('.xpm'):
                    xpm_files.append(file)
            
            # Then, look for XPM files in subfolders
            for root, dirs, files in os.walk(folder_path):
                # Skip the top-level folder since we already processed it
                if root == folder_path:
                    continue
                    
                # Skip hidden directories
                dirs[:] = [d for d in dirs if not is_hidden_file(os.path.join(root, d))]
                    
                # Process files in this subfolder
                for file in files:
                    file_path = os.path.join(root, file)
                    # Skip hidden files
                    if is_hidden_file(file_path):
                        continue
                    # Only include .xpm files (case insensitive)
                    if file.lower().endswith('.xpm'):
                        # Get relative path for better display
                        rel_path = os.path.relpath(file_path, folder_path)
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

    def show_context_menu(self, event):
        """Show the context menu on right-click"""
        # Get the item under the cursor
        item = self.tree.identify_row(event.y)
        if item:
            # Select the item and show the context menu
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)
    
    def edit_root_note(self):
        """Edit the root note of the selected sample"""
        selected = self.tree.selection()
        if not selected:
            return
            
        item = selected[0]
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
            
            # Update in the XML if a program is loaded
            if self.xpm_program:
                sample_path = self.mappings[idx]['path']
                for keygroup in self.xpm_program.findall('.//keygroup'):
                    for sample in keygroup.findall('.//sample'):
                        path_elem = sample.find('path')
                        if path_elem is not None and path_elem.text == sample_path:
                            root_note = sample.find('root_note')
                            if root_note is not None:
                                root_note.text = str(midi)
                                
                            # Also update low_note and high_note if they exist
                            low_note = sample.find('low_note')
                            if low_note is not None:
                                low_note.text = str(midi)
                                
                            high_note = sample.find('high_note')
                            if high_note is not None:
                                high_note.text = str(midi)
            
        except Exception as e:
            messagebox.showerror('Invalid Note', str(e), parent=self)
    
    def override_detected_pitch(self):
        """Manually override the detected pitch for a sample"""
        selected = self.tree.selection()
        if not selected:
            return
            
        item = selected[0]
        idx = int(self.tree.set(item, 'index'))
        mapping = self.mappings[idx]
        current_detected = mapping.get('detected', 60)
        current_name = midi_to_name(current_detected) if current_detected is not None else "C4"
        
        # Ask for new detected pitch
        res = simpledialog.askstring(
            'Override Detected Pitch', 
            'Enter manual pitch detection value (e.g., C3 or 60):\nUse note names (C3) or MIDI numbers (60)',
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
                    
            # Update detected pitch
            self.mappings[idx]['detected'] = midi
            
            # Recalculate difference
            root_note = self.mappings[idx]['root_note']
            diff = root_note - midi
            self.mappings[idx]['diff'] = diff
            
            # Mark as manually set
            self.mappings[idx]['manual_detection'] = True
            
            # Update tree display
            self.refresh_tree()
            
        except Exception as e:
            messagebox.showerror('Invalid Note', str(e), parent=self)
    
    def play_selected_sample(self):
        """Play the selected sample audio"""
        selected = self.tree.selection()
        if not selected:
            return
            
        item = selected[0]
        idx = int(self.tree.set(item, 'index'))
        sample_path = self.mappings[idx]['sample_path']
        
        if not os.path.exists(sample_path):
            messagebox.showerror("File Not Found", f"Sample file not found:\n{sample_path}", parent=self)
            return
            
        if not PYGAME_AVAILABLE:
            messagebox.showinfo("Playback Unavailable", 
                               "Audio playback requires pygame. Install it with 'pip install pygame'.",
                               parent=self)
            return
            
        try:
            # Play using pygame which was already imported at module level
            pygame.mixer.init()
            pygame.mixer.music.load(sample_path)
            pygame.mixer.music.play()
            
            # Show the stop button if it exists, or create it if it doesn't
            if not hasattr(self, 'audio_stop_btn'):
                # Create a stop button
                self.audio_stop_btn = ttk.Button(self, text="Stop Audio", command=self.stop_audio)
                self.audio_stop_btn.pack(side='bottom', pady=5, before=self.winfo_children()[-1])
            else:
                # Make sure the button is visible
                self.audio_stop_btn.pack(side='bottom', pady=5, before=self.winfo_children()[-1])
                
        except Exception as e:
            messagebox.showerror("Playback Error", 
                               f"Couldn't play the sample: {e}\n\nMake sure the file is valid.")
    
    def stop_audio(self):
        """Stop audio playback"""
        if PYGAME_AVAILABLE and pygame.mixer.get_init():
            pygame.mixer.music.stop()
            
            # Hide the stop button
            if hasattr(self, 'audio_stop_btn'):
                self.audio_stop_btn.pack_forget()
    
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
