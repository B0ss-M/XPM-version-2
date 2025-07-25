import os
import glob
import re
from collections import defaultdict
from difflib import SequenceMatcher


# Professional XPM Standards (based on ConvertWithMoss analysis):
# 1. Root notes should have +1 offset (MPC hardware convention)
# 2. Use File_Version 2.1 and Application_Version v2.11.6.6
# 3. Group samples by key ranges instead of single notes
# 4. Maximum 4 layers per keygroup (MPC hardware limit)
# 5. Use consecutive key ranges for better playability

def extract_group_name(filename: str) -> str:
    """Return a simplified group name based on underscores, spaces and digits with improved detection."""
    base = os.path.splitext(os.path.basename(filename))[0]
    
    # Remove note indicators more thoroughly (C4, D#3, Db2, etc.)
    base = re.sub(r'[_\s-]*[A-G][#b]?[0-9]?[_\s-]*', '', base, flags=re.IGNORECASE)
    
    # Remove velocity indicators (v1, vel1, velocity_01, etc.)
    base = re.sub(r'[_\s-]*v(el)?(ocity)?[_\s-]?[0-9]+[_\s-]*', '', base, flags=re.IGNORECASE)
    
    # Remove round-robin indicators (rr1, round1, etc.)
    base = re.sub(r'[_\s-]*(rr|round)[_\s-]?[0-9]+[_\s-]*', '', base, flags=re.IGNORECASE)
    
    # Remove trailing numbers (but be more careful about meaningful numbers)
    base = re.sub(r'[_\s-]*[0-9]+$', '', base)
    
    # Split and take meaningful parts
    parts = re.split(r'[ _-]+', base)
    
    # Remove empty parts
    parts = [p for p in parts if p.strip()]
    
    if not parts:
        return base.lower()
    
    # For drum samples, try to preserve meaningful descriptors
    drum_keywords = ['kick', 'snare', 'hihat', 'hat', 'crash', 'ride', 'tom', 'cymbal', 'perc']
    
    # If first part is a drum keyword, use it
    if parts[0].lower() in drum_keywords:
        return parts[0].lower()
    
    # If any part is a drum keyword, prefer that
    for part in parts:
        if part.lower() in drum_keywords:
            return part.lower()
    
    # Otherwise use first meaningful part
    return parts[0].lower()


def group_similar_files(folder: str, similarity_threshold: float = 0.7) -> dict:
    """Group WAV files in a folder by similar names with enhanced similarity detection."""
    wav_files = glob.glob(os.path.join(folder, '*.wav'))
    
    if not wav_files:
        return {}
    
    # Phase 1: Initial grouping by extract_group_name
    initial_groups = defaultdict(list)
    for wav in wav_files:
        if '.xpm.wav' not in wav.lower():  # Skip preview files
            name = extract_group_name(wav)
            initial_groups[name].append(os.path.relpath(wav, folder))
    
    # Phase 2: Merge groups with high similarity
    final_groups = defaultdict(list)
    processed_groups = set()
    
    group_items = list(initial_groups.items())
    
    for i, (group_name, files) in enumerate(group_items):
        if group_name in processed_groups:
            continue
        
        # Start with current group
        merged_files = files[:]
        merged_name = group_name
        processed_groups.add(group_name)
        
        # Look for similar groups to merge
        for j, (other_name, other_files) in enumerate(group_items[i+1:], i+1):
            if other_name in processed_groups:
                continue
            
            # Calculate similarity between group names
            similarity = SequenceMatcher(None, group_name.lower(), other_name.lower()).ratio()
            
            # Also check if one name is contained in the other
            name_contained = (group_name.lower() in other_name.lower() or 
                            other_name.lower() in group_name.lower())
            
            if similarity > similarity_threshold or name_contained:
                merged_files.extend(other_files)
                processed_groups.add(other_name)
                
                # Use shorter, more meaningful name
                if len(other_name) < len(merged_name) and other_name.strip():
                    merged_name = other_name
        
        # Sort files in the group
        merged_files.sort()
        final_groups[merged_name] = merged_files
    
    return dict(final_groups)


def advanced_similarity_check(name1: str, name2: str) -> bool:
    """Check if two filenames represent the same instrument with advanced pattern matching."""
    # Remove file extensions
    base1 = os.path.splitext(name1)[0].lower()
    base2 = os.path.splitext(name2)[0].lower()
    
    # Basic similarity check
    similarity = SequenceMatcher(None, base1, base2).ratio()
    if similarity > 0.8:
        return True
    
    # Extract core names by removing common suffixes
    core1 = extract_group_name(name1)
    core2 = extract_group_name(name2)
    
    if core1 == core2:
        return True
    
    # Check for note variations (Piano_C4 and Piano_D4)
    note_pattern = r'^(.+?)[_\s-]*[a-g][#b]?[0-9]?'
    match1 = re.match(note_pattern, base1)
    match2 = re.match(note_pattern, base2)
    
    if match1 and match2:
        prefix1 = match1.group(1).strip('_- ')
        prefix2 = match2.group(1).strip('_- ')
        if prefix1 == prefix2:
            return True
    
    # Check for velocity variations
    vel_pattern = r'^(.+?)[_\s-]*v(el)?(ocity)?[_\s-]*[0-9]+'
    match1 = re.match(vel_pattern, base1)
    match2 = re.match(vel_pattern, base2)
    
    if match1 and match2:
        prefix1 = match1.group(1).strip('_- ')
        prefix2 = match2.group(1).strip('_- ')
        if prefix1 == prefix2:
            return True
    
    return False

