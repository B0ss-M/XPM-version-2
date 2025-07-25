"""
Keyboard Mapping Visualizer for XPM Files
Shows which samples are mapped to which keys on a visual keyboard
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import xml.etree.ElementTree as ET
import os
import re
from collections import defaultdict


class KeyboardMapperWindow(tk.Toplevel):
    """Visual keyboard showing XPM sample mappings"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("XPM Keyboard Mapper - Visual Sample Mapping")
        self.geometry("1200x800")
        self.minsize(1000, 600)
        
        # Colors for the keyboard
        self.WHITE_KEY_COLOR = "#FFFFFF"
        self.BLACK_KEY_COLOR = "#2C2C2C"
        self.MAPPED_WHITE_COLOR = "#FFE4E1"  # Light pink for mapped white keys
        self.MAPPED_BLACK_COLOR = "#8B4B6B"  # Dark pink for mapped black keys
        self.SELECTED_COLOR = "#FF6347"      # Tomato for selected key
        self.EDIT_HIGHLIGHT_COLOR = "#87CEEB"  # Sky blue for edit mode highlighting
        self.RANGE_SELECTION_COLOR = "#98FB98"  # Pale green for range selection
        
        # Current XPM data
        self.xpm_path = None
        self.keygroups = []
        self.selected_keygroup = None
        self.key_mappings = {}  # MIDI note -> keygroup info
        
        # Edit mode data
        self.edit_mode = False
        self.selected_instrument = None
        self.range_selection_start = None
        self.range_selection_end = None
        self.mapping_changes = {}  # Track changes made during editing
        self.original_tree = None  # Store original XPM tree for comparison
        
        # GUI elements
        self.canvas = None
        self.key_rects = {}  # MIDI note -> canvas rectangle
        self.key_labels = {}  # MIDI note -> canvas text
        
        self.setup_gui()
        
    def setup_gui(self):
        """Create the GUI layout"""
        # Configure style to match main app
        self.configure(bg="#F5F5DC")  # MPC_BEIGE
        
        # Top frame for file selection and controls
        top_frame = ttk.Frame(self, padding="10")
        top_frame.pack(fill="x")
        
        # File selection
        file_frame = ttk.LabelFrame(top_frame, text="XPM File", padding="5")
        file_frame.pack(fill="x", pady=(0, 10))
        file_frame.grid_columnconfigure(0, weight=1)
        
        self.file_path_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.file_path_var, state="readonly").grid(
            row=0, column=0, sticky="ew", padx=(0, 5)
        )
        ttk.Button(file_frame, text="Browse XPM...", command=self.browse_xpm).grid(
            row=0, column=1
        )
        ttk.Button(file_frame, text="Reload", command=self.reload_xmp).grid(
            row=0, column=2, padx=(5, 0)
        )
        
        # Controls frame
        controls_frame = ttk.LabelFrame(top_frame, text="Controls", padding="5")
        controls_frame.pack(fill="x")
        
        # Keygroup selection
        ttk.Label(controls_frame, text="Instrument:").grid(row=0, column=0, sticky="w")
        self.keygroup_var = tk.StringVar()
        self.keygroup_combo = ttk.Combobox(
            controls_frame, textvariable=self.keygroup_var, state="readonly", width=20
        )
        self.keygroup_combo.grid(row=0, column=1, sticky="w", padx=(5, 20))
        self.keygroup_combo.bind("<<ComboboxSelected>>", self.on_keygroup_selected)
        
        # View options
        ttk.Label(controls_frame, text="View:").grid(row=0, column=2, sticky="w")
        self.view_var = tk.StringVar(value="all")
        view_combo = ttk.Combobox(
            controls_frame, 
            textvariable=self.view_var, 
            values=["all", "single_instrument"], 
            state="readonly",
            width=15
        )
        view_combo.grid(row=0, column=3, sticky="w", padx=(5, 20))
        view_combo.bind("<<ComboboxSelected>>", self.update_keyboard_display)
        
        # Edit mode toggle
        self.edit_mode_var = tk.BooleanVar(value=False)
        self.edit_mode_btn = ttk.Checkbutton(
            controls_frame, text="Edit Mode", variable=self.edit_mode_var,
            command=self.toggle_edit_mode
        )
        self.edit_mode_btn.grid(row=0, column=6, sticky="w", padx=(20, 0))
        
        # Octave range
        ttk.Label(controls_frame, text="Range:").grid(row=0, column=4, sticky="w")
        self.octave_start_var = tk.IntVar(value=1)
        self.octave_end_var = tk.IntVar(value=7)
        
        octave_frame = ttk.Frame(controls_frame)
        octave_frame.grid(row=0, column=5, sticky="w", padx=(5, 0))
        
        tk.Spinbox(
            octave_frame, from_=-1, to=9, width=3, 
            textvariable=self.octave_start_var,
            command=self.update_keyboard_display
        ).pack(side="left")
        ttk.Label(octave_frame, text=" to ").pack(side="left")
        tk.Spinbox(
            octave_frame, from_=-1, to=9, width=3,
            textvariable=self.octave_end_var, 
            command=self.update_keyboard_display
        ).pack(side="left")
        
        # Main content area with keyboard and details
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill="both", expand=True)
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=2)
        main_frame.grid_columnconfigure(1, weight=1)
        
        # Keyboard canvas
        keyboard_frame = ttk.LabelFrame(main_frame, text="Keyboard Mapping", padding="5")
        keyboard_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        keyboard_frame.grid_rowconfigure(0, weight=1)
        keyboard_frame.grid_columnconfigure(0, weight=1)
        
        self.canvas = tk.Canvas(keyboard_frame, bg="white")
        self.canvas.grid(row=0, column=0, sticky="nsew")
        
        # Scrollbars for canvas
        h_scroll = ttk.Scrollbar(keyboard_frame, orient="horizontal", command=self.canvas.xview)
        h_scroll.grid(row=1, column=0, sticky="ew")
        self.canvas.configure(xscrollcommand=h_scroll.set)
        
        v_scroll = ttk.Scrollbar(keyboard_frame, orient="vertical", command=self.canvas.yview)
        v_scroll.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=v_scroll.set)
        
        # Bind canvas events
        self.canvas.bind("<Button-1>", self.on_key_click)
        self.canvas.bind("<Motion>", self.on_mouse_motion)
        
        # Details panel
        details_frame = ttk.LabelFrame(main_frame, text="Sample Details", padding="5")
        details_frame.grid(row=0, column=1, sticky="nsew")
        details_frame.grid_rowconfigure(0, weight=1)
        details_frame.grid_columnconfigure(0, weight=1)
        
        # Create notebook for details and editing
        self.details_notebook = ttk.Notebook(details_frame)
        self.details_notebook.grid(row=0, column=0, sticky="nsew")
        
        # Details tab
        details_tab = ttk.Frame(self.details_notebook, padding="5")
        self.details_notebook.add(details_tab, text="Sample Details")
        details_tab.grid_rowconfigure(0, weight=1)
        details_tab.grid_columnconfigure(0, weight=1)

        # Details text widget
        self.details_text = tk.Text(
            details_tab, 
            wrap="word", 
            state="disabled",
            bg="#FFFFFF",
            fg="#2C2C2C",
            font=("Courier", 10)
        )
        self.details_text.grid(row=0, column=0, sticky="nsew")

        details_scroll = ttk.Scrollbar(
            details_tab, orient="vertical", command=self.details_text.yview
        )
        details_scroll.grid(row=0, column=1, sticky="ns")
        self.details_text.configure(yscrollcommand=details_scroll.set)
        
        # Edit tab
        self.edit_tab = ttk.Frame(self.details_notebook, padding="5")
        self.details_notebook.add(self.edit_tab, text="Range Editor")
        self.create_edit_controls()
        
        # Initially disable edit tab
        self.details_notebook.tab(1, state="disabled")        # Status bar
        self.status_var = tk.StringVar(value="Ready. Load an XPM file to see sample mappings.")
        status_label = ttk.Label(self, textvariable=self.status_var, relief="sunken")
        status_label.pack(side="bottom", fill="x")
        
        # Load current folder's first XPM if available
        self.try_load_current_folder_xpm()
        
    def create_edit_controls(self):
        """Create the editing controls in the edit tab"""
        # Instrument selection for editing
        inst_frame = ttk.LabelFrame(self.edit_tab, text="Select Instrument to Edit", padding="5")
        inst_frame.pack(fill="x", pady=(0, 10))
        
        self.edit_instrument_var = tk.StringVar()
        self.edit_instrument_combo = ttk.Combobox(
            inst_frame, textvariable=self.edit_instrument_var, state="readonly"
        )
        self.edit_instrument_combo.pack(fill="x")
        self.edit_instrument_combo.bind("<<ComboboxSelected>>", self.on_edit_instrument_selected)
        
        # Range editing controls
        range_frame = ttk.LabelFrame(self.edit_tab, text="Key Range Adjustment", padding="5")
        range_frame.pack(fill="x", pady=(0, 10))
        
        # Current range display
        current_frame = ttk.Frame(range_frame)
        current_frame.pack(fill="x", pady=(0, 5))
        ttk.Label(current_frame, text="Current Range:").pack(side="left")
        self.current_range_var = tk.StringVar(value="None Selected")
        ttk.Label(current_frame, textvariable=self.current_range_var, font=("Helvetica", 10, "bold")).pack(side="left", padx=(10, 0))
        
        # New range inputs
        new_range_frame = ttk.Frame(range_frame)
        new_range_frame.pack(fill="x", pady=5)
        new_range_frame.grid_columnconfigure(1, weight=1)
        new_range_frame.grid_columnconfigure(3, weight=1)
        
        ttk.Label(new_range_frame, text="New Low:").grid(row=0, column=0, sticky="w", padx=(0, 5))
        self.new_low_note_var = tk.IntVar(value=60)
        self.new_low_spin = tk.Spinbox(
            new_range_frame, from_=0, to=127, textvariable=self.new_low_note_var, width=10
        )
        self.new_low_spin.grid(row=0, column=1, sticky="ew", padx=(0, 10))
        
        ttk.Label(new_range_frame, text="New High:").grid(row=0, column=2, sticky="w", padx=(0, 5))
        self.new_high_note_var = tk.IntVar(value=72)
        self.new_high_spin = tk.Spinbox(
            new_range_frame, from_=0, to=127, textvariable=self.new_high_note_var, width=10
        )
        self.new_high_spin.grid(row=0, column=3, sticky="ew")
        
        # Range adjustment buttons
        buttons_frame = ttk.Frame(range_frame)
        buttons_frame.pack(fill="x", pady=5)
        
        ttk.Button(
            buttons_frame, text="Apply Range", command=self.apply_range_change
        ).pack(side="left", padx=(0, 5))
        
        ttk.Button(
            buttons_frame, text="Select on Keyboard", command=self.start_keyboard_selection
        ).pack(side="left", padx=5)
        
        ttk.Button(
            buttons_frame, text="Auto-Fit Range", command=self.auto_fit_range
        ).pack(side="left", padx=5)
        
        ttk.Button(
            buttons_frame, text="Optimize Mapping", command=self.optimize_mapping
        ).pack(side="left", padx=5)
        
        # Velocity layer management
        velocity_frame = ttk.LabelFrame(self.edit_tab, text="Velocity Layers", padding="5")
        velocity_frame.pack(fill="x", pady=(0, 10))
        
        # Layer distribution options
        distrib_frame = ttk.Frame(velocity_frame)
        distrib_frame.pack(fill="x", pady=(0, 5))
        
        ttk.Label(distrib_frame, text="Layer Distribution:").pack(side="left")
        self.velocity_mode_var = tk.StringVar(value="even")
        mode_combo = ttk.Combobox(
            distrib_frame, textvariable=self.velocity_mode_var,
            values=["even", "dynamic", "custom"], state="readonly", width=12
        )
        mode_combo.pack(side="left", padx=(10, 0))
        mode_combo.bind("<<ComboboxSelected>>", self.on_velocity_mode_changed)
        
        ttk.Button(
            distrib_frame, text="Apply", command=self.apply_velocity_distribution
        ).pack(side="right")
        
        # Save/Cancel controls
        save_frame = ttk.LabelFrame(self.edit_tab, text="Save Changes", padding="5")
        save_frame.pack(fill="x", pady=(10, 0))
        
        buttons = ttk.Frame(save_frame)
        buttons.pack(fill="x")
        
        ttk.Button(
            buttons, text="Save XPM", command=self.save_changes, 
            style="Accent.TButton"
        ).pack(side="left", padx=(0, 5))
        
        ttk.Button(
            buttons, text="Revert Changes", command=self.revert_changes
        ).pack(side="left", padx=5)
        
        ttk.Button(
            buttons, text="Export as New", command=self.export_as_new
        ).pack(side="right")
        
    def toggle_edit_mode(self):
        """Toggle between view and edit modes"""
        self.edit_mode = self.edit_mode_var.get()
        
        if self.edit_mode:
            # Enable edit tab and populate with current data
            self.details_notebook.tab(1, state="normal")
            self.update_edit_controls()
            self.details_notebook.select(1)  # Switch to edit tab
            self.status_var.set("Edit Mode: Click and drag to select key ranges, or use controls to adjust mappings")
        else:
            # Disable edit tab and return to details
            self.details_notebook.tab(1, state="disabled")
            self.details_notebook.select(0)  # Switch to details tab
            self.selected_instrument = None
            self.range_selection_start = None
            self.range_selection_end = None
            self.status_var.set("View Mode: Click keys to see sample details")
            
        self.update_keyboard_display()
        
    def update_edit_controls(self):
        """Update edit controls with current instrument data"""
        if not self.keygroups:
            self.edit_instrument_combo['values'] = []
            return
            
        # Populate instrument selection
        values = []
        for i, kg in enumerate(self.keygroups):
            layer_names = [layer['sample_name'] for layer in kg['layers'][:2]]
            layer_str = ", ".join(layer_names)
            if len(kg['layers']) > 2:
                layer_str += f" (+{len(kg['layers'])-2} more)"
            values.append(f"Instrument {i}: {kg['note_range']} - {layer_str}")
            
        self.edit_instrument_combo['values'] = values
        if values and not self.edit_instrument_var.get():
            self.edit_instrument_var.set(values[0])
            self.on_edit_instrument_selected()
            
    def on_edit_instrument_selected(self, event=None):
        """Handle instrument selection in edit mode"""
        selection = self.edit_instrument_var.get()
        if not selection:
            return
            
        # Extract instrument index
        inst_index = int(selection.split(":")[0].split()[-1])
        self.selected_instrument = inst_index
        
        # Update range controls with current values
        if inst_index < len(self.keygroups):
            kg = self.keygroups[inst_index]
            self.current_range_var.set(f"{kg['note_range']} (MIDI {kg['low_note']}-{kg['high_note']})")
            self.new_low_note_var.set(kg['low_note'])
            self.new_high_note_var.set(kg['high_note'])
            
        self.update_keyboard_display()
        
    def start_keyboard_selection(self):
        """Start keyboard-based range selection mode"""
        if self.selected_instrument is None:
            messagebox.showwarning("No Instrument", "Please select an instrument to edit first.", parent=self)
            return
            
        self.range_selection_start = None
        self.range_selection_end = None
        self.status_var.set("Click on the keyboard to select the LOW note of the new range...")
        
    def apply_range_change(self):
        """Apply the new range to the selected instrument"""
        if self.selected_instrument is None:
            messagebox.showwarning("No Instrument", "Please select an instrument to edit first.", parent=self)
            return
            
        low_note = self.new_low_note_var.get()
        high_note = self.new_high_note_var.get()
        
        if low_note >= high_note:
            messagebox.showerror("Invalid Range", "Low note must be less than high note.", parent=self)
            return
            
        # Apply the change
        if self.selected_instrument < len(self.keygroups):
            kg = self.keygroups[self.selected_instrument]
            old_range = f"{kg['low_note']}-{kg['high_note']}"
            
            kg['low_note'] = low_note
            kg['high_note'] = high_note
            kg['note_range'] = f"{self.midi_to_note(low_note)}-{self.midi_to_note(high_note)}"
            
            # Track the change
            if self.selected_instrument not in self.mapping_changes:
                self.mapping_changes[self.selected_instrument] = {}
            self.mapping_changes[self.selected_instrument]['range'] = (low_note, high_note)
            
            # Update displays
            self.rebuild_key_mappings()
            self.update_edit_controls()
            self.update_keyboard_display()
            
            self.status_var.set(f"Updated Instrument {self.selected_instrument} range: {old_range} → {low_note}-{high_note}")
            
    def auto_fit_range(self):
        """Automatically fit range based on sample root notes"""
        if self.selected_instrument is None or self.selected_instrument >= len(self.keygroups):
            messagebox.showwarning("No Instrument", "Please select an instrument to edit first.", parent=self)
            return
            
        kg = self.keygroups[self.selected_instrument]
        if not kg['layers']:
            messagebox.showwarning("No Layers", "Selected instrument has no layers to analyze.", parent=self)
            return
            
        # Find the range of root notes in the layers
        root_notes = [layer['root_note'] for layer in kg['layers']]
        min_root = min(root_notes)
        max_root = max(root_notes)
        
        # Add some padding around the range
        padding = 6  # Half an octave
        suggested_low = max(0, min_root - padding)
        suggested_high = min(127, max_root + padding)
        
        # Update the controls
        self.new_low_note_var.set(suggested_low)
        self.new_high_note_var.set(suggested_high)
        
        # Ask user if they want to apply
        if messagebox.askyesno(
            "Auto-Fit Range", 
            f"Suggested range based on root notes:\nLow: {self.midi_to_note(suggested_low)} (MIDI {suggested_low})\nHigh: {self.midi_to_note(suggested_high)} (MIDI {suggested_high})\n\nApply this range?",
            parent=self
        ):
            self.apply_range_change()
                
    def optimize_mapping(self):
        """Intelligently optimize the keyboard mapping for better playability"""
        if self.selected_instrument is None or self.selected_instrument >= len(self.keygroups):
            messagebox.showwarning("No Instrument", "Please select an instrument to optimize.", parent=self)
            return
            
        kg = self.keygroups[self.selected_instrument]
        if not kg['layers']:
            messagebox.showwarning("No Layers", "Selected instrument has no layers to optimize.", parent=self)
            return
            
        # Analyze the samples and propose optimizations
        analysis = self.analyze_sample_distribution(kg)
        
        # Create optimization dialog
        self.show_optimization_dialog(analysis)
        
    def analyze_sample_distribution(self, keygroup):
        """Analyze the sample distribution and suggest optimizations"""
        layers = keygroup['layers']
        analysis = {
            'total_layers': len(layers),
            'root_notes': [layer['root_note'] for layer in layers],
            'velocity_ranges': [(layer['vel_start'], layer['vel_end']) for layer in layers],
            'sample_files': [layer['sample_file'] for layer in layers],
            'recommendations': []
        }
        
        # Analyze root note distribution
        root_notes = analysis['root_notes']
        if len(set(root_notes)) == 1:
            analysis['recommendations'].append({
                'type': 'single_note',
                'message': f"All samples have the same root note ({self.midi_to_note(root_notes[0])}). This is good for velocity layers.",
                'action': 'velocity_optimize'
            })
        else:
            note_range = max(root_notes) - min(root_notes)
            analysis['recommendations'].append({
                'type': 'multi_note',
                'message': f"Samples span {note_range} semitones ({self.midi_to_note(min(root_notes))} to {self.midi_to_note(max(root_notes))}). Consider splitting into separate instruments.",
                'action': 'range_optimize'
            })
            
        # Analyze velocity distribution
        vel_ranges = analysis['velocity_ranges']
        overlapping = any(
            r1[0] <= r2[1] and r2[0] <= r1[1] 
            for i, r1 in enumerate(vel_ranges) 
            for j, r2 in enumerate(vel_ranges) 
            if i != j
        )
        
        if overlapping:
            analysis['recommendations'].append({
                'type': 'velocity_overlap',
                'message': "Velocity ranges overlap. This can cause inconsistent playback.",
                'action': 'fix_velocity'
            })
        else:
            gaps = []
            sorted_ranges = sorted(vel_ranges, key=lambda x: x[0])
            for i in range(len(sorted_ranges) - 1):
                if sorted_ranges[i][1] + 1 < sorted_ranges[i+1][0]:
                    gaps.append((sorted_ranges[i][1] + 1, sorted_ranges[i+1][0] - 1))
            
            if gaps:
                analysis['recommendations'].append({
                    'type': 'velocity_gaps',
                    'message': f"Velocity gaps found: {gaps}. Some velocities won't trigger any sample.",
                    'action': 'fill_velocity'
                })
                
        # Check for pitch detection issues
        import os
        for i, layer in enumerate(layers):
            if layer['sample_file'] and os.path.exists(layer['sample_file']):
                try:
                    # Try to detect pitch from filename
                    filename = os.path.basename(layer['sample_file'])
                    detected_note = self.detect_note_from_filename(filename)
                    if detected_note is not None and detected_note != layer['root_note']:
                        analysis['recommendations'].append({
                            'type': 'pitch_mismatch',
                            'message': f"Layer {i+1}: Root note ({self.midi_to_note(layer['root_note'])}) doesn't match detected note from filename ({self.midi_to_note(detected_note)})",
                            'action': 'fix_pitch',
                            'layer_index': i,
                            'suggested_note': detected_note
                        })
                except:
                    pass
                    
        return analysis
        
    def detect_note_from_filename(self, filename):
        """Try to detect musical note from filename"""
        import re
        
        # Look for note patterns like C4, D#3, Bb2, etc.
        patterns = [
            r'([A-G])([#b]?)([0-9])',  # C4, D#3, Bb2
            r'([A-G])([#b]?)_([0-9])', # C_4, D#_3
            r'([A-G])([#b]?)-([0-9])', # C-4, D#-3
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                note_name = match.group(1).upper()
                accidental = match.group(2)
                octave = int(match.group(3))
                
                # Convert to MIDI number
                note_map = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
                midi_note = note_map[note_name] + (octave + 1) * 12
                
                if accidental == '#':
                    midi_note += 1
                elif accidental == 'b':
                    midi_note -= 1
                    
                if 0 <= midi_note <= 127:
                    return midi_note
                    
        return None
        
    def show_optimization_dialog(self, analysis):
        """Show optimization recommendations dialog"""
        dialog = tk.Toplevel(self)
        dialog.title("Mapping Optimization")
        dialog.geometry("500x400")
        dialog.transient(self)
        dialog.grab_set()
        
        # Configure style
        dialog.configure(bg="#F5F5DC")
        
        main_frame = ttk.Frame(dialog, padding="10")
        main_frame.pack(fill="both", expand=True)
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        
        # Analysis results
        results_frame = ttk.LabelFrame(main_frame, text="Analysis Results", padding="5")
        results_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        results_frame.grid_rowconfigure(0, weight=1)
        results_frame.grid_columnconfigure(0, weight=1)
        
        results_text = tk.Text(results_frame, wrap="word", height=15, bg="#FFFFFF", fg="#2C2C2C")
        results_text.grid(row=0, column=0, sticky="nsew")
        
        results_scroll = ttk.Scrollbar(results_frame, orient="vertical", command=results_text.yview)
        results_scroll.grid(row=0, column=1, sticky="ns")
        results_text.configure(yscrollcommand=results_scroll.set)
        
        # Populate analysis text
        results_text.insert(tk.END, f"🎹 INSTRUMENT {self.selected_instrument} ANALYSIS\n")
        results_text.insert(tk.END, "=" * 50 + "\n\n")
        results_text.insert(tk.END, f"Total Layers: {analysis['total_layers']}\n")
        results_text.insert(tk.END, f"Root Notes: {[self.midi_to_note(note) for note in analysis['root_notes']]}\n")
        results_text.insert(tk.END, f"Velocity Ranges: {analysis['velocity_ranges']}\n\n")
        
        results_text.insert(tk.END, "🔍 RECOMMENDATIONS:\n")
        results_text.insert(tk.END, "-" * 30 + "\n\n")
        
        for i, rec in enumerate(analysis['recommendations']):
            results_text.insert(tk.END, f"{i+1}. {rec['message']}\n\n")
            
        if not analysis['recommendations']:
            results_text.insert(tk.END, "✅ No issues found! This instrument appears to be well-configured.\n")
        
        results_text.config(state="disabled")
        
        # Action buttons
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=1, column=0, sticky="ew")
        
        if analysis['recommendations']:
            ttk.Button(
                buttons_frame, text="Auto-Fix Issues", 
                command=lambda: self.auto_fix_issues(analysis, dialog)
            ).pack(side="left", padx=(0, 5))
            
        ttk.Button(
            buttons_frame, text="Manual Adjust", 
            command=lambda: dialog.destroy()
        ).pack(side="left", padx=5)
        
        ttk.Button(
            buttons_frame, text="Close", 
            command=dialog.destroy
        ).pack(side="right")
        
    def auto_fix_issues(self, analysis, dialog):
        """Automatically fix detected issues"""
        if not messagebox.askyesno(
            "Auto-Fix", 
            "This will automatically apply fixes for detected issues. Continue?", 
            parent=dialog
        ):
            return
            
        kg = self.keygroups[self.selected_instrument]
        changes_made = []
        
        for rec in analysis['recommendations']:
            if rec['action'] == 'velocity_optimize':
                # Apply even velocity distribution
                self.velocity_mode_var.set("even")
                self.apply_velocity_distribution()
                changes_made.append("Applied even velocity distribution")
                
            elif rec['action'] == 'fix_velocity':
                # Fix overlapping velocities
                self.velocity_mode_var.set("even")
                self.apply_velocity_distribution()
                changes_made.append("Fixed velocity overlaps")
                
            elif rec['action'] == 'fill_velocity':
                # Fill velocity gaps
                self.velocity_mode_var.set("even")
                self.apply_velocity_distribution()
                changes_made.append("Filled velocity gaps")
                
            elif rec['action'] == 'fix_pitch' and 'layer_index' in rec:
                # Fix pitch mismatch
                layer_index = rec['layer_index']
                if layer_index < len(kg['layers']):
                    old_note = kg['layers'][layer_index]['root_note']
                    kg['layers'][layer_index]['root_note'] = rec['suggested_note']
                    
                    # Track change
                    if self.selected_instrument not in self.mapping_changes:
                        self.mapping_changes[self.selected_instrument] = {}
                    if 'pitch_fixes' not in self.mapping_changes[self.selected_instrument]:
                        self.mapping_changes[self.selected_instrument]['pitch_fixes'] = []
                    self.mapping_changes[self.selected_instrument]['pitch_fixes'].append({
                        'layer': layer_index,
                        'old_note': old_note,
                        'new_note': rec['suggested_note']
                    })
                    
                    changes_made.append(f"Fixed root note for layer {layer_index+1}: {self.midi_to_note(old_note)} → {self.midi_to_note(rec['suggested_note'])}")
                    
            elif rec['action'] == 'range_optimize':
                # Auto-fit range based on root notes
                self.auto_fit_range()
                changes_made.append("Optimized key range")
        
        if changes_made:
            messagebox.showinfo(
                "Auto-Fix Complete", 
                f"Applied {len(changes_made)} fixes:\n\n" + "\n".join(f"• {change}" for change in changes_made),
                parent=dialog
            )
            self.update_keyboard_display()
        else:
            messagebox.showinfo("No Fixes", "No automatic fixes were applied.", parent=dialog)
            
        dialog.destroy()
        
    def on_velocity_mode_changed(self, event=None):
        """Handle velocity distribution mode changes"""
        # This could be expanded to show different controls based on mode
        pass
        
    def apply_velocity_distribution(self):
        """Apply velocity layer distribution"""
        if self.selected_instrument is None or self.selected_instrument >= len(self.keygroups):
            messagebox.showwarning("No Instrument", "Please select an instrument to edit first.", parent=self)
            return
            
        kg = self.keygroups[self.selected_instrument]
        layers = kg['layers']
        
        if len(layers) <= 1:
            messagebox.showinfo("Single Layer", "Instrument has only one layer - no velocity distribution needed.", parent=self)
            return
            
        mode = self.velocity_mode_var.get()
        
        if mode == "even":
            # Distribute velocity ranges evenly
            vel_range = 127 // len(layers)
            for i, layer in enumerate(layers):
                layer['vel_start'] = i * vel_range
                layer['vel_end'] = (i + 1) * vel_range - 1 if i < len(layers) - 1 else 127
                
        elif mode == "dynamic":
            # Dynamic distribution: softer layers get smaller ranges
            total_range = 128
            # Create a curve where later layers (typically louder) get more range
            ratios = [1.0 / (2 ** (len(layers) - i - 1)) for i in range(len(layers))]
            ratio_sum = sum(ratios)
            
            current_vel = 0
            for i, (layer, ratio) in enumerate(zip(layers, ratios)):
                layer_range = int((ratio / ratio_sum) * total_range)
                layer['vel_start'] = current_vel
                layer['vel_end'] = min(127, current_vel + layer_range - 1) if i < len(layers) - 1 else 127
                current_vel += layer_range
                
        # Track changes
        if self.selected_instrument not in self.mapping_changes:
            self.mapping_changes[self.selected_instrument] = {}
        self.mapping_changes[self.selected_instrument]['velocity'] = mode
        
        self.status_var.set(f"Applied {mode} velocity distribution to Instrument {self.selected_instrument}")
        
    def rebuild_key_mappings(self):
        """Rebuild the key mappings after changes"""
        self.key_mappings = {}
        
        for kg in self.keygroups:
            for note in range(kg['low_note'], kg['high_note'] + 1):
                if note not in self.key_mappings:
                    self.key_mappings[note] = []
                self.key_mappings[note].append(kg)
                
    def save_changes(self):
        """Save changes back to the XPM file"""
        if not self.mapping_changes:
            messagebox.showinfo("No Changes", "No changes to save.", parent=self)
            return
            
        if not self.xpm_path or not os.path.exists(self.xpm_path):
            messagebox.showerror("No File", "No XPM file loaded.", parent=self)
            return
            
        try:
            # Create backup
            backup_path = self.xpm_path + ".backup"
            import shutil
            shutil.copy2(self.xpm_path, backup_path)
            
            # Load and modify the XML
            tree = ET.parse(self.xpm_path)
            root = tree.getroot()
            
            # Find the Instruments element
            program = root.find('.//Program')
            if program is not None:
                instruments = program.find('Instruments')
                if instruments is not None:
                    instrument_elements = instruments.findall('Instrument')
                    
                    # Apply changes
                    for inst_index, changes in self.mapping_changes.items():
                        if inst_index < len(instrument_elements):
                            inst_elem = instrument_elements[inst_index]
                            
                            # Apply range changes
                            if 'range' in changes:
                                low_note, high_note = changes['range']
                                
                                low_elem = inst_elem.find('LowNote')
                                if low_elem is not None:
                                    low_elem.text = str(low_note)
                                    
                                high_elem = inst_elem.find('HighNote')
                                if high_elem is not None:
                                    high_elem.text = str(high_note)
                                    
                            # Apply velocity distribution changes
                            if 'velocity' in changes and inst_index < len(self.keygroups):
                                kg = self.keygroups[inst_index]
                                layers_elem = inst_elem.find('Layers')
                                if layers_elem is not None:
                                    layer_elements = layers_elem.findall('Layer')
                                    for i, (layer_elem, layer_data) in enumerate(zip(layer_elements, kg['layers'])):
                                        vel_start_elem = layer_elem.find('VelStart')
                                        if vel_start_elem is not None:
                                            vel_start_elem.text = str(layer_data['vel_start'])
                                            
                                        vel_end_elem = layer_elem.find('VelEnd')
                                        if vel_end_elem is not None:
                                            vel_end_elem.text = str(layer_data['vel_end'])
                                            
                            # Apply pitch fixes
                            if 'pitch_fixes' in changes:
                                kg = self.keygroups[inst_index]
                                layers_elem = inst_elem.find('Layers')
                                if layers_elem is not None:
                                    layer_elements = layers_elem.findall('Layer')
                                    for fix in changes['pitch_fixes']:
                                        layer_idx = fix['layer']
                                        if layer_idx < len(layer_elements):
                                            layer_elem = layer_elements[layer_idx]
                                            root_note_elem = layer_elem.find('RootNote')
                                            if root_note_elem is not None:
                                                root_note_elem.text = str(fix['new_note'])
            
            # Save the modified file
            self.indent_xml_tree(tree)
            tree.write(self.xpm_path, encoding="utf-8", xml_declaration=True)
            
            # Clear changes and reload
            self.mapping_changes = {}
            self.reload_xmp()
            
            messagebox.showinfo("Success", f"Changes saved to {os.path.basename(self.xpm_path)}\nBackup created: {os.path.basename(backup_path)}", parent=self)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save changes:\n{e}", parent=self)
            
    def revert_changes(self):
        """Revert all changes and reload original data"""
        if not self.mapping_changes:
            messagebox.showinfo("No Changes", "No changes to revert.", parent=self)
            return
            
        if messagebox.askyesno("Revert Changes", "Are you sure you want to revert all changes?", parent=self):
            self.mapping_changes = {}
            self.reload_xmp()
            self.status_var.set("All changes reverted.")
            
    def export_as_new(self):
        """Export the modified XPM as a new file"""
        if not self.mapping_changes:
            messagebox.showinfo("No Changes", "No changes to export.", parent=self)
            return
            
        # Ask for new filename
        new_path = filedialog.asksaveasfilename(
            parent=self,
            title="Export Modified XPM As",
            defaultextension=".xpm",
            filetypes=[("XPM Files", "*.xmp"), ("All Files", "*.*")],
            initialdir=os.path.dirname(self.xpm_path) if self.xpm_path else os.path.expanduser("~"),
            initialname=f"{os.path.splitext(os.path.basename(self.xpm_path))[0]}_modified.xpm" if self.xpm_path else "modified.xpm"
        )
        
        if new_path:
            # Save to new location
            original_path = self.xpm_path
            self.xpm_path = new_path
            self.save_changes()
            self.xpm_path = original_path  # Restore original path
            
    def indent_xml_tree(self, tree):
        """Add proper indentation to XML tree"""
        def indent(elem, level=0):
            i = "\n" + level * "  "
            if len(elem):
                if not elem.text or not elem.text.strip():
                    elem.text = i + "  "
                if not elem.tail or not elem.tail.strip():
                    elem.tail = i
                for elem in elem:
                    indent(elem, level + 1)
                if not elem.tail or not elem.tail.strip():
                    elem.tail = i
            else:
                if level and (not elem.tail or not elem.tail.strip()):
                    elem.tail = i
                    
        indent(tree.getroot())
        
    def try_load_current_folder_xpm(self):
        """Try to load the first XPM from the parent's selected folder"""
        if hasattr(self.parent, 'folder_path') and self.parent.folder_path.get():
            folder = self.parent.folder_path.get()
            if os.path.isdir(folder):
                import glob
                xpm_files = glob.glob(os.path.join(folder, "*.xpm"))
                if xpm_files:
                    self.load_xpm(xpm_files[0])
                    
    def browse_xpm(self):
        """Browse for an XPM file"""
        file_path = filedialog.askopenfilename(
            parent=self,
            title="Select XPM File",
            filetypes=[("XPM Files", "*.xpm"), ("All Files", "*.*")],
            initialdir=getattr(self.parent, 'last_browse_path', os.path.expanduser("~"))
        )
        
        if file_path:
            self.load_xpm(file_path)
            
    def reload_xmp(self):
        """Reload the current XPM file"""
        if self.xpm_path and os.path.exists(self.xpm_path):
            self.load_xpm(self.xpm_path)
        else:
            messagebox.showwarning("No File", "No XPM file loaded to reload.", parent=self)
            
    def load_xpm(self, file_path):
        """Load and parse an XPM file"""
        try:
            self.xpm_path = file_path
            self.file_path_var.set(os.path.basename(file_path))
            
            # Parse the XPM file
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Extract keygroups - XPM files use Instrument elements, not Keygroup
            self.keygroups = []
            self.key_mappings = {}
            
            # Look for Instruments within the Program
            program = root.find('.//Program')
            if program is not None:
                instruments = program.find('Instruments')
                if instruments is not None:
                    for i, instrument in enumerate(instruments.findall('Instrument')):
                        kg_info = self.parse_keygroup(instrument, i)
                        if kg_info:
                            self.keygroups.append(kg_info)
                            
                            # Map each MIDI note in the range to this keygroup
                            for note in range(kg_info['low_note'], kg_info['high_note'] + 1):
                                if note not in self.key_mappings:
                                    self.key_mappings[note] = []
                                self.key_mappings[note].append(kg_info)
            
            # Update UI
            self.update_keygroup_combo()
            self.update_keyboard_display()
            
            self.status_var.set(f"Loaded: {len(self.keygroups)} instruments, {len(self.key_mappings)} mapped keys")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load XPM file:\n{e}", parent=self)
            self.status_var.set(f"Error loading file: {e}")
            
    def parse_keygroup(self, instrument_elem, index):
        """Parse an instrument element and extract relevant information"""
        try:
            # Get basic instrument info
            low_note = int(self.get_element_text(instrument_elem, "LowNote", "0"))
            high_note = int(self.get_element_text(instrument_elem, "HighNote", "127"))
            
            # Get layers
            layers = []
            layers_elem = instrument_elem.find("Layers")
            if layers_elem is not None:
                for layer in layers_elem.findall("Layer"):
                    layer_info = {
                        'sample_name': self.get_element_text(layer, "SampleName", "Unknown"),
                        'sample_file': self.get_element_text(layer, "SampleFile", ""),
                        'root_note': int(self.get_element_text(layer, "RootNote", "60")),
                        'vel_start': int(self.get_element_text(layer, "VelStart", "0")),
                        'vel_end': int(self.get_element_text(layer, "VelEnd", "127")),
                        'volume': float(self.get_element_text(layer, "Volume", "1.0")),
                        'pan': float(self.get_element_text(layer, "Pan", "0.5")),
                        'tune': float(self.get_element_text(layer, "Tune", "0.0")),
                    }
                    layers.append(layer_info)
            
            return {
                'index': index,
                'low_note': low_note,
                'high_note': high_note,
                'layers': layers,
                'note_range': f"{self.midi_to_note(low_note)}-{self.midi_to_note(high_note)}"
            }
            
        except Exception as e:
            print(f"Error parsing instrument {index}: {e}")
            return None
            
    def get_element_text(self, parent, tag, default=""):
        """Safely get text from an XML element"""
        elem = parent.find(tag)
        return elem.text if elem is not None and elem.text else default
        
    def midi_to_note(self, midi_num):
        """Convert MIDI number to note name"""
        if midi_num < 0 or midi_num > 127:
            return f"MIDI{midi_num}"
            
        notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        octave = (midi_num // 12) - 1
        note = notes[midi_num % 12]
        return f"{note}{octave}"
        
    def update_keygroup_combo(self):
        """Update the keygroup selection combo"""
        if not self.keygroups:
            self.keygroup_combo['values'] = []
            self.keygroup_var.set("")
            return
            
        values = ["All Instruments"]
        for i, kg in enumerate(self.keygroups):
            layer_names = [layer['sample_name'] for layer in kg['layers'][:2]]  # Show first 2
            layer_str = ", ".join(layer_names)
            if len(kg['layers']) > 2:
                layer_str += f" (+{len(kg['layers'])-2} more)"
            values.append(f"Inst{i}: {kg['note_range']} - {layer_str}")
            
        self.keygroup_combo['values'] = values
        self.keygroup_var.set(values[0])
        
    def on_keygroup_selected(self, event=None):
        """Handle keygroup selection"""
        selection = self.keygroup_var.get()
        if selection.startswith("Inst"):
            # Extract keygroup index
            kg_index = int(selection.split(":")[0][4:])  # Remove "Inst" prefix
            self.selected_keygroup = kg_index
        else:
            self.selected_keygroup = None
            
        self.update_keyboard_display()
        
    def update_keyboard_display(self, event=None):
        """Update the keyboard visualization"""
        if not self.canvas:
            return
            
        self.canvas.delete("all")
        self.key_rects = {}
        self.key_labels = {}
        
        if not self.keygroups:
            self.canvas.create_text(
                400, 200, text="No XPM file loaded", 
                font=("Helvetica", 16), fill="gray"
            )
            return
            
        # Calculate keyboard dimensions
        start_octave = self.octave_start_var.get()
        end_octave = self.octave_end_var.get()
        
        start_midi = (start_octave + 1) * 12  # C of start_octave
        end_midi = min(127, (end_octave + 1) * 12 + 11)  # B of end_octave
        
        # Key dimensions
        white_key_width = 40
        white_key_height = 200
        black_key_width = 25
        black_key_height = 130
        
        # Draw keyboard
        x_offset = 20
        y_offset = 20
        white_x = x_offset
        
        # First pass: draw white keys
        for midi_note in range(start_midi, end_midi + 1):
            if self.is_white_key(midi_note):
                # Determine if this key has mappings
                has_mapping = midi_note in self.key_mappings
                should_highlight = self.should_highlight_key(midi_note)
                
                # Choose color
                if should_highlight:
                    if self.edit_mode and self.selected_instrument is not None:
                        if self.range_selection_start is not None:
                            color = self.RANGE_SELECTION_COLOR
                        else:
                            color = self.EDIT_HIGHLIGHT_COLOR
                    else:
                        color = self.SELECTED_COLOR
                elif has_mapping:
                    color = self.MAPPED_WHITE_COLOR
                else:
                    color = self.WHITE_KEY_COLOR
                    
                # Draw key
                rect = self.canvas.create_rectangle(
                    white_x, y_offset,
                    white_x + white_key_width, y_offset + white_key_height,
                    fill=color, outline="black", width=1
                )
                
                # Add note label
                note_name = self.midi_to_note(midi_note)
                text = self.canvas.create_text(
                    white_x + white_key_width // 2, 
                    y_offset + white_key_height - 15,
                    text=note_name, font=("Arial", 8), anchor="center"
                )
                
                # Store for click detection
                self.key_rects[midi_note] = rect
                self.key_labels[midi_note] = text
                
                # Add mapping indicator
                if has_mapping:
                    self.add_mapping_indicator(midi_note, white_x, y_offset, white_key_width)
                
                white_x += white_key_width
                
        # Second pass: draw black keys
        white_x = x_offset
        for midi_note in range(start_midi, end_midi + 1):
            if self.is_white_key(midi_note):
                # Check if there's a black key after this white key
                black_midi = midi_note + 1
                if black_midi <= end_midi and not self.is_white_key(black_midi):
                    # Draw black key
                    black_x = white_x + white_key_width - black_key_width // 2
                    
                    has_mapping = black_midi in self.key_mappings
                    should_highlight = self.should_highlight_key(black_midi)
                    
                    if should_highlight:
                        if self.edit_mode and self.selected_instrument is not None:
                            if self.range_selection_start is not None:
                                color = self.RANGE_SELECTION_COLOR
                            else:
                                color = self.EDIT_HIGHLIGHT_COLOR
                        else:
                            color = self.SELECTED_COLOR
                    elif has_mapping:
                        color = self.MAPPED_BLACK_COLOR
                    else:
                        color = self.BLACK_KEY_COLOR
                        
                    rect = self.canvas.create_rectangle(
                        black_x, y_offset,
                        black_x + black_key_width, y_offset + black_key_height,
                        fill=color, outline="black", width=1
                    )
                    
                    # Add note label
                    note_name = self.midi_to_note(black_midi)
                    text = self.canvas.create_text(
                        black_x + black_key_width // 2,
                        y_offset + black_key_height - 10,
                        text=note_name, font=("Arial", 7), fill="white", anchor="center"
                    )
                    
                    self.key_rects[black_midi] = rect
                    self.key_labels[black_midi] = text
                    
                    if has_mapping:
                        self.add_mapping_indicator(black_midi, black_x, y_offset, black_key_width)
                
                white_x += white_key_width
                
        # Update canvas scroll region
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
    def is_white_key(self, midi_note):
        """Check if a MIDI note corresponds to a white key"""
        note_in_octave = midi_note % 12
        return note_in_octave in [0, 2, 4, 5, 7, 9, 11]  # C, D, E, F, G, A, B
        
    def should_highlight_key(self, midi_note):
        """Check if a key should be highlighted based on current selection"""
        if self.edit_mode and self.selected_instrument is not None:
            # In edit mode, highlight the selected instrument's range
            if self.selected_instrument < len(self.keygroups):
                kg = self.keygroups[self.selected_instrument]
                if kg['low_note'] <= midi_note <= kg['high_note']:
                    return True
                    
            # Also highlight range selection
            if self.range_selection_start is not None:
                if self.range_selection_end is None:
                    # Just highlight the start
                    return midi_note == self.range_selection_start
                else:
                    # Highlight the range
                    low = min(self.range_selection_start, self.range_selection_end)
                    high = max(self.range_selection_start, self.range_selection_end)
                    return low <= midi_note <= high
                    
        elif self.view_var.get() == "single_instrument" and self.selected_keygroup is not None:
            # Only highlight keys in the selected keygroup
            if midi_note in self.key_mappings:
                for kg in self.key_mappings[midi_note]:
                    if kg['index'] == self.selected_keygroup:
                        return True
            return False
        return False
        
    def add_mapping_indicator(self, midi_note, x, y, width):
        """Add a small indicator showing sample count"""
        if midi_note not in self.key_mappings:
            return
            
        # Count total layers across all keygroups for this note
        total_layers = sum(len(kg['layers']) for kg in self.key_mappings[midi_note])
        
        if total_layers > 0:
            # Small colored circle with layer count
            circle_x = x + width - 8
            circle_y = y + 8
            
            self.canvas.create_oval(
                circle_x - 6, circle_y - 6,
                circle_x + 6, circle_y + 6,
                fill="#FF4500", outline="white", width=1
            )
            
            self.canvas.create_text(
                circle_x, circle_y,
                text=str(total_layers), font=("Arial", 8, "bold"),
                fill="white", anchor="center"
            )
            
    def on_key_click(self, event):
        """Handle keyboard key clicks"""
        clicked_item = self.canvas.find_closest(event.x, event.y)[0]
        
        # Find which MIDI note was clicked
        clicked_midi = None
        for midi_note, rect in self.key_rects.items():
            if rect == clicked_item:
                clicked_midi = midi_note
                break
                
        if clicked_midi is not None:
            if self.edit_mode and self.selected_instrument is not None:
                self.handle_edit_mode_click(clicked_midi)
            else:
                self.show_key_details(clicked_midi)
                
    def handle_edit_mode_click(self, midi_note):
        """Handle clicks in edit mode for range selection"""
        if self.range_selection_start is None:
            # First click - set start
            self.range_selection_start = midi_note
            self.status_var.set(f"Range start: {self.midi_to_note(midi_note)} (MIDI {midi_note}). Click HIGH note to complete range...")
        elif self.range_selection_end is None:
            # Second click - set end and apply
            self.range_selection_end = midi_note
            
            # Ensure start <= end
            low_note = min(self.range_selection_start, self.range_selection_end)
            high_note = max(self.range_selection_start, self.range_selection_end)
            
            # Update the range controls
            self.new_low_note_var.set(low_note)
            self.new_high_note_var.set(high_note)
            
            # Ask if user wants to apply
            range_str = f"{self.midi_to_note(low_note)}-{self.midi_to_note(high_note)} (MIDI {low_note}-{high_note})"
            if messagebox.askyesno(
                "Apply Range", 
                f"Set Instrument {self.selected_instrument} range to:\n{range_str}?",
                parent=self
            ):
                self.apply_range_change()
            
            # Reset selection
            self.range_selection_start = None
            self.range_selection_end = None
            self.status_var.set("Edit Mode: Range applied. Click 'Select on Keyboard' to select another range.")
        else:
            # Reset and start over
            self.range_selection_start = midi_note
            self.range_selection_end = None
            self.status_var.set(f"Range start: {self.midi_to_note(midi_note)} (MIDI {midi_note}). Click HIGH note to complete range...")
            
    def on_mouse_motion(self, event):
        """Handle mouse motion for tooltips"""
        item = self.canvas.find_closest(event.x, event.y)[0]
        
        # Find which MIDI note is under cursor
        hovered_midi = None
        for midi_note, rect in self.key_rects.items():
            if rect == item:
                hovered_midi = midi_note
                break
                
        if hovered_midi is not None and hovered_midi in self.key_mappings:
            # Show basic info in status bar
            kg_count = len(self.key_mappings[hovered_midi])
            layer_count = sum(len(kg['layers']) for kg in self.key_mappings[hovered_midi])
            note_name = self.midi_to_note(hovered_midi)
            self.status_var.set(
                f"{note_name} (MIDI {hovered_midi}): {kg_count} instrument(s), {layer_count} layer(s)"
            )
        else:
            self.status_var.set("Ready. Click a key to see sample details.")
            
    def show_key_details(self, midi_note):
        """Show detailed information about a specific key"""
        self.details_text.config(state="normal")
        self.details_text.delete(1.0, tk.END)
        
        note_name = self.midi_to_note(midi_note)
        self.details_text.insert(tk.END, f"🎹 KEY: {note_name} (MIDI {midi_note})\n")
        self.details_text.insert(tk.END, "=" * 50 + "\n\n")
        
        if midi_note not in self.key_mappings:
            self.details_text.insert(tk.END, "❌ No samples mapped to this key.\n")
        else:
            instruments = self.key_mappings[midi_note]
            total_layers = sum(len(kg['layers']) for kg in instruments)
            
            self.details_text.insert(tk.END, f"📊 MAPPING SUMMARY:\n")
            self.details_text.insert(tk.END, f"   • {len(instruments)} instrument(s)\n")
            self.details_text.insert(tk.END, f"   • {total_layers} total layer(s)\n\n")
            
            for kg in instruments:
                self.details_text.insert(tk.END, f"🎛️  INSTRUMENT {kg['index']}:\n")
                self.details_text.insert(tk.END, f"   Range: {kg['note_range']} (MIDI {kg['low_note']}-{kg['high_note']})\n")
                self.details_text.insert(tk.END, f"   Layers: {len(kg['layers'])}\n\n")
                
                for i, layer in enumerate(kg['layers']):
                    self.details_text.insert(tk.END, f"   🎵 Layer {i+1}:\n")
                    self.details_text.insert(tk.END, f"      Sample: {layer['sample_name']}\n")
                    
                    if layer['sample_file']:
                        file_name = os.path.basename(layer['sample_file'])
                        self.details_text.insert(tk.END, f"      File: {file_name}\n")
                        
                    self.details_text.insert(tk.END, f"      Root Note: {self.midi_to_note(layer['root_note'])} (MIDI {layer['root_note']})\n")
                    self.details_text.insert(tk.END, f"      Velocity: {layer['vel_start']}-{layer['vel_end']}\n")
                    self.details_text.insert(tk.END, f"      Volume: {layer['volume']:.2f}\n")
                    self.details_text.insert(tk.END, f"      Pan: {layer['pan']:.2f}\n")
                    
                    if layer['tune'] != 0.0:
                        self.details_text.insert(tk.END, f"      Tune: {layer['tune']:+.2f} cents\n")
                        
                    self.details_text.insert(tk.END, "\n")
                    
                self.details_text.insert(tk.END, "-" * 30 + "\n\n")
        
        self.details_text.config(state="disabled")
        
    def try_load_current_folder_xpm(self):
        """Try to load the first XPM from the parent's selected folder"""
        if hasattr(self.parent, 'folder_path') and self.parent.folder_path.get():
            folder = self.parent.folder_path.get()
            if os.path.isdir(folder):
                import glob
                xpm_files = glob.glob(os.path.join(folder, "*.xpm"))
                if xpm_files:
                    self.load_xpm(xpm_files[0])


if __name__ == "__main__":
    # Test window
    root = tk.Tk()
    root.withdraw()
    
    class MockParent:
        def __init__(self):
            self.folder_path = tk.StringVar()
            self.last_browse_path = os.path.expanduser("~")
    
    mock_parent = MockParent()
    window = KeyboardMapperWindow(mock_parent)
    window.mainloop()
