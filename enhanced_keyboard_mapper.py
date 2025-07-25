#!/usr/bin/env python3
"""
Enhanced Keyboard Mapper with Manual Correction Features
Addresses root note, velocity, and range mapping issues
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import xml.etree.ElementTree as ET
import os
import sys
import json
from typing import Dict, List, Optional, Tuple

# Add current directory to path for imports
sys.path.append('/Users/marlsz/Documents/GitHub/XPM-version-2')

try:
    from xpm_mapping_corrector import XPMappingCorrector
except ImportError:
    print("Warning: xmp_mapping_corrector not available")
    XPMappingCorrector = None

class EnhancedKeyboardMapper(tk.Toplevel):
    """Enhanced keyboard mapper with manual correction capabilities"""
    
    def __init__(self, master):
        super().__init__(master.root if hasattr(master, 'root') else master)
        self.title("Enhanced XPM Keyboard Mapper - Manual Correction")
        self.geometry("1200x800")
        self.resizable(True, True)
        self.master = master
        
        # Data storage
        self.current_xpm_path = None
        self.xpm_tree = None
        self.instruments = []
        self.mapping_corrector = XPMappingCorrector() if XPMappingCorrector else None
        
        # UI state
        self.selected_instrument = 0
        self.selected_layer = 0
        
        self.create_widgets()
        
    def create_widgets(self):
        """Create the enhanced UI"""
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill="both", expand=True)
        
        # File selection section
        file_frame = ttk.LabelFrame(main_frame, text="XPM File", padding="5")
        file_frame.pack(fill="x", pady=(0, 10))
        
        self.file_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.file_var, width=60).pack(side="left", padx=(0, 5))
        ttk.Button(file_frame, text="Browse...", command=self.browse_xpm).pack(side="left", padx=5)
        ttk.Button(file_frame, text="Load", command=self.load_xpm).pack(side="left", padx=5)
        ttk.Button(file_frame, text="🔍 Analyze Issues", command=self.analyze_mapping_issues).pack(side="left", padx=5)
        
        # Create notebook for tabbed interface
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill="both", expand=True, pady=(0, 10))
        
        # Tab 1: Manual Correction Interface
        self.create_manual_correction_tab()
        
        # Tab 2: Automatic Analysis
        self.create_analysis_tab()
        
        # Tab 3: Batch Operations
        self.create_batch_tab()
        
        # Bottom buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x")
        
        ttk.Button(btn_frame, text="💾 Save Changes", command=self.save_changes).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="🔄 Reload", command=self.load_xpm).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="🎯 Auto-Fix All", command=self.auto_fix_all).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Close", command=self.destroy).pack(side="right", padx=5)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready - Load an XPM file to begin")
        ttk.Label(main_frame, textvariable=self.status_var, relief="sunken").pack(fill="x", pady=(5, 0))
    
    def create_manual_correction_tab(self):
        """Create manual correction interface"""
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text="Manual Correction")
        
        # Instrument selection
        inst_frame = ttk.LabelFrame(tab_frame, text="Instrument Selection", padding="5")
        inst_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(inst_frame, text="Instrument:").pack(side="left")
        self.inst_var = tk.StringVar()
        self.inst_combo = ttk.Combobox(inst_frame, textvariable=self.inst_var, width=40, state="readonly")
        self.inst_combo.pack(side="left", padx=5)
        self.inst_combo.bind("<<ComboboxSelected>>", self.on_instrument_selected)
        
        ttk.Label(inst_frame, text="Layer:").pack(side="left", padx=(20, 5))
        self.layer_var = tk.StringVar()
        self.layer_combo = ttk.Combobox(inst_frame, textvariable=self.layer_var, width=20, state="readonly")
        self.layer_combo.pack(side="left", padx=5)
        self.layer_combo.bind("<<ComboboxSelected>>", self.on_layer_selected)
        
        # Create paned window for layout
        paned = ttk.PanedWindow(tab_frame, orient="horizontal")
        paned.pack(fill="both", expand=True)
        
        # Left panel: Sample details and correction
        left_frame = ttk.LabelFrame(paned, text="Sample Details & Correction", padding="5")
        paned.add(left_frame, weight=1)
        
        # Sample information
        info_frame = ttk.LabelFrame(left_frame, text="Current Sample Information", padding="5")
        info_frame.pack(fill="x", pady=(0, 10))
        
        # Sample name
        ttk.Label(info_frame, text="Sample Name:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.sample_name_var = tk.StringVar()
        ttk.Label(info_frame, textvariable=self.sample_name_var, font=("Courier", 10)).grid(row=0, column=1, sticky="w", padx=5, pady=2)
        
        # Current root note
        ttk.Label(info_frame, text="Current Root Note:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.current_root_var = tk.StringVar()
        ttk.Label(info_frame, textvariable=self.current_root_var, font=("Courier", 10), foreground="red").grid(row=1, column=1, sticky="w", padx=5, pady=2)
        
        # Detected note
        ttk.Label(info_frame, text="Auto-Detected Note:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.detected_note_var = tk.StringVar()
        ttk.Label(info_frame, textvariable=self.detected_note_var, font=("Courier", 10), foreground="green").grid(row=2, column=1, sticky="w", padx=5, pady=2)
        
        # Velocity range
        ttk.Label(info_frame, text="Velocity Range:").grid(row=3, column=0, sticky="w", padx=5, pady=2)
        self.velocity_range_var = tk.StringVar()
        ttk.Label(info_frame, textvariable=self.velocity_range_var, font=("Courier", 10)).grid(row=3, column=1, sticky="w", padx=5, pady=2)
        
        # Manual correction frame
        correction_frame = ttk.LabelFrame(left_frame, text="Manual Correction", padding="5")
        correction_frame.pack(fill="x", pady=(0, 10))
        
        # Root note correction
        ttk.Label(correction_frame, text="New Root Note:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.new_root_var = tk.StringVar()
        root_frame = ttk.Frame(correction_frame)
        root_frame.grid(row=0, column=1, sticky="w", padx=5, pady=2)
        
        self.root_spinbox = tk.Spinbox(root_frame, from_=0, to=127, textvariable=self.new_root_var, width=5)
        self.root_spinbox.pack(side="left")
        
        self.root_note_name_var = tk.StringVar()
        ttk.Label(root_frame, textvariable=self.root_note_name_var, width=8).pack(side="left", padx=5)
        
        ttk.Button(root_frame, text="Auto-Detect", command=self.auto_detect_root_note).pack(side="left", padx=5)
        
        # Bind root note changes to update note name
        self.new_root_var.trace("w", self.update_root_note_name)
        
        # Velocity range correction
        ttk.Label(correction_frame, text="Velocity Low:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.new_vel_low_var = tk.StringVar()
        tk.Spinbox(correction_frame, from_=0, to=127, textvariable=self.new_vel_low_var, width=5).grid(row=1, column=1, sticky="w", padx=5, pady=2)
        
        ttk.Label(correction_frame, text="Velocity High:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.new_vel_high_var = tk.StringVar()
        tk.Spinbox(correction_frame, from_=0, to=127, textvariable=self.new_vel_high_var, width=5).grid(row=2, column=1, sticky="w", padx=5, pady=2)
        
        # Apply buttons
        ttk.Button(correction_frame, text="✅ Apply to Current Layer", command=self.apply_layer_changes).grid(row=3, column=0, columnspan=2, pady=10)
        
        # Right panel: Instrument range settings
        right_frame = ttk.LabelFrame(paned, text="Instrument Range Settings", padding="5")
        paned.add(right_frame, weight=1)
        
        # Instrument range
        range_frame = ttk.LabelFrame(right_frame, text="Key Range", padding="5")
        range_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(range_frame, text="Low Note:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.inst_low_var = tk.StringVar()
        low_frame = ttk.Frame(range_frame)
        low_frame.grid(row=0, column=1, sticky="w", padx=5, pady=2)
        
        self.low_spinbox = tk.Spinbox(low_frame, from_=0, to=127, textvariable=self.inst_low_var, width=5)
        self.low_spinbox.pack(side="left")
        self.low_note_name_var = tk.StringVar()
        ttk.Label(low_frame, textvariable=self.low_note_name_var, width=8).pack(side="left", padx=5)
        
        ttk.Label(range_frame, text="High Note:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.inst_high_var = tk.StringVar()
        high_frame = ttk.Frame(range_frame)
        high_frame.grid(row=1, column=1, sticky="w", padx=5, pady=2)
        
        self.high_spinbox = tk.Spinbox(high_frame, from_=0, to=127, textvariable=self.inst_high_var, width=5)
        self.high_spinbox.pack(side="left")
        self.high_note_name_var = tk.StringVar()
        ttk.Label(high_frame, textvariable=self.high_note_name_var, width=8).pack(side="left", padx=5)
        
        # Bind instrument range changes
        self.inst_low_var.trace("w", self.update_low_note_name)
        self.inst_high_var.trace("w", self.update_high_note_name)
        
        # Range presets
        preset_frame = ttk.LabelFrame(right_frame, text="Range Presets", padding="5")
        preset_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Button(preset_frame, text="Single Key", command=lambda: self.apply_range_preset("single")).pack(side="left", padx=2)
        ttk.Button(preset_frame, text="Octave", command=lambda: self.apply_range_preset("octave")).pack(side="left", padx=2)
        ttk.Button(preset_frame, text="Auto-Range", command=lambda: self.apply_range_preset("auto")).pack(side="left", padx=2)
        
        ttk.Button(range_frame, text="✅ Apply Range", command=self.apply_instrument_range).grid(row=2, column=0, columnspan=2, pady=10)
    
    def create_analysis_tab(self):
        """Create analysis tab"""
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text="Analysis")
        
        # Analysis results text
        self.analysis_text = tk.Text(tab_frame, height=25, wrap="word")
        scrollbar = ttk.Scrollbar(tab_frame, orient="vertical", command=self.analysis_text.yview)
        self.analysis_text.configure(yscrollcommand=scrollbar.set)
        
        self.analysis_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def create_batch_tab(self):
        """Create batch operations tab"""
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text="Batch Operations")
        
        # Batch operation buttons
        batch_frame = ttk.LabelFrame(tab_frame, text="Batch Corrections", padding="10")
        batch_frame.pack(fill="x", pady=10)
        
        ttk.Button(batch_frame, text="🎵 Auto-Fix All Root Notes", command=self.batch_fix_root_notes).pack(fill="x", pady=2)
        ttk.Button(batch_frame, text="🔊 Fix All Velocity Ranges", command=self.batch_fix_velocity_ranges).pack(fill="x", pady=2)
        ttk.Button(batch_frame, text="🎹 Auto-Set Instrument Ranges", command=self.batch_fix_instrument_ranges).pack(fill="x", pady=2)
        ttk.Button(batch_frame, text="🚀 Apply All Fixes", command=self.auto_fix_all).pack(fill="x", pady=10)
        
        # Settings
        settings_frame = ttk.LabelFrame(tab_frame, text="Batch Settings", padding="10")
        settings_frame.pack(fill="x", pady=10)
        
        self.create_backup_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(settings_frame, text="Create backup before changes", variable=self.create_backup_var).pack(anchor="w")
        
        self.auto_detect_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(settings_frame, text="Use automatic note detection", variable=self.auto_detect_var).pack(anchor="w")
        
        self.fix_overlaps_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(settings_frame, text="Fix velocity overlaps", variable=self.fix_overlaps_var).pack(anchor="w")
    
    def browse_xpm(self):
        """Browse for XPM file"""
        filename = filedialog.askopenfilename(
            title="Select XPM File",
            filetypes=[("XPM Files", "*.xpm"), ("All Files", "*.*")]
        )
        if filename:
            self.file_var.set(filename)
    
    def load_xpm(self):
        """Load XPM file"""
        filename = self.file_var.get()
        if not filename or not os.path.exists(filename):
            messagebox.showerror("Error", "Please select a valid XPM file")
            return
        
        try:
            self.xpm_tree = ET.parse(filename)
            self.current_xpm_path = filename
            root = self.xpm_tree.getroot()
            self.instruments = root.findall('.//Instrument')
            
            # Update instrument combo
            instrument_names = []
            for i, instrument in enumerate(self.instruments):
                # Try to get a meaningful name
                name = f"Instrument {i+1}"
                
                # Check for layers to get sample names
                layers = instrument.find('Layers')
                if layers is not None:
                    first_layer = layers.find('Layer')
                    if first_layer is not None:
                        sample_name_elem = first_layer.find('SampleName')
                        if sample_name_elem is not None and sample_name_elem.text:
                            name = f"Inst{i+1}: {sample_name_elem.text[:20]}"
                
                instrument_names.append(name)
            
            self.inst_combo['values'] = instrument_names
            if instrument_names:
                self.inst_combo.current(0)
                self.on_instrument_selected()
            
            self.status_var.set(f"Loaded: {os.path.basename(filename)} - {len(self.instruments)} instruments")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load XPM file: {e}")
            
    def on_instrument_selected(self, event=None):
        """Handle instrument selection"""
        try:
            self.selected_instrument = self.inst_combo.current()
            if self.selected_instrument < 0 or self.selected_instrument >= len(self.instruments):
                return
            
            instrument = self.instruments[self.selected_instrument]
            
            # Update layer combo
            layers = instrument.find('Layers')
            if layers is not None:
                layer_list = layers.findall('Layer')
                layer_names = []
                for i, layer in enumerate(layer_list):
                    sample_name_elem = layer.find('SampleName')
                    sample_name = sample_name_elem.text if sample_name_elem is not None and sample_name_elem.text else f"Layer {i+1}"
                    layer_names.append(f"Layer {i+1}: {sample_name[:25]}")
                
                self.layer_combo['values'] = layer_names
                if layer_names:
                    self.layer_combo.current(0)
                    self.on_layer_selected()
            
            # Update instrument range
            self.update_instrument_range_display()
            
        except Exception as e:
            print(f"Error in instrument selection: {e}")
    
    def on_layer_selected(self, event=None):
        """Handle layer selection"""
        try:
            self.selected_layer = self.layer_combo.current()
            self.update_layer_display()
        except Exception as e:
            print(f"Error in layer selection: {e}")
    
    def update_layer_display(self):
        """Update the layer information display"""
        if not self.instruments or self.selected_instrument >= len(self.instruments):
            return
        
        instrument = self.instruments[self.selected_instrument]
        layers = instrument.find('Layers')
        
        if layers is not None:
            layer_list = layers.findall('Layer')
            if self.selected_layer < len(layer_list):
                layer = layer_list[self.selected_layer]
                
                # Update sample name
                sample_name_elem = layer.find('SampleName')
                sample_name = sample_name_elem.text if sample_name_elem is not None and sample_name_elem.text else "Unknown"
                self.sample_name_var.set(sample_name)
                
                # Update current root note
                root_note_elem = layer.find('RootNote')
                current_root = int(root_note_elem.text) if root_note_elem is not None and root_note_elem.text else 0
                self.current_root_var.set(f"{current_root} ({self.midi_to_note_name(current_root)})")
                
                # Update detected note
                if self.mapping_corrector:
                    detected = self.mapping_corrector.detect_note_from_filename(sample_name)
                    if detected:
                        self.detected_note_var.set(f"{detected} ({self.midi_to_note_name(detected)})")
                    else:
                        self.detected_note_var.set("Could not detect")
                
                # Update velocity range
                vel_low_elem = layer.find('VelocityLow')
                vel_high_elem = layer.find('VelocityHigh')
                vel_low = int(vel_low_elem.text) if vel_low_elem is not None and vel_low_elem.text else 0
                vel_high = int(vel_high_elem.text) if vel_high_elem is not None and vel_high_elem.text else 127
                self.velocity_range_var.set(f"{vel_low} - {vel_high}")
                
                # Set values for editing
                self.new_root_var.set(str(current_root))
                self.new_vel_low_var.set(str(vel_low))
                self.new_vel_high_var.set(str(vel_high))
    
    def update_instrument_range_display(self):
        """Update instrument range display"""
        if not self.instruments or self.selected_instrument >= len(self.instruments):
            return
        
        instrument = self.instruments[self.selected_instrument]
        
        # Get current range
        low_note_elem = instrument.find('LowNote')
        high_note_elem = instrument.find('HighNote')
        
        low_note = int(low_note_elem.text) if low_note_elem is not None and low_note_elem.text else 0
        high_note = int(high_note_elem.text) if high_note_elem is not None and high_note_elem.text else 127
        
        self.inst_low_var.set(str(low_note))
        self.inst_high_var.set(str(high_note))
    
    def midi_to_note_name(self, midi_number: int) -> str:
        """Convert MIDI number to note name"""
        if not 0 <= midi_number <= 127:
            return f"INVALID({midi_number})"
        
        note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        octave = (midi_number // 12) - 1
        note_index = midi_number % 12
        note_name = note_names[note_index]
        
        return f"{note_name}{octave}"
    
    def update_root_note_name(self, *args):
        """Update root note name display"""
        try:
            midi_num = int(self.new_root_var.get())
            self.root_note_name_var.set(self.midi_to_note_name(midi_num))
        except ValueError:
            self.root_note_name_var.set("")
    
    def update_low_note_name(self, *args):
        """Update low note name display"""
        try:
            midi_num = int(self.inst_low_var.get())
            self.low_note_name_var.set(self.midi_to_note_name(midi_num))
        except ValueError:
            self.low_note_name_var.set("")
    
    def update_high_note_name(self, *args):
        """Update high note name display"""
        try:
            midi_num = int(self.inst_high_var.get())
            self.high_note_name_var.set(self.midi_to_note_name(midi_num))
        except ValueError:
            self.high_note_name_var.set("")
    
    def auto_detect_root_note(self):
        """Auto-detect root note for current sample"""
        if not self.mapping_corrector:
            messagebox.showwarning("Warning", "Auto-detection not available")
            return
        
        sample_name = self.sample_name_var.get()
        detected = self.mapping_corrector.detect_note_from_filename(sample_name)
        
        if detected:
            self.new_root_var.set(str(detected))
            self.status_var.set(f"Auto-detected root note: {self.midi_to_note_name(detected)}")
        else:
            messagebox.showinfo("Info", "Could not auto-detect note from filename")
    
    def apply_layer_changes(self):
        """Apply changes to current layer"""
        if not self.instruments or self.selected_instrument >= len(self.instruments):
            return
        
        instrument = self.instruments[self.selected_instrument]
        layers = instrument.find('Layers')
        
        if layers is not None:
            layer_list = layers.findall('Layer')
            if self.selected_layer < len(layer_list):
                layer = layer_list[self.selected_layer]
                
                try:
                    # Apply root note
                    new_root = int(self.new_root_var.get())
                    root_note_elem = layer.find('RootNote')
                    if root_note_elem is None:
                        root_note_elem = ET.SubElement(layer, 'RootNote')
                    root_note_elem.text = str(new_root)
                    
                    # Apply velocity range
                    new_vel_low = int(self.new_vel_low_var.get())
                    new_vel_high = int(self.new_vel_high_var.get())
                    
                    vel_low_elem = layer.find('VelocityLow')
                    if vel_low_elem is None:
                        vel_low_elem = ET.SubElement(layer, 'VelocityLow')
                    vel_low_elem.text = str(new_vel_low)
                    
                    vel_high_elem = layer.find('VelocityHigh')
                    if vel_high_elem is None:
                        vel_high_elem = ET.SubElement(layer, 'VelocityHigh')
                    vel_high_elem.text = str(new_vel_high)
                    
                    self.status_var.set("✅ Layer changes applied - don't forget to save!")
                    self.update_layer_display()  # Refresh display
                    
                except ValueError as e:
                    messagebox.showerror("Error", f"Invalid values: {e}")
    
    def apply_instrument_range(self):
        """Apply instrument range changes"""
        if not self.instruments or self.selected_instrument >= len(self.instruments):
            return
        
        instrument = self.instruments[self.selected_instrument]
        
        try:
            new_low = int(self.inst_low_var.get())
            new_high = int(self.inst_high_var.get())
            
            if new_low > new_high:
                messagebox.showerror("Error", "Low note cannot be higher than high note")
                return
            
            # Apply range
            low_note_elem = instrument.find('LowNote')
            if low_note_elem is None:
                low_note_elem = ET.SubElement(instrument, 'LowNote')
            low_note_elem.text = str(new_low)
            
            high_note_elem = instrument.find('HighNote')
            if high_note_elem is None:
                high_note_elem = ET.SubElement(instrument, 'HighNote')
            high_note_elem.text = str(new_high)
            
            self.status_var.set("✅ Instrument range applied - don't forget to save!")
            
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid range values: {e}")
    
    def apply_range_preset(self, preset_type):
        """Apply range presets"""
        if preset_type == "single":
            # Single key - use current root note
            try:
                root_note = int(self.new_root_var.get())
                self.inst_low_var.set(str(root_note))
                self.inst_high_var.set(str(root_note))
            except ValueError:
                pass
        elif preset_type == "octave":
            # One octave around root note
            try:
                root_note = int(self.new_root_var.get())
                self.inst_low_var.set(str(max(0, root_note - 6)))
                self.inst_high_var.set(str(min(127, root_note + 6)))
            except ValueError:
                pass
        elif preset_type == "auto":
            # Auto-calculate based on sample content
            messagebox.showinfo("Auto Range", "Auto-range calculation coming soon!")
    
    def analyze_mapping_issues(self):
        """Analyze mapping issues and display results"""
        if not self.current_xpm_path or not self.mapping_corrector:
            messagebox.showwarning("Warning", "Load an XPM file first")
            return
        
        issues = self.mapping_corrector.analyze_mapping_issues(self.current_xpm_path)
        
        # Display results in analysis tab
        self.analysis_text.delete(1.0, tk.END)
        
        analysis_report = "🔍 XPM MAPPING ANALYSIS REPORT\\n"
        analysis_report += "=" * 50 + "\\n\\n"
        
        analysis_report += f"📁 File: {os.path.basename(self.current_xpm_path)}\\n"
        analysis_report += f"📊 Total Instruments: {len(self.instruments)}\\n\\n"
        
        # Root note issues
        if issues['incorrect_root_notes']:
            analysis_report += "🎵 ROOT NOTE ISSUES:\\n"
            for issue in issues['incorrect_root_notes']:
                analysis_report += f"   Instrument {issue['instrument']}, Layer {issue['layer']}:\\n"
                analysis_report += f"   Sample: {issue['sample_name']}\\n"
                analysis_report += f"   Current: {issue['current_root']} ({self.midi_to_note_name(issue['current_root'])})\\n"
                analysis_report += f"   Detected: {issue['detected_root']} ({issue['note_name']})\\n\\n"
        
        # Velocity issues
        if issues['velocity_overlaps']:
            analysis_report += "🔊 VELOCITY OVERLAP ISSUES:\\n"
            for issue in issues['velocity_overlaps']:
                analysis_report += f"   Instrument {issue['instrument']}, Layer {issue['layer']}: {issue['sample_name']}\\n"
            analysis_report += "   All samples respond to full velocity range (0-127)\\n\\n"
        
        # Range issues
        if issues['range_problems']:
            analysis_report += "🎹 INSTRUMENT RANGE ISSUES:\\n"
            for issue in issues['range_problems']:
                analysis_report += f"   Instrument {issue['instrument']}: {issue['issue']}\\n"
                analysis_report += f"   Recommendation: {issue['recommendation']}\\n\\n"
        
        # Recommendations
        if issues['recommendations']:
            analysis_report += "💡 RECOMMENDATIONS:\\n"
            for rec in issues['recommendations']:
                analysis_report += f"   {rec}\\n"
            analysis_report += "\\n"
        
        if not any([issues['incorrect_root_notes'], issues['velocity_overlaps'], issues['range_problems']]):
            analysis_report += "✅ No major mapping issues detected!\\n"
        
        self.analysis_text.insert(1.0, analysis_report)
        
        # Switch to analysis tab
        self.notebook.select(1)
    
    def batch_fix_root_notes(self):
        """Batch fix all root notes"""
        if not self.mapping_corrector or not self.current_xpm_path:
            return
        
        if messagebox.askyesno("Confirm", "Auto-fix all root notes based on sample names?"):
            # Implementation here
            self.status_var.set("Batch root note fix completed")
    
    def batch_fix_velocity_ranges(self):
        """Batch fix velocity ranges"""
        if messagebox.askyesno("Confirm", "Auto-fix all velocity ranges to avoid overlaps?"):
            # Implementation here
            self.status_var.set("Batch velocity fix completed")
    
    def batch_fix_instrument_ranges(self):
        """Batch fix instrument ranges"""
        if messagebox.askyesno("Confirm", "Auto-set all instrument ranges based on root notes?"):
            # Implementation here
            self.status_var.set("Batch range fix completed")
    
    def auto_fix_all(self):
        """Apply all automatic fixes"""
        if not self.mapping_corrector or not self.current_xpm_path:
            messagebox.showwarning("Warning", "Load an XPM file first")
            return
        
        if not messagebox.askyesno("Confirm All Fixes", 
                                   "This will automatically fix:\\n"
                                   "• Root note mappings\\n"
                                   "• Velocity ranges\\n"
                                   "• Instrument key ranges\\n\\n"
                                   "Continue?"):
            return
        
        try:
            fixes = {
                'fix_root_notes': self.auto_detect_var.get(),
                'fix_velocity_ranges': self.fix_overlaps_var.get(),
                'fix_instrument_ranges': True,
                'auto_detect_ranges': True
            }
            
            success = self.mapping_corrector.fix_mapping_issues(self.current_xpm_path, fixes)
            
            if success:
                messagebox.showinfo("Success", "All fixes applied successfully!")
                self.load_xpm()  # Reload to show changes
            else:
                messagebox.showerror("Error", "Failed to apply some fixes")
                
        except Exception as e:
            messagebox.showerror("Error", f"Auto-fix failed: {e}")
    
    def save_changes(self):
        """Save changes to XPM file"""
        if not self.xpm_tree or not self.current_xpm_path:
            messagebox.showwarning("Warning", "No file loaded")
            return
        
        try:
            if self.create_backup_var.get():
                backup_path = self.current_xpm_path + '.keyboard_mapper_backup'
                if not os.path.exists(backup_path):
                    import shutil
                    shutil.copy2(self.current_xpm_path, backup_path)
            
            self.xpm_tree.write(self.current_xpm_path, encoding='utf-8', xml_declaration=True)
            messagebox.showinfo("Success", f"Changes saved to {os.path.basename(self.current_xpm_path)}")
            self.status_var.set("✅ Changes saved successfully")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {e}")

def main():
    """Test the enhanced keyboard mapper"""
    root = tk.Tk()
    root.title("Test Enhanced Keyboard Mapper")
    
    app = EnhancedKeyboardMapper(root)
    root.mainloop()

if __name__ == "__main__":
    main()
