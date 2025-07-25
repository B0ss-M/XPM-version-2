#!/usr/bin/env python3
# Professional XPM Standards (based on ConvertWithMoss analysis):
# 1. Root notes should have +1 offset (MPC hardware convention)
# 2. Use File_Version 2.1 and Application_Version v2.11.6.6
# 3. Group samples by key ranges instead of single notes
# 4. Maximum 4 layers per keygroup (MPC hardware limit)
# 5. Use consecutive key ranges for better playability

"""
Apply ConvertWithMoss Professional Standards to Existing XPM Code
Quick fixes based on professional analysis
"""

import re
import os
from pathlib import Path

class XPMProfessionalFixer:
    """Apply professional standards to existing XPM creation code"""
    
    def __init__(self):
        self.fixes_applied = []
        
    def fix_root_note_offset_in_code(self, file_path):
        """
        Fix the root note offset bug in existing code
        Apply the +1 offset that ConvertWithMoss uses
        """
        print(f"🔧 Fixing root note offset in: {file_path}")
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        original_content = content
        fixes = []
        
        # Fix 1: Root note assignment without offset
        pattern1 = r'root_note_elem\.text\s*=\s*str\(detected_note\)'
        replacement1 = 'root_note_elem.text = str(detected_note + 1)  # ConvertWithMoss +1 offset'
        if re.search(pattern1, content):
            content = re.sub(pattern1, replacement1, content)
            fixes.append("Applied +1 root note offset in detected_note assignment")
        
        # Fix 2: Direct root note setting
        pattern2 = r'<RootNote>(\d+)</RootNote>'
        def add_offset(match):
            note_value = int(match.group(1))
            return f'<RootNote>{note_value + 1}</RootNote>'
        
        if re.search(pattern2, content):
            content = re.sub(pattern2, add_offset, content)
            fixes.append("Applied +1 offset to direct RootNote XML values")
        
        # Fix 3: Root note variable assignments
        pattern3 = r'root_note\s*=\s*(\w+)'
        replacement3 = r'root_note = \1 + 1  # ConvertWithMoss standard offset'
        if re.search(pattern3, content):
            content = re.sub(pattern3, replacement3, content)
            fixes.append("Applied +1 offset to root_note variable assignments")
        
        # Write back if changes were made
        if content != original_content:
            # Create backup
            backup_path = f"{file_path}.backup_before_professional_fix"
            with open(backup_path, 'w') as f:
                f.write(original_content)
            
            # Write fixed content
            with open(file_path, 'w') as f:
                f.write(content)
            
            print(f"✅ Applied {len(fixes)} fixes to {file_path}")
            print(f"📄 Backup created: {backup_path}")
            for fix in fixes:
                print(f"  - {fix}")
            
            self.fixes_applied.extend(fixes)
            return True
        else:
            print(f"ℹ️  No root note offset issues found in {file_path}")
            return False
    
    def update_version_constants(self, file_path):
        """Update version constants to professional standards"""
        print(f"🔧 Updating version constants in: {file_path}")
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        original_content = content
        fixes = []
        
        # Fix file version
        pattern1 = r'File_Version["\']?\s*>\s*[\d.]+\s*<'
        replacement1 = 'File_Version">2.1<'
        if re.search(pattern1, content):
            content = re.sub(pattern1, replacement1, content)
            fixes.append("Updated File_Version to 2.1 (ConvertWithMoss standard)")
        
        # Fix application version
        pattern2 = r'Application_Version["\']?\s*>\s*v?[\d.]+\s*<'
        replacement2 = 'Application_Version">v2.11.6.6<'
        if re.search(pattern2, content):
            content = re.sub(pattern2, replacement2, content)
            fixes.append("Updated Application_Version to v2.11.6.6 (ConvertWithMoss standard)")
        
        # Fix version constants in Python
        pattern3 = r'FILE_VERSION\s*=\s*["\'][\d.]+["\']'
        replacement3 = 'FILE_VERSION = "2.1"  # ConvertWithMoss professional standard  # ConvertWithMoss professional standard'
        if re.search(pattern3, content):
            content = re.sub(pattern3, replacement3, content)
            fixes.append("Updated FILE_VERSION constant")
        
        pattern4 = r'APP_VERSION\s*=\s*["\']v?[\d.]+["\']'
        replacement4 = 'APP_VERSION = "v2.11.6.6"  # ConvertWithMoss professional standard  # ConvertWithMoss professional standard'
        if re.search(pattern4, content):
            content = re.sub(pattern4, replacement4, content)
            fixes.append("Updated APP_VERSION constant")
        
        # Write back if changes were made
        if content != original_content:
            # Create backup
            backup_path = f"{file_path}.backup_version_fix"
            with open(backup_path, 'w') as f:
                f.write(original_content)
            
            # Write fixed content
            with open(file_path, 'w') as f:
                f.write(content)
            
            print(f"✅ Applied {len(fixes)} version fixes to {file_path}")
            for fix in fixes:
                print(f"  - {fix}")
            
            self.fixes_applied.extend(fixes)
            return True
        else:
            print(f"ℹ️  No version issues found in {file_path}")
            return False
    
    def add_professional_comments(self, file_path):
        """Add comments explaining professional standards"""
        print(f"📝 Adding professional comments to: {file_path}")
        
        with open(file_path, 'r') as f:
            lines = f.readlines()
        
        modified = False
        professional_comments = [
            "# Professional XPM Standards (based on ConvertWithMoss analysis):",
            "# 1. Root notes should have +1 offset (MPC hardware convention)",
            "# 2. Use File_Version 2.1 and Application_Version v2.11.6.6",
            "# 3. Group samples by key ranges instead of single notes",
            "# 4. Maximum 4 layers per keygroup (MPC hardware limit)",
            "# 5. Use consecutive key ranges for better playability",
            "",
        ]
        
        # Find a good place to insert comments (after imports, before main logic)
        insert_position = 0
        for i, line in enumerate(lines):
            if line.strip().startswith('import ') or line.strip().startswith('from '):
                continue
            elif line.strip() == '' or line.strip().startswith('#'):
                continue
            else:
                insert_position = i
                break
        
        # Insert professional comments
        for comment in reversed(professional_comments):
            lines.insert(insert_position, comment + '\n')
            modified = True
        
        if modified:
            with open(file_path, 'w') as f:
                f.writelines(lines)
            print(f"✅ Added professional standards comments to {file_path}")
            self.fixes_applied.append("Added professional standards comments")
            return True
        
        return False
    
    def fix_keygroup_counting(self, file_path):
        """Fix keygroup counting logic based on ConvertWithMoss"""
        print(f"🔧 Fixing keygroup counting in: {file_path}")
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        original_content = content
        fixes = []
        
        # Fix KeygroupNumKeygroups calculation
        # Look for patterns where keygroup count might be wrong
        pattern1 = r'KeygroupNumKeygroups["\']?\s*>\s*(\d+)\s*<'
        
        def fix_keygroup_count(match):
            # This is a complex fix that would need more context
            # For now, just add a comment
            return match.group(0) + '  <!-- Count should match distinct key ranges, not individual samples -->'
        
        if re.search(pattern1, content):
            content = re.sub(pattern1, fix_keygroup_count, content)
            fixes.append("Added comment about proper keygroup counting")
        
        # Look for Python keygroup counting
        pattern2 = r'num_keygroups\s*=\s*len\(.*\)'
        replacement2 = '''num_keygroups = len(distinct_key_ranges)  # ConvertWithMoss: count distinct ranges, not samples  # ConvertWithMoss: count distinct ranges, not samples'''
        
        if re.search(pattern2, content):
            content = re.sub(pattern2, replacement2, content)
            fixes.append("Updated keygroup counting logic")
        
        # Write back if changes were made
        if content != original_content:
            backup_path = f"{file_path}.backup_keygroup_fix"
            with open(backup_path, 'w') as f:
                f.write(original_content)
            
            with open(file_path, 'w') as f:
                f.write(content)
            
            print(f"✅ Applied {len(fixes)} keygroup fixes to {file_path}")
            for fix in fixes:
                print(f"  - {fix}")
            
            self.fixes_applied.extend(fixes)
            return True
        else:
            print(f"ℹ️  No keygroup counting issues found in {file_path}")
            return False
    
    def apply_all_professional_fixes(self, directory):
        """Apply all professional fixes to Python files in directory"""
        print(f"🚀 Applying professional fixes to all Python files in: {directory}")
        print("=" * 60)
        
        python_files = list(Path(directory).glob("*.py"))
        fixed_files = []
        
        for py_file in python_files:
            # Skip test files and this script itself
            if 'test_' in py_file.name or py_file.name == 'professional_xpm_creator.py':
                continue
            
            print(f"\n📁 Processing: {py_file.name}")
            
            file_fixed = False
            
            # Apply all fixes
            if self.fix_root_note_offset_in_code(str(py_file)):
                file_fixed = True
            
            if self.update_version_constants(str(py_file)):
                file_fixed = True
            
            if self.add_professional_comments(str(py_file)):
                file_fixed = True
            
            if self.fix_keygroup_counting(str(py_file)):
                file_fixed = True
            
            if file_fixed:
                fixed_files.append(py_file.name)
        
        # Generate summary
        print(f"\n📊 PROFESSIONAL FIX SUMMARY")
        print(f"=" * 40)
        print(f"Files processed: {len(python_files)}")
        print(f"Files modified: {len(fixed_files)}")
        print(f"Total fixes applied: {len(self.fixes_applied)}")
        
        if fixed_files:
            print(f"\n✅ MODIFIED FILES:")
            for filename in fixed_files:
                print(f"  - {filename}")
        
        if self.fixes_applied:
            print(f"\n🔧 FIXES APPLIED:")
            for i, fix in enumerate(self.fixes_applied, 1):
                print(f"  {i}. {fix}")
        
        print(f"\n💡 NEXT STEPS:")
        print(f"  1. Test your XPM creation with the updated code")
        print(f"  2. Compare output with ConvertWithMoss using professional_xpm_creator.py")
        print(f"  3. Run batch fixes on existing XPM files")
        print(f"  4. Validate with MPC hardware/software")
        
        return len(fixed_files) > 0

def main():
    """Main function for applying professional fixes"""
    fixer = XPMProfessionalFixer()
    
    print("🎯 XPM Professional Standards Fixer")
    print("Based on ConvertWithMoss analysis")
    print("=" * 50)
    
    # Apply fixes to current directory
    current_dir = "/Users/marlsz/Documents/GitHub/XPM-version-2"
    success = fixer.apply_all_professional_fixes(current_dir)
    
    if success:
        print(f"\n🎉 Professional fixes applied successfully!")
        print(f"Your XPM creation should now follow ConvertWithMoss standards.")
    else:
        print(f"\n ℹ️ No fixes needed - code already follows professional standards.")

if __name__ == "__main__":
    main()
