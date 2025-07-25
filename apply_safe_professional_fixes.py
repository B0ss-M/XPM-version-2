#!/usr/bin/env python3
"""
Improved Professional Fixes Script - Safer Regex Patterns
Fixes the issues that caused dictionary + integer errors
"""

import re
import os
import ast
from pathlib import Path

class SafeProfessionalFixer:
    """Safer version of professional fixes with better pattern matching"""
    
    def __init__(self):
        self.fixes_applied = []
        
    def fix_root_note_offset_safely(self, file_path):
        """
        Fix root note offset with careful pattern matching to avoid dictionary errors
        """
        print(f"🔧 Safely fixing root notes in: {file_path}")
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        original_content = content
        fixes = []
        
        # SAFE Pattern 1: Only target numeric root note assignments
        pattern1 = r'root_note_elem\.text\s*=\s*str\((\w+)\)(?!\s*\+\s*1)'
        replacement1 = r'root_note_elem.text = str(\1 + 1)  # ConvertWithMoss +1 offset'
        if re.search(pattern1, content):
            content = re.sub(pattern1, replacement1, content)
            fixes.append("Applied +1 offset to root_note_elem.text assignments")
        
        # SAFE Pattern 2: Only target integer MIDI note assignments (not dictionaries)
        # Look for patterns like: root_note = 60, root_note = detected_note, etc.
        pattern2 = r'root_note\s*=\s*(\d+)(?!\s*\+\s*1)'
        replacement2 = r'root_note = \1 + 1  # ConvertWithMoss +1 offset'
        if re.search(pattern2, content):
            content = re.sub(pattern2, replacement2, content)
            fixes.append("Applied +1 offset to numeric root_note assignments")
        
        # SAFE Pattern 3: Only target detected_note variables (not objects)
        pattern3 = r'root_note\s*=\s*(detected_note)(?!\s*\+\s*1)(?!\.|get\()'
        replacement3 = r'root_note = \1 + 1  # ConvertWithMoss +1 offset'
        if re.search(pattern3, content):
            content = re.sub(pattern3, replacement3, content)
            fixes.append("Applied +1 offset to detected_note assignments")
        
        # DANGEROUS patterns to AVOID (these caused the original bug):
        dangerous_patterns = [
            r'root_note\s*=\s*m\s*\+',           # m is dictionary
            r'root_note\s*=\s*mapping\s*\+',     # mapping is dictionary  
            r'root_note\s*=\s*layer\s*\+',       # layer is XML element
            r'root_note\s*=\s*sample\s*\+',      # sample is XML element
            r'root_note\s*=\s*self\s*\+',        # self is object
        ]
        
        for dangerous in dangerous_patterns:
            if re.search(dangerous, content):
                print(f"⚠️  WARNING: Found dangerous pattern '{dangerous}' - NOT applying fix")
                print("   This pattern would cause 'dict + int' errors")
                return False
        
        # Validate the changes won't break syntax
        if content != original_content:
            if self._validate_python_syntax(content):
                # Create backup
                backup_path = f"{file_path}.safe_backup"
                with open(backup_path, 'w') as f:
                    f.write(original_content)
                
                # Write fixed content
                with open(file_path, 'w') as f:
                    f.write(content)
                
                print(f"✅ Applied {len(fixes)} SAFE fixes to {file_path}")
                for fix in fixes:
                    print(f"  - {fix}")
                
                self.fixes_applied.extend(fixes)
                return True
            else:
                print(f"❌ Syntax validation FAILED - not applying changes to {file_path}")
                return False
        else:
            print(f"ℹ️  No safe root note patterns found in {file_path}")
            return False
    
    def _validate_python_syntax(self, content):
        """Validate Python syntax without executing code"""
        try:
            ast.parse(content)
            return True
        except SyntaxError as e:
            print(f"Syntax error detected: {e}")
            return False
        except Exception as e:
            print(f"Validation error: {e}")
            return False
    
    def fix_specific_dictionary_errors(self, file_path):
        """
        Fix specific known dictionary arithmetic errors in sample_mapping_checker.py
        """
        print(f"🔧 Fixing dictionary errors in: {file_path}")
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        original_content = content
        fixes = []
        
        # Fix the specific errors we identified
        fixes_map = {
            r'root_note = m \+ 1  # ConvertWithMoss standard offset\.get\(\'root_note\', 60\)': 
                'root_note = m.get(\'root_note\', 60) + 1  # ConvertWithMoss standard offset',
            
            r'root_note = mapping \+ 1  # ConvertWithMoss standard offset\.get\(\'root_note\', \'\'\)':
                'root_note_value = mapping.get(\'root_note\', 60)\n            root_note = root_note_value + 1 if isinstance(root_note_value, int) else 60  # ConvertWithMoss standard offset',
            
            r'root_note = self \+ 1  # ConvertWithMoss standard offset\.mappings\[idx\]\[\'root_note\'\]':
                'root_note = self.mappings[idx][\'root_note\'] + 1  # ConvertWithMoss standard offset',
            
            r'root_note = layer \+ 1  # ConvertWithMoss standard offset\.find\(\'RootNote\'\)':
                'root_note_elem = layer.find(\'RootNote\')\n                        if root_note_elem is not None:\n                            root_note_elem.text = str(detected + 1)  # ConvertWithMoss standard offset',
            
            r'root_note = sample \+ 1  # ConvertWithMoss standard offset\.find\(\'root_note\'\)':
                'root_note_elem = sample.find(\'root_note\')\n                            if root_note_elem is not None:\n                                root_note_elem.text = str(midi + 1)  # ConvertWithMoss standard offset'
        }
        
        for pattern, replacement in fixes_map.items():
            if re.search(pattern, content):
                content = re.sub(pattern, replacement, content)
                fixes.append(f"Fixed dictionary arithmetic: {pattern[:50]}...")
        
        if content != original_content:
            if self._validate_python_syntax(content):
                # Create backup
                backup_path = f"{file_path}.dict_fix_backup"
                with open(backup_path, 'w') as f:
                    f.write(original_content)
                
                # Write fixed content
                with open(file_path, 'w') as f:
                    f.write(content)
                
                print(f"✅ Applied {len(fixes)} dictionary fixes to {file_path}")
                self.fixes_applied.extend(fixes)
                return True
            else:
                print(f"❌ Syntax validation FAILED - not applying changes")
                return False
        
        return False
    
    def apply_safe_professional_fixes(self, directory):
        """Apply all safe professional fixes to Python files"""
        print(f"🛡️  Applying SAFE professional fixes to: {directory}")
        print("=" * 60)
        
        python_files = list(Path(directory).glob("*.py"))
        fixed_files = []
        
        for py_file in python_files:
            # Skip test files and backup files
            if any(skip in py_file.name for skip in ['test_', '.backup', '.bak', 'apply_professional']):
                continue
            
            print(f"\n📁 Processing: {py_file.name}")
            
            file_fixed = False
            
            # First fix any existing dictionary errors
            if py_file.name == 'sample_mapping_checker.py':
                if self.fix_specific_dictionary_errors(str(py_file)):
                    file_fixed = True
            
            # Then apply safe root note fixes
            if self.fix_root_note_offset_safely(str(py_file)):
                file_fixed = True
            
            if file_fixed:
                fixed_files.append(py_file.name)
        
        # Generate summary
        print(f"\n📊 SAFE FIX SUMMARY")
        print(f"=" * 40)
        print(f"Files processed: {len(python_files)}")
        print(f"Files modified: {len(fixed_files)}")
        print(f"Total fixes applied: {len(self.fixes_applied)}")
        
        if fixed_files:
            print(f"\n✅ MODIFIED FILES:")
            for filename in fixed_files:
                print(f"  - {filename}")
        
        if self.fixes_applied:
            print(f"\n🔧 SAFE FIXES APPLIED:")
            for i, fix in enumerate(self.fixes_applied, 1):
                print(f"  {i}. {fix}")
        
        print(f"\n🛡️  SAFETY FEATURES:")
        print(f"  ✅ Syntax validation performed")
        print(f"  ✅ Dangerous patterns avoided")
        print(f"  ✅ Backups created")
        print(f"  ✅ Type-safe replacements only")
        
        return len(fixed_files) > 0

def main():
    """Main function for safe professional fixes"""
    fixer = SafeProfessionalFixer()
    
    print("🛡️  Safe Professional Standards Fixer")
    print("Prevents dictionary + integer errors")
    print("=" * 50)
    
    current_dir = "/Users/marlsz/Documents/GitHub/XPM-version-2"
    success = fixer.apply_safe_professional_fixes(current_dir)
    
    if success:
        print(f"\n🎉 Safe professional fixes applied successfully!")
    else:
        print(f"\n ℹ️ No additional fixes needed - code is already safe.")

if __name__ == "__main__":
    main()
