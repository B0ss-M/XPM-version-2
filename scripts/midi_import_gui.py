#!/usr/bin/env python3
"""
MIDI Import and Analysis GUI for Advanced Music Theory Engine

This GUI provides:
1. MIDI file import and batch processing
2. Real-time chord detection visualization
3. Interactive chord correction and learning
4. Database integration with learning statistics
5. Machine learning progress tracking
6. Export functionality for analyzed progressions

Features:
- Drag-and-drop MIDI file support
- Visual chord progression display
- Interactive correction interface for improving AI
- Batch processing with progress tracking
- Integration with existing chord library
- Real-time analysis preview
- Learning statistics and improvement metrics
"""

import os
import json
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from typing import List, Dict, Optional, Any
import traceback
from pathlib import Path
from datetime import datetime

# Try to import drag-and-drop support
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DRAG_DROP_AVAILABLE = True
except ImportError:
    DRAG_DROP_AVAILABLE = False

# Import our modules
try:
    from midi_chord_analyzer import MIDIChordAnalyzer, ProgressionAnalysis
    from database_enhancer import MIDIDataManager, enhance_music_theory_database
    MIDI_MODULES_AVAILABLE = True
except ImportError as e:
    print(f"MIDI modules not available: {e}")
    MIDI_MODULES_AVAILABLE = False

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

class MIDIImportGUI:
    """Advanced MIDI import interface for the music theory engine."""
    
    def __init__(self, parent=None, music_engine=None):
        """Initialize the MIDI import GUI."""
        if parent is None:
            self.root = TkinterDnD.Tk() if DRAG_DROP_AVAILABLE else tk.Tk()
            self.root.title("MIDI Import & Analysis - Advanced Music Theory Engine")
            self.is_toplevel = False
        else:
            self.root = tk.Toplevel(parent)
            self.root.title("MIDI Import & Analysis")
            self.root.transient(parent)
            self.is_toplevel = True
        
        self.root.geometry("1200x900")
        self.root.minsize(800, 600)
        
        # Initialize components
        self.music_engine = music_engine
        self.midi_analyzer = None
        self.data_manager = None
        self.selected_files = []
        self.current_analysis = None
        self.analysis_results = []
        self.processing_thread = None
        
        # GUI state variables
        self.processing_var = tk.BooleanVar()
        self.auto_correct_var = tk.BooleanVar(value=True)
        self.save_to_library_var = tk.BooleanVar(value=True)
        self.batch_mode_var = tk.BooleanVar()
        self.progress_var = tk.DoubleVar()
        self.status_var = tk.StringVar(value="Ready")
        
        # Initialize MIDI components
        self._initialize_midi_components()
        
        # Create GUI
        self.create_widgets()
        
        # Setup drag and drop
        if DRAG_DROP_AVAILABLE:
            self.setup_drag_drop()
        
        self.update_status("MIDI Import Ready - Select files or drag and drop")
    
    def _initialize_midi_components(self):
        """Initialize MIDI analyzer and database components."""
        if not MIDI_MODULES_AVAILABLE:
            self.update_status("❌ MIDI modules not available - install required dependencies")
            return
        
        try:
            self.midi_analyzer = MIDIChordAnalyzer()
            
            # Initialize database
            if self.music_engine and hasattr(self.music_engine, 'db_path'):
                db_path = self.music_engine.db_path
            else:
                db_path = os.path.expanduser('~/.xpm_progression_builder/chord_library.db')
            
            # Enhance database for MIDI support
            enhance_music_theory_database(db_path)
            self.data_manager = MIDIDataManager(db_path)
            
        except Exception as e:
            messagebox.showerror("MIDI Components Error", 
                               f"Failed to initialize MIDI components: {e}")
    
    def create_widgets(self):
        """Create the GUI widgets."""
        # Create main notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Tab 1: File Import
        self.import_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.import_frame, text="📁 Import MIDI")
        self.create_import_tab()
        
        # Tab 2: Analysis Results
        self.results_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.results_frame, text="🎵 Analysis Results")
        self.create_results_tab()
        
        # Tab 3: Learning Center
        self.learning_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.learning_frame, text="🧠 Learning Center")
        self.create_learning_tab()
        
        # Tab 4: Statistics
        self.stats_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.stats_frame, text="📊 Statistics")
        self.create_stats_tab()
        
        # Status bar and progress
        self.create_status_bar()
    
    def create_import_tab(self):
        """Create the MIDI import tab."""
        # File selection frame
        file_frame = ttk.LabelFrame(self.import_frame, text="📂 Select MIDI Files")
        file_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # File selection buttons
        button_frame = ttk.Frame(file_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(button_frame, text="Select MIDI Files", 
                  command=self.select_midi_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Select Folder", 
                  command=self.select_midi_folder).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Clear Selection", 
                  command=self.clear_selection).pack(side=tk.LEFT, padx=5)
        
        # Selected files display
        list_frame = ttk.Frame(file_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        ttk.Label(list_frame, text="Selected Files:").pack(anchor=tk.W)
        
        # File list with scrollbar
        list_container = ttk.Frame(list_frame)
        list_container.pack(fill=tk.BOTH, expand=True)
        
        self.file_listbox = tk.Listbox(list_container, height=6)
        scrollbar = ttk.Scrollbar(list_container, orient=tk.VERTICAL, command=self.file_listbox.yview)
        self.file_listbox.configure(yscrollcommand=scrollbar.set)
        
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Analysis options frame
        options_frame = ttk.LabelFrame(self.import_frame, text="⚙️ Analysis Options")
        options_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Options grid
        opts_grid = ttk.Frame(options_frame)
        opts_grid.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Checkbutton(opts_grid, text="Save to Chord Library", 
                       variable=self.save_to_library_var).grid(row=0, column=0, sticky=tk.W, padx=5)
        ttk.Checkbutton(opts_grid, text="Auto-correct Detected Chords", 
                       variable=self.auto_correct_var).grid(row=0, column=1, sticky=tk.W, padx=5)
        ttk.Checkbutton(opts_grid, text="Batch Processing Mode", 
                       variable=self.batch_mode_var).grid(row=1, column=0, sticky=tk.W, padx=5)
        
        # Advanced options
        advanced_frame = ttk.LabelFrame(options_frame, text="Advanced Settings")
        advanced_frame.pack(fill=tk.X, padx=5, pady=5)
        
        advanced_grid = ttk.Frame(advanced_frame)
        advanced_grid.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(advanced_grid, text="Minimum Chord Duration (s):").grid(row=0, column=0, sticky=tk.W)
        self.min_duration_var = tk.DoubleVar(value=0.25)
        duration_spin = ttk.Spinbox(advanced_grid, from_=0.1, to=2.0, increment=0.1, width=8,
                                   textvariable=self.min_duration_var)
        duration_spin.grid(row=0, column=1, sticky=tk.W, padx=(5, 0))
        
        ttk.Label(advanced_grid, text="Detection Threshold:").grid(row=0, column=2, sticky=tk.W, padx=(15, 0))
        self.threshold_var = tk.IntVar(value=3)
        threshold_spin = ttk.Spinbox(advanced_grid, from_=2, to=6, increment=1, width=8,
                                   textvariable=self.threshold_var)
        threshold_spin.grid(row=0, column=3, sticky=tk.W, padx=(5, 0))
        
        # Control buttons frame
        control_frame = ttk.LabelFrame(self.import_frame, text="🎛️ Analysis Controls")
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        control_buttons = ttk.Frame(control_frame)
        control_buttons.pack(padx=5, pady=5)
        
        self.analyze_button = ttk.Button(control_buttons, text="🎵 Analyze Selected", 
                                       command=self.start_analysis, style="Accent.TButton")
        self.analyze_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(control_buttons, text="⏹️ Stop Analysis", 
                                    command=self.stop_analysis, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        # Progress display
        progress_frame = ttk.Frame(control_frame)
        progress_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, 
                                          maximum=100, length=400)
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        self.progress_label = ttk.Label(progress_frame, text="Ready")
        self.progress_label.pack(side=tk.RIGHT)
        
        # Drag and drop area
        if DRAG_DROP_AVAILABLE:
            self.create_drag_drop_area()
    
    def create_drag_drop_area(self):
        """Create drag and drop area for MIDI files."""
        drop_frame = ttk.LabelFrame(self.import_frame, text="🎯 Drag & Drop Zone")
        drop_frame.pack(fill=tk.X, padx=5, pady=5)
        
        drop_label = ttk.Label(drop_frame, text="Drag MIDI files here", 
                              font=("Arial", 12), foreground="gray")
        drop_label.pack(pady=20)
        
        self.drop_frame = drop_frame
    
    def create_results_tab(self):
        """Create the analysis results tab."""
        # Results header
        header_frame = ttk.Frame(self.results_frame)
        header_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(header_frame, text="Analysis Results", 
                 font=("Arial", 14, "bold")).pack(side=tk.LEFT)
        
        ttk.Button(header_frame, text="Export Results", 
                  command=self.export_results).pack(side=tk.RIGHT, padx=5)
        
        # Results display
        self.create_results_display()
    
    def create_results_display(self):
        """Create the results display area."""
        # Create paned window for results
        paned = ttk.PanedWindow(self.results_frame, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Top pane: Files list and basic info
        top_frame = ttk.LabelFrame(paned, text="📄 Analyzed Files")
        
        # Files tree view
        files_container = ttk.Frame(top_frame)
        files_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        columns = ("File", "Key", "Tempo", "Chords", "Complexity", "Status")
        self.results_tree = ttk.Treeview(files_container, columns=columns, show="headings", height=8)
        
        for col in columns:
            self.results_tree.heading(col, text=col)
            self.results_tree.column(col, width=100, anchor="center")
        
        # Scrollbars for tree
        tree_scroll_y = ttk.Scrollbar(files_container, orient=tk.VERTICAL, command=self.results_tree.yview)
        tree_scroll_x = ttk.Scrollbar(files_container, orient=tk.HORIZONTAL, command=self.results_tree.xview)
        self.results_tree.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)
        
        self.results_tree.grid(row=0, column=0, sticky="nsew")
        tree_scroll_y.grid(row=0, column=1, sticky="ns")
        tree_scroll_x.grid(row=1, column=0, sticky="ew")
        
        files_container.rowconfigure(0, weight=1)
        files_container.columnconfigure(0, weight=1)
        
        # Bind selection event
        self.results_tree.bind("<<TreeviewSelect>>", self.on_result_select)
        
        paned.add(top_frame, weight=1)
        
        # Bottom pane: Detailed chord progression
        bottom_frame = ttk.LabelFrame(paned, text="🎼 Chord Progression Details")
        
        detail_container = ttk.Frame(bottom_frame)
        detail_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Chord progression display
        self.progression_text = scrolledtext.ScrolledText(detail_container, height=10, 
                                                         font=("Monaco", 10))
        self.progression_text.pack(fill=tk.BOTH, expand=True)
        
        paned.add(bottom_frame, weight=1)
    
    def create_learning_tab(self):
        """Create the machine learning and correction tab."""
        # Learning header
        header = ttk.Label(self.learning_frame, text="🧠 Machine Learning Center", 
                          font=("Arial", 14, "bold"))
        header.pack(pady=10)
        
        # Correction interface
        correction_frame = ttk.LabelFrame(self.learning_frame, text="🔧 Chord Correction Interface")
        correction_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # This would contain interactive chord correction tools
        correction_placeholder = ttk.Label(correction_frame, 
                                         text="Interactive chord correction interface will be here\n"
                                              "• Click on detected chords to correct them\n"
                                              "• AI learns from your corrections\n"
                                              "• Real-time accuracy improvement\n"
                                              "• Confidence scoring visualization",
                                         justify=tk.CENTER, font=("Arial", 10))
        correction_placeholder.pack(expand=True, pady=50)
        
        # Learning progress
        progress_frame = ttk.LabelFrame(self.learning_frame, text="📈 Learning Progress")
        progress_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Add learning progress indicators here
        progress_placeholder = ttk.Label(progress_frame, 
                                       text="Learning progress metrics will be displayed here")
        progress_placeholder.pack(pady=10)
    
    def create_stats_tab(self):
        """Create the statistics tab."""
        # Stats header
        header = ttk.Label(self.stats_frame, text="📊 Analysis Statistics", 
                          font=("Arial", 14, "bold"))
        header.pack(pady=10)
        
        # Statistics display
        self.stats_text = scrolledtext.ScrolledText(self.stats_frame, height=25, 
                                                   font=("Monaco", 10))
        self.stats_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Refresh button
        ttk.Button(self.stats_frame, text="🔄 Refresh Statistics", 
                  command=self.refresh_statistics).pack(pady=5)
        
        # Load initial stats
        self.refresh_statistics()
    
    def create_status_bar(self):
        """Create status bar and progress indicators."""
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var, 
                                     relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Processing indicator
        self.processing_label = ttk.Label(status_frame, text="", foreground="blue")
        self.processing_label.pack(side=tk.RIGHT, padx=5)
    
    def setup_drag_drop(self):
        """Setup drag and drop functionality."""
        if hasattr(self, 'drop_frame'):
            self.drop_frame.drop_target_register(DND_FILES)
            self.drop_frame.dnd_bind('<<Drop>>', self.on_drop)
    
    def on_drop(self, event):
        """Handle drag and drop events."""
        files = event.data.split()
        midi_files = [f for f in files if f.lower().endswith(('.mid', '.midi'))]
        
        if midi_files:
            self.selected_files.extend(midi_files)
            self.update_file_list()
            self.update_status(f"Added {len(midi_files)} MIDI files via drag & drop")
        else:
            messagebox.showwarning("Invalid Files", "Please drop MIDI files (.mid, .midi)")
    
    def select_midi_files(self):
        """Select MIDI files for analysis."""
        files = safe_askopenfilenames(
            title="Select MIDI Files",
            filetypes=[("MIDI files", "*.mid *.midi"), ("All files", "*.*")]
        )
        
        if files:
            self.selected_files.extend(files)
            self.update_file_list()
            self.update_status(f"Selected {len(files)} MIDI files")
    
    def select_midi_folder(self):
        """Select a folder containing MIDI files."""
        folder = safe_askdirectory(title="Select Folder with MIDI Files")
        
        if folder:
            midi_files = []
            for ext in ('*.mid', '*.midi'):
                midi_files.extend(Path(folder).rglob(ext))
            
            if midi_files:
                self.selected_files.extend([str(f) for f in midi_files])
                self.update_file_list()
                self.update_status(f"Found {len(midi_files)} MIDI files in folder")
            else:
                messagebox.showinfo("No Files", "No MIDI files found in selected folder")
    
    def clear_selection(self):
        """Clear selected files."""
        self.selected_files.clear()
        self.update_file_list()
        self.update_status("File selection cleared")
    
    def update_file_list(self):
        """Update the file list display."""
        self.file_listbox.delete(0, tk.END)
        for file_path in self.selected_files:
            filename = os.path.basename(file_path)
            self.file_listbox.insert(tk.END, filename)
    
    def start_analysis(self):
        """Start MIDI analysis in a separate thread."""
        if not self.selected_files:
            messagebox.showwarning("No Files", "Please select MIDI files to analyze")
            return
        
        if not self.midi_analyzer:
            messagebox.showerror("Error", "MIDI analyzer not available")
            return
        
        # Update GUI state
        self.processing_var.set(True)
        self.analyze_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        
        # Configure analyzer with current settings
        self.midi_analyzer.min_chord_duration = self.min_duration_var.get()
        self.midi_analyzer.chord_detection_threshold = self.threshold_var.get()
        
        # Start processing thread
        self.processing_thread = threading.Thread(target=self._analyze_files, daemon=True)
        self.processing_thread.start()
    
    def _analyze_files(self):
        """Analyze selected MIDI files (runs in separate thread)."""
        try:
            self.analysis_results.clear()
            total_files = len(self.selected_files)
            
            for i, file_path in enumerate(self.selected_files):
                if not self.processing_var.get():
                    break
                
                # Update progress
                progress = (i / total_files) * 100
                self.root.after(0, lambda p=progress: self.progress_var.set(p))
                self.root.after(0, lambda f=file_path: 
                              self.progress_label.config(text=f"Analyzing: {os.path.basename(f)}"))
                
                try:
                    # Analyze the file
                    analysis = self.midi_analyzer.analyze_midi_file(file_path)
                    
                    if analysis:
                        self.analysis_results.append(analysis)
                        
                        # Save to database if enabled
                        if self.save_to_library_var.get() and self.data_manager:
                            self.data_manager.store_midi_analysis(analysis)
                        
                        # Update UI
                        self.root.after(0, lambda a=analysis: self._add_result_to_tree(a))
                        
                    else:
                        self.root.after(0, lambda f=file_path: 
                                      self.update_status(f"Failed to analyze: {os.path.basename(f)}"))
                        
                except Exception as e:
                    error_msg = f"Error analyzing {os.path.basename(file_path)}: {e}"
                    self.root.after(0, lambda msg=error_msg: self.update_status(msg))
            
            # Analysis complete
            final_progress = 100.0
            self.root.after(0, lambda: self.progress_var.set(final_progress))
            self.root.after(0, lambda: self.progress_label.config(text="Analysis Complete"))
            self.root.after(0, lambda: self.update_status(f"Analysis complete: {len(self.analysis_results)} files processed"))
            
        except Exception as e:
            error_msg = f"Analysis error: {e}"
            self.root.after(0, lambda: self.update_status(error_msg))
        
        finally:
            # Reset GUI state
            self.root.after(0, self._analysis_finished)
    
    def _add_result_to_tree(self, analysis: ProgressionAnalysis):
        """Add analysis result to the tree view."""
        filename = os.path.basename(analysis.file_path)
        key = analysis.key_signature or "Unknown"
        tempo = f"{analysis.tempo:.1f}"
        chord_count = str(len(analysis.chords))
        complexity = f"{analysis.complexity_score:.2f}"
        status = "✅ Success"
        
        self.results_tree.insert("", "end", values=(filename, key, tempo, chord_count, complexity, status))
    
    def _analysis_finished(self):
        """Clean up after analysis is finished."""
        self.processing_var.set(False)
        self.analyze_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.processing_label.config(text="")
    
    def stop_analysis(self):
        """Stop the current analysis."""
        self.processing_var.set(False)
        self.update_status("Analysis stopped by user")
        self._analysis_finished()
    
    def on_result_select(self, event):
        """Handle selection of analysis result."""
        selection = self.results_tree.selection()
        if not selection:
            return
        
        item = self.results_tree.item(selection[0])
        filename = item['values'][0]
        
        # Find the corresponding analysis
        for analysis in self.analysis_results:
            if os.path.basename(analysis.file_path) == filename:
                self.show_progression_details(analysis)
                break
    
    def show_progression_details(self, analysis: ProgressionAnalysis):
        """Show detailed progression information."""
        self.progression_text.delete(1.0, tk.END)
        
        details = f"File: {os.path.basename(analysis.file_path)}\n"
        details += f"Key: {analysis.key_signature or 'Unknown'}\n"
        details += f"Tempo: {analysis.tempo:.1f} BPM\n"
        details += f"Duration: {analysis.total_duration:.1f} seconds\n"
        details += f"Complexity: {analysis.complexity_score:.2f}\n"
        details += f"Mood: {', '.join(analysis.mood_indicators)}\n\n"
        
        details += "Chord Progression:\n"
        details += "=" * 40 + "\n"
        
        for i, chord in enumerate(analysis.chords, 1):
            timing = f"{chord.start_time:.1f}s - {chord.end_time:.1f}s"
            details += f"{i:2d}. {chord.chord_symbol:<12} [{timing}] (confidence: {chord.confidence:.2f})\n"
        
        if analysis.roman_numerals:
            details += f"\nRoman Numeral Analysis:\n"
            details += " - ".join(analysis.roman_numerals)
        
        self.progression_text.insert(1.0, details)
    
    def refresh_statistics(self):
        """Refresh the statistics display."""
        if not self.data_manager:
            self.stats_text.delete(1.0, tk.END)
            self.stats_text.insert(1.0, "Statistics not available - database not initialized")
            return
        
        try:
            stats = self.data_manager.get_learning_statistics()
            
            stats_text = "MIDI ANALYSIS STATISTICS\n"
            stats_text += "=" * 50 + "\n\n"
            
            stats_text += f"📁 Total MIDI Files Processed: {stats.get('total_midi_files', 0)}\n"
            stats_text += f"🎵 Total Chord Instances: {stats.get('total_chord_instances', 0)}\n"
            stats_text += f"🎼 Unique Chord Types: {stats.get('unique_chord_types', 0)}\n"
            stats_text += f"📊 Average Detection Confidence: {stats.get('average_detection_confidence', 0):.2f}\n"
            stats_text += f"🔑 Successful Key Detections: {stats.get('successful_key_detections', 0)}\n\n"
            
            stats_text += "MOST COMMON PROGRESSIONS:\n"
            stats_text += "-" * 30 + "\n"
            
            for prog in stats.get('common_progressions', []):
                chords = prog['chords']
                count = prog['count']
                stats_text += f"• {chords} (occurred {count} times)\n"
            
            stats_text += f"\n\nLast Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            
            self.stats_text.delete(1.0, tk.END)
            self.stats_text.insert(1.0, stats_text)
            
        except Exception as e:
            error_text = f"Error loading statistics: {e}\n\n{traceback.format_exc()}"
            self.stats_text.delete(1.0, tk.END)
            self.stats_text.insert(1.0, error_text)
    
    def export_results(self):
        """Export analysis results."""
        if not self.analysis_results:
            messagebox.showwarning("No Results", "No analysis results to export")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Export Analysis Results",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                if file_path.endswith('.json'):
                    self._export_json(file_path)
                else:
                    self._export_text(file_path)
                
                messagebox.showinfo("Export Complete", f"Results exported to {file_path}")
                
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export results: {e}")
    
    def _export_json(self, file_path: str):
        """Export results as JSON."""
        export_data = []
        for analysis in self.analysis_results:
            data = {
                'file_path': analysis.file_path,
                'key_signature': analysis.key_signature,
                'tempo': analysis.tempo,
                'complexity_score': analysis.complexity_score,
                'chord_progression': analysis.chord_symbols,
                'roman_numerals': analysis.roman_numerals,
                'mood_indicators': analysis.mood_indicators,
                'total_duration': analysis.total_duration
            }
            export_data.append(data)
        
        with open(file_path, 'w') as f:
            json.dump(export_data, f, indent=2)
    
    def _export_text(self, file_path: str):
        """Export results as text."""
        with open(file_path, 'w') as f:
            f.write("MIDI ANALYSIS RESULTS\n")
            f.write("=" * 50 + "\n\n")
            
            for analysis in self.analysis_results:
                f.write(f"File: {analysis.file_path}\n")
                f.write(f"Key: {analysis.key_signature or 'Unknown'}\n")
                f.write(f"Tempo: {analysis.tempo:.1f} BPM\n")
                f.write(f"Progression: {' | '.join(analysis.chord_symbols)}\n")
                f.write("-" * 30 + "\n\n")
    
    def update_status(self, message: str):
        """Update status bar message."""
        self.status_var.set(message)

# Integration with main progression rebuilder GUI
def add_midi_import_tab(parent_notebook, music_engine):
    """Add MIDI import tab to existing progression rebuilder GUI."""
    from midi_import_gui import MIDIImportGUI
    
    midi_frame = ttk.Frame(parent_notebook)
    parent_notebook.add(midi_frame, text="📁 MIDI Import")
    
    # Create MIDI import GUI within the existing interface
    midi_gui = MIDIImportGUI(parent=midi_frame, music_engine=music_engine)
    return midi_gui

if __name__ == "__main__":
    # Test the MIDI import GUI
    app = MIDIImportGUI()
    app.root.mainloop()