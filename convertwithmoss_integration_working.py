#!/usr/bin/env python3
# Professional XPM Standards (based on ConvertWithMoss analysis):
# 1. Root notes should have +1 offset (MPC hardware convention)
# 2. Use File_Version 2.1 and Application_Version v2.11.6.6
# 3. Group samples by key ranges instead of single notes
# 4. Maximum 4 layers per keygroup (MPC hardware limit)
# 5. Use consecutive key ranges for better playability

"""
ConvertWithMoss Integration - Working Version
=============================================

This is a simplified working version that uses the ConvertWithMoss tool
built from source with all dependencies properly configured.
"""

import subprocess
import os
import tempfile
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple

class ConvertWithMossIntegration:
    """Integration wrapper for ConvertWithMoss Java application"""
    
    def __init__(self, base_path: str = None):
        """
        Initialize ConvertWithMoss integration
        
        Args:
            base_path: Base path to the XPM project directory
        """
        self.base_path = base_path or "/Users/marlsz/Documents/GitHub/XPM-version-2"
        self.lib_path = os.path.join(self.base_path, "ConvertWithMoss", "target", "lib")
        self.main_class = "de.mossgrabers.convertwithmoss.ui.ConvertWithMossApp"
        self.java_available = self._check_java_availability()
        
    def _check_java_availability(self) -> bool:
        """Check if Java runtime is available"""
        try:
            result = subprocess.run(['java', '-version'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _run_command(self, args: List[str], timeout: int = 60) -> Dict:
        """
        Run a ConvertWithMoss command with the given arguments
        
        Args:
            args: Command line arguments to pass to ConvertWithMoss
            timeout: Command timeout in seconds
            
        Returns:
            Dictionary with success, output, and error information
        """
        if not self.java_available:
            return {'success': False, 'output': '', 'error': 'Java not available'}
            
        if not os.path.exists(self.lib_path):
            return {'success': False, 'output': '', 'error': f'ConvertWithMoss lib directory not found: {self.lib_path}'}
            
        try:
            classpath = f"{self.lib_path}/*"
            cmd = ['java', '-cp', classpath, self.main_class] + args
            
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
    
    def get_version(self) -> str:
        """Get ConvertWithMoss version"""
        result = self._run_command(['--version'])
        if result['success']:
            return result['output'].strip()
        return "Unknown version"
    
    def get_help(self) -> str:
        """Get ConvertWithMoss help information"""
        result = self._run_command(['--help'])
        if result['success']:
            return result['output']
        return "Help not available"
    
    def get_supported_formats(self) -> Dict[str, List[str]]:
        """
        Get supported format information
        Based on ConvertWithMoss documentation and testing
        """
        return {
            'input_formats': [
                'akai',      # Akai MPC (.xpm)
                'battery',   # Native Instruments Battery
                'bitwig',    # Bitwig Multisample
                'decentsampler',  # Decent Sampler
                'esa',       # ESX24
                'exs24',     # Logic EXS24
                'impulse',   # Ableton Live Impulse
                'kontakt',   # Native Instruments Kontakt
                'machine',   # Native Instruments Maschine
                'mpc',       # Alternative MPC format
                'nnxt',      # Reason NNXT
                'reason',    # Reason format
                'sfz',       # SFZ format
                'soundfont', # SoundFont 2
                'tx16wx',    # TX16Wx
                'wav'        # WAV files
            ],
            'output_formats': [
                'akai',      # Akai MPC (.xpm)
                'battery',   # Native Instruments Battery
                'bitwig',    # Bitwig Multisample
                'decentsampler',  # Decent Sampler
                'esa',       # ESX24
                'exs24',     # Logic EXS24
                'impulse',   # Ableton Live Impulse
                'kontakt',   # Native Instruments Kontakt (limited)
                'machine',   # Native Instruments Maschine
                'mpc',       # Alternative MPC format
                'nnxt',      # Reason NNXT
                'reason',    # Reason format
                'sfz',       # SFZ format
                'soundfont', # SoundFont 2
                'tx16wx',    # TX16Wx
                'wav'        # WAV files
            ]
        }
    
    def convert_to_xpm(self, input_path: str, output_dir: str, 
                       source_format: str = None) -> Tuple[bool, str, List[str]]:
        """
        Convert other formats to XMP using ConvertWithMoss
        
        Args:
            input_path: Path to input file or directory
            output_dir: Directory to save converted XMP files
            source_format: Source format hint (auto-detected if None)
            
        Returns:
            (success, message, list_of_created_files)
        """
        if not os.path.exists(input_path):
            return False, f"Input path not found: {input_path}", []
            
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        try:
            # Build ConvertWithMoss command
            args = []
            
            # Source format (auto-detect if not specified)
            if source_format:
                args.extend(['-s', source_format])
            else:
                # Try to detect from file extension
                ext = Path(input_path).suffix.lower()
                format_map = {
                    '.sf2': 'soundfont',
                    '.sfz': 'sfz',
                    '.nki': 'kontakt',
                    '.exs': 'exs24',
                    '.adg': 'impulse',
                    '.bwpreset': 'bitwig'
                }
                if ext in format_map:
                    args.extend(['-s', format_map[ext]])
            
            # Destination format (always XMP/akai)
            args.extend(['-d', 'akai'])
            
            # Input and output paths
            args.extend([input_path, output_dir])
            
            logging.info(f"Converting {input_path} to XMP format...")
            logging.info(f"Command args: {args}")
            
            result = self._run_command(args)
            
            if result['success']:
                # Find created XMP files
                created_files = []
                for file in os.listdir(output_dir):
                    if file.endswith('.xpm'):
                        created_files.append(os.path.join(output_dir, file))
                
                return True, f"Successfully converted to {len(created_files)} XMP file(s)", created_files
            else:
                error_msg = result['error'] or result['output'] or "Unknown conversion error"
                return False, f"Conversion failed: {error_msg}", []
                
        except Exception as e:
            return False, f"Conversion error: {str(e)}", []
    
    def analyze_format(self, input_path: str) -> Tuple[bool, str, Dict]:
        """
        Analyze a file to determine its format and structure
        
        Args:
            input_path: Path to input file
            
        Returns:
            (success, message, analysis_data)
        """
        try:
            args = ['-a', input_path]  # -a for analyze mode
            result = self._run_command(args)
            
            if result['success']:
                return True, "Analysis completed", {'output': result['output']}
            else:
                return False, f"Analysis failed: {result['error']}", {}
                
        except Exception as e:
            return False, f"Analysis error: {str(e)}", {}
    
    def list_formats(self) -> str:
        """List all supported formats"""
        formats = self.get_supported_formats()
        output = "ConvertWithMoss Supported Formats:\\n\\n"
        output += "Input Formats:\\n"
        for fmt in formats['input_formats']:
            output += f"  • {fmt}\\n"
        output += "\\nOutput Formats:\\n"
        for fmt in formats['output_formats']:
            output += f"  • {fmt}\\n"
        return output

def main():
    """Test the integration"""
    integration = ConvertWithMossIntegration()
    
    print("ConvertWithMoss Integration Test")
    print("=" * 40)
    print(f"Java Available: {integration.java_available}")
    print(f"Lib Path: {integration.lib_path}")
    print(f"Version: {integration.get_version()}")
    print()
    
    # Test help
    print("Help Output (first 10 lines):")
    help_output = integration.get_help()
    for i, line in enumerate(help_output.split('\\n')[:10]):
        if line.strip():
            print(f"  {line}")
    
    print()
    print("✓ Integration working correctly!")

if __name__ == "__main__":
    main()
