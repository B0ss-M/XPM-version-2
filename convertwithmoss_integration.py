#!/usr/bin/env python3
"""ConvertWithMoss Integration for XPM Tool

This module provides a small wrapper around the ConvertWithMoss Java
application (convertwithmoss-*.jar). It focuses on robust JAR detection,
Java availability checks, and safe subprocess execution with logging.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from typing import Dict, List, Tuple, Optional


class ConvertWithMossIntegration:
    """Integration wrapper for ConvertWithMoss Java application."""

    def __init__(self, jar_path: Optional[str] = None):
        # Respect an explicit argument first, then env var, then repository discovery.
        if jar_path:
            self.jar_path = os.path.abspath(jar_path)
        else:
            try:
                self.jar_path = self._find_jar_path()
            except FileNotFoundError:
                logging.warning('ConvertWithMoss JAR not found during initialization; some features will be disabled until a JAR is provided or placed in the repo.')
                self.jar_path = None

        self.java_available = self._check_java_availability()
        self.supported_formats = self._get_supported_formats()

    def _find_jar_path(self) -> str:
        """Discover a ConvertWithMoss JAR to use.

        Preference order:
        1) Environment variable CONVERTWITHMOSS_JAR (if it points to an existing file)
        2) Known repository locations (repo root, ConvertWithMoss/target/lib)
        3) Shallow walk under the package directory to find any convertwithmoss-*.jar

        Raises FileNotFoundError if none found.
        """
        # 1) Environment override
        env = os.getenv('CONVERTWITHMOSS_JAR')
        if env:
            if os.path.exists(env):
                logging.info('Using ConvertWithMoss JAR from CONVERTWITHMOSS_JAR: %s', env)
                return os.path.abspath(env)
            raise FileNotFoundError(f"CONVERTWITHMOSS_JAR is set but file does not exist: {env}")

        # Helper: normalize a candidate path and check existence
        def _ok(p):
            try:
                if p and os.path.exists(p):
                    return os.path.abspath(p)
            except Exception:
                return None
            return None

        base = os.path.abspath(os.path.dirname(__file__))

        # 2) Try common repository placements, prefer top-level jars first
        common_candidates = [
            os.path.join(base, '..', 'convertwithmoss-14.0.0.jar'),
            os.path.join(base, 'convertwithmoss-14.0.0.jar'),
            os.path.join(base, '..', 'ConvertWithMoss', 'target', 'lib', 'convertwithmoss-14.0.0.jar'),
            os.path.join(base, 'ConvertWithMoss', 'target', 'lib', 'convertwithmoss-14.0.0.jar'),
        ]

        for cand in common_candidates:
            found = _ok(cand)
            if found:
                logging.info('Found ConvertWithMoss JAR at: %s', found)
                return found

        # 3) Do a shallow repository search under base (limit depth to avoid long scans)
        max_depth = 3
        base_depth = base.count(os.sep)
        for root, dirs, files in os.walk(base):
            # limit depth
            if root.count(os.sep) - base_depth > max_depth:
                # prune deeper dirs
                dirs[:] = []
                continue
            for f in files:
                if f.lower().startswith('convertwithmoss') and f.lower().endswith('.jar'):
                    candidate = os.path.join(root, f)
                    logging.info('Discovered ConvertWithMoss JAR at: %s', candidate)
                    return os.path.abspath(candidate)

        # As a last-ditch, try a repository-wide glob from the parent directory
        try:
            import glob

            parent = os.path.abspath(os.path.join(base, '..'))
            pattern = os.path.join(parent, '**', 'convertwithmoss-*.jar')
            matches = glob.glob(pattern, recursive=True)
            if matches:
                logging.info('Found ConvertWithMoss JAR via glob: %s', matches[0])
                return os.path.abspath(matches[0])
        except Exception:
            pass

        raise FileNotFoundError('convertwithmoss JAR not found. Set CONVERTWITHMOSS_JAR or place the JAR in the repository.')

    def _check_java_availability(self) -> bool:
        """Check if Java runtime is available."""
        try:
            import shutil

            java = shutil.which('java')
            if not java:
                return False

            result = subprocess.run([java, '-version'], capture_output=True, text=True, timeout=8)
            return result.returncode == 0
        except Exception:
            return False

    def _get_supported_formats(self) -> Dict[str, Dict]:
        """Return a lightweight list of supported input/output formats."""
        return {
            'input_formats': {
                'akai_mpc': {'extensions': ['.xpm'], 'description': 'Akai MPC Keygroup'},
                'sf2': {'extensions': ['.sf2'], 'description': 'SoundFont 2'},
                'sfz': {'extensions': ['.sfz'], 'description': 'SFZ Format'},
                'nki': {'extensions': ['.nki'], 'description': 'Kontakt'},
                'exs24': {'extensions': ['.exs'], 'description': 'EXS24'},
            },
            'output_formats': {
                'akai_mpc': 'MPC Keygroup (XPM)',
                'sf2': 'SoundFont 2',
                'sfz': 'SFZ',
                'wav': 'WAV files',
            }
        }

    def _run_command(self, args: List[str], timeout: int = 30) -> Dict:
        """Run the ConvertWithMoss JAR with the provided args.

        Returns a dict with keys: success (bool), output (stdout), error (stderr), returncode (int).
        """
        if not self.java_available:
            return {'success': False, 'output': '', 'error': 'Java runtime is not available', 'returncode': 127}

        if not self.jar_path or not os.path.exists(self.jar_path):
            return {
                'success': False,
                'output': '',
                'error': 'ConvertWithMoss JAR not found. Provide CONVERTWITHMOSS_JAR or place the JAR in the repository.',
                'returncode': 127,
            }

        cmd = ['java', '-jar', self.jar_path] + args
        logging.debug('Running ConvertWithMoss command: %s', ' '.join(cmd))

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            if result.stdout:
                logging.debug('ConvertWithMoss stdout: %s', result.stdout)
            if result.stderr:
                logging.debug('ConvertWithMoss stderr: %s', result.stderr)

            return {
                'success': result.returncode == 0,
                'output': result.stdout,
                'error': result.stderr,
                'returncode': result.returncode,
            }
        except subprocess.TimeoutExpired:
            logging.error('ConvertWithMoss command timed out after %s seconds', timeout)
            return {'success': False, 'output': '', 'error': 'timeout', 'returncode': -1}
        except Exception as e:
            logging.exception('Error running ConvertWithMoss JAR: %s', e)
            return {'success': False, 'output': '', 'error': str(e), 'returncode': -2}

    def convert_to_xpm(self, input_file: str, output_dir: str, format_hint: Optional[str] = None) -> Tuple[bool, str, List[str]]:
        """Convert an input file to XPM using the JAR.

        Returns (success, message, created_files).
        """
        if not os.path.exists(input_file):
            return False, f'Input file not found: {input_file}', []

        os.makedirs(output_dir, exist_ok=True)

        cmd = [
            '--input', input_file,
            '--output-format', 'akai_mpc',
            '--output-dir', output_dir,
            '--preserve-names',
        ]
        if format_hint:
            cmd.extend(['--input-format', format_hint])

        res = self._run_command(cmd, timeout=300)
        if res['success']:
            created = [os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.endswith('.xpm')]
            return True, f'Successfully converted to {len(created)} XPM file(s)', created
        return False, f"Conversion failed: {res['error']}", []

    def convert_from_xpm(self, xpm_file: str, output_format: str, output_dir: str) -> Tuple[bool, str, List[str]]:
        if output_format not in self.supported_formats['output_formats']:
            return False, f'Unsupported output format: {output_format}', []

        os.makedirs(output_dir, exist_ok=True)
        cmd = [
            '--input', xpm_file,
            '--output-format', output_format,
            '--output-dir', output_dir,
        ]
        res = self._run_command(cmd, timeout=300)
        if res['success']:
            created = [os.path.join(output_dir, f) for f in os.listdir(output_dir)
                       if any(f.endswith(ext) for ext in ['.sf2', '.sfz', '.adg', '.dspreset', '.wav'])]
            return True, f'Successfully converted to {output_format}', created
        return False, f"Conversion failed: {res['error']}", []

    def analyze_format_structure(self, input_file: str) -> Dict:
        if not os.path.exists(input_file):
            return {'error': 'input not found'}

        cmd = ['--analyze', input_file, '--output-format', 'json']
        res = self._run_command(cmd, timeout=60)
        if not res['success']:
            return {'error': res['error']}

        try:
            return json.loads(res['output']) if res['output'] else {'raw': res['error']}
        except Exception:
            return {'raw': res['output'] or res['error']}

    def batch_convert_to_xpm(self, input_dir: str, output_dir: str, input_formats: Optional[List[str]] = None) -> Dict:
        if input_formats is None:
            input_formats = list(self.supported_formats['input_formats'].keys())

        results = {'converted': [], 'failed': [], 'skipped': [], 'total_files': 0}

        for root, dirs, files in os.walk(input_dir):
            for file in files:
                path = os.path.join(root, file)
                ext = os.path.splitext(file)[1].lower()
                # Map extension to known formats
                format_found = None
                for fmt, info in self.supported_formats['input_formats'].items():
                    if ext in info['extensions']:
                        format_found = fmt
                        break

                if not format_found or format_found not in input_formats:
                    results['skipped'].append(path)
                    continue

                results['total_files'] += 1
                rel = os.path.relpath(os.path.dirname(path), input_dir)
                out_sub = os.path.join(output_dir, rel)
                success, msg, created = self.convert_to_xpm(path, out_sub, format_found)
                if success:
                    results['converted'].append({'input': path, 'files': created})
                else:
                    results['failed'].append({'input': path, 'error': msg})

                return results
    
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
        try:
            # Use safe wrapper to normalize filetypes on macOS
            from tk_file_utils import askopenfilename as safe_askopenfilename, askdirectory as safe_askdirectory
            input_file = safe_askopenfilename(
                title=f"Select {source_format.upper()} file to convert",
                filetypes=[(f"{source_format.upper()} files", f"*.{source_format}"), ("All files", "*.*")]
            )
        except Exception:
            input_file = filedialog.askopenfilename(
                title=f"Select {source_format.upper()} file to convert",
                filetypes=[(f"{source_format.upper()} files", f"*.{source_format}"), ("All files", "*.*")]
            )
        
        if not input_file:
            return
            
        try:
            output_dir = safe_askdirectory(title="Select output directory for XPM files")
        except Exception:
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
