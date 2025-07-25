#!/usr/bin/env python3
"""
XPM Professional Improvements
Based on ConvertWithMoss analysis - implements professional XPM creation standards
"""

import os
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from convertwithmoss_integration_working import ConvertWithMossIntegration

class ProfessionalXPMCreator:
    """Professional XPM creation using ConvertWithMoss insights"""
    
    def __init__(self):
        self.converter = ConvertWithMossIntegration()
        
        # Professional constants from ConvertWithMoss
        self.PROFESSIONAL_FILE_VERSION = "2.1"
        self.PROFESSIONAL_APP_VERSION = "v2.11.6.6"
        self.MAX_LAYERS_PER_KEYGROUP = 4
        self.ROOT_NOTE_OFFSET = 1  # ConvertWithMoss adds +1 to root notes
        
    def analyze_professional_structure(self, sample_path):
        """
        Convert samples with ConvertWithMoss and analyze the professional structure
        """
        print(f"🔍 Analyzing professional structure for: {sample_path}")
        
        # Create temporary output directory
        temp_dir = "/tmp/professional_analysis"
        os.makedirs(temp_dir, exist_ok=True)
        
        try:
            # Convert with ConvertWithMoss
            success, message, files = self.converter.convert_to_xpm(sample_path, temp_dir)
            
            if success and files:
                professional_xpm = files[0]
                print(f"✅ Professional conversion successful: {professional_xpm}")
                
                # Analyze the structure
                analysis = self._analyze_xpm_structure(professional_xpm)
                return analysis
            else:
                print(f"❌ Professional conversion failed: {message}")
                return None
                
        except Exception as e:
            print(f"Error in professional analysis: {e}")
            return None
    
    def _analyze_xpm_structure(self, xpm_path):
        """Extract key structural information from professional XPM"""
        try:
            tree = ET.parse(xpm_path)
            root = tree.getroot()
            
            analysis = {
                'file_version': None,
                'app_version': None,
                'num_keygroups': 0,
                'instruments': [],
                'professional_patterns': []
            }
            
            # Extract version info
            version_elem = root.find('.//Version')
            if version_elem is not None:
                file_ver = version_elem.find('File_Version')
                app_ver = version_elem.find('Application_Version')
                if file_ver is not None:
                    analysis['file_version'] = file_ver.text
                if app_ver is not None:
                    analysis['app_version'] = app_ver.text
            
            # Extract keygroup count
            keygroup_count = root.find('.//KeygroupNumKeygroups')
            if keygroup_count is not None:
                analysis['num_keygroups'] = int(keygroup_count.text)
            
            # Analyze instruments
            for instrument in root.findall('.//Instrument'):
                inst_analysis = self._analyze_instrument(instrument)
                analysis['instruments'].append(inst_analysis)
            
            # Identify professional patterns
            analysis['professional_patterns'] = self._identify_professional_patterns(analysis)
            
            return analysis
            
        except Exception as e:
            print(f"Error analyzing XPM structure: {e}")
            return None
    
    def _analyze_instrument(self, instrument_elem):
        """Analyze individual instrument structure"""
        inst_data = {
            'number': instrument_elem.get('number'),
            'low_note': None,
            'high_note': None,
            'layers': [],
            'root_note_pattern': None
        }
        
        # Extract note range
        low_note = instrument_elem.find('LowNote')
        high_note = instrument_elem.find('HighNote')
        if low_note is not None:
            inst_data['low_note'] = int(low_note.text)
        if high_note is not None:
            inst_data['high_note'] = int(high_note.text)
        
        # Analyze layers
        for layer in instrument_elem.findall('.//Layer'):
            layer_data = self._analyze_layer(layer)
            inst_data['layers'].append(layer_data)
        
        # Detect root note pattern
        if inst_data['layers']:
            root_notes = [layer.get('root_note') for layer in inst_data['layers'] if layer.get('root_note')]
            if root_notes and inst_data['low_note']:
                # Check for +1 offset pattern
                typical_offset = int(root_notes[0]) - inst_data['low_note']
                inst_data['root_note_pattern'] = f"offset_{typical_offset}"
        
        return inst_data
    
    def _analyze_layer(self, layer_elem):
        """Analyze layer structure"""
        layer_data = {
            'number': layer_elem.get('number'),
            'root_note': None,
            'vel_start': None,
            'vel_end': None,
            'sample_name': None,
            'volume': None,
            'pan': None
        }
        
        # Extract key parameters
        for param in ['RootNote', 'VelStart', 'VelEnd', 'SampleName', 'Volume', 'Pan']:
            elem = layer_elem.find(param)
            if elem is not None:
                key = param.lower().replace('vel', 'vel_').replace('sample', 'sample_').replace('root', 'root_')
                if param in ['RootNote', 'VelStart', 'VelEnd']:
                    layer_data[key] = int(elem.text)
                else:
                    layer_data[key] = elem.text
        
        return layer_data
    
    def _identify_professional_patterns(self, analysis):
        """Identify professional patterns in the XPM structure"""
        patterns = []
        
        # Check for consistent +1 root note offset
        root_offsets = []
        for inst in analysis['instruments']:
            if inst['layers'] and inst['low_note']:
                for layer in inst['layers']:
                    if layer['root_note']:
                        offset = layer['root_note'] - inst['low_note']
                        root_offsets.append(offset)
        
        if root_offsets and all(offset == 1 for offset in root_offsets):
            patterns.append("consistent_plus_one_root_offset")
        
        # Check for intelligent key range grouping
        note_ranges = [(inst['low_note'], inst['high_note']) for inst in analysis['instruments'] 
                      if inst['low_note'] and inst['high_note']]
        
        if note_ranges:
            # Check if ranges are consecutive or intelligently grouped
            sorted_ranges = sorted(note_ranges)
            consecutive = all(sorted_ranges[i][1] + 1 == sorted_ranges[i+1][0] 
                            for i in range(len(sorted_ranges)-1))
            if consecutive:
                patterns.append("consecutive_key_ranges")
        
        # Check for proper velocity layering
        multilayer_instruments = [inst for inst in analysis['instruments'] if len(inst['layers']) > 1]
        if multilayer_instruments:
            patterns.append("velocity_layering")
        
        return patterns
    
    def compare_with_professional(self, your_xpm_path, sample_source):
        """
        Compare your XPM with professional ConvertWithMoss output
        """
        print(f"🔍 Comparing {your_xpm_path} with professional standard")
        
        # Get professional analysis
        professional_analysis = self.analyze_professional_structure(sample_source)
        if not professional_analysis:
            print("❌ Could not get professional reference")
            return None
        
        # Analyze your XPM
        your_analysis = self._analyze_xpm_structure(your_xpm_path)
        if not your_analysis:
            print("❌ Could not analyze your XPM")
            return None
        
        # Compare structures
        comparison = {
            'version_differences': {},
            'structural_differences': {},
            'missing_professional_patterns': [],
            'recommendations': []
        }
        
        # Version comparison
        if your_analysis['file_version'] != professional_analysis['file_version']:
            comparison['version_differences']['file_version'] = {
                'yours': your_analysis['file_version'],
                'professional': professional_analysis['file_version']
            }
        
        if your_analysis['app_version'] != professional_analysis['app_version']:
            comparison['version_differences']['app_version'] = {
                'yours': your_analysis['app_version'],
                'professional': professional_analysis['app_version']
            }
        
        # Structural comparison
        if your_analysis['num_keygroups'] != professional_analysis['num_keygroups']:
            comparison['structural_differences']['keygroup_count'] = {
                'yours': your_analysis['num_keygroups'],
                'professional': professional_analysis['num_keygroups']
            }
        
        # Pattern comparison
        your_patterns = set(your_analysis.get('professional_patterns', []))
        prof_patterns = set(professional_analysis.get('professional_patterns', []))
        missing_patterns = prof_patterns - your_patterns
        comparison['missing_professional_patterns'] = list(missing_patterns)
        
        # Generate recommendations
        if 'consistent_plus_one_root_offset' in missing_patterns:
            comparison['recommendations'].append(
                "Apply +1 offset to root notes (ConvertWithMoss standard)"
            )
        
        if 'consecutive_key_ranges' in missing_patterns:
            comparison['recommendations'].append(
                "Use consecutive key ranges instead of single-note mappings"
            )
        
        if comparison['version_differences']:
            comparison['recommendations'].append(
                f"Update version to professional standard: {professional_analysis['file_version']}, {professional_analysis['app_version']}"
            )
        
        return comparison
    
    def generate_improvement_report(self, xpm_directory):
        """
        Generate a comprehensive improvement report for all XPM files
        """
        print(f"📊 Generating improvement report for: {xpm_directory}")
        
        xpm_files = list(Path(xpm_directory).glob("*.xpm"))
        if not xpm_files:
            print("❌ No XPM files found")
            return
        
        report = {
            'total_files': len(xpm_files),
            'analyzed_files': 0,
            'common_issues': {},
            'recommendations': [],
            'files_with_issues': []
        }
        
        issue_counts = {}
        
        for xpm_file in xpm_files:
            try:
                print(f"  Analyzing: {xpm_file.name}")
                analysis = self._analyze_xpm_structure(str(xpm_file))
                
                if analysis:
                    report['analyzed_files'] += 1
                    
                    # Check for common issues
                    issues = []
                    
                    # Version issues
                    if analysis['file_version'] != self.PROFESSIONAL_FILE_VERSION:
                        issues.append('outdated_file_version')
                    
                    if analysis['app_version'] != self.PROFESSIONAL_APP_VERSION:
                        issues.append('outdated_app_version')
                    
                    # Pattern issues
                    prof_patterns = analysis.get('professional_patterns', [])
                    if 'consistent_plus_one_root_offset' not in prof_patterns:
                        issues.append('missing_root_offset')
                    
                    if 'consecutive_key_ranges' not in prof_patterns:
                        issues.append('poor_key_range_grouping')
                    
                    # Count issues
                    for issue in issues:
                        issue_counts[issue] = issue_counts.get(issue, 0) + 1
                    
                    if issues:
                        report['files_with_issues'].append({
                            'file': str(xpm_file),
                            'issues': issues
                        })
                
            except Exception as e:
                print(f"  Error analyzing {xpm_file.name}: {e}")
        
        # Generate common issues summary
        total_analyzed = report['analyzed_files']
        for issue, count in issue_counts.items():
            percentage = (count / total_analyzed) * 100 if total_analyzed > 0 else 0
            report['common_issues'][issue] = {
                'count': count,
                'percentage': round(percentage, 1)
            }
        
        # Generate recommendations
        if issue_counts.get('missing_root_offset', 0) > 0:
            report['recommendations'].append(
                f"Fix root note offset in {issue_counts['missing_root_offset']} files (apply +1 offset)"
            )
        
        if issue_counts.get('outdated_file_version', 0) > 0:
            report['recommendations'].append(
                f"Update file version to {self.PROFESSIONAL_FILE_VERSION} in {issue_counts['outdated_file_version']} files"
            )
        
        if issue_counts.get('poor_key_range_grouping', 0) > 0:
            report['recommendations'].append(
                f"Improve key range grouping in {issue_counts['poor_key_range_grouping']} files"
            )
        
        # Save report
        report_path = os.path.join(xpm_directory, 'professional_improvement_report.json')
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"📄 Report saved to: {report_path}")
        
        # Print summary
        print(f"\n📊 IMPROVEMENT REPORT SUMMARY")
        print(f"Files analyzed: {report['analyzed_files']}/{report['total_files']}")
        print(f"Files with issues: {len(report['files_with_issues'])}")
        
        print(f"\n🔍 COMMON ISSUES:")
        for issue, data in report['common_issues'].items():
            print(f"  {issue}: {data['count']} files ({data['percentage']}%)")
        
        print(f"\n💡 RECOMMENDATIONS:")
        for i, rec in enumerate(report['recommendations'], 1):
            print(f"  {i}. {rec}")
        
        return report

def main():
    """Main function for testing and demonstration"""
    creator = ProfessionalXPMCreator()
    
    print("🚀 Professional XPM Creator - ConvertWithMoss Integration")
    print("=" * 60)
    
    # Test directory (adjust path as needed)
    test_directory = "/Users/marlsz/Documents/GitHub/XPM-version-2"
    
    # Generate improvement report
    report = creator.generate_improvement_report(test_directory)
    
    # Test professional analysis if samples are available
    sample_files = list(Path(test_directory).glob("*.wav"))
    if sample_files:
        print(f"\n🎵 Testing professional analysis with: {sample_files[0]}")
        analysis = creator.analyze_professional_structure(str(sample_files[0]))
        if analysis:
            print("✅ Professional analysis completed")
            print(f"Professional patterns found: {analysis.get('professional_patterns', [])}")

if __name__ == "__main__":
    main()
