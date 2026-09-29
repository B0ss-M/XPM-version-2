#!/usr/bin/env python3
"""
Advanced Progression Builder & Rebuilder GUI

This GUI provides:
1. Rebuild function for existing progression files with analysis
2. Intelligent chord progression expansion using music theory
3. User library database management and statistics
4. AI-inspired chord progression generation
5. Advanced music theory tools and chord substitutions
"""

import os
import json
import datetime
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from typing import List, Dict, Optional
import traceback
from pathlib import Path

# Import our advanced music theory engine
try:
    # First try direct import (when run standalone)
    from scripts.music_theory_engine import MusicTheoryEngine, ProgressionAnalysis
    MUSIC_THEORY_AVAILABLE = True
except ImportError:
    try:
        # Try relative import when run as part of main app
        import sys
        import os
        script_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(script_dir)
        sys.path.insert(0, parent_dir)
        sys.path.insert(0, script_dir)
        from music_theory_engine import MusicTheoryEngine, ProgressionAnalysis
        MUSIC_THEORY_AVAILABLE = True
    except ImportError as e:
        print(f"Music theory engine not available: {e}")
        MUSIC_THEORY_AVAILABLE = False
        # Create dummy classes so GUI can still load
        class MusicTheoryEngine:
            def __init__(self, *args, **kwargs):
                pass
            def close(self):
                pass
        
        class ProgressionAnalysis:
            def __init__(self):
                self.key = "C"
                self.scale = "major"
                self.complexity_score = 0.5
                self.mood_tags = []
                self.roman_numerals = []
                self.chord_functions = []
                self.modulations = []
                self.borrowed_chords = []
                self.secondary_dominants = []

# Import MIDI functionality
MIDI_IMPORT_AVAILABLE = False
try:
    import mido
    # Try both import paths (standalone and as module)
    try:
        from midi_chord_analyzer import MIDIChordAnalyzer
    except ImportError:
        from scripts.midi_chord_analyzer import MIDIChordAnalyzer
    
    try:
        from database_enhancer import enhance_music_theory_database
    except ImportError:
        from scripts.database_enhancer import enhance_music_theory_database
    
    MIDI_IMPORT_AVAILABLE = True    
except ImportError as e:
    print(f"MIDI import functionality not available: {e}")
    MIDI_IMPORT_AVAILABLE = False

# Safe file dialogs
try:
    from tk_file_utils import (
        askopenfilenames as safe_askopenfilenames,
        askopenfilename as safe_askopenfilename,
        askdirectory as safe_askdirectory,
    )
except ImportError:
    safe_askopenfilenames = filedialog.askopenfilenames
    safe_askopenfilename = filedialog.askopenfilename  
    safe_askdirectory = filedialog.askdirectory

class ProgressionRebuilderGUI:
    """Advanced GUI for progression analysis, rebuilding, and generation."""
    
    def __init__(self, parent=None):
        """Initialize the GUI."""
        if parent is None:
            self.root = tk.Tk()
            self.root.title("Advanced Progression Builder & Music Theory Engine")
            self.is_toplevel = False
        else:
            self.root = tk.Toplevel(parent)
            self.root.title("Advanced Progression Builder")
            self.root.transient(parent)
            self.is_toplevel = True
        
        self.root.geometry("1000x800")
        self.music_engine = None
        self.current_analysis = None
        self.user_library = []
        
        # Initialize music theory engine
        if MUSIC_THEORY_AVAILABLE:
            try:
                self.music_engine = MusicTheoryEngine()
                # Enhance database for MIDI support if available
                if MIDI_IMPORT_AVAILABLE:
                    enhance_music_theory_database(self.music_engine.db_path)
                # Load user library after GUI is created
                self.root.after(100, self.load_user_library)
            except Exception as e:
                messagebox.showerror("Engine Error", f"Failed to initialize music theory engine: {e}")
        
        self.create_widgets()
        self.update_status("Ready - Advanced Music Theory Engine Loaded")
    
    def create_widgets(self):
        """Create the GUI widgets."""
        # Create notebook for tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Tab 1: File Rebuild & Analysis
        self.rebuild_frame = ttk.Frame(notebook)
        notebook.add(self.rebuild_frame, text="Rebuild & Analyze")
        self.create_rebuild_tab()
        
        # Tab 2: Progression Generator
        self.generator_frame = ttk.Frame(notebook)
        notebook.add(self.generator_frame, text="Generate New")
        self.create_generator_tab()
        
        # Tab 3: User Library
        self.library_frame = ttk.Frame(notebook)
        notebook.add(self.library_frame, text="Chord Library")
        self.create_library_tab()
        
        # Tab 4: MIDI Import & Analysis (if available)
        if MIDI_IMPORT_AVAILABLE:
            self.midi_frame = ttk.Frame(notebook)
            notebook.add(self.midi_frame, text="🎵 MIDI Import")
            self.create_midi_tab()
        
        # Tab 5: Music Theory Tools
        self.theory_frame = ttk.Frame(notebook)
        notebook.add(self.theory_frame, text="Theory Tools")
        self.create_theory_tab()
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        
    def create_rebuild_tab(self):
        """Create the rebuild and analysis tab."""
        # File selection frame
        file_frame = ttk.LabelFrame(self.rebuild_frame, text="Select Progression Files")
        file_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(file_frame, text="Select Files to Rebuild", 
                  command=self.select_files_to_rebuild).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(file_frame, text="Select Folder", 
                  command=self.select_folder_to_rebuild).pack(side=tk.LEFT, padx=5, pady=5)
        
        self.selected_files_var = tk.StringVar()
        ttk.Label(file_frame, textvariable=self.selected_files_var).pack(side=tk.LEFT, padx=10)
        
        # Options frame
        options_frame = ttk.LabelFrame(self.rebuild_frame, text="Rebuild Options")
        options_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.enhance_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Add Enhanced Analysis", 
                       variable=self.enhance_var).pack(side=tk.LEFT, padx=5)
        
        self.expand_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Expand with Substitutions", 
                       variable=self.expand_var).pack(side=tk.LEFT, padx=5)
        
        self.backup_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Create Backup Files", 
                       variable=self.backup_var).pack(side=tk.LEFT, padx=5)
        
        # Analysis display
        analysis_frame = ttk.LabelFrame(self.rebuild_frame, text="Harmonic Analysis")
        analysis_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.analysis_text = scrolledtext.ScrolledText(analysis_frame, wrap=tk.WORD, height=15)
        self.analysis_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Control buttons
        control_frame = ttk.Frame(self.rebuild_frame)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(control_frame, text="Analyze Selected", 
                  command=self.analyze_selected_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Rebuild Files", 
                  command=self.rebuild_selected_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Clear Analysis", 
                  command=self.clear_analysis).pack(side=tk.RIGHT, padx=5)
        
    def create_generator_tab(self):
        """Create the progression generator tab."""
        # Parameters frame
        params_frame = ttk.LabelFrame(self.generator_frame, text="Generation Parameters")
        params_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Key selection
        ttk.Label(params_frame, text="Key:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.key_var = tk.StringVar(value="C")
        key_combo = ttk.Combobox(params_frame, textvariable=self.key_var, width=10)
        key_combo['values'] = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        key_combo.grid(row=0, column=1, padx=5, pady=5)
        
        # Scale selection
        ttk.Label(params_frame, text="Scale:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.scale_var = tk.StringVar(value="major")
        scale_combo = ttk.Combobox(params_frame, textvariable=self.scale_var, width=15)
        scale_combo['values'] = ['major', 'minor', 'dorian', 'phrygian', 'lydian', 'mixolydian', 
                               'blues', 'pentatonic_major', 'pentatonic_minor', 'harmonic_minor',
                               'melodic_minor', 'whole_tone', 'diminished_wh', 'altered']
        scale_combo.grid(row=0, column=3, padx=5, pady=5)
        
        # Length selection
        ttk.Label(params_frame, text="Length:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.length_var = tk.IntVar(value=4)
        length_spin = ttk.Spinbox(params_frame, from_=2, to=16, textvariable=self.length_var, width=10)
        length_spin.grid(row=1, column=1, padx=5, pady=5)
        
        # Style selection
        ttk.Label(params_frame, text="Style:").grid(row=1, column=2, padx=5, pady=5, sticky=tk.W)
        self.style_var = tk.StringVar(value="pop")
        style_combo = ttk.Combobox(params_frame, textvariable=self.style_var, width=15)
        style_combo['values'] = ['pop', 'jazz', 'rock', 'folk', 'blues', 'ballad', 'classical',
                               'funk', 'soul', 'prog_rock', 'punk', 'new_wave', 'synthpop',
                               'grunge', 'hip_hop', 'britpop', 'rnb', 'neo_soul', 'emo', 'indie',
                               'trap', 'modern_pop', 'alt_rnb', 'electronic', 'indie_pop']
        style_combo.grid(row=1, column=3, padx=5, pady=5)
        
        # Voicing selection
        ttk.Label(params_frame, text="Voicing:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.voicing_var = tk.StringVar(value="close")
        voicing_combo = ttk.Combobox(params_frame, textvariable=self.voicing_var, width=15)
        voicing_combo['values'] = ['close', 'open', 'drop2', 'drop3', 'spread', 'shell', 'rootless']
        voicing_combo.grid(row=2, column=1, padx=5, pady=5)
        
        # Historical style selection
        ttk.Label(params_frame, text="Historical:").grid(row=2, column=2, padx=5, pady=5, sticky=tk.W)
        self.historical_var = tk.StringVar(value="none")
        historical_combo = ttk.Combobox(params_frame, textvariable=self.historical_var, width=15)
        historical_combo['values'] = ['none', 'classical_cadential', 'baroque_sequence', 'rhythm_changes_a',
                                     'giant_steps', 'fifty_doo_wop', 'axis_progression', 'twelve_bar_blues',
                                     'funk_vamp', 'motown_progression', 'prog_rock_complex', 'punk_three_chord',
                                     'new_wave_synth', 'hip_hop_loop', 'grunge_progression', 'britpop_anthem',
                                     'neo_soul_jazz', 'trap_dark', 'modern_pop_edm', 'alt_rnb_modern']
        historical_combo.grid(row=2, column=3, padx=5, pady=5)
        
        # Complexity slider
        ttk.Label(params_frame, text="Complexity:").grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)
        self.complexity_var = tk.DoubleVar(value=0.5)
        complexity_scale = ttk.Scale(params_frame, from_=0.0, to=1.0, variable=self.complexity_var, orient=tk.HORIZONTAL)
        complexity_scale.grid(row=3, column=1, columnspan=3, padx=5, pady=5, sticky=tk.EW)
        
        # Transposition control
        ttk.Label(params_frame, text="Options:").grid(row=4, column=0, padx=5, pady=5, sticky=tk.W)
        self.preserve_original_key_var = tk.BooleanVar(value=False)  # Default: Apply transposition
        preserve_key_check = ttk.Checkbutton(params_frame, text="Preserve Original Key (No Auto-Transpose)", 
                                           variable=self.preserve_original_key_var)
        preserve_key_check.grid(row=4, column=1, columnspan=2, padx=5, pady=5, sticky=tk.W)
        
        # Information label
        info_label = ttk.Label(params_frame, text="ℹ️ When checked, chords are generated in their original form (key of C). Uncheck to transpose to selected key.", 
                              font=('Arial', 8), foreground='gray')
        info_label.grid(row=5, column=0, columnspan=4, padx=5, pady=(0, 5), sticky=tk.W)
        
        # Generated progression display
        gen_frame = ttk.LabelFrame(self.generator_frame, text="Generated Progression")
        gen_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.generated_text = scrolledtext.ScrolledText(gen_frame, wrap=tk.WORD, height=20)
        self.generated_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Generation controls
        gen_control_frame = ttk.Frame(self.generator_frame)
        gen_control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(gen_control_frame, text="Generate Progression", 
                  command=self.generate_new_progression).pack(side=tk.LEFT, padx=5)
        ttk.Button(gen_control_frame, text="Generate Historical", 
                  command=self.generate_historical_progression).pack(side=tk.LEFT, padx=5)
        ttk.Button(gen_control_frame, text="Generate Variations", 
                  command=self.generate_variations).pack(side=tk.LEFT, padx=5)
        ttk.Button(gen_control_frame, text="Save Progression", 
                  command=self.save_generated_progression).pack(side=tk.LEFT, padx=5)
        
        # Batch Variation Section
        batch_frame = ttk.LabelFrame(self.generator_frame, text="🎭 Intelligent Batch Variation Generator")
        batch_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Batch parameters
        batch_params = ttk.Frame(batch_frame)
        batch_params.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(batch_params, text="Variations:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.batch_count_var = tk.IntVar(value=25)
        batch_count_spin = ttk.Spinbox(batch_params, from_=5, to=500, textvariable=self.batch_count_var, width=10)
        batch_count_spin.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(batch_params, text="Naming:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.naming_pattern_var = tk.StringVar(value="intelligent")
        naming_combo = ttk.Combobox(batch_params, textvariable=self.naming_pattern_var, width=15)
        naming_combo['values'] = ['intelligent', 'sequential', 'technique_based', 'complexity_based', 'musical_style']
        naming_combo.grid(row=0, column=3, padx=5, pady=5)
        
        ttk.Label(batch_params, text="Mode:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.generation_mode_var = tk.StringVar(value="accumulate")
        mode_combo = ttk.Combobox(batch_params, textvariable=self.generation_mode_var, width=10)
        mode_combo['values'] = ['accumulate', 'replace']
        mode_combo.grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Label(batch_params, text="Technique:").grid(row=1, column=2, padx=5, pady=5, sticky=tk.W)
        self.variation_technique_var = tk.StringVar(value="comprehensive")
        technique_combo = ttk.Combobox(batch_params, textvariable=self.variation_technique_var, width=15)
        technique_combo['values'] = ['comprehensive', 'inversions_only', 'voicing_only', 'substitutions_only', 
                                   'reharmonization', 'classical_techniques', 'jazz_techniques', 'modern_techniques']
        technique_combo.grid(row=1, column=3, padx=5, pady=5)
        
        # Variation options
        var_options = ttk.Frame(batch_frame)
        var_options.pack(fill=tk.X, padx=5, pady=5)
        
        self.use_inversions_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(var_options, text="Inversions & Voicings", variable=self.use_inversions_var).grid(row=0, column=0, padx=5, sticky=tk.W)
        
        self.use_substitutions_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(var_options, text="Chord Substitutions", variable=self.use_substitutions_var).grid(row=0, column=1, padx=5, sticky=tk.W)
        
        self.use_extensions_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(var_options, text="Extensions & Alterations", variable=self.use_extensions_var).grid(row=0, column=2, padx=5, sticky=tk.W)
        
        self.use_reharmonization_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(var_options, text="Reharmonization", variable=self.use_reharmonization_var).grid(row=1, column=0, padx=5, sticky=tk.W)
        
        self.use_modal_interchange_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(var_options, text="Modal Interchange", variable=self.use_modal_interchange_var).grid(row=1, column=1, padx=5, sticky=tk.W)
        
        self.use_secondary_dominants_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(var_options, text="Secondary Dominants", variable=self.use_secondary_dominants_var).grid(row=1, column=2, padx=5, sticky=tk.W)
        
        # Intelligence level
        ttk.Label(batch_frame, text="Intelligence Level (Uniqueness):").pack(anchor=tk.W, padx=5, pady=(5, 0))
        self.intelligence_level_var = tk.DoubleVar(value=0.8)
        intelligence_scale = ttk.Scale(batch_frame, from_=0.0, to=1.0, variable=self.intelligence_level_var, orient=tk.HORIZONTAL)
        intelligence_scale.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        intelligence_info = ttk.Label(batch_frame, 
                                    text="💡 Higher values create more unique variations using advanced music theory techniques",
                                    font=('Arial', 8), foreground='gray')
        intelligence_info.pack(anchor=tk.W, padx=5, pady=(0, 5))
        
        # Batch controls
        batch_controls = ttk.Frame(batch_frame)
        batch_controls.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(batch_controls, text="🎭 Generate Batch Variations", 
                  command=self.generate_batch_variations).pack(side=tk.LEFT, padx=5)
        ttk.Button(batch_controls, text="💾 Export Batch (Folder)", 
                  command=self.export_batch_variations).pack(side=tk.LEFT, padx=5)
        ttk.Button(batch_controls, text="🎵 Preview Random Variation", 
                  command=self.preview_random_variation).pack(side=tk.LEFT, padx=5)
        
    def create_library_tab(self):
        """Create the user library management tab."""
        # Statistics frame
        stats_frame = ttk.LabelFrame(self.library_frame, text="Library Statistics")
        stats_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.stats_text = tk.Text(stats_frame, height=8, wrap=tk.WORD)
        self.stats_text.pack(fill=tk.X, padx=5, pady=5)
        
        # Library browser
        browser_frame = ttk.LabelFrame(self.library_frame, text="Chord & Progression Library")
        browser_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Treeview for library items
        columns = ("Name", "Type", "Key", "Usage", "Complexity")
        self.library_tree = ttk.Treeview(browser_frame, columns=columns, show='tree headings')
        
        for col in columns:
            self.library_tree.heading(col, text=col)
            self.library_tree.column(col, width=120)
        
        scrollbar = ttk.Scrollbar(browser_frame, orient=tk.VERTICAL, command=self.library_tree.yview)
        self.library_tree.configure(yscrollcommand=scrollbar.set)
        
        self.library_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Library controls
        lib_control_frame = ttk.Frame(self.library_frame)
        lib_control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(lib_control_frame, text="Refresh Library", 
                  command=self.refresh_library).pack(side=tk.LEFT, padx=5)
        ttk.Button(lib_control_frame, text="Export Library", 
                  command=self.export_library).pack(side=tk.LEFT, padx=5)
        ttk.Button(lib_control_frame, text="Import Progressions & MIDI", 
                  command=self.import_progressions_to_library).pack(side=tk.LEFT, padx=5)
        
    def create_theory_tab(self):
        """Create the music theory tools tab."""
        # Chord analyzer
        analyzer_frame = ttk.LabelFrame(self.theory_frame, text="Chord Analyzer & Builder")
        analyzer_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(analyzer_frame, text="Chord Name:").pack(side=tk.LEFT, padx=5)
        self.chord_entry = ttk.Entry(analyzer_frame, width=20)
        self.chord_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(analyzer_frame, text="Analyze Chord", 
                  command=self.analyze_chord).pack(side=tk.LEFT, padx=5)
        ttk.Button(analyzer_frame, text="Show Inversions", 
                  command=self.show_chord_inversions).pack(side=tk.LEFT, padx=5)
        ttk.Button(analyzer_frame, text="Show Voicings", 
                  command=self.show_chord_voicings).pack(side=tk.LEFT, padx=5)
        ttk.Button(analyzer_frame, text="Find Substitutions", 
                  command=self.find_substitutions).pack(side=tk.LEFT, padx=5)
        
        # Historical progression browser
        historical_frame = ttk.LabelFrame(self.theory_frame, text="Historical Progressions")
        historical_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(historical_frame, text="Browse Historical Styles", 
                  command=self.browse_historical_styles).pack(side=tk.LEFT, padx=5)
        ttk.Button(historical_frame, text="Analyze Classical Harmony", 
                  command=self.analyze_classical_harmony).pack(side=tk.LEFT, padx=5)
        
        # Theory display
        theory_display_frame = ttk.LabelFrame(self.theory_frame, text="Music Theory Analysis")
        theory_display_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.theory_text = scrolledtext.ScrolledText(theory_display_frame, wrap=tk.WORD)
        self.theory_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def create_midi_tab(self):
        """Create the MIDI import and analysis tab."""
        if not MIDI_IMPORT_AVAILABLE:
            # Show unavailable message
            unavailable_frame = ttk.Frame(self.midi_frame)
            unavailable_frame.pack(expand=True, fill=tk.BOTH)
            
            message_text = ("🎵 MIDI Import Feature\n\n" +
                          "MIDI import functionality is not available.\n" +
                          "To enable MIDI support, install the required dependencies:\n\n" +
                          "pip install mido\n" +
                          "pip install pretty-midi (optional, for enhanced analysis)\n" +
                          "pip install music21 (optional, for advanced theory analysis)")
            
            ttk.Label(unavailable_frame, 
                     text=message_text,
                     font=("Arial", 12),
                     justify=tk.CENTER).pack(expand=True)
            return
        
        # Create main MIDI interface
        main_frame = ttk.Frame(self.midi_frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Header
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        title_label = ttk.Label(header_frame, 
                               text="🎵 MIDI Chord Import & Analysis",
                               font=("Arial", 16, "bold"))
        title_label.pack(anchor=tk.W)
        
        subtitle_label = ttk.Label(header_frame,
                                 text="Import MIDI files to enhance your chord library and improve algorithm accuracy",
                                 font=("Arial", 10))
        subtitle_label.pack(anchor=tk.W, pady=(5, 0))
        
        # Quick Import Section
        quick_frame = ttk.LabelFrame(main_frame, text="🚀 Quick MIDI Import")
        quick_frame.pack(fill=tk.X, pady=(0, 15))
        
        quick_info = ttk.Label(quick_frame,
                              text="Use the main 'Import Progressions & MIDI' button in the Chord Library tab for full import features:",
                              wraplength=400)
        quick_info.pack(anchor=tk.W, padx=10, pady=5)
        
        quick_features = ttk.Label(quick_frame,
                                  text="✓ Individual file selection\n✓ Batch folder processing\n✓ Recursive subdirectory scanning\n✓ Progress tracking\n✓ Automatic library integration",
                                  justify=tk.LEFT)
        quick_features.pack(anchor=tk.W, padx=20, pady=5)
        
        ttk.Button(quick_frame, 
                  text="➤ Go to Chord Library Tab",
                  command=self.switch_to_library_tab).pack(anchor=tk.W, padx=10, pady=10)
        
        # Alternative Direct Import  
        direct_frame = ttk.LabelFrame(main_frame, text="📁 Direct MIDI Import")
        direct_frame.pack(fill=tk.X, pady=(0, 15))
        
        # File selection controls
        controls_frame = ttk.Frame(direct_frame)
        controls_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(controls_frame, text="Select MIDI Files", 
                  command=self.select_midi_files_integrated).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(controls_frame, text="Analyze & Import", 
                  command=self.analyze_midi_files_integrated).pack(side=tk.LEFT, padx=(0, 10))
        
        # Status display
        self.midi_status_var = tk.StringVar(value="No MIDI files selected")
        status_label = ttk.Label(controls_frame, textvariable=self.midi_status_var)
        status_label.pack(side=tk.LEFT, padx=(20, 0))
        
        # Progress section
        progress_frame = ttk.Frame(direct_frame)
        progress_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        self.midi_progress_label = ttk.Label(progress_frame, text="Ready to analyze...")
        self.midi_progress_label.pack(anchor=tk.W)
        
        self.midi_progress = ttk.Progressbar(progress_frame, length=400, mode='determinate')
        self.midi_progress.pack(fill=tk.X, pady=(5, 0))
        
        # Info section
        info_frame = ttk.LabelFrame(main_frame, text="ℹ️ How MIDI Import Works")
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        info_text = ("The MIDI chord analysis system:\n\n" +
                    "1. 🎼 Analyzes MIDI files for chord progressions\n" +
                    "2. 🎯 Detects key signatures and chord voicings\n" +
                    "3. 📚 Adds detected chords to your library database\n" +
                    "4. 🧠 Learns from your corrections to improve accuracy\n" +
                    "5. 📈 The more MIDI files you import, the smarter the algorithm becomes!")
        
        ttk.Label(info_frame, text=info_text, justify=tk.LEFT).pack(anchor=tk.W, padx=10, pady=10)
        
    def switch_to_library_tab(self):
        """Switch to the Chord Library tab."""
        # Find the notebook parent and switch to library tab
        notebook = self.midi_frame.master
        for i in range(notebook.index("end")):
            if notebook.tab(i, "text") == "Chord Library":
                notebook.select(i)
                break
        
    def select_midi_files_integrated(self):
        """Select MIDI files for analysis (integrated version)."""
        files = safe_askopenfilenames(
            title="Select MIDI Files",
            filetypes=[("MIDI files", "*.mid *.midi"), ("All files", "*.*")]
        )
        
        if files:
            self.selected_midi_files = list(files)
            count = len(files)
            self.midi_status_var.set(f"{count} MIDI file{'s' if count != 1 else ''} selected")
        else:
            self.selected_midi_files = []
            self.midi_status_var.set("No MIDI files selected")
    
    def analyze_midi_files_integrated(self):
        """Analyze selected MIDI files (integrated version)."""
        if not hasattr(self, 'selected_midi_files') or not self.selected_midi_files:
            messagebox.showwarning("No Files", "Please select MIDI files first")
            return
        
        if not MIDI_IMPORT_AVAILABLE:
            messagebox.showerror("Feature Unavailable", "MIDI import functionality is not available")
            return
        
        # Start analysis in a separate thread
        threading.Thread(target=self._analyze_midi_thread, daemon=True).start()
    
    def _analyze_midi_thread(self):
        """Analyze MIDI files in background thread."""
        try:
            # Try both import paths
            try:
                from midi_chord_analyzer import MIDIChordAnalyzer
            except ImportError:
                from scripts.midi_chord_analyzer import MIDIChordAnalyzer
            
            try:
                from database_enhancer import MIDIDataManager
            except ImportError:
                from scripts.database_enhancer import MIDIDataManager
            
            analyzer = MIDIChordAnalyzer()
            data_manager = MIDIDataManager(self.music_engine.db_path)
            
            total_files = len(self.selected_midi_files)
            imported_count = 0
            
            for i, file_path in enumerate(self.selected_midi_files):
                try:
                    progress = (i / total_files) * 100
                    filename = os.path.basename(file_path)
                    
                    # Update UI safely
                    if hasattr(self, 'midi_progress'):
                        self.root.after(0, lambda p=progress: self.midi_progress.config(value=p))
                    if hasattr(self, 'midi_progress_label'):
                        self.root.after(0, lambda f=filename: self.midi_progress_label.config(text=f"Analyzing {f}"))
                    
                    # Analyze file
                    analysis = analyzer.analyze_midi_file(file_path)
                    
                    if analysis and analysis.chord_symbols:
                        # Store in database using the same logic as import_progressions_to_library
                        file_name = os.path.splitext(os.path.basename(file_path))[0]
                        progression_name = f"MIDI: {file_name}"
                        
                        # Add progression to library
                        self.music_engine.add_progression_to_library(
                            name=progression_name,
                            chords=analysis.chord_symbols,
                            key=analysis.key_signature or "C",
                            scale="major",
                            mood_tags=[f"complexity_{analysis.complexity_score:.1f}"],
                            complexity=analysis.complexity_score,
                            source_file=file_path
                        )
                        
                        # Add individual chords to library
                        chord_objects = []
                        for idx, chord_symbol in enumerate(analysis.chord_symbols):
                            chord_obj = {
                                'name': chord_symbol,
                                'position': idx,
                                'confidence': 1.0
                            }
                            chord_objects.append(chord_obj)
                        
                        self.music_engine.add_chords_to_library(chord_objects, file_path)
                        imported_count += 1
                        print(f"✅ Successfully imported MIDI: {filename} ({len(analysis.chord_symbols)} chords)")
                    else:
                        print(f"⚠️ No chords detected in: {filename}")
                        
                except Exception as e:
                    print(f"❌ Error analyzing {filename}: {e}")
            
            # Update UI completion
            if hasattr(self, 'midi_progress'):
                self.root.after(0, lambda: self.midi_progress.config(value=100))
            if hasattr(self, 'midi_progress_label'):
                self.root.after(0, lambda: self.midi_progress_label.config(text=f"Complete! Imported {imported_count}/{total_files} files"))
            
            # Show completion message
            self.root.after(0, lambda: messagebox.showinfo(
                "MIDI Import Complete", 
                f"Successfully imported {imported_count} out of {total_files} MIDI files to your chord library.\n\n" +
                "The algorithm has been enhanced with the new chord data!"
            ))
            
            # Refresh library if imported any files
            if imported_count > 0:
                self.root.after(0, self.refresh_library)
                
        except Exception as e:
            error_msg = f"Error during MIDI analysis: {str(e)}"
            print(error_msg)
            if hasattr(self, 'midi_progress_label'):
                self.root.after(0, lambda: self.midi_progress_label.config(text="Error occurred"))
            self.root.after(0, lambda: messagebox.showerror("MIDI Analysis Error", error_msg))
    
    def refresh_midi_imports(self):
        """Refresh the display of imported MIDI files."""
        if not MIDI_IMPORT_AVAILABLE or not hasattr(self, 'midi_tree'):
            return
        
        try:
            # Clear existing items
            for item in self.midi_tree.get_children():
                self.midi_tree.delete(item)
            
            # Get recent MIDI imports from database
            from database_enhancer import MIDIDataManager
            data_manager = MIDIDataManager(self.music_engine.db_path)
            
            # This is a simplified version - the actual implementation would query the database
            # for recent MIDI imports and display them
            pass
            
        except Exception as e:
            print(f"Error refreshing MIDI imports: {e}")
    
    def view_midi_details(self, event):
        """View details of selected MIDI import."""
        selection = self.midi_tree.selection()
        if not selection:
            return
        
        # Get selected item details and show them
        item = self.midi_tree.item(selection[0])
        filename = item['values'][0]
        
        # Show details in theory text area
        self.notebook.select(self.theory_frame)
        self.theory_text.delete(1.0, tk.END)
        self.theory_text.insert(1.0, f"MIDI Import Details for: {filename}\n" + "="*50 + "\n\nDetails would be shown here...")
        
    def select_files_to_rebuild(self):
        """Select individual progression files to rebuild."""
        files = safe_askopenfilenames(
            title="Select Progression Files to Rebuild",
            filetypes=[
                ("Progression Files", "*.progression"),
                ("All Files", "*.*")
            ]
        )
        
        if files:
            self.selected_files = list(files)
            self.selected_files_var.set(f"{len(files)} files selected")
            self.update_status(f"Selected {len(files)} files for rebuilding")
        
    def select_folder_to_rebuild(self):
        """Select a folder containing progression files."""
        folder = safe_askdirectory(title="Select Folder with Progression Files")
        
        if folder:
            # Find all .progression files in the folder
            prog_files = []
            for file in Path(folder).rglob("*.progression"):
                prog_files.append(str(file))
            
            if prog_files:
                self.selected_files = prog_files
                self.selected_files_var.set(f"{len(prog_files)} files found in folder")
                self.update_status(f"Found {len(prog_files)} progression files in folder")
            else:
                messagebox.showwarning("No Files", "No .progression files found in selected folder")
        
    def analyze_selected_files(self):
        """Analyze the selected progression files."""
        if not hasattr(self, 'selected_files') or not self.selected_files:
            messagebox.showwarning("No Files", "Please select files to analyze first")
            return
        
        if not MUSIC_THEORY_AVAILABLE or not self.music_engine:
            messagebox.showerror("Engine Error", "Music theory engine not available")
            return
        
        self.clear_analysis()
        analyses = []
        
        try:
            for file_path in self.selected_files:
                self.update_status(f"Analyzing {os.path.basename(file_path)}...")
                analysis = self.music_engine.analyze_progression(file_path)
                analyses.append((file_path, analysis))
                
                # Display analysis
                self.display_analysis(file_path, analysis)
            
            self.update_status(f"Analyzed {len(analyses)} files successfully")
            
        except Exception as e:
            messagebox.showerror("Analysis Error", f"Error analyzing files: {str(e)}")
            self.update_status("Analysis failed")
    
    def display_analysis(self, file_path: str, analysis: ProgressionAnalysis):
        """Display analysis results in the text widget."""
        filename = os.path.basename(file_path)
        
        analysis_output = f"\\n{'='*60}\\n"
        analysis_output += f"FILE: {filename}\\n"
        analysis_output += f"{'='*60}\\n\\n"
        
        analysis_output += f"KEY SIGNATURE: {analysis.key} {analysis.scale}\\n"
        analysis_output += f"COMPLEXITY SCORE: {analysis.complexity_score:.2f}/1.0\\n"
        analysis_output += f"MOOD TAGS: {', '.join(analysis.mood_tags)}\\n\\n"
        
        if analysis.roman_numerals:
            analysis_output += f"ROMAN NUMERAL ANALYSIS:\\n"
            for i, numeral in enumerate(analysis.roman_numerals):
                function = analysis.chord_functions[i] if i < len(analysis.chord_functions) else "normal"
                analysis_output += f"  {i+1}. {numeral} ({function})\\n"
            analysis_output += "\\n"
        
        if analysis.modulations:
            analysis_output += f"MODULATIONS DETECTED:\\n"
            for pos, key in analysis.modulations:
                analysis_output += f"  Chord {pos+1}: Modulation to {key}\\n"
            analysis_output += "\\n"
        
        if analysis.borrowed_chords:
            analysis_output += f"BORROWED CHORDS: {[i+1 for i in analysis.borrowed_chords]}\\n\\n"
            
        if analysis.secondary_dominants:
            analysis_output += f"SECONDARY DOMINANTS: {[i+1 for i in analysis.secondary_dominants]}\\n\\n"
        
        # Historical context
        if analysis.historical_context:
            analysis_output += f"HISTORICAL CONTEXT:\\n"
            analysis_output += f"  Era: {analysis.era}\\n"
            analysis_output += f"  Description: {analysis.historical_context}\\n"
            if analysis.similar_to_famous:
                analysis_output += f"  Similar to: {', '.join(analysis.similar_to_famous)}\\n"
            analysis_output += "\\n"
        
        # Voice leading quality
        analysis_output += f"VOICE LEADING QUALITY: {analysis.voice_leading_quality:.2f}/1.0\\n\\n"
        
        # Recommendations
        analysis_output += f"RECOMMENDATIONS:\\n"
        if analysis.complexity_score < 0.3:
            analysis_output += "  - Consider adding seventh chords for more sophistication\\n"
            analysis_output += "  - Try modal interchange or secondary dominants\\n"
        elif analysis.complexity_score > 0.8:
            analysis_output += "  - Very sophisticated harmonic content\\n"
            analysis_output += "  - Great for jazz or advanced styles\\n"
        else:
            analysis_output += "  - Well-balanced harmonic complexity\\n"
            analysis_output += "  - Good for commercial and artistic use\\n"
            
        if analysis.voice_leading_quality < 0.5:
            analysis_output += "  - Consider smoother voice leading between chords\\n"
            analysis_output += "  - Try chord inversions for better flow\\n"
        
        self.analysis_text.insert(tk.END, analysis_output)
        self.analysis_text.see(tk.END)
    
    def rebuild_selected_files(self):
        """Rebuild the selected progression files."""
        if not hasattr(self, 'selected_files') or not self.selected_files:
            messagebox.showwarning("No Files", "Please select files to rebuild first")
            return
        
        if not MUSIC_THEORY_AVAILABLE or not self.music_engine:
            messagebox.showerror("Engine Error", "Music theory engine not available")
            return
        
        enhance = self.enhance_var.get()
        expand = self.expand_var.get()
        backup = self.backup_var.get()
        
        successful = 0
        failed = 0
        
        try:
            for file_path in self.selected_files:
                self.update_status(f"Rebuilding {os.path.basename(file_path)}...")
                
                try:
                    # Create backup if requested
                    if backup:
                        backup_path = file_path + ".backup"
                        with open(file_path, 'r') as src, open(backup_path, 'w') as dst:
                            dst.write(src.read())
                    
                    # Rebuild the file
                    self.music_engine.rebuild_progression(
                        file_path,
                        enhance=enhance,
                        expand=expand
                    )
                    
                    successful += 1
                    
                except Exception as e:
                    failed += 1
                    print(f"Failed to rebuild {file_path}: {e}")
            
            # Show results
            result_msg = f"Rebuild complete!\\n\\nSuccessful: {successful}\\nFailed: {failed}"
            if backup:
                result_msg += f"\\n\\nBackup files created with .backup extension"
            
            messagebox.showinfo("Rebuild Complete", result_msg)
            self.update_status(f"Rebuild complete: {successful} successful, {failed} failed")
            
            # Refresh library
            self.refresh_library()
            
        except Exception as e:
            messagebox.showerror("Rebuild Error", f"Error during rebuild: {str(e)}")
            self.update_status("Rebuild failed")
    
    def generate_new_progression(self):
        """Generate a new chord progression using the AI engine."""
        if not MUSIC_THEORY_AVAILABLE or not self.music_engine:
            messagebox.showerror("Engine Error", "Music theory engine not available")
            return
        
        try:
            key = self.key_var.get()
            scale = self.scale_var.get()
            length = self.length_var.get()
            style = self.style_var.get()
            complexity = self.complexity_var.get()
            voicing = self.voicing_var.get()
            preserve_original_key = self.preserve_original_key_var.get()
            
            # If user wants to preserve original key, use C as the base key
            # and inform them that the progression will be in its original form
            generation_key = "C" if preserve_original_key else key
            
            self.update_status("Generating new progression...")
            
            progression = self.music_engine.generate_progression(
                key=generation_key,
                scale=scale,
                length=length,
                style=style,
                complexity=complexity
            )
            
            # If transposition was disabled, add a note about the original key
            if preserve_original_key and key != "C":
                for chord in progression:
                    chord['note'] = f"Generated in original key (C). Select different key and uncheck 'Preserve Original Key' to transpose."
            
            # Apply voicing to all chords
            for chord in progression:
                name = chord['name']
                root, intervals, chord_type = self.music_engine.chord_name_to_intervals(name)
                voiced_notes = self.music_engine.generate_chord_notes(root, intervals, voicing=voicing)
                chord['notes'] = voiced_notes
                chord['voicing'] = voicing
            
            # Display the generated progression
            self.display_generated_progression(progression, {
                'key': key,
                'scale': scale,
                'style': style,
                'complexity': complexity,
                'voicing': voicing
            })
            
            self.current_generated = progression
            self.update_status("Progression generated successfully")
            
        except Exception as e:
            messagebox.showerror("Generation Error", f"Error generating progression: {str(e)}")
            self.update_status("Generation failed")
    
    def generate_historical_progression(self):
        """Generate a progression based on historical styles."""
        if not MUSIC_THEORY_AVAILABLE or not self.music_engine:
            messagebox.showerror("Engine Error", "Music theory engine not available")
            return
        
        historical_style = self.historical_var.get()
        if historical_style == "none":
            messagebox.showwarning("No Style", "Please select a historical style first")
            return
        
        try:
            key = self.key_var.get()
            voicing = self.voicing_var.get()
            preserve_original_key = self.preserve_original_key_var.get()
            
            # If user wants to preserve original key, use C as the base key
            generation_key = "C" if preserve_original_key else key
            
            self.update_status(f"Generating {historical_style} progression...")
            
            progression = self.music_engine.generate_progression_from_historical(historical_style, generation_key)
            
            # If transposition was disabled, add a note about the original key
            if preserve_original_key and key != "C":
                for chord in progression:
                    chord['note'] = f"Generated in original key (C). Historical progressions preserve their traditional form."
            
            # Apply voicing
            for chord in progression:
                name = chord['name']
                root, intervals, chord_type = self.music_engine.chord_name_to_intervals(name)
                voiced_notes = self.music_engine.generate_chord_notes(root, intervals, voicing=voicing)
                chord['notes'] = voiced_notes
                chord['voicing'] = voicing
            
            # Display with historical context
            self.display_generated_progression(progression, {
                'key': key,
                'style': 'historical',
                'historical_style': historical_style,
                'voicing': voicing
            })
            
            self.current_generated = progression
            self.update_status(f"Historical progression generated: {historical_style}")
            
        except Exception as e:
            messagebox.showerror("Generation Error", f"Error generating historical progression: {str(e)}")
            self.update_status("Historical generation failed")
    
    def display_generated_progression(self, progression: List[Dict], params: Dict):
        """Display the generated progression."""
        self.generated_text.delete(1.0, tk.END)
        
        preserve_key = self.preserve_original_key_var.get()
        requested_key = self.key_var.get()
        
        output = f"GENERATED PROGRESSION\\n"
        output += f"{'='*50}\\n\\n"
        
        # Show transposition status
        if preserve_key and requested_key != "C":
            output += f"🔒 ORIGINAL KEY PRESERVED: Generated in key of C (as originally composed)\\n"
            output += f"   Selected Key: {requested_key} (not applied - uncheck 'Preserve Original Key' to transpose)\\n"
        else:
            output += f"Key: {params['key']} {params['scale']}\\n"
            if not preserve_key and requested_key != "C":
                output += f"✓ Transposed to {requested_key} (from original key of C)\\n"
        
        output += f"Style: {params['style']}\\n"
        output += f"Complexity: {params['complexity']:.2f}\\n\\n"
        
        output += f"CHORD SEQUENCE:\\n"
        for i, chord in enumerate(progression):
            name = chord['name']
            role = chord.get('role', 'Normal')
            notes = chord.get('notes', [])
            degree = chord.get('scaleDegree', '?')
            
            output += f"{i+1:2d}. {name:<10} | Role: {role:<12} | Degree: {degree:<2} | Notes: {notes}\\n"
        
        # Add chord voicings
        output += f"\\n\\nCHORD VOICINGS:\\n"
        for i, chord in enumerate(progression):
            name = chord['name']
            notes = chord.get('notes', [])
            if notes:
                note_names = [self.midi_to_note_name(note) for note in notes]
                output += f"{name}: {' - '.join(note_names)}\\n"
        
        # Add suggestions
        output += f"\\n\\nSUGGESTIONS:\\n"
        output += f"- Try different voicings by transposing up/down octaves\\n"
        output += f"- Add rhythmic variations to create interest\\n"
        output += f"- Consider inversions for smoother voice leading\\n"
        if params['complexity'] < 0.5:
            output += f"- Increase complexity for more sophisticated harmonies\\n"
        
        self.generated_text.insert(tk.END, output)
    
    def generate_variations(self):
        """Generate variations of the current progression."""
        if not hasattr(self, 'current_generated') or not self.current_generated:
            messagebox.showwarning("No Progression", "Please generate a progression first")
            return
        
        if not self.music_engine:
            return
        
        try:
            # Create fake analysis for expansion
            fake_analysis = ProgressionAnalysis(
                key=self.key_var.get(),
                scale=self.scale_var.get(),
                roman_numerals=[],
                chord_functions=[],
                modulations=[],
                borrowed_chords=[],
                secondary_dominants=[],
                complexity_score=self.complexity_var.get(),
                mood_tags=[]
            )
            
            variations = self.music_engine.expand_progression(self.current_generated, fake_analysis)
            
            if variations:
                # Show variations
                var_text = f"\\n\\nVARIATIONS & SUBSTITUTIONS:\\n"
                var_text += f"{'='*40}\\n"
                
                for i, var in enumerate(variations):
                    name = var['name']
                    original = var.get('originalChord', 'Unknown')
                    var_type = var.get('type', 'Substitution')
                    
                    var_text += f"{i+1}. {original} → {name} ({var_type})\\n"
                
                self.generated_text.insert(tk.END, var_text)
                self.update_status(f"Generated {len(variations)} variations")
            else:
                messagebox.showinfo("No Variations", "No suitable variations found for this progression")
                
        except Exception as e:
            messagebox.showerror("Variation Error", f"Error generating variations: {str(e)}")
    
    def generate_batch_variations(self):
        """Generate unlimited intelligent batch variations using advanced music theory."""
        if not hasattr(self, 'current_generated') or not self.current_generated:
            messagebox.showwarning("No Progression", "Please generate a base progression first")
            return
        
        if not self.music_engine:
            messagebox.showerror("Engine Error", "Music theory engine not available")
            return
        
        try:
            # Get all GUI parameters to ensure they're applied properly
            count = self.batch_count_var.get()
            technique = self.variation_technique_var.get()
            intelligence_level = self.intelligence_level_var.get()
            mode = self.generation_mode_var.get()
            naming_pattern = self.naming_pattern_var.get()
            
            # Core generation parameters
            key = self.key_var.get()
            scale = self.scale_var.get()
            style = self.style_var.get()
            complexity = self.complexity_var.get()
            voicing = self.voicing_var.get()
            length = self.length_var.get()
            preserve_original_key = self.preserve_original_key_var.get()
            
            # Variation options
            use_inversions = self.use_inversions_var.get()
            use_substitutions = self.use_substitutions_var.get()
            use_extensions = self.use_extensions_var.get()
            use_reharmonization = self.use_reharmonization_var.get()
            use_modal_interchange = self.use_modal_interchange_var.get()
            use_secondary_dominants = self.use_secondary_dominants_var.get()
            
            # Handle accumulative vs replace mode
            if mode == "accumulate" and hasattr(self, 'batch_variations') and self.batch_variations:
                existing_count = len(self.batch_variations)
                self.update_status(f"Adding {count} new variations to existing {existing_count}...")
            else:
                self.batch_variations = []
                existing_count = 0
                self.update_status(f"Generating {count} intelligent variations...")
            
            # Generate batch variations with all GUI parameters
            new_variations = self._create_intelligent_variations(
                self.current_generated,
                count,
                technique,
                intelligence_level,
                {
                    'inversions': use_inversions,
                    'substitutions': use_substitutions,
                    'extensions': use_extensions,
                    'reharmonization': use_reharmonization,
                    'modal_interchange': use_modal_interchange,
                    'secondary_dominants': use_secondary_dominants
                },
                naming_pattern,
                existing_count,  # Start numbering from existing count
                {
                    'key': key,
                    'scale': scale,
                    'style': style,
                    'complexity': complexity,
                    'voicing': voicing,
                    'length': length,
                    'preserve_original_key': preserve_original_key
                }
            )
            
            # Add to existing batch or replace
            if mode == "accumulate":
                self.batch_variations.extend(new_variations)
            else:
                self.batch_variations = new_variations
            
            # Display results summary
            batch_text = f"\\n\\n🎭 BATCH VARIATIONS GENERATED:\\n"
            batch_text += f"{'='*50}\\n"
            batch_text += f"Total Variations: {len(self.batch_variations)}\\n"
            batch_text += f"Technique: {technique.title()}\\n"
            batch_text += f"Intelligence Level: {intelligence_level:.1f}\\n"
            batch_text += f"\\nVariation Techniques Applied:\\n"
            
            for i, variation in enumerate(self.batch_variations[:5], 1):  # Show first 5 as preview
                variant_name = variation.get('variant_name', f"Variation {i}")
                techniques_used = ", ".join(variation.get('techniques_applied', []))
                batch_text += f"{i}. {variant_name} - {techniques_used}\\n"
            
            if len(self.batch_variations) > 5:
                batch_text += f"... and {len(self.batch_variations) - 5} more variations\\n"
            
            batch_text += f"\\n✅ Ready for export! Use 'Export Batch (Folder)' to save all variations.\\n"
            
            self.generated_text.insert(tk.END, batch_text)
            self.update_status(f"Generated {len(self.batch_variations)} intelligent variations")
            
        except Exception as e:
            messagebox.showerror("Batch Generation Error", f"Error generating batch variations: {str(e)}")
    
    def _create_intelligent_variations(self, base_progression, count, technique, intelligence_level, options, naming_pattern='intelligent', start_index=0, gui_params=None):
        """Create intelligent variations using advanced music theory techniques."""
        variations = []
        used_signatures = set()  # Track unique progressions to avoid duplicates
        
        # Add existing signatures if accumulating
        if hasattr(self, 'batch_variations') and self.batch_variations:
            for existing in self.batch_variations:
                used_signatures.add(existing.get('signature', ''))
        
        import random
        from datetime import datetime
        
        # Base data for variations - Use GUI parameters if provided
        if gui_params:
            base_key = gui_params.get('key', self.key_var.get())
            base_scale = gui_params.get('scale', self.scale_var.get())
            style = gui_params.get('style', 'pop')
            complexity = gui_params.get('complexity', 0.5)
            voicing = gui_params.get('voicing', 'close')
            length = gui_params.get('length', 4)
            preserve_original_key = gui_params.get('preserve_original_key', True)
        else:
            base_key = self.key_var.get()
            base_scale = self.scale_var.get()
            style = 'pop'
            complexity = 0.5
            voicing = 'close'
            length = 4
            preserve_original_key = True
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        
        # Music theory transformation options
        voicing_types = ['close', 'open', 'drop2', 'drop3', 'spread', 'shell', 'rootless']
        substitution_types = ['tritone', 'chromatic', 'diatonic', 'secondary_dominant']
        extension_types = ['7th', '9th', '11th', '13th', 'sus4', 'sus2', 'add9']
        
        for i in range(count):
            try:
                # Initialize techniques_applied at the start of each iteration
                techniques_applied = []
                variant_num = start_index + i + 1
                
                # Create deep copy of base progression
                variant_progression = []
                for chord in base_progression:
                    variant_progression.append({
                        'name': chord['name'],
                        'position': chord.get('position', i),
                        'duration': chord.get('duration', 1.0),
                        'velocity': chord.get('velocity', 100)
                    })
                
                # Generate actual chord progression if base is empty or too simple
                if len(variant_progression) <= 1 or all(c['name'] == variant_progression[0]['name'] for c in variant_progression):
                    variant_progression = self._generate_base_progression(base_key, base_scale, i, style, length)
                
                # Apply key transposition if not preserving original key
                if not preserve_original_key and base_key != "C":
                    variant_progression = self._transpose_progression(variant_progression, "C", base_key)
                    techniques_applied.append(f'transposed_to_{base_key}')
                
                # Apply complexity-based modifications
                if complexity > 0.6:
                    # Higher complexity: add more sophisticated chords
                    variant_progression = self._apply_complexity_enhancements(variant_progression, complexity)
                    techniques_applied.append('complexity_enhanced')
                
                # Apply style-specific modifications
                if style.lower() == 'jazz' and random.random() < 0.7:
                    variant_progression = self._apply_jazz_sophistication(variant_progression, complexity)
                    techniques_applied.append('jazz_sophistication')
                elif style.lower() == 'classical' and random.random() < 0.6:
                    variant_progression = self._apply_classical_voice_leading(variant_progression)
                    techniques_applied.append('classical_voice_leading')

                # Get style from GUI params for better naming
                style_name = gui_params.get('style', 'Modern') if gui_params else 'Modern'
                complexity_name = gui_params.get('complexity', intelligence_level) if gui_params else intelligence_level
                voicing_name = gui_params.get('voicing', 'close') if gui_params else 'close'
                
                # Generate intelligent naming based on pattern
                if naming_pattern == 'intelligent':
                    complexity_desc = "Simple" if complexity_name < 0.4 else "Advanced" if complexity_name < 0.7 else "Expert"
                    style_desc = style_name.title() if style_name else "Modern"
                    variant_name = f"{base_key}_{base_scale}_{style_desc}_{complexity_desc}_v{variant_num:03d}"
                elif naming_pattern == 'sequential':
                    variant_name = f"Progression_{variant_num:03d}_{timestamp}_{style_name.title()}"
                elif naming_pattern == 'technique_based':
                    primary_technique = technique.replace('_', ' ').title()
                    variant_name = f"{primary_technique}_{base_key}_{style_name.title()}_v{variant_num:03d}"
                elif naming_pattern == 'complexity_based':
                    complexity_level = "Simple" if intelligence_level < 0.4 else "Advanced" if intelligence_level < 0.7 else "Expert"
                    variant_name = f"{complexity_level}_{style_name.title()}_{base_key}_v{variant_num:03d}"
                elif naming_pattern == 'musical_style':
                    style_desc = style_name.title() if style_name else ("Classical" if intelligence_level < 0.5 else "Jazz" if intelligence_level < 0.8 else "Modern")
                    voicing_suffix = f"_{voicing_name}" if voicing_name != 'close' else ""
                    variant_name = f"{style_desc}_{base_key}_{base_scale}{voicing_suffix}_v{variant_num:03d}"
                else:
                    variant_name = f"Intelligent_Variation_{variant_num:03d}"
                
                # Apply techniques based on intelligence level and options
                if options['inversions'] and random.random() < intelligence_level:
                    variant_progression = self._apply_smart_inversions(variant_progression)
                    techniques_applied.append('smart_inversions')
                
                if options['substitutions'] and random.random() < intelligence_level * 0.8:
                    variant_progression = self._apply_intelligent_substitutions_batch(variant_progression, base_key)
                    techniques_applied.append('intelligent_substitutions')
                
                if options['extensions'] and random.random() < intelligence_level * 0.7:
                    variant_progression = self._apply_sophisticated_extensions_batch(variant_progression, intelligence_level)
                    techniques_applied.append('sophisticated_extensions')
                
                if options['reharmonization'] and random.random() < intelligence_level * 0.5:
                    variant_progression = self._apply_reharmonization_batch(variant_progression)
                    techniques_applied.append('reharmonization')
                
                if options['secondary_dominants'] and random.random() < intelligence_level * 0.6:
                    variant_progression = self._apply_secondary_dominants_batch(variant_progression)
                    techniques_applied.append('secondary_dominants')
                
                if options['modal_interchange'] and random.random() < intelligence_level * 0.4:
                    variant_progression = self._apply_modal_interchange_batch(variant_progression)
                    techniques_applied.append('modal_interchange')
                
                # Ensure we have meaningful variation - Enhanced diversity
                if not techniques_applied or random.random() < 0.3:
                    variant_progression = self._apply_random_musical_variation(variant_progression, i)
                    techniques_applied.append('musical_variation')
                
                # Apply additional diversity based on iteration number
                if i % 3 == 1:  # Every 3rd variation gets rhythm changes
                    variant_progression = self._apply_rhythm_changes(variant_progression)
                    techniques_applied.append('rhythm_variation')
                elif i % 3 == 2:  # Every 3rd variation gets reharmonization  
                    variant_progression = self._apply_intelligent_reharmonization(variant_progression, base_key)
                    techniques_applied.append('reharmonization')
                
                # Apply style-specific modifications from GUI
                if style == 'jazz':
                    variant_progression = self._apply_jazz_sophistication(variant_progression, complexity)
                    techniques_applied.append('jazz_sophistication')
                elif style == 'classical':
                    variant_progression = self._apply_classical_voice_leading(variant_progression)
                    techniques_applied.append('classical_voice_leading')
                elif style == 'ballad':
                    variant_progression = self._apply_ballad_harmonies(variant_progression, complexity)
                    techniques_applied.append('ballad_harmonies')
                elif style == 'blues':
                    variant_progression = self._apply_blues_characteristics(variant_progression, complexity)
                    techniques_applied.append('blues_characteristics')
                elif style == 'folk':
                    variant_progression = self._apply_folk_simplicity(variant_progression)
                    techniques_applied.append('folk_simplicity')
                elif style in ['modern', 'pop', 'rock']:
                    variant_progression = self._apply_modern_extensions(variant_progression)
                    techniques_applied.append('modern_extensions')
                
                # Add complexity enhancements based on GUI setting
                if complexity > 0.6:
                    variant_progression = self._apply_complexity_enhancements(variant_progression, complexity)
                    techniques_applied.append('complexity_enhancement')

                # Add voicing variations - Apply GUI voicing setting consistently
                chosen_voicing = voicing  # Use GUI voicing as primary choice
                if intelligence_level > 0.6 and random.random() < 0.3:
                    # 30% chance to use alternative voicing for variety
                    chosen_voicing = random.choice(voicing_types)
                
                # Apply voicing to ALL chords in progression
                for chord in variant_progression:
                    chord['voicing'] = chosen_voicing
                    chord['gui_voicing_applied'] = True
                    # Store original chord name for MIDI conversion
                    chord['original_name'] = chord['name']
                techniques_applied.append(f'voicing_{chosen_voicing}')

                # Apply spacing techniques
                if intelligence_level > 0.7 and random.random() < 0.3:
                    variant_progression = self._apply_spacing_techniques(variant_progression)
                    techniques_applied.append('advanced_spacing')

                # Create unique signature
                chord_signature = '|'.join([chord['name'] for chord in variant_progression])
                if chord_signature in used_signatures and len(variations) < count * 2:
                    continue  # Skip duplicate

                used_signatures.add(chord_signature)

                # Store variation with all GUI parameters preserved
                variations.append({
                    'progression': variant_progression,
                    'variant_name': variant_name,
                    'techniques_applied': techniques_applied,
                    'intelligence_level': intelligence_level,
                    'base_key': base_key,
                    'signature': chord_signature,
                    'uniqueness_score': len(techniques_applied) * intelligence_level,
                    'gui_params': {
                        'style': style,
                        'complexity': complexity,
                        'voicing': voicing,
                        'length': length,
                        'preserve_original_key': preserve_original_key
                    }
                })
                
            except Exception as e:
                print(f"Error creating variation {i}: {e}")
                continue
        
        return variations
    
    def _apply_smart_inversions(self, progression):
        """Apply smart inversion patterns for smoother voice leading."""
        import random
        
        for chord in progression:
            chord_name = chord['name']
            # Add inversion indicators to chord names
            if random.random() < 0.7:  # 70% chance of inversion
                inversion = random.choice(['', '/3', '/5', '/7'])
                if inversion and not any(x in chord_name for x in ['/', 'inv']):
                    chord['name'] = f"{chord_name}{inversion}"
                    chord['inversion'] = inversion.replace('/', '') if inversion else 'root'
        
        return progression
    
    def _apply_intelligent_substitutions_batch(self, progression, key):
        """Apply chord substitutions based on music theory."""
        import random
        
        substitutions = {
            'maj': ['maj7', 'add9', '6'],
            'min': ['min7', 'min9', 'min6'], 
            'dim': ['dim7', 'min7b5'],
            '7': ['9', '11', '13']
        }
        
        for chord in progression:
            chord_name = chord['name']
            base_quality = 'maj'
            
            if 'min' in chord_name.lower():
                base_quality = 'min'
            elif 'dim' in chord_name.lower():
                base_quality = 'dim'
            elif '7' in chord_name:
                base_quality = '7'
            
            # Apply substitution 40% of the time
            if random.random() < 0.4 and base_quality in substitutions:
                new_extension = random.choice(substitutions[base_quality])
                # Replace or add extension
                root = chord_name[:-3] if len(chord_name) > 3 else chord_name[0]
                chord['name'] = f"{root}{new_extension}"
        
        return progression
    
    def _apply_sophisticated_extensions_batch(self, progression, intelligence_level):
        """Apply chord extensions and alterations."""
        import random
        
        extensions = ['7', '9', '11', '13', 'add9', 'sus4', 'sus2']
        alterations = ['b5', '#5', 'b9', '#9', '#11', 'b13']
        
        for chord in progression:
            if random.random() < intelligence_level * 0.8:
                if random.random() < 0.6:  # Add extension
                    ext = random.choice(extensions)
                    if not any(e in chord['name'] for e in extensions):
                        chord['name'] = f"{chord['name']}{ext}"
                else:  # Add alteration  
                    alt = random.choice(alterations)
                    chord['name'] = f"{chord['name']}{alt}"
        
        return progression
    
    def _apply_reharmonization_batch(self, progression):
        """Apply reharmonization techniques.""" 
        import random
        
        # Common reharmonization patterns
        reharmonizations = {
            'maj': ['maj7#11', 'maj9', 'maj13'],
            'min': ['min11', 'minMaj7', 'min9'],
            '7': ['7alt', '7sus4', '13']
        }
        
        for i, chord in enumerate(progression):
            if random.random() < 0.3:  # 30% reharmonization chance
                for base_type in reharmonizations:
                    if base_type in chord['name'].lower():
                        new_chord = random.choice(reharmonizations[base_type])
                        root = chord['name'][0]  # Get root note
                        chord['name'] = f"{root}{new_chord}"
                        break
        
        return progression
    
    def _apply_secondary_dominants_batch(self, progression):
        """Add secondary dominant chords."""
        import random
        
        for i in range(len(progression) - 1):
            if random.random() < 0.25:  # 25% chance
                next_chord = progression[i + 1]['name']
                # Create dominant chord leading to next chord
                next_root = next_chord[0] if next_chord else 'C'
                dominant_root = self._transpose_note(next_root, -7)  # Fifth below
                progression[i]['name'] = f"{dominant_root}7"
        
        return progression
    
    def _apply_modal_interchange_batch(self, progression):
        """Apply modal interchange chords."""
        import random
        
        # Common borrowed chords from parallel minor/major
        modal_subs = {
            'maj': 'min', 'min': 'maj',
            'IV': 'iv', 'vi': 'VI'
        }
        
        for chord in progression:
            if random.random() < 0.2:  # 20% chance
                orig_name = chord['name']
                for pattern, replacement in modal_subs.items():
                    if pattern in orig_name:
                        chord['name'] = orig_name.replace(pattern, replacement)
                        break
        
        return progression
    
    def _apply_random_musical_variation(self, progression, variation_index):
        """Apply random but musical variations to ensure uniqueness."""
        import random
        
        # Vary by transposition occasionally
        if variation_index % 5 == 0 and random.random() < 0.3:
            transpose_steps = random.choice([-2, -1, 1, 2, 3, 5])  # Musical intervals
            for chord in progression:
                root = chord['name'][0] if chord['name'] else 'C'
                new_root = self._transpose_note(root, transpose_steps)
                chord_suffix = chord['name'][1:] if len(chord['name']) > 1 else 'maj'
                chord['name'] = f"{new_root}{chord_suffix}"
        
        # Add random chord quality changes
        if random.random() < 0.4:
            target_chord = random.choice(progression)
            qualities = ['maj', 'min', '7', 'maj7', 'min7', 'sus4', 'dim']
            new_quality = random.choice(qualities)
            root = target_chord['name'][0] if target_chord['name'] else 'C'
            target_chord['name'] = f"{root}{new_quality}"
        
        return progression
        import random
        inversions = ['', '/3', '/5']
        
        for i, chord in enumerate(progression):
            if random.random() < 0.4:
                inversion = random.choice(inversions)
                if inversion:
                    base_chord = chord['name'].split('/')[0]
                    chord['name'] = base_chord + inversion
        
        return progression
    
    def _apply_intelligent_substitutions_batch(self, progression, key):
        """Apply intelligent substitutions with music theory logic."""
        import random
        
        # Basic substitution patterns
        substitutions = {
            'C': ['Am', 'Em', 'F'], 'F': ['Dm', 'Am'], 'G': ['Em', 'Bm'],
            'Am': ['C', 'F'], 'Dm': ['F', 'Bb'], 'Em': ['G', 'C']
        }
        
        for chord in progression:
            if random.random() < 0.3:
                base = chord['name'].split('/')[0]
                if base in substitutions:
                    chord['name'] = random.choice(substitutions[base])
        
        return progression
    
    def _apply_sophisticated_extensions_batch(self, progression, intelligence_level):
        """Apply sophisticated harmonic extensions."""
        import random
        
        extensions = ['7', 'maj7', '9', '6', 'sus4', 'add9']
        advanced_extensions = ['11', '13', 'maj9', 'b5', '#5'] if intelligence_level > 0.8 else []
        
        for chord in progression:
            if random.random() < intelligence_level * 0.6:
                available_extensions = extensions + advanced_extensions
                extension = random.choice(available_extensions)
                base = chord['name'].split('/')[0]
                inversion = '/' + chord['name'].split('/')[1] if '/' in chord['name'] else ''
                chord['name'] = base + extension + inversion
        
        return progression
    
    def _apply_reharmonization_batch(self, progression):
        """Apply basic reharmonization techniques."""
        import random
        
        for chord in progression:
            if random.random() < 0.2:
                # Simple reharmonization - add passing chords or alterations
                if random.random() < 0.5:
                    chord['name'] = chord['name'] + '/5'  # Add bass note
                else:
                    chord['name'] = chord['name'] + 'sus4'  # Add suspension
        
        return progression
    
    def _apply_secondary_dominants_batch(self, progression):
        """Apply secondary dominant patterns."""
        import random
        
        for i, chord in enumerate(progression):
            if random.random() < 0.25 and i < len(progression) - 1:
                # Create V7/next_chord pattern
                next_chord = progression[i + 1]['name']
                if random.random() < 0.5:
                    chord['name'] = f"V7/{next_chord}"
        
        return progression
    
    def _apply_modal_interchange_batch(self, progression):
        """Apply modal interchange techniques."""
        import random
        
        modal_alterations = ['m', 'dim', 'aug', 'b5']
        
        for chord in progression:
            if random.random() < 0.15:
                alteration = random.choice(modal_alterations)
                chord['name'] = chord['name'] + alteration
        
        return progression
    
    def _apply_spacing_techniques(self, progression):
        """Apply advanced spacing and distribution techniques."""
        import random
        
        spacing_types = ['wide', 'close', 'mixed', 'clustered']
        chosen_spacing = random.choice(spacing_types)
        
        for chord in progression:
            chord['spacing'] = chosen_spacing
            if chosen_spacing == 'wide':
                chord['octave_spread'] = random.choice([2, 3, 4])
            elif chosen_spacing == 'clustered':
                chord['note'] = 'Uses adjacent semitones for modern harmony'
        
        return progression
    
    def _apply_spacing_techniques(self, progression):
        """Apply advanced spacing techniques to chord progression."""
        import random
        
        spacing_techniques = ['tight', 'wide', 'cluster', 'sparse']
        
        for chord in progression:
            # Add spacing indicators to chord metadata
            spacing_type = random.choice(spacing_techniques)
            chord['spacing'] = spacing_type
            
            # Modify velocity based on spacing
            if spacing_type == 'tight':
                chord['velocity'] = max(80, chord.get('velocity', 100) - 20)
            elif spacing_type == 'wide':
                chord['velocity'] = min(127, chord.get('velocity', 100) + 15)
            elif spacing_type == 'cluster':
                chord['cluster_voicing'] = True
            elif spacing_type == 'sparse':
                chord['sparse_voicing'] = True
        
        return progression
    
    def _apply_rhythm_changes(self, progression):
        """Apply rhythmic variations to chord progression."""
        import random
        
        for chord in progression:
            # Add rhythmic variation markers
            rhythm_patterns = ['syncopated', 'offbeat', 'straight', 'swing', 'latin']
            chord['rhythm_pattern'] = random.choice(rhythm_patterns)
            
            # Modify timing based on pattern
            if chord['rhythm_pattern'] == 'syncopated':
                chord['timing'] = 'anticipate_beat'
            elif chord['rhythm_pattern'] == 'latin':
                chord['timing'] = 'clave_pattern'
        
        return progression
    
    def _apply_intelligent_reharmonization(self, progression, key):
        """Apply sophisticated reharmonization techniques."""
        import random
        
        substitution_map = {
            'C': ['Am7', 'F6', 'Em7b5'],
            'Dm': ['F', 'Bb', 'Gm'],
            'Em': ['C', 'Am', 'G'],
            'F': ['Dm7', 'Bb', 'Am7b5'],
            'G': ['Em7', 'C', 'Bm7b5'],
            'Am': ['F', 'C', 'Dm']
        }
        
        for chord in progression:
            if random.random() < 0.25:  # 25% chance of reharmonization
                chord_root = chord['name'].split('m')[0].split('7')[0].split('M')[0]
                if chord_root in substitution_map:
                    new_chord = random.choice(substitution_map[chord_root])
                    chord['name'] = new_chord
                    chord['reharmonized'] = True
        
        return progression
    
    def _apply_jazz_sophistication(self, progression, complexity):
        """Apply jazz-specific harmonic sophistication based on complexity level."""
        import random
        
        # Scale jazz extensions by complexity level
        if complexity < 0.3:
            # Simple jazz - just add 7ths
            jazz_extensions = ['7', 'maj7']
            application_chance = 0.4
        elif complexity < 0.6:
            # Medium jazz - add 9ths and some alterations
            jazz_extensions = ['7', 'maj7', '9', 'add9']
            application_chance = 0.6
        elif complexity < 0.8:
            # Advanced jazz - extended harmonies
            jazz_extensions = ['9', '11', '13', 'maj9', '#11', 'add9']
            application_chance = 0.7
        else:
            # Expert jazz - sophisticated alterations
            jazz_extensions = ['9', '11', '13', 'maj9', '#11', 'b13', 'alt', '#5']
            application_chance = 0.8
        
        for chord in progression:
            if random.random() < application_chance:
                # Don't double-extend already extended chords
                if not any(ext in chord['name'] for ext in ['7', '9', '11', '13']):
                    extension = random.choice(jazz_extensions)
                    chord['name'] = chord['name'] + extension
                    chord['jazz_enhanced'] = True
                    chord['complexity_applied'] = complexity
        
        return progression
    
    def _apply_classical_voice_leading(self, progression):
        """Apply classical voice leading principles with style-appropriate harmonies."""
        import random
        
        # Classical progressions favor traditional harmony
        for i, chord in enumerate(progression):
            chord_name = chord['name']
            
            # Add appropriate classical extensions (avoid jazz alterations)
            if random.random() < 0.3:
                # Classical music uses simpler extensions
                if 'maj' in chord_name and '7' not in chord_name:
                    if random.random() < 0.5:
                        chord['name'] = chord_name + 'maj7'  # Add major 7th
                elif 'min' in chord_name and '7' not in chord_name:
                    if random.random() < 0.3:
                        chord['name'] = chord_name + '7'  # Add minor 7th sparingly
                        
            # Apply voice leading techniques
            voice_leading_techniques = ['stepwise_bass', 'contrary_motion', 'parallel_thirds']
            technique = random.choice(voice_leading_techniques)
            chord['voice_leading'] = technique
            
            # Classical-specific voicing preferences
            chord['classical_voicing'] = True
            chord['avoid_jazz_extensions'] = True
            
            if technique == 'stepwise_bass' and i > 0:
                chord['bass_movement'] = 'stepwise'
            elif technique == 'parallel_thirds':
                chord['parallel_motion'] = True
        
        return progression
    
    def _apply_modern_extensions(self, progression):
        """Apply modern harmonic extensions and alterations."""
        import random
        
        # Modern music uses contemporary chord extensions
        modern_alterations = ['sus2', 'sus4', 'add9', 'add11']
        advanced_modern = ['#11', 'b9', '#9', '2']
        
        for chord in progression:
            if random.random() < 0.5:
                # Use basic modern extensions most of the time
                if random.random() < 0.7:
                    alteration = random.choice(modern_alterations)
                else:
                    alteration = random.choice(advanced_modern)
                
                # Don't add extensions to already complex chords
                if not any(ext in chord['name'] for ext in ['7', '9', '11', '13', 'sus']):
                    chord['name'] = chord['name'] + alteration
                    chord['modern_enhanced'] = True
        
        return progression
    
    def _apply_complexity_enhancements(self, progression, complexity):
        """Apply complexity-based enhancements to progression with proper scaling."""
        import random
        
        for chord in progression:
            chord_name = chord['name']
            
            # Avoid adding to already complex chords
            if any(ext in chord_name for ext in ['7', '9', '11', '13', 'sus', 'add', 'alt']):
                continue
                
            if complexity < 0.3:
                # Low complexity - keep it simple, maybe add a 7th
                if random.random() < 0.2:
                    if 'maj' in chord_name:
                        chord['name'] = chord_name + 'maj7'
                    elif 'min' in chord_name:
                        chord['name'] = chord_name + '7'
                    chord['complexity_level'] = 'simple'
                    
            elif complexity < 0.6:
                # Medium complexity - add moderate extensions
                if random.random() < 0.4:
                    med_alterations = ['7', '9', 'sus4', 'add9']
                    extension = random.choice(med_alterations)
                    chord['name'] = chord_name + extension
                    chord['complexity_level'] = 'medium'
                    
            elif complexity < 0.8:
                # High complexity - more sophisticated harmonies
                if random.random() < 0.6:
                    advanced_alterations = ['9', '11', 'maj9', '#11', 'add9']
                    extension = random.choice(advanced_alterations)
                    chord['name'] = chord_name + extension
                    chord['complexity_level'] = 'advanced'
                    
            else:
                # Expert complexity - very sophisticated alterations
                if random.random() < 0.7:
                    expert_alterations = ['11', '13', '#11', 'b13', 'maj13', '#5']
                    extension = random.choice(expert_alterations)
                    chord['name'] = chord_name + extension
                    chord['complexity_level'] = 'expert'
        
        return progression
    
    def _apply_ballad_harmonies(self, progression, complexity):
        """Apply ballad-specific harmonic characteristics."""
        import random
        
        # Ballads favor emotional, stable harmonies
        for chord in progression:
            chord_name = chord['name']
            
            # Ballads use tasteful extensions, not overly complex
            if random.random() < 0.4:
                if complexity < 0.5:
                    # Simple ballad harmonies
                    if 'maj' in chord_name and '7' not in chord_name:
                        if random.random() < 0.6:
                            chord['name'] = chord_name + 'maj7'  # Warm major 7th
                elif complexity < 0.8:
                    # Medium ballad complexity
                    ballad_extensions = ['maj7', 'add9', 'sus4', '6']
                    if not any(ext in chord_name for ext in ['7', '9', 'sus']):
                        chord['name'] = chord_name + random.choice(ballad_extensions)
                else:
                    # Advanced ballad harmonies
                    advanced_ballad = ['maj9', 'add9', 'sus2', '6/9', 'sus4']
                    if not any(ext in chord_name for ext in ['7', '9', 'sus']):
                        chord['name'] = chord_name + random.choice(advanced_ballad)
                        
            chord['ballad_style'] = True
            chord['emotional_weight'] = 'high'
        
        return progression
    
    def _apply_blues_characteristics(self, progression, complexity):
        """Apply blues-specific harmonic characteristics."""
        import random
        
        # Blues heavily features dominant 7th chords
        for chord in progression:
            chord_name = chord['name']
            
            # Blues almost always uses 7th chords
            if random.random() < 0.8:
                if '7' not in chord_name and 'maj7' not in chord_name:
                    if 'maj' in chord_name:
                        chord['name'] = chord_name.replace('maj', '7')  # Dominant 7th
                    elif 'min' not in chord_name:
                        chord['name'] = chord_name + '7'  # Add dominant 7th
                    else:
                        chord['name'] = chord_name + '7'  # Minor 7th
                        
            # Add blues-specific extensions based on complexity
            if complexity > 0.5 and random.random() < 0.3:
                blues_extensions = ['9', 'b9', '#9', '13']
                if '7' in chord['name'] and not any(ext in chord_name for ext in ['9', '13']):
                    chord['name'] = chord['name'] + random.choice(blues_extensions)
                    
            chord['blues_style'] = True
            chord['swing_feel'] = True
        
        return progression
    
    def _apply_folk_simplicity(self, progression):
        """Apply folk-specific harmonic characteristics - keep it simple."""
        import random
        
        # Folk music avoids complex extensions
        for chord in progression:
            chord_name = chord['name']
            
            # Folk occasionally uses simple additions
            if random.random() < 0.2:
                folk_additions = ['sus4', 'sus2', 'add9']
                if not any(ext in chord_name for ext in ['7', '9', 'sus']):
                    chord['name'] = chord_name + random.choice(folk_additions)
                    
            chord['folk_style'] = True
            chord['acoustic_friendly'] = True
            chord['avoid_extensions'] = True
        
        return progression
    
    def preview_random_variation(self):
        """Preview a random variation from the generated batch."""
        if not hasattr(self, 'batch_variations') or not self.batch_variations:
            messagebox.showwarning("No Variations", "Please generate batch variations first")
            return
        
        import random
        random_var = random.choice(self.batch_variations)
        
        # Display preview
        preview_text = f"\\n\\n🎵 RANDOM VARIATION PREVIEW:\\n"
        preview_text += f"{'='*40}\\n"
        preview_text += f"Name: {random_var['variant_name']}\\n"
        preview_text += f"Techniques: {', '.join(random_var['techniques_applied'])}\\n"
        preview_text += f"Uniqueness Score: {random_var['uniqueness_score']:.2f}\\n"
        preview_text += f"\\nChord Progression:\\n"
        
        for i, chord in enumerate(random_var['progression'], 1):
            chord_info = f"{i}. {chord['name']}"
            if chord.get('voicing'):
                chord_info += f" ({chord['voicing']} voicing)"
            preview_text += chord_info + "\\n"
        
        self.generated_text.insert(tk.END, preview_text)
    
    def export_batch_variations(self):
        """Export all batch variations to a folder with individual progression files."""
        if not hasattr(self, 'batch_variations') or not self.batch_variations:
            messagebox.showwarning("No Variations", "Please generate batch variations first")
            return
        
        # Select export folder
        folder = safe_askdirectory(title="Select Folder for Batch Export")
        if not folder:
            return
        
        try:
            import os
            from datetime import datetime
            
            # Create timestamped batch folder
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            batch_folder = os.path.join(folder, f"Intelligent_Variations_{timestamp}")
            os.makedirs(batch_folder, exist_ok=True)
            
            exported_count = 0
            
            for variation in self.batch_variations:
                try:
                    # Convert chord progressions to MPC-compatible format with MIDI notes
                    mpc_chords = []
                    for pos, chord in enumerate(variation['progression']):
                        try:
                            # Get MIDI notes for this chord using music theory engine
                            chord_name = chord['name']
                            
                            # Extract root note from chord name for proper conversion
                            root_note = chord_name[0] if chord_name else variation['base_key']
                            if len(chord_name) > 1 and chord_name[1] in ['#', 'b']:
                                root_note = chord_name[:2]
                            
                            # Generate MIDI notes using enhanced conversion with proper octave
                            midi_notes = self._chord_name_to_midi_notes(chord_name, root_note, 4)
                            
                            # Apply GUI voicing setting if specified
                            gui_voicing = variation.get('gui_params', {}).get('voicing', 'close')
                            if chord.get('voicing'):
                                # Use chord-specific voicing if set
                                midi_notes = self._apply_voicing_to_notes(midi_notes, chord['voicing'])
                            else:
                                # Use GUI voicing setting
                                midi_notes = self._apply_voicing_to_notes(midi_notes, gui_voicing)
                            
                            # Apply inversion if specified  
                            if 'inversion' in chord and chord['inversion'] != 'root':
                                midi_notes = self._apply_inversion_to_notes(midi_notes, chord['inversion'])
                            
                            # Create MPC-compatible chord structure
                            mpc_chord = {
                                "note": midi_notes,  # Array of MIDI note numbers
                                "role": "chord",     # MPC role designation
                                "beat": pos + 1      # Beat position (1-based)
                            }
                            mpc_chords.append(mpc_chord)
                            
                        except Exception as e:
                            print(f"Error converting chord {chord.get('name', 'Unknown')}: {e}")
                            # Fallback based on position to ensure variation
                            fallback_notes = [60 + (pos * 2), 64 + (pos * 2), 67 + (pos * 2)]  # Different for each position
                            mpc_chords.append({
                                "note": fallback_notes,
                                "role": "chord", 
                                "beat": pos + 1
                            })
                    
                    # Create MPC-compatible progression file structure with full GUI parameters
                    gui_params = variation.get('gui_params', {})
                    progression_data = {
                        "name": variation['variant_name'],
                        "rootNote": variation['base_key'],
                        "scale": f"{variation['base_key']} {gui_params.get('scale', self.scale_var.get()).title()}",
                        "recordingOctave": 4,
                        "chords": mpc_chords,  # Now contains proper MIDI note arrays
                        "metadata": {
                            "generated": True,
                            "variation_type": "intelligent_batch",
                            "techniques_applied": variation['techniques_applied'],
                            "intelligence_level": variation['intelligence_level'], 
                            "uniqueness_score": variation['uniqueness_score'],
                            "batch_export": True,
                            "mpc_compatible": True,
                            "gui_parameters_applied": {
                                "style": gui_params.get('style', 'pop'),
                                "complexity": gui_params.get('complexity', 0.5),
                                "voicing": gui_params.get('voicing', 'close'),
                                "length": gui_params.get('length', 4),
                                "preserve_original_key": gui_params.get('preserve_original_key', True),
                                "key_transposed": not gui_params.get('preserve_original_key', True)
                            },
                            "engine": "XPM Advanced Music Theory Engine v2.0 - Intelligent Batch Generator"
                        }
                    }
                    
                    # Save individual progression file
                    filename = os.path.join(batch_folder, f"{variation['variant_name']}.progression")
                    with open(filename, 'w') as f:
                        json.dump(progression_data, f, indent=2)
                    
                    # Add to music engine library
                    if self.music_engine:
                        chord_names = [chord['name'] for chord in variation['progression']]
                        self.music_engine.add_progression_to_library(
                            name=variation['variant_name'],
                            chords=chord_names,
                            key=variation['base_key'],
                            scale=self.scale_var.get(),
                            mood_tags=variation['techniques_applied'],
                            complexity=variation['uniqueness_score'],
                            source_file=filename
                        )
                    
                    exported_count += 1
                    
                except Exception as e:
                    print(f"Error exporting {variation['variant_name']}: {e}")
            
            # Create batch summary
            summary_file = os.path.join(batch_folder, "BATCH_EXPORT_SUMMARY.txt")
            with open(summary_file, 'w') as f:
                f.write("🎭 INTELLIGENT BATCH VARIATIONS - EXPORT SUMMARY\\n")
                f.write("="*60 + "\\n")
                f.write(f"Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n")
                f.write(f"Total Variations: {len(self.batch_variations)}\\n")
                f.write(f"Successfully Exported: {exported_count}\\n")
                f.write(f"Base Key: {self.batch_variations[0]['base_key']}\\n")
                f.write(f"Intelligence Level: {self.batch_variations[0]['intelligence_level']:.1f}\\n")
                f.write(f"\\nINTELLIGENT MUSIC THEORY TECHNIQUES USED:\\n")
                f.write("-" * 50 + "\\n")
                
                # Collect all techniques used
                all_techniques = set()
                for var in self.batch_variations:
                    all_techniques.update(var['techniques_applied'])
                
                for technique in sorted(all_techniques):
                    count = sum(1 for var in self.batch_variations if technique in var['techniques_applied'])
                    f.write(f"• {technique.replace('_', ' ').title()}: {count} variations\\n")
                
                f.write(f"\\nDETAILED VARIATION LIST:\\n")
                f.write("-" * 30 + "\\n")
                for i, var in enumerate(self.batch_variations, 1):
                    f.write(f"{i:3d}. {var['variant_name']}\\n")
                    f.write(f"     🎵 Chords: {' | '.join([c['name'] for c in var['progression']])}\\n")
                    f.write(f"     🧠 Techniques: {', '.join(var['techniques_applied'])}\\n")
                    f.write(f"     ⭐ Uniqueness: {var['uniqueness_score']:.2f}\\n\\n")
            
            messagebox.showinfo("Batch Export Complete", 
                              f"🎉 Successfully exported {exported_count} intelligent variations!\\n\\n" +
                              f"📁 Location: {batch_folder}\\n\\n" +
                              f"🎭 Each variation uses different advanced music theory techniques:\\n" +
                              f"• Inversions & Voice Leading\\n" +
                              f"• Intelligent Chord Substitutions\\n" +
                              f"• Sophisticated Extensions & Alterations\\n" +
                              f"• Classical & Jazz Reharmonization\\n" +
                              f"• Modern Spacing & Voicing Techniques\\n\\n" +
                              f"🧠 The algorithm ensures each progression is unique!")
            
            self.update_status(f"Exported {exported_count} intelligent variations")
            self.refresh_library()
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Error exporting batch variations: {str(e)}")
    
    def _chord_name_to_midi_notes(self, chord_name, root_note, octave):
        """Convert chord name to MIDI notes array for MPC compatibility."""
        try:
            # Basic note-to-MIDI mapping
            note_to_midi = {
                'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5,
                'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8, 'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11
            }
            
            # Enhanced chord intervals (semitones from root)
            chord_intervals = {
                'maj': [0, 4, 7],
                'min': [0, 3, 7], 
                'm': [0, 3, 7],
                'dim': [0, 3, 6],
                'aug': [0, 4, 8],
                '7': [0, 4, 7, 10],
                'maj7': [0, 4, 7, 11],
                'min7': [0, 3, 7, 10],
                'm7': [0, 3, 7, 10],
                'dim7': [0, 3, 6, 9],
                'sus4': [0, 5, 7],
                'sus2': [0, 2, 7],
                '9': [0, 4, 7, 10, 14],
                'm9': [0, 3, 7, 10, 14],
                'maj9': [0, 4, 7, 11, 14],
                'add9': [0, 4, 7, 14],
                '11': [0, 4, 7, 10, 14, 17],
                '13': [0, 4, 7, 10, 14, 17, 21]
            }
            
            # Parse root note from chord name
            chord_upper = chord_name.upper()
            root = None
            
            # Extract root note (handle sharps and flats)
            if len(chord_upper) >= 2 and chord_upper[1] in ['#', 'B']:  # Sharp or flat
                root = chord_upper[:2]
            else:  # Natural note
                root = chord_upper[0] if chord_upper else 'C'
            
            # Fallback to provided root_note if parsing fails
            if root not in note_to_midi:
                root = str(root_note).upper() if root_note else 'C'
            
            # Parse chord type from the remaining part
            chord_suffix = chord_name[len(root):] if len(chord_name) > len(root) else ''
            chord_type = 'maj'  # default
            
            # Enhanced chord type detection
            suffix_lower = chord_suffix.lower()
            if 'm97' in suffix_lower or 'min97' in suffix_lower:
                chord_type = 'm9'  # Treat as minor 9th
            elif 'm9' in suffix_lower or 'min9' in suffix_lower:
                chord_type = 'm9'
            elif 'maj9' in suffix_lower:
                chord_type = 'maj9'
            elif 'min7' in suffix_lower or 'm7' in suffix_lower:
                chord_type = 'min7'
            elif 'maj7' in suffix_lower:
                chord_type = 'maj7'
            elif 'min' in suffix_lower or suffix_lower.startswith('m'):
                chord_type = 'min'
            elif 'dim7' in suffix_lower:
                chord_type = 'dim7'
            elif 'dim' in suffix_lower:
                chord_type = 'dim'
            elif 'aug' in suffix_lower:
                chord_type = 'aug'
            elif '13' in suffix_lower:
                chord_type = '13'
            elif '11' in suffix_lower:
                chord_type = '11'
            elif '9' in suffix_lower:
                chord_type = '9'
            elif '7' in suffix_lower:
                chord_type = '7'
            elif 'sus4' in suffix_lower:
                chord_type = 'sus4'
            elif 'sus2' in suffix_lower:
                chord_type = 'sus2'
            elif 'add9' in suffix_lower:
                chord_type = 'add9'
                
            # Get root MIDI note
            root_midi = (octave * 12) + note_to_midi.get(root, 0)
            
            # Build MIDI notes array
            intervals = chord_intervals.get(chord_type, [0, 4, 7])
            midi_notes = [root_midi + interval for interval in intervals]
            
            # Ensure notes are in valid MIDI range (0-127)
            midi_notes = [note for note in midi_notes if 0 <= note <= 127]
            
            return midi_notes if midi_notes else [60, 64, 67]  # Fallback to C major
            
        except Exception as e:
            print(f"Error converting chord {chord_name}: {e}")
            print(f"Debug: chord_name='{chord_name}', root_note='{root_note}', octave={octave}")
            return [60, 64, 67]  # C major triad fallback
    
    def _apply_voicing_to_notes(self, midi_notes, voicing_type):
        """Apply different voicing techniques to MIDI notes."""
        if not midi_notes or len(midi_notes) < 3:
            return midi_notes
            
        try:
            notes = sorted(list(midi_notes))  # Sort notes ascending
            
            if voicing_type == 'drop2':
                # Drop the second highest note down an octave
                if len(notes) >= 3:
                    second_highest = notes[-2]
                    notes[-2] = max(48, second_highest - 12)  # Ensure not too low
            elif voicing_type == 'drop3':
                # Drop the third highest note down an octave  
                if len(notes) >= 4:
                    third_highest = notes[-3]
                    notes[-3] = max(48, third_highest - 12)
                elif len(notes) == 3:
                    # For triads, drop the middle note
                    notes[1] = max(48, notes[1] - 12)
            elif voicing_type == 'spread':
                # Spread notes across wider range but maintain clarity
                bass_note = notes[0]
                for i in range(1, len(notes)):
                    notes[i] = bass_note + (i * 7) + (i * 2)  # Add 5ths plus extra spacing
            elif voicing_type == 'close':
                # Keep all notes within one octave of bass note
                bass_note = notes[0]
                for i in range(1, len(notes)):
                    while notes[i] - bass_note > 12:
                        notes[i] -= 12
                    notes[i] = max(bass_note, notes[i])  # Don't go below bass
            elif voicing_type == 'open':
                # Open voicing - spread notes but not as wide as spread
                bass_note = notes[0]
                if len(notes) >= 4:
                    # Move higher notes up an octave selectively
                    notes[2] += 12  # Move third up
                    if len(notes) >= 5:
                        notes[4] += 12  # Move fifth up if exists
            elif voicing_type == 'shell':
                # Shell voicing - root, 3rd, 7th only (most important notes)
                if len(notes) >= 4:
                    notes = [notes[0], notes[1], notes[3]]  # 1, 3, 7
                elif len(notes) == 3:
                    notes = notes  # Keep triad as is
            elif voicing_type == 'rootless':
                # Remove root note, emphasize upper structure
                if len(notes) > 2:
                    notes = notes[1:]  # Remove lowest note (root)
                    # Ensure remaining notes are in good range
                    notes = [max(48, note) for note in notes]
            
            # Ensure all notes stay in optimal range (48-84)
            notes = [max(48, min(84, note)) for note in notes]
            
            # Sort final notes for consistent ordering
            return sorted(notes)
            
        except Exception as e:
            print(f"Error applying voicing {voicing_type}: {e}")
            return sorted(midi_notes)
    
    def _apply_inversion_to_notes(self, midi_notes, inversion):
        """Apply chord inversions to MIDI notes."""
        if not midi_notes or len(midi_notes) < 2:
            return midi_notes
            
        try:
            notes = sorted(list(midi_notes))  # Sort ascending
            
            if inversion == '3' or inversion == '/3':  # First inversion
                # Move root note up an octave
                root = notes[0]
                notes[0] = min(84, root + 12)  # Move up octave but keep in range
                notes = sorted(notes)  # Re-sort
            elif inversion == '5' or inversion == '/5':  # Second inversion
                # Move root and third up an octave
                if len(notes) >= 3:
                    for i in range(2):  # Move first two notes
                        notes[i] = min(84, notes[i] + 12)
                    notes = sorted(notes)
            elif inversion == '7' or inversion == '/7':  # Third inversion
                # Move root, third, and fifth up an octave
                if len(notes) >= 4:
                    for i in range(3):  # Move first three notes
                        notes[i] = min(84, notes[i] + 12)
                    notes = sorted(notes)
            
            # Ensure notes stay in optimal range (48-84)
            notes = [max(48, min(84, note)) for note in notes]
            return notes
            
        except Exception as e:
            print(f"Error applying inversion {inversion}: {e}")
            return sorted(midi_notes)
    
    def _generate_base_progression(self, key, scale, variation_index, style='pop', length=4):
        """Generate a musical chord progression based on key, scale, style, and length."""
        import random
        
        # Define chord progressions for different styles and scales
        progressions_major = {
            'pop': [
                ['I', 'V', 'vi', 'IV'],  # Pop progression
                ['I', 'vi', 'IV', 'V'],  # 50s progression  
                ['vi', 'IV', 'I', 'V'],  # Modern pop
                ['I', 'VIm', 'IIm', 'V'], # Pop ballad
            ],
            'jazz': [
                ['IIm7', 'V7', 'Imaj7', 'VImaj7'],  # ii-V-I
                ['Imaj7', 'VIm7', 'IIm7', 'V7'],    # Jazz standard
                ['IIIm7', 'VIm7', 'IIm7', 'V7'],   # Circle of fifths
                ['Imaj7', 'IIIm7', 'VIm7', 'IIm7'], # Jazz cycle
            ],
            'rock': [
                ['I', 'VII', 'IV', 'I'],  # Rock progression
                ['I', 'V', 'VIm', 'IV'], # Rock ballad
                ['I', 'III', 'IV', 'V'], # Classic rock
                ['VIm', 'V', 'I', 'IV'], # Alternative rock
            ],
            'classical': [
                ['I', 'IV', 'V', 'I'],   # Classical cadence
                ['I', 'VIm', 'IV', 'V'], # Classical progression
                ['I', 'III', 'VIm', 'IV'], # Baroque style
                ['I', 'ii', 'V', 'I'],   # Simple classical
            ],
            'ballad': [
                ['I', 'VIm', 'IV', 'V'],  # Classic ballad
                ['VIm', 'IV', 'I', 'V'],  # Emotional ballad
                ['I', 'V', 'VIm', 'IV'],  # Power ballad 
                ['I', 'IIm', 'V', 'VIm'], # Tender ballad
            ],
            'blues': [
                ['I7', 'IV7', 'I7', 'V7'], # 12-bar blues condensed
                ['I7', 'I7', 'IV7', 'I7'], # Blues variation
                ['VIm', 'IV7', 'I7', 'V7'], # Minor blues feel
            ],
            'folk': [
                ['I', 'V', 'VIm', 'IV'],  # Folk standard
                ['I', 'IV', 'V', 'I'],    # Traditional folk
                ['VIm', 'IV', 'I', 'V'],  # Modern folk
            ]
        }
        
        progressions_minor = {
            'pop': [
                ['i', 'VII', 'VI', 'VII'], # Natural minor
                ['i', 'v', 'VI', 'III'],   # Harmonic minor feel
                ['i', 'iv', 'VII', 'i'],   # Phrygian cadence
                ['VIm', 'IV', 'I', 'V'],   # Relative major feel
            ],
            'jazz': [
                ['im7', 'iv7', 'VII7', 'IIImaj7'], # Minor jazz
                ['im7', 'IVm7', 'VIImaj7', 'IIImaj7'], # Modal jazz
                ['iim7b5', 'V7', 'im7', 'im7'], # Minor ii-V-i
                ['im7', 'imaj7', 'iv7', 'VII7'], # Melodic minor jazz
            ],
            'rock': [
                ['i', 'VII', 'VI', 'VII'], # Minor rock
                ['i', 'VI', 'VII', 'i'],   # Metal progression
                ['i', 'iv', 'v', 'i'],     # Dorian rock
                ['i', 'III', 'VII', 'VI'], # Alternative minor
            ],
            'classical': [
                ['i', 'ii°', 'V', 'i'],    # Minor classical
                ['i', 'VI', 'III', 'VII'], # Classical minor
                ['i', 'iv', 'V', 'i'],     # Simple classical minor
                ['i', 'ii°', 'V7', 'i'],   # Harmonic minor classical
            ],
            'ballad': [
                ['i', 'VI', 'III', 'VII'], # Minor ballad
                ['i', 'iv', 'VII', 'III'], # Emotional minor ballad
                ['i', 'v', 'VI', 'VII'],   # Dramatic ballad
                ['i', 'ii°', 'V', 'i'],    # Classical ballad minor
            ],
            'blues': [
                ['i7', 'iv7', 'i7', 'V7'],  # Minor blues
                ['i7', 'i7', 'iv7', 'i7'],  # Traditional minor blues
                ['i', 'IV7', 'i', 'V7'],    # Mixed minor blues
            ],
            'folk': [
                ['i', 'VII', 'VI', 'VII'],  # Folk minor
                ['i', 'iv', 'V', 'i'],      # Traditional folk minor
                ['i', 'VI', 'VII', 'i'],    # Celtic minor
            ]
        }
        
        # Select progression based on scale and style
        valid_styles = ['pop', 'jazz', 'rock', 'classical', 'ballad', 'blues', 'folk']
        style_key = style.lower() if style.lower() in valid_styles else 'pop'
        
        if 'major' in scale.lower():
            available_progressions = progressions_major.get(style_key, progressions_major['pop'])
            progression_template = random.choice(available_progressions)
            chord_map = {
                'I': f"{key}maj", 'Imaj7': f"{key}maj7", 
                'ii': f"{self._transpose_note(key, 1)}min", 'IIm7': f"{self._transpose_note(key, 1)}min7",
                'iii': f"{self._transpose_note(key, 2)}min", 'III': f"{self._transpose_note(key, 2)}maj", 'IIIm7': f"{self._transpose_note(key, 2)}min7",
                'IV': f"{self._transpose_note(key, 3)}maj", 'IVmaj7': f"{self._transpose_note(key, 3)}maj7",
                'V': f"{self._transpose_note(key, 4)}maj", 'V7': f"{self._transpose_note(key, 4)}7",
                'vi': f"{self._transpose_note(key, 5)}min", 'VIm': f"{self._transpose_note(key, 5)}min", 'VIm7': f"{self._transpose_note(key, 5)}min7", 'VImaj7': f"{self._transpose_note(key, 5)}maj7",
                'VII': f"{self._transpose_note(key, 6)}maj"
            }
        else:  # minor or other
            available_progressions = progressions_minor.get(style_key, progressions_minor['pop'])
            progression_template = random.choice(available_progressions)
            chord_map = {
                'i': f"{key}min", 'im7': f"{key}min7",
                'ii°': f"{self._transpose_note(key, 1)}dim", 'iim7b5': f"{self._transpose_note(key, 1)}min7b5",
                'III': f"{self._transpose_note(key, 2)}maj", 'IIImaj7': f"{self._transpose_note(key, 2)}maj7",
                'iv': f"{self._transpose_note(key, 3)}min", 'IVm7': f"{self._transpose_note(key, 3)}min7",
                'v': f"{self._transpose_note(key, 4)}min", 'V': f"{self._transpose_note(key, 4)}maj", 'V7': f"{self._transpose_note(key, 4)}7",
                'VI': f"{self._transpose_note(key, 5)}maj", 'VImaj7': f"{self._transpose_note(key, 5)}maj7",
                'VII': f"{self._transpose_note(key, 6)}maj", 'VIImaj7': f"{self._transpose_note(key, 6)}maj7"
            }
        
        # Adjust progression length to match desired length
        if len(progression_template) > length:
            progression_template = progression_template[:length]
        elif len(progression_template) < length:
            # Extend progression by repeating or adding logical chords
            while len(progression_template) < length:
                if style_key == 'jazz':
                    progression_template.extend(['IIm7', 'V7'])  # Common jazz extension
                else:
                    progression_template.append(progression_template[0])  # Repeat first chord
                progression_template = progression_template[:length]
        
        # Build actual chord progression
        progression = []
        for pos, roman_numeral in enumerate(progression_template):
            chord_name = chord_map.get(roman_numeral, f"{key}maj" if 'major' in scale.lower() else f"{key}min")
            progression.append({
                'name': chord_name,
                'position': pos,
                'duration': 1.0,
                'velocity': 100,
                'scale_context': scale,  # Add scale context for better processing
                'style_context': style_key  # Add style context
            })
        
        return progression
    
    def _apply_complexity_enhancements(self, progression, complexity):
        """Apply complexity-based enhancements to the progression."""
        import random
        
        enhanced_progression = []
        for chord in progression:
            enhanced_chord = chord.copy()
            chord_name = chord['name']
            
            # Higher complexity = more sophisticated chord types
            if complexity > 0.7 and random.random() < complexity:
                # Add extensions and alterations
                extensions = ['9', '11', '13', 'add9', 'sus4']
                if '7' not in chord_name and 'maj' not in chord_name:
                    extension = random.choice(extensions)
                    enhanced_chord['name'] = f"{chord_name}{extension}"
            elif complexity > 0.5 and random.random() < complexity:
                # Add basic extensions
                if 'min' in chord_name.lower():
                    enhanced_chord['name'] = f"{chord_name}7"
                elif 'maj' in chord_name.lower() or chord_name.endswith('maj'):
                    enhanced_chord['name'] = f"{chord_name}7"
            
            enhanced_progression.append(enhanced_chord)
        
        return enhanced_progression

    def _transpose_note(self, note, semitones):
        """Transpose a note by semitones."""
        notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        try:
            current_index = notes.index(note.upper())
            new_index = (current_index + semitones) % 12
            return notes[new_index]
        except ValueError:
            return note
    
    def _transpose_progression(self, progression, from_key, to_key):
        """Transpose entire progression from one key to another."""
        if from_key == to_key:
            return progression
        
        # Calculate semitone difference
        notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        try:
            from_index = notes.index(from_key.upper())
            to_index = notes.index(to_key.upper())
            semitone_diff = (to_index - from_index) % 12
            
            transposed_progression = []
            for chord in progression:
                transposed_chord = chord.copy()
                
                # Extract root note from chord name
                chord_name = chord['name']
                if len(chord_name) >= 2 and chord_name[1] in ['#', 'b']:
                    root = chord_name[:2]
                    suffix = chord_name[2:]
                else:
                    root = chord_name[0]
                    suffix = chord_name[1:]
                
                # Transpose root note
                try:
                    root_index = notes.index(root.upper())
                    new_root_index = (root_index + semitone_diff) % 12
                    new_root = notes[new_root_index]
                    transposed_chord['name'] = f"{new_root}{suffix}"
                except ValueError:
                    # If root note parsing fails, keep original
                    pass
                
                transposed_progression.append(transposed_chord)
                
            return transposed_progression
            
        except (ValueError, IndexError):
            # If transposition fails, return original progression
            return progression

    def save_generated_progression(self):
        """Save the generated progression to a .progression file."""
        if not hasattr(self, 'current_generated') or not self.current_generated:
            messagebox.showwarning("No Progression", "Please generate a progression first")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".progression",
            filetypes=[("Progression Files", "*.progression"), ("All Files", "*.*")]
        )
        
        if filename:
            try:
                # Create the progression file structure
                progression_data = {
                    "progression": {
                        "name": os.path.splitext(os.path.basename(filename))[0],
                        "rootNote": self.key_var.get(),
                        "scale": f"{self.key_var.get()} {self.scale_var.get().title()}",
                        "recordingOctave": 4,
                        "chords": self.current_generated,
                        "metadata": {
                            "generated": True,
                            "style": self.style_var.get(),
                            "complexity": self.complexity_var.get(),
                            "engine": "XPM Advanced Music Theory Engine v2.0"
                        }
                    }
                }
                
                with open(filename, 'w') as f:
                    json.dump(progression_data, f, indent=2)
                
                # Add to library
                if self.music_engine:
                    chord_names = [chord['name'] for chord in self.current_generated]
                    self.music_engine.add_progression_to_library(
                        name=os.path.basename(filename),
                        chords=chord_names,
                        key=self.key_var.get(),
                        scale=self.scale_var.get(),
                        mood_tags=[self.style_var.get()],
                        complexity=self.complexity_var.get(),
                        source_file=filename
                    )
                
                messagebox.showinfo("Success", f"Progression saved to {filename}")
                self.refresh_library()
                
            except Exception as e:
                messagebox.showerror("Save Error", f"Error saving progression: {str(e)}")
    
    def refresh_library(self):
        """Refresh the library display."""
        if not self.music_engine:
            return
        
        try:
            # Update statistics
            stats = self.music_engine.get_chord_statistics()
            self.display_library_stats(stats)
            
            # Update library tree
            self.update_library_tree()
            
        except Exception as e:
            print(f"Error refreshing library: {e}")
    
    def display_library_stats(self, stats: Dict):
        """Display library statistics."""
        self.stats_text.delete(1.0, tk.END)
        
        output = "CHORD LIBRARY STATISTICS\\n"
        output += "=" * 30 + "\\n\\n"
        
        # Most used chord types
        output += "Most Used Chord Types:\\n"
        for chord_type, count, usage in stats.get('most_used_chord_types', []):
            output += f"  {chord_type}: {usage} uses ({count} unique chords)\\n"
        
        output += "\\n"
        
        # Favorite keys
        output += "Favorite Keys:\\n"
        for key, count in stats.get('favorite_keys', []):
            output += f"  {key}: {count} progressions\\n"
        
        output += "\\n"
        
        # Preferred styles
        output += "Preferred Styles:\\n"
        for style_json, count in stats.get('preferred_styles', []):
            try:
                styles = json.loads(style_json) if style_json else []
                style_str = ", ".join(styles) if styles else "Unknown"
                output += f"  {style_str}: {count} progressions\\n"
            except:
                pass
        
        self.stats_text.insert(tk.END, output)
    
    def update_library_tree(self):
        """Update the library treeview."""
        # Clear existing items
        for item in self.library_tree.get_children():
            self.library_tree.delete(item)
        
        if not self.music_engine:
            return
        
        try:
            # Add progressions
            self.music_engine.cursor.execute('''
                SELECT name, key_signature, scale, complexity_score, usage_count
                FROM progressions ORDER BY usage_count DESC
            ''')
            
            prog_parent = self.library_tree.insert("", "end", text="Progressions", open=True)
            
            for row in self.music_engine.cursor.fetchall():
                name, key, scale, complexity, usage = row
                self.library_tree.insert(prog_parent, "end",
                                       values=(name, "Progression", f"{key} {scale}", usage, f"{complexity:.2f}"))
            
            # Add individual chords
            self.music_engine.cursor.execute('''
                SELECT type, COUNT(*) as count, AVG(usage_count) as avg_usage
                FROM chords GROUP BY type ORDER BY avg_usage DESC LIMIT 20
            ''')
            
            chord_parent = self.library_tree.insert("", "end", text="Chords", open=False)
            
            for row in self.music_engine.cursor.fetchall():
                chord_type, count, avg_usage = row
                self.library_tree.insert(chord_parent, "end",
                                       values=(chord_type, "Chord Type", "-", f"{avg_usage:.1f}", f"{count} chords"))
        
        except Exception as e:
            print(f"Error updating library tree: {e}")
    
    def analyze_chord(self):
        """Analyze a single chord."""
        chord_name = self.chord_entry.get().strip()
        if not chord_name:
            return
        
        try:
            if self.music_engine:
                root, intervals, chord_type = self.music_engine.chord_name_to_intervals(chord_name)
                notes = self.music_engine.generate_chord_notes(root, intervals)
                
                analysis = f"CHORD ANALYSIS: {chord_name}\\n"
                analysis += "=" * 40 + "\\n\\n"
                analysis += f"Root Note: {self.music_engine.NOTE_NAMES[root]}\\n"
                analysis += f"Chord Type: {chord_type}\\n"
                analysis += f"Intervals: {intervals}\\n"
                analysis += f"MIDI Notes: {notes}\\n"
                analysis += f"Note Names: {[self.midi_to_note_name(note) for note in notes]}\\n\\n"
                
                # Music theory analysis
                analysis += "THEORY ANALYSIS:\\n"
                if chord_type in ['maj', 'min']:
                    analysis += f"- Basic {chord_type}or triad\\n"
                elif '7' in chord_type:
                    analysis += f"- Seventh chord - adds color and movement\\n"
                elif chord_type == 'dim':
                    analysis += f"- Diminished chord - creates tension\\n"
                elif chord_type == 'aug':
                    analysis += f"- Augmented chord - unstable, seeks resolution\\n"
                
                self.theory_text.delete(1.0, tk.END)
                self.theory_text.insert(tk.END, analysis)
            
        except Exception as e:
            messagebox.showerror("Analysis Error", f"Error analyzing chord: {str(e)}")
    
    def find_substitutions(self):
        """Find chord substitutions."""
        chord_name = self.chord_entry.get().strip()
        if not chord_name or not self.music_engine:
            return
        
        try:
            root, intervals, chord_type = self.music_engine.chord_name_to_intervals(chord_name)
            substitutions = self.music_engine._generate_substitutions(root, chord_type, "C")
            
            sub_text = f"\\n\\nSUBSTITUTIONS FOR {chord_name}:\\n"
            sub_text += "=" * 30 + "\\n"
            
            for i, (sub_name, sub_intervals) in enumerate(substitutions):
                sub_notes = self.music_engine.generate_chord_notes(root, sub_intervals)
                sub_text += f"{i+1}. {sub_name}: {[self.midi_to_note_name(note) for note in sub_notes]}\\n"
            
            if not substitutions:
                sub_text += "No common substitutions found for this chord type.\\n"
            
            self.theory_text.insert(tk.END, sub_text)
            
        except Exception as e:
            messagebox.showerror("Substitution Error", f"Error finding substitutions: {str(e)}")
    
    def show_chord_inversions(self):
        """Show all inversions for the entered chord."""
        chord_name = self.chord_entry.get().strip()
        if not chord_name or not self.music_engine:
            return
        
        try:
            root, intervals, chord_type = self.music_engine.chord_name_to_intervals(chord_name)
            inversions = self.music_engine.get_chord_inversions(root, chord_type)
            
            inv_text = f"\\n\\nINVERSIONS FOR {chord_name}:\\n"
            inv_text += "=" * 30 + "\\n"
            
            for inv_name, inv_notes in inversions.items():
                note_names = [self.midi_to_note_name(note) for note in inv_notes]
                inv_text += f"{inv_name}: {' - '.join(note_names)} | MIDI: {inv_notes}\\n"
            
            self.theory_text.insert(tk.END, inv_text)
            
        except Exception as e:
            messagebox.showerror("Inversion Error", f"Error showing inversions: {str(e)}")
    
    def show_chord_voicings(self):
        """Show all voicings for the entered chord."""
        chord_name = self.chord_entry.get().strip()
        if not chord_name or not self.music_engine:
            return
        
        try:
            root, intervals, chord_type = self.music_engine.chord_name_to_intervals(chord_name)
            voicings = self.music_engine.get_chord_voicings(root, chord_type)
            
            voicing_text = f"\\n\\nVOICINGS FOR {chord_name}:\\n"
            voicing_text += "=" * 30 + "\\n"
            
            for voicing_name, voicing_notes in voicings.items():
                note_names = [self.midi_to_note_name(note) for note in voicing_notes]
                voicing_text += f"{voicing_name}: {' - '.join(note_names)}\\n"
                voicing_text += f"  MIDI: {voicing_notes}\\n\\n"
            
            self.theory_text.insert(tk.END, voicing_text)
            
        except Exception as e:
            messagebox.showerror("Voicing Error", f"Error showing voicings: {str(e)}")
    
    def browse_historical_styles(self):
        """Browse and display historical progression styles."""
        if not self.music_engine:
            return
        
        try:
            styles = self.music_engine.get_all_historical_styles()
            
            hist_text = f"\\n\\nHISTORICAL PROGRESSION STYLES:\\n"
            hist_text += "=" * 50 + "\\n\\n"
            
            current_era = None
            for style in styles:
                if style['era'] != current_era:
                    current_era = style['era']
                    hist_text += f"\\n📅 {current_era.upper()} ERA:\\n"
                    hist_text += "-" * 30 + "\\n"
                
                hist_text += f"• {style['display_name']}\\n"
                hist_text += f"  Composer: {style['composer']}\\n"
                hist_text += f"  Complexity: {style['complexity']:.1f}/1.0\\n"
                hist_text += f"  Description: {style['description']}\\n\\n"
            
            self.theory_text.delete(1.0, tk.END)
            self.theory_text.insert(tk.END, hist_text)
            
        except Exception as e:
            messagebox.showerror("Historical Error", f"Error browsing historical styles: {str(e)}")
    
    def analyze_classical_harmony(self):
        """Analyze classical harmony principles."""
        classical_text = f"\\n\\nCLASSICAL HARMONY ANALYSIS:\\n"
        classical_text += "=" * 40 + "\\n\\n"
        
        classical_text += f"🎼 FUNCTIONAL HARMONY PRINCIPLES:\\n"
        classical_text += f"• Tonic (I): Stability, home, resolution\\n"
        classical_text += f"• Subdominant (IV): Departure from tonic\\n"
        classical_text += f"• Dominant (V): Tension, drives to tonic\\n"
        classical_text += f"• Leading tone (viiº): Strong pull to tonic\\n\\n"
        
        classical_text += f"🎵 VOICE LEADING RULES:\\n"
        classical_text += f"• Avoid parallel fifths and octaves\\n"
        classical_text += f"• Resolve leading tones upward\\n"
        classical_text += f"• Move inner voices smoothly\\n"
        classical_text += f"• Double root in root position chords\\n\\n"
        
        classical_text += f"🎹 CADENCE TYPES:\\n"
        classical_text += f"• Authentic: V-I (strongest resolution)\\n"
        classical_text += f"• Plagal: IV-I (Amen cadence)\\n"
        classical_text += f"• Deceptive: V-vi (unexpected resolution)\\n"
        classical_text += f"• Half: ends on V (creates suspense)\\n\\n"
        
        classical_text += f"🎭 CHROMATIC HARMONY:\\n"
        classical_text += f"• Secondary dominants: V/V, V/vi, etc.\\n"
        classical_text += f"• Neapolitan sixth: bII6 (exotic color)\\n"
        classical_text += f"• Augmented sixth chords: dramatic tension\\n"
        classical_text += f"• Diminished seventh: modulatory pivot\\n"
        
        self.theory_text.delete(1.0, tk.END)
        self.theory_text.insert(tk.END, classical_text)
    
    def import_progressions_to_library(self):
        """Import existing progression files and MIDI files into the library (supports batch folders)."""
        # Check MIDI availability early
        if not MIDI_IMPORT_AVAILABLE:
            response = messagebox.askyesno(
                "MIDI Import Unavailable",
                "MIDI import functionality requires additional packages:\n\n" +
                "• mido\n• pretty_midi (optional)\n• music21 (optional)\n\n" +
                "Install with: pip install mido pretty_midi music21\n\n" +
                "Continue with progression files only?"
            )
            if not response:
                return
        
        # Ask user for import type
        import_type = messagebox.askyesnocancel(
            "Import Type",
            "Choose import method:\n\n" +
            "• Yes = Select individual files\n" +
            "• No = Select folder (batch process)\n" +
            "• Cancel = Abort"
        )
        
        if import_type is None:  # User cancelled
            return
            
        all_files = []
        
        if import_type:  # Yes = individual files
            files = safe_askopenfilenames(
                title="Select Progression or MIDI Files to Import",
                filetypes=[
                    ("All Supported", "*.progression;*.mid;*.midi"),
                    ("Progression Files", "*.progression"), 
                    ("MIDI Files", "*.mid;*.midi"),
                    ("All Files", "*.*")
                ]
            )
            all_files = list(files) if files else []
        else:  # No = folder selection
            folder = safe_askdirectory(
                title="Select Folder to Batch Import (includes subdirectories)"
            )
            if folder:
                # Recursively find all supported files
                all_files = self._find_supported_files(folder)
                if not all_files:
                    messagebox.showinfo("No Files Found", 
                                      f"No progression or MIDI files found in:\n{folder}")
                    return
                else:
                    # Show what we found
                    file_count = len(all_files)
                    midi_count = len([f for f in all_files if f.lower().endswith(('.mid', '.midi'))])
                    prog_count = len([f for f in all_files if f.lower().endswith('.progression')])
                    
                    confirm = messagebox.askyesno(
                        "Batch Import Confirmation",
                        f"Found {file_count} files to import:\n\n" +
                        f"• {midi_count} MIDI files\n" +
                        f"• {prog_count} progression files\n\n" +
                        "Proceed with batch import?"
                    )
                    if not confirm:
                        return
        
        if all_files and self.music_engine:
            imported = 0
            total_files = len(all_files)
            
            # Show progress for batch imports
            if total_files > 5:
                progress_window = self._create_progress_window("Importing Files", total_files)
                self.root.update()
            
            for i, file_path in enumerate(all_files):
                try:
                    file_ext = os.path.splitext(file_path)[1].lower()
                    
                    if file_ext in ['.mid', '.midi']:
                        # Handle MIDI file import
                        imported += self._import_midi_file(file_path)
                    elif file_ext == '.progression':
                        # Handle progression file import (existing logic)
                        imported += self._import_progression_file(file_path)
                    else:
                        print(f"Unsupported file type: {file_ext} for {file_path}")
                        
                    # Update progress for batch imports
                    if total_files > 5 and 'progress_window' in locals():
                        progress = int((i + 1) / total_files * 100)
                        progress_window.update_progress(progress, f"Processing: {os.path.basename(file_path)}")
                        self.root.update()
                        
                except Exception as e:
                    print(f"Failed to import {file_path}: {e}")
            
            # Close progress window
            if total_files > 5 and 'progress_window' in locals():
                progress_window.destroy()
            
            # Show results
            if imported > 0:
                messagebox.showinfo("Import Complete", 
                                  f"Successfully imported {imported} files to library\n" +
                                  f"(from {total_files} files processed)")
                self.refresh_library()
            else:
                messagebox.showwarning("Import Results", 
                                     f"No files were imported from {total_files} files processed.\n" +
                                     "Check that files contain valid chord progressions.")

    def _find_supported_files(self, folder_path: str) -> List[str]:
        """Recursively find all supported files in folder and subdirectories."""
        supported_files = []
        supported_extensions = {'.progression', '.mid', '.midi'}
        
        try:
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    file_ext = os.path.splitext(file)[1].lower()
                    if file_ext in supported_extensions:
                        full_path = os.path.join(root, file)
                        supported_files.append(full_path)
        except Exception as e:
            print(f"Error scanning folder {folder_path}: {e}")
            
        return sorted(supported_files)
    
    def _create_progress_window(self, title: str, total_items: int):
        """Create a simple progress window for batch operations."""
        progress_window = tk.Toplevel(self.root)
        progress_window.title(title)
        progress_window.geometry("400x120")
        progress_window.transient(self.root)
        progress_window.grab_set()
        
        # Center the window
        progress_window.update_idletasks()
        x = (progress_window.winfo_screenwidth() // 2) - (400 // 2)
        y = (progress_window.winfo_screenheight() // 2) - (120 // 2)
        progress_window.geometry(f"400x120+{x}+{y}")
        
        # Progress widgets
        ttk.Label(progress_window, text=f"Processing {total_items} files...").pack(pady=10)
        
        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(progress_window, 
                                     variable=progress_var, 
                                     maximum=100, 
                                     length=350)
        progress_bar.pack(pady=5)
        
        status_label = ttk.Label(progress_window, text="Starting...")
        status_label.pack(pady=5)
        
        # Add update method to window
        def update_progress(percentage, status_text):
            progress_var.set(percentage)
            status_label.config(text=status_text)
            
        progress_window.update_progress = update_progress
        return progress_window

    def _import_midi_file(self, file_path):
        """Import a single MIDI file into the library."""
        try:
            # Import MIDI analyzer (try both import paths)
            try:
                from midi_chord_analyzer import MIDIChordAnalyzer
            except ImportError:
                from scripts.midi_chord_analyzer import MIDIChordAnalyzer
            
            # Analyze MIDI file
            analyzer = MIDIChordAnalyzer()
            analysis = analyzer.analyze_midi_file(file_path)
            
            if analysis and analysis.chord_symbols:
                # Create a progression name from filename
                file_name = os.path.splitext(os.path.basename(file_path))[0]
                progression_name = f"MIDI: {file_name}"
                
                # Add progression to library
                self.music_engine.add_progression_to_library(
                    name=progression_name,
                    chords=analysis.chord_symbols,
                    key=analysis.key_signature or "C",
                    scale="major",  # Default to major for now
                    mood_tags=[f"complexity_{analysis.complexity_score:.1f}"],
                    complexity=analysis.complexity_score,
                    source_file=file_path
                )
                
                # Also add individual chords to library
                chord_objects = []
                for i, chord_symbol in enumerate(analysis.chord_symbols):
                    chord_obj = {
                        'name': chord_symbol,
                        'position': i,
                        'confidence': 1.0  # MIDI analysis confidence
                    }
                    chord_objects.append(chord_obj)
                
                self.music_engine.add_chords_to_library(chord_objects, file_path)
                print(f"✅ Successfully imported MIDI: {os.path.basename(file_path)} ({len(analysis.chord_symbols)} chords)")
                return 1
            else:
                print(f"⚠️ No chords detected in MIDI file: {os.path.basename(file_path)}")
                return 0
                
        except ImportError as ie:
            print(f"❌ MIDI analysis unavailable: {ie}")
            return 0
        except Exception as e:
            print(f"❌ Error analyzing MIDI file {os.path.basename(file_path)}: {e}")
            return 0

    def _import_progression_file(self, file_path):
        """Import a single progression file into the library (existing logic)."""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            if 'progression' in data:
                prog_data = data['progression']
                chords = prog_data.get('chords', [])
                
                # Extract chord names
                chord_names = [chord.get('name', 'C') for chord in chords]
                
                # Analyze for key and scale
                analysis = self.music_engine.analyze_progression(file_path)
                
                # Add to library
                self.music_engine.add_progression_to_library(
                    name=os.path.basename(file_path),
                    chords=chord_names,
                    key=analysis.key,
                    scale=analysis.scale,
                    mood_tags=analysis.mood_tags,
                    complexity=analysis.complexity_score,
                    source_file=file_path
                )
                
                # Also add individual chords
                self.music_engine.add_chords_to_library(chords, file_path)
                return 1
            else:
                print(f"Invalid progression file format: {file_path}")
                return 0
                
        except Exception as e:
            print(f"Error processing progression file {file_path}: {e}")
            return 0
    
    def export_library(self):
        """Export the library to a JSON file."""
        if not self.music_engine:
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        
        if filename:
            try:
                # Export progressions
                self.music_engine.cursor.execute('SELECT * FROM progressions')
                progressions = self.music_engine.cursor.fetchall()
                
                self.music_engine.cursor.execute('SELECT * FROM chords')
                chords = self.music_engine.cursor.fetchall()
                
                export_data = {
                    "export_info": {
                        "exported_at": str(datetime.datetime.now()),
                        "total_progressions": len(progressions),
                        "total_chords": len(chords)
                    },
                    "progressions": [dict(zip([col[0] for col in self.music_engine.cursor.description], row)) 
                                   for row in progressions],
                    "chords": [dict(zip([col[0] for col in self.music_engine.cursor.description], row)) 
                             for row in chords]
                }
                
                with open(filename, 'w') as f:
                    json.dump(export_data, f, indent=2)
                
                messagebox.showinfo("Export Complete", f"Library exported to {filename}")
                
            except Exception as e:
                messagebox.showerror("Export Error", f"Error exporting library: {str(e)}")
    
    def load_user_library(self):
        """Load the user's progression library."""
        if self.music_engine:
            self.refresh_library()
    
    def clear_analysis(self):
        """Clear the analysis display."""
        self.analysis_text.delete(1.0, tk.END)
    
    def update_status(self, message: str):
        """Update the status bar."""
        self.status_var.set(message)
        self.root.update_idletasks()
    
    def midi_to_note_name(self, midi_note: int) -> str:
        """Convert MIDI note number to note name."""
        note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        octave = (midi_note // 12) - 1
        note = note_names[midi_note % 12]
        return f"{note}{octave}"
    
    def on_closing(self):
        """Handle window closing."""
        if self.music_engine:
            self.music_engine.close()
        
        if self.is_toplevel:
            self.root.destroy()
        else:
            self.root.quit()
    
    def run(self):
        """Run the GUI (for standalone mode)."""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

# Standalone execution
if __name__ == "__main__":
    app = ProgressionRebuilderGUI()
    app.run()
