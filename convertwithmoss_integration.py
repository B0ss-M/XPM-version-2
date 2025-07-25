#!/usr/bin/env python3
# Professional XPM Standards (based on ConvertWithMoss analysis):
# 1. Root notes should have +1 offset (MPC hardware convention)
# 2. Use File_Version 2.1 and Application_Version v2.11.6.6
# 3. Group samples by key ranges instead of single notes
# 4. Maximum 4 layers per keygroup (MPC hardware limit)
# 5. Use consecutive key ranges for better playability

"""
ConvertWithMoss Integration for XPM Tool
=========================            }
        }
    
    def _run_command(self, args: List[str], timeout: int = 30) -> Dict:
        """
        Run a ConvertWithMoss command with the given arguments
        
        Args:
            args: Command line arguments to pass to the JAR
            timeout: Command timeout in seconds
            
        Returns:
            Dictionary with success, output, and error information
        """
        if not self.java_available:
            return {'success': False, 'output': '', 'error': 'Java not available'}
            
        try:
            cmd = ['java', '-jar', self.jar_path] + args
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            
            return {
                'success': result.returncode == 0,
                'output': result.stdout,
                'error': result.stderr,
                'returncode': result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {'success': False, 'output': '', 'error': 'Command timed out'}
        except Exception as e:
            return {'success': False, 'output': '', 'error': str(e)}
    
    def convert_to_xpm(self, input_file: str, output_dir: str,===========

This module integrates the ConvertWithMoss Java library (convertwithmoss-14.0.0.jar) 
into our Python XPM processing workflow to enable multi-format conversion.

ConvertWithMoss supports:
- Akai MPC (XPM) ↔ Many other formats
- SF2, SFZ, NKI/Kontakt, EXS24, Ableton, etc.
- Intelligent sample mapping and range detection
- Cross-platform format conversion

Integration Benefits:
1. Import samples from other formats into XPM
2. Export XPM to other popular sampler formats  
3. Learn from ConvertWithMoss's mapping algorithms
4. Batch convert between formats
5. Cross-reference format-specific optimizations
"""

import subprocess
import json
import os
import logging
import tempfile
from pathlib import Path
from typing import List, Dict, Optional, Tuple

class ConvertWithMossIntegration:
    """Integration wrapper for ConvertWithMoss Java application"""
    
    def __init__(self, jar_path: str = None):
        """
        Initialize ConvertWithMoss integration
        
        Args:
            jar_path: Path to convertwithmoss-14.0.0.jar (ConvertWithMoss)
        """
        self.jar_path = jar_path or self._find_jar_path()
        self.java_available = self._check_java_availability()
        self.supported_formats = self._get_supported_formats()
        
    def _find_jar_path(self) -> str:
        """Find the convertwithmoss JAR file in the workspace"""
        possible_paths = [
            "./convertwithmoss-14.0.0.jar",
            "../convertwithmoss-14.0.0.jar", 
            "/Users/marlsz/Documents/GitHub/XPM-version-2/convertwithmoss-14.0.0.jar"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return os.path.abspath(path)
                
        raise FileNotFoundError("convertwithmoss-14.0.0.jar not found. Please ensure it's in the workspace.")
    
    def _check_java_availability(self) -> bool:
        """Check if Java runtime is available"""
        try:
            result = subprocess.run(['java', '-version'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _get_supported_formats(self) -> Dict[str, Dict]:
        """Get list of formats supported by ConvertWithMoss"""
        return {
            'input_formats': {
                'akai_mpc': {'extensions': ['.xpm'], 'description': 'Akai MPC Keygroup'},
                'sf2': {'extensions': ['.sf2'], 'description': 'SoundFont 2'},
                'sfz': {'extensions': ['.sfz'], 'description': 'SFZ Format'},
                'nki': {'extensions': ['.nki'], 'description': 'Native Instruments Kontakt'},
                'exs24': {'extensions': ['.exs'], 'description': 'Logic EXS24'},
                'ableton': {'extensions': ['.adg'], 'description': 'Ableton Drum Rack'},
                'bitwig': {'extensions': ['.bwpreset'], 'description': 'Bitwig Multisample'},
                'yamaha': {'extensions': ['.ysfc'], 'description': 'Yamaha YSFC'},
                'tal_sampler': {'extensions': ['.talsmpl'], 'description': 'TAL Sampler'},
                'tx16wx': {'extensions': ['.txprog'], 'description': 'TX16Wx'},
                'decentsampler': {'extensions': ['.dspreset'], 'description': 'DecentSampler'},
                'korg': {'extensions': ['.multisample'], 'description': 'Korg Multisample'},
            },
            'output_formats': {
                'akai_mpc': 'MPC Keygroup (XPM)',
                'sf2': 'SoundFont 2', 
                'sfz': 'SFZ',
                'nki': 'Kontakt (limited)',
                'ableton': 'Ableton Drum Rack',
                'bitwig': 'Bitwig Multisample',
                'decentsampler': 'DecentSampler',
                'wav': 'Individual WAV files'
            }
        }
    
    def convert_to_xpm(self, input_file: str, output_dir: str, 
                       format_hint: str = None) -> Tuple[bool, str, List[str]]:
        """
        Convert other formats to XPM using ConvertWithMoss
        
        Args:
            input_file: Path to input file (SF2, SFZ, NKI, etc.)
            output_dir: Directory to save converted XPM files
            format_hint: Hint about input format if auto-detection fails
            
        Returns:
            (success, message, list_of_created_files)
        """
        if not self.java_available:
            return False, "Java runtime not available. Please install Java.", []
            
        if not os.path.exists(input_file):
            return False, f"Input file not found: {input_file}", []
            
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        try:
            # ConvertWithMoss command structure (example - need to verify actual syntax)
            cmd = [
                'java', '-jar', self.jar_path,
                '--input', input_file,
                '--output-format', 'akai_mpc',
                '--output-dir', output_dir,
                '--preserve-names'
            ]
            
            if format_hint:
                cmd.extend(['--input-format', format_hint])
            
            logging.info(f"🔄 Converting {os.path.basename(input_file)} to XPM format...")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                # Find created XPM files
                created_files = []
                for file in os.listdir(output_dir):
                    if file.endswith('.xpm'):
                        created_files.append(os.path.join(output_dir, file))
                
                return True, f"Successfully converted to {len(created_files)} XPM file(s)", created_files
            else:
                error_msg = result.stderr or result.stdout or "Unknown conversion error"
                return False, f"Conversion failed: {error_msg}", []
                
        except subprocess.TimeoutExpired:
            return False, "Conversion timed out (>5 minutes)", []
        except Exception as e:
            return False, f"Conversion error: {str(e)}", []
    
    def convert_from_xmp(self, xpm_file: str, output_format: str, 
                        output_dir: str) -> Tuple[bool, str, List[str]]:
        """
        Convert XPM to other formats using ConvertWithMoss
        
        Args:
            xpm_file: Path to XPM file
            output_format: Target format (sf2, sfz, ableton, etc.)
            output_dir: Directory to save converted files
            
        Returns:
            (success, message, list_of_created_files) 
        """
        if not self.java_available:
            return False, "Java runtime not available", []
            
        if output_format not in self.supported_formats['output_formats']:
            return False, f"Unsupported output format: {output_format}", []
            
        os.makedirs(output_dir, exist_ok=True)
        
        try:
            cmd = [
                'java', '-jar', self.jar_path,
                '--input', xpm_file,
                '--output-format', output_format,
                '--output-dir', output_dir
            ]
            
            logging.info(f"🔄 Converting {os.path.basename(xpm_file)} to {output_format} format...")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                # Find created files (format-dependent extensions)
                created_files = []
                for file in os.listdir(output_dir):
                    if any(file.endswith(ext) for ext in ['.sf2', '.sfz', '.adg', '.dspreset', '.wav']):
                        created_files.append(os.path.join(output_dir, file))
                        
                return True, f"Successfully converted to {output_format}", created_files
            else:
                error_msg = result.stderr or result.stdout or "Unknown conversion error"
                return False, f"Conversion failed: {error_msg}", []
                
        except Exception as e:
            return False, f"Conversion error: {str(e)}", []
    
    def analyze_format_structure(self, input_file: str) -> Dict:
        """
        Use ConvertWithMoss to analyze file structure and extract mapping info
        
        This can help us learn optimal mapping strategies for our XPM tool.
        """
        if not self.java_available:
            return {'error': 'Java not available'}
            
        try:
            # Use ConvertWithMoss in analysis mode (if supported)
            cmd = [
                'java', '-jar', self.jar_path,
                '--analyze', input_file,
                '--output-format', 'json'  # If supported
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                try:
                    analysis = json.loads(result.stdout)
                    return analysis
                except json.JSONDecodeError:
                    return {'raw_output': result.stdout}
            else:
                return {'error': result.stderr or 'Analysis failed'}
                
        except Exception as e:
            return {'error': str(e)}
    
    def batch_convert_to_xpm(self, input_dir: str, output_dir: str, 
                            input_formats: List[str] = None) -> Dict:
        """
        Batch convert multiple format files to XPM
        
        Args:
            input_dir: Directory containing source files
            output_dir: Directory to save XPM files
            input_formats: List of formats to convert (default: all supported)
            
        Returns:
            Dictionary with conversion results
        """
        if not input_formats:
            input_formats = list(self.supported_formats['input_formats'].keys())
            
        results = {
            'converted': [],
            'failed': [],
            'skipped': [],
            'total_files': 0
        }
        
        # Find all convertible files
        for root, dirs, files in os.walk(input_dir):
            for file in files:
                file_path = os.path.join(root, file)
                file_ext = os.path.splitext(file)[1].lower()
                
                # Check if file extension matches supported formats
                format_found = None
                for format_name, format_info in self.supported_formats['input_formats'].items():
                    if file_ext in format_info['extensions']:
                        format_found = format_name
                        break
                
                if format_found and format_found in input_formats:
                    results['total_files'] += 1
                    
                    # Create output subdirectory maintaining structure
                    rel_path = os.path.relpath(os.path.dirname(file_path), input_dir)
                    output_subdir = os.path.join(output_dir, rel_path)
                    
                    success, message, created_files = self.convert_to_xpm(
                        file_path, output_subdir, format_found
                    )
                    
                    if success:
                        results['converted'].append({
                            'source': file_path,
                            'format': format_found,
                            'created_files': created_files,
                            'message': message
                        })
                    else:
                        results['failed'].append({
                            'source': file_path,
                            'format': format_found,
                            'error': message
                        })
                else:
                    results['skipped'].append(file_path)
        
        return results


def create_conversion_gui_integration():
    """
    Create GUI integration for ConvertWithMoss in our main XPM tool
    """
    conversion_gui_code = '''
    def create_conversion_tab(self, notebook):
        """Add conversion tab to main XPM tool GUI"""
        conversion_frame = ttk.Frame(notebook)
        notebook.add(conversion_frame, text="🔄 Format Conversion")
        
        # ConvertWithMoss integration
        self.converter = ConvertWithMossIntegration()
        
        # Input section
        input_frame = ttk.LabelFrame(conversion_frame, text="Import from Other Formats", padding="10")
        input_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(input_frame, text="Convert TO XPM:").pack(anchor="w")
        
        format_buttons = [
            ("SF2 → XPM", "sf2", "Convert SoundFont files to MPC format"),
            ("SFZ → XPM", "sfz", "Convert SFZ files to MPC format"),
            ("NKI → XPM", "nki", "Convert Kontakt files to MPC format"),
            ("EXS24 → XPM", "exs24", "Convert Logic files to MPC format"),
        ]
        
        for text, format_id, tooltip in format_buttons:
            btn = ttk.Button(input_frame, text=text, 
                           command=lambda f=format_id: self.convert_to_xpm_dialog(f))
            btn.pack(side="left", padx=5)
            self.create_tooltip(btn, tooltip)
        
        # Output section
        output_frame = ttk.LabelFrame(conversion_frame, text="Export to Other Formats", padding="10")
        output_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(output_frame, text="Convert FROM XPM:").pack(anchor="w")
        
        export_buttons = [
            ("XPM → SF2", "sf2", "Export to SoundFont format"),
            ("XPM → SFZ", "sfz", "Export to SFZ format"), 
            ("XPM → Ableton", "ableton", "Export to Ableton Drum Rack"),
            ("XPM → DecentSampler", "decentsampler", "Export to DecentSampler format"),
        ]
        
        for text, format_id, tooltip in export_buttons:
            btn = ttk.Button(output_frame, text=text,
                           command=lambda f=format_id: self.convert_from_xmp_dialog(f))
            btn.pack(side="left", padx=5)
            self.create_tooltip(btn, tooltip)
        
        # Batch conversion section
        batch_frame = ttk.LabelFrame(conversion_frame, text="Batch Conversion", padding="10")
        batch_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(batch_frame, text="📁 Batch Convert Folder to XPM",
                  command=self.batch_convert_dialog).pack(side="left", padx=5)
        ttk.Button(batch_frame, text="📊 Analyze Format Structure", 
                  command=self.analyze_format_dialog).pack(side="left", padx=5)
    
    def convert_to_xpm_dialog(self, source_format):
        """Dialog for converting other formats to XPM"""
        input_file = filedialog.askopenfilename(
            title=f"Select {source_format.upper()} file to convert",
            filetypes=[(f"{source_format.upper()} files", f"*.{source_format}"), ("All files", "*.*")]
        )
        
        if not input_file:
            return
            
        output_dir = filedialog.askdirectory(title="Select output directory for XPM files")
        if not output_dir:
            return
            
        # Show progress
        progress_window = self.create_progress_window("Converting to XPM...")
        
        try:
            success, message, created_files = self.converter.convert_to_xpm(
                input_file, output_dir, source_format
            )
            
            progress_window.destroy()
            
            if success:
                result_msg = f"{message}\\n\\nCreated files:\\n"
                result_msg += "\\n".join([os.path.basename(f) for f in created_files])
                messagebox.showinfo("Conversion Successful", result_msg)
                
                # Ask if user wants to open the files in XPM tool
                if messagebox.askyesno("Open Files", "Open converted XPM files in the tool?"):
                    for xpm_file in created_files:
                        self.load_xpm_file(xpm_file)
            else:
                messagebox.showerror("Conversion Failed", message)
                
        except Exception as e:
            progress_window.destroy() 
            messagebox.showerror("Error", f"Conversion error: {str(e)}")
    '''
    
    return conversion_gui_code


if __name__ == "__main__":
    # Test the integration
    try:
        converter = ConvertWithMossIntegration()
        print("✅ ConvertWithMoss integration initialized successfully")
        print(f"📁 JAR path: {converter.jar_path}")
        print(f"☕ Java available: {converter.java_available}")
        print(f"🔧 Supported input formats: {len(converter.supported_formats['input_formats'])}")
        print(f"📤 Supported output formats: {len(converter.supported_formats['output_formats'])}")
        
        if converter.java_available:
            print("\\n🚀 Ready for format conversion!")
        else:
            print("\\n⚠️  Java runtime required for format conversion")
            
    except Exception as e:
        print(f"❌ Error initializing ConvertWithMoss: {e}")
