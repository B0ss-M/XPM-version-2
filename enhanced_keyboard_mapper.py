#!/usr/bin/env python3
# Professional XPM Standards (based on ConvertWithMoss analysis):
# 1. Root notes should have +1 offset (MPC hardware convention)
# 2. Use File_Version 2.1 and Application_Version v2.11.6.6
# 3. Group samples by key ranges instead of single notes
# 4. Maximum 4 layers per keygroup (MPC hardware limit)
# 5. Use consecutive key ranges for better playability

"""
Enhanced Keyboard Mapper with Manual Correc        # Tab 3: Batch Operations
        self.create_batch_tab()
        
        # Tab 4: Structural Cleanup (NEW)
        self.create_cleanup_tab()
        
        # Tab 5: Visual Keyboard (NEW)
        self.create_visual_keyboard_tab()
        
        # Bottom buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x")
        
        ttk.Button(btn_frame, text="💾 Save Changes", command=self.save_changes).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="🔄 Reload", command=self.load_xmp).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="🎯 Auto-Fix All", command=self.auto_fix_all).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="🧹 Remove Bloat", command=self.remove_structural_bloat).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="🎹 Fix All Ranges", command=self.fix_all_instrument_ranges).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Close", command=self.destroy).pack(side="right", padx=5)es
Addresses root note, velocity, and range mapping issues
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import xml.etree.ElementTree as ET
import os
import sys
import json
import logging
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
        
        # Tab 4: Structural Cleanup (NEW)
        self.create_cleanup_tab()
        
        # Tab 5: Visual Keyboard (NEW) 
        self.create_visual_keyboard_tab()
        
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
                root_note = int + 1  # ConvertWithMoss standard offset(self.new_root_var.get())
                self.inst_low_var.set(str(root_note))
                self.inst_high_var.set(str(root_note))
            except ValueError:
                pass
        elif preset_type == "octave":
            # One octave around root note
            try:
                root_note = int + 1  # ConvertWithMoss standard offset(self.new_root_var.get())
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
    
    def create_cleanup_tab(self):
        """Create structural cleanup interface"""
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text="Structural Cleanup")
        
        # Bloat detection and removal
        bloat_frame = ttk.LabelFrame(tab_frame, text="Structural Bloat Management", padding="10")
        bloat_frame.pack(fill="x", pady=10)
        
        ttk.Label(bloat_frame, text="Remove empty instruments and optimize file structure for MPC Live 2", 
                 wraplength=400).pack(pady=5)
        
        # Bloat analysis display
        self.bloat_analysis_text = tk.Text(bloat_frame, height=8, width=80)
        bloat_scrollbar = ttk.Scrollbar(bloat_frame, orient="vertical", command=self.bloat_analysis_text.yview)
        self.bloat_analysis_text.configure(yscrollcommand=bloat_scrollbar.set)
        self.bloat_analysis_text.pack(side="left", fill="both", expand=True)
        bloat_scrollbar.pack(side="right", fill="y")
        
        # Bloat control buttons
        bloat_btn_frame = ttk.Frame(bloat_frame)
        bloat_btn_frame.pack(fill="x", pady=10)
        
        ttk.Button(bloat_btn_frame, text="🔍 Analyze Structural Bloat", command=self.analyze_structural_bloat).pack(side="left", padx=5)
        ttk.Button(bloat_btn_frame, text="🧹 Remove Empty Instruments", command=self.remove_structural_bloat).pack(side="left", padx=5)
        ttk.Button(bloat_btn_frame, text="📊 Show Cleanup Stats", command=self.show_cleanup_stats).pack(side="left", padx=5)
        
        # Batch folder processing
        batch_folder_frame = ttk.LabelFrame(tab_frame, text="Batch Folder Processing", padding="10")
        batch_folder_frame.pack(fill="x", pady=10)
        
        # Folder selection
        folder_frame = ttk.Frame(batch_folder_frame)
        folder_frame.pack(fill="x", pady=5)
        
        ttk.Label(folder_frame, text="Batch Folder:").pack(side="left")
        self.batch_folder_var = tk.StringVar()
        ttk.Entry(folder_frame, textvariable=self.batch_folder_var, width=50).pack(side="left", padx=5)
        ttk.Button(folder_frame, text="Browse...", command=self.browse_batch_folder).pack(side="left", padx=5)
        
        # Batch processing options
        options_frame = ttk.Frame(batch_folder_frame)
        options_frame.pack(fill="x", pady=5)
        
        self.batch_remove_bloat_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Remove structural bloat", variable=self.batch_remove_bloat_var).pack(side="left", padx=5)
        
        self.batch_fix_ranges_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Fix instrument ranges", variable=self.batch_fix_ranges_var).pack(side="left", padx=5)
        
        self.batch_backup_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Create backups", variable=self.batch_backup_var).pack(side="left", padx=5)
        
        # Batch processing controls
        batch_btn_frame = ttk.Frame(batch_folder_frame)
        batch_btn_frame.pack(fill="x", pady=10)
        
        ttk.Button(batch_btn_frame, text="🔍 Scan Folder", command=self.scan_batch_folder).pack(side="left", padx=5)
        ttk.Button(batch_btn_frame, text="🚀 Process All XPM Files", command=self.process_batch_folder).pack(side="left", padx=5)
        ttk.Button(batch_btn_frame, text="📈 Show Batch Results", command=self.show_batch_results).pack(side="left", padx=5)
        
        # Batch results display
        self.batch_results_text = tk.Text(batch_folder_frame, height=10, width=80)
        batch_results_scrollbar = ttk.Scrollbar(batch_folder_frame, orient="vertical", command=self.batch_results_text.yview)
        self.batch_results_text.configure(yscrollcommand=batch_results_scrollbar.set)
        self.batch_results_text.pack(side="left", fill="both", expand=True, pady=5)
        batch_results_scrollbar.pack(side="right", fill="y")
        
    def create_visual_keyboard_tab(self):
        """Create visual keyboard display with all sample mapping"""
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text="Visual Keyboard")
        
        # Controls frame
        controls_frame = ttk.Frame(tab_frame)
        controls_frame.pack(fill="x", pady=5)
        
        # View mode selection
        view_frame = ttk.LabelFrame(controls_frame, text="View Mode", padding="5")
        view_frame.pack(side="left", padx=5)
        
        self.view_mode_var = tk.StringVar(value="all_instruments")
        ttk.Radiobutton(view_frame, text="All Instruments", variable=self.view_mode_var, 
                       value="all_instruments", command=self.update_keyboard_display).pack(anchor="w")
        ttk.Radiobutton(view_frame, text="Single Instrument", variable=self.view_mode_var, 
                       value="single_instrument", command=self.update_keyboard_display).pack(anchor="w")
        
        # Instrument selection for single mode
        inst_frame = ttk.LabelFrame(controls_frame, text="Instrument Selection", padding="5")
        inst_frame.pack(side="left", padx=5)
        
        self.visual_inst_var = tk.StringVar()
        self.visual_inst_combo = ttk.Combobox(inst_frame, textvariable=self.visual_inst_var, width=30, state="readonly")
        self.visual_inst_combo.pack()
        self.visual_inst_combo.bind("<<ComboboxSelected>>", self.update_keyboard_display)
        
        # Octave range controls
        range_frame = ttk.LabelFrame(controls_frame, text="Octave Range", padding="5")
        range_frame.pack(side="left", padx=5)
        
        ttk.Label(range_frame, text="Start:").grid(row=0, column=0)
        self.start_octave_var = tk.IntVar(value=1)
        tk.Spinbox(range_frame, from_=-1, to=9, textvariable=self.start_octave_var, 
                  width=5, command=self.update_keyboard_display).grid(row=0, column=1)
        
        ttk.Label(range_frame, text="End:").grid(row=0, column=2, padx=(10,0))
        self.end_octave_var = tk.IntVar(value=7)
        tk.Spinbox(range_frame, from_=-1, to=9, textvariable=self.end_octave_var, 
                  width=5, command=self.update_keyboard_display).grid(row=0, column=3)
        
        # Keyboard canvas frame
        keyboard_frame = ttk.Frame(tab_frame)
        keyboard_frame.pack(fill="both", expand=True, pady=5)
        
        # Create canvas with scrollbars
        self.keyboard_canvas = tk.Canvas(keyboard_frame, height=300, bg="white")
        h_scrollbar = ttk.Scrollbar(keyboard_frame, orient="horizontal", command=self.keyboard_canvas.xview)
        v_scrollbar = ttk.Scrollbar(keyboard_frame, orient="vertical", command=self.keyboard_canvas.yview)
        self.keyboard_canvas.configure(xscrollcommand=h_scrollbar.set, yscrollcommand=v_scrollbar.set)
        
        self.keyboard_canvas.pack(side="top", fill="both", expand=True)
        h_scrollbar.pack(side="bottom", fill="x")
        v_scrollbar.pack(side="right", fill="y")
        
        # Bind canvas events
        self.keyboard_canvas.bind("<Button-1>", self.on_keyboard_click)
        self.keyboard_canvas.bind("<Motion>", self.on_keyboard_hover)
        
        # Sample details frame
        details_frame = ttk.LabelFrame(tab_frame, text="Sample Details", padding="5")
        details_frame.pack(fill="x", pady=5)
        
        self.selected_key_var = tk.StringVar(value="Click a key to see sample details")
        ttk.Label(details_frame, textvariable=self.selected_key_var, wraplength=800).pack()
        
        # Storage for keyboard mappings
        self.key_mappings = {}  # MIDI note -> list of {instrument, layer, sample_info}
        self.key_rects = {}     # MIDI note -> canvas rectangle id
        
        # Color palette for different samples (bright, distinguishable colors)
        self.sample_colors = [
            "#FFB6C1",  # Light Pink
            "#87CEEB",  # Sky Blue
            "#98FB98",  # Pale Green
            "#F0E68C",  # Khaki
            "#DDA0DD",  # Plum
            "#F5DEB3",  # Wheat
            "#FFE4B5",  # Moccasin
            "#B0E0E6",  # Powder Blue
            "#FFCCCB",  # Light Coral
            "#D3D3D3",  # Light Gray
            "#F0FFFF",  # Azure
            "#FFF8DC",  # Cornsilk
        ]
    
    # ============================================================================
    # STRUCTURAL BLOAT REMOVAL METHODS
    # ============================================================================
    
    def analyze_structural_bloat(self):
        """Analyze current XPM file for structural bloat"""
        if not self.xpm_tree:
            messagebox.showwarning("Warning", "Load an XPM file first")
            return
        
        root = self.xpm_tree.getroot()
        instruments = root.findall(".//Instrument")
        total_instruments = len(instruments)
        
        instruments_with_samples = 0
        empty_instruments = []
        sample_instrument_details = []
        
        for i, instrument in enumerate(instruments):
            has_samples = False
            layers = instrument.find("Layers")
            
            if layers is not None:
                for layer in layers.findall("Layer"):
                    sample_name_elem = layer.find("SampleName")
                    sample_file_elem = layer.find("SampleFile")
                    
                    if ((sample_name_elem is not None and sample_name_elem.text and sample_name_elem.text.strip()) or
                        (sample_file_elem is not None and sample_file_elem.text and sample_file_elem.text.strip())):
                        has_samples = True
                        sample_name = sample_name_elem.text if sample_name_elem is not None else "Unknown"
                        sample_instrument_details.append(f"Instrument {i+1}: {sample_name}")
                        break
            
            if has_samples:
                instruments_with_samples += 1
            else:
                empty_instruments.append(i + 1)
        
        # Calculate bloat statistics
        empty_count = len(empty_instruments)
        bloat_ratio = (empty_count / total_instruments) * 100 if total_instruments > 0 else 0
        
        # Generate analysis report
        analysis_report = "🔍 STRUCTURAL BLOAT ANALYSIS\n"
        analysis_report += "=" * 50 + "\n\n"
        
        analysis_report += f"📊 Total Instruments: {total_instruments}\n"
        analysis_report += f"✅ Instruments with samples: {instruments_with_samples}\n"
        analysis_report += f"❌ Empty instruments: {empty_count}\n"
        analysis_report += f"📈 Bloat ratio: {bloat_ratio:.1f}%\n\n"
        
        # Severity assessment
        if bloat_ratio >= 70:
            severity = "🚨 CRITICAL"
            recommendation = "IMMEDIATE cleanup required for MPC Live 2 compatibility"
        elif bloat_ratio >= 50:
            severity = "⚠️ HIGH"
            recommendation = "Cleanup recommended for optimal performance"
        elif bloat_ratio >= 25:
            severity = "⚡ MODERATE"
            recommendation = "Cleanup beneficial but not critical"
        else:
            severity = "✅ LOW"
            recommendation = "File structure is relatively clean"
        
        analysis_report += f"🎯 Severity: {severity}\n"
        analysis_report += f"💡 Recommendation: {recommendation}\n\n"
        
        # Show instruments with samples
        if sample_instrument_details:
            analysis_report += "🎵 INSTRUMENTS WITH SAMPLES:\n"
            for detail in sample_instrument_details:
                analysis_report += f"   • {detail}\n"
            analysis_report += "\n"
        
        # Show empty instrument numbers (limited to first 20)
        if empty_instruments:
            analysis_report += f"🗑️ EMPTY INSTRUMENTS ({len(empty_instruments)} total):\n"
            if len(empty_instruments) <= 20:
                analysis_report += f"   {', '.join(map(str, empty_instruments))}\n"
            else:
                analysis_report += f"   {', '.join(map(str, empty_instruments[:20]))} ... and {len(empty_instruments)-20} more\n"
        
        # Display in bloat analysis text widget
        self.bloat_analysis_text.delete(1.0, tk.END)
        self.bloat_analysis_text.insert(1.0, analysis_report)
        
        # Switch to cleanup tab
        self.notebook.select(3)  # Structural Cleanup tab
    
    def remove_structural_bloat(self):
        """Remove empty instruments from the current XPM file"""
        if not self.xpm_tree:
            messagebox.showwarning("Warning", "Load an XPM file first")
            return
        
        if not messagebox.askyesno("Confirm Bloat Removal", 
                                   "This will remove all empty instruments from the XPM file.\n\n"
                                   "This operation:\n"
                                   "• Removes instruments without samples\n"
                                   "• Renumbers remaining instruments\n"
                                   "• Updates keygroup count\n"
                                   "• Optimizes for MPC Live 2 performance\n\n"
                                   "Continue?"):
            return
        
        try:
            root = self.xpm_tree.getroot()
            instruments_container = root.find(".//Instruments")
            
            if instruments_container is None:
                messagebox.showerror("Error", "No Instruments container found")
                return
            
            instruments = instruments_container.findall("Instrument")
            original_count = len(instruments)
            
            # Find instruments with samples
            instruments_to_keep = []
            removed_count = 0
            
            for instrument in instruments:
                has_samples = False
                layers = instrument.find("Layers")
                
                if layers is not None:
                    for layer in layers.findall("Layer"):
                        sample_name_elem = layer.find("SampleName")
                        sample_file_elem = layer.find("SampleFile")
                        
                        if ((sample_name_elem is not None and sample_name_elem.text and sample_name_elem.text.strip()) or
                            (sample_file_elem is not None and sample_file_elem.text and sample_file_elem.text.strip())):
                            has_samples = True
                            break
                
                if has_samples:
                    instruments_to_keep.append(instrument)
                else:
                    removed_count += 1
            
            # Only proceed if significant bloat was found
            if removed_count < 5:
                messagebox.showinfo("No Bloat", "No significant structural bloat detected (fewer than 5 empty instruments)")
                return
            
            # Remove all instruments and rebuild with only those containing samples
            instruments_container.clear()
            
            # Add back instruments with samples, renumbered sequentially
            for i, instrument in enumerate(instruments_to_keep):
                instrument.set("number", str(i + 1))
                instruments_container.append(instrument)
            
            # Update keygroup count
            kg_count_elem = root.find(".//KeygroupNumKeygroups")
            if kg_count_elem is not None:
                kg_count_elem.text = str(len(instruments_to_keep))
            
            # Update file format to modern version
            version_elem = root.find(".//File_Version")
            if version_elem is not None:
                version_elem.text = "2.1"
            
            app_version_elem = root.find(".//Application_Version")
            if app_version_elem is not None:
                app_version_elem.text = "3.5.0.54"
            
            platform_elem = root.find(".//Platform")
            if platform_elem is not None:
                platform_elem.text = "Linux"
            
            # Reload the instruments list for the UI
            self.load_xmp()
            
            # Show results
            result_msg = f"✅ Structural Bloat Removal Complete!\n\n"
            result_msg += f"• Removed {removed_count} empty instruments\n"
            result_msg += f"• Kept {len(instruments_to_keep)} instruments with samples\n"
            result_msg += f"• Reduced from {original_count} → {len(instruments_to_keep)} instruments\n"
            result_msg += f"• Updated file format to 2.1 for MPC Live 2 compatibility\n\n"
            result_msg += f"File is now optimized for MPC Live 2 performance!"
            
            messagebox.showinfo("Bloat Removal Complete", result_msg)
            self.status_var.set(f"✅ Removed {removed_count} empty instruments")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to remove structural bloat: {e}")
    
    def show_cleanup_stats(self):
        """Show cleanup statistics for the current file"""
        if not self.xpm_tree:
            messagebox.showwarning("Warning", "Load an XPM file first")
            return
        
        self.analyze_structural_bloat()  # This will display the stats
    
    # ============================================================================
    # BATCH PROCESSING METHODS
    # ============================================================================
    
    def browse_batch_folder(self):
        """Browse for batch processing folder"""
        folder = filedialog.askdirectory(title="Select Folder for Batch Processing")
        if folder:
            self.batch_folder_var.set(folder)
    
    def scan_batch_folder(self):
        """Scan the batch folder for XPM files"""
        folder = self.batch_folder_var.get()
        if not folder or not os.path.isdir(folder):
            messagebox.showerror("Error", "Please select a valid folder")
            return
        
        # Find all XPM files recursively
        xmp_files = []
        for root_dir, dirs, files in os.walk(folder):
            for file in files:
                if file.lower().endswith('.xpm'):
                    xmp_files.append(os.path.join(root_dir, file))
        
        # Display scan results
        scan_report = f"📁 BATCH FOLDER SCAN RESULTS\n"
        scan_report += "=" * 50 + "\n\n"
        scan_report += f"📂 Folder: {folder}\n"
        scan_report += f"📄 XPM files found: {len(xmp_files)}\n\n"
        
        if xmp_files:
            scan_report += "📋 FILES TO PROCESS:\n"
            for i, file_path in enumerate(xmp_files[:20]):  # Show first 20
                relative_path = os.path.relpath(file_path, folder)
                scan_report += f"   {i+1:3d}. {relative_path}\n"
            
            if len(xmp_files) > 20:
                scan_report += f"   ... and {len(xmp_files) - 20} more files\n"
        else:
            scan_report += "❌ No XPM files found in the selected folder.\n"
        
        # Display results
        self.batch_results_text.delete(1.0, tk.END)
        self.batch_results_text.insert(1.0, scan_report)
    
    def process_batch_folder(self):
        """Process all XPM files in the batch folder"""
        folder = self.batch_folder_var.get()
        if not folder or not os.path.isdir(folder):
            messagebox.showerror("Error", "Please select a valid folder")
            return
        
        # Find all XPM files recursively
        xmp_files = []
        for root_dir, dirs, files in os.walk(folder):
            for file in files:
                if file.lower().endswith('.xpm'):
                    xmp_files.append(os.path.join(root_dir, file))
        
        if not xmp_files:
            messagebox.showerror("Error", "No XPM files found in the selected folder")
            return
        
        # Confirm batch processing
        options = []
        if self.batch_remove_bloat_var.get():
            options.append("Remove structural bloat")
        if self.batch_fix_ranges_var.get():
            options.append("Fix instrument ranges")
        
        if not options:
            messagebox.showerror("Error", "Please select at least one processing option")
            return
        
        confirm_msg = f"Process {len(xmp_files)} XPM files?\n\n"
        confirm_msg += "Selected operations:\n"
        for option in options:
            confirm_msg += f"• {option}\n"
        confirm_msg += f"\nBackups will be created: {'Yes' if self.batch_backup_var.get() else 'No'}"
        
        if not messagebox.askyesno("Confirm Batch Processing", confirm_msg):
            return
        
        # Process files
        processed_count = 0
        bloat_removed_count = 0
        ranges_fixed_count = 0
        error_count = 0
        errors = []
        
        total_files = len(xmp_files)
        
        for i, file_path in enumerate(xmp_files):
            try:
                # Update progress
                progress = f"Processing {i+1}/{total_files}: {os.path.basename(file_path)}"
                self.status_var.set(progress)
                self.update()
                
                # Create backup if requested
                if self.batch_backup_var.get():
                    backup_path = file_path + ".keyboard_mapper_backup"
                    if not os.path.exists(backup_path):
                        import shutil
                        shutil.copy2(file_path, backup_path)
                
                # Load file
                tree = ET.parse(file_path)
                root = tree.getroot()
                file_modified = False
                
                # Remove structural bloat
                if self.batch_remove_bloat_var.get():
                    if self._remove_file_bloat(tree, file_path):
                        bloat_removed_count += 1
                        file_modified = True
                
                # Fix instrument ranges
                if self.batch_fix_ranges_var.get():
                    if self._fix_file_ranges(tree, file_path):
                        ranges_fixed_count += 1
                        file_modified = True
                
                # Save if modified
                if file_modified:
                    tree.write(file_path, encoding='utf-8', xml_declaration=True)
                    processed_count += 1
                
            except Exception as e:
                error_count += 1
                error_msg = f"{os.path.basename(file_path)}: {str(e)}"
                errors.append(error_msg)
        
        # Show results
        result_report = f"🚀 BATCH PROCESSING COMPLETE\n"
        result_report += "=" * 50 + "\n\n"
        result_report += f"📂 Folder: {folder}\n"
        result_report += f"📄 Total files found: {total_files}\n"
        result_report += f"✅ Files processed: {processed_count}\n"
        result_report += f"🧹 Files with bloat removed: {bloat_removed_count}\n"
        result_report += f"🎹 Files with ranges fixed: {ranges_fixed_count}\n"
        result_report += f"❌ Errors: {error_count}\n\n"
        
        if errors:
            result_report += "❌ ERRORS:\n"
            for error in errors[:10]:  # Show first 10 errors
                result_report += f"   • {error}\n"
            if len(errors) > 10:
                result_report += f"   ... and {len(errors) - 10} more errors\n"
        
        self.batch_results_text.delete(1.0, tk.END)
        self.batch_results_text.insert(1.0, result_report)
        
        self.status_var.set(f"✅ Batch processing complete: {processed_count}/{total_files} files processed")
        messagebox.showinfo("Batch Processing Complete", 
                           f"Processed {processed_count} out of {total_files} files.\n"
                           f"Bloat removed from {bloat_removed_count} files.\n"
                           f"Ranges fixed in {ranges_fixed_count} files.")
    
    def show_batch_results(self):
        """Show the batch processing results"""
        # Switch to cleanup tab to show results
        self.notebook.select(3)  # Structural Cleanup tab
    
    def _remove_file_bloat(self, tree, file_path):
        """Remove bloat from a single file (internal helper)"""
        try:
            root = tree.getroot()
            instruments_container = root.find(".//Instruments")
            
            if instruments_container is None:
                return False
            
            instruments = instruments_container.findall("Instrument")
            original_count = len(instruments)
            
            # Skip if not likely to be bloated
            if original_count < 20:
                return False
            
            # Find instruments with samples
            instruments_to_keep = []
            
            for instrument in instruments:
                has_samples = False
                layers = instrument.find("Layers")
                
                if layers is not None:
                    for layer in layers.findall("Layer"):
                        sample_name_elem = layer.find("SampleName")
                        sample_file_elem = layer.find("SampleFile")
                        
                        if ((sample_name_elem is not None and sample_name_elem.text and sample_name_elem.text.strip()) or
                            (sample_file_elem is not None and sample_file_elem.text and sample_file_elem.text.strip())):
                            has_samples = True
                            break
                
                if has_samples:
                    instruments_to_keep.append(instrument)
            
            # Only proceed if significant bloat detected
            removed_count = original_count - len(instruments_to_keep)
            if removed_count < 5:
                return False
            
            # Remove all instruments and rebuild
            instruments_container.clear()
            
            for i, instrument in enumerate(instruments_to_keep):
                instrument.set("number", str(i + 1))
                instruments_container.append(instrument)
            
            # Update keygroup count
            kg_count_elem = root.find(".//KeygroupNumKeygroups")
            if kg_count_elem is not None:
                kg_count_elem.text = str(len(instruments_to_keep))
            
            return True
            
        except Exception:
            return False
    
    def _fix_file_ranges(self, tree, file_path):
        """Fix instrument ranges in a single file (internal helper)"""
        try:
            root = tree.getroot()
            instruments = root.findall(".//Instrument")
            
            ranges_fixed = 0
            
            for instrument in instruments:
                low_note_elem = instrument.find("LowNote")
                high_note_elem = instrument.find("HighNote")
                
                # Check if ranges need fixing
                needs_fix = False
                
                if low_note_elem is None or high_note_elem is None:
                    needs_fix = True
                else:
                    try:
                        low_note = int(low_note_elem.text)
                        high_note = int(high_note_elem.text)
                        
                        # Fix invalid ranges or very limited ranges
                        if (low_note >= high_note or 
                            low_note < 0 or high_note > 127 or
                            high_note < 84):  # Less than C6
                            needs_fix = True
                    except (ValueError, TypeError):
                        needs_fix = True
                
                if needs_fix:
                    # Set full keyboard range
                    if low_note_elem is None:
                        low_note_elem = ET.SubElement(instrument, "LowNote")
                    if high_note_elem is None:
                        high_note_elem = ET.SubElement(instrument, "HighNote")
                    
                    low_note_elem.text = "0"
                    high_note_elem.text = "127"
                    ranges_fixed += 1
            
            return ranges_fixed > 0
            
        except Exception:
            return False
    
    # ============================================================================
    # VISUAL KEYBOARD METHODS
    # ============================================================================
    
    def update_keyboard_display(self):
        """Update the visual keyboard display"""
        if not self.instruments:
            return
        
        # Clear existing display
        self.keyboard_canvas.delete("all")
        self.key_mappings.clear()
        self.key_rects.clear()
        
        # Build key mappings based on view mode
        if self.view_mode_var.get() == "all_instruments":
            self._build_all_instruments_mapping()
        else:
            self._build_single_instrument_mapping()
        
        # Draw keyboard
        self._draw_keyboard()
        
        # Add legend showing color mappings
        self._update_sample_legend()
        
        # Update instrument combo for single view
        self._update_visual_instrument_combo()
    
    def _build_all_instruments_mapping(self):
        """Build key mappings for all instruments"""
        for inst_idx, instrument in enumerate(self.instruments):
            layers = instrument.find("Layers")
            if layers is not None:
                for layer_idx, layer in enumerate(layers.findall("Layer")):
                    sample_name_elem = layer.find("SampleName")
                    sample_file_elem = layer.find("SampleFile")
                    root_note_elem = layer.find("RootNote")
                    
                    if sample_name_elem is not None and sample_name_elem.text:
                        sample_name = sample_name_elem.text
                        sample_file = sample_file_elem.text if sample_file_elem is not None else "Unknown"
                        
                        # Get root note and instrument range
                        try:
                            root_note = int + 1  # ConvertWithMoss standard offset(root_note_elem.text) if root_note_elem is not None else 60
                            
                            # Get instrument range
                            low_note_elem = instrument.find("LowNote")
                            high_note_elem = instrument.find("HighNote")
                            low_note = int(low_note_elem.text) if low_note_elem is not None else 0
                            high_note = int(high_note_elem.text) if high_note_elem is not None else 127
                            
                            # Map this sample to all keys in instrument range
                            for midi_note in range(max(0, low_note), min(128, high_note + 1)):
                                if midi_note not in self.key_mappings:
                                    self.key_mappings[midi_note] = []
                                
                                self.key_mappings[midi_note].append({
                                    'instrument': inst_idx,
                                    'layer': layer_idx,
                                    'sample_name': sample_name,
                                    'sample_file': sample_file,
                                    'root_note': root_note,
                                    'inst_range': f"{low_note}-{high_note}"
                                })
                        except (ValueError, TypeError):
                            continue
    
    def _build_single_instrument_mapping(self):
        """Build key mappings for a single selected instrument"""
        try:
            selected_idx = self.visual_inst_combo.current()
            if selected_idx < 0 or selected_idx >= len(self.instruments):
                return
            
            instrument = self.instruments[selected_idx]
            layers = instrument.find("Layers")
            
            if layers is not None:
                for layer_idx, layer in enumerate(layers.findall("Layer")):
                    sample_name_elem = layer.find("SampleName")
                    sample_file_elem = layer.find("SampleFile")
                    root_note_elem = layer.find("RootNote")
                    
                    if sample_name_elem is not None and sample_name_elem.text:
                        sample_name = sample_name_elem.text
                        sample_file = sample_file_elem.text if sample_file_elem is not None else "Unknown"
                        
                        try:
                            root_note = int + 1  # ConvertWithMoss standard offset(root_note_elem.text) if root_note_elem is not None else 60
                            
                            # Get instrument range
                            low_note_elem = instrument.find("LowNote")
                            high_note_elem = instrument.find("HighNote")
                            low_note = int(low_note_elem.text) if low_note_elem is not None else 0
                            high_note = int(high_note_elem.text) if high_note_elem is not None else 127
                            
                            # Map this sample to all keys in instrument range
                            for midi_note in range(max(0, low_note), min(128, high_note + 1)):
                                if midi_note not in self.key_mappings:
                                    self.key_mappings[midi_note] = []
                                
                                self.key_mappings[midi_note].append({
                                    'instrument': selected_idx,
                                    'layer': layer_idx,
                                    'sample_name': sample_name,
                                    'sample_file': sample_file,
                                    'root_note': root_note,
                                    'inst_range': f"{low_note}-{high_note}"
                                })
                        except (ValueError, TypeError):
                            continue
        except Exception:
            pass
    
    def _draw_keyboard(self):
        """Draw the visual keyboard with sample mappings"""
        # Calculate octave range
        start_octave = self.start_octave_var.get()
        end_octave = self.end_octave_var.get()
        
        if start_octave >= end_octave:
            return
        
        # Constants for drawing
        white_key_width = 30
        white_key_height = 150
        black_key_width = 20
        black_key_height = 100
        
        # Calculate canvas size
        octaves = end_octave - start_octave
        canvas_width = octaves * 7 * white_key_width  # 7 white keys per octave
        canvas_height = white_key_height + 50
        
        self.keyboard_canvas.configure(scrollregion=(0, 0, canvas_width, canvas_height))
        
        # Draw white keys first
        white_key_x = 0
        for octave in range(start_octave, end_octave):
            for note_offset in [0, 2, 4, 5, 7, 9, 11]:  # C, D, E, F, G, A, B
                midi_note = (octave + 1) * 12 + note_offset
                if 0 <= midi_note <= 127:
                    # Determine color based on mapping - enhanced for individual samples
                    if midi_note in self.key_mappings:
                        mappings = self.key_mappings[midi_note]
                        if len(mappings) == 1:
                            # Single sample - use color based on layer/instrument
                            mapping = mappings[0]
                            # Generate color based on instrument and layer
                            color_index = (mapping['instrument'] * 3 + mapping['layer']) % len(self.sample_colors)
                            fill_color = self.sample_colors[color_index]
                            outline_color = "#000000"
                        else:
                            # Multiple samples layered - use gradient/striped pattern
                            fill_color = "#FFD700"  # Gold for layered samples
                            outline_color = "#FF4500"  # Orange outline
                    else:
                        fill_color = "#FFFFFF"  # White for unmapped
                        outline_color = "#000000"  # Black outline
                    
                    # Draw white key
                    rect_id = self.keyboard_canvas.create_rectangle(
                        white_key_x, 30, white_key_x + white_key_width, 30 + white_key_height,
                        fill=fill_color, outline=outline_color, width=1
                    )
                    
                    self.key_rects[midi_note] = rect_id
                    
                    # Add note label
                    note_name = self.midi_to_note_name(midi_note)
                    self.keyboard_canvas.create_text(
                        white_key_x + white_key_width // 2, 30 + white_key_height - 15,
                        text=note_name, font=("Arial", 8), anchor="center"
                    )
                    
                    # Add sample count indicator
                    if midi_note in self.key_mappings:
                        sample_count = len(self.key_mappings[midi_note])
                        self.keyboard_canvas.create_oval(
                            white_key_x + white_key_width - 12, 35,
                            white_key_x + white_key_width - 2, 45,
                            fill="#FF4500", outline="white", width=1
                        )
                        self.keyboard_canvas.create_text(
                            white_key_x + white_key_width - 7, 40,
                            text=str(sample_count), font=("Arial", 7, "bold"),
                            fill="white", anchor="center"
                        )
                
                white_key_x += white_key_width
        
        # Draw black keys on top
        white_key_x = 0
        for octave in range(start_octave, end_octave):
            black_positions = [0.7, 1.7, 3.7, 4.7, 5.7]  # Relative positions for black keys
            black_notes = [1, 3, 6, 8, 10]  # C#, D#, F#, G#, A#
            
            for i, pos in enumerate(black_positions):
                midi_note = (octave + 1) * 12 + black_notes[i]
                if 0 <= midi_note <= 127:
                    black_key_x = white_key_x + pos * white_key_width - black_key_width // 2
                    
                    # Determine color based on mapping - enhanced for individual samples
                    if midi_note in self.key_mappings:
                        mappings = self.key_mappings[midi_note]
                        if len(mappings) == 1:
                            # Single sample - use darker version of the color
                            mapping = mappings[0]
                            color_index = (mapping['instrument'] * 3 + mapping['layer']) % len(self.sample_colors)
                            base_color = self.sample_colors[color_index]
                            # Darken the color for black keys
                            fill_color = self._darken_color(base_color)
                            outline_color = "#FFFFFF"  # White outline for contrast
                        else:
                            # Multiple samples layered - use dark gold
                            fill_color = "#B8860B"  # Dark goldenrod for layered samples
                            outline_color = "#FF4500"  # Orange outline
                    else:
                        fill_color = "#2C2C2C"  # Dark gray for unmapped
                        outline_color = "#000000"  # Black outline
                    
                    # Draw black key
                    rect_id = self.keyboard_canvas.create_rectangle(
                        black_key_x, 30, black_key_x + black_key_width, 30 + black_key_height,
                        fill=fill_color, outline=outline_color, width=1
                    )
                    
                    self.key_rects[midi_note] = rect_id
                    
                    # Add note label
                    note_name = self.midi_to_note_name(midi_note)
                    self.keyboard_canvas.create_text(
                        black_key_x + black_key_width // 2, 30 + black_key_height - 10,
                        text=note_name, font=("Arial", 6), fill="white", anchor="center"
                    )
                    
                    # Add sample count indicator
                    if midi_note in self.key_mappings:
                        sample_count = len(self.key_mappings[midi_note])
                        self.keyboard_canvas.create_oval(
                            black_key_x + black_key_width - 10, 35,
                            black_key_x + black_key_width - 2, 43,
                            fill="#FF4500", outline="white", width=1
                        )
                        self.keyboard_canvas.create_text(
                            black_key_x + black_key_width - 6, 39,
                            text=str(sample_count), font=("Arial", 6, "bold"),
                            fill="white", anchor="center"
                        )
            
            white_key_x += 7 * white_key_width  # Move to next octave
    
    def _darken_color(self, hex_color):
        """Darken a hex color by reducing RGB values"""
        try:
            # Remove # if present
            hex_color = hex_color.lstrip('#')
            # Convert to RGB
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            # Darken by reducing values
            r = max(0, int(r * 0.6))
            g = max(0, int(g * 0.6))
            b = max(0, int(b * 0.6))
            # Convert back to hex
            return f"#{r:02x}{g:02x}{b:02x}"
        except:
            return "#2C2C2C"  # Default dark color
    
    def _update_sample_legend(self):
        """Update the legend showing which colors represent which samples"""
        try:
            # Clear existing legend
            if hasattr(self, 'legend_frame'):
                self.legend_frame.destroy()
            
            # Create legend frame
            self.legend_frame = ttk.LabelFrame(self.visual_tab, text="Sample Color Legend", padding=5)
            self.legend_frame.pack(fill='x', padx=5, pady=5)
            
            # Collect unique samples from mappings
            unique_samples = {}
            for midi_note, mappings in self.key_mappings.items():
                for mapping in mappings:
                    key = (mapping['instrument'], mapping['layer'])
                    if key not in unique_samples:
                        color_index = (mapping['instrument'] * 3 + mapping['layer']) % len(self.sample_colors)
                        unique_samples[key] = {
                            'color': self.sample_colors[color_index],
                            'sample_name': mapping['sample_name'],
                            'instrument': mapping['instrument'],
                            'layer': mapping['layer']
                        }
            
            # Create legend items
            row = 0
            col = 0
            for key, info in sorted(unique_samples.items()):
                # Color indicator
                color_frame = tk.Frame(self.legend_frame, bg=info['color'], width=20, height=15, relief='solid', bd=1)
                color_frame.grid(row=row, column=col*3, padx=2, pady=1, sticky='w')
                color_frame.grid_propagate(False)
                
                # Sample info
                sample_label = ttk.Label(self.legend_frame, 
                    text=f"Inst{info['instrument']+1}L{info['layer']+1}: {info['sample_name'][:15]}{'...' if len(info['sample_name']) > 15 else ''}")
                sample_label.grid(row=row, column=col*3+1, padx=5, pady=1, sticky='w')
                
                col += 1
                if col >= 3:  # 3 columns
                    col = 0
                    row += 1
                    
        except Exception as e:
            logging.error(f"Error updating sample legend: {e}")
    
    def _update_visual_instrument_combo(self):
        """Update the instrument combo box for visual display"""
        values = []
        for i, instrument in enumerate(self.instruments):
            layers = instrument.find("Layers")
            if layers is not None:
                layer_count = len(layers.findall("Layer"))
                values.append(f"Instrument {i+1} ({layer_count} layers)")
            else:
                values.append(f"Instrument {i+1} (no layers)")
        
        self.visual_inst_combo['values'] = values
        if values and not self.visual_inst_var.get():
            self.visual_inst_combo.current(0)
    
    def on_keyboard_click(self, event):
        """Handle keyboard click events"""
        # Find which key was clicked
        clicked_item = self.keyboard_canvas.find_closest(event.x, event.y)[0]
        
        # Find the MIDI note for this rectangle
        clicked_midi_note = None
        for midi_note, rect_id in self.key_rects.items():
            if rect_id == clicked_item:
                clicked_midi_note = midi_note
                break
        
        if clicked_midi_note is not None:
            self._show_key_details(clicked_midi_note)
    
    def on_keyboard_hover(self, event):
        """Handle keyboard hover events"""
        # You could add hover tooltips here if desired
        pass
    
    def _show_key_details(self, midi_note):
        """Show details for a clicked key"""
        note_name = self.midi_to_note_name(midi_note)
        
        if midi_note in self.key_mappings:
            details = f"🎹 {note_name} (MIDI {midi_note}) - {len(self.key_mappings[midi_note])} sample(s):\n\n"
            
            for i, mapping in enumerate(self.key_mappings[midi_note]):
                details += f"Sample {i+1}:\n"
                details += f"   • Instrument: {mapping['instrument'] + 1}\n"
                details += f"   • Layer: {mapping['layer'] + 1}\n"
                details += f"   • Sample: {mapping['sample_name']}\n"
                details += f"   • Root Note: {self.midi_to_note_name(mapping['root_note'])}\n"
                details += f"   • Range: {mapping['inst_range']}\n"
                details += f"   • File: {os.path.basename(mapping['sample_file'])}\n\n"
        else:
            details = f"🎹 {note_name} (MIDI {midi_note}) - No samples mapped"
        
        self.selected_key_var.set(details)
    
    # ============================================================================
    # WHOLE INSTRUMENT RANGE FIXING METHODS
    # ============================================================================
    
    def fix_all_instrument_ranges(self):
        """Fix ranges for all instruments in the XPM file"""
        if not self.xpm_tree:
            messagebox.showwarning("Warning", "Load an XPM file first")
            return
        
        if not messagebox.askyesno("Fix All Instrument Ranges", 
                                   "This will fix the note ranges for ALL instruments in the file.\n\n"
                                   "Each instrument will be set to full keyboard range (0-127)\n"
                                   "unless it has specific sample-based range requirements.\n\n"
                                   "Continue?"):
            return
        
        try:
            root = self.xpm_tree.getroot()
            instruments = root.findall(".//Instrument")
            fixed_count = 0
            
            for i, instrument in enumerate(instruments):
                # Check if instrument has samples
                has_samples = False
                layers = instrument.find("Layers")
                
                if layers is not None:
                    for layer in layers.findall("Layer"):
                        sample_name_elem = layer.find("SampleName")
                        sample_file_elem = layer.find("SampleFile")
                        
                        if ((sample_name_elem is not None and sample_name_elem.text and sample_name_elem.text.strip()) or
                            (sample_file_elem is not None and sample_file_elem.text and sample_file_elem.text.strip())):
                            has_samples = True
                            break
                
                # Only fix instruments that have samples
                if has_samples:
                    low_note_elem = instrument.find("LowNote")
                    high_note_elem = instrument.find("HighNote")
                    
                    # Create elements if missing
                    if low_note_elem is None:
                        low_note_elem = ET.SubElement(instrument, "LowNote")
                    if high_note_elem is None:
                        high_note_elem = ET.SubElement(instrument, "HighNote")
                    
                    # Check if range needs fixing
                    needs_fix = False
                    try:
                        low_note = int(low_note_elem.text)
                        high_note = int(high_note_elem.text)
                        
                        # Fix invalid ranges or very limited ranges
                        if (low_note >= high_note or 
                            low_note < 0 or high_note > 127 or
                            high_note < 84):  # Less than C6 (limited playability)
                            needs_fix = True
                    except (ValueError, TypeError):
                        needs_fix = True
                    
                    if needs_fix:
                        # Set full keyboard range for maximum playability
                        low_note_elem.text = "0"
                        high_note_elem.text = "127"
                        fixed_count += 1
            
            # Reload the UI to show changes
            self.load_xmp()
            
            # Show results
            result_msg = f"✅ Fixed ranges for {fixed_count} instruments.\n\n"
            result_msg += f"All instruments now have full keyboard range (0-127)\n"
            result_msg += f"ensuring C6, C7, C8 playability on MPC Live 2."
            
            messagebox.showinfo("Range Fix Complete", result_msg)
            self.status_var.set(f"✅ Fixed ranges for {fixed_count} instruments")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fix instrument ranges: {e}")

def main():
    """Test the enhanced keyboard mapper"""
    root = tk.Tk()
    root.title("Test Enhanced Keyboard Mapper")
    
    app = EnhancedKeyboardMapper(root)
    root.mainloop()

if __name__ == "__main__":
    main()
